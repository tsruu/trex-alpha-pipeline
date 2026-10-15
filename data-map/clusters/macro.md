# Macro / Index  (16 vars)

**Status:** Open — all market-wide (must interact).
**Notes:** Every series is market-wide (1D) — cannot rank stocks alone; interact with a stock-level variable or use to tilt/condition; includes SPX/VIX/GLD. FRED macro observations are forward-filled daily, so CPI/GDP/unemployment carry no true day-to-day information; index and ETF series do carry daily changes.

⬤ = used by the 101 alphas.

Caveats are emitted only when raw metadata changes how a field should be handled. `delay_0=0` requests a timing review; it never means to add `ts_delay` automatically.

| var | what it is | dim | freq | caveat |
|---|---|---|---|---|
| `close_spx` | the closing price of the S&P 500 Index (SPX), which is an American stock mark… | market-wide | daily | — |
| `close_vix` | the closing price of the VIX, which is the ticker symbol for the Chicago Boar… | market-wide | daily | — |
| `cpi_all_urban_consumers` | the Consumer Price Index (CPI) for All Urban Consumers, covering all items an… | market-wide | daily | `delay_0=0`: timing review; do not auto-delay; forward-filled; underlying cadence is slower |
| `cpi_all_urban_consumers_ex_food_energy` | the Consumer Price Index (CPI) for All Urban Consumers, excluding food and en… | market-wide | daily | `delay_0=0`: timing review; do not auto-delay; forward-filled; underlying cadence is slower |
| `cpi_all_urban_consumers_purchasing_power` | the Consumer Price Index (CPI) for All Urban Consumers, indicating the purcha… | market-wide | daily | `delay_0=0`: timing review; do not auto-delay; forward-filled; underlying cadence is slower |
| `cpi_total_all_items_us` | the Consumer Price Index (CPI) for all items in the United States, not season… | market-wide | daily | `delay_0=0`: timing review; do not auto-delay; forward-filled; underlying cadence is slower |
| `gdp_implicit_price_deflator` | the Gross Domestic Product (GDP) implicit price deflator, which measures the… | market-wide | daily | `delay_0=0`: timing review; do not auto-delay; forward-filled; underlying cadence is slower |
| `gdp_now_annualized_percent_change` | the GDPNow estimate, which indicates the seasonally adjusted annual rate of c… | market-wide | daily | `delay_0=0`: timing review; do not auto-delay; forward-filled; underlying cadence is slower |
| `gdp_seasonally_adjusted_annual_rate` | the Gross Domestic Product (GDP) of the United States, expressed in billions… | market-wide | daily | `delay_0=0`: timing review; do not auto-delay; forward-filled; underlying cadence is slower |
| `real_gdp_seasonally_adjusted_annual_rate` | the Real Gross Domestic Product (GDP) of the United States, adjusted for seas… | market-wide | daily | `delay_0=0`: timing review; do not auto-delay; forward-filled; underlying cadence is slower |
| `ret1_gld` | the daily returns of the GLD ETF, which tracks the price of gold bullion. | market-wide | daily | missing encoded as `0` |
| `ret1_spx` | the 1-day return of the S&P 500 Index (SPX), calculated as the percentage cha… | market-wide | daily | derived |
| `ret1_vix` | the 1-day return of the CBOE Volatility Index (VIX), which measures market ex… | market-wide | daily | derived |
| `unemployment_level_seasonally_adjusted` | the seasonally adjusted unemployment level in the United States, measured in… | market-wide | daily | `delay_0=0`: timing review; do not auto-delay; forward-filled; underlying cadence is slower |
| `unemployment_rate_20_years_and_over` | the seasonally adjusted unemployment rate for individuals aged 20 years and o… | market-wide | daily | `delay_0=0`: timing review; do not auto-delay; forward-filled; underlying cadence is slower |
| `wti_spot_crude_oil_price` | the spot price of West Texas Intermediate (WTI) crude oil, measured in dollar… | market-wide | daily | `delay_0=0`: timing review; do not auto-delay; forward-filled; underlying cadence is slower |
