"""Protection against LLM hallucinated numbers.

The model only receives numbers that were computed by pandas. After it answers we extract
every number from its text and check that each one can be traced back to the facts we
supplied (as is, rounded, as a percentage or in thousands). Untraceable numbers are reported.
"""
from __future__ import annotations

import re
from typing import Any, Iterable, List, Set

NUM_RE = re.compile(r"(?<![\w.])-?\$?\d[\d,]*(?:\.\d+)?\s?(?:%|K|k|M)?")


def _walk(obj: Any, out: List[float]) -> None:
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        out.append(float(obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            _walk(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _walk(v, out)
    elif isinstance(obj, str):
        for tok in NUM_RE.findall(obj):
            v = parse_number(tok)
            if v is not None:
                out.append(v)


def parse_number(tok: str):
    t = tok.strip().replace("$", "").replace(",", "")
    mult = 1.0
    pct = False
    if t.endswith("%"):
        pct, t = True, t[:-1]
    elif t[-1:] in ("K", "k"):
        mult, t = 1e3, t[:-1]
    elif t[-1:] == "M":
        mult, t = 1e6, t[:-1]
    try:
        v = float(t.strip()) * mult
    except ValueError:
        return None
    return v


def collect_facts(*objs: Any) -> List[float]:
    out: List[float] = []
    for o in objs:
        _walk(o, out)
    return out


def _matches(x: float, facts: Iterable[float]) -> bool:
    for f in facts:
        for cand in (f, f * 100.0, f / 1000.0, f / 1e6, abs(f)):
            tol = max(0.011 * abs(cand), 0.051 if abs(cand) < 100 else 0.51)
            if abs(abs(x) - abs(cand)) <= tol:
                return True
    return False


MONTHS = "Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
_DATE_RES = [
    re.compile(r"\b20\d\d-\d\d-\d\d\b"),
    re.compile(r"\b(?:%s)[a-z]*\.?\s+\d{1,2}(?:\s*[-\u2013]\s*\d{1,2})?\b" % MONTHS),
    re.compile(r"\b\d{1,2}\s+(?:%s)[a-z]*\b" % MONTHS),
    re.compile(r"\b\d{1,3}\s*-?\s*(?:day|days|week|weeks|hour|hours|minute|minutes|min)\b", re.I),
    re.compile(r"\bF\d+\b"),
    re.compile(r"\bD\d+\b"),
]


def _strip_non_claims(text: str) -> str:
    """Remove dates, durations ('14 days') and fact ids: they are not numeric claims about the data."""
    for rx in _DATE_RES:
        text = rx.sub(" ", text)
    return text


def unverified_numbers(text: str, facts: Iterable[float], ignore_small_ints: bool = True) -> List[str]:
    """Numbers in `text` that cannot be traced to `facts`."""
    facts = list(facts)
    text = _strip_non_claims(text)
    bad: List[str] = []
    seen: Set[str] = set()
    for tok in NUM_RE.findall(text):
        v = parse_number(tok)
        if v is None:
            continue
        if ignore_small_ints and float(v).is_integer() and abs(v) <= 12 and not tok.strip().endswith("%"):
            continue
        if re.fullmatch(r"20\d\d", tok.strip()):  # years
            continue
        if not _matches(v, facts) and tok.strip() not in seen:
            seen.add(tok.strip())
            bad.append(tok.strip())
    return bad
