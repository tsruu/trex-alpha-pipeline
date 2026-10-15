# Fundamental — Expenses  (18 vars)

**Status:** Open — richest whitespace (only market cap is used by the 101, once).
**Notes:** Reporting-lag / lookahead risk — watch the fast-vs-slow gap; quarterly/annual variables behave as step-functions (low turnover); cross-sec, so rankable.

⬤ = used by the 101 alphas.

Caveats are emitted only when raw metadata changes how a field should be handled. `delay_0=0` requests a timing review; it never means to add `ts_delay` automatically.

| var | what it is | dim | freq | caveat |
|---|---|---|---|---|
| `amortization_of_intangible_assets` | the amortization expense related to intangible assets as reported in a compan… | cross-sec | quarterly | sparse coverage (361) |
| `cost_of_goods_sold_to_fixed_expenses_and_production_and_general` | the Cost of Goods Sold (COGS) as reported in a company's Form 8-K filings wit… | cross-sec | quarterly | — |
| `deferred_income_taxes` | the amount of Deferred Income Taxes as reported in a company's Form 8-K filin… | cross-sec | quarterly | — |
| `depreciation_amortization` | the total Depreciation and Amortization expenses as reported in the Income St… | cross-sec | quarterly | — |
| `depreciation_amortization` | the total amount of Depreciation and Amortization expenses reported in a comp… | cross-sec | quarterly | — |
| `general_and_admin_expense` | the General and Administrative Expenses as reported in a company's Form 8-K f… | cross-sec | quarterly | — |
| `income_tax_expense_year_growth_pct` | the percentage change in income tax expense from the previous year to the cur… | cross-sec | quarterly | derived |
| `income_tax_expenses` | the Income Tax Expenses (or Credits) as reported in a company's Form 8-K fili… | cross-sec | quarterly | — |
| `interest_expense` | the Interest Expense as reported in a company's Form 8-K filings with the SEC. | cross-sec | quarterly | — |
| `interest_expense_year_growth_pct` | the percentage change in interest expense from the previous year to the curre… | cross-sec | quarterly | derived |
| `net_interest_expense` | the Net Interest Expense as reported in a company's Form 8-K filings with the… | cross-sec | quarterly | — |
| `non_interest_expense` | the Non-Interest Expense as reported in a company's Form 8-K filings with the… | cross-sec | quarterly | sparse coverage (248) |
| `personnel_expenses` | the total personnel expenses reported in a company's Form 8-K filings with th… | cross-sec | quarterly | sparse coverage (302) |
| `research_and_development_expense` | the Research and Development (R&D) Expense as reported in a company's Form 8-… | cross-sec | quarterly | — |
| `sell_and_admin_exp_to_net_sales_ratio` | This ratio measures the efficiency of a company's management by comparing Sel… | cross-sec | quarterly | derived |
| `stock_based_compensation` | the total amount of stock-based compensation reported in a company's Form 8-K… | cross-sec | quarterly | — |
| `total_operating_expenses` | the total operating expenses as reported in a company's Form 8-K filings with… | cross-sec | quarterly | sparse coverage (298) |
| `total_operating_expenses` | the Total Operating Expenses as reported in a company's Form 8-K filings with… | cross-sec | quarterly | — |
