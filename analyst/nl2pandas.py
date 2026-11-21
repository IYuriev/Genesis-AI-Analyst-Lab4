"""Feature 3: natural language -> pandas. The code is shown, validated (AST allow-list) and then executed."""
from __future__ import annotations

import ast
import re
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from .data import schema_description
from .llm import LLM

SYSTEM_TMPL = """You translate analytics questions into pandas code.
Available DataFrames (already loaded, do not read files): users, payments, sessions.
Also available: pd (pandas), np (numpy).
{schema}
Semantics:
- users: one row per registered user; revenue_usd/payments_cnt are lifetime sums; is_payer = payments_cnt > 0.
  Event data (payments, sessions) covers {lo}..{hi}; users.reg_date also contains older registrations.
- payments.amount_usd is the revenue; payments.feature is premium/vip; dates are pay_date / session_date / reg_date (datetime64).
Rules: write plain pandas, no imports, no file/network access, no attribute names starting with an underscore.
Assign the final answer to a variable named `result` (DataFrame, Series or scalar). Keep it small (use head/nlargest).
For a 'month' use a date filter like (payments.pay_date >= '2024-04-01') & (payments.pay_date <= '2024-04-30').
Round money to 2 decimals. If the question cannot be answered from these tables, set `code` to an empty string and explain why in `explanation`."""

SCHEMA = {
    "type": "object",
    "properties": {
        "code": {"type": "string", "description": "pandas code that assigns `result`"},
        "explanation": {"type": "string", "description": "one or two sentences: what the code computes and which assumptions were made"},
    },
    "required": ["code", "explanation"],
}

SAFE_BUILTINS = {n: __builtins__[n] if isinstance(__builtins__, dict) else getattr(__builtins__, n)
                 for n in ("len", "sum", "min", "max", "round", "sorted", "range", "abs", "int", "float", "str", "list", "dict", "set", "tuple", "enumerate", "zip", "any", "all", "bool")}
BANNED_NAMES = {"open", "exec", "eval", "compile", "__import__", "getattr", "setattr", "delattr", "globals", "locals", "vars", "input", "breakpoint", "os", "sys", "subprocess"}
BANNED_ATTRS = {"to_csv", "to_pickle", "to_parquet", "to_excel", "to_sql", "read_csv", "read_pickle", "eval", "query_exec", "system", "popen"}
ALLOWED_NODES = (ast.Module, ast.Expr, ast.Assign, ast.AugAssign, ast.Name, ast.Load, ast.Store, ast.Constant, ast.Attribute, ast.Call, ast.keyword, ast.Subscript, ast.Slice,
                 ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.IfExp, ast.List, ast.Tuple, ast.Dict, ast.Set, ast.ListComp, ast.DictComp, ast.comprehension,
                 ast.Lambda, ast.arguments, ast.arg, ast.JoinedStr, ast.FormattedValue, ast.Starred,
                 ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow, ast.BitAnd, ast.BitOr, ast.BitXor, ast.Invert, ast.Not, ast.USub, ast.UAdd, ast.And, ast.Or,
                 ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn, ast.Is, ast.IsNot)


class UnsafeCode(Exception):
    pass


def validate(code: str) -> ast.AST:
    """Allow-list validation: no imports, no dunder/private attributes, no I/O, no statements except assignments/expressions."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise UnsafeCode("syntax error: %s" % e)
    assigns_result = False
    for node in ast.walk(tree):
        if not isinstance(node, ALLOWED_NODES):
            raise UnsafeCode("forbidden construct: %s" % type(node).__name__)
        if isinstance(node, ast.Name):
            if node.id in BANNED_NAMES or node.id.startswith("__"):
                raise UnsafeCode("forbidden name: %s" % node.id)
            if isinstance(node.ctx, ast.Store) and node.id == "result":
                assigns_result = True
        if isinstance(node, ast.Attribute) and (node.attr.startswith("_") or node.attr in BANNED_ATTRS):
            raise UnsafeCode("forbidden attribute: %s" % node.attr)
    if not assigns_result:
        raise UnsafeCode("code must assign `result`")
    return tree


def execute(code: str, tables: Dict[str, pd.DataFrame]):
    tree = validate(code)
    ns: Dict[str, Any] = {"pd": pd, "np": np, **{k: v.copy() for k, v in tables.items()}}
    exec(compile(tree, "<generated>", "exec"), {"__builtins__": SAFE_BUILTINS}, ns)
    return ns["result"]


def _fallback_factory(question: str, tables):
    """Tiny rule-based translator so the CLI is demonstrable offline. Understands a few common questions."""
    q = question.lower()

    def month_filter(df, col):
        months = {"april": "2024-04", "квіт": "2024-04", "may": "2024-05", "трав": "2024-05"}
        for k, v in months.items():
            if k in q:
                return "(%s.%s >= '%s-01') & (%s.%s < '%s')" % (df, col, v, df, col, str((pd.Timestamp(v + "-01") + pd.offsets.MonthBegin(1)).date()))
        return None

    def build():
        m = re.search(r"top[- ]?(\d+)", q)
        n = int(m.group(1)) if m else 10
        if "countr" in q and "revenue" in q:
            f = month_filter("payments", "pay_date")
            base = "payments[%s]" % f if f else "payments"
            return {"code": "result = %s.groupby('country')['amount_usd'].sum().round(2).nlargest(%d)" % (base, n), "explanation": "[offline rules] Sum of payments per country, top %d%s." % (n, " for the requested month" if f else "")}
        if "conversion" in q and "app" in q or "platform" in q and "conversion" in q:
            return {"code": "result = (users.groupby('app')['is_payer'].mean() * 100).round(2)", "explanation": "[offline rules] Share of users with at least one payment, by app (lifetime, all registered users)."}
        if "revenue" in q and ("app" in q or "platform" in q):
            return {"code": "result = payments.groupby('app')['amount_usd'].sum().round(2).sort_values(ascending=False)", "explanation": "[offline rules] Revenue by platform."}
        if "revenue" in q and "feature" in q:
            return {"code": "result = payments.groupby('feature')['amount_usd'].sum().round(2)", "explanation": "[offline rules] Revenue by feature type."}
        if "how many" in q and "user" in q:
            return {"code": "result = len(users)", "explanation": "[offline rules] Number of registered users in the dataset (includes pre-window registrations)."}
        if "revenue" in q:
            return {"code": "result = round(payments['amount_usd'].sum(), 2)", "explanation": "[offline rules] Total revenue."}
        return {"code": "", "explanation": "[offline rules] I only understand a few patterns without an LLM key (top-N countries by revenue, revenue by app/feature, conversion by app, user count). Set ANTHROPIC_API_KEY for free-form questions."}
    return build


def ask(tables, llm: LLM, question: str, max_retries: int = 1) -> Dict[str, Any]:
    from .metrics import data_range
    lo, hi = data_range(tables)
    system = SYSTEM_TMPL.format(schema=schema_description(tables), lo=lo.date(), hi=hi.date())
    prompt = "Question: " + question
    attempts = []
    for attempt in range(max_retries + 1):
        out = llm.structured(system, prompt, SCHEMA, "pandas_answer", _fallback_factory(question, tables))
        code = (out.get("code") or "").strip()
        rec: Dict[str, Any] = {"code": code, "explanation": out.get("explanation", "")}
        if not code:
            rec["error"] = None
            attempts.append(rec)
            break
        try:
            res = execute(code, tables)
            rec["result"] = res
            attempts.append(rec)
            break
        except Exception as e:  # unsafe code, runtime error, wrong column...
            rec["error"] = "%s: %s" % (type(e).__name__, e)
            attempts.append(rec)
            prompt = "Question: %s\nYour previous code failed.\nCode:\n%s\nError: %s\nFix it." % (question, code, rec["error"])
            if not llm.online:
                break
    return {"question": question, "attempts": attempts, "final": attempts[-1], "mode": llm.mode}


def to_markdown(res: Dict[str, Any]) -> str:
    f = res["final"]
    L = ["# Q: %s" % res["question"], "", "_mode: %s_" % res["mode"], ""]
    if len(res["attempts"]) > 1:
        L += ["_the first attempt failed (%s); regenerated with the error message_" % res["attempts"][0]["error"], ""]
    L += ["**What the code does:** %s" % f["explanation"], ""]
    if f["code"]:
        L += ["```python", f["code"], "```", ""]
    if f.get("error"):
        L += ["**Error:** %s" % f["error"]]
    elif "result" in f:
        r = f["result"]
        L += ["**Result:**", "", "```", (r.head(30).to_string() if isinstance(r, (pd.DataFrame, pd.Series)) else str(r)), "```"]
    return "\n".join(L)
