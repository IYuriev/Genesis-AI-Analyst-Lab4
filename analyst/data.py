"""Loading and joining the dataset (mobile-app product analytics from lab 3)."""
from __future__ import annotations

import os
from typing import Dict

import pandas as pd

DEFAULT_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def _read(data_dir: str, name: str, **kw) -> pd.DataFrame:
    for ext in (".csv.gz", ".csv"):
        path = os.path.join(data_dir, name + ext)
        if os.path.exists(path):
            return pd.read_csv(path, **kw)
    raise FileNotFoundError("Table '%s' not found in %s (.csv or .csv.gz)" % (name, data_dir))


def load_tables(data_dir: str = DEFAULT_DATA_DIR) -> Dict[str, pd.DataFrame]:
    """Return analysis-ready tables.

    users:    one row per registered user (reg_date, app, country) + lifetime revenue/payments
    payments: one row per payment (+ country, app, feature type, pay_date)
    sessions: one row per user-day (+ country, app)
    """
    reg = _read(data_dir, "registrations", parse_dates=["reg_dt"])
    pay = _read(data_dir, "payments", parse_dates=["pay_dt"])
    ses = _read(data_dir, "sessions_daily", parse_dates=["session_date"])
    cty = _read(data_dir, "country_info_dict")
    feat = _read(data_dir, "feature_type_dict")

    reg = reg.merge(cty, left_on="country_code", right_on="dict_country_code", how="left")
    reg["country"] = reg["country_name"].fillna(reg["country_code"]).fillna("unknown")
    reg["reg_date"] = reg["reg_dt"].dt.normalize()
    users = reg[["user_id", "reg_date", "app", "country"]].copy()

    pay = pay.merge(feat, left_on="feature_type_id", right_on="dict_feature_type_id", how="left")
    pay = pay.rename(columns={"pay_user_id": "user_id", "feature_type_name": "feature"})
    pay["pay_date"] = pay["pay_dt"].dt.normalize()
    pay = pay.merge(users[["user_id", "app", "country"]], on="user_id", how="left")
    pay = pay[["user_id", "pay_dt", "pay_date", "amount_usd", "feature", "app", "country"]]

    ses = ses.rename(columns={"ses_user_id": "user_id"})
    ses = ses.merge(users[["user_id", "app", "country"]], on="user_id", how="left")

    agg = pay.groupby("user_id").agg(revenue_usd=("amount_usd", "sum"), payments_cnt=("amount_usd", "size"))
    users = users.merge(agg, on="user_id", how="left")
    users["revenue_usd"] = users["revenue_usd"].fillna(0.0)
    users["payments_cnt"] = users["payments_cnt"].fillna(0).astype(int)
    users["is_payer"] = users["payments_cnt"] > 0
    return {"users": users, "payments": pay, "sessions": ses}


def schema_description(tables: Dict[str, pd.DataFrame]) -> str:
    """Compact schema text that is given to the LLM (no row data)."""
    lines = []
    for name, df in tables.items():
        cols = ", ".join("%s (%s)" % (c, str(t)) for c, t in df.dtypes.items())
        lines.append("%s: %d rows; columns: %s" % (name, len(df), cols))
    return "\n".join(lines)
