# The search: how candidate alphas are generated

This describes `scripts/trexsim-search.js` and `scripts/search/grammar.js`. Numbers come from the
run logs of the competition run (about 41,000 evaluations); treat them as that run's, not as defaults.

## Idea

A strongly typed genetic-programming search over small formula trees. "Typed" means every leaf is a
unit-free quantity, and trees combine only through ranks or z-scores, so formulas never mix units.
Variation is by **mutation and selection only**. The code contains a crossover function that is never called.

## Grammar

- **Leaf** = a building block (123 of them, built from about 255 raw fields) + a transform + a window
  (3, 5, 10, 22, 66, 126 or 252 days).
- **Binary nodes:** add or subtract (both sides z-scored first), or multiply.
- **Unary nodes:** negate, smooth, exponential average, signed log.
- **Gate:** one of 12 regimes; when it is off the stock gets no position (`np.nan`, never 0).
- **Size:** fresh trees have 1 to 7 nodes (about 45% are a single leaf); the cap is 9 nodes.
- Every tree renders to a complete Trexsim Python buffer, and an expression-safety check rejects any
  look-ahead (`scripts/trexsim-expression-safety.js`).

## Loop

1. Propose a batch of 24 candidates.
2. Run each on a **Fast** backtest (about 15 seconds).
3. Judge: a **keeper** has |IR| >= 0.065 and correlation <= 0.5 to everything already known.
   A **near-miss** has |IR| >= 0.03. Strongly negative IR is sign-flipped and queued.
4. Update the steering state and repeat. Keepers are later re-run in **Slow** mode by the worker.

Correlation is judged on Fast PnL over 2020-21. A correlated candidate is rejected unless its
IR/sqrt(turnover) is at least 1.3x the other's.

## How candidates are proposed

Settings are 50% fresh trees, 25% mutations of a parent, 20% turnover variants, 5% sums.
(Actual mix over the run: fresh 55%, turnover 24%, mutation 18%, sum 2%, sign flip 1%.)

- **Bandit over data families:** picks 1 of 20 data families, **for fresh trees only** (not the tree itself).
  The reward is a *novel hit* (|IR| >= 0.035 and correlation <= 0.5 to everything known).
  Score = (hits + 1) / (tries + 2) plus an exploration bonus. It is UCB-style, not the textbook version.
- **Block weights** = (novel hits + 1) / (tries + 10): working blocks about 2.0, untried 1.2, failing 0.4.
- **Parents:** draw 40 near-misses, keep the novel ones, take the best of 3 by IR.
- **Caps:** 16 follow-ups per root idea, 20 mutations per parent, 12 turnover variants per hit.

## Statistics to keep in mind

The standard error of a daily IR over about 3,900 days is 1/sqrt(3900) = 0.016, so a keeper at 0.065 is
about 4 standard errors. With roughly 41,000 tries at a one-sided p of about 2e-5, expect about one false
keeper. Fast mode is approximate; only Slow results are submittable.

## Where the outputs go

`alphas/search/` (created at run time): `evals.jsonl`, `archive.json`, `near-misses.json`, `bandit.json`,
`log.txt`, `leaderboard.md`, and `pnl/` (one Fast PnL file per candidate). Stop with `touch alphas/search/STOP`.
