# AI Analyst Assistant (Lab 4)

A command line tool that helps a product analyst work faster with data. **pandas computes every number; an LLM (Google Gemini by default, Anthropic Claude optional) only interprets them**, and a guardrail checks that no number in the AI text is invented.

Dataset: mobile-app product analytics from lab 3 (Tableau): 202,382 registrations, 11,330 payments, 547,860 user-day session rows, 196 countries, 5 platforms, period 2024-04-05..2024-05-11. The files are in `data/` (gzipped CSV).

## Functions

| Command | What it does |
|---|---|
| `eda` | Automatic EDA: column types, missing values, distributions, IQR outliers, day-over-day anomalies (median/MAD), data-quality checks (old registrations outside the window, partial last day, unknown platform, duplicates, orphans), LLM interpretation |
| `hypotheses` | 5-10 testable hypotheses. Each cites fact ids (F1..F9, computed by pandas), quotes their numbers and says how to test; the code verifies the evidence ids and the numbers |
| `ask "<question>"` | Natural language -> pandas. Shows the generated code, validates it with an AST allow-list, executes it in a restricted namespace, retries once with the error message |
| `explain --metric M --a P1 --b P2` | Why a metric changed: exact decomposition by app / country / feature (contributions sum to the total change), then the LLM names drivers and a hypothesis |
| `summary` | Executive summary for stakeholders (last 7 complete days vs the previous 7): what happened, why it matters, what to do |
| `retention` | Custom function: D1/D7 retention by platform or country (computed, no LLM) |

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export GEMINI_API_KEY=...      # free key: https://aistudio.google.com -> "Get API key" (no card needed)
```

Provider selection (`--provider auto`): `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) -> Gemini, otherwise `ANTHROPIC_API_KEY` -> Claude (`pip install anthropic`), otherwise offline. Default model `gemini-3.1-flash-lite` (automatic fallback to `gemini-3.5-flash` / `gemini-flash-latest` on 404, 429 or 503); change with `--model` or `ANALYST_MODEL`. The Gemini calls use plain HTTPS (no extra package) and retry on rate limits of the free tier.

Without a key (or with `--offline`) the tool still runs with deterministic templates, so the whole pipeline can be tried and tested; free-form `ask` questions need an LLM.

## Usage

```bash
python -m analyst eda
python -m analyst hypotheses
python -m analyst ask "Show top-10 countries by revenue in April"
python -m analyst explain --metric active_users --a 2024-04-22:2024-04-28 --b 2024-04-29:2024-05-05
python -m analyst summary
python -m analyst retention --by app
python -m analyst --out report.md eda        # save markdown; --json prints raw JSON
```

Metrics for `explain`: `revenue`, `payers`, `avg_check`, `new_users`, `active_users`, `sessions`.

## Example (live model, Gemini)

```
$ python -m analyst ask "Which 5 countries have the highest average check among countries with at least 100 payments?"
grouped = payments.groupby('country').agg(avg_check=('amount_usd', 'mean'), pay_count=('amount_usd', 'count'))
result = grouped[grouped['pay_count'] >= 100].nlargest(5, 'avg_check')[['avg_check']].round(2)

Germany 10.80 | Netherlands, Kingdom of the 10.62 | USA 10.48 | Poland 9.87 | Spain 8.73
```

Full outputs of every function on the real dataset are in `examples/` (EDA, hypotheses, six `ask` questions including a destructive and an unanswerable one, two `explain` runs, summary, retention) and screenshots with explanations are in `docs/screenshots.md`.

What the tool finds in this data (computed numbers): active users jump from 1,802 to 23,265 on 2024-04-19 (most likely a tracking change, flagged by the anomaly detector), D7 retention differs by platform (ios 4.82%, desktop 14.87%), payer conversion is 14.65% on android vs 4.43% on ios, registrations of native apps collapse after 2024-04-19 while the total grows (iOS new users 8,710 in 2024-04-05..04-19 vs 89 in 04-20..05-10, android 775 vs 78; mobile web 17,096 -> 108,549; see `examples/04c_explain_new_users_offline.md`, the numbers are computed, the text there is an offline template), 62,589 registrations are older than the event window, the `unknown` platform has 54 sessions per active user (bots or a logging error?).

## Reliability

- The LLM gets only computed facts and returns structured output (Gemini JSON mode with `responseSchema`, or a forced Claude tool call; `temperature=0`).
- `guardrails.py` traces every number of the AI text back to the facts; untraceable numbers are printed as a warning under the report.
- Generated pandas code is shown to the user and validated before execution (no imports, no I/O, no private attributes; restricted builtins; tables are copied).
- Known limits: the offline mode understands only a few question patterns; the number tracing is heuristic (e.g. a correct number derived by the model from two facts is flagged); the decomposition shows where a change happened, not why; the dataset has no acquisition source or event-level funnel, so hypotheses about channels cannot be confirmed.

## Tests

```bash
python -m unittest discover -s tests -v
```

22 offline tests: control numbers equal to the lab 3 dashboard (139,793 new users, 196,318 active, 7,781 payers, $93,749.58 revenue, Germany $2,690 / 167 payers), decomposition sums, guardrails, code-safety validator, stubbed LLM calls for both providers (structured output parsing, invented numbers flagged, retry with error message, provider selection), CLI smoke tests.

## Technologies

Python 3, pandas, numpy, Google Gemini REST API (`urllib`, no SDK), optional Anthropic SDK, unittest. Prompts are documented in [prompts.md](prompts.md).
