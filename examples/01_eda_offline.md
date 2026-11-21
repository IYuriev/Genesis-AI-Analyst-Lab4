# Automatic EDA

_mode: offline_

## Summary
[offline template] 202382 users, 7781 payers, revenue $93,749.58, window 2024-04-05..2024-05-11.

## Findings
- mobile web is the dominant platform (93.3% of users).
- Highest payer conversion in the window: android (14.65%).
- Top 1% of payers bring 6.2% of revenue.
- Anomaly: new_users on 2024-04-20 changed 65.7% vs the previous day.
- Anomaly: active_users on 2024-04-19 changed 1191.1% vs the previous day.
- Anomaly: active_users on 2024-04-20 changed 33.6% vs the previous day.

## Data quality
- users registered before the event window: 62589 (event tables cover 2024-04-05..2024-05-11, but registrations go back to 2013-04-05; metrics like 'new users' must use reg_date inside the window)
- last day is partial: 1 (2024-05-11 has far fewer events than the day before; excluded from trend comparisons)
- app = 'unknown': 3 (unclassified platform values)

## Anomalies (programmatic, median/MAD on day-over-day change)
- new_users on 2024-04-20: 4586.0 (prev day 2767.0, 65.7%)
- active_users on 2024-04-19: 23265.0 (prev day 1802.0, 1191.1%)
- active_users on 2024-04-20: 31085.0 (prev day 23265.0, 33.6%)
- active_users on 2024-04-29: 24518.0 (prev day 33071.0, -25.9%)
- active_users on 2024-04-30: 21296.0 (prev day 24518.0, -13.1%)
- active_users on 2024-05-06: 15737.0 (prev day 19086.0, -17.5%)

## Tables

### users (202382 rows)

| column | dtype | missing % | unique | min | median | mean | max |
|---|---|---|---|---|---|---|---|
| user_id | int64 | 0.0 | 202382 | 20001.0 | 267898286.5 | 244008510.08 | 269309916.0 |
| reg_date | datetime64[ns] | 0.0 | 1774 | 2013-04-05 |  |  | 2024-05-11 |
| app | object | 0.0 | 5 |  |  |  |  |
| country | object | 0.0 | 196 |  |  |  |  |
| revenue_usd | float64 | 0.0 | 876 | 0.0 | 0.0 | 0.46 | 1223.97 |
| payments_cnt | int64 | 0.0 | 10 | 0.0 | 0.0 | 0.06 | 71.0 |
| is_payer | bool | 0.0 | 2 |  |  |  |  |

### payments (11330 rows)

| column | dtype | missing % | unique | min | median | mean | max |
|---|---|---|---|---|---|---|---|
| user_id | int64 | 0.0 | 7781 | 20030.0 | 268179918.0 | 238679885.21 | 269309406.0 |
| pay_date | datetime64[ns] | 0.0 | 37 | 2024-04-05 |  |  | 2024-05-11 |
| amount_usd | float64 | 0.0 | 488 | 5.01 | 5.99 | 8.27 | 19.99 |
| feature | object | 0.0 | 2 |  |  |  |  |
| app | object | 0.0 | 4 |  |  |  |  |
| country | object | 0.0 | 109 |  |  |  |  |

### sessions (547860 rows)

| column | dtype | missing % | unique | min | median | mean | max |
|---|---|---|---|---|---|---|---|
| user_id | int64 | 0.0 | 196318 | 20001.0 | 264653455.0 | 242923091.4 | 269309863.0 |
| session_date | datetime64[ns] | 0.0 | 37 | 2024-04-05 |  |  | 2024-05-11 |
| sessions_cnt | int64 | 0.0 | 31 | 1.0 | 1.0 | 2.75 | 34.0 |
| duration_sum | int64 | 0.0 | 32428 | 1197.0 | 2524.0 | 4967.97 | 94533.0 |
| app | object | 0.0 | 5 |  |  |  |  |
| country | object | 0.0 | 195 |  |  |  |  |

## KPIs

```json
{
  "users_total": 202382,
  "users_registered_in_window": 137226,
  "payers_total": 7781,
  "payer_share_pct_of_window_registrations": 4.76,
  "revenue_total_usd": 93749.58,
  "avg_check_usd": 8.27,
  "top1pct_payers_share_of_revenue_pct": 6.2
}
```

## Next steps
- Run `hypotheses` to get testable explanations.
- Run `explain` on the days flagged as anomalies.

> Guardrail: every number in the AI text was traced to computed facts.