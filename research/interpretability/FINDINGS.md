# Interpretability of the alpha pool — initial findings (2026-10-09)

Goal (interview feedback): explain *why* the pool works, which shared drivers it rests on, and how it would fail.
Unit of analysis: the 334 ingredients inside the 320 submitted alphas (323 with readable PnL; 11 files were locked on disk).
Reuses tags and blend risk shares from `research/hypothesis-audit/` (ingredient-catalog.csv, blend-attribution.csv).
All results are in-sample (2006/08-2021) and descriptive.

## 1. Composition (s1_composition.py)
Each ingredient's weight in the combined alpha = sum over submitted alphas of (1/320) x its risk share in that alpha.
Risk budget by audit motif: balance sheet/financing 17%, volume & trade activity 12%, price returns & shape 12%,
intraday distribution 10%, session returns 9%, session price pressure 8%, earnings valuation 7%, risk/volatility 7%,
tax accounting 6%, earnings calendar 5%, market-state gate 4%. Roughly half intraday/price-volume, half fundamental.

## 2. How many independent bets (s1, s2_drivers.py)
- 323 ingredients, mean pairwise PnL correlation 0.024. Effective number of bets (participation ratio) = 74.
- Marchenko-Pastur noise edge 1.70 (N=323, T=3477): **42 eigen-directions are real**, 55% of ingredient variance.
- Top 5 drivers are stable across 2006-13 vs 2014-21 (subspace cosines 0.95, 0.92, 0.89, 0.85, 0.82); beyond ~8 they are not.
- The 42 drivers explain 91.5% of the combined alpha's daily variance. Residual (idiosyncratic) part still has IR 0.26
  and carries ~17% of the pool's mean return.

## 3. Hidden concentration — the headline
Despite 0.05 mean correlation between submitted alphas, the pool is concentrated in two intraday drivers:
| driver | what its top ingredients are built from | share of pool risk | share of pool return | driver IR |
|---|---|---:|---:|---:|
| 1 | session price pressure (late-day), risk/volatility, price shape | 29% | 18% | 0.14 |
| 7 | intraday distribution, session returns | 15% | 14% | 0.15 |
| 5 | risk & volatility, price shape, volume | 6% | 5% | 0.09 |
| all others | | <4% each | | |
Diversification at the level of *pairs* hid a factor-level concentration: if late-session reversal decays, ~30% of
the pool's risk goes with it. This is exactly the "know why it fails" question.

## 3b. Drawdowns (s4_drawdowns.py)
- Driver 1 (late-session pressure) caused most of every major combined-alpha drawdown: 64% (Mar-Jun 2019, the worst),
  88% (May-Jun 2018), 50% (Dec 2020), 46% (Jul-Aug 2021), 60% (Mar 2021). Mar 2020 nets out (d1 lost, d7 gained).
- Drivers 1 and 7 do not hedge each other: 63-day return correlation 0.30; driver 1 vs all the rest 0.40.
- Driver 1 is regime-dependent: largest in 2008 (68 daily-sd units), 2007, 2021, 2020; smallest in calm 2012-13 and 2017.
  Hypothesis to test: it is paid for liquidity provision, which earns more when volatility is high (cf. Nagel 2012,
  "Evaporating Liquidity"). Test with a market-volatility series before claiming it.

## 3c. Naming the two big drivers (s3 with price refs, s5_regime_d7.py) — 2026-10-09
12 price/intraday reference factors added (alphas/validation/REF, Fast). Own IRs: last-hour reversal 0.071 (best of all
26 refs), 5d reversal 0.047, 1d reversal 0.034, open-to-close reversal 0.034, first-hour reversal -0.013 (control fails),
12-1 momentum 0.008, size 0.005, low vol -0.004, illiquidity 0.005.
- All 26 refs explain 28% of pool variance (price refs 22%), but none of its return: alpha IR 0.432 vs raw 0.414.
- **Driver 1 = last-hour reversal.** R2 0.73 (t=51 on ref-lasthour-rev), +5d reversal. Several hand-built intraday
  hypotheses (close-vs-VWAP exhaustion, risk-adjusted last-hour reversal, skew handoff) are last-hour reversal in disguise:
  R2 0.6-0.7, IR after control ~0.00-0.03.
- **Driver 1 pays in turbulent markets.** Daily IR by trailing-turbulence tercile (proxy: 21d volatility of slow factor
  books, lagged): calm 0.10, mid 0.16, turbulent 0.17; in 2014-21 calm -0.01 vs turbulent 0.12. Same shape for the plain
  reference factor. Consistent with liquidity provision being paid more when liquidity is scarce (Nagel 2012). Proxy is crude.
- **Driver 7 = last-hour return skewness (`skew_return_last_hour`).** Top-loading ingredients all build on it (level,
  vs own 126/252-day history, smoothed). Refs explain only 13%; IR 0.15; stable across halves; best in CALM markets
  (0.21 calm vs 0.13 turbulent) — the opposite regime profile to driver 1.
  Direction: the pool is LONG stocks with unusually positive late-session skew. That is the OPPOSITE of the lottery-skewness
  result (Amaya et al. 2015: high realized skew underperforms), so that paper does not explain it. Mechanism open.
  Clean tests queued as REF: level skew, skew vs own history, first-hour skew control, skew net of last-hour return.

## 3d. Skewness tests (REF, Fast, 2008-21)
- cs_rank(skew_return_last_hour), long high skew: IR 0.094 (2008-13 0.113, 2014-21 0.076). Not reversal: corr -0.12 with
  last-hour reversal; IR 0.102 after controlling last-hour, first-hour and 1d reversal.
- Skew vs own 126d history: 0.064. First-hour skew (control): 0.061, uncorrelated with last-hour skew (-0.05), so the
  effect is general intraday skewness, measured twice, not a last-hour phenomenon.
- Skew + last-hour reversal combined: 0.111 (two independent intraday effects).
- Mechanism tests pre-registered in MECHANISM_TESTS.md (16 Fast runs, exp REF, names mech-*).

## 3e. Mechanism verdicts (MECHANISM_TESTS.md, pre-registered)
- Driver 1 (last-hour reversal): liquidity provision fits — stronger on heavy-volume days (0.062 vs 0.051) and before
  earnings (0.079 vs 0.051); informed-trading explanation rejected on both. No size gradient inside top-1000.
- Driver 7 (intraday skewness): jump-information, microstructure-artefact and lottery explanations all rejected. Profile:
  dies after one day (lag-1 IR 0.001), strongest on quiet days (low volume 0.080 vs high 0.033; no earnings 0.077 vs 0.040),
  stronger in large caps (0.113 vs 0.076), best in calm markets. Mechanism open.

## 4. Attribution to textbook fundamental factors (s3_attribution.py)
14 canonical fundamental factors (book-to-market, earnings/FCF yield, profitability, ROA, accruals, asset growth,
issuance, EPS surprise, leverage, EY vs own history, tax growth, R&D), Fast-mode PnLs 2008-21, industry-neutral.
- These factors themselves earned ~0 (IR -0.00 to 0.04) in this universe/period.
- They explain **7% of pool variance and none of its return**: pool IR 0.414 -> 0.412 after controlling for them.
- Some drivers *are* fundamental-style risk: driver 3 (R2 0.56, FCF yield / leverage / issuance) and driver 2
  (R2 0.43, asset growth / EY vs history). The return they earn is not explained by the textbook premia.
- Individual ingredients that are mostly a named factor: search-688358bcfc87 (R2 0.52, EY vs own history — the
  slide-3 example), search-e41970f32e4c (asset growth + gross profitability), mine-610caed7310b (FCF yield).
- Pool-weighted, only 6.5% of the pool sits in ingredients with R2 > 0.25 against these factors.

## 5. What is missing (next)
1. Price/intraday reference factors to *name* drivers 1, 5 and 7: request in `reference-price-factors.json`
   (1d/5d reversal, 12-1 and 1m momentum, size, low vol, Amihud illiquidity, low turnover, overnight / open-to-close /
   last-hour / first-hour reversal). Run in Fast mode; put PnLs in `alphas/research/results/ref-<name>/fast-*.pnl.csv`;
   rerun s3_attribution.py (it picks up ref-* automatically). Expectation to test: driver 1 = last-hour / close-to-close
   reversal; driver 7 = open-to-close vs overnight return split.
2. Cluster ingredients on (factor loadings + residual correlation), check split-half stability, name each cluster
   with mechanism + failure mode.
3. Drawdown attribution: worst combined-alpha drawdowns (2008, 2020, factor crashes) split by driver.
4. Seeded search design: restrict the grammar to the fields of driver 1 and driver 7 and test economically motivated
   variants (horizon, liquidity/news conditioning, first- vs last-hour controls) out of sample.

## Caveats
Driver signs are arbitrary (each oriented so its largest loading is positive). Driver labels come from the audit's
motif tags of the 12 highest-loading ingredients: descriptive, not causal. Reference factors are Fast-mode PnLs;
ingredients are Slow-mode. Correlations use pairwise overlap (>=500 days), missing filled with 0 for the eigen step.

## 6. Follow-up (2026-10-10): timing, extended references, out-of-sample driver weighting
Scripts: s6_extended_refs.py, s7_reweight.py; factors in reference-ext-factors.json; outputs attribution-extended.csv, reweight-holdout.csv.
- Timing (tim-* jobs): fwd 1-day return IR 2.63, fwd overnight gap 1.78, fwd last-hour return 1.49 -> positions from day-t data earn close(t)->close(t+1); return_last_hour is stamped on its own day (rebuilt-from-close corr 0.785). No look-ahead; but signals assume trading at the same day's close. Driver 7 dies at lag 1 (0.001), driver 1 keeps ~half.
- 47 references (26 + 21): pool R2 0.276 -> 0.326 (OOS 0.167 -> 0.187), alpha IR 0.432 -> 0.437. Driver 1 R2 0.73 -> 0.82, top match close-vs-last-hour-VWAP (t 35). Driver 7 R2 0.14 -> 0.24, alpha IR unchanged 0.145. Drivers 4/5/6/8 mostly abnormal volume. Platform barra value/momentum/beta ~0 IR. Note: the original 14 fundamental refs already were the standard academic set.
- Holdout weighting (fit 2006-13, test 2014-21, 316 ingredients): baseline test IR 0.380; cap driver-1 cluster 0.391 (+0.011, SE 0.004); risk budget proportional to train return share 0.415 (+0.035, SE 0.008); equal risk per driver cluster 0.288 (-0.092). Three schemes tried.
- Data hygiene: ~100 PnL files had been offloaded to iCloud (errno 35 on read); rehydrated by staging. s3 rd() now retries via cat.

## 7. Review corrections and cluster map (2026-10-11)
Full detail: RESEARCH_NOTES.md section 7b. Script: s9_clusters.py; outputs clusters.csv, cluster-members.json.
- Cluster view (average linkage on 1 - PnL corr; exact additive pool decomposition): 10 clusters = 50% of pool risk, 30 = 80%. Largest = closing-price reversal, 41 alphas, 17.8% risk / 11.4% return, IR 0.193 (2006-13) -> 0.090 (2014-21), corr +0.87 with PCA driver 1. Last-hour skewness cluster 5.3% / 5.3%, 0.128 -> 0.107, corr +0.55 with driver 7.
- PCA drivers are orthogonal by construction, so 29% / 15% overstate how concentrated the pool is; read them as the PCA view, not the only view.
- Proxies: d1-subind corr 0.60 with driver 1 (R^2 0.34); d7-both corr 0.38 with driver 7 (R^2 0.15); use d7-base (corr 0.65). Both one-liners cover R^2 0.159 / 14.1% of pool return; PCA drivers 1+7 cover R^2 0.44 / 30%.
- Driver 1 decayed after 2014 (d1-base 0.144 -> 0.059). Driver 2 is about 25% the d7-d1 contrast, not a third effect.
- Batch-1 residual IR (after the residual_ir.py window fix, train 1,952 days): no variant clear in 2014-21 (best about 0.03-0.04).
