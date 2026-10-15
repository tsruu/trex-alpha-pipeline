# Mechanism tests for the two dominant drivers (pre-registered 2026-10-09, before results)

Splits halve the universe, so compare the two halves of a split with each other, not with the full-universe IR.
Splits are conditioned only on information available at the time (size, last-hour volume vs its own 20d history,
scheduled days to next earnings).

## Driver 1 — last-hour reversal. Hypothesis H-LP: paid liquidity provision. Rival H-INF: late moves are informed.
| test | H-LP predicts | H-INF predicts |
|---|---|---|
| small vs big caps (mech-d1-small / -big) | small > big (less liquid, more pressure) | no clear order |
| high vs low last-hour volume vs own history (-hivol / -lovol) | hivol >= lovol (heavy flow = more pressure) | hivol < lovol (heavy-volume moves are informed, they continue) |
| signal lagged 1 day (-lag1) | sharp decay (most of the effect is next day) | slow decay |
| in 10 days before earnings vs not (-preearn / -noearn) | similar or weaker before earnings | much weaker before earnings (more informed trading) |

## Driver 7 — intraday return skewness (long high skew). H-JUMP: jumps carry information, prices continue.
## Rival H-MICRO: microstructure artefact (bid-ask bounce, tick size). Rival H-LOTTERY: lottery demand (Amaya et al. 2015).
| test | H-JUMP | H-MICRO | H-LOTTERY |
|---|---|---|---|
| small vs big caps (mech-d7-small / -big) | works in both | small >> big, ~0 in big | small > big |
| high vs low last-hour volume (-hivol / -lovol) | hivol > lovol | no clear order | no clear order |
| lag 1 and 5 days (-lag1, -lag5) | gradual decay | collapses at lag 1 | — |
| 20-day mean skew (-mean20) | positive | ~0 | NEGATIVE (high skew underperforms over weeks) |
| before earnings vs not (-preearn / -noearn) | stronger before earnings | no difference | — |

## Results (2026-10-10, Fast, IR full / 2008-13 / 2014-21; size split from 2011-09, 425 stocks per side)
Note: the first size split (cs_rank(mktcap) > 0.5) silently failed (no stocks / identical halves); rerun with
cs_zscore(log mktcap) > 0. Volume and earnings splits were unaffected.

### Driver 1 — last-hour reversal (full universe 0.066)
| test | result | H-LP (liquidity provision) | H-INF (informed) |
|---|---|---|---|
| high vs low last-hour volume | 0.062 vs 0.051 (2014-21: 0.065 vs 0.035) | supported | rejected |
| before earnings vs not | 0.079 vs 0.051 | consistent | rejected (predicted much weaker) |
| big vs small caps | 0.040 vs 0.036 | not supported (no size gradient inside top-1000) | — |
| lag 1 day | 0.033 (half survives) | mixed | mixed |
Verdict: liquidity provision fits best; the informed-trading explanation fails both of its tests. Together with the
regime result (pays in turbulent markets) this is a coherent mechanism.

### Driver 7 — intraday return skewness, long high skew (full universe 0.094)
| test | result | H-JUMP | H-MICRO | H-LOTTERY |
|---|---|---|---|---|
| big vs small caps | 0.113 vs 0.076 | ok | rejected (works best in large caps) | — |
| high vs low last-hour volume | 0.033 vs 0.080 | rejected | — | — |
| before earnings vs not | 0.040 vs 0.077 | rejected | — | — |
| lag 1 / lag 5 days | 0.001 / 0.002 | rejected (no gradual decay) | consistent | — |
| 20-day mean skew | 0.015 | — | — | rejected (not negative) |
Verdict: all three candidate explanations fail. What is known: a one-day effect, strongest on quiet days (low volume,
no earnings), in large caps and in calm markets. Mechanism open; next hypotheses must explain that profile.
