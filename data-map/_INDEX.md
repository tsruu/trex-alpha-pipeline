# Alpha Data Catalog — 255 variables

_The full lookup for the research agent. Keep this file in context; open clusters/<file>.md for the cluster you're working in._

## How to use this
- Work in one cluster/subcluster at a time. Generate the core of each alpha from its variables (open the relevant cluster file for depth).
- You may pull one term from another cluster for a conditioner, neutralizer, or interaction; keep the main signal in your assigned cluster.
- A strong novel move is crossing two distant clusters in one formula, such as a price/volume reversal gated by a seasonality flag.
- `dim` = `cross-sec` (varies per stock and is rankable) or `market-wide` (one series that must be interacted). `freq` is the update cadence.
- Cluster files add a `caveat` column for actionable metadata such as timing, derivation, sparse coverage, missing-value encoding, adjustments, and forward-fill.
- ⬤ marks variables used by the 101 alphas; treat them as picked-over.

## Clusters at a glance
| file | vars | status |
|---|---:|---|
| `clusters/price_volume.md` | 16 | EXPLORED — all 101 alphas live here. |
| `clusters/intraday.md` | 30 | Open — 101 never use intraday timing. |
| `clusters/fundamental_cash.md` | 30 | Open — richest whitespace (only market cap is used by the 101, once). |
| `clusters/fundamental_earnings.md` | 18 | Open — richest whitespace (only market cap is used by the 101, once). |
| `clusters/fundamental_net_income.md` | 15 | Open — richest whitespace (only market cap is used by the 101, once). |
| `clusters/fundamental_expenses.md` | 18 | Open — richest whitespace (only market cap is used by the 101, once). |
| `clusters/fundamental_sales.md` | 14 | Open — richest whitespace (only market cap is used by the 101, once). |
| `clusters/fundamental_equity.md` | 20 | Open — richest whitespace (only market cap is used by the 101, once). |
| `clusters/fundamental_debt.md` | 28 | Open — richest whitespace (only market cap is used by the 101, once). |
| `clusters/fundamental_assets.md` | 25 | Open — richest whitespace (only market cap is used by the 101, once). |
| `clusters/fundamental_year.md` | 7 | Open — richest whitespace (only market cap is used by the 101, once). |
| `clusters/seasonality.md` | 18 | Open. |
| `clusters/macro.md` | 16 | Open — all market-wide (must interact). |

## Price / Volume  (16)

| var | what it is | dim | freq |
|---|---|---|---|
| `cashdvd` | the amount of cash dividend distributed to shareholders. | cross-sec | annual |
| `close` ⬤ | the adjusted closing price of stocks, which accounts for corporate actions su… | cross-sec | daily |
| `high` ⬤ | the adjusted high price of stocks, reflecting the highest price reached durin… | cross-sec | daily |
| `industry` ⬤ | an integer representation of industries, encompassing approximately 70 distin… | cross-sec | annual |
| `low` ⬤ | the adjusted low price of stocks, accounting for factors such as stock splits… | cross-sec | daily |
| `mktcap` ⬤ | the market capitalization of stocks, calculated by multiplying the stock's cu… | cross-sec | daily |
| `open` ⬤ | the adjusted opening price of stocks, reflecting the price at which a stock b… | cross-sec | daily |
| `ret1` ⬤ | the 1-day return of a stock, calculated as the percentage change from the pre… | cross-sec | daily |
| `ret10` ⬤ | the 10-day return, calculated as the percentage change in the stock's closing… | cross-sec | daily |
| `ret20` ⬤ | the 20-day return, calculated as the percentage change in the stock's closing… | cross-sec | daily |
| `ret5` ⬤ | the 5-day return of a stock, calculated as the percentage change between toda… | cross-sec | daily |
| `sector` ⬤ | the integer representation of sectors as classified, encompassing approximate… | cross-sec | annual |
| `shsfloat` | the number of floating shares available for trading, expressed in millions. | cross-sec | monthly |
| `shsout` | the total number of outstanding shares of a company, expressed in millions. | cross-sec | quarterly |
| `subindustry` ⬤ | an integer representation of subindustries, categorizing companies into appro… | cross-sec | annual |
| `volume` ⬤ | the total composite trading volume, which includes all trading activity durin… | cross-sec | daily |

## Intraday  (30)

| var | what it is | dim | freq |
|---|---|---|---|
| `close_price_first_hour` | The last trade price recorded after the first hour of trading in the morning… | cross-sec | daily |
| `close_price_last_hour` | the last trade price of an asset during the afternoon trading session, provid… | cross-sec | daily |
| `high_price_first_hour` | the highest price reached during the first hour of trading in the morning ses… | cross-sec | daily |
| `high_price_last_hour` | The highest price of the asset during the afternoon trading session. | cross-sec | daily |
| `information_ratio_first_hour` | Return information ratio during the first hour of trading. | cross-sec | daily |
| `information_ratio_last_hour` | Return information ratio during the last hour of trading. | cross-sec | daily |
| `low_price_first_hour` | the lowest price recorded during the first hour of trading, providing insight… | cross-sec | daily |
| `low_price_last_hour` | the lowest price recorded during the last hour of trading, providing insight… | cross-sec | daily |
| `number_of_trades_first_hour` | the total number of trades executed during the first hour of trading in the m… | cross-sec | daily |
| `number_of_trades_last_hour` | the total number of trades executed during the last hour of the trading sessi… | cross-sec | daily |
| `open_price_first_hour` | The opening price of the asset during the first hour of trading. | cross-sec | daily |
| `open_price_last_hour` | The opening price of the asset during the last hour of trading. | cross-sec | daily |
| `return_first_hour` | the return generated during the first hour of trading, capturing the performa… | cross-sec | daily |
| `return_last_hour` | the return generated during the last hour of trading, capturing the asset's p… | cross-sec | daily |
| `skew_close_first_hour` | the skewness of asset prices during the first hour of trading, indicating the… | cross-sec | daily |
| `skew_close_last_hour` | the skewness of asset prices during the last hour of trading, indicating the… | cross-sec | daily |
| `skew_return_first_hour` | the skewness of returns during the first hour of trading, indicating the asym… | cross-sec | daily |
| `skew_return_last_hour` | the skewness of returns during the last hour of trading, indicating the asymm… | cross-sec | daily |
| `skew_volume_first_hour` | This metric represents the skewness of trading volume during the first hour o… | cross-sec | daily |
| `skew_volume_last_hour` | This metric represents the skewness of trading volume during the last hour of… | cross-sec | daily |
| `std_close_first_hour` | This metric represents the standard deviation of closing prices during the fi… | cross-sec | daily |
| `std_close_last_hour` | This metric represents the standard deviation of closing prices during the la… | cross-sec | daily |
| `std_dev_return_first_hour` | This metric represents the standard deviation of returns during the first hou… | cross-sec | daily |
| `std_dev_return_last_hour` | This metric represents the standard deviation of returns during the last hour… | cross-sec | daily |
| `std_volume_first_hour` | This metric represents the standard deviation of trading volume during the fi… | cross-sec | daily |
| `std_volume_last_hour` | This metric represents the standard deviation of trading volume during the la… | cross-sec | daily |
| `volume_first_hour` | Total trading volume during the first hour of the trading session. | cross-sec | daily |
| `volume_last_hour` | Total trading volume during the last hour of the trading session. | cross-sec | daily |
| `vwap_first_hour` | The Volume-Weighted Average Price (VWAP) calculated during the first trading… | cross-sec | daily |
| `vwap_last_hour` | The Volume-Weighted Average Price (VWAP) calculated during the last hour of t… | cross-sec | daily |

## Fundamental — Cash  (30)

| var | what it is | dim | freq |
|---|---|---|---|
| `balance_sheet_cash_near_cash_items` | the total amount of cash and near cash items reported in a company's balance… | cross-sec | quarterly |
| `capital_expenditures_property_additions` | the capital expenditures related to property additions as reported in a compa… | cross-sec | quarterly |
| `cash_and_investments_to_current_assets_pct` | the percentage of cash and near cash items, along with marketable securities,… | cross-sec | quarterly |
| `cash_and_marketable_securities_per_share` | the amount of cash and marketable securities available per share, as reported… | cross-sec | monthly |
| `cash_and_short_term_investments` | cash and liquid securities that can be quickly converted into cash at a reaso… | cross-sec | quarterly |
| `cash_flow_net_income` | the Cash Flow from Net Income as reported in a company's Form 8-K filings wit… | cross-sec | quarterly |
| `cash_flow_per_share` | a firm's financial strength by representing the net cash generated by the fir… | cross-sec | quarterly |
| `cash_from_financing_activities` | the cash flow generated from financing activities as reported in a company's… | cross-sec | quarterly |
| `cash_from_investing_activities` | the cash flow generated or used in investing activities as reported in a comp… | cross-sec | quarterly |
| `cash_from_operations` | the Cash From Operations as reported in a company's Form 8-K filings with the… | cross-sec | quarterly |
| `cash_from_operations_to_total_debt` | the ratio of Trailing 12-month Cash From Operations to the total of Short- an… | cross-sec | quarterly |
| `cash_generation_to_cash_requirements_ratio` | This ratio measures the cash generated from operations relative to the cash p… | cross-sec | quarterly |
| `cash_ratio` | The Cash Ratio is a liquidity metric calculated by dividing the sum of Cash a… | cross-sec | quarterly |
| `cash_to_total_assets_ratio` | the ratio of cash and near-cash assets to total assets, indicating the percen… | cross-sec | quarterly |
| `collaterals_cash_market_short_term_investments` | the value of collaterals held in cash and cash equivalents, including marketa… | cross-sec | annual |
| `dividend_per_share` | the Dividend Per Share (DPS) as reported in a company’s Form 8-K filings with… | cross-sec | annual |
| `dividends_paid` | the total amount of dividends paid by the company as reported in its Form 8-K… | cross-sec | quarterly |
| `effect_of_exchange_rate_changes_on_cash` | the impact of exchange rate fluctuations on cash and cash equivalents as repo… | cross-sec | quarterly |
| `ev_to_t12m_cash_flow` | the enterprise value (EV) as a multiple of the trailing twelve months (T12M)… | cross-sec | monthly |
| `ev_to_t12m_free_cash_flow` | the ratio of Enterprise Value (EV) to the Trailing 12 Months (T12M) Free Cash… | cross-sec | daily |
| `free_cash_flow` | financial performance by calculating Free Cash Flow, which is derived from op… | cross-sec | quarterly |
| `free_cash_flow_per_share` | a company's financial flexibility by calculating Free Cash Flow per Share. | cross-sec | quarterly |
| `free_cash_flow_to_total_debt_ttm` | the ratio of Free Cash Flow (FCF) to Total Debt, calculated as the trailing t… | cross-sec | monthly |
| `marketable_securities_and_other_short_term_investments` | the total value of marketable securities and other short-term investments as… | cross-sec | annual |
| `net_change_in_cash` | the net changes in cash as reported in a company's Form 8-K filings with the… | cross-sec | quarterly |
| `price_to_cash_flow_ratio` | The price to cash flow ratio is calculated by dividing a stock's price by its… | cross-sec | quarterly |
| `price_to_free_cash_flow` | the Price to Free Cash Flow ratio, calculated by dividing the period-end stoc… | cross-sec | daily |
| `short_term_investments` | the value of short-term investments as reported in a company's Form 8-K filin… | cross-sec | annual |
| `trailing_12_month_cash_flow_per_share` | the Trailing Twelve Months (TTM) Cash Flow per Share, calculated by summing t… | cross-sec | monthly |
| `trailing_12_months_cash_from_operations` | the Trailing Twelve Months (TTM) Cash From Operations, calculated by summing… | cross-sec | monthly |

## Fundamental — Earnings  (18)

| var | what it is | dim | freq |
|---|---|---|---|
| `average_number_of_shares_for_eps` | the average number of shares outstanding used in the calculation of Earnings… | cross-sec | quarterly |
| `basic_eps` | the Basic Earnings Per Share (EPS) as reported in a company's Form 8-K filing… | cross-sec | quarterly |
| `diluted_eps` | the Diluted Earnings Per Share (EPS) as reported in a company's Form 8-K fili… | cross-sec | quarterly |
| `diluted_weighted_average_shares` | the Diluted Weighted Average Shares outstanding, which accounts for all poten… | cross-sec | quarterly |
| `ebit_yield` | the Earnings Before Interest and Taxes (EBIT) yield, calculated as the percen… | cross-sec | monthly |
| `ebitda_per_diluted_share` | Earnings Before Interest, Taxes, Depreciation, and Amortization (EBITDA) calc… | cross-sec | quarterly |
| `ebitda_to_revenue_pct` | the relationship between Earnings Before Interest, Taxes, Depreciation, and A… | cross-sec | quarterly |
| `enterprise_value_to_market_cap_ratio` | the ratio of enterprise value (EV) to market capitalization (MKT CAP) as repo… | cross-sec | monthly |
| `ev_to_t12m_ebit` | the enterprise value (EV) as a multiple of the trailing twelve months (T12M)… | cross-sec | monthly |
| `interest_income` | the Interest Income reported in a company's Form 8-K filings with the SEC. | cross-sec | quarterly |
| `net_interest_income` | the Net Interest Income as reported in a company's Form 8-K filings with the… | cross-sec | quarterly |
| `net_interest_income_after_provision` | the Net Interest Income after provisions as reported in a company's Form 8-K… | cross-sec | quarterly |
| `non_interest_income` | the Non-Interest Income reported in a company's Form 8-K filings with the SEC. | cross-sec | quarterly |
| `operating_income` | the Operating Income or Loss as reported in a company's Form 8-K filings with… | cross-sec | quarterly |
| `operating_income_per_share` | a firm's profitability by calculating Operating Income per Share, excluding n… | cross-sec | quarterly |
| `price_to_ebitda` | the Price to EBITDA ratio, calculated by dividing the market price per share… | cross-sec | daily |
| `t12m_diluted_eps_continuing_operations` | the Trailing Twelve Months (T12M) Diluted Earnings Per Share (EPS) from Conti… | cross-sec | quarterly |
| `trailing_12_month_diluted_eps` | the trailing 12-month diluted Earnings Per Share (EPS) from continuing operat… | cross-sec | quarterly |

## Fundamental — Net Income  (15)

| var | what it is | dim | freq |
|---|---|---|---|
| `adjusted_net_income_as_reported` | the Adjusted Net Income as reported in a company's Form 8-K filings with the… | cross-sec | annual |
| `cash_flow_to_net_income_ratio` | the Cash Flow to Net Income Ratio, indicating the proportion of a company's t… | cross-sec | quarterly |
| `earnings_yield` | the Earnings Yield, calculated as the reciprocal of the Price-to-Earnings (P/… | cross-sec | quarterly |
| `earnings_yield_history` | the company's earnings per share (EPS) expressed as a percentage of its curre… | cross-sec | quarterly |
| `ev_to_t12m_net_income` | the ratio of Enterprise Value (EV) to Trailing 12-Month (T12M) Net Income. | cross-sec | monthly |
| `high_price_to_earnings_ratio` | the Price-to-Earnings (P/E) ratio calculated as the stock's highest price div… | cross-sec | quarterly |
| `low_price_to_earnings_ratio` | the low price-to-earnings (P/E) ratio of a stock, calculated by dividing the… | cross-sec | quarterly |
| `net_income` | the Net Income or Net Profit (Loss) as reported in a company's Form 8-K filin… | cross-sec | quarterly |
| `net_income_before_minority_interest` | the Net Income Before Minority (Non-controlling) Interest as reported in a co… | cross-sec | quarterly |
| `net_income_growth_pct` | the percentage change in net income, calculated by comparing the current peri… | cross-sec | quarterly |
| `net_income_per_employee` | the ratio of net income to the number of employees, providing a measure of pr… | cross-sec | quarterly |
| `operating_profits_discontinued_operations` | the operating (trading) profits generated from discontinued operations as rep… | cross-sec | annual |
| `pre_tax_income` | the Pre-Tax Income as reported in a company's Form 8-K filings with the SEC. | cross-sec | quarterly |
| `pretax_income_per_share` | the ratio of pre-tax income calculated on a per-share basis, providing insigh… | cross-sec | quarterly |
| `profit_margin` | the company's profitability by comparing the amount of revenue retained as in… | cross-sec | quarterly |

## Fundamental — Expenses  (18)

| var | what it is | dim | freq |
|---|---|---|---|
| `amortization_of_intangible_assets` | the amortization expense related to intangible assets as reported in a compan… | cross-sec | quarterly |
| `cost_of_goods_sold_to_fixed_expenses_and_production_and_general` | the Cost of Goods Sold (COGS) as reported in a company's Form 8-K filings wit… | cross-sec | quarterly |
| `deferred_income_taxes` | the amount of Deferred Income Taxes as reported in a company's Form 8-K filin… | cross-sec | quarterly |
| `depreciation_amortization` | the total Depreciation and Amortization expenses as reported in the Income St… | cross-sec | quarterly |
| `depreciation_amortization` | the total amount of Depreciation and Amortization expenses reported in a comp… | cross-sec | quarterly |
| `general_and_admin_expense` | the General and Administrative Expenses as reported in a company's Form 8-K f… | cross-sec | quarterly |
| `income_tax_expense_year_growth_pct` | the percentage change in income tax expense from the previous year to the cur… | cross-sec | quarterly |
| `income_tax_expenses` | the Income Tax Expenses (or Credits) as reported in a company's Form 8-K fili… | cross-sec | quarterly |
| `interest_expense` | the Interest Expense as reported in a company's Form 8-K filings with the SEC. | cross-sec | quarterly |
| `interest_expense_year_growth_pct` | the percentage change in interest expense from the previous year to the curre… | cross-sec | quarterly |
| `net_interest_expense` | the Net Interest Expense as reported in a company's Form 8-K filings with the… | cross-sec | quarterly |
| `non_interest_expense` | the Non-Interest Expense as reported in a company's Form 8-K filings with the… | cross-sec | quarterly |
| `personnel_expenses` | the total personnel expenses reported in a company's Form 8-K filings with th… | cross-sec | quarterly |
| `research_and_development_expense` | the Research and Development (R&D) Expense as reported in a company's Form 8-… | cross-sec | quarterly |
| `sell_and_admin_exp_to_net_sales_ratio` | This ratio measures the efficiency of a company's management by comparing Sel… | cross-sec | quarterly |
| `stock_based_compensation` | the total amount of stock-based compensation reported in a company's Form 8-K… | cross-sec | quarterly |
| `total_operating_expenses` | the total operating expenses as reported in a company's Form 8-K filings with… | cross-sec | quarterly |
| `total_operating_expenses` | the Total Operating Expenses as reported in a company's Form 8-K filings with… | cross-sec | quarterly |

## Fundamental — Sales  (14)

| var | what it is | dim | freq |
|---|---|---|---|
| `cash_from_operations_to_sales_pct` | the percentage of Cash Flow from Operations relative to Sales, indicating the… | cross-sec | quarterly |
| `ebit_margin` | the EBIT (Earnings Before Interest and Taxes) margin, a key profitability met… | cross-sec | monthly |
| `ebit_to_net_sales_ratio` | the EBIT (Earnings Before Interest and Taxes) margin of the company, calculat… | cross-sec | quarterly |
| `ebitda_margin` | the percentage margin of trailing twelve-month Earnings Before Interest, Taxe… | cross-sec | monthly |
| `gross_profit` | the Gross Profit as reported in a company's Form 8-K filings with the SEC. | cross-sec | quarterly |
| `net_sales` | the Net Sales as reported in a company's Form 8-K filings with the SEC. | cross-sec | quarterly |
| `operating_margin` | the Operating Margin, a financial metric used to assess a company's pricing s… | cross-sec | quarterly |
| `pretax_margin` | a company's pretax margin, calculated as earnings before tax expressed as a p… | cross-sec | quarterly |
| `price_to_sales_ratio` | The Price to Sales (P/S) ratio is calculated by dividing a stock's last price… | cross-sec | quarterly |
| `sales_revenue_turnover` | the revenue generated by a company as reported in its Form 8-K filings with t… | cross-sec | quarterly |
| `sales_to_cash_ratio` | the cash and near-cash turnover ratio, which measures how effectively a compa… | cross-sec | quarterly |
| `sales_to_marketable_securities` | the ratio of a company's sales to its marketable securities, indicating how e… | cross-sec | quarterly |
| `sales_to_total_assets_ratio` | the ratio of a company's sales to its total assets, indicating how efficientl… | cross-sec | quarterly |
| `trailing_12_month_operating_margin_pct` | the Trailing 12-Month Operating Margin, calculated by dividing the Trailing 1… | cross-sec | monthly |

## Fundamental — Equity  (20)

| var | what it is | dim | freq |
|---|---|---|---|
| `accumulated_other_comprehensive_income` | the Accumulated Other Comprehensive Income (AOCI) as reported in a company's… | cross-sec | quarterly |
| `additional_paid_in_capital` | the Additional Paid-in Capital (APIC) as reported in a company's Form 8-K fil… | cross-sec | quarterly |
| `ann_return_on_equity` | the annual return on equity (ROE) expressed as a percentage, assessing a comp… | cross-sec | quarterly |
| `asset_to_equity_ratio` | the ratio of total assets to shareholders' equity, calculated by dividing tot… | cross-sec | quarterly |
| `common_stocks` | the total value of common stocks as reported in a company's Form 8-K filings… | cross-sec | annual |
| `minority_non_controlling_interest` | the value of Minority or Non-Controlling Interest as reported in a company's… | cross-sec | annual |
| `minority_non_controlling_interests_credits` | the credits associated with Minority or Non-Controlling Interests as reported… | cross-sec | annual |
| `normalized_roe` | the normalized Return on Equity (ROE), calculated using the formula: (Trailin… | cross-sec | monthly |
| `price_to_book_ratio` | the Price to Book Ratio, which is the ratio of the stock price to the book va… | cross-sec | daily |
| `price_to_tangible_book_value_per_share` | the Price to Net Tangible Assets per Share ratio, which compares the stock pr… | cross-sec | daily |
| `pure_retained_earnings` | the Pure Retained Earnings as reported in a company's Form 8-K filings with t… | cross-sec | quarterly |
| `reinvested_earnings` | the amount of net income (or loss) available for reinvestment after deducting… | cross-sec | quarterly |
| `retained_earnings_and_other_equity` | the total amount of retained earnings and other equity components as reported… | cross-sec | quarterly |
| `retained_earnings_to_total_liabilities_and_equity` | the ratio of retained earnings and other equity to total liabilities and equi… | cross-sec | quarterly |
| `return_on_equity` | a corporation's profitability by indicating how much profit a company generat… | cross-sec | quarterly |
| `tangible_equity` | the Tangible Equity as reported in a company's Form 8-K filings with the SEC. | cross-sec | annual |
| `total_equity_partnership_capital` | the Total Equity or Partnership Capital as reported in a company's Form 8-K f… | cross-sec | quarterly |
| `total_liabilities_and_equity` | the total liabilities and equity as reported in a company's Form 8-K filings… | cross-sec | quarterly |
| `total_shareholders_equity` | the Total Shareholders' Equity as reported in a company's Form 8-K filings wi… | cross-sec | quarterly |
| `treasury_stock_amount` | the amount of Treasury Stock reported in a company's Form 8-K filings with th… | cross-sec | annual |

## Fundamental — Debt  (28)

| var | what it is | dim | freq |
|---|---|---|---|
| `accounts_payable` | the total amount of Accounts Payable as reported in a company's Form 8-K fili… | cross-sec | quarterly |
| `accounts_payable_and_accruals` | the total amount of Accounts Payable and Accruals as reported in a company's… | cross-sec | quarterly |
| `cash_and_equivalents_to_total_liabilities_pct` | the ratio of cash and cash equivalents to total liabilities, expressed as a p… | cross-sec | quarterly |
| `cash_flow_to_interest_expense_ratio` | the ratio of cash flow from operations to total interest expenses incurred du… | cross-sec | quarterly |
| `cash_flow_to_total_liabilities` | the ratio of cash flow to total liabilities, indicating the company's ability… | cross-sec | quarterly |
| `current_liabilities` | the Current Liabilities as reported in a company's Form 8-K filings with the… | cross-sec | quarterly |
| `current_portion_of_long_term_debt` | the current portion of long-term debt as reported in a company's Form 8-K fil… | cross-sec | annual |
| `debt_to_market_cap` | the ratio of a company's total debt to its market capitalization, providing a… | cross-sec | daily |
| `deferred_tax_liabilities` | the Deferred Tax Liabilities as reported in a company's Form 8-K filings with… | cross-sec | quarterly |
| `long_term_borrowings` | the total amount of long-term borrowings reported in a company's Form 8-K fil… | cross-sec | quarterly |
| `long_term_debt` | the Long Term Debt as reported in a company's Form 8-K filings with the SEC. | cross-sec | quarterly |
| `net_change_long_term_debt` | the year-on-year change in Long Term Debt as reported in a company’s Form 8-K… | cross-sec | quarterly |
| `net_debt` | the net debt of a company as reported in its Form 8-K filings with the SEC. | cross-sec | quarterly |
| `net_debt_to_ebitda` | a company's ability to pay off its net debt using its earnings before interes… | cross-sec | quarterly |
| `net_debt_to_ebitda_after_capex` | This leverage ratio indicates a company's ability to pay off its net debt usi… | cross-sec | quarterly |
| `net_debt_to_shareholders_equity` | the ratio of net debt to shareholders' equity, providing insight into a compa… | cross-sec | quarterly |
| `non_current_liabilities` | the total amount of non-current liabilities as reported in a company's Form 8… | cross-sec | quarterly |
| `operating_income_to_current_liabilities` | the ratio of Operating Income to Current Liabilities, providing insight into… | cross-sec | quarterly |
| `operating_income_to_long_term_debt` | the ratio of Operating Income to Long Term Debt, providing insight into a com… | cross-sec | quarterly |
| `operating_income_to_total_debt` | the ratio of Operating Income to Total Debt, calculated as Operating Income d… | cross-sec | quarterly |
| `other_long_term_liabilities` | the total amount of Other Long Term Liabilities reported in a company's Form… | cross-sec | quarterly |
| `other_short_term_liabilities` | the total amount of other short-term liabilities reported in a company's Form… | cross-sec | quarterly |
| `short_term_borrowings` | the total amount of short-term borrowings reported in a company's Form 8-K fi… | cross-sec | annual |
| `times_interest_earned_ratio` | the Times Interest Earned (TIE) ratio, also known as the Interest Coverage Ra… | cross-sec | quarterly |
| `total_debt` | the total debt of a company, calculated as the sum of both short-term and lon… | cross-sec | quarterly |
| `total_debt_to_enterprise_value` | the ratio of Total Debt to Enterprise Value (EV) as reported in a company's F… | cross-sec | daily |
| `total_deposits` | the total deposits reported by a company in its Form 8-K filings with the SEC. | cross-sec | quarterly |
| `total_liabilities` | the total liabilities as reported in a company's Form 8-K filings with the SE… | cross-sec | quarterly |

## Fundamental — Assets  (25)

| var | what it is | dim | freq |
|---|---|---|---|
| `accounts_notes_receivable` | the total value of Accounts and Notes Receivable as reported in a company's F… | cross-sec | annual |
| `accounts_receivable_excluding_notes` | the total Accounts Receivable for a company as reported in its Form 8-K filin… | cross-sec | quarterly |
| `accumulated_depreciation` | the accumulated depreciation as reported in a company's Form 8-K filings with… | cross-sec | annual |
| `change_in_inventories` | the change in inventories as reported in a company's Form 8-K filings with th… | cross-sec | quarterly |
| `current_assets_report` | the total current assets reported by a company in its Form 8-K filings with t… | cross-sec | quarterly |
| `current_assets_to_total_assets_ratio` | This ratio measures the percentage of total current assets relative to total… | cross-sec | quarterly |
| `deferred_tax_assets_long_term` | the long-term Deferred Tax Assets as reported in a company's Form 8-K filings… | cross-sec | annual |
| `goodwill` | the amount of Goodwill reported in a company's balance sheet as disclosed in… | cross-sec | annual |
| `intangible_and_other_assets` | the value of Intangible and Other Assets as reported in a company's Balance S… | cross-sec | quarterly |
| `inventories` | the total inventories reported in a company's Form 8-K filings with the SEC. | cross-sec | quarterly |
| `inventories_to_working_capital_pct` | the percentage of inventories relative to working capital, indicating the pro… | cross-sec | quarterly |
| `inventory_growth_pct_change` | the percentage change in inventory levels from the previous year to the curre… | cross-sec | quarterly |
| `inventory_to_current_assets_pct` | the percentage of inventories relative to total current assets, indicating th… | cross-sec | quarterly |
| `inventory_to_current_assets_ratio` | the percentage of inventories relative to total current assets, providing ins… | cross-sec | quarterly |
| `inventory_to_total_assets_ratio` | the ratio of inventories to total assets, measuring the percentage of a compa… | cross-sec | quarterly |
| `non_cash_working_capital` | the company's non-cash working capital, calculated as Current Assets minus Ca… | cross-sec | quarterly |
| `other_assets` | the total value of other assets as reported in a company's Form 8-K filings w… | cross-sec | quarterly |
| `other_assets_turnover_ratio` | The Other Assets Turnover Ratio measures the efficiency with which a company… | cross-sec | quarterly |
| `other_current_assets` | the value of Other Current Assets as reported in a company's Form 8-K filings… | cross-sec | quarterly |
| `quick_ratio` | the Quick Ratio, a financial metric that indicates a company's ability to mee… | cross-sec | quarterly |
| `return_on_assets` | the Return on Assets (ROA), indicating how profitable a company is relative t… | cross-sec | quarterly |
| `roa_based_on_bottom_eps` | the Return on Assets (ROA) calculated based on the bottom-line Earnings Per S… | cross-sec | quarterly |
| `total_assets` | the Total Assets as reported in a company's Form 8-K filings with the SEC. | cross-sec | quarterly |
| `total_other_property_and_equipment` | the total value of Other Property and Equipment as reported in a company's Fo… | cross-sec | quarterly |
| `working_capital_changes` | the changes in Working Capital as reported in a company's Form 8-K filings wi… | cross-sec | annual |

## Fundamental — Year  (7)

| var | what it is | dim | freq |
|---|---|---|---|
| `accounts_receivable_growth_pct` | the percentage change in Accounts Receivable from the previous year to the cu… | cross-sec | quarterly |
| `cash_flow_growth` | Cash Flow Growth is calculated as the percentage change in Cash Flow from Ope… | cross-sec | quarterly |
| `ebit_year_over_year_growth` | the percentage change in Earnings Before Interest and Taxes (EBIT) from the p… | cross-sec | quarterly |
| `ebitda_growth_pct` | the percentage change in Earnings Before Interest, Taxes, Depreciation, and A… | cross-sec | quarterly |
| `eps_growth` | the percentage change in Earnings Per Share (EPS) before extraordinary items,… | cross-sec | quarterly |
| `operating_income_growth` | the percentage change in operating income, calculated by comparing the curren… | cross-sec | quarterly |
| `pretax_income_year_growth_pct` | the percentage change in pre-tax income from the previous year to the current… | cross-sec | quarterly |

## Seasonality  (18)

| var | what it is | dim | freq |
|---|---|---|---|
| `day_of_the_week` | a numeric representation of the days of the week, where 1 corresponds to Mond… | cross-sec | daily |
| `days_since_first_trading_day_of_month` | the number of trading days that have elapsed since the first trading day of t… | cross-sec | daily |
| `days_since_first_trading_day_of_quarter` | the number of trading days that have elapsed since the first trading day of t… | cross-sec | daily |
| `days_since_first_trading_day_of_year` | the number of trading days that have elapsed since the first trading day of t… | cross-sec | daily |
| `days_since_last_fomc_meeting` | the number of trading days that have elapsed since the last Federal Open Mark… | cross-sec | daily |
| `days_since_last_monthly_options_expiration` | the number of trading days that have elapsed since the last monthly options e… | cross-sec | daily |
| `days_since_last_quarterly_options_expiration` | the number of trading days that have elapsed since the last quarterly options… | cross-sec | daily |
| `days_since_last_trading_holiday` | the number of trading days that have elapsed since the last trading holiday. | cross-sec | daily |
| `days_until_last_trading_day_of_month` | the number of trading days remaining until the last trading day of the curren… | cross-sec | daily |
| `days_until_last_trading_day_of_quarter` | the number of trading days remaining until the last trading day of the curren… | cross-sec | daily |
| `days_until_last_trading_day_of_year` | the number of trading days remaining until the last trading day of the calend… | cross-sec | daily |
| `days_until_next_fomc_meeting` | the number of trading days remaining until the next Federal Open Market Commi… | cross-sec | daily |
| `days_until_next_monthly_options_expiration` | the number of trading days remaining until the next monthly options expiratio… | cross-sec | daily |
| `days_until_next_quarterly_options_expiration` | the number of trading days remaining until the next quarterly options expirat… | cross-sec | daily |
| `days_until_next_trading_holiday` | the number of trading days remaining until the next scheduled trading holiday… | cross-sec | daily |
| `month_of_the_year` | a numeric representation of the months of the year, where each month is assig… | cross-sec | monthly |
| `quarter_of_year` | a numeric representation of the quarter of the year, where 1 represents the f… | cross-sec | quarterly |
| `trading_days_until_next_earnings_announcement` | the number of trading days remaining until the next earnings announcement dat… | cross-sec | daily |

## Macro / Index  (16)

| var | what it is | dim | freq |
|---|---|---|---|
| `close_spx` | the closing price of the S&P 500 Index (SPX), which is an American stock mark… | market-wide | daily |
| `close_vix` | the closing price of the VIX, which is the ticker symbol for the Chicago Boar… | market-wide | daily |
| `cpi_all_urban_consumers` | the Consumer Price Index (CPI) for All Urban Consumers, covering all items an… | market-wide | daily |
| `cpi_all_urban_consumers_ex_food_energy` | the Consumer Price Index (CPI) for All Urban Consumers, excluding food and en… | market-wide | daily |
| `cpi_all_urban_consumers_purchasing_power` | the Consumer Price Index (CPI) for All Urban Consumers, indicating the purcha… | market-wide | daily |
| `cpi_total_all_items_us` | the Consumer Price Index (CPI) for all items in the United States, not season… | market-wide | daily |
| `gdp_implicit_price_deflator` | the Gross Domestic Product (GDP) implicit price deflator, which measures the… | market-wide | daily |
| `gdp_now_annualized_percent_change` | the GDPNow estimate, which indicates the seasonally adjusted annual rate of c… | market-wide | daily |
| `gdp_seasonally_adjusted_annual_rate` | the Gross Domestic Product (GDP) of the United States, expressed in billions… | market-wide | daily |
| `real_gdp_seasonally_adjusted_annual_rate` | the Real Gross Domestic Product (GDP) of the United States, adjusted for seas… | market-wide | daily |
| `ret1_gld` | the daily returns of the GLD ETF, which tracks the price of gold bullion. | market-wide | daily |
| `ret1_spx` | the 1-day return of the S&P 500 Index (SPX), calculated as the percentage cha… | market-wide | daily |
| `ret1_vix` | the 1-day return of the CBOE Volatility Index (VIX), which measures market ex… | market-wide | daily |
| `unemployment_level_seasonally_adjusted` | the seasonally adjusted unemployment level in the United States, measured in… | market-wide | daily |
| `unemployment_rate_20_years_and_over` | the seasonally adjusted unemployment rate for individuals aged 20 years and o… | market-wide | daily |
| `wti_spot_crude_oil_price` | the spot price of West Texas Intermediate (WTI) crude oil, measured in dollar… | market-wide | daily |
