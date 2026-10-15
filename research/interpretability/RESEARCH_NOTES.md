# Interpretability research notes (agent context)

**What this is.** The working context behind the interpretability phase: why it exists, what was done and how, every hypothesis with its status, where each number comes from, and what is running now. Read it before touching anything in `research/interpretability/`.

**Relationship to the other docs.**
- **Notion** "What actually drives my alpha pool — interpretability analysis" (pages 1-9) is the owner's reading copy: plain language, interview phrasing. It omits file paths, exact definitions, dead ends and caveats that matter for agents. This file is the supplement.
- `FINDINGS.md` has the raw results by step, `MECHANISM_TESTS.md` the pre-registered tests, `SEEDED_SEARCH_HANDOFF.md` how to run new jobs, and `SEEDED_SEARCH.md` the current batch's predictions and results.
- The project doc `claude/interpretability-initial-findings.md` is the short cross-chat summary. The Claude project also keeps a copy of this file (`claude/interpretability-research-notes.md`). It lives in the Claude project, not in the repo, so the owner re-uploads this file after each update.

Last updated 2026-10-10 (after the step-1 coverage check; batch 2 written, not yet run).

---

## 1. Motivation

- **The competition phase** (Trexquant alpha challenge) optimised **count**. The site requires each submission to have Slow IR > 0.07 and full-history PnL correlation <= 0.5 with every earlier submission, or the IR/sqrt(turnover) override (>= 1.2x the correlated predecessor). The site also needs >= 1000 valid days and >= 100 average stocks. 320 alphas were submitted, mostly from a grammar search (`scripts/search/`, `alphas/factory/`) plus mining and hand-built intraday ideas. The exact maximum independent set of the pool under the full-history gate was later computed with CP-SAT (488 of 545).
- **Interview feedback** (first round): quantity was good, but the analysis was missing. Why do the alphas work? What are the common components? Cluster them, isolate the core interpretable signals, then search around those signals with a grammar instead of blind mining.
- **The owner's goal:** if something goes wrong in the pool, know *why*. Be able to name the main risks, their mechanisms and their failure modes. A second interview is about 1.5 days away (as of 2026-10-10), so prefer clear, defensible results over breadth.
- **Guiding principle:** quantity is not diversification. Pairwise correlation <= 0.5 says nothing about shared components: many weakly correlated alphas can add up to one dominant bet.

## 2. Definitions and conventions (use these exactly)

| Term | Meaning |
|---|---|
| Ingredient | A single signal inside a submitted alpha. 277 of 320 submissions are blends of 2-4 ingredients; 43 are singles. There are 334 distinct ingredients, of which 323 had readable Slow PnL in the original run. |
| Pool weight of ingredient i | w_i = sum over submitted alphas a of (1/320) x s_ia, where s_ia is i's share of a's risk (from `research/hypothesis-audit/blend-attribution.csv`). Stored in `ingredient-weights.csv`. |
| Combined alpha / pool PnL | The equal-risk average of the submitted alphas' Slow PnL. At ingredient level: sum_i w_i z_i, with z_i the ingredient PnL scaled to unit std. |
| Driver | An eigenvector of the ingredient PnL **correlation** matrix (2006-2021, Slow). The driver's PnL = Z @ v_k. Sign is aligned so the largest-magnitude loading is positive, so a driver's own IR can be negative while the pool still holds it with the opposite sign. |
| Real driver | Eigenvalue above the Marchenko-Pastur edge (1+sqrt(N/T))^2 = 1.70 (N = 323, T = 3477). 42 are real. |
| Effective bets | Participation ratio (sum lambda)^2 / sum lambda^2 = 74. The entropy version gives 147. |
| Risk share / return share | From the exact linear decomposition pool = sum of driver PnLs + residual: variance share and mean share. Note there is a second, *cluster*-based definition in `s7_reweight.py` (ingredients assigned to the driver that explains > 10% of their variance), which gives different numbers. Say which one you use. |
| IR | Daily mean / daily std (not annualised). SE ~ sqrt((1 + IR^2/2)/T): about 0.017 on the full sample, about 0.025 per half. Gaps under about 0.03 are noise. |
| Fast vs Slow | Fast = whole history in one shot (can carry forward bias and corporate-action artefacts). Slow = day by day with a lookback (the submission mode). The reference/mechanism/timing runs are Fast; ingredients are Slow. |
| Timing convention | Verified with deliberate look-ahead signals (section 4.6): positions built from day-t data earn the close(t) -> close(t+1) return. Last-hour fields are stamped on their own day. |
| Sim settings | US TOP1000, industry-neutral, delay 0, no slippage (`tq.py` and `sim-queue-worker.js`). Keep these for comparability. |

## 3. Data, code and infrastructure

- **Inputs from the earlier Codex audit** (`research/hypothesis-audit/`): `ingredient-catalog.csv` (name, formula tree features, motifs, `pnl_path`), `blend-attribution.csv`, `INITIAL_FINDINGS.md`. Use them for bookkeeping only. Its 0.5-threshold clustering is too coarse to see the drivers.
- **Scripts** (run from the repo root):
  - `s1_composition.py`: pool weights, risk budget by family.
  - `s2_drivers.py`: PCA, MP edge, split-half stability, `drivers-pca.csv`, `drivers-loadings.csv`.
  - `s3_attribution.py`: 26-ref regressions; also the shared loaders `rd()` (retries reads) and REF_DIRS.
  - `s4_drawdowns.py`, `s5_regime_d7.py`: drawdown attribution, regimes.
  - `s6_extended_refs.py`: 26 vs 47 refs, out-of-sample R^2, timing printout.
  - `s7_reweight.py`: holdout driver weighting.
  - `residual_ir.py`: scores any PnL on residual IR after the top-10 drivers + 47 refs. (Train window fixed 2026-10-10, see 4.8.)
  - `s8_coverage.py`: regresses the pool on the one-liners (R^2, return share, residual IR, out of sample); writes `coverage-oneliners.csv`.
  - `seed-jobs/make_batch*.py`, `analyze_batch*.py`: build each batch's jobs, and analyse its results (paired tests; batch 2 also decodes VIX and runs the step-4 sizing test).
  - `enqueue.py`: queue jobs through the VM inbox (sets `notify: true`).
- **Reference definitions:** `reference-price-factors.json` (12) and `reference-ext-factors.json` (21 + 4 timing tests). The 14 fundamental refs are existing `fund-probe-*` runs mapped in `s3`. Committed PnL copies are in `data/ref-pnl/`.
- **Where jobs run:** the Azure VM (`trex-vm`). Its worker `scripts/composites/sim-queue-worker.js` reads `alphas/validation/queue.json`, merges `alphas/validation/inbox/*.json`, and writes `alphas/validation/<exp>/<name>.<fast|slow>.pnl.csv` and `.json`. `deploy/sync.sh` commits and pushes `alphas/**` hourly, or on demand / via ntfy-batch completion. **Only the VM pushes `alphas/**`.** The Mac and agents push `research/**` and code.
- **Earlier REF/mechanism/timing runs** were done from the Mac with `run_ref.py` (`tq.py`, exp `REF`). Their run data exists only on the Mac (`alphas/validation/REF/`), plus the committed copy.
- **Mac hazards:** iCloud offloads files ("errno 35 Resource deadlock avoided" on reads, git "Bus error"). Fix: Finder > Download Now. The Mac's working tree also has stale edits to `alphas/validation/queue.json` and iCloud duplicates named `* 2.*`. Never commit those.
- **Queue state on the VM (2026-10-10):** 21 pending M006 mining Slow jobs were parked as `hold:pending` so the SEED runs are not blocked. `alphas/search/STOP` and `alphas/composites/STOP-CYCLE` pause the competition search and the pool cycle. Restore only if the owner asks.

## 4. What was done, step by step

### 4.1 Composition (s1)
Pool weight per ingredient, risk by leaf family and motif. Result: risk concentrates in intraday "session price pressure" and "intraday distribution" motifs, with a long tail of small fundamental and volume ingredients.

### 4.2 Drivers (s2)
- Correlation matrix of 323 ingredient PnLs (min 500 overlapping days); eigen-decomposition.
- Mean pairwise correlation is 0.024, yet 42 eigenvalues exceed the noise edge. Together they hold 55% of ingredient variance and 91.5% of pool variance; the pool's residual still carries about 17% of its mean.
- Split-half stability (2006-13 vs 2014-21, principal-angle cosines of the top-k subspaces): 0.95/0.92/0.89/0.85/0.82/0.71/0.58/0.56/0.45/0.07. **Interpret only the top ~5 directions as stable.** Driver 7 is an exception in practice because it is a strong, distinct effect, but its exact eigenvector is not guaranteed.
- Why few drivers produce many "uncorrelated" alphas: if n members each put a fraction rho of their variance on one driver, any pair correlates ~rho (e.g. 0.12, which passes the gate), but their average is rho + (1 - rho)/n driver, i.e. 85% for rho = 0.12 and n = 40. A pairwise gate cannot see this.

### 4.3 Attribution to reference factors (s3, then s6)
Regress each driver (and the pool, and each ingredient) on the reference PnLs (OLS, plain t-stats, no HAC correction).
- 26 refs: pool R^2 0.276 (price 0.224, fundamental 0.074); alpha IR after controls 0.432 vs raw 0.414.
- 47 refs: pool R^2 0.326, out-of-sample R^2 (betas fitted 2008-13, scored 2014-21) 0.167 -> 0.187, alpha IR 0.437. **Known factors explain some risk and none of the return.**
- Standard styles earn about 0 in this simulator: value (several definitions, platform `barra_value`), momentum (`barra_momentum`, residual, industry), low vol, idiosyncratic vol, MAX, seasonality, `barra_beta`. Accruals (0.059), gross profitability (0.036) and R&D intensity (0.043) are the only fundamentals with some IR.
- Short-horizon refs that matter: close vs last-hour VWAP (0.102), last-hour volume share (0.071), last-hour reversal (0.071), 5-day reversal (0.047), abnormal volume (0.033).
- Correction made during the analysis: the original 14 fundamental refs *were* the standard academic set (an earlier chat claim said otherwise).

### 4.4 Concentration and drawdowns (s4)
- Driver 1 accounts for most of every major drawdown: 2019-03 -> 06 (-11 daily SD, 64% from driver 1), 2018 (88%), Dec 2020 (50%), Mar 2021 (60%), Jul-Aug 2021 (46%). Mar 2020 nets out.
- The 63-day return correlation of driver 1 vs driver 7 is 0.30. Ingredient-level check (top-40 members each): within-group correlation 0.336 (d1) and 0.122 (d7), cross-group 0.043, 6/40 members shared. **Drivers 1 and 7 are distinct.** Member-average PnLs correlate 0.23 daily and 0.43 over 63 days (a mild shared component).
- **Possible split factor: drivers 7 and 2.** Their member averages correlate 0.35 daily (0.42 at 63d), with 7/40 shared members. This is unresolved.

### 4.5 Mechanism tests (pre-registered, Fast)
See `MECHANISM_TESTS.md` for the predictions. Hypotheses:

| Code | Story | Prediction signature |
|---|---|---|
| H-LP | Liquidity provision: paid to absorb temporary order-flow imbalance | stronger when liquidity demand is high (volume, turbulence); decays over days |
| H-INF | Informed trading / news | stronger before earnings; persists with lag |
| H-JUMP | Compensation for jump / skew risk | stronger in turbulent regimes |
| H-MICRO | Microstructure / bid-ask / capacity | stronger in small, illiquid names; dies at lag |
| H-LOTTERY | Lottery demand mispricing | stronger in small, retail-heavy names |

**Driver 1** results (IR full; 2008-13 / 2014-21 in brackets):

| Test | IR |
|---|---|
| High volume | 0.062 (0.058 / 0.065) |
| Low volume | 0.051 (0.069 / 0.035) |
| Pre-earnings | 0.079 (0.117 / 0.050) |
| No earnings | 0.051 (0.061 / 0.041) |
| Lag-1 | 0.033 |
| Big | 0.040 |
| Small | 0.036 |
| Turbulence terciles (calm / mid / turbulent) | 0.098 / 0.162 / 0.173 |
| Same, 2014-21 | -0.011 / 0.123 / 0.123 |

Verdict: **H-LP preferred, moderate evidence.** The regime pattern and the slow decay are clear; the volume and earnings splits are within noise. Failure mode: calm markets.

**Driver 7** results:

| Test | IR |
|---|---|
| Big | 0.113 (0.074 / 0.123) |
| Small | 0.076 (0.207 / 0.045) |
| High volume | 0.033 |
| Low volume | 0.080 |
| Pre-earnings | 0.040 |
| No earnings | 0.077 |
| Lag-1 | 0.001 |
| Lag-5 | 0.002 |
| 20-day mean | 0.015 |
| Terciles (calm / mid / turbulent) | 0.21 / 0.14 / 0.132 |

Size splits start 2011-09, with 425 stocks per side. A first version (`cs_rank(mktcap) > 0.5`) silently selected nothing and was replaced by `cs_zscore(log mktcap) > 0`.

Verdict: H-JUMP, H-MICRO and H-LOTTERY fail. **Strong fingerprint** (a one-day effect, quiet days, calm markets), **weak splits**, mechanism open.

Skew details:
- Level, Fast: 0.088 (0.094 aligned).
- Relative to its own history: 0.064.
- First-hour skew: 0.058-0.061.
- Skew minus last-hour return: 0.109-0.111.
- Correlation with last-hour reversal: -0.12.
- Alpha IR after reversal controls: 0.102.

Note: Amaya et al. (2015) find realised skewness predicts *negative* returns, the opposite sign, so it is not an explanation.

### 4.6 Timing check (tim-* jobs)
- Tomorrow's ret1: IR 2.63.
- Tomorrow's overnight gap: 1.78. Together these mean the position is entered at the close of day t.
- Tomorrow's last-hour return: 1.49 (the field is stamped on its own day).
- Last-hour reversal rebuilt from the daily close and the 3 pm price: 0.085, correlation 0.785 with the original (alignment confirmed).
- Two-days-ahead variants score 0.22 and 0.46: unexplained secondary leakage, probably cross-day return correlation. Not decisive.
- **Conclusion:** no look-ahead. But last-hour signals assume trading in the closing auction with data up to the close. Driver 7 is fully dependent on that (0 at lag 1).

### 4.7 Out-of-sample driver weighting (s7)
- Fitted on 2006-13 only (scaling, PCA, cluster membership, weights), evaluated on 2014-21, 316 ingredients.
- Train cluster shares: driver-1 cluster 18.7% risk / 13.5% return; the "no dominant driver" bucket (164 ingredients) 43.8% / 49.9%.

| Weighting | Test IR |
|---|---|
| Baseline | 0.380 |
| Cap the driver-1 cluster at its return share (x0.48) | 0.391 (+0.011, SE 0.004) |
| Risk budget proportional to train return share | 0.415 (+0.035, SE 0.008) |
| Equal risk per cluster | 0.288 (-0.092) |

- Three schemes were tried, so the best is mildly selected. The SEs are small because the portfolios are highly correlated.
- The competition does not let you set weights; this is the "real strategy" use of the analysis.

### 4.8 Coverage of the pool by the two one-liners (step 1, no new runs; `s8_coverage.py`)
Full table in `SEEDED_SEARCH.md` ("Step 1").
- Pool on d1-subind + d7-both: **R^2 0.159** (0.157 / 0.161 by half; 0.150 out of sample), **14% of the pool's mean return** (19% in 2006-13, 10% in 2014-21), pool residual IR 0.411 vs 0.439. d1-base + d7-base gives R^2 0.187, also 14% of return.
- For scale: the full PCA drivers 1 + 7 give R^2 0.441 and 30% of return. The 47 refs give R^2 0.305 and 17% of the mean, with residual IR unchanged at 0.439. Refs + both one-liners: R^2 0.347, residual IR 0.424 (0.380 out of sample).
- The one-liners correlate 0.70 (d1-base) and 0.66 (d7-base) with the average of their driver's top-40 members, so each captures about half its driver. First-hour skew is *not* in the pool (0.05 with driver 7's members).
- **Plain reading:** the two named effects are real and the largest single pieces, but they are a minority of the pool. About 80% of the pool's mean return (78%) is in components that neither the one-liners nor the 47 known factors capture.
- **Driver 1 weakened after 2014:** d1-base IR 0.144 (2006-13) -> 0.059 (2014-21); d1-subind 0.165 -> 0.062. Driver 7 did not: d7-both 0.093 -> 0.109, d7-base 0.101 -> 0.076. This was in the batch-1 table but not stated before. It matters for the interview: the biggest risk driver is also the one whose payoff has decayed most.
- **residual_ir.py bug, fixed:** six refs (fcf_yield, value_bm, rd_intensity, size, x_value-bm, x_value-cfp) start 2011-09, and the all-columns-present filter silently cut the "train" window to 2011-09..2013-12 (about 570 days). Refs now count as 0 before their start. Residual IRs reported before this date (only the batch-1 smoke checks) used the short window. With the fix, no batch-1 variant has clear residual IR in 2014-21. The largest are d7-skewclose 0.040, d7-fh 0.035, d1-vix-hi 0.028, d1-subind 0.024 (all about 1-1.5 SE).

### 4.9 Driver 2 is a contrast of drivers 1 and 7, not a third mechanism
- PCA driver 2 regressed on d1-base and d7-base: R^2 0.26, t = -24 (closing reversal) and +23 (last-hour skew). Its top-40 members' average correlates +0.37 / -0.32 with d7-base / d1-base, with opposite signs.
- d1 and d7 correlate -0.10. PCA's orthogonality then splits their common space into a "both" direction and a "difference" direction, so driver 2 is mostly the difference. This answers the "split factor" question from 4.4: treat drivers 1, 2 and 7 as two economic effects, not three.

## 5. Driver identity cards (current best names)

Shares: full-sample projection definition (`drivers-pca.csv`). Top refs: from `attribution-extended.csv` (47 refs).

| Driver | Own IR | Risk / return share | Best reference matches | Members / motifs | Working name |
|---|---|---|---|---|---|
| 1 | 0.142 | 29% / 18% | close vs last-hour VWAP (+35t), last-hour reversal (+17t), 5-day reversal (+13t) | session price pressure; hand-built 44%, search 43%, 101 13% | **Closing-price reversal** (liquidity provision) |
| 2 | 0.058 | 3.0% / 2.8% | close-vs-VWAP (-25t, opposite side), 5-day reversal (+14t), 1-month return (-12t), abnormal volume (+10t) | volume and trade activity; balance sheet | **Skew minus closing reversal**: mostly a PCA contrast of drivers 7 and 1 (4.9) |
| 3 | -0.029 | 1.3% / 0.9% | FCF yield (-12t), MAX (-10t), abnormal volume (+10t) | volume; balance sheet | Small; volume x value mix |
| 4 | -0.038 | 3.0% / 1.8% | abnormal volume (-15t), earnings yield vs history (-12t), 5-day reversal (+12t) | 101-alpha-51/09/10/56 | **101-formula short-term reversal / volume** |
| 5 | 0.088 | 6.4% / 5.0% | abnormal volume (-25t), last-hour volume share (+11t) | risk and volatility; mined ndm-* | **Quiet-volume / closing-share** |
| 6 | -0.063 | 3.2% / 2.5% | abnormal volume (+19t), 5-day reversal (-16t), earnings yield vs history (+12t) | earnings valuation; balance sheet | Volume shock x valuation |
| 7 | 0.145 | 15.4% / 14.1% | close-vs-VWAP (+14t), last-hour reversal (-6t); R^2 only 0.24 | 97% search-generated (38/38 members) | **Intraday return skewness** (spike-then-fade rejected in batch 1; members' average corr 0.66 with last-hour skew) |

Driver 6's stability is borderline (cosine 0.71). Treat drivers 2-6 as a map, not as findings.

Origin of the two big drivers:
- Driver 1 = 50 members: 18 hand-built, 24 search, 8 from the 101 formulas.
- Driver 7 = 38 search members.

Why did the search lean intraday? **Hypothesis (untested):** breadth. IR ~ skill x sqrt(independent bets per year), and fast signals re-bet daily. The competition score also ignores trading costs. Test: IR vs turnover across ingredients.

## 6. Batch 1 (done; results in SEEDED_SEARCH.md)

Files: `seed-jobs/make_batch1.py` -> `seed-jobs/batch1.json` (44 Fast + 4 Slow, exps `SEED-D1` / `SEED-D7`, `notify: true`). The predictions table is in `SEEDED_SEARCH.md` (written before any run). After the VM sync, run `seed-jobs/analyze_batch1.py` (it prints the paired tests with the 0.03 threshold) and `residual_ir.py --exp SEED-D7`.

**Driver 1, base `-(close / vwap_last_hour - 1)`:**
- *Reference price* (VWAP vs 3 pm price vs (H+L)/2 vs first-hour VWAP vs VWAP-vs-3pm). Question: is it the *closing price's deviation from where volume traded* that reverts? Prediction: the last-hour VWAP is the best anchor.
- *Liquidity demand* (abnormal volume, last-hour volume share, trade-count surprise, stock-level last-hour volatility; high vs low halves). Under H-LP, every "high" split should beat its "low" by more than 0.03.
- *Market turbulence* (VIX above vs below its 1-year mean). H-LP predicts the turbulent half is stronger (matches the tercile result).
- *Horizon* (3-day mean, lag 1, lag 2). Slow decay is predicted.
- *Robustness* (subindustry neutralisation; plus last-hour reversal; tilt to volume shocks).

**Driver 7, base `skew_return_last_hour`:**
- *Spike-then-fade*: the 47-ref loadings (+close-below-VWAP, -last-hour reversal) suggest positive skew = the price spiked within the hour and gave it back. Predictions: closed below VWAP beats above; last hour up beats down; "fade from high" `(high_lh - close)/(high_lh - low_lh)` is positive on its own.
- *Session*: first-hour skew, both summed, `skew_close_last_hour`; `skew_volume_last_hour` as a control (about 0).
- *Conditioning*: quiet vs noisy hour (quiet predicted stronger); closing-flow share high vs low (the institutional close-flow story predicts high > low); VIX low vs high (calm predicted stronger); trade-count splits (exploratory).
- *Controls*: lag 1 (expect 0), subindustry neutralisation, skew minus 0.5 x driver-1 base.

**Slow base runs:** d1-base, d1-lh-rev, d7-base, d7-fh (lookback 30). These give proper PnLs and a Fast-vs-Slow check of the core effects.

**Smoke test from the Mac** (Fast, before the VM batch):
- d1-vix-hi 0.103, d1-subind 0.113, d1-x-volscale 0.063.
- d7-belowvwap 0.083, d7-fade-from-high 0.100 (supports spike-then-fade, pending the paired test), d7-ir-lh -0.061.

**Decision rules for batch 2 (Slow confirmation, about 20-30 jobs):**
- Slow-run the top 3-5 variants per family by Fast IR.
- Also Slow-run any paired test that is "clear" (> 0.03), in both halves of the pair.
- Use lookback = longest window + 10.
- Report Fast vs Slow side by side.


**Batch 1 outcome (2026-10-10; full tables in `SEEDED_SEARCH.md`).**
- Slow = Fast for the base signals (PnL corr 0.99+).
- Driver 1: last-hour VWAP is the best anchor; subindustry-neutral version 0.113. It is mostly a 1-day effect. Paid in stress (VIX high vs low +0.046 in both halves). Volume and trade surprises make no difference. It is stronger on *thin* closing volume (-0.054, 2006-13 only).
- Driver 7: spike-then-fade **rejected** (the fade signal is driver 1, corr 0.74). The closing-flow story is **rejected**. Quiet > noisy in both halves. First- and last-hour skew are independent (corr -0.05) and sum to 0.101.

## 7. Where things stand and next directions (updated after step 1; batch 2 queued)

**State of knowledge**
- **Driver 1** = closing-price reversal: the close's deviation from the last-hour VWAP reverts the next day.
  - Paid in **stress**: VIX high vs low +0.046 in both halves (batch-1 gate not clean per stock; being recomputed at the PnL level in batch 2). Stock-level volatility weakly +0.027.
  - Strongest on **thin closing volume** (-0.054 for heavy vs light; 2006-13 only). Indifferent to volume and trade surprises.
  - Mostly a one-day effect.
  - **Weakened after 2014**: d1-base 0.144 -> 0.059, d1-subind 0.165 -> 0.062.
  - Best one-liner: `cs_rank(cs_indneut(cs_zscore(-(close/vwap_last_hour-1)), subindustry))`, IR 0.113. It captures about half of the driver (corr 0.66 with its members' average).
  - Working mechanism: liquidity provision against **temporary, thin-market closing dislocations**. Volume-backed closing moves likely carry information (Llorente et al. 2002). This is an interpretation, being tested in batch 2.
- **Driver 7** = intraday return skewness.
  - The pool holds the **last-hour** version (members' average corr 0.66 with last-hour skew, 0.05 with first-hour skew).
  - First- and last-hour skew are independent (corr -0.05). Their sum gives IR 0.101, steady across halves (0.093 / 0.109).
  - Stronger in **quiet** conditions (both halves).
  - Rejected: spike-then-fade, closing institutional flow, jump compensation, microstructure, lottery. Mechanism open. Batch 2 tests the "lumpy returns in thinly traded stocks" artefact.
- **Driver 2** = mostly the contrast of drivers 7 and 1 (4.9). Not a separate mechanism.
- **Coverage:** the two one-liners explain about 16-19% of pool variance and 14% of pool return. The PCA drivers 1 + 7 explain 44% / 30%. Pool residual IR after one-liners + 47 refs is still 0.42.
- **Method lessons:**
  - Slow matches Fast for these intraday signals (PnL corr 0.99+).
  - Day-level gates must use the same value for every stock. `ts_mean` of a broadcast index field is not (each stock has its own window).
  - Positions are rescaled to a fixed book each day, so market-level sizing has to be applied to PnL.

**Running now: batch 2** (`seed-jobs/batch2.json`, predictions in `SEEDED_SEARCH.md`). After the sync: `python3 research/interpretability/seed-jobs/analyze_batch2.py`, then `residual_ir.py --exp SEED-D1` / `SEED-D7`.
- Step 2 (thin-volume reading of driver 1): characteristic vs day-surprise closing share, continuous thin/thick tilts, size (dollar volume) x share 2x2, close above vs below VWAP, market up vs down days.
- Step 3 (driver 7): trade-count terciles, average trade size, cross-sectional quiet/noisy, sign of skew only, size halves, first-hour trade count, and a `cs_factorneut` attempt.
- Steps 2-3: look-ahead diagnostics (SEED-LA): is each effect earned overnight or intraday tomorrow?
- Step 4: VIX decoded from 10 bit-gated jobs; one-parameter VIX sizing, fit 2006-13, tested 2014-21 (pre-registered in `SEEDED_SEARCH.md`).
- Slow confirms of d1-subind and d7-both.

**Next directions, in priority order**
1. **Analyse batch 2** and update the driver-1 and driver-7 stories. Report failed predictions plainly.
2. **Why did driver 1 weaken after 2014?** Cheap checks on existing PnLs: rolling 1-year IR of d1-base, the turnover-adjusted view, and whether the decay is concentrated in calm years (VIX decode from batch 2). Candidate explanations: crowding of closing-auction liquidity provision, and more closing-auction volume after 2014 (more index/ETF flow makes the close "thicker", which the thin-volume reading says should weaken the effect). The second is testable with the closing share by year.
3. **Seeded search scored on residual IR** (old step 5). Seeds: first-hour skew and skew of close prices (the only batch-1 variants with test residual IR around 0.035-0.040), plus whatever batch 2 shows. Score on residual IR after the drivers + 47 refs (train > 0.05, same sign in test). Stop when the residual dries up.
4. **The unexplained 80% of pool return.** The drivers beyond 7 are unstable, so describe the residual by family (s1 motifs) rather than by eigenvector: which ingredient families carry the pool's residual mean after d1/d7/refs.
5. **Housekeeping on the VM** (unchanged since 2026-10-10 ~00:00 IST):
   - The worker runs by hand in tmux `w` (`--fast 4 --slow 2`).
   - `trex-cycle` is stopped; `alphas/search/STOP` and `STOP-CYCLE` exist.
   - 52 M006/M007 mining jobs are parked as `hold:pending`.
   - Restore with `tmux kill-session -t w; sudo systemctl start trex-worker` (plus trex-cycle and removing the STOP files only if the mining/search should resume). Revert parked jobs by swapping `hold:pending` -> `pending`.

## 7b. Review corrections and cluster map (2026-10-11)

A second agent reviewed the work; every claim below was re-checked against existing files (no new simulations). Sections 5-8 were updated by a parallel session with the same corrections (batch-2 plans); this section adds the proxy-correlation numbers and the full cluster map. If the two ever disagree, check the underlying CSVs.

**Corrections**
- **Names are proxies.** PCA drivers are orthogonal by construction, so a real effect can be split or blended; naming by regression onto reference factors is loose. One-liners are stand-ins:
  - `d1-subind` correlates **0.60** with PCA driver 1 (R^2 0.34; explains 47% of its return). "R^2 0.82" is driver 1 regressed on all 47 refs, not the one-liner.
  - `d7-both` (first + last hour skew) correlates only **0.38** with PCA driver 7 (R^2 0.15, 27% of its return; the first-hour part has corr 0.04). **Use `d7-base` (last-hour skew; corr 0.65 with the top-40 driver-7 members) as the driver-7 proxy.** First-hour skew is a separate signal, not a property of driver 7. Drop the "two independent sessions" claim from driver 7.
- **Coverage is small.** The two one-liners explain pool R^2 0.159 and 14.1% of pool return (pool IR 0.439 -> 0.411 when removed). PCA drivers 1 + 7 explain R^2 0.44 and 30% of return.
- **Driver 1 has decayed.** IR 2006-13 -> 2014-21: d1-base 0.144 -> 0.059, d1-subind 0.165 -> 0.062; d7-both 0.093 -> 0.109, d7-base 0.101 -> 0.076. The biggest risk driver has the most-decayed payoff.
- **VIX result is approximate.** The gate was not uniform across stocks (both PnLs nonzero on 1,941 of 3,715 days; on days only one side was active, high 0.193 vs low 0.050). Market-level sizing inside an alpha is normalised away by booksize; VIX sizing must be applied to the PnL afterwards. Soften "paid in stress" to "leans toward stress".
- **`residual_ir.py` bug.** The training window was 572 days (2011-09 to 2013-12) because late-starting refs dropped rows. After the `fillna(0)` fix it is 1,952 days. After the fix **no batch-1 variant has clear residual IR in 2014-21 (best about 0.03-0.04, inside the noise)**. Batch 1 gave descriptions of the drivers, not better versions. The script now also skips a reference identical to the candidate.
- **Driver 2.** About 25% of it is the d7 - d1 contrast (R^2 0.245, t -23.9 / +24.4); the remainder has residual IR 0.071. It is small (3.0% risk / 2.8% return) and not a named third effect; the PCA-orthogonality artefact reading is partly right.

**Cluster map (`s9_clusters.py`, outputs `clusters.csv`, `cluster-members.json`; commit 953ea9a9)**
- Method: average-linkage clustering of the 323 ingredients on 1 - PnL correlation. Exact additive decomposition of the pool PnL into cluster parts (risk share = cov(part, pool) / var(pool), return share = mean ratio). Naming by field enrichment (member field share vs pool share). Split-half stability by Jaccard overlap; coverage curve.
- Result: **10 clusters carry 50% of pool risk, 30 carry 80%**; the 33 clusters with >= 3 members carry 82% risk / 71% return. Cluster count depends on the cut (74-153 clusters for cuts 0.15-0.30); about half the top clusters recur in both halves.
- Families (risk / return share; IR 2006-13 -> 2014-21; split-half stability):
  - closing-price reversal (cl0, 41 alphas): 17.8% / 11.4%; 0.193 -> 0.090; 0.56. Corr with PCA driver 1 +0.87.
  - size / valuation x price (cl1, 16): 6.9% / 4.8%; 0.119 -> 0.098; 0.50.
  - last-hour skewness (cl2, 11): 5.3% / 5.3%; 0.128 -> 0.107; 0.65. Corr with driver 7 only +0.55.
  - balance sheet x size (cl5, 5): 3.5% / 3.1%; 0.049 -> 0.104; 1.00.
  - balance sheet / profit margin x intraday (cl6, 6): 3.4% / 3.6%; 0.089 -> 0.122.
  - volume / market-state gate (cl3, 7): 3.3% / 2.9%; 0.139 -> 0.034; 0.20 (unstable).
  - range / volatility (cl4, 10): 3.0% / 3.1%; 0.114 -> 0.073.
  - volume x high/low, mostly 101 formulas (cl14, 12): 3.0% / 2.0%; 0.171 -> 0.054.
  - trade activity (cl7, 11): 2.9% / 2.3%; 0.130 -> 0.042; 0.42. Corr with driver 2 about +0.47.
  - 101-formula price shape (cl8, 11): 2.7% / 3.3%; 0.212 -> 0.050.
  - first/last-hour price shape mix (cl12, 7): 2.7% / 2.0%; 0.062 -> 0.115.
  - balance sheet x first-hour volatility (cl9, 6): 2.1% / 1.8%; 0.088 -> 0.069.
- Reading: price/volume pattern families faded after 2014; skewness, size/valuation, and the balance-sheet-plus-intraday families held or improved. The pool is not "two drivers": PCA concentrates shared variance on the first components, while the cluster view shows the largest block at about 18% and a long tail of families.
- Using it: describe the 5-6 next-largest families with the same pre-registered tests as drivers 1 and 7 before seeding any new search. Score new candidates on residual IR after the drivers and families, not on raw IR.

**Family descriptions (2026-10-11): `FAMILY_EXEMPLARS.md`, script `s10_families.py`** (outputs `family-*.csv`; brief in `FAMILY_HANDOFF.md`).
- Exemplars: one simple member stands for each big family. LOO corr 0.75-0.79 for closing reversal, earnings yield vs history, and last-hour skew; cl2's top member *is* the last-hour-skew one-liner.
- Renamed: cl1 = earnings yield vs its own 1-year history (`cs_rank(ts_rank(operating_income/mktcap, 252))`), not size. cl5 = current liabilities / total assets (very slow). cl6 = a loose mix of short-term move x profitability.
- Post-2014: clear falls (> 2 SE) in closing reversal (0.193 -> 0.090), volume on up days, closing share of trades, and both 101-formula families. No clear change in earnings yield vs history, skew, cl5 or cl6. Pool 0.52 -> 0.40. Yearly IR shows the closing reversal's drop came in **2009** (0.40-0.43 in 2006-08, mostly 0.03-0.17 after).
- Drawdowns by family: closing reversal is the largest single family in all six worst drawdowns, averaging 38% of each loss (about 2x its 18% risk share). In the deepest (2019) it was only 20%, with cl1 19% and cl7 17%. The PCA figures (64% / 88%) overstated it.
- Cut robustness: the top four families survive every cut; cl6, cl3 and cl14 do not.

**Framing note from the owner (2026-10-11): alignment with known factors is validation, not a weakness.**
- When a family matches a published effect, that shows the search rediscovered something real. Say so, and cite the paper ("this is the earnings-announcement premium, Frazzini-Lamont 2007").
- Novelty is good only when it is tested and explainable (skew is the example: tested, described precisely, mechanism still open).
- Residual IR after the reference factors measures *what is new*. It is **not** a quality filter: do not rank or drop families for resembling known factors.
- For every family, including the smaller ones, record a literature link where one exists and how close the match is: same effect / variant of a known effect / novel.

**10-family tests (2026-10-11).** Files:
- `FAMILY_CARDS.md`: the readable summary (math, exemplar mapping, tests, verdicts).
- `FAMILY_TESTS.md`: predictions and full results.
- `s11_family_screen.py`: family selection.
- `s12_family_realism.py`: costs and bad days.
- `seed-jobs/batch3*` (65 Fast) and `batch4*` (11 Slow + 2 Fast, queued).

Results:
- **Skew (cl2) is not a lumpy-tape artefact.** It fails 3 of 4 artefact predictions: it is present in heavily traded stocks (0.048), strongest where trades are small (0.100 vs 0.023), and the sign alone is worthless (-0.010).
- **Small-trade reversal (cl20) held in both halves** (0.068 vs 0.027). Provisional: Fast != Slow (corr ~0.5) for ts_* operators on last-hour fields; batch 4 re-checks it in Slow.
- **Known effects confirmed:** up-gap reversal (cl12), attention on busy wide-range days (cl4).
- **Stories that failed:** earnings-announcement premium (cl11), current liabilities (cl5), profitability x reversal (cl6).
- **Reversal decay:** concentrated in big stocks (cl0 provisional, cl8).
- **Costs:** fast families break even at about 1-3 bps per dollar traded (not tradeable alone); slow fundamental ones at 6-47 bps.
- **Batch 4 (Slow) landed:**
  - The cl20 small-trade reversal is confirmed (0.071 vs 0.019, both halves).
  - The cl0 'decay only in big stocks' claim is NOT confirmed (both sizes decayed).
  - The cl2 artefact tests are confirmed.
  - With trade size in dollars, skew's small-trade link holds only in 2006-13.
  - Cards, tests file and Notion 3g updated.

## 8. Caveats to state honestly
- Mostly in-sample; only the weighting test is a true holdout.
- Fast references vs Slow ingredients.
- No multiple-testing correction across many splits; plain OLS t-stats.
- PCA eigenvectors beyond about 5 rotate between halves.
- The turbulence proxy is crude (21-day volatility of slow factor books; VIX in batch 1).
- Last-hour effects depend on closing-auction execution.
- The batch-1 VIX gate was not uniform across stocks (see 7). Treat its hi/lo numbers as approximate until batch 2 recomputes them.
- The coverage numbers use Fast PnLs for the one-liners against a Slow pool (Slow confirms of d1-subind and d7-both are in batch 2; Fast = Slow so far).
- PCA driver PnLs inside `residual_ir.py` use full-sample eigenvectors, so "betas fitted 2006-13" is not fully out of sample.
- One-liners are proxies (corr 0.60 / 0.65 with their PCA drivers); cluster counts depend on the cut; VIX result approximate (see 7b).

## 9. Interview framing (lines the owner can use)
- "320 alphas are about 74 independent bets. In a PCA view two drivers carry 44% of the risk, but PCA exaggerates concentration: grouping alphas directly, the biggest family (closing-price reversal) is about 18% of risk and ten families carry half."
- "That reversal family has weakened since 2014 (IR 0.19 -> 0.09), and my simple one-line stand-ins explain only about 14% of the pool's return, so I describe the largest parts, not the whole pool."
- "Driver 1 is a closing-price reversal. It pays most when liquidity is scarce, and it caused most of my drawdowns. Driver 7 is a skewness effect I can describe but not yet explain: it lasts one day and fails the standard explanations."
- "Known factors explain a third of the pool's risk and none of its return. I checked look-ahead with deliberately cheating signals. Sizing by driver, fitted on 2006-13 only, lifted 2014-21 IR from 0.38 to 0.41."
- "The lesson: the next alpha should be judged on what new driver it adds, not on passing a correlation gate."
- "Two one-line signals reproduce about a sixth of the pool's daily risk and about a seventh of its return. They are the biggest named pieces, but most of the pool is many small components I can't name yet. I'd rather say that than over-claim."
- "The closing reversal has weakened: IR 0.14 before 2014, 0.06 after. The skew effect hasn't. So my largest risk is also my most decayed source of return, which is why sizing by driver matters."
- "Driver 2 looked like a third effect, but it's the difference of the first two: PCA forces it to be orthogonal."

- **Batch 5 (ran; results in `seed-jobs/batch5-predictions.md`: first-hour twin shows no reversal and no trade-size gap, ambiguous because entry is at the close):** first-hour twin of cl20 (`seed-jobs/batch5.json`, 5 Fast + 3 Slow, names `fh20-*`). Predictions and the reading rule are in `seed-jobs/batch5-predictions.md`; analyse with `seed-jobs/analyze_batch5.py`. Open presentation decisions are in `PRESENTATION_ALPHAS.md` section 5.
