# Automatic EDA

_mode: llm:gemini/gemini-3.5-flash_

## Summary
This dataset tracks 202,382 users, 547,860 session records, and 11,330 payment transactions totaling $93,749.58 USD between 2024-04-05 and 2024-05-11. Data quality is structurally strong with zero missing values across critical fields, though 62,589 users registered before the event window and the final day (2024-05-11) is incomplete.

## Findings
- While mobile web dominates top-of-funnel traffic with 93.3% of users, android and desktop yield vastly superior conversion rates at 14.65% and 9.75% respectively, compared to mobile web's 4.64%.
- Revenue in the payments table is driven primarily by the premium feature ($74,138.27 USD, 84.0% of transactions) over the vip feature ($19,611.31 USD, 16.0% of transactions), yielding an average check of $8.27 USD.
- Geographic representation shifts between user acquisition and monetization: USA leads user share at 15.7% (vs Ukraine at 12.6%), but Ukraine dominates payment share at 28.6% (vs USA at 16.1%).
- Anomalous engagement spikes occurred on 2024-04-19 when active users grew by 1,191.1% (from 1,802.0 to 23,265.0) and on 2024-04-20 when new users rose by 65.7% (from 2,767.0 to 4,586.0).

## Data quality
- The users table contains 62,589 historical registrations dating back to 2013-04-05 outside the 2024-04-05 to 2024-05-11 event window, requiring strict filtering on reg_date for cohort analyses.
- The final window day 2024-05-11 is a partial day and must be excluded from daily time-series and trend calculations to prevent downward metric skew.
- User-level aggregated spend in users.revenue_usd reaches a max of $1,223.97 USD despite payments.amount_usd having a single-transaction max of $19.99 USD, reflecting heavy tail spending distributions.

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
- Analyze android channel acquisition sources to determine why conversion (14.65%) is high while app distribution share (0.6%) remains extremely low.
- Segment the 2024-04-19 active user anomaly (23,265.0 users vs 1,802.0 prior day) by sessions.country and sessions.app to isolate the traffic source.
- Evaluate user retention and average check ($8.27 USD) differences between premium feature buyers ($74,138.27 USD total) and vip feature buyers ($19,611.31 USD total).

> Guardrail: every number in the AI text was traced to computed facts.