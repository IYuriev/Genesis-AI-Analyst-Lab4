# Why did revenue change?

_mode: offline_

Period A 2024-04-22..2024-04-28 = **25022.06**, period B 2024-04-29..2024-05-05 = **28443.38** (delta 3421.32, 13.7%)

## [offline template] revenue changed by 3421.32 (13.7%) between the periods.
- By app: mobile web contributes 2789.04 (81.5% of the change; 23846.02 -> 26635.06).
- By country: Spain contributes 588.97 (17.2% of the change; 1345.89 -> 1934.86).
- By feature: premium contributes 2704.94 (79.1% of the change; 20572.02 -> 23276.96).

**Hypothesis** (confidence: low): The largest segment above is the most likely source of the change; verify whether it follows acquisition or product changes.

**Check:** Split the leading segment further (by day and source).

### by app

| segment | A | B | contribution | share of change % |
|---|---|---|---|---|
| mobile web | 23846.02 | 26635.06 | 2789.04 | 81.5 |
| desktop | 746.38 | 1256.41 | 510.03 | 14.9 |
| android | 252.45 | 438.49 | 186.04 | 5.4 |
| ios | 177.21 | 113.42 | -63.79 | -1.9 |

### by country

| segment | A | B | contribution | share of change % |
|---|---|---|---|---|
| Spain | 1345.89 | 1934.86 | 588.97 | 17.2 |
| Dominican Republic | 309.38 | 891.02 | 581.64 | 17.0 |
| Argentina | 583.49 | 1163.5 | 580.01 | 17.0 |
| Poland | 407.4 | 857.95 | 450.55 | 13.2 |
| United Kingdom | 1073.71 | 1460.88 | 387.17 | 11.3 |

### by feature

| segment | A | B | contribution | share of change % |
|---|---|---|---|---|
| premium | 20572.02 | 23276.96 | 2704.94 | 79.1 |
| vip | 4450.04 | 5166.42 | 716.38 | 20.9 |

> Guardrail: all numbers in the AI text were traced to the decomposition.