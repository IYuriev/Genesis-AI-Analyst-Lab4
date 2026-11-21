# Prompts used in the assistant

All prompts live in the module of the feature they belong to (`SYSTEM` constants). This file explains the shared design and every prompt.

## Shared design (applies to all features)

1. **The LLM never calculates.** pandas computes every number (`metrics.py`, `eda.py`, `hypotheses.py`...). The model receives a JSON of computed facts and only writes interpretation. Reason: LLMs state invented numbers with confidence (the lab text warns about this), so numbers must come from code.
2. **Structured output through tool use.** Each call forces a tool (`tool_choice = {"type": "tool", ...}`) with a JSON Schema, `temperature = 0`. Reason: parsing JSON from a tool call is simpler and more reliable than extracting numbers from free text.
3. **Guardrail after every answer** (`guardrails.py`). All numbers in the model text are extracted and traced back to the supplied facts (exact, rounded, as % or in thousands). Dates, durations ("14 days") and fact ids are ignored. Untraceable numbers are listed under the report as a warning. For hypotheses the numbers must be found in the *cited* facts.
4. **Schema contains the structure we want to read**, e.g. `evidence` (fact ids) for every hypothesis, `confidence` for explanations. This forces the model to ground claims and to admit uncertainty.
5. **Offline fallback.** If there is no API key the same pipeline runs with deterministic templates (used by tests and for demos without a key).

## 1. EDA interpretation (`eda.py`)

Input: the EDA report (types, missing values, distributions, outliers, anomalies, data-quality list), all computed by pandas.

Prompt rules and why:
- "use ONLY numbers that appear in the report, copy them exactly, never compute new ones" - prevents arithmetic and invented figures.
- "separate data-quality risks from business findings" - in this dataset there are old registrations outside the event window, a partial last day and 3 `unknown` platform rows; mixing them with business findings makes the report misleading.
- "be concrete: name the table/column/segment; no generic advice" - removes filler like "consider further analysis".

## 2. Hypothesis generation (`hypotheses.py`)

Input: numbered FACTS F1..F9 (conversion/ARPU by platform, by country, session depth, DAU shift and decline, weekday pattern, revenue by feature, D1/D7 retention, payer behaviour, new-user growth and mix).

Rules and why:
- Every hypothesis must cite fact ids in `evidence` and quote the numbers - the lab requires hypotheses "justified by numbers from the dataset, not general phrases". Ids make this checkable by code (`validation.ok`).
- "a hypothesis is a causal or segment claim that can be tested, not a restatement of a fact" - without it the model repeats the facts.
- `how_to_test` must name the exact cut/experiment - turns a guess into a task.
- "mark clearly when data cannot confirm a cause (e.g. a tracking change vs a real behaviour change)" - the DAU jumps from about 1.5K to 31K on one day, which is more likely a logging change than growth.

## 3. Natural language to pandas (`nl2pandas.py`)

Input: the question + the schema of the three DataFrames and their semantics (event window, lifetime fields on `users`).

Rules and why:
- "no imports, no file/network access, no underscore attributes" and "assign the final answer to `result`" - the code is then validated by an AST allow-list (`validate`) before `exec`, with restricted builtins and copies of the tables. The prompt asks for safe code, the validator enforces it (the prompt alone is not a security measure).
- Semantics of the tables are in the prompt (e.g. `users.reg_date` includes pre-window registrations) so questions like "new users" use the right filter.
- "if the question cannot be answered, return empty code and explain" - a refusal path instead of a made-up query.
- On an exception the code and the error text are sent back once ("Your previous code failed... Fix it").
- The code and the explanation are always printed, so the analyst can verify the logic.

## 4. Explaining a metric change (`explain.py`)

Input: exact decomposition by app, country, feature (`metrics.explain_change`): for additive metrics the contribution is `value_B - value_A`; for average check the exact mix decomposition. The model does not look for segments itself.

Rules: name the segments that drive the change, quote `share_of_change_pct` only when given, separate what the data shows from a guess, give one check that would confirm the hypothesis, and set `confidence`.

## 5. Executive summary (`summary.py`)

Input: KPIs for the last 7 complete days vs the previous 7, top movers, caveats (the partial last day, the DAU level shift).

Rules: structure "what happened / why it matters / what to do"; about 150 words; no jargon; every action tied to a number from the input; unreliable numbers named in `caveats` must be flagged.

## 6. Retention (custom function, `retention.py`)

Computed only (D1/D7 by platform from sessions of the registration cohort). The numbers are also used as fact F7 in the hypotheses prompt.

## Iterations

Design iterations made while building (by reading outputs of the offline pipeline and the unit tests):
1. The decomposition of `payers` by `feature` did not sum to the total change because a payer can buy both features -> the dimension was removed for this metric (found by `test_contributions_sum_to_delta`).
2. `new_users` and DAU trends were wrong when registrations before the event window were used -> the analysis window is defined by the event tables and the partial last day is excluded.
3. The first guardrail flagged dates ("Apr 19") and durations ("14 days") as invented numbers -> these patterns are ignored.

Live-model iterations: **TODO (fill in after running with a real API key)** - paste 2-3 outputs where the model's wording or numbers had to be corrected and how the prompt changed.
