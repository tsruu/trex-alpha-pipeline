# The 47 reference factors: what they are, where they come from, how good they are

Written 2026-10-11. The analysis compares the pool against "47 textbook factors". This file checks that claim: is each one a real published factor, and does our formula match the paper?

**Where the list came from.** An earlier agent wrote these signals during the competition analysis. Each has a one-line "hypothesis" comment in the repo naming its idea, often with the paper (for example "Novy-Marx gross profitability", "Amihud illiquidity premium", "Jegadeesh-Titman momentum"). So the list was not made up at random. But the citations had never been checked, and several formulas are simplified versions of the published ones.
- Definitions: `reference-price-factors.json` (12), `reference-ext-factors.json` (21 used, plus `ref-x-bab`, which failed to run), and 14 earlier `fund-probe-*` runs mapped in `s3_attribution.py`.
- PnLs: `data/ref-pnl/`.

**How this was checked.** A research sub-agent matched each signal to the literature and compared formulas. Six citations were confirmed by web search in that session; they are marked **[V]**. The rest are well-known papers cited from memory and marked **[M]**: they are standard references, but spot-check any you plan to quote.

## The short answer
- **47 entries, but only 40 distinct signals.** Seven appear twice, once in the original 14 fundamental probes and once in the extended set: book-to-market, earnings yield, gross profitability, ROA, asset growth, accruals and leverage.
- **15 entries (9 distinct signals) are standard textbook factors.** These are the Fama-French / q-factor / classic set: book-to-market, earnings yield, gross and operating profitability, ROA, accruals, asset growth, 12-1 momentum, size. Six of them appear twice.
- **21 entries (20 distinct) are recognised anomalies** with published support, though less standard than the core set: low volatility, MAX/lottery, illiquidity, weekly reversal, share issuance, R&D, seasonality, residual momentum, and others.
- **8 are project-specific or only weakly sourced.** These are mostly the intraday ones closest to our own alphas: close vs last-hour VWAP, last-hour volume share, last-hour / first-hour / overnight / intraday reversal, earnings yield vs own history, and 1-month return used with momentum's sign.
- **3 are platform vendor factors** (Barra value, momentum and beta). They are well known in industry, but their construction is opaque.

**So the honest phrasing is:** "I measured the pool against about 40 distinct reference signals. Most are published academic factors (Fama-French value and profitability, momentum, size, accruals, investment, low volatility and so on), and a few are intraday signals I added myself because they are close to what my alphas do."

## The table
Verdicts: **S** = standard textbook factor, **R** = recognised anomaly, **P** = project-specific or weakly sourced, **V** = platform vendor factor. IR = the factor's own daily IR in this simulator (for scale).

| # | Factor | What it does | Source | Verdict | Does our formula match the paper? |
|---|---|---|---|---|---|
| **Value** | | | | | |
| 1 | value_bm (also ref-x-value-bm) | Buy high book equity / market cap | Rosenberg-Reid-Lanstein 1985 (JPM) [M]; Fama-French 1992 (JF), 1993 (JFE) [M] | S | Close. Uses current market cap (the Asness-Frazzini 2013 "Devil in HML's Details" variant [M]); Fama-French use lagged December market equity. |
| 2 | earn_yield (also ref-x-value-ep) | Buy high earnings / price | Basu 1977 (JF), 1983 (JFE) [M] | S | Yes, if the platform's `earnings_yield` is trailing EPS / price. |
| 3 | fcf_yield | Buy high free cash flow / market cap | Lakonishok-Shleifer-Vishny 1994 (JF) [M] (cash flow / price) | R | Partly: the literature uses operating cash flow; free cash flow has no single canonical paper. |
| 4 | ref-x-value-cfp | Buy high operating cash flow / market cap | Lakonishok-Shleifer-Vishny 1994 [M] | R | Yes. |
| 5 | ey_vs_history | Earnings yield minus its own 1-year average | No clear academic source | P | Not a standard factor. If earnings move slowly, it mostly measures the stock's 1-year price change (closer to long-horizon reversal, De Bondt-Thaler 1985 [M]). |
| **Profitability / quality** | | | | | |
| 6 | gross_prof (also ref-x-prof-gpa) | Buy high gross profit / assets | Novy-Marx 2013 (JFE), "The Other Side of Value" [M] | S | Yes. |
| 7 | oper_prof | Buy high operating income / assets | Fama-French 2015 (JFE) [M]; Ball-Gerakos-Linnainmaa-Nikolaev 2015 (JFE) [M] | S | Variant: scaled by assets (Ball et al.), not book equity (Fama-French). |
| 8 | roa (also ref-x-prof-roa) | Buy high return on assets | Haugen-Baker 1996 (JFE) [M]; Hou-Xue-Zhang 2015 (RFS) [M] | S | Loose: the q-factor uses quarterly ROE timed to earnings announcements. |
| 9 | low_accruals (also ref-x-accruals) | Buy firms whose profits are backed by cash | Sloan 1996 (Accounting Review) [M]; Hribar-Collins 2002 (JAR) [M] | S | Cash-flow-statement version (a recognised variant); Sloan used balance-sheet accruals. |
| **Investment / financing** | | | | | |
| 10 | low_asset_growth (also ref-x-invest) | Buy firms whose assets grew least over a year | Cooper-Gulen-Schill 2008 (JF) [M]; Fama-French 2015 [M] | S | Yes. |
| 11 | low_issuance | Buy firms that issued fewest new shares | Pontiff-Woodgate 2008 (JF) [M]; Daniel-Titman 2006 (JF) [M] | R | Close. |
| 12 | low_debt (also ref-x-leverage) | Buy low debt / market cap | Bhandari 1988 (JF) [M]; Asness-Frazzini-Pedersen 2019 "Quality Minus Junk" [M] | R | **Direction is contested:** Bhandari found high leverage earns more; quality factors prefer low leverage. |
| 13 | rd_intensity | Buy high R&D / market cap | Chan-Lakonishok-Sougiannis 2001 (JF) [M] | R | Yes. |
| **Earnings** | | | | | |
| 14 | eps_surprise | Buy firms whose trailing EPS rose most over a quarter, scaled by price | Ball-Brown 1968 (JAR) [M]; Bernard-Thomas 1989 (JAR) [M] | R | **Proxy only:** not a real surprise vs analyst forecasts, and stale between reports. |
| 15 | ref-x-eps-growth | Buy high EPS growth | Chan-Jegadeesh-Lakonishok 1996 (JF) [M] | R | Unknown: the platform's `eps_growth` definition is not documented. |
| 16 | tax_growth | Buy firms whose income tax expense grew most | Thomas-Zhang 2011 (JAR), "Tax Expense Momentum" [M] | R | Partial: the paper scales the change by assets or price; a % growth rate is noisy. |
| **Momentum** | | | | | |
| 17 | ref-mom-12-1 | Buy past-year winners, skipping the last month | Jegadeesh-Titman 1993 (JF) [M]; Carhart 1997 (JF) [M] | S | Yes. |
| 18 | ref-mom-1m | Buy last month's winners | Jegadeesh 1990 (JF) [M] | P | **Opposite sign to the known effect** (single stocks *reverse* at one month). Used here as a control. |
| 19 | ref-x-resmom | Industry-adjusted 12-1 momentum | Blitz-Huij-Martens 2011 (J. Empirical Finance) [V] | R | Variant: the paper removes Fama-French factor exposure and scales by volatility; ours only removes the industry average. |
| 20 | ref-x-indmom | Buy stocks in the best-performing industries (6 months) | Moskowitz-Grinblatt 1999 (JF) [V] | R | **Unreliable here.** The simulator neutralises positions by industry, which mostly cancels an industry-level signal. Our run shows half the usual PnL volatility and IR -0.008. |
| 21 | ref-x-season | Buy stocks that did well in the same calendar month 1 and 2 years ago | Heston-Sadka 2008 (JFE) [V] | R | Close (they use up to 20 years of lags). |
| **Short-term reversal** | | | | | |
| 22 | ref-str-1d | Buy yesterday's losers | Lo-MacKinlay 1990 (RFS) [M]; Nagel 2012 (RFS) [M] | R | Concept matches; a 1-day version of the classic weekly/monthly reversal. |
| 23 | ref-str-5d | Buy last week's losers | Lehmann 1990 (QJE) [M]; Jegadeesh 1990 [M] | R | Yes. |
| 24 | ref-overnight-rev | Bet against last night's gap | Related: Lou-Polk-Skouras 2019 (JFE) [V]; Berkman et al. 2012 (JFQA) [M] | P | No paper tests this exact signal. |
| 25 | ref-intraday-rev | Bet against today's open-to-close move | Related: Lou-Polk-Skouras 2019 [V] | P | Same. |
| 26 | ref-lasthour-rev | Bet against today's last-hour move | Related: Heston-Korajczyk-Sadka 2010 (JF) [M]; Baltussen-Da-Soebhag "End-of-day reversal" (working paper) [V] | P | Weak: the related work is about patterns within the day, not next-day reversal. |
| 27 | ref-firsthour-rev | Bet against today's first-hour move | Related: Gao-Han-Li-Zhou 2018 (JFE) [M] (index level) | P | No direct source; used as a control. |
| 28 | ref-x-close-vwap | Bet against the close's gap from the last-hour average price | Related by analogy: Hendershott-Menkveld 2014 (JFE), "Price Pressures" [M] | P | No paper tests this exact signal. **This is the reference our biggest family resembles**, so "close vs VWAP" is our own construction, not a textbook factor. |
| 29 | ref-x-overnight-mom | Buy stocks with high average overnight returns over a month | Lou-Polk-Skouras 2019 [V]; Bogousslavsky 2021 (JFE) [V] | R | Direction matches; their window is longer. |
| **Risk / size / liquidity** | | | | | |
| 30 | ref-size | Buy small companies | Banz 1981 (JFE) [M]; Fama-French 1992 [M] | S | Yes (within the top 1000 only, so a narrow size range). |
| 31 | ref-lowvol | Buy low-volatility stocks | Ang-Hodrick-Xing-Zhang 2006 (JF) [M]; Baker-Bradley-Wurgler 2011 (FAJ) [M] | R | Yes. |
| 32 | ref-x-idiovol | Buy low idiosyncratic volatility | Ang-Hodrick-Xing-Zhang 2006 [M] | R | Variant: market-adjusted instead of factor-model residuals. |
| 33 | ref-x-max | Avoid stocks with the biggest one-day jump last month ("lottery") | Bali-Cakici-Whitelaw 2011 (JFE) [M] | R | Yes. |
| 34 | ref-illiquidity | Buy illiquid stocks (big price moves per dollar traded) | Amihud 2002 (J. Financial Markets) [M] | R | Close (1-month window instead of up to a year). |
| 35 | ref-low-turnover | Buy low share turnover | Datar-Naik-Radcliffe 1998 (J. Financial Markets) [M] | R | Yes. |
| **Volume** | | | | | |
| 36 | ref-x-volshock | Buy unusual-volume stocks | Gervais-Kaniel-Mingelgrin 2001 (JF), "The High-Volume Return Premium" [M] | R | Close. |
| 37 | ref-x-lh-volshare | Buy stocks with a high share of volume in the last hour | Related: Heston-Korajczyk-Sadka 2010 [M] | P | No paper tests this exact signal. |
| **Platform** | | | | | |
| 38-40 | barra_value, barra_momentum, -barra_beta | Vendor style factors | MSCI Barra style models | V | Industry-standard but opaque. |
| (not used) | ref-x-bab | Buy low-beta stocks | Frazzini-Pedersen 2014 (JFE) [M] | - | Failed to run, so low beta is covered only by the Barra beta factor. |

(Rows 1-40 list the 40 distinct signals; the 47 count includes the 7 duplicates noted in the first column.)

## What an interviewer might push on
1. **These are simple one-line versions, not the published constructions.** For example: Fama-French use lagged book equity and value-weighted portfolios; a true earnings surprise uses analyst forecasts; idiosyncratic volatility uses factor-model residuals.
2. **Different test design.** The papers sort stocks into portfolios monthly or yearly. Here every signal is ranked daily, industry-neutral, within the top 1000 stocks. That removes the industry part of value and quality, kills pure industry momentum, and leaves out the small caps where many anomalies are strongest. So "textbook factors earn about zero here" partly reflects this setup, not only the factors.
3. **Missing factors:** the market factor itself, short interest, analyst revisions, a real earnings surprise, net operating assets, and betting-against-beta (failed).
4. **Many anomalies have weakened since publication** (McLean-Pontiff 2016, JF [M]), so a flat result is not necessarily a bug.
5. **The intraday references** (close vs VWAP, last-hour reversal and volume share) are better described as microstructure hypotheses than established factors. That matters because they are the ones our biggest family resembles.

## What this changes in our claims
- "47 textbook factors" should be "about 40 distinct reference signals, most of them published factors, plus a few intraday signals I built".
- The main conclusion stands: **the pool's IR is unchanged after removing all of them.** But the strongest part of that statement is about the standard factors (value, profitability, momentum, size, quality). The intraday references are our own constructions, so "the closing-reversal family looks like close-vs-VWAP" means it resembles *our* signal, not a textbook one.
- The finding that standard styles earn about zero in this simulator should be stated with caveat 2 above (daily, industry-neutral, large caps only).
