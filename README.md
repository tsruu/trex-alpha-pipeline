# trex-alpha-pipeline

An automated alpha-search and submission pipeline for the Trexquant alpha-generation competition
(Trexsim), plus the methodology and a post-hoc interpretability study of the alpha pool it produced.

This is the **method, not the alphas**: no submitted alpha code, PnL series, simulator results or
alpha formulas are included. The Trexsim field and operator catalogs and the competition tutorial are included because the code reads them; they belong to Trexquant. Everything here is in-sample research on one simulator
(US TOP1000, industry-neutral, delay 0, no costs). Nothing is investment advice.

## What it does

1. **Search.** A strongly typed genetic-programming search (mutation and selection only) builds expressions
   from about 123 building blocks, a window and a transform. A bandit picks which data family to try next.
   Candidates are judged on a Fast backtest (about 15 s). Keepers need |IR| >= 0.065 and correlation <= 0.5
   to what is already known.
2. **Verify.** Keepers are re-run in Slow mode (day by day, the only mode that can be submitted).
   A Slow IR above 0.07 qualifies.
3. **Admit and blend.** An alpha is admitted if its Slow PnL correlation is at most 0.5 with every submitted
   alpha, or its IR/sqrt(turnover) is at least 1.2x each correlated one. Weak but independent signals are
   combined into blends that clear the bar.
4. **Submit.** `scripts/submission/` builds, orders and submits the set.
5. **Interpret.** `research/interpretability/` clusters the pool's ingredients into families by PnL
   correlation and regresses each on 47 known reference factors.

## What is where

| Path | Contents |
|---|---|
| `SEARCH.md` | How the search works: grammar, loop, bandit, caps. Start here |
| `scripts/` | Node and Python tooling: run a backtest, grammar search, triage, factory context, tests |
| `scripts/search/` | The grammar and the search analysis |
| `scripts/composites/` | Slow-run worker, hourly cycle (ingest, pool, mining), blend and packing tools |
| `scripts/submission/` | Build, order, check and submit a set; combined-IR tracker |
| `deploy/` | Optional systemd units for running unattended on a server |
| `101_alphas_trexquant_code.md` | The 101 Formulaic Alphas (Kakushadze 2015) translated to Trexsim code |
| `RESEARCH_CANDIDATE_FORMAT.md`, `BUILD_DATA_MAP.md` | How candidates are stored; how the data catalog is built |
| `data-distribution.json`, `built-in-operators.json`, `operators.md`, `data-map/` | Trexsim's field and operator catalogs, which the grammar reads |
| `Trexquant-Alpha-Generation-Competition.md` | The competition tutorial and rules |
| `research/interpretability/` | Study of the pool: findings, mechanism tests, reference factors, analysis scripts |

## Requirements

- Node.js 18+ and npm; Python 3.10+ with numpy, pandas, scipy, requests (`scripts/composites/requirements.txt`).
- Playwright (installed by `npm install`) for the Trexsim login.
- **A Trexsim account.** The simulator, market data and competition belong to Trexquant. Without an account
  you can read everything and run the offline analysis scripts on your own PnL files, but not run backtests.

## Setup

```bash
git clone <this repo> && cd trex-alpha-pipeline
npm install
python3 -m venv .venv && .venv/bin/pip install -r scripts/composites/requirements.txt
cp .env.example .env          # fill trexsim_username / trexsim_password (git-ignored; never commit)
```

State is created at run time under `alphas/` (git-ignored in your own fork if you wish).

## Running it: locally or on a server

Nothing requires a VM. The same commands work on a laptop (macOS or Linux) and on a server. On macOS,
prefix long runs with `caffeinate -i` so the machine does not sleep. Run each in its own terminal, from the repo root.

```bash
# 1. Search (Fast only, runs until stopped)
npm run search:pilot             # 300-candidate pilot first
npm run search:run               # long run
npm run search:report            # progress;  npm run search:stop  to stop after the current batch

# 2. Worker: Slow runs for keepers and composites
node scripts/composites/sim-queue-worker.js --slow 4 --fast 2
#    stop:  touch alphas/validation/STOP-WORKER   (delete the file before restarting)

# 3. Hourly cycle: ingest results, refresh pool, triage keepers, repack, mine
scripts/composites/cycle-loop.sh
#    stop:  touch alphas/composites/STOP-CYCLE
```

Hand-written candidates use the research loop: `npm run research:validate`, `research:triage`,
`research:summary`; run `npm run research:test` for the tooling tests. Generation-agent context is rebuilt
with `npm run factory:refresh` and checked with `factory:validate` and `factory:check-duplicate`.

To run unattended on a server instead, see `deploy/README.md` (systemd units, a sync timer, stop files).
Only one machine should write run data, whichever you choose.

## Submitting

```bash
python3 scripts/submission/build_set.py       # assemble a set
python3 scripts/submission/quality_order.py   # order weak-to-strong within correlated groups
python3 scripts/submission/subcorr.py         # pairwise correlation check
python3 scripts/submission/combined_ir.py     # combined IR of the pool
node scripts/submission/submit.js             # submit (needs a login)
```

## The interpretability study

`research/interpretability/FINDINGS.md` and `RESEARCH_NOTES.md` describe the method (PCA with a
Marchenko-Pastur noise edge, average-linkage clustering into families, regression on known factors,
pre-registered mechanism tests). The scripts (`s1_*.py` ...) read PnL files you generate yourself.
IR is daily mean over daily standard deviation, not annualised. Positions built from day-t data earn the
close(t) to close(t+1) return.

## Caveats

In-sample, one simulator, no transaction costs; Fast mode is approximate (only Slow results count); several
effects weakened after 2014; family names are descriptive labels, not proven causes.

## Credits

The 101 formulaic alphas are from Z. Kakushadze, "101 Formulaic Alphas" (2015). Papers cited in the notes
are referenced where used.
