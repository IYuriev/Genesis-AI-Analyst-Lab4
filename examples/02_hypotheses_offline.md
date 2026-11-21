# Hypotheses to test

_mode: offline_

## 1. Platform drives conversion  [high]
[offline template] android converts at 14.65% vs ios at 4.43%; the gap may come from paywall placement or payment friction on ios.

- evidence: F1
- how to test: Funnel by platform from paywall view to payment.
- guardrail: numbers verified against cited facts

## 2. DAU level shift is a tracking change, not growth  [high]
[offline template] Average DAU jumps from 1517.0 to 30947.0 after Apr 19 and falls -63.9% from the peak; a logging change is more likely than organic growth.

- evidence: F4
- how to test: Compare session logging code releases on Apr 18-19 and DAU of long-registered users only.
- guardrail: numbers verified against cited facts

## 3. Revenue concentrated in one feature  [medium]
[offline template] premium brings 79.1% of revenue.

- evidence: F6
- how to test: Check price elasticity and upsell paths from the other feature.
- guardrail: numbers verified against cited facts

## 4. Retention differs by platform  [medium]
[offline template] D7 retention by platform: android 8.38%, desktop 14.87%, ios 4.82%, mobile web 7.78%.

- evidence: F7
- how to test: Retention curves per platform and acquisition source.
- guardrail: numbers verified against cited facts

## 5. Few payers repeat  [medium]
[offline template] 35.8% of 7781 payers paid at least twice.

- evidence: F8
- how to test: Cohort of first payers: second payment within 14 days, by feature.
- guardrail: numbers verified against cited facts

## Facts used (computed by pandas)

**F1. Payer conversion and ARPU by platform (users registered in window)**
```json
{"android": {"users": 853, "conversion_pct": 14.65, "arpu_usd": 2.423}, "desktop": {"users": 1929, "conversion_pct": 9.75, "arpu_usd": 1.243}, "ios": {"users": 8799, "conversion_pct": 4.43, "arpu_usd": 0.547}, "mobile web": {"users": 125645, "conversion_pct": 4.64, "arpu_usd": 0.548}}
```
**F2. Payer conversion by country (countries with >= 1000 registrations): best 4 and worst 4**
```json
{"best": {"Ukraine": {"users": 12335, "conversion_pct": 13.99}, "United Kingdom": {"users": 2329, "conversion_pct": 11.89}, "Kazakhstan": {"users": 4319, "conversion_pct": 7.13}, "Germany": {"users": 1985, "conversion_pct": 6.7}}, "worst": {"Dominican Republic": {"users": 9548, "conversion_pct": 1.54}, "Panama": {"users": 1344, "conversion_pct": 1.49}, "Ecuador": {"users": 5233, "conversion_pct": 1.17}, "Honduras": {"users": 1167, "conversion_pct": 0.6}}}
```
**F3. Session depth by platform**
```json
{"android": {"avg_session_minutes": 32.14, "sessions_per_active_user": 16.92}, "desktop": {"avg_session_minutes": 33.32, "sessions_per_active_user": 14.97}, "ios": {"avg_session_minutes": 32.55, "sessions_per_active_user": 5.53}, "mobile web": {"avg_session_minutes": 29.85, "sessions_per_active_user": 7.64}, "unknown": {"avg_session_minutes": 23.57, "sessions_per_active_user": 54.33}}
```
**F4. Daily active users: level shift and decline**
```json
{"avg_dau_before_apr19": 1517.0, "avg_dau_apr19_to_apr28": 30947.0, "peak_date": "2024-04-28", "peak_dau": 33071.0, "last_complete_day": "2024-05-10", "last_dau": 11923.0, "drop_from_peak_pct": -63.9}
```
**F5. Average daily revenue by weekday (USD)**
```json
{"Friday": 2344.0, "Monday": 2539.0, "Saturday": 2772.0, "Sunday": 2914.0, "Thursday": 2574.0, "Tuesday": 2323.0, "Wednesday": 2512.0}
```
**F6. Revenue by feature type**
```json
{"premium": {"revenue_usd": 74138.27, "share_pct": 79.1, "avg_check_usd": 7.79}, "vip": {"revenue_usd": 19611.31, "share_pct": 20.9, "avg_check_usd": 10.84}}
```
**F7. Cohort retention by platform (D1 and D7, registered inside window)**
```json
{"android": {"d1_pct": 31.07, "cohort_size_d1": 853, "d7_pct": 8.38, "cohort_size_d7": 835}, "desktop": {"d1_pct": 37.71, "cohort_size_d1": 1896, "d7_pct": 14.87, "cohort_size_d7": 1601}, "ios": {"d1_pct": 23.22, "cohort_size_d1": 8797, "d7_pct": 4.82, "cohort_size_d7": 8778}, "mobile web": {"d1_pct": 19.27, "cohort_size_d1": 120448, "d7_pct": 7.78, "cohort_size_d7": 86338}}
```
**F8. Payer behaviour**
```json
{"payers": 7781, "repeat_payers_share_pct": 35.8, "median_days_from_registration_to_first_payment_for_new_users": 0.0}
```
**F9. New-user growth and mix**
```json
{"avg_daily_new_users_first_7_days": 1611.0, "avg_daily_new_users_last_7_days": 5668.0, "mobile_web_share_of_new_users_pct_first_week": 51.1, "mobile_web_share_of_new_users_pct_last_week": 99.1}
```