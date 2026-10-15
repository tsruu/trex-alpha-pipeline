# Intraday  (30 vars)

**Status:** Open — 101 never use intraday timing.
**Notes:** First/last-hour fields; close cousin of price/volume, easy to reason about; low lookahead risk.

⬤ = used by the 101 alphas.

Caveats are emitted only when raw metadata changes how a field should be handled. `delay_0=0` requests a timing review; it never means to add `ts_delay` automatically.

| var | what it is | dim | freq | caveat |
|---|---|---|---|---|
| `close_price_first_hour` | The last trade price recorded after the first hour of trading in the morning… | cross-sec | daily | corporate-action adjusted |
| `close_price_last_hour` | the last trade price of an asset during the afternoon trading session, provid… | cross-sec | daily | corporate-action adjusted |
| `high_price_first_hour` | the highest price reached during the first hour of trading in the morning ses… | cross-sec | daily | corporate-action adjusted |
| `high_price_last_hour` | The highest price of the asset during the afternoon trading session. | cross-sec | daily | corporate-action adjusted |
| `information_ratio_first_hour` | Return information ratio during the first hour of trading. | cross-sec | daily | — |
| `information_ratio_last_hour` | Return information ratio during the last hour of trading. | cross-sec | daily | — |
| `low_price_first_hour` | the lowest price recorded during the first hour of trading, providing insight… | cross-sec | daily | corporate-action adjusted |
| `low_price_last_hour` | the lowest price recorded during the last hour of trading, providing insight… | cross-sec | daily | corporate-action adjusted |
| `number_of_trades_first_hour` | the total number of trades executed during the first hour of trading in the m… | cross-sec | daily | corporate-action adjusted |
| `number_of_trades_last_hour` | the total number of trades executed during the last hour of the trading sessi… | cross-sec | daily | corporate-action adjusted |
| `open_price_first_hour` | The opening price of the asset during the first hour of trading. | cross-sec | daily | corporate-action adjusted |
| `open_price_last_hour` | The opening price of the asset during the last hour of trading. | cross-sec | daily | corporate-action adjusted |
| `return_first_hour` | the return generated during the first hour of trading, capturing the performa… | cross-sec | daily | — |
| `return_last_hour` | the return generated during the last hour of trading, capturing the asset's p… | cross-sec | daily | — |
| `skew_close_first_hour` | the skewness of asset prices during the first hour of trading, indicating the… | cross-sec | daily | — |
| `skew_close_last_hour` | the skewness of asset prices during the last hour of trading, indicating the… | cross-sec | daily | — |
| `skew_return_first_hour` | the skewness of returns during the first hour of trading, indicating the asym… | cross-sec | daily | — |
| `skew_return_last_hour` | the skewness of returns during the last hour of trading, indicating the asymm… | cross-sec | daily | — |
| `skew_volume_first_hour` | This metric represents the skewness of trading volume during the first hour o… | cross-sec | daily | — |
| `skew_volume_last_hour` | This metric represents the skewness of trading volume during the last hour of… | cross-sec | daily | — |
| `std_close_first_hour` | This metric represents the standard deviation of closing prices during the fi… | cross-sec | daily | corporate-action adjusted |
| `std_close_last_hour` | This metric represents the standard deviation of closing prices during the la… | cross-sec | daily | corporate-action adjusted |
| `std_dev_return_first_hour` | This metric represents the standard deviation of returns during the first hou… | cross-sec | daily | — |
| `std_dev_return_last_hour` | This metric represents the standard deviation of returns during the last hour… | cross-sec | daily | — |
| `std_volume_first_hour` | This metric represents the standard deviation of trading volume during the fi… | cross-sec | daily | corporate-action adjusted |
| `std_volume_last_hour` | This metric represents the standard deviation of trading volume during the la… | cross-sec | daily | corporate-action adjusted |
| `volume_first_hour` | Total trading volume during the first hour of the trading session. | cross-sec | daily | corporate-action adjusted |
| `volume_last_hour` | Total trading volume during the last hour of the trading session. | cross-sec | daily | corporate-action adjusted |
| `vwap_first_hour` | The Volume-Weighted Average Price (VWAP) calculated during the first trading… | cross-sec | daily | corporate-action adjusted |
| `vwap_last_hour` | The Volume-Weighted Average Price (VWAP) calculated during the last hour of t… | cross-sec | daily | corporate-action adjusted |
