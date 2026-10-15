# Fundamental — Net Income  (15 vars)

**Status:** Open — richest whitespace (only market cap is used by the 101, once).
**Notes:** Reporting-lag / lookahead risk — watch the fast-vs-slow gap; quarterly/annual variables behave as step-functions (low turnover); cross-sec, so rankable.

⬤ = used by the 101 alphas.

Caveats are emitted only when raw metadata changes how a field should be handled. `delay_0=0` requests a timing review; it never means to add `ts_delay` automatically.

| var | what it is | dim | freq | caveat |
|---|---|---|---|---|
| `adjusted_net_income_as_reported` | the Adjusted Net Income as reported in a company's Form 8-K filings with the… | cross-sec | annual | sparse coverage (387) |
| `cash_flow_to_net_income_ratio` | the Cash Flow to Net Income Ratio, indicating the proportion of a company's t… | cross-sec | quarterly | derived |
| `earnings_yield` | the Earnings Yield, calculated as the reciprocal of the Price-to-Earnings (P/… | cross-sec | quarterly | derived; `delay_0=0`: timing review; do not auto-delay |
| `earnings_yield_history` | the company's earnings per share (EPS) expressed as a percentage of its curre… | cross-sec | quarterly | derived; `delay_0=0`: timing review; do not auto-delay |
| `ev_to_t12m_net_income` | the ratio of Enterprise Value (EV) to Trailing 12-Month (T12M) Net Income. | cross-sec | monthly | derived; `delay_0=0`: timing review; do not auto-delay |
| `high_price_to_earnings_ratio` | the Price-to-Earnings (P/E) ratio calculated as the stock's highest price div… | cross-sec | quarterly | derived; `delay_0=0`: timing review; do not auto-delay |
| `low_price_to_earnings_ratio` | the low price-to-earnings (P/E) ratio of a stock, calculated by dividing the… | cross-sec | quarterly | derived; `delay_0=0`: timing review; do not auto-delay |
| `net_income` | the Net Income or Net Profit (Loss) as reported in a company's Form 8-K filin… | cross-sec | quarterly | — |
| `net_income_before_minority_interest` | the Net Income Before Minority (Non-controlling) Interest as reported in a co… | cross-sec | quarterly | — |
| `net_income_growth_pct` | the percentage change in net income, calculated by comparing the current peri… | cross-sec | quarterly | derived |
| `net_income_per_employee` | the ratio of net income to the number of employees, providing a measure of pr… | cross-sec | quarterly | derived |
| `operating_profits_discontinued_operations` | the operating (trading) profits generated from discontinued operations as rep… | cross-sec | annual | sparse coverage (176) |
| `pre_tax_income` | the Pre-Tax Income as reported in a company's Form 8-K filings with the SEC. | cross-sec | quarterly | — |
| `pretax_income_per_share` | the ratio of pre-tax income calculated on a per-share basis, providing insigh… | cross-sec | quarterly | derived; corporate-action adjusted |
| `profit_margin` | the company's profitability by comparing the amount of revenue retained as in… | cross-sec | quarterly | derived |
