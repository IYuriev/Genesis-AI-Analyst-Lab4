"""Offline tests (no API key needed): python -m unittest discover -s tests -v"""
import os
import sys
import unittest
import warnings

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings("ignore")

from analyst import guardrails, hypotheses, nl2pandas, cli  # noqa: E402
from analyst.data import load_tables  # noqa: E402
from analyst.llm import LLM  # noqa: E402
from analyst.metrics import data_range, explain_change, metric_value, parse_period  # noqa: E402

T = load_tables()


class TestNumbersMatchLab3(unittest.TestCase):
    """Control numbers of the Tableau dashboard (lab 3) must be reproduced by the tool."""

    def test_kpis(self):
        w = data_range(T)
        self.assertEqual(metric_value(T, "new_users", w), 139793)
        self.assertEqual(metric_value(T, "active_users", w), 196318)
        self.assertEqual(metric_value(T, "payers", w), 7781)
        self.assertAlmostEqual(metric_value(T, "revenue", w), 93749.58, places=2)
        self.assertAlmostEqual(metric_value(T, "avg_check", w), 8.27, places=2)

    def test_germany(self):
        df = T["payments"]
        g = df[(df.country == "Germany")]
        self.assertAlmostEqual(g.amount_usd.sum(), 2690, delta=1)
        self.assertEqual(g.user_id.nunique(), 167)


class TestExplainChange(unittest.TestCase):
    def test_contributions_sum_to_delta(self):
        a, b = parse_period("2024-04-22:2024-04-28"), parse_period("2024-04-29:2024-05-05")
        for metric in ("revenue", "payers", "active_users", "avg_check"):
            d = explain_change(T, metric, a, b, top=500)
            for dim, rows in d["dimensions"].items():
                self.assertAlmostEqual(sum(r["contribution"] for r in rows), d["delta"], delta=0.05, msg="%s by %s" % (metric, dim))

    def test_bad_period(self):
        with self.assertRaises(ValueError):
            parse_period("2024-05-05:2024-05-01")


class TestGuardrails(unittest.TestCase):
    facts = guardrails.collect_facts({"revenue": 93749.58, "conv": 4.43, "n": 7781})

    def test_traced(self):
        self.assertEqual(guardrails.unverified_numbers("Revenue is $93,750, conversion 4.4%, 7,781 payers.", self.facts), [])

    def test_hallucinated(self):
        self.assertEqual(guardrails.unverified_numbers("Revenue grew 37% to $120,000.", self.facts), ["37%", "$120,000"])

    def test_dates_and_durations_ignored(self):
        self.assertEqual(guardrails.unverified_numbers("On Apr 19 (F4) within 14 days, 2024-04-19.", self.facts), [])


class TestSafeExecution(unittest.TestCase):
    def test_accepts_plain_pandas(self):
        r = nl2pandas.execute("result = users['app'].value_counts().head(2)", T)
        self.assertEqual(len(r), 2)

    def test_rejects_dangerous(self):
        for code in ("import os\nresult = 1", "result = open('/etc/passwd').read()", "result = users.__class__", "result = __import__('os')",
                     "result = users.to_csv('x.csv')", "exec('result=1')", "def f():\n    pass\nresult = 1", "x = 1"):
            with self.assertRaises(Exception, msg=code):
                nl2pandas.execute(code, T)

    def test_does_not_mutate_original(self):
        n = len(T["users"])
        nl2pandas.execute("users = users.head(3)\nresult = len(users)", T)
        self.assertEqual(len(T["users"]), n)

    def test_offline_translation(self):
        res = nl2pandas.ask(T, LLM(offline=True), "Show top-3 countries by revenue")
        self.assertEqual(list(res["final"]["result"].index), ["Ukraine", "USA", "South Africa"])

    def test_unanswerable_question(self):
        res = nl2pandas.ask(T, LLM(offline=True), "What is the weather?")
        self.assertEqual(res["final"]["code"], "")


class TestHypotheses(unittest.TestCase):
    def test_offline_hypotheses_have_evidence_and_are_checked(self):
        res = hypotheses.run(T, LLM(offline=True))
        self.assertGreaterEqual(len(res["hypotheses"]), 5)
        for h in res["hypotheses"]:
            self.assertTrue(h["evidence"])
            self.assertIn("ok", h["validation"])


class _StubClient:
    """Imitates anthropic.Anthropic().messages.create returning a tool call (no network)."""

    def __init__(self, payload):
        from types import SimpleNamespace
        self.calls = []
        block = SimpleNamespace(type="tool_use", input=payload)
        self.messages = SimpleNamespace(create=lambda **kw: (self.calls.append(kw), SimpleNamespace(content=[block]))[1])


class TestLLMPathWithStub(unittest.TestCase):
    def test_tool_call_is_parsed_and_hallucinations_flagged(self):
        from analyst import explain
        llm = LLM(offline=True)
        stub = _StubClient({"headline": "Revenue grew 99% to $777,777", "drivers": ["mobile web added 81.5% of the change"],
                            "hypothesis": "campaign", "confidence": "medium", "check": "split by day"})
        llm.client, llm.mode = stub, "llm:stub"
        res = explain.run(T, llm, "revenue", parse_period("2024-04-22:2024-04-28"), parse_period("2024-04-29:2024-05-05"))
        self.assertEqual(stub.calls[0]["tool_choice"]["type"], "tool")      # structured output is forced
        self.assertEqual(stub.calls[0]["temperature"], 0)
        self.assertIn("99%", res["explanation"]["unverified_numbers"])      # invented numbers are caught
        self.assertIn("$777,777", res["explanation"]["unverified_numbers"])
        self.assertNotIn("81.5%", res["explanation"]["unverified_numbers"])  # real number passes

    def test_nl2pandas_retries_with_error_message(self):
        llm = LLM(offline=True)
        answers = [{"code": "result = users['no_such_column'].sum()", "explanation": "bad"}, {"code": "result = len(users)", "explanation": "fixed"}]
        stub = _StubClient(answers[0])
        seq = iter(answers)
        from types import SimpleNamespace
        stub.messages = SimpleNamespace(create=lambda **kw: (stub.calls.append(kw), SimpleNamespace(content=[SimpleNamespace(type="tool_use", input=next(seq))]))[1])
        llm.client, llm.mode = stub, "llm:stub"
        res = nl2pandas.ask(T, llm, "how many users?")
        self.assertEqual(len(res["attempts"]), 2)
        self.assertIn("KeyError", res["attempts"][0]["error"])
        self.assertIn("Error:", stub.calls[1]["messages"][0]["content"])   # the error was fed back to the model
        self.assertEqual(res["final"]["result"], len(T["users"]))


class TestCLI(unittest.TestCase):
    def test_runs(self):
        for argv in (["--offline", "eda"], ["--offline", "summary"], ["--offline", "retention"],
                     ["--offline", "explain", "--metric", "revenue", "--a", "2024-04-22:2024-04-28", "--b", "2024-04-29:2024-05-05"]):
            self.assertEqual(cli.main(argv), 0, argv)

    def test_bad_metric_period_returns_error_code(self):
        self.assertEqual(cli.main(["--offline", "explain", "--metric", "revenue", "--a", "2024-05-05:2024-05-01", "--b", "2024-05-06"]), 2)

    def test_missing_data_dir(self):
        self.assertEqual(cli.main(["--data-dir", "/nonexistent", "--offline", "eda"]), 2)


if __name__ == "__main__":
    unittest.main()
