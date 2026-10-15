# Fundamental — Earnings  (18 vars)

**Status:** Open — richest whitespace (only market cap is used by the 101, once).
**Notes:** Reporting-lag / lookahead risk — watch the fast-vs-slow gap; quarterly/annual variables behave as step-functions (low turnover); cross-sec, so rankable.

⬤ = used by the 101 alphas.

Caveats are emitted only when raw metadata changes how a field should be handled. `delay_0=0` requests a timing review; it never means to add `ts_delay` automatically.

| var | what it is | dim | freq | caveat |
|---|---|---|---|---|
| `average_number_of_shares_for_eps` | the average number of shares outstanding used in the calculation of Earnings… | cross-sec | quarterly | corporate-action adjusted |
| `basic_eps` | the Basic Earnings Per Share (EPS) as reported in a company's Form 8-K filing… | cross-sec | quarterly | corporate-action adjusted |
| `diluted_eps` | the Diluted Earnings Per Share (EPS) as reported in a company's Form 8-K fili… | cross-sec | quarterly | corporate-action adjusted |
| `diluted_weighted_average_shares` | the Diluted Weighted Average Shares outstanding, which accounts for all poten… | cross-sec | quarterly | corporate-action adjusted |
| `ebit_yield` | the Earnings Before Interest and Taxes (EBIT) yield, calculated as the percen… | cross-sec | monthly | derived; `delay_0=0`: timing review; do not auto-delay |
| `ebitda_per_diluted_share` | Earnings Before Interest, Taxes, Depreciation, and Amortization (EBITDA) calc… | cross-sec | quarterly | derived; corporate-action adjusted |
| `ebitda_to_revenue_pct` | the relationship between Earnings Before Interest, Taxes, Depreciation, and A… | cross-sec | quarterly | derived |
| `enterprise_value_to_market_cap_ratio` | the ratio of enterprise value (EV) to market capitalization (MKT CAP) as repo… | cross-sec | monthly | derived; `delay_0=0`: timing review; do not auto-delay; sparse coverage (392) |
| `ev_to_t12m_ebit` | the enterprise value (EV) as a multiple of the trailing twelve months (T12M)… | cross-sec | monthly | derived; `delay_0=0`: timing review; do not auto-delay |
| `interest_income` | the Interest Income reported in a company's Form 8-K filings with the SEC. | cross-sec | quarterly | — |
| `net_interest_income` | the Net Interest Income as reported in a company's Form 8-K filings with the… | cross-sec | quarterly | sparse coverage (402) |
| `net_interest_income_after_provision` | the Net Interest Income after provisions as reported in a company's Form 8-K… | cross-sec | quarterly | sparse coverage (202) |
| `non_interest_income` | the Non-Interest Income reported in a company's Form 8-K filings with the SEC. | cross-sec | quarterly | sparse coverage (244) |
| `operating_income` | the Operating Income or Loss as reported in a company's Form 8-K filings with… | cross-sec | quarterly | — |
| `operating_income_per_share` | a firm's profitability by calculating Operating Income per Share, excluding n… | cross-sec | quarterly | derived; corporate-action adjusted |
| `price_to_ebitda` | the Price to EBITDA ratio, calculated by dividing the market price per share… | cross-sec | daily | derived |
| `t12m_diluted_eps_continuing_operations` | the Trailing Twelve Months (T12M) Diluted Earnings Per Share (EPS) from Conti… | cross-sec | quarterly | derived; corporate-action adjusted |
| `trailing_12_month_diluted_eps` | the trailing 12-month diluted Earnings Per Share (EPS) from continuing operat… | cross-sec | quarterly | derived; corporate-action adjusted |
