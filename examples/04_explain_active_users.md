# Why did active_users change?

_mode: llm:gemini/gemini-3.5-flash_

Period A 2024-04-22..2024-04-28 = **85087.0**, period B 2024-04-29..2024-05-05 = **78790.0** (delta -6297.0, -7.4%)

## Active users dropped by 6,297.0 (-7.4%), driven almost entirely by mobile web and a sharp decline in Ukraine.
- Mobile web explains most of the change with a contribution of -6157.0 and a 97.8% share of change.
- Ukraine explains most of the geographic decline with a contribution of -5857.0 and a 93.0% share of change.
- South Africa also negatively contributed -2006.0 with a 31.9% share of change, partially offset by growth in Dominican Republic (+1935.0 contribution, -30.7% share of change).

**Hypothesis** (confidence: medium): The data shows a drop of 6297.0 active users driven mainly by mobile web in Ukraine. I hypothesize that a technical issue or service outage specifically affecting mobile web users in Ukraine caused the decline.

**Check:** Verify mobile web error logs, latency metrics, and crash rates specifically for Ukraine traffic between 2024-04-29 and 2024-05-05.

### by app

| segment | A | B | contribution | share of change % |
|---|---|---|---|---|
| mobile web | 82813.0 | 76656.0 | -6157.0 | 97.8 |
| desktop | 1860.0 | 1780.0 | -80.0 | 1.3 |
| android | 348.0 | 274.0 | -74.0 | 1.2 |
| ios | 63.0 | 80.0 | 17.0 | -0.3 |
| unknown | 3.0 | 0.0 | -3.0 | 0.0 |

### by country

| segment | A | B | contribution | share of change % |
|---|---|---|---|---|
| Ukraine | 13825.0 | 7968.0 | -5857.0 | 93.0 |
| South Africa | 9110.0 | 7104.0 | -2006.0 | 31.9 |
| Dominican Republic | 3301.0 | 5236.0 | 1935.0 | -30.7 |
| Spain | 4963.0 | 6412.0 | 1449.0 | -23.0 |
| USA | 11657.0 | 10370.0 | -1287.0 | 20.4 |

> Guardrail: all numbers in the AI text were traced to the decomposition.