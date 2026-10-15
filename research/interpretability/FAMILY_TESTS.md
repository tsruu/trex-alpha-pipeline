# Family tests: what each family does, why it might work, and how it is tested

Written 2026-10-11, **before** batch 3 ran. Families come from `s9_clusters.py` (CUT 0.8). Selection is in `s11_family_screen.py` / `family-screen.csv`: the four largest by risk, plus the ones that look best on paper (steady IR, positive most years, robust to the clustering cut, a member that tracks the family well).
Framing (owner, 2026-10-11): matching a known effect is validation of the search. Novelty is good only when it is tested and explainable, and it is what an interviewer will attack.

**Real-world check** (`s12_family_realism.py`, `family-realism.csv`; from each member's own Slow stats, pool-weighted).
- *Break-even* is the trading cost per dollar traded, in basis points, at which the family earns nothing. The simulator charged no costs. Realistic one-way costs for large US stocks are roughly 2-5 bps, so families below about 2-3 bps would not survive costs on their own.
- Netting across a whole pool lowers real turnover, so the per-family numbers are pessimistic.
- *Bad-day ratio* = the family's share of the pool's loss on its worst 5% of days, divided by its normal risk share. Above 1 means it is over-represented when the pool has a bad day.

| Family | Risk share | Turnover / day | Break-even (bps) | Bad-day ratio | Worst day (SD) | Would I trade it alone? |
|---|---|---|---|---|---|---|
| cl0 closing-price reversal | 17.8% | 1.11 | 2.9 | 1.10 | -7.4 | Marginal: needs cheap closing-auction execution |
| cl1 earnings yield vs own history | 6.9% | 0.70 | 2.9 | 0.76 | -11.2 | Marginal; it is a cushion on bad days, but has one very large worst day |
| cl2 last-hour skewness | 5.3% | 1.17 | 1.4 | 1.10 | -5.9 | **No**: edge too small per dollar traded |
| cl5 current-liabilities share | 3.5% | 0.24 | 8.1 | 1.29 | -5.0 | Yes on costs; somewhat over-represented on bad days |
| cl4 wide range on high-volume days | 3.0% | 1.18 | 1.5 | **1.60** | **-12.2** | **No**: thin edge, and the most over-represented on bad days |
| cl11 approaching earnings | 1.7% | 0.22 | 6.4 | 1.12 | -8.1 | Yes on costs |
| cl20 many small trades at the close | 2.0% | 1.22 | 1.2 | 1.05 | -5.8 | **No**: edge too small per dollar traded |
| cl12 overnight gap reversal | 2.7% | 0.83 | 2.4 | 1.09 | -7.7 | Marginal |
| cl6 short-term move x profitability | 3.4% | 1.22 | 1.5 | 1.11 | -9.0 | **No** on costs |
| cl8 intraday reversal (101 formulas) | 2.7% | 1.43 | 1.8 | 1.21 | -9.7 | **No**: high turnover, decayed, over-represented on bad days |

Reading: the slow, fundamental families (current liabilities, approaching earnings) survive realistic costs. The fast intraday families, including both novel ones, earn too little per dollar traded to trade alone. Their value is inside a pooled book where trades net out, and only if closing-auction execution is cheap. That is the honest "would I trade it" answer.

## The 10 families

**cl0 Closing-price reversal** (41 alphas; exemplar `intraday-vr1-vwap-exp22`)
- *Does:* shorts stocks whose last-hour close sits above the last-hour average price (VWAP), averaged over about 5 days; buys those below.
- *Why (tested in batches 1-2):* someone pushed the price at the close; the liquidity provider who takes the other side is paid when it snaps back. It pays more in stress. Faded after 2008.
- *Literature:* price pressure and liquidity provision (Campbell-Grossman-Wang 1993; Hendershott-Menkveld 2014; Nagel 2012). **Variant of a known effect.**

**cl1 Earnings yield vs its own history** (16; exemplar `search-688358bcfc87`, `cs_rank(ts_rank(basic_eps/close, 252))`)
- *Does:* buys stocks whose earnings yield is near the top of its own past-year range.
- *Why (hypothesis):* either the price has fallen while earnings held (long-horizon reversal / cheapness vs own history) or earnings rose and the price has not caught up (post-earnings drift).
- *Test:* split the signal into its earnings part and its price part, and check whether it pays mainly after announcements.
- *Literature:* post-earnings drift (Bernard-Thomas 1989), long-term reversal (De Bondt-Thaler 1985). **Variant, to be decided by the test.**

**cl2 Last-hour skewness** (11; exemplar `ndm-d593b15066e9`, a monotone transform of `cs_rank(skew_return_last_hour)`) **NOVEL**
- *Does:* buys stocks whose returns inside the last hour were skewed upward.
- *Why:* unknown. Already ruled out: reversal, spike-then-fade, closing institutional flow, jump-risk compensation, microstructure, lottery demand.
- *Main attack:* "it's a data artefact". In thinly traded stocks returns are lumpy and skew just measures the biggest jump. Tested here with trade count, trade size, sign-only and size splits.
- *Literature:* realised skewness (Amaya et al. 2015) finds the opposite sign at a weekly horizon. **Novel.**

**cl5 Current-liabilities share** (5; core `cs_rank(ts_mean(current_liabilities/total_assets, 66))`)
- *Does:* buys firms funded more by short-term liabilities. Very slow.
- *Why (hypothesis):* operating liabilities such as supplier credit are cheap financing used by efficient firms (Nissim-Penman 2003), as opposed to a funding-risk premium.
- *Test:* payables vs short-term borrowings; stress vs calm (the risk-premium reading already failed one check).

**cl4 Wide range on high-volume days** (10; exemplar `search-2870dff1977e`)
- *Does:* shorts stocks whose daily high-low range was unusually wide on a high-volume day.
- *Why (hypothesis):* attention or overreaction on busy days. Big, visible moves attract buyers, and that excess reverts (Barber-Odean 2008; Campbell-Grossman-Wang 1993).
- *Test:* does the volume condition matter? Is it direction-free (volatility) or a reversal?

**cl11 Approaching earnings** (3; exemplar `ndm-6d88434bdd24`)
- *Does:* buys stocks as their next earnings announcement approaches.
- *Why:* the earnings-announcement premium: stocks earn more around their announcements (Beaver 1968; Frazzini-Lamont 2007; Barber et al. 2013). **Same as a known effect**, so it validates the search.
- *Test:* the classic "announcers in the next 5 days" portfolio.

**cl20 Many small trades at the close** (4; exemplar `intraday-w2-sign-correct-trade-count-vs-volume-surprise`, owner's hand-written idea) **NOVEL-ish**
- *Does:* when the last hour has unusually many trades for its volume (small average trade), bets against the last-hour move.
- *Why (hypothesis):* small trades suggest retail-driven moves without information, which revert. Large trades suggest institutions with information, so the move continues.
- *Literature:* retail flow and reversal (Kaniel-Saar-Titman 2008).
- *Test:* reversal when trades are small vs large; small vs big stocks; lag 1.

**cl12 Overnight gap reversal** (7; core `cs_rank(-ts_mean(open/prev_close - 1, 5))`)
- *Does:* bets against stocks that gapped up at the open over the past week.
- *Why (hypothesis):* attention-driven buying at the open overshoots and reverts (Berkman et al. 2012; Lou-Polk-Skouras 2019). News gaps should not revert.
- *Test:* horizon; excluding earnings gaps; up-gaps vs down-gaps.

**cl6 Short-term move x profitability** (6, loose; core `-cs_rank((rank(10d return) - 1.5) x (rank(ROA) - 1.5))`)
- *Does:* a recent rise is shorted in profitable firms and bought in unprofitable ones.
- *Why (hypothesis):* moves without news revert, moves with news continue (Chan 2003). Moves in weak firms are more often news.
- *Test:* reversal among profitable vs unprofitable firms.

**cl8 Intraday reversal, published 101 formula** (11; exemplar `101-alpha-54`)
- *Does:* shorts stocks that closed near the day's high.
- *Why:* classic short-term reversal (Kakushadze 2016, "101 Formulaic Alphas"). Strong 2006-08, faded after. **Known effect that decayed.**
- *Test:* plain close-location version; size; lag 1.

## Predictions (batch 3, 65 Fast jobs, exp FAM)
Built by `seed-jobs/make_batch3.py`; analysis `seed-jobs/analyze_batch3.py`. Gated jobs earn 0 outside their gate, so compare gated pairs with each other. A gap above 0.03 is clear; SE is about 0.017 on the full sample and 0.025 per half.

| family | job | prediction |
|---|---|---|
| cl0 | cl0-rev-ex | exemplar intraday-vr1-vwap-exp22 (Slow 0.100): Fast about 0.10 |
| cl0 | cl0-rev-lag1 | timing: well under half of rev-ex (most of the effect is next-day) |
| cl0 | cl0-rev-slow | cost: lower turnover; IR falls but break-even cost per dollar traded rises |
| cl0 | cl0-rev-big | liquidity provision: big (liquid) stocks weaker than small |
| cl0 | cl0-rev-small | liquidity provision: small stronger than big by > 0.03 |
| cl1 | cl1-ey-ex | exemplar search-688358bcfc87 (Slow 0.090): Fast about 0.09 |
| cl1 | cl1-ey-epsonly | decomposition: earnings vs own history, no price. Earnings-drift story says this carries the effect |
| cl1 | cl1-ey-priceonly | decomposition: price low in its own 1-year range, no earnings. MY PREDICTION: price-only >= eps-only (EPS changes only quarterly) |
| cl1 | cl1-ey-postann | drift story: stronger in the ~4 weeks after an announcement than before the next one (post > pre by > 0.03) |
| cl1 | cl1-ey-preann | below ey-postann if it is post-earnings drift |
| cl1 | cl1-ey-big | no strong prior |
| cl1 | cl1-ey-small | no strong prior; mispricing stories favour small |
| cl2 | cl2-skew-fewtrades | ARTEFACT story (few trades -> lumpy returns): highest of the three trade-count terciles |
| cl2 | cl2-skew-midtrades | between few and many |
| cl2 | cl2-skew-manytrades | ARTEFACT story: near 0. If many-trades keeps most of the IR, the artefact story fails |
| cl2 | cl2-skew-bigtrades | artefact story: large average trade size (lumpier tape) higher |
| cl2 | cl2-skew-smalltrades | artefact story: lower |
| cl2 | cl2-skew-sign | if skew is just the sign of the biggest bar move, the sign alone keeps most of the IR (>= 0.07) |
| cl2 | cl2-skew-big | artefact story: below skew-small |
| cl2 | cl2-skew-small | artefact story: above skew-big |
| cl2 | cl2-skew-csquiet | cross-sectionally quiet stocks higher (batch-1 'quiet' was time-series) |
| cl2 | cl2-skew-csnoisy | lower than csquiet |
| cl2 | cl2-skew-slow3 | cost: lower turnover; one-day effect so IR drops a lot (to about 0.05) |
| cl2 | cl2-la-skew-smallgap | LOOK-AHEAD diagnostic: exploratory; tells whether skew is paid overnight or intraday |
| cl2 | cl2-la-skew-smallintra | LOOK-AHEAD diagnostic: exploratory |
| cl5 | cl5-cl-ex | plain core without the large-cap gate: positive, about 0.05 |
| cl5 | cl5-cl-big | the pool's member gates on large caps: big >= small |
| cl5 | cl5-cl-small | below cl-big |
| cl5 | cl5-cl-payables | operating-liability story (supplier credit, Nissim-Penman 2003): payables carry it, above stdebt by > 0.03 |
| cl5 | cl5-cl-stdebt | financial short-term debt: weaker than payables |
| cl5 | cl5-cl-calm | risk-premium story: calm > stress. MY PREDICTION (it made money in 2008): no clear difference |
| cl5 | cl5-cl-stress | risk-premium story: weak or negative |
| cl4 | cl4-rng-ex | exemplar search-2870dff1977e (Slow 0.071): Fast about 0.07 |
| cl4 | cl4-rng-allvol | overreaction-on-busy-days story: the volume condition matters, so below rng-ex by > 0.03 |
| cl4 | cl4-rng-lowvol | quiet days: lower than rng-ex |
| cl4 | cl4-rng-updays | attention/volatility story (Barber-Odean): same as down days. Reversal story: weaker than down days |
| cl4 | cl4-rng-downdays | see rng-updays. MY PREDICTION: roughly symmetric (it is a volatility signal, not a direction signal) |
| cl4 | cl4-rng-lag1 | smoothed 5-day signal: keeps most of its IR at lag 1 (> 0.04) |
| cl11 | cl11-earn-ex | exemplar ndm-6d88434bdd24 (Slow 0.053): Fast about 0.05 |
| cl11 | cl11-earn-simple | plain version: buy stocks closest to their next announcement; positive |
| cl11 | cl11-earn-eap5 | classic earnings-announcement premium (long announcers within 5 days vs the rest): positive, IR > 0.03 |
| cl11 | cl11-earn-eap10 | wider window: positive, below or near eap5 |
| cl11 | cl11-earn-big | no strong prior |
| cl11 | cl11-earn-small | Frazzini-Lamont: premium larger where attention/volume demand is larger; weak prior small > big |
| cl20 | cl20-frag-ex | exemplar intraday-w2-sign-correct-trade-count-vs-volume-surprise (Slow 0.060): Fast about 0.06 |
| cl20 | cl20-frag-revhi | small-trade (retail) story: last-hour reversal stronger when trades are unusually small (hi > lo by > 0.03) |
| cl20 | cl20-frag-revlo | large trades (institutional): weaker reversal, possibly continuation (< 0) |
| cl20 | cl20-frag-big | retail story: below frag-small |
| cl20 | cl20-frag-small | retail story: above frag-big |
| cl20 | cl20-frag-lag1 | timing: about 0 (one-day effect) |
| cl12 | cl12-gap-ex | plain core of the family (5-day mean gap, reversed): positive, about 0.05 |
| cl12 | cl12-gap-1d | horizon: same-day version (ref overnight-rev 0.012) is weaker than the 5-day mean |
| cl12 | cl12-gap-20d | horizon: 20-day mean also positive (slow-moving overnight pressure) |
| cl12 | cl12-gap-noearn | news story: excluding the ~8 days after earnings (news gaps that should NOT revert) strengthens it (> gap-ex) |
| cl12 | cl12-gap-up | attention story (Berkman et al. 2012): up-gaps revert more than down-gaps (by > 0.03) |
| cl12 | cl12-gap-down | below gap-up |
| cl6 | cl6-qrev-ex | plain core of the family: positive, about 0.06 |
| cl6 | cl6-qrev-all | plain 10-day reversal, no profitability: small |
| cl6 | cl6-qrev-prof | noise story: reversal among PROFITABLE firms is positive |
| cl6 | cl6-qrev-unprof | news story: among UNPROFITABLE firms reversal is negative (moves continue). Interaction real only if prof - unprof > 0.03 |
| cl8 | cl8-irev-ex | exemplar 101-alpha-54 (Slow 0.108): Fast about 0.10 |
| cl8 | cl8-irev-cloc | plain close-location reversal: carries most of it (> 0.07) |
| cl8 | cl8-irev-lag1 | timing: about 0 (one-day effect) |
| cl8 | cl8-irev-big | microstructure story: big weaker than small |
| cl8 | cl8-irev-small | above irev-big |

---

## Batch 3 results (2026-10-11)
Full tables: `seed-jobs/batch3-results.md` (run `seed-jobs/analyze_batch3.py`). IR = daily mean/std. A gap above 0.03 is clear; SE is about 0.017 on the full sample and 0.025 per half.

**Fast-mode warning, found while checking.** Re-running two exemplars in Fast mode reproduced their Slow originals poorly:
- cl0 `rev-ex`: corr 0.52; IR 0.068 Fast vs 0.100 Slow.
- cl20 `frag-ex`: corr 0.51; IR 0.080 Fast vs 0.060 Slow.

The other exemplars matched (cl4 corr 0.94, cl8 1.00). Both mismatches apply time-series operators (`ts_mean_exp`, `ts_zscore`) to last-hour fields; plain last-hour signals matched Slow at 0.99+ in batch 1. So the Fast results for cl0's variants and cl20's tests are provisional until the Slow batch (batch 4) confirms them. The skew tests (cl2) use no time-series operators on intraday fields, so they are reliable in Fast.

### Per family: which predictions held

**cl2 Last-hour skewness (the main novelty): the "data artefact" story fails on 3 of 4 tests.**

| Test | Result | Artefact story predicted | Held? |
|---|---|---|---|
| Heavily traded stocks (top third by trade count) | **0.048** (few-trades third 0.083, middle 0.045) | about 0 | **No**: the effect survives in the most heavily traded stocks |
| Large vs small average trade size (lumpy tape) | **0.023 vs 0.100** | large > small | **Reversed**: the effect lives where trades are *small* |
| Sign of skew only | **-0.010** | keeps most of the IR | **No**: the magnitude matters, not just the direction of the biggest jump |
| Few vs many trades | 0.083 vs 0.048 (+0.035, 2006-13 only) | few > many | Weakly, first half only |

- Also: cross-sectionally quiet stocks 0.111 vs noisy 0.039 (clear in both halves). Small vs big stocks within noise. A 3-day average keeps 0.065.
- Look-ahead diagnostic: paid both overnight and during the next day's session (0.064 vs 0.089, within noise).
- Caveat: average trade size here is in shares, so it also partly sorts by share price (low-priced stocks trade more shares per trade). A dollar trade-size version would remove that.
- **Reading:** skew is not a lumpy-tape artefact of thinly traded stocks. It is strongest in quiet stocks and where trades are small. That links it to cl20, which also points to small trades at the close. Mechanism still open.

**cl20 Many small trades at the close (second novelty).** Provisional (Fast); Slow confirm in batch 4.
- **Prediction held:** last-hour reversal is stronger when the hour's trades are unusually small: 0.068 vs 0.027, +0.041 in **both** halves.
- The exemplar is steady: 0.078 / 0.082 by half. Lag 1: 0.026, so mostly a next-day effect (prediction "about 0" partly held).
- Failed predictions: large trades did not continue (0.027, still positive); small vs big stocks within noise (0.071 vs 0.050).

**cl0 Closing-price reversal.** Provisional (Fast).
- Lag 1 keeps 0.030 of 0.068: mostly next-day.
- Small vs big stocks: no overall difference (prediction small > big **failed**). But by half: big stocks 0.106 -> 0.027, small stocks 0.057 -> 0.056. **The decay happened in large, liquid stocks**, which fits "competed away by electronic liquidity providers". To be confirmed in Slow.
- Slower version: break-even barely changes (4.5 vs 4.2 bps).

**cl1 Earnings yield vs its own history.**
- The ratio matters, not either half: combined 0.099, earnings-only 0.031, price-only 0.012. My prediction (price-only >= earnings-only) **failed** (within noise, other way).
- Stronger in the ~4 weeks after an announcement: 0.080 vs 0.049 (+0.031, but 2006-13 only). That partly supports post-earnings drift.
- No size difference. **Very cheap to trade:** break-even 14 bps.

**cl5 Current-liabilities share.**
- Core 0.050, but almost all of it is recent: 0.016 (2006-13), 0.082 (2014-21).
- Neither payables (0.007) nor short-term borrowings (-0.005) carries it alone: the operating-liability story **failed**.
- **Calm 0.054 vs stress (VIX > 25) 0.006:** it stops working in stress. My prediction (no difference) **failed**; the risk-premium story's prediction held. The earlier "made money in 2008" read was too generous.
- Extremely slow (break-even 47 bps).

**cl4 Wide range on high-volume days.**
- The volume condition matters: 0.072 vs 0.019 on all days and -0.019 on low-volume days. Clear in both halves.
- Up and down days are symmetric (0.064 vs 0.055), as predicted: it is a volatility/attention signal (busy, wide-range days are followed by underperformance whatever the direction), not a reversal.
- Lag 1: 0.011, so a one-day effect despite the 5-day smoothing (my prediction > 0.04 **failed**). Decayed 0.108 -> 0.042.

**cl11 Approaching earnings.**
- The classic earnings-announcement premium portfolio **did not work**: next 5 days 0.009, next 10 days -0.004. My prediction **failed**.
- The family's signal (0.054) and the plain days-to-announcement rank (0.042) work, but not via the announcement window. It is something about where a firm sits in its reporting cycle. Decayed 0.091 -> 0.026.
- **Not a clean known-effect validation.** Do not present it as the earnings-announcement premium.

**cl12 Overnight gap reversal.**
- The 5-day horizon is best (0.038 vs 1-day 0.012, 20-day 0.017).
- **Up-gaps revert, down-gaps do not:** 0.031 vs -0.010, clear in both halves. As predicted by the attention-buying story (Berkman et al. 2012).
- Excluding post-earnings gaps helps slightly (0.049 vs 0.038, within noise; direction as predicted).

**cl6 Short-term move x profitability.**
- The combined signal works (0.090), and plain 10-day reversal is weak (0.031).
- But reversal is the same among profitable and unprofitable firms (0.025 vs 0.022): the noise-vs-news story **failed**. Why the product works is unexplained. Do not present.

**cl8 Intraday reversal (101 formula).**
- A plain close-location reversal reproduces it (0.109 vs 0.106). Lag 1: 0.033, so mostly next-day.
- Decay in both size halves, strongest in big stocks: 0.231 -> 0.015 vs small 0.180 -> 0.030.

### What this means for the story
- **Novelty that held up:**
  - cl2 skew survives the artefact attack.
  - cl20 small-trade reversal held its main prediction in both halves (pending Slow).
  - Both point to the same place: small trades and quiet stocks around the close.
- **Known effects that checked out:**
  - cl12 up-gaps revert (attention buying).
  - cl4 behaves like an attention/volatility effect.
  - cl0 and cl8 are reversal, decaying first in big liquid stocks (cl0 provisional).
- **Failed stories, to report honestly:** the cl11 earnings-announcement premium, the cl5 operating-liability story, the cl6 noise-vs-news story.

## Batch 4: Slow confirmation (2026-10-11)
11 Slow runs of the results that depended on Fast mode, plus 2 Fast runs that measure trade size in dollars. All numbers are in `seed-jobs/batch3-results.md` (columns `ir_slow`, `diff_slow`).

| Claim | Fast | Slow | Verdict |
|---|---|---|---|
| cl20: reversal stronger when trades are small | 0.068 vs 0.027 | **0.071 vs 0.019**; halves 0.070/0.011 and 0.072/0.024 | **Confirmed** |
| cl20 exemplar steady | 0.078 / 0.082 by half | 0.074 / 0.048, positive 11 of 14 years | Steady but weaker than Fast said |
| cl0: decay only in big stocks | big 0.106 -> 0.027, small 0.057 -> 0.056 | big 0.104 -> 0.056, small 0.102 -> 0.077 | **Not confirmed**: both decayed, big slightly more |
| cl2: present in heavily traded stocks | 0.048 | 0.039 (0.049 / 0.033) | Confirmed |
| cl2: small > large trade size (shares) | 0.100 vs 0.023 | 0.094 vs 0.034, both halves | Confirmed |
| cl2: sign alone worthless | -0.010 | 0.012 | Confirmed |
| cl2: quiet stocks strongest | 0.111 | 0.112, positive 15 of 16 years | Confirmed |
| cl2: small > large trade size in **dollars** (Fast) | 0.084 vs 0.044 | n/a | Holds overall, **but only in 2006-13** (+0.109; 2014-21 -0.004). The share-count version partly reflected share price. |

Fast vs Slow correlation was 0.85-0.99 for the gated skew and cl20 tests. It was about 0.5 for the cl0 size splits and the cl20 exemplar, whose Fast numbers should not be used.
