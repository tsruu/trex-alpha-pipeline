# TrexSim local pipeline

These scripts keep the authenticated TrexSim tab as the only privileged step. Code does the rest: select IDs, fetch JSON, write CSV, and fill markdown.

## Compact alpha-factory context

Refresh the deterministic generation-agent package from authoritative research state, operator and
data catalogs, the legacy frontier, and live candidate records:

```bash
node scripts/trexsim-refresh-factory-context.js
```

Validate syntax, source hashes, reproducibility, live-only paths, and metric provenance:

```bash
node scripts/trexsim-validate-factory-context.js
```

The full `attempt-index.jsonl` is machine memory and should not be loaded into an agent prompt.
Agents read the bounded `attempt-summary.json`, then every proposed candidate is checked against the
full index before acceptance:

```bash
node scripts/trexsim-check-factory-duplicate.js path/to/candidate.json
```

## Files

- `trexsim-fetch-existing.js`
  Reads Fast OS IDs from `alphas/101-alpha-NN.md` and builds a **read-only** fetch. It never submits or reruns.
- `trexsim-build-fast-batch.js`
  Builds a pending Fast OS batch from alphas whose markdown still has no Fast OS ID.
- `trexsim-api-batch.js`
  Builds a **submit + poll + summary** Fast OS run for that pending batch.
  Submissions are spaced to respect TrexSim's interval limit; the pool controls overlapping workers.
- `trexsim-build-slow-batch.js`
  Builds a pending Slow OS manifest from Fast IDs and each alpha's buffered Slow OS lookback.
  It skips alphas that already have a Slow OS ID.
- `trexsim-api-slow-batch.js`
  Builds a **submit + poll + summary** Slow OS run inside the authenticated tab.
  It uses `mode=os`, the existing Fast ID and expression, and defaults to one worker.
- `trexsim-fetch-ids.js`
  Builds a read-only fetch for explicit `{n, id}` results produced by `trexsim-api-batch.js`.
- `trexsim-ingest-results.js`
  Saves `alphas/results/101-alpha-NN/<fast|slow>-<id>.json` and `.pnl.csv`.
  If a Fast or Slow OS result is not already in the markdown, it writes that block from the JSON.
- `trexsim-correlate-local.py`
  Computes a TrexSim-compatible Pearson correlation matrix from archived
  `dailypnl` CSVs, using the exact browser report IDs and date window.
- `build-data-map.py`
  Deterministically builds `data-map/` from `data-distribution.json` and
  `fundamental_themes.json`. It writes the catalog index and cluster files.
- `TREXSIM-CORRELATION.md`
  Detailed local and browser-assisted correlation SOP.

## Typical use

1. Keep one logged-in TrexSim tab.
2. Fetch existing results, then ingest with `--archive-only` so completed markdown is not rewritten.
3. Later, run the pending Fast OS batch and save its summary JSON.
4. Use `trexsim-fetch-ids.js` with that summary, then ingest the fetched JSON without `--archive-only`.

For Slow OS:

1. `node scripts/trexsim-build-slow-batch.js [alpha-numbers-csv] > /tmp/trex-slow-pending.json`
2. `node scripts/trexsim-api-slow-batch.js /tmp/trex-slow-pending.json 1`, then evaluate the expression in the authenticated tab and save its summary JSON.
3. Use `trexsim-fetch-ids.js` with the summary, then ingest without `--archive-only`.

Slow OS is simulation-only here; competition submission is a separate, explicit step.

For correlation after results are archived:

1. Use the authenticated Alphas page to select the exact result IDs and click
   **Compute Correlation**.
2. Record the report's `alpha_ids`, `start_date`, and `end_date`.
3. Run `trexsim-correlate-local.py` with those IDs and the converted
   `YYYY-MM-DD` dates.
4. Compare the local matrix with the browser matrix, allowing only
   floating-point noise.

## Persistent local runner

For model-driven Fast and Slow OS runs without Cursor browser tools, install
the runner once:

```bash
npm install
npx playwright install chromium
[ -f .env ] || cp .env.example .env
```

Set `trexsim_username` and `trexsim_password` in `.env`. The first run opens
an automation-owned browser and signs in when its persistent profile has no
valid session. Later runs reuse `.trexsim-browser/`.

```bash
# Run pending Fast OS simulations for alphas 6 and 12.
node scripts/trexsim-run.js fast 6,12

# Run pending Slow OS simulations for those same alphas.
node scripts/trexsim-run.js slow 6,12
```

Omit the numbers to run every pending alpha for the selected mode. The command
prints one JSON object to stdout with result IDs and metrics. It never invokes
competition submission. A local lock prevents two model calls from driving the
same profile or submitting concurrently.

See `TREXSIM-CORRELATION.md` for the complete procedure and the current
25-run `IR >= 0.07` example.

## Generic research candidates

New autoresearch candidates are separate from the fixed 101-alpha archive. Their JSON record
format is documented in `RESEARCH_CANDIDATE_FORMAT.md`. Place records under
`alphas/research/candidates/`, then run:

```bash
node scripts/trexsim-run.js research-fast
node scripts/trexsim-run.js research-slow
```

The generic runner archives raw responses and daily PNL under `alphas/research/results/` and updates
each candidate record with Fast/Slow metrics, turnover, archive paths, lifecycle state, and explicit
errors. Each attempted run records code and batch provenance. Ingestion atomically rebuilds
`alphas/research/reservoir.json` from all qualified/submitted candidate records; the candidate files
remain the source of truth. Candidate records also carry titles, input inventories, and
root/parent/family lineage as defined in `RESEARCH_CANDIDATE_FORMAT.md`. The Fast manifest adds the
one-line hypothesis as a Python comment above the submitted formula; Slow inherits the same saved
expression. Run Slow only once after Fast iteration is complete, and only for candidates with Fast
IR at least 0.05.

Fast submission stops opening new simulations after five consecutive submission, runtime, or
invalid-output failures; already-running workers finish, and candidates skipped by the circuit
breaker remain pending for a later run. Set `TREXSIM_FAST_ERROR_LIMIT` to another positive integer
only when deliberately changing that guardrail. Blank/non-numeric IR, a `0x0` stock book, or a
missing daily-PNL series is archived and recorded as `fast_error`, not as a low-IR rejection.

The runner polls TrexSim internally and returns the completed batch, so callers should treat the
whole batch as one job. Do not externally monitor or process individual alpha completions. Estimate
total wall time from recent observed timings, the manifest count, submission/runtime variance, and
the configured worker pool. Fast uses four workers by default, so estimate it in
`ceil(run_count / pool_size)` waves. Slow uses one worker in the intended research setup and is
therefore sequential. The research agent must not increase `TREXSIM_SLOW_POOL` unless the human
explicitly requests it.

Launch the direct runner command once in the foreground, retain its process/session, and make only a
few coarse checks of that same session: normally near one third, two thirds, and then the full
estimated duration (for example, every 30 minutes for an approximately 90-minute batch). Use the
same batch-level policy for Fast; do not wake after every run or worker wave. Process all results only
after the runner finishes. Do not use `nohup`, a shell wrapper, background execution, or a separate
watcher by default, because the direct command is the expected allowlisted path. Never launch a
duplicate runner while the original session is active. Timings are scheduling estimates, not failure
timeouts; if a batch runs long, continue checking the same session with increasing backoff.

Campaign and reporting commands:

```bash
node scripts/trexsim-research-campaign.js init
node scripts/trexsim-research-campaign.js show
node scripts/trexsim-research-campaign.js sync
node scripts/trexsim-research-summary.js
```

Run the focused local checks with `npm run research:test`; validate all candidate records and
lookahead guardrails with `npm run research:validate` before a Fast batch.

The correlation calculator accepts `--source legacy`, `--source research`, or `--source all`.
After producing a combined Slow matrix, `trexsim-optimize-pool.py` finds a maximum-cardinality
valid subset, orders it by IR/sqrt(TVR), replays every correlation/override admission, and writes
JSON plus Markdown reports.

To regenerate the alpha data catalog:

```bash
python3 scripts/build-data-map.py
```

## Fast triage and the Slow queue (v3)

After every Fast ingestion (and after the morning Slow ingestion) run:

```bash
python3 scripts/trexsim-fast-triage.py            # or: npm run research:triage
python3 scripts/trexsim-fast-triage.py --dry-run  # print the summary only
```

It buckets Fast results against the selected frontier, groups PNL neighborhoods, applies the Slow
gate, lists variant seeds, and writes `alphas/research/slow-queue.json` plus
`alphas/research/triage/latest-summary.md`. When the queue file exists,
`node scripts/trexsim-run.js research-slow` runs exactly the queued candidates, in priority order,
up to the nightly cap. Delete the queue file to fall back to the old `Fast IR >= 0.05` gate.

## Waiting for a Slow batch

Launch the Slow runner in the foreground piped through `tee alphas/research/logs/slow-<stamp>.log`
(background launches get killed by agent harnesses). If the tool returns control while it runs, wait with
`node scripts/trexsim-wait.js --mode slow --runs <N> --max-minutes <M>`. Each call blocks until the
batch finishes or M minutes pass, polling the runner lock every 30 s inside the process; pass
`--checkpoints` to also return at 1/3, 2/3 and 100% of the ETA. Exit 0 finished, 10 still running, 3 stale lock.

## Formula search (pilot)

`scripts/trexsim-search.js` generates unit-free random formulas from `scripts/search/grammar.js`
(124 building blocks across price/volume, intraday, fundamentals and earnings timing, plus 12
macro/season/size gates) and runs them through the Fast API, about 700 per hour. No LLM is involved.

```bash
npm run search:pilot     # 300 random formulas, stratified across 20 families (~25-30 min)
npm run search:report    # progress at any time
npm run search:analyze   # hit rates by family/shape and how many distinct PnL regions the hits form
npm run search:stop      # graceful stop after the current batch
```

Outputs live in `alphas/search/`: `log.txt` (one line per batch plus every keep/reject), `status.json`,
`leaderboard.md`, `evals.jsonl` (every formula and result), `pnl/` (PnL of every |IR| >= 0.03 result) and
`pilot-report-<tag>.md`. Positive results with Fast IR >= 0.05 that are not near-copies of the pool
are written as `search-<hash>` candidate records, so triage and the Slow queue pick them up.
The search holds the runner lock, so it cannot run at the same time as `research-fast`/`research-slow`.
It runs headless by default (`TREXSIM_HEADLESS=0` to watch it).

### Continuous mode

```bash
caffeinate -i npm run search:run   # runs until stopped; keeps the Mac awake
```

Each batch: ~45% fresh random formulas (bandit rewards hits in new PnL regions), ~25% turnover and
window variants of hits (aimed at higher IR/sqrt(turnover), so correlated versions can climb the
1.2x ladder), ~20% mutations of near-misses that sit in empty regions, ~10% composites of 2-3
uncorrelated near-misses. Once a night between 05:00 and 12:00 local time (IST on the Mac) it pauses, runs triage,
the Slow queue, the correlation rebuild, the pool optimizer and a factory refresh, then resumes
against the updated pool. `npm run search:report` shows totals, per-origin yield and the last Slow
cycles (pool size before -> after); `alphas/search/slow-cycle.log` has the full nightly output.
