# Fundamental — Year  (7 vars)

**Status:** Open — richest whitespace (only market cap is used by the 101, once).
**Notes:** Reporting-lag / lookahead risk — watch the fast-vs-slow gap; quarterly/annual variables behave as step-functions (low turnover); cross-sec, so rankable.

⬤ = used by the 101 alphas.

Caveats are emitted only when raw metadata changes how a field should be handled. `delay_0=0` requests a timing review; it never means to add `ts_delay` automatically.

| var | what it is | dim | freq | caveat |
|---|---|---|---|---|
| `accounts_receivable_growth_pct` | the percentage change in Accounts Receivable from the previous year to the cu… | cross-sec | quarterly | derived; sparse coverage (268) |
| `cash_flow_growth` | Cash Flow Growth is calculated as the percentage change in Cash Flow from Ope… | cross-sec | quarterly | derived |
| `ebit_year_over_year_growth` | the percentage change in Earnings Before Interest and Taxes (EBIT) from the p… | cross-sec | quarterly | derived |
| `ebitda_growth_pct` | the percentage change in Earnings Before Interest, Taxes, Depreciation, and A… | cross-sec | quarterly | derived |
| `eps_growth` | the percentage change in Earnings Per Share (EPS) before extraordinary items,… | cross-sec | quarterly | derived |
| `operating_income_growth` | the percentage change in operating income, calculated by comparing the curren… | cross-sec | quarterly | derived |
| `pretax_income_year_growth_pct` | the percentage change in pre-tax income from the previous year to the current… | cross-sec | quarterly | derived |
