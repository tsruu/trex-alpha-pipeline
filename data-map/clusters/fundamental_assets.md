# Fundamental — Assets  (25 vars)

**Status:** Open — richest whitespace (only market cap is used by the 101, once).
**Notes:** Reporting-lag / lookahead risk — watch the fast-vs-slow gap; quarterly/annual variables behave as step-functions (low turnover); cross-sec, so rankable.

⬤ = used by the 101 alphas.

Caveats are emitted only when raw metadata changes how a field should be handled. `delay_0=0` requests a timing review; it never means to add `ts_delay` automatically.

| var | what it is | dim | freq | caveat |
|---|---|---|---|---|
| `accounts_notes_receivable` | the total value of Accounts and Notes Receivable as reported in a company's F… | cross-sec | annual | sparse coverage (298) |
| `accounts_receivable_excluding_notes` | the total Accounts Receivable for a company as reported in its Form 8-K filin… | cross-sec | quarterly | — |
| `accumulated_depreciation` | the accumulated depreciation as reported in a company's Form 8-K filings with… | cross-sec | annual | sparse coverage (113) |
| `change_in_inventories` | the change in inventories as reported in a company's Form 8-K filings with th… | cross-sec | quarterly | sparse coverage (399) |
| `current_assets_report` | the total current assets reported by a company in its Form 8-K filings with t… | cross-sec | quarterly | — |
| `current_assets_to_total_assets_ratio` | This ratio measures the percentage of total current assets relative to total… | cross-sec | quarterly | derived |
| `deferred_tax_assets_long_term` | the long-term Deferred Tax Assets as reported in a company's Form 8-K filings… | cross-sec | annual | sparse coverage (145) |
| `goodwill` | the amount of Goodwill reported in a company's balance sheet as disclosed in… | cross-sec | annual | — |
| `intangible_and_other_assets` | the value of Intangible and Other Assets as reported in a company's Balance S… | cross-sec | quarterly | — |
| `inventories` | the total inventories reported in a company's Form 8-K filings with the SEC. | cross-sec | quarterly | — |
| `inventories_to_working_capital_pct` | the percentage of inventories relative to working capital, indicating the pro… | cross-sec | quarterly | derived |
| `inventory_growth_pct_change` | the percentage change in inventory levels from the previous year to the curre… | cross-sec | quarterly | derived |
| `inventory_to_current_assets_pct` | the percentage of inventories relative to total current assets, indicating th… | cross-sec | quarterly | derived |
| `inventory_to_current_assets_ratio` | the percentage of inventories relative to total current assets, providing ins… | cross-sec | quarterly | derived |
| `inventory_to_total_assets_ratio` | the ratio of inventories to total assets, measuring the percentage of a compa… | cross-sec | quarterly | derived |
| `non_cash_working_capital` | the company's non-cash working capital, calculated as Current Assets minus Ca… | cross-sec | quarterly | derived |
| `other_assets` | the total value of other assets as reported in a company's Form 8-K filings w… | cross-sec | quarterly | — |
| `other_assets_turnover_ratio` | The Other Assets Turnover Ratio measures the efficiency with which a company… | cross-sec | quarterly | derived |
| `other_current_assets` | the value of Other Current Assets as reported in a company's Form 8-K filings… | cross-sec | quarterly | — |
| `quick_ratio` | the Quick Ratio, a financial metric that indicates a company's ability to mee… | cross-sec | quarterly | derived |
| `return_on_assets` | the Return on Assets (ROA), indicating how profitable a company is relative t… | cross-sec | quarterly | derived |
| `roa_based_on_bottom_eps` | the Return on Assets (ROA) calculated based on the bottom-line Earnings Per S… | cross-sec | quarterly | derived |
| `total_assets` | the Total Assets as reported in a company's Form 8-K filings with the SEC. | cross-sec | quarterly | — |
| `total_other_property_and_equipment` | the total value of Other Property and Equipment as reported in a company's Fo… | cross-sec | quarterly | — |
| `working_capital_changes` | the changes in Working Capital as reported in a company's Form 8-K filings wi… | cross-sec | annual | sparse coverage (24) |
