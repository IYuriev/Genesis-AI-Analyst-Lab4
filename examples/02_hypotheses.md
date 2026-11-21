# Hypotheses to test

_mode: llm:gemini/gemini-3.5-flash_

## 1. Mobile Web Acquisition Surge Diluting Overall Conversion and Retention  [high]
The massive shift in user acquisition mix toward mobile web—where mobile web share of new users rose from 51.1% in the first week to 99.1% in the last week—could possibly explain lower platform performance, as mobile web exhibits a conversion rate of 4.64% (compared to 14.65% on android) and D1 retention of 19.27% (compared to 37.71% on desktop). Note that current data cannot confirm whether this stems from lower top-of-funnel user intent or web onboarding UX friction.

- evidence: F1, F7, F9
- how to test: Segment mobile web registration cohorts by acquisition channel/campaign and audit conversion funnel drop-off steps relative to native mobile apps.
- guardrail: numbers verified against cited facts

## 2. iOS Checkout Friction or Measurement Gaps  [high]
The low iOS conversion rate of 4.43% and low ARPU of 0.547 USD compared to Android (14.65% conversion rate and 2.423 USD ARPU), along with lower session frequency (5.53 sessions per active user on iOS vs 16.92 on Android and D1 retention of 23.22% vs 37.71% on desktop), could potentially be related to payment gateway errors on iOS. Alternatively, this may reflect tracking or attribution gaps on iOS, which current aggregate data cannot confirm.

- evidence: F1, F3, F7
- how to test: Compare checkout error rates, payment submission completion rates, and event tracking health across iOS and Android builds.
- guardrail: numbers verified against cited facts

## 3. Post-Peak Traffic Scaledown or Logging Interruption  [high]
The 63.9% decline in DAU from a peak of 33071.0 on 2024-04-28 to 11923.0 on 2024-05-10 (following an increase from 1517.0 before Apr 19 to an average of 30947.0 between Apr 19 and Apr 28) may possibly stem from the termination of a paid marketing campaign or an analytics logging outage. Available data cannot verify whether this represents real user churn or a tracking breakage.

- evidence: F4, F9
- how to test: Compare daily active users by marketing campaign channel and audit server-side event tracking logs around 2024-04-28.
- guardrail: numbers verified against cited facts

## 4. LATAM Payment Method and Local Purchasing Power Mismatch  [medium]
Geographic conversion disparities—such as Ukraine reaching 13.99% conversion across 12335 users and the United Kingdom reaching 11.89% across 2329 users versus Honduras at 0.6% across 1167 users and Ecuador at 1.17% across 5233 users—could potentially be explained by unoptimized local pricing or missing regional payment options in LATAM markets.

- evidence: F2
- how to test: Run an A/B test introducing localized payment gateways and purchasing-power adjusted price tiers in Ecuador and Honduras.
- guardrail: numbers verified against cited facts

## 5. Paywall Monetization Dependent on Onboarding Immediate Purchase  [medium]
A median of 0.0 days from registration to first payment across 7781 total payers, combined with Premium features driving 79.1% of revenue at a 7.79 USD average check, suggests monetization may be heavily dependent on immediate onboarding paywalls. However, repeat payers represent only 35.8% of total payers, indicating that long-term subscription value could possibly be underperforming.

- evidence: F6, F8
- how to test: Track repeat payment rate by initial purchase feature (Premium vs VIP at 10.84 USD average check) and test post-onboarding lifecycle monetization prompts.
- guardrail: numbers verified against cited facts

## 6. Automated Traffic Anomaly in Unknown Platform Category  [low]
The high engagement metric of 54.33 sessions per active user on the 'unknown' platform category (with 23.57 average session minutes, compared to 16.92 sessions per active user on android and 14.97 on desktop) could potentially be driven by web scrapers or tracking attribution failures. Current data cannot confirm whether this reflects real user activity.

- evidence: F3
- how to test: Filter 'unknown' platform traffic by user-agent strings, IP ranges, and client-side cookie persistence to separate legitimate users from non-human traffic.
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