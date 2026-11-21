"""Feature 4: explain why a metric rose or fell between two periods."""
from __future__ import annotations

import json
from typing import Any, Dict

from . import guardrails
from .llm import LLM
from .metrics import explain_change

SYSTEM = (
    "You are a product analyst. A metric changed between period A and period B. You receive an exact decomposition by "
    "app, country and feature computed by pandas (`contribution` is the part of the change explained by the segment). "
    "Write which segments drive the change and a hypothesis for the cause. Rules: use only numbers from the input; "
    "say 'share of change' only when the segment's share_of_change_pct is given; if one segment explains most of the change, "
    "say so; distinguish what the data shows from what is a guess; give one check that would confirm the hypothesis."
)
SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {"type": "string"},
        "drivers": {"type": "array", "items": {"type": "string"}, "description": "2-4 bullet points naming segments and their numbers"},
        "hypothesis": {"type": "string"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "check": {"type": "string"},
    },
    "required": ["headline", "drivers", "hypothesis", "confidence", "check"],
}


def _fallback(d: Dict[str, Any]) -> Dict[str, Any]:
    dr = []
    for dim, rows in d["dimensions"].items():
        if rows:
            r = rows[0]
            dr.append("By %s: %s contributes %s (%s%% of the change; %s -> %s)." % (dim, r["segment"], r["contribution"], r["share_of_change_pct"], r["value_a"], r["value_b"]))
    return {"headline": "[offline template] %s changed by %s (%s%%) between the periods." % (d["metric"], d["delta"], d["delta_pct"]),
            "drivers": dr, "hypothesis": "The largest segment above is the most likely source of the change; verify whether it follows acquisition or product changes.",
            "confidence": "low", "check": "Split the leading segment further (by day and source)."}


def run(tables, llm: LLM, metric: str, a, b) -> Dict[str, Any]:
    decomposition = explain_change(tables, metric, a, b)
    out = llm.structured(SYSTEM, "Decomposition (JSON):\n" + json.dumps(decomposition, ensure_ascii=False), SCHEMA, "explain_metric_change", lambda: _fallback(decomposition))
    text = " ".join([out["headline"], " ".join(out["drivers"]), out["hypothesis"], out["check"]])
    out["unverified_numbers"] = guardrails.unverified_numbers(text, guardrails.collect_facts(decomposition))
    return {"decomposition": decomposition, "explanation": out, "mode": llm.mode}


def to_markdown(res: Dict[str, Any]) -> str:
    d, e = res["decomposition"], res["explanation"]
    L = ["# Why did %s change?" % d["metric"], "", "_mode: %s_" % res["mode"], "",
         "Period A %s..%s = **%s**, period B %s..%s = **%s** (delta %s, %s%%)" % (*d["period_a"], d["value_a"], *d["period_b"], d["value_b"], d["delta"], d["delta_pct"]), "",
         "## %s" % e["headline"]] + ["- " + x for x in e["drivers"]] + ["", "**Hypothesis** (confidence: %s): %s" % (e["confidence"], e["hypothesis"]), "", "**Check:** %s" % e["check"], ""]
    for dim, rows in d["dimensions"].items():
        L += ["### by %s" % dim, "", "| segment | A | B | contribution | share of change % |", "|---|---|---|---|---|"]
        L += ["| %s | %s | %s | %s | %s |" % (r["segment"], r["value_a"], r["value_b"], r["contribution"], r["share_of_change_pct"]) for r in rows]
        L.append("")
    L.append("> Guardrail: " + ("all numbers in the AI text were traced to the decomposition." if not e["unverified_numbers"] else "untraced numbers: %s" % ", ".join(e["unverified_numbers"])))
    return "\n".join(L)
