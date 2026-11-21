"""Thin LLM layer with two providers (Google Gemini, Anthropic Claude) and an offline fallback.

Every call asks the model for *structured output* that conforms to a JSON Schema
(Gemini: responseSchema / JSON mode; Claude: forced tool call), so we never parse numbers
out of free text. If no API key is available (or --offline is given) a deterministic
fallback supplied by the caller is used, so the tool still runs and the whole pipeline can
be tested without network access.

Provider choice (--provider auto): GEMINI_API_KEY / GOOGLE_API_KEY -> Gemini,
else ANTHROPIC_API_KEY -> Claude, else offline.
"""
from __future__ import annotations

import json
import os
import socket
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, Optional

DEFAULT_MODELS = {"gemini": "gemini-3.1-flash-lite", "anthropic": "claude-sonnet-5-5"}
# used only when the user did not pick a model: if the default is retired (404), overloaded (503) or over its free-tier quota (429) try the next one
GEMINI_FALLBACKS = ["gemini-3.5-flash", "gemini-flash-latest"]
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent"


class LLMError(RuntimeError):
    pass


def _gemini_key() -> Optional[str]:
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")


def to_gemini_schema(schema: Any) -> Any:
    """Gemini accepts an OpenAPI-style subset of JSON Schema: drop keys it rejects."""
    if isinstance(schema, dict):
        return {k: to_gemini_schema(v) for k, v in schema.items() if k not in ("additionalProperties", "$schema", "default")}
    if isinstance(schema, list):
        return [to_gemini_schema(v) for v in schema]
    return schema


class LLM:
    def __init__(self, offline: bool = False, model: Optional[str] = None, verbose: bool = False, provider: str = "auto"):
        self.verbose = verbose
        self.client = None  # Anthropic client (set only for provider 'anthropic')
        self.provider = "offline"
        self.mode = "offline"
        self.model = model
        self.user_model = bool(model or os.environ.get("ANALYST_MODEL"))
        if offline:
            return
        if provider == "auto":
            provider = "gemini" if _gemini_key() else ("anthropic" if os.environ.get("ANTHROPIC_API_KEY") else "offline")
        if provider == "gemini":
            if not _gemini_key():
                print("[warn] GEMINI_API_KEY is not set -> offline mode", flush=True)
                return
            self.provider = "gemini"
            self.model = model or os.environ.get("ANALYST_MODEL") or DEFAULT_MODELS["gemini"]
            self.mode = "llm:gemini/" + self.model
        elif provider == "anthropic":
            if not os.environ.get("ANTHROPIC_API_KEY"):
                print("[warn] ANTHROPIC_API_KEY is not set -> offline mode", flush=True)
                return
            try:
                import anthropic  # imported lazily: other modes do not need the package

                self.client = anthropic.Anthropic()
            except ImportError:
                print("[warn] package 'anthropic' is not installed -> offline mode", flush=True)
                return
            self.provider = "anthropic"
            self.model = model or os.environ.get("ANALYST_MODEL") or DEFAULT_MODELS["anthropic"]
            self.mode = "llm:anthropic/" + self.model

    @property
    def online(self) -> bool:
        return self.provider != "offline" or self.client is not None

    # ------------------------------------------------------------------ providers
    def _post_gemini(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """HTTP call with retries for rate limits (free tier) and temporary server errors."""
        url = GEMINI_URL % self.model
        data = json.dumps(body).encode("utf-8")
        last = None
        for attempt in range(4):
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", "x-goog-api-key": _gemini_key() or ""})
            try:
                with urllib.request.urlopen(req, timeout=180) as r:
                    return json.loads(r.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", "replace")[:400]
                last = "HTTP %s: %s" % (e.code, detail)
                daily = e.code == 429 and "per day" in detail.lower()  # daily quota: waiting seconds will not help
                if e.code in (429, 500, 502, 503, 504) and attempt < 3 and not daily:
                    time.sleep(5 * (attempt + 1))
                    continue
                raise LLMError("Gemini API error - %s" % last)
            except (urllib.error.URLError, socket.timeout, TimeoutError) as e:
                last = str(e)
                if attempt < 3:
                    time.sleep(3)
                    continue
                raise LLMError("Gemini API is unreachable: %s" % last)
        raise LLMError("Gemini API failed: %s" % last)

    def _post_with_fallback(self, body: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return self._post_gemini(body)
        except LLMError as first:
            if self.user_model:
                raise
            for alt in GEMINI_FALLBACKS:
                if alt == self.model:
                    continue
                reason = " ".join(str(first).split())[:70]
                print("[warn] %s failed (%s...); trying %s" % (self.model, reason, alt), file=sys.stderr, flush=True)
                self.model = alt
                self.mode = "llm:gemini/" + alt
                try:
                    return self._post_gemini(body)
                except LLMError:
                    continue
            raise first

    def _structured_gemini(self, system: str, user: str, schema: Dict[str, Any], max_tokens: int) -> Dict[str, Any]:
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": max(max_tokens, 16000),  # newer Gemini models also spend output tokens on thinking
                "responseMimeType": "application/json",
                "responseSchema": to_gemini_schema(schema),
            },
        }
        resp = self._post_with_fallback(body)
        try:
            cand = resp["candidates"][0]
            text = "".join(p.get("text", "") for p in cand["content"]["parts"])
        except (KeyError, IndexError):
            raise LLMError("Gemini returned no candidates: %s" % json.dumps(resp)[:300])
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            raise LLMError("Gemini returned invalid JSON (finish reason %s): %s" % (cand.get("finishReason"), text[:200]))

    def _structured_anthropic(self, system: str, user: str, schema: Dict[str, Any], tool_name: str, max_tokens: int) -> Dict[str, Any]:
        tool = {"name": tool_name, "description": "Return the result of the task.", "input_schema": schema}
        resp = self.client.messages.create(
            model=self.model, max_tokens=max_tokens, temperature=0, system=system, tools=[tool],
            tool_choice={"type": "tool", "name": tool_name}, messages=[{"role": "user", "content": user}],
        )
        for block in resp.content:
            if getattr(block, "type", "") == "tool_use":
                return dict(block.input)
        raise LLMError("Model did not return a tool call")

    # ------------------------------------------------------------------ public
    def structured(self, system: str, user: str, schema: Dict[str, Any], tool_name: str,
                   fallback: Callable[[], Dict[str, Any]], max_tokens: int = 4000) -> Dict[str, Any]:
        """Return a dict that conforms to `schema` (JSON Schema of the result)."""
        if not self.online:
            return fallback()
        if self.client is not None:
            out = self._structured_anthropic(system, user, schema, tool_name, max_tokens)
        else:
            out = self._structured_gemini(system, user, schema, max_tokens)
        if self.verbose:
            print("[llm] %s -> %s" % (tool_name, json.dumps(out, ensure_ascii=False)[:500]))
        return out
