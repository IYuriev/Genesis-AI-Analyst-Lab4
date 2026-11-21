"""Metric definitions. All numbers in the tool are computed here, never by the LLM."""
from __future__ import annotations

from typing import Dict, Optional, Tuple

import pandas as pd

Period = Tuple[pd.Timestamp, pd.Timestamp]  # inclusive start/end dates

# metric -> (source table, date column)
METRICS = {
    "revenue": ("payments", "pay_date"),
    "payers": ("payments", "pay_date"),
    "avg_check": ("payments", "pay_date"),
    "new_users": ("users", "reg_date"),
    "active_users": ("sessions", "session_date"),
    "sessions": ("sessions", "session_date"),
}
DIMENSIONS = {
    "revenue": ("app", "country", "feature"),
    "payers": ("app", "country"),  # not by feature: a payer can buy both features, so segments would overlap
    "avg_check": ("app", "country", "feature"),
    "new_users": ("app", "country"),
    "active_users": ("app", "country"),
    "sessions": ("app", "country"),
}


def parse_period(text: str) -> Period:
    """'2024-04-22:2024-04-28' (or a single day) -> (start, end)."""
    parts = text.split(":")
    start = pd.Timestamp(parts[0])
    end = pd.Timestamp(parts[-1])
    if end < start:
        raise ValueError("period end is before start: %s" % text)
    return start, end


def _slice(tables: Dict[str, pd.DataFrame], metric: str, period: Period) -> pd.DataFrame:
    if metric not in METRICS:
        raise ValueError("unknown metric '%s' (choose from %s)" % (metric, ", ".join(METRICS)))
    table, col = METRICS[metric]
    df = tables[table]
    return df[(df[col] >= period[0]) & (df[col] <= period[1])]


def _agg(obj, metric: str):
    """Aggregate a DataFrame or a DataFrameGroupBy for the metric."""
    if metric == "revenue":
        return obj["amount_usd"].sum()
    if metric == "avg_check":
        return obj["amount_usd"].mean()
    if metric == "sessions":
        return obj["sessions_cnt"].sum()
    return obj["user_id"].nunique()  # payers, new_users, active_users


def metric_value(tables, metric: str, period: Period, by: Optional[str] = None):
    """Scalar (by=None) or Series indexed by the dimension."""
    df = _slice(tables, metric, period)
    if by is None:
        v = _agg(df, metric)
        return 0.0 if pd.isna(v) else float(v)
    if by not in DIMENSIONS[metric]:
        raise ValueError("metric '%s' cannot be split by '%s'" % (metric, by))
    return _agg(df.groupby(by), metric).astype(float)


def daily_series(tables, metric: str, period: Period) -> pd.Series:
    df = _slice(tables, metric, period)
    _, col = METRICS[metric]
    s = _agg(df.groupby(col), metric)
    idx = pd.date_range(period[0], period[1], freq="D")
    return s.reindex(idx).fillna(0.0).astype(float)


def data_range(tables) -> Period:
    """Analysis window = period covered by the event tables (payments, sessions).

    Registrations also contain older users (registered before the window), so users.reg_date
    is deliberately not used here."""
    lo = min(tables["payments"]["pay_date"].min(), tables["sessions"]["session_date"].min())
    hi = max(tables["payments"]["pay_date"].max(), tables["sessions"]["session_date"].max())
    return lo, hi


def last_complete_day(tables) -> pd.Timestamp:
    """The last day is often partial (data pulled mid-day). Drop it if its volume is < 60% of the previous day."""
    lo, hi = data_range(tables)
    cur = float(daily_series(tables, "new_users", (hi, hi)).iloc[0])
    prev = float(daily_series(tables, "new_users", (hi - pd.Timedelta(days=1),) * 2).iloc[0])
    if prev > 0 and cur < 0.6 * prev:
        return hi - pd.Timedelta(days=1)
    return hi


def explain_change(tables, metric: str, a: Period, b: Period, top: int = 5) -> dict:
    """Decompose the change of `metric` between period a and period b by every available dimension.

    For additive metrics (revenue, payers, new_users, active_users, sessions) the contribution of a
    segment is value_b - value_a. For avg_check it is the exact mix decomposition
    share_b*avg_b - share_a*avg_a (shares of payments), which sums to avg_b - avg_a.
    """
    va, vb = metric_value(tables, metric, a), metric_value(tables, metric, b)
    delta = vb - va
    out = {
        "metric": metric,
        "period_a": [str(a[0].date()), str(a[1].date())],
        "period_b": [str(b[0].date()), str(b[1].date())],
        "value_a": round(va, 2),
        "value_b": round(vb, 2),
        "delta": round(delta, 2),
        "delta_pct": round(100.0 * delta / va, 1) if va else None,
        "days_a": (a[1] - a[0]).days + 1,
        "days_b": (b[1] - b[0]).days + 1,
        "dimensions": {},
    }
    for dim in DIMENSIONS[metric]:
        sa, sb = metric_value(tables, metric, a, dim), metric_value(tables, metric, b, dim)
        keys = sorted(set(sa.index) | set(sb.index), key=str)
        sa, sb = sa.reindex(keys).fillna(0.0), sb.reindex(keys).fillna(0.0)
        if metric == "avg_check":
            na = _slice(tables, "revenue", a).groupby(dim)["amount_usd"].size().reindex(keys).fillna(0.0)
            nb = _slice(tables, "revenue", b).groupby(dim)["amount_usd"].size().reindex(keys).fillna(0.0)
            share_a = na / na.sum() if na.sum() else na
            share_b = nb / nb.sum() if nb.sum() else nb
            contrib = share_b * sb - share_a * sa
        else:
            contrib = sb - sa
        rows = []
        for k in keys:
            rows.append({
                "segment": str(k),
                "value_a": round(float(sa[k]), 2),
                "value_b": round(float(sb[k]), 2),
                "contribution": round(float(contrib[k]), 2),
                "share_of_change_pct": round(100.0 * float(contrib[k]) / delta, 1) if delta else None,
            })
        rows.sort(key=lambda r: -abs(r["contribution"]))
        out["dimensions"][dim] = rows[:top]
    return out
