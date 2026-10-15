# Fundamental — Equity  (20 vars)

**Status:** Open — richest whitespace (only market cap is used by the 101, once).
**Notes:** Reporting-lag / lookahead risk — watch the fast-vs-slow gap; quarterly/annual variables behave as step-functions (low turnover); cross-sec, so rankable.

⬤ = used by the 101 alphas.

Caveats are emitted only when raw metadata changes how a field should be handled. `delay_0=0` requests a timing review; it never means to add `ts_delay` automatically.

| var | what it is | dim | freq | caveat |
|---|---|---|---|---|
| `accumulated_other_comprehensive_income` | the Accumulated Other Comprehensive Income (AOCI) as reported in a company's… | cross-sec | quarterly | — |
| `additional_paid_in_capital` | the Additional Paid-in Capital (APIC) as reported in a company's Form 8-K fil… | cross-sec | quarterly | — |
| `ann_return_on_equity` | the annual return on equity (ROE) expressed as a percentage, assessing a comp… | cross-sec | quarterly | derived |
| `asset_to_equity_ratio` | the ratio of total assets to shareholders' equity, calculated by dividing tot… | cross-sec | quarterly | derived |
| `common_stocks` | the total value of common stocks as reported in a company's Form 8-K filings… | cross-sec | annual | — |
| `minority_non_controlling_interest` | the value of Minority or Non-Controlling Interest as reported in a company's… | cross-sec | annual | sparse coverage (475) |
| `minority_non_controlling_interests_credits` | the credits associated with Minority or Non-Controlling Interests as reported… | cross-sec | annual | sparse coverage (423) |
| `normalized_roe` | the normalized Return on Equity (ROE), calculated using the formula: (Trailin… | cross-sec | monthly | derived |
| `price_to_book_ratio` | the Price to Book Ratio, which is the ratio of the stock price to the book va… | cross-sec | daily | derived; sparse coverage (54) |
| `price_to_tangible_book_value_per_share` | the Price to Net Tangible Assets per Share ratio, which compares the stock pr… | cross-sec | daily | derived |
| `pure_retained_earnings` | the Pure Retained Earnings as reported in a company's Form 8-K filings with t… | cross-sec | quarterly | — |
| `reinvested_earnings` | the amount of net income (or loss) available for reinvestment after deducting… | cross-sec | quarterly | derived |
| `retained_earnings_and_other_equity` | the total amount of retained earnings and other equity components as reported… | cross-sec | quarterly | — |
| `retained_earnings_to_total_liabilities_and_equity` | the ratio of retained earnings and other equity to total liabilities and equi… | cross-sec | quarterly | derived |
| `return_on_equity` | a corporation's profitability by indicating how much profit a company generat… | cross-sec | quarterly | derived |
| `tangible_equity` | the Tangible Equity as reported in a company's Form 8-K filings with the SEC. | cross-sec | annual | sparse coverage (8) |
| `total_equity_partnership_capital` | the Total Equity or Partnership Capital as reported in a company's Form 8-K f… | cross-sec | quarterly | sparse coverage (471) |
| `total_liabilities_and_equity` | the total liabilities and equity as reported in a company's Form 8-K filings… | cross-sec | quarterly | — |
| `total_shareholders_equity` | the Total Shareholders' Equity as reported in a company's Form 8-K filings wi… | cross-sec | quarterly | — |
| `treasury_stock_amount` | the amount of Treasury Stock reported in a company's Form 8-K filings with th… | cross-sec | annual | sparse coverage (315) |
