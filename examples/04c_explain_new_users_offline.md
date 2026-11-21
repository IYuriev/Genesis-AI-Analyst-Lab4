# Why did new_users change?

_mode: offline_

Period A 2024-04-05..2024-04-19 = **27204.0**, period B 2024-04-20..2024-05-10 = **110022.0** (delta 82818.0, 304.4%)

## [offline template] new_users changed by 82818.0 (304.4%) between the periods.
- By app: mobile web contributes 91453.0 (110.4% of the change; 17096.0 -> 108549.0).
- By country: USA contributes 16236.0 (19.6% of the change; 5243.0 -> 21479.0).

**Hypothesis** (confidence: low): The largest segment above is the most likely source of the change; verify whether it follows acquisition or product changes.

**Check:** Split the leading segment further (by day and source).

### by app

| segment | A | B | contribution | share of change % |
|---|---|---|---|---|
| mobile web | 17096.0 | 108549.0 | 91453.0 | 110.4 |
| ios | 8710.0 | 89.0 | -8621.0 | -10.4 |
| android | 775.0 | 78.0 | -697.0 | -0.8 |
| desktop | 623.0 | 1306.0 | 683.0 | 0.8 |

### by country

| segment | A | B | contribution | share of change % |
|---|---|---|---|---|
| USA | 5243.0 | 21479.0 | 16236.0 | 19.6 |
| South Africa | 2801.0 | 10546.0 | 7745.0 | 9.4 |
| Dominican Republic | 903.0 | 8645.0 | 7742.0 | 9.3 |
| Peru | 962.0 | 7518.0 | 6556.0 | 7.9 |
| Ukraine | 3738.0 | 8597.0 | 4859.0 | 5.9 |

> Guardrail: all numbers in the AI text were traced to the decomposition.