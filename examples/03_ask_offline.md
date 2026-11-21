# Q: Show top-10 countries by revenue in April

_mode: offline_

**What the code does:** [offline rules] Sum of payments per country, top 10 for the requested month.

```python
result = payments[(payments.pay_date >= '2024-04-01') & (payments.pay_date < '2024-05-01')].groupby('country')['amount_usd'].sum().round(2).nlargest(10)
```

**Result:**

```
country
Ukraine           13490.60
USA               11695.41
South Africa       3434.45
Chile              3218.89
Spain              2458.52
United Kingdom     2176.35
Kazakhstan         2154.20
Germany            1478.00
Argentina          1184.08
Peru               1144.77
```