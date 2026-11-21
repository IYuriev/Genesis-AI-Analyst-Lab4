"""Feature 2: hypothesis generation grounded in computed facts."""
from __future__ import annotations

import json
from typing import Any, Dict, List

import pandas as pd

from . import guardrails
from .llm import LLM
from .metrics import daily_series, data_range, last_complete_day
from .retention import retention_by

SYSTEM = (
    "You are a product analyst proposing hypotheses to investigate. You get a numbered list of FACTS computed "
    "from the data. Propose 5-10 hypotheses. Hard rules: (1) every hypothesis must cite at least one fact id "
    "in `evidence` and quote the concrete numbers from that fact; (2) never use a number that is not in the facts; "
    "(3) a hypothesis is a causal or segment claim that can be tested, not a restatement of a fact; "
    "(4) `how_to_test` names the exact cut/experiment/metric; (5) mark clearly when data cannot confirm a cause "
    "(e.g. a tracking change vs a real behaviour change); (6) phrase every cause as a possibility ('may', 'could', 'possibly'), "
    "never as an established fact, and do not use 'because' / 'caused' / 'drove' for causes the data cannot prove."
)

SCHEMA = {
    "type": "object",
    "properties": {
        "hypotheses": {
            "type": "array", "minItems": 5, "maxItems": 10,
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "hypothesis": {"type": "string"},
                    "evidence": {"type": "array", "items": {"type": "string"}, "description": "fact ids like F3"},
                    "how_to_test": {"type": "string"},
                    "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                },
                "required": ["title", "hypothesis", "evidence", "how_to_test", "priority"],
            },
        }
    },
    "required": ["hypotheses"],
}


def build_facts(tables) -> List[Dict[str, Any]]:
    users, pay, ses = tables["users"], tables["payments"], tables["sessions"]
    lo, hi = data_range(tables)
    end = last_complete_day(tables)
    win = (lo, end)
    inw = users[(users["reg_date"] >= lo) & (users["reg_date"] <= end)]
    facts: List[Dict[str, Any]] = []

    def add(title, data):
        facts.append({"id": "F%d" % (len(facts) + 1), "title": title, "data": data})

    conv = inw.groupby("app").agg(users=("user_id", "size"), conv=("is_payer", "mean"), arpu=("revenue_usd", "mean"))
    add("Payer conversion and ARPU by platform (users registered in window)",
        {k: {"users": int(r.users), "conversion_pct": round(100 * float(r.conv), 2), "arpu_usd": round(float(r.arpu), 3)} for k, r in conv.iterrows()})

    big = inw.groupby("country").agg(users=("user_id", "size"), conv=("is_payer", "mean"), arpu=("revenue_usd", "mean"))
    big = big[big["users"] >= 1000].sort_values("conv", ascending=False)
    add("Payer conversion by country (countries with >= 1000 registrations): best 4 and worst 4",
        {"best": {k: {"users": int(r.users), "conversion_pct": round(100 * float(r.conv), 2)} for k, r in big.head(4).iterrows()},
         "worst": {k: {"users": int(r.users), "conversion_pct": round(100 * float(r.conv), 2)} for k, r in big.tail(4).iterrows()}})

    s = ses[(ses["session_date"] >= lo) & (ses["session_date"] <= end)]
    sd = s.groupby("app").agg(sess=("sessions_cnt", "sum"), dur=("duration_sum", "sum"), au=("user_id", "nunique"))
    add("Session depth by platform", {k: {"avg_session_minutes": round(float(r.dur / r.sess / 60), 2), "sessions_per_active_user": round(float(r.sess / r.au), 2)} for k, r in sd.iterrows()})

    dau = daily_series(tables, "active_users", win)
    peak_day = dau.idxmax()
    add("Daily active users: level shift and decline",
        {"avg_dau_before_apr19": round(float(dau[:"2024-04-18"].mean()), 0), "avg_dau_apr19_to_apr28": round(float(dau["2024-04-19":"2024-04-28"].mean()), 0),
         "peak_date": str(peak_day.date()), "peak_dau": float(dau.max()), "last_complete_day": str(end.date()), "last_dau": float(dau.iloc[-1]),
         "drop_from_peak_pct": round(100.0 * float((dau.iloc[-1] - dau.max()) / dau.max()), 1)})

    rev = daily_series(tables, "revenue", win)
    wd = rev.groupby(rev.index.day_name()).mean()
    add("Average daily revenue by weekday (USD)", {k: round(float(v), 0) for k, v in wd.items()})

    f = pay.groupby("feature").agg(rev=("amount_usd", "sum"), n=("amount_usd", "size"), avg=("amount_usd", "mean"))
    add("Revenue by feature type", {k: {"revenue_usd": round(float(r.rev), 2), "share_pct": round(100 * float(r.rev / f.rev.sum()), 1), "avg_check_usd": round(float(r.avg), 2)} for k, r in f.iterrows()})

    ret = retention_by(tables, "app")
    add("Cohort retention by platform (D1 and D7, registered inside window)", ret["rows"])

    pu = pay.groupby("user_id").size()
    first = pay.groupby("user_id")["pay_date"].min().rename("first_pay").reset_index().merge(users[["user_id", "reg_date"]], on="user_id")
    first = first[first["reg_date"] >= lo]
    add("Payer behaviour", {"payers": int(len(pu)), "repeat_payers_share_pct": round(100.0 * float((pu >= 2).mean()), 1),
                            "median_days_from_registration_to_first_payment_for_new_users": float((first["first_pay"] - first["reg_date"]).dt.days.median()) if len(first) else None})

    nu = daily_series(tables, "new_users", win)
    w1, w5 = nu.iloc[:7], nu.iloc[-7:]
    mix = inw.assign(wk=inw["reg_date"].dt.to_period("W").astype(str))
    add("New-user growth and mix", {"avg_daily_new_users_first_7_days": round(float(w1.mean()), 0), "avg_daily_new_users_last_7_days": round(float(w5.mean()), 0),
                                     "mobile_web_share_of_new_users_pct_first_week": round(100.0 * float((inw[inw.reg_date <= lo + pd.Timedelta(days=6)]["app"] == "mobile web").mean()), 1),
                                     "mobile_web_share_of_new_users_pct_last_week": round(100.0 * float((inw[inw.reg_date > end - pd.Timedelta(days=7)]["app"] == "mobile web").mean()), 1)})
    return facts


def _fallback(facts: List[Dict[str, Any]]) -> Dict[str, Any]:
    by = {f["id"]: f for f in facts}
    h = []
    conv = by["F1"]["data"]
    best = max(conv, key=lambda k: conv[k]["conversion_pct"])
    worst = min(conv, key=lambda k: conv[k]["conversion_pct"])
    h.append({"title": "Platform drives conversion", "hypothesis": "[offline template] %s converts at %s%% vs %s at %s%%; the gap may come from paywall placement or payment friction on %s."
              % (best, conv[best]["conversion_pct"], worst, conv[worst]["conversion_pct"], worst), "evidence": ["F1"], "how_to_test": "Funnel by platform from paywall view to payment.", "priority": "high"})
    d = by["F4"]["data"]
    h.append({"title": "DAU level shift is a tracking change, not growth", "hypothesis": "[offline template] Average DAU jumps from %s to %s after Apr 19 and falls %s%% from the peak; a logging change is more likely than organic growth." % (d["avg_dau_before_apr19"], d["avg_dau_apr19_to_apr28"], d["drop_from_peak_pct"]), "evidence": ["F4"], "how_to_test": "Compare session logging code releases on Apr 18-19 and DAU of long-registered users only.", "priority": "high"})
    f = by["F6"]["data"]
    top = max(f, key=lambda k: f[k]["share_pct"])
    h.append({"title": "Revenue concentrated in one feature", "hypothesis": "[offline template] %s brings %s%% of revenue." % (top, f[top]["share_pct"]), "evidence": ["F6"], "how_to_test": "Check price elasticity and upsell paths from the other feature.", "priority": "medium"})
    r = by["F7"]["data"]
    h.append({"title": "Retention differs by platform", "hypothesis": "[offline template] D7 retention by platform: %s." % ", ".join("%s %s%%" % (k, v.get("d7_pct")) for k, v in r.items()), "evidence": ["F7"], "how_to_test": "Retention curves per platform and acquisition source.", "priority": "medium"})
    p = by["F8"]["data"]
    h.append({"title": "Few payers repeat", "hypothesis": "[offline template] %s%% of %s payers paid at least twice." % (p["repeat_payers_share_pct"], p["payers"]), "evidence": ["F8"], "how_to_test": "Cohort of first payers: second payment within 14 days, by feature.", "priority": "medium"})
    return {"hypotheses": h}


def run(tables, llm: LLM) -> Dict[str, Any]:
    facts = build_facts(tables)
    prompt = "FACTS (JSON, computed by pandas):\n" + json.dumps(facts, ensure_ascii=False)
    out = llm.structured(SYSTEM, prompt, SCHEMA, "propose_hypotheses", lambda: _fallback(facts), max_tokens=4000)
    ids = {f["id"] for f in facts}
    all_facts = guardrails.collect_facts(facts)
    checked = []
    for h in out["hypotheses"]:
        cited = [f for f in facts if f["id"] in h.get("evidence", [])]
        bad_ids = [e for e in h.get("evidence", []) if e not in ids]
        allowed = guardrails.collect_facts([c["data"] for c in cited]) if cited else []
        text = h["title"] + ". " + h["hypothesis"] + " " + h["how_to_test"]
        bad = guardrails.unverified_numbers(text, allowed if allowed else all_facts)
        h["validation"] = {"unknown_evidence_ids": bad_ids, "unverified_numbers": bad, "ok": bool(cited) and not bad_ids and not bad}
        checked.append(h)
    return {"facts": facts, "hypotheses": checked, "mode": llm.mode}


def to_markdown(res: Dict[str, Any]) -> str:
    L = ["# Hypotheses to test", "", "_mode: %s_" % res["mode"], ""]
    for n, h in enumerate(res["hypotheses"], 1):
        v = h["validation"]
        L += ["## %d. %s  [%s]" % (n, h["title"], h["priority"]), h["hypothesis"], "", "- evidence: %s" % ", ".join(h["evidence"]),
              "- how to test: %s" % h["how_to_test"],
              "- guardrail: %s" % ("numbers verified against cited facts" if v["ok"] else "NEEDS REVIEW (unknown ids %s, untraced numbers %s)" % (v["unknown_evidence_ids"], v["unverified_numbers"])), ""]
    L += ["## Facts used (computed by pandas)", ""]
    for f in res["facts"]:
        L += ["**%s. %s**" % (f["id"], f["title"]), "```json", json.dumps(f["data"], ensure_ascii=False), "```"]
    return "\n".join(L)
