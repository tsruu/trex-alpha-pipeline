# Fundamental — Debt  (28 vars)

**Status:** Open — richest whitespace (only market cap is used by the 101, once).
**Notes:** Reporting-lag / lookahead risk — watch the fast-vs-slow gap; quarterly/annual variables behave as step-functions (low turnover); cross-sec, so rankable.

⬤ = used by the 101 alphas.

Caveats are emitted only when raw metadata changes how a field should be handled. `delay_0=0` requests a timing review; it never means to add `ts_delay` automatically.

| var | what it is | dim | freq | caveat |
|---|---|---|---|---|
| `accounts_payable` | the total amount of Accounts Payable as reported in a company's Form 8-K fili… | cross-sec | quarterly | — |
| `accounts_payable_and_accruals` | the total amount of Accounts Payable and Accruals as reported in a company's… | cross-sec | quarterly | — |
| `cash_and_equivalents_to_total_liabilities_pct` | the ratio of cash and cash equivalents to total liabilities, expressed as a p… | cross-sec | quarterly | derived |
| `cash_flow_to_interest_expense_ratio` | the ratio of cash flow from operations to total interest expenses incurred du… | cross-sec | quarterly | derived |
| `cash_flow_to_total_liabilities` | the ratio of cash flow to total liabilities, indicating the company's ability… | cross-sec | quarterly | derived |
| `current_liabilities` | the Current Liabilities as reported in a company's Form 8-K filings with the… | cross-sec | quarterly | — |
| `current_portion_of_long_term_debt` | the current portion of long-term debt as reported in a company's Form 8-K fil… | cross-sec | annual | sparse coverage (384) |
| `debt_to_market_cap` | the ratio of a company's total debt to its market capitalization, providing a… | cross-sec | daily | derived |
| `deferred_tax_liabilities` | the Deferred Tax Liabilities as reported in a company's Form 8-K filings with… | cross-sec | quarterly | — |
| `long_term_borrowings` | the total amount of long-term borrowings reported in a company's Form 8-K fil… | cross-sec | quarterly | — |
| `long_term_debt` | the Long Term Debt as reported in a company's Form 8-K filings with the SEC. | cross-sec | quarterly | — |
| `net_change_long_term_debt` | the year-on-year change in Long Term Debt as reported in a company’s Form 8-K… | cross-sec | quarterly | derived |
| `net_debt` | the net debt of a company as reported in its Form 8-K filings with the SEC. | cross-sec | quarterly | derived |
| `net_debt_to_ebitda` | a company's ability to pay off its net debt using its earnings before interes… | cross-sec | quarterly | derived |
| `net_debt_to_ebitda_after_capex` | This leverage ratio indicates a company's ability to pay off its net debt usi… | cross-sec | quarterly | derived |
| `net_debt_to_shareholders_equity` | the ratio of net debt to shareholders' equity, providing insight into a compa… | cross-sec | quarterly | derived |
| `non_current_liabilities` | the total amount of non-current liabilities as reported in a company's Form 8… | cross-sec | quarterly | sparse coverage (220) |
| `operating_income_to_current_liabilities` | the ratio of Operating Income to Current Liabilities, providing insight into… | cross-sec | quarterly | derived |
| `operating_income_to_long_term_debt` | the ratio of Operating Income to Long Term Debt, providing insight into a com… | cross-sec | quarterly | derived |
| `operating_income_to_total_debt` | the ratio of Operating Income to Total Debt, calculated as Operating Income d… | cross-sec | quarterly | derived |
| `other_long_term_liabilities` | the total amount of Other Long Term Liabilities reported in a company's Form… | cross-sec | quarterly | — |
| `other_short_term_liabilities` | the total amount of other short-term liabilities reported in a company's Form… | cross-sec | quarterly | — |
| `short_term_borrowings` | the total amount of short-term borrowings reported in a company's Form 8-K fi… | cross-sec | annual | sparse coverage (276) |
| `times_interest_earned_ratio` | the Times Interest Earned (TIE) ratio, also known as the Interest Coverage Ra… | cross-sec | quarterly | derived |
| `total_debt` | the total debt of a company, calculated as the sum of both short-term and lon… | cross-sec | quarterly | derived |
| `total_debt_to_enterprise_value` | the ratio of Total Debt to Enterprise Value (EV) as reported in a company's F… | cross-sec | daily | derived; sparse coverage (406) |
| `total_deposits` | the total deposits reported by a company in its Form 8-K filings with the SEC. | cross-sec | quarterly | sparse coverage (204) |
| `total_liabilities` | the total liabilities as reported in a company's Form 8-K filings with the SE… | cross-sec | quarterly | — |
