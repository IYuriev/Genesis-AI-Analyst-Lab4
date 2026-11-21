"""Feature 6 (custom): cohort retention by platform. Computed, then commented on by the LLM."""
from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from .metrics import data_range, last_complete_day


def retention_by(tables, by: str = "app", days=(1, 7)) -> Dict[str, Any]:
    users, ses = tables["users"], tables["sessions"]
    lo, _ = data_range(tables)
    end = last_complete_day(tables)
    out: Dict[str, Any] = {"cohort": "registered %s..(last complete day - N)" % lo.date(), "by": by, "rows": {}}
    keys = ses[["user_id", "session_date"]].drop_duplicates()
    for n in days:
        cohort = users[(users["reg_date"] >= lo) & (users["reg_date"] <= end - pd.Timedelta(days=n))][["user_id", "reg_date", by]].copy()
        cohort["target"] = cohort["reg_date"] + pd.Timedelta(days=n)
        hit = cohort.merge(keys, left_on=["user_id", "target"], right_on=["user_id", "session_date"], how="left", indicator=True)
        hit["retained"] = hit["_merge"] == "both"
        res = hit.groupby(by)["retained"].agg(["mean", "size"])
        for seg, row in res.iterrows():
            out["rows"].setdefault(str(seg), {})["d%d_pct" % n] = round(100.0 * float(row["mean"]), 2)
            out["rows"][str(seg)]["cohort_size_d%d" % n] = int(row["size"])
        out.setdefault("overall", {})["d%d_pct" % n] = round(100.0 * float(hit["retained"].mean()), 2)
    return out
