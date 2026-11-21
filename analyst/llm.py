"""Thin LLM layer.

Every call asks the model for *structured output* through tool use (function calling),
so we never parse numbers out of free text. If no API key is available (or --offline is
given) a deterministic fallback supplied by the caller is used, so the tool still runs and
the whole pipeline can be tested without network access.
"""
from __future__ import annotations

import json
import os
from typing import Any, Callable, Dict, Optional

DEFAULT_MODEL = os.environ.get("ANALYST_MODEL", "claude-sonnet-5-5")


class LLM:
    def __init__(self, offline: bool = False, model: Optional[str] = None, verbose: bool = False):
        self.model = model or DEFAULT_MODEL
        self.verbose = verbose
        self.client = None
        self.mode = "offline"
        if not offline and os.environ.get("ANTHROPIC_API_KEY"):
            try:
                import anthropic  # imported lazily: offline mode does not need the package

                self.client = anthropic.Anthropic()
                self.mode = "llm:" + self.model
            except ImportError:
                print("[warn] package 'anthropic' is not installed -> offline mode", flush=True)

    @property
    def online(self) -> bool:
        return self.client is not None

    def structured(self, system: str, user: str, schema: Dict[str, Any], tool_name: str,
                   fallback: Callable[[], Dict[str, Any]], max_tokens: int = 3000) -> Dict[str, Any]:
        """Return a dict that conforms to `schema` (JSON Schema of the tool input)."""
        if not self.online:
            return fallback()
        tool = {"name": tool_name, "description": "Return the result of the task.", "input_schema": schema}
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=0,
            system=system,
            tools=[tool],
            tool_choice={"type": "tool", "name": tool_name},
            messages=[{"role": "user", "content": user}],
        )
        for block in resp.content:
            if getattr(block, "type", "") == "tool_use":
                if self.verbose:
                    print("[llm] %s -> %s" % (tool_name, json.dumps(block.input, ensure_ascii=False)[:500]))
                return dict(block.input)
        raise RuntimeError("Model did not return a tool call")
