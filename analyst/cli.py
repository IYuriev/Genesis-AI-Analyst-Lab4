"""Command line interface:  python -m analyst <command> [options]"""
from __future__ import annotations

import argparse
import json
import sys

import pandas as pd

from . import eda, explain, hypotheses, nl2pandas, retention, summary
from .data import DEFAULT_DATA_DIR, load_tables
from .llm import LLM, LLMError
from .metrics import parse_period

EXAMPLES = """examples:
  python -m analyst eda
  python -m analyst hypotheses
  python -m analyst ask "Show top-10 countries by revenue in April"
  python -m analyst explain --metric active_users --a 2024-04-22:2024-04-28 --b 2024-04-29:2024-05-05
  python -m analyst summary
  python -m analyst retention
"""


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="analyst", description="AI analyst assistant: pandas computes, an LLM interprets.", epilog=EXAMPLES, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data-dir", default=DEFAULT_DATA_DIR, help="folder with registrations/payments/sessions_daily/country_info_dict/feature_type_dict (.csv or .csv.gz)")
    p.add_argument("--offline", action="store_true", help="do not call the LLM; use deterministic templates (also used when no API key is set)")
    p.add_argument("--provider", default="auto", choices=["auto", "gemini", "anthropic"], help="LLM provider (auto: GEMINI_API_KEY, else ANTHROPIC_API_KEY, else offline)")
    p.add_argument("--model", default=None, help="model id (default: env ANALYST_MODEL, else gemini-3.1-flash-lite / claude-sonnet-5-5)")
    p.add_argument("--out", default=None, help="write the markdown report to this file")
    p.add_argument("--json", action="store_true", help="print raw JSON instead of markdown")
    p.add_argument("--verbose", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("eda", help="automatic EDA report")
    sub.add_parser("hypotheses", help="5-10 testable hypotheses grounded in computed facts")
    a = sub.add_parser("ask", help="natural language -> pandas")
    a.add_argument("question")
    e = sub.add_parser("explain", help="why did a metric change between two periods")
    e.add_argument("--metric", required=True, choices=["revenue", "payers", "avg_check", "new_users", "active_users", "sessions"])
    e.add_argument("--a", required=True, help="period A, YYYY-MM-DD:YYYY-MM-DD")
    e.add_argument("--b", required=True, help="period B, YYYY-MM-DD:YYYY-MM-DD")
    s = sub.add_parser("summary", help="executive summary (last complete 7 days vs the 7 days before)")
    s.add_argument("--a", default=None)
    s.add_argument("--b", default=None)
    r = sub.add_parser("retention", help="D1/D7 retention by platform")
    r.add_argument("--by", default="app", choices=["app", "country"])
    return p


def _json_default(o):
    if isinstance(o, (pd.DataFrame, pd.Series)):
        return o.to_dict()
    if hasattr(o, "item"):
        return o.item()
    return str(o)


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    llm = LLM(offline=args.offline, model=args.model, verbose=args.verbose, provider=args.provider)
    try:
        tables = load_tables(args.data_dir)
    except FileNotFoundError as e:
        print("error: %s" % e, file=sys.stderr)
        return 2
    try:
        if args.cmd == "eda":
            res = eda.run(tables, llm); md = eda.to_markdown(res)
        elif args.cmd == "hypotheses":
            res = hypotheses.run(tables, llm); md = hypotheses.to_markdown(res)
        elif args.cmd == "ask":
            res = nl2pandas.ask(tables, llm, args.question); md = nl2pandas.to_markdown(res)
        elif args.cmd == "explain":
            res = explain.run(tables, llm, args.metric, parse_period(args.a), parse_period(args.b)); md = explain.to_markdown(res)
        elif args.cmd == "summary":
            res = summary.run(tables, llm, parse_period(args.a) if args.a else None, parse_period(args.b) if args.b else None); md = summary.to_markdown(res)
        else:
            res = retention.retention_by(tables, args.by)
            md = "# Retention by %s\n\n```json\n%s\n```" % (args.by, json.dumps(res, indent=2))
    except (ValueError, LLMError) as e:
        print("error: %s" % e, file=sys.stderr)
        return 2
    text = json.dumps(res, indent=2, ensure_ascii=False, default=_json_default) if args.json else md
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print("saved to %s (mode: %s)" % (args.out, llm.mode))
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
