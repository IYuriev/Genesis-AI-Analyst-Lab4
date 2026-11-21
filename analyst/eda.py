"""Feature 1: automatic EDA. Numbers come from pandas; the LLM only interprets them."""
from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd

from . import guardrails
from .llm import LLM
from .metrics import data_range, daily_series, last_complete_day

SYSTEM = (
    "You are a senior product data analyst. You receive an EDA report that was computed by pandas. "
    "Interpret it for another analyst. Rules: (1) use ONLY numbers that appear in the report, copy them "
    "exactly, never compute new ones; (2) separate data-quality risks from business findings; "
    "(3) be concrete: name the table/column/segment; (4) no generic advice."
)

SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string", "description": "2-3 sentences: what this dataset is and how healthy it is"},
        "findings": {"type": "array", "items": {"type": "string"}, "description": "3-6 business findings with numbers from the report"},
        "data_quality_risks": {"type": "array", "items": {"type": "string"}},
        "next_steps": {"type": "array", "items": {"type": "string"}, "description": "3-4 concrete follow-up analyses"},
    },
    "required": ["summary", "findings", "data_quality_risks", "next_steps"],
}


def column_profile(s: pd.Series) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "dtype": str(s.dtype),
        "missing": int(s.isna().sum()),
        "missing_pct": round(100.0 * s.isna().mean(), 2),
        "unique": int(s.nunique()),
    }
    if pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s):
        d = s.describe(percentiles=[0.5, 0.99])
        out.update({k: round(float(d[k]), 2) for k in ("min", "50%", "mean", "99%", "max")})
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        out["outliers_iqr"] = int(((s < q1 - 3 * iqr) | (s > q3 + 3 * iqr)).sum()) if iqr > 0 else 0
    elif pd.api.types.is_datetime64_any_dtype(s):
        out.update({"min": str(s.min().date()), "max": str(s.max().date())})
    else:
        vc = s.value_counts(normalize=True).head(5)
        out["top_values"] = {str(k): round(100.0 * float(v), 1) for k, v in vc.items()}
    return out


def robust_anomalies(series: pd.Series, name: str, z: float = 3.5) -> List[Dict[str, Any]]:
    """Days whose change vs the previous day is extreme (median/MAD z-score on day-over-day change)."""
    diff = series.diff().dropna()
    med = diff.median()
    mad = (diff - med).abs().median() or 1e-9
    score = 0.6745 * (diff - med) / mad
    out = []
    for day, sc in score.items():
        if abs(sc) >= z:
            prev = series.shift(1)[day]
            out.append({
                "metric": name,
                "date": str(day.date()),
                "value": round(float(series[day]), 2),
                "previous_day": round(float(prev), 2),
                "change_pct": round(100.0 * (series[day] - prev) / prev, 1) if prev else None,
            })
    return out


def data_quality(tables: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
    users, pay, ses = tables["users"], tables["payments"], tables["sessions"]
    lo, hi = data_range(tables)
    issues: List[Dict[str, Any]] = []
    old = int((users["reg_date"] < lo).sum())
    if old:
        issues.append({"issue": "users registered before the event window", "count": old,
                       "detail": "event tables cover %s..%s, but registrations go back to %s; metrics like 'new users' must use reg_date inside the window"
                                 % (lo.date(), hi.date(), users["reg_date"].min().date())})
    lcd = last_complete_day(tables)
    if lcd < hi:
        issues.append({"issue": "last day is partial", "count": 1, "detail": "%s has far fewer events than the day before; excluded from trend comparisons" % hi.date()})
    unknown = int((users["app"] == "unknown").sum())
    if unknown:
        issues.append({"issue": "app = 'unknown'", "count": unknown, "detail": "unclassified platform values"})
    dups = int(users.duplicated("user_id").sum())
    issues.append({"issue": "duplicate user_id in registrations", "count": dups, "detail": "should be 0"})
    orph = int((~pay["user_id"].isin(users["user_id"])).sum()) + int((~ses["user_id"].isin(users["user_id"])).sum())
    issues.append({"issue": "payments/sessions of users missing in registrations", "count": orph, "detail": "should be 0"})
    nonpos = int((pay["amount_usd"] <= 0).sum())
    issues.append({"issue": "non-positive payment amounts", "count": nonpos, "detail": "refunds or errors; should be reviewed"})
    return issues


def build_report(tables: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    users, pay, ses = tables["users"], tables["payments"], tables["sessions"]
    lo, hi = data_range(tables)
    lcd = last_complete_day(tables)
    window = (lo, lcd)
    report: Dict[str, Any] = {"window": [str(lo.date()), str(hi.date())], "last_complete_day": str(lcd.date()), "tables": {}}
    for name, df in tables.items():
        report["tables"][name] = {"rows": int(len(df)), "columns": {c: column_profile(df[c]) for c in df.columns if c != "pay_dt"}}
    in_win = users[(users["reg_date"] >= lo) & (users["reg_date"] <= lcd)]
    report["kpis"] = {
        "users_total": int(len(users)),
        "users_registered_in_window": int(len(in_win)),
        "payers_total": int(users["is_payer"].sum()),
        "payer_share_pct_of_window_registrations": round(100.0 * float(in_win["is_payer"].mean()), 2),
        "revenue_total_usd": round(float(pay["amount_usd"].sum()), 2),
        "avg_check_usd": round(float(pay["amount_usd"].mean()), 2),
        "top1pct_payers_share_of_revenue_pct": round(100.0 * float(users[users.is_payer].sort_values("revenue_usd", ascending=False).head(max(1, int(users.is_payer.sum() * 0.01)))["revenue_usd"].sum() / pay["amount_usd"].sum()), 1),
    }
    report["distributions"] = {
        "app_share_pct": {k: round(100 * float(v), 1) for k, v in users["app"].value_counts(normalize=True).items()},
        "top5_countries_by_users_pct": {k: round(100 * float(v), 1) for k, v in users["country"].value_counts(normalize=True).head(5).items()},
        "revenue_by_feature_usd": {k: round(float(v), 2) for k, v in pay.groupby("feature")["amount_usd"].sum().items()},
        "payer_conversion_by_app_pct_in_window": {k: round(100 * float(v), 2) for k, v in in_win.groupby("app")["is_payer"].mean().items()},
    }
    anomalies: List[Dict[str, Any]] = []
    for m in ("revenue", "new_users", "active_users"):
        anomalies += robust_anomalies(daily_series(tables, m, window), m)
    report["anomalies"] = anomalies
    report["data_quality"] = data_quality(tables)
    return report


def _fallback(report: Dict[str, Any]) -> Dict[str, Any]:
    k, d = report["kpis"], report["distributions"]
    top_app = max(d["app_share_pct"], key=d["app_share_pct"].get)
    conv = d["payer_conversion_by_app_pct_in_window"]
    best = max(conv, key=conv.get)
    return {
        "summary": "[offline template] %d users, %d payers, revenue $%s, window %s..%s."
                   % (k["users_total"], k["payers_total"], format(k["revenue_total_usd"], ",.2f"), report["window"][0], report["window"][1]),
        "findings": [
            "%s is the dominant platform (%s%% of users)." % (top_app, d["app_share_pct"][top_app]),
            "Highest payer conversion in the window: %s (%s%%)." % (best, conv[best]),
            "Top 1%% of payers bring %s%% of revenue." % k["top1pct_payers_share_of_revenue_pct"],
        ] + ["Anomaly: %s on %s changed %s%% vs the previous day." % (a["metric"], a["date"], a["change_pct"]) for a in report["anomalies"][:3]],
        "data_quality_risks": ["%s: %s (%s)" % (i["issue"], i["count"], i["detail"]) for i in report["data_quality"] if i["count"]],
        "next_steps": ["Run `hypotheses` to get testable explanations.", "Run `explain` on the days flagged as anomalies."],
    }


def run(tables, llm: LLM) -> Dict[str, Any]:
    report = build_report(tables)
    interp = llm.structured(SYSTEM, "EDA report (JSON):\n" + __import__("json").dumps(report, ensure_ascii=False), SCHEMA, "eda_interpretation", lambda: _fallback(report))
    text = " ".join([interp.get("summary", "")] + interp.get("findings", []) + interp.get("data_quality_risks", []) + interp.get("next_steps", []))
    interp["unverified_numbers"] = guardrails.unverified_numbers(text, guardrails.collect_facts(report))
    return {"report": report, "interpretation": interp, "mode": llm.mode}


def to_markdown(res: Dict[str, Any]) -> str:
    r, i = res["report"], res["interpretation"]
    L = ["# Automatic EDA", "", "_mode: %s_" % res["mode"], "", "## Summary", i["summary"], "", "## Findings"]
    L += ["- " + f for f in i["findings"]]
    L += ["", "## Data quality"] + ["- " + f for f in i["data_quality_risks"]]
    L += ["", "## Anomalies (programmatic, median/MAD on day-over-day change)"]
    L += ["- %s on %s: %s (prev day %s, %s%%)" % (a["metric"], a["date"], a["value"], a["previous_day"], a["change_pct"]) for a in r["anomalies"]] or ["- none"]
    L += ["", "## Tables"]
    for name, t in r["tables"].items():
        L += ["", "### %s (%d rows)" % (name, t["rows"]), "", "| column | dtype | missing % | unique | min | median | mean | max |", "|---|---|---|---|---|---|---|---|"]
        for c, p in t["columns"].items():
            L.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (c, p["dtype"], p["missing_pct"], p["unique"], p.get("min", ""), p.get("50%", ""), p.get("mean", ""), p.get("max", "")))
    L += ["", "## KPIs", "", "```json", __import__("json").dumps(r["kpis"], indent=2), "```", "", "## Next steps"] + ["- " + s for s in i["next_steps"]]
    if i.get("unverified_numbers"):
        L += ["", "> Guardrail warning: numbers in the AI text that could not be traced to computed facts: %s" % ", ".join(i["unverified_numbers"])]
    else:
        L += ["", "> Guardrail: every number in the AI text was traced to computed facts."]
    return "\n".join(L)
