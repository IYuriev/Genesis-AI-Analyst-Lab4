"""Feature 5: executive summary for stakeholders."""
from __future__ import annotations

import json
from typing import Any, Dict

import pandas as pd

from . import guardrails
from .llm import LLM
from .metrics import data_range, explain_change, last_complete_day, metric_value

SYSTEM = (
    "You write a short executive summary for a non-technical stakeholder (CEO/product lead) from computed KPIs. "
    "Structure: what happened, why it matters, what to do next. Rules: only numbers from the input, copied exactly; "
    "no jargon; say which numbers are unreliable (see `caveats`); every action must be tied to a number from the input; "
    "max ~150 words in total; say 'fell by 4.8%' instead of 'fell by -4.8%'; actions must start with a verb like "
    "'Investigate' or 'Check' and must not name causes (checkout bugs, campaigns...) that are not in the input."
)
SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {"type": "string"},
        "what_happened": {"type": "array", "items": {"type": "string"}},
        "why_it_matters": {"type": "array", "items": {"type": "string"}},
        "actions": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["headline", "what_happened", "why_it_matters", "actions"],
}
KPIS = ("revenue", "new_users", "active_users", "payers", "avg_check")


def build_inputs(tables, a=None, b=None) -> Dict[str, Any]:
    end = last_complete_day(tables)
    if b is None:
        b = (end - pd.Timedelta(days=6), end)
    if a is None:
        a = (b[0] - pd.Timedelta(days=7), b[0] - pd.Timedelta(days=1))
    kpis = {}
    for m in KPIS:
        va, vb = metric_value(tables, m, a), metric_value(tables, m, b)
        kpis[m] = {"previous": round(va, 2), "current": round(vb, 2), "change_pct": round(100.0 * (vb - va) / va, 1) if va else None}
    movers = {}
    for m in ("revenue", "active_users"):
        d = explain_change(tables, m, a, b, top=2)
        movers[m] = {"app": d["dimensions"]["app"], "country": d["dimensions"]["country"]}
    return {
        "period_current": [str(b[0].date()), str(b[1].date())], "period_previous": [str(a[0].date()), str(a[1].date())],
        "kpis": kpis, "top_movers": movers,
        "caveats": ["active_users level shifted sharply on 2024-04-19 (likely tracking), so long-term DAU trends are unreliable",
                    "the last partial day (%s) is excluded" % str(data_range(tables)[1].date()) if end < data_range(tables)[1] else "none"],
    }


def _fallback(inp: Dict[str, Any]) -> Dict[str, Any]:
    k = inp["kpis"]
    return {"headline": "[offline template] Week %s..%s vs previous week" % tuple(inp["period_current"]),
            "what_happened": ["%s: %s -> %s (%s%%)" % (m, v["previous"], v["current"], v["change_pct"]) for m, v in k.items()],
            "why_it_matters": ["Revenue and active users moved in different directions only if signs differ above; check the table."],
            "actions": ["Investigate the biggest negative KPI with `explain`."]}


def run(tables, llm: LLM, a=None, b=None) -> Dict[str, Any]:
    inp = build_inputs(tables, a, b)
    out = llm.structured(SYSTEM, "KPIs (JSON):\n" + json.dumps(inp, ensure_ascii=False), SCHEMA, "executive_summary", lambda: _fallback(inp))
    text = " ".join([out["headline"]] + out["what_happened"] + out["why_it_matters"] + out["actions"])
    out["unverified_numbers"] = guardrails.unverified_numbers(text, guardrails.collect_facts(inp))
    return {"inputs": inp, "summary": out, "mode": llm.mode}


def to_markdown(res: Dict[str, Any]) -> str:
    s, i = res["summary"], res["inputs"]
    L = ["# Executive summary", "", "_mode: %s; current %s..%s vs previous %s..%s_" % (res["mode"], *i["period_current"], *i["period_previous"]), "", "## %s" % s["headline"], "", "**What happened**"]
    L += ["- " + x for x in s["what_happened"]] + ["", "**Why it matters**"] + ["- " + x for x in s["why_it_matters"]] + ["", "**What to do next**"] + ["- " + x for x in s["actions"]]
    L += ["", "| KPI | previous | current | change % |", "|---|---|---|---|"] + ["| %s | %s | %s | %s |" % (m, v["previous"], v["current"], v["change_pct"]) for m, v in i["kpis"].items()]
    L += ["", "> Caveats: " + "; ".join(i["caveats"]), "> Guardrail: " + ("all numbers traced to computed KPIs." if not s["unverified_numbers"] else "untraced numbers: %s" % ", ".join(s["unverified_numbers"]))]
    return "\n".join(L)
