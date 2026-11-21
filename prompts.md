# Prompts used in the assistant

All prompts live in the module of the feature they belong to (`SYSTEM` constants). This file explains the shared design and every prompt.

## Shared design (applies to all features)

1. **The LLM never calculates.** pandas computes every number (`metrics.py`, `eda.py`, `hypotheses.py`...). The model receives a JSON of computed facts and only writes interpretation. Reason: LLMs state invented numbers with confidence (the lab text warns about this), so numbers must come from code.
2. **Structured output.** Each call returns JSON that conforms to a schema: Gemini JSON mode (`responseMimeType: application/json` + `responseSchema`) or a forced Claude tool call; `temperature = 0`. Reason: parsing JSON is simpler and more reliable than extracting numbers from free text.
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

Iterations with the live model (Gemini, `temperature = 0`; hypotheses iterations A below were made with `gemini-3.5-flash`, the final `examples/` and screenshots with the default `gemini-3.1-flash-lite`, see D):

**A. Hypotheses stated causes as facts.** First output (rule 6 absent) - hypothesis 1: "The increase in mobile web share ... **drove down** retention ... **because** mobile web acquisition channels brought in low-intent users." Hypothesis 4: "... **because** payment prompts are concentrated during onboarding". The data cannot prove these causes. Added rule (6): "phrase every cause as a possibility ('may', 'could', 'possibly'), never as an established fact, and do not use 'because' / 'caused' / 'drove' for causes the data cannot prove." Second output: "... **may reflect** lower-intent traffic, which **could explain** why mobile web conversion_pct is 4.64% ..." and each hypothesis ends with a sentence about what the data cannot confirm. The second run also produced a new useful hypothesis about the `unknown` platform (54.33 sessions per active user, likely bots or a logging error).

**B. Executive summary invented causes and used awkward wording.** First output: "Revenue fell by **-4.8%**" (double negative) and the action "Investigate the technical **and checkout issues** on mobile web" - "checkout issues" are not in the input. Added: "say 'fell by 4.8%' instead of 'fell by -4.8%'; actions must start with a verb like 'Investigate' or 'Check' and must not name causes (checkout bugs, campaigns...) that are not in the input." Second output: "Revenue fell by 4.8% ...", "Investigate the mobile web revenue drop of 978.55." No invented causes.

**C. NL to pandas used a partial day.** For "Revenue per day for the last 7 days of data" the model included 2024-05-11 (1,509 USD, a partial day, looks like a crash). Added to the system prompt: "The last day of the data is partial: for 'last N days' / trend questions end at the previous day and say so in `explanation`." Second output: "last 7 full days (2024-05-04 to 2024-05-10), excluding the partial final day".

**E. A destructive request was emulated instead of refused.** For "Delete all rows of the users table and save to disk" the model wrote `result = users.iloc[0:0]` (an empty copy of the table) and explained that saving is not permitted. Nothing is deleted (code runs on copies), but the answer was misleading. Added to the system prompt: "This tool is strictly read-only analytics. If the user asks to delete, modify, overwrite or save data ... do NOT emulate it: set `code` to an empty string and say that only read-only analysis is supported." Second output: empty code and "Only read-only analysis is supported; I cannot delete data or save files."

**D. Integration problems found only with the real API** (not prompt changes): the first default model `gemini-2.5-flash` returned 404 ("no longer available to new users"), so I tried other models; `gemini-3.5-flash` hit the free-tier limit of 20 requests per day, so the default became `gemini-3.1-flash-lite` with automatic fallback to other models on 404/429/503; newer Gemini models also spend output tokens on thinking, so a 4,000-token limit cut the JSON off (`finishReason: MAX_TOKENS`) - the limit is now at least 16,000; read timeouts and 503 "high demand" are retried.

**Edge cases checked with the live model** (`examples/03_ask.md`): a destructive request ("Delete all rows of the users table and save to disk") and an unanswerable one ("weather in Kyiv") both return empty code with an explanation instead of a made-up query (after iteration E); unsafe or broken code is blocked or retried by the validator (unit tests).
