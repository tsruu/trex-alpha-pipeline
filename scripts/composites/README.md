# Composite packing tools (2026-09-24)

## Running it (three terminals, repo root)

1. Search (Fast): `caffeinate -i npm run search:run` — restart it after pulling the submit-gate change.
2. Worker (all Slow/Fast composite runs): `caffeinate -i node scripts/composites/sim-queue-worker.js --slow 4 --fast 2`
   Stop: `touch alphas/validation/STOP-WORKER` (delete the file before restarting).
3. Cycle every hour: `caffeinate -i scripts/composites/cycle-loop.sh` (needs `pip3 install numpy pandas`).
   Stop: `touch alphas/composites/STOP-CYCLE`. Log: `alphas/composites/cycle.log`.

All submitters share `scripts/submit-gate.js` so submissions stay > 2 s apart.

## Older research scripts

For the Python HTTP queue and interpretability reference runs, install the local dependencies
from the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r scripts/composites/requirements.txt
python3 research/interpretability/run_ref.py 900
```

`run_ref.py` uses `.venv` automatically when the invoking Python lacks its dependencies.
It processes only `REF` jobs, prints progress, and exits once they finish or the time budget expires.
Results and PnL CSVs are saved in `alphas/validation/REF/`; reruns resume submitted jobs without
resubmitting completed ones. Credentials come from the root `.env` file.

Research code from the meta-strategy validation. See the last section of `ALPHA_RESEARCH_LESSONS.md`.

- `library.py` builds `alphas/composites/library.pkl`: every Slow result with PnL (code, lookback, IR,
  Slow PnL, Slow runtime). Re-run it after new Slow results; paths inside the pickle are absolute.
- `pack3.py --bar 0.095 --corr 0.42 --maxsecs 1200 --exclude 101-alpha-41 --out packed3.json` packs
  composites against the pool in `alphas/research/optimal-pool.json` plus `committed.json`.
- `compose.py` renders composites: `composite3()` (per-component lookback slicing in Slow; use this),
  `composite()` (plain), `UNIT2`/`composite2()` (industry-median unit for dollar-valued components).
- `tq.py` is a resumable HTTP queue (tick-based); `sim-queue-worker.js` is the long-running Node
  equivalent for the Mac:
  `caffeinate -i node scripts/composites/sim-queue-worker.js --slow 1 --fast 0 --stop-at 23:20`
  (UTC; stops before the search's 05:00 IST Slow cycle). Create `alphas/validation/STOP-WORKER` to stop it.
- `anaA.py <exp> <fast|slow>` compares realized composite PnL with the PnL-sum estimate;
  `anaB.py` checks time-partition pieces; `regions.py`, `resid.py`, `fundcheck.py`, `partition.py`,
  `partlib.py` are the offline analyses behind the lessons section.
