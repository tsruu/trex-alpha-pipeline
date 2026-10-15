# Seasonality  (18 vars)

**Status:** Open.
**Notes:** Calendar effects (options-expiry, month/quarter ends, FOMC/earnings proximity); low turnover; best as a conditioner/gate on another signal.

⬤ = used by the 101 alphas.

Caveats are emitted only when raw metadata changes how a field should be handled. `delay_0=0` requests a timing review; it never means to add `ts_delay` automatically.

| var | what it is | dim | freq | caveat |
|---|---|---|---|---|
| `day_of_the_week` | a numeric representation of the days of the week, where 1 corresponds to Mond… | cross-sec | daily | derived; `delay_0=0`: timing review; do not auto-delay |
| `days_since_first_trading_day_of_month` | the number of trading days that have elapsed since the first trading day of t… | cross-sec | daily | derived; `delay_0=0`: timing review; do not auto-delay; missing encoded as `0` |
| `days_since_first_trading_day_of_quarter` | the number of trading days that have elapsed since the first trading day of t… | cross-sec | daily | derived; `delay_0=0`: timing review; do not auto-delay; missing encoded as `0` |
| `days_since_first_trading_day_of_year` | the number of trading days that have elapsed since the first trading day of t… | cross-sec | daily | derived; `delay_0=0`: timing review; do not auto-delay; missing encoded as `0` |
| `days_since_last_fomc_meeting` | the number of trading days that have elapsed since the last Federal Open Mark… | cross-sec | daily | `delay_0=0`: timing review; do not auto-delay |
| `days_since_last_monthly_options_expiration` | the number of trading days that have elapsed since the last monthly options e… | cross-sec | daily | derived; `delay_0=0`: timing review; do not auto-delay; missing encoded as `0` |
| `days_since_last_quarterly_options_expiration` | the number of trading days that have elapsed since the last quarterly options… | cross-sec | daily | derived; `delay_0=0`: timing review; do not auto-delay |
| `days_since_last_trading_holiday` | the number of trading days that have elapsed since the last trading holiday. | cross-sec | daily | derived; `delay_0=0`: timing review; do not auto-delay |
| `days_until_last_trading_day_of_month` | the number of trading days remaining until the last trading day of the curren… | cross-sec | daily | derived; `delay_0=0`: timing review; do not auto-delay; missing encoded as `0` |
| `days_until_last_trading_day_of_quarter` | the number of trading days remaining until the last trading day of the curren… | cross-sec | daily | derived; `delay_0=0`: timing review; do not auto-delay; missing encoded as `0` |
| `days_until_last_trading_day_of_year` | the number of trading days remaining until the last trading day of the calend… | cross-sec | daily | derived; `delay_0=0`: timing review; do not auto-delay; missing encoded as `0` |
| `days_until_next_fomc_meeting` | the number of trading days remaining until the next Federal Open Market Commi… | cross-sec | daily | `delay_0=0`: timing review; do not auto-delay |
| `days_until_next_monthly_options_expiration` | the number of trading days remaining until the next monthly options expiratio… | cross-sec | daily | derived; `delay_0=0`: timing review; do not auto-delay; missing encoded as `0` |
| `days_until_next_quarterly_options_expiration` | the number of trading days remaining until the next quarterly options expirat… | cross-sec | daily | derived; `delay_0=0`: timing review; do not auto-delay; missing encoded as `0` |
| `days_until_next_trading_holiday` | the number of trading days remaining until the next scheduled trading holiday… | cross-sec | daily | derived; `delay_0=0`: timing review; do not auto-delay |
| `month_of_the_year` | a numeric representation of the months of the year, where each month is assig… | cross-sec | monthly | derived; `delay_0=0`: timing review; do not auto-delay |
| `quarter_of_year` | a numeric representation of the quarter of the year, where 1 represents the f… | cross-sec | quarterly | derived; `delay_0=0`: timing review; do not auto-delay |
| `trading_days_until_next_earnings_announcement` | the number of trading days remaining until the next earnings announcement dat… | cross-sec | daily | derived |
