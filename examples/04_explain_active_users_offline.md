# Why did active_users change?

_mode: offline_

Period A 2024-04-22..2024-04-28 = **85087.0**, period B 2024-04-29..2024-05-05 = **78790.0** (delta -6297.0, -7.4%)

## [offline template] active_users changed by -6297.0 (-7.4%) between the periods.
- By app: mobile web contributes -6157.0 (97.8% of the change; 82813.0 -> 76656.0).
- By country: Ukraine contributes -5857.0 (93.0% of the change; 13825.0 -> 7968.0).

**Hypothesis** (confidence: low): The largest segment above is the most likely source of the change; verify whether it follows acquisition or product changes.

**Check:** Split the leading segment further (by day and source).

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