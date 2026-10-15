# Research Candidate Record Format

New autoresearch alphas use one canonical JSON record per formula:

```text
alphas/research/candidates/<candidate_id>.json
```

The legacy `alphas/101-alpha-NN.md` files remain an immutable archive. Do not use that format for
new candidates. A formula change always creates a new candidate linked through `lineage`; never edit
the code of a candidate that already has a completed run.

## Complete record

```json
{
  "candidate_id": "intraday-vwap-reversal-industry-22d",
  "title": "Industry-neutralized 22-day intraday VWAP reversal",
  "status": "draft",
  "code": "move = (vwap_last_hour - vwap_first_hour) / vwap_first_hour\nalpha = cs_indneut(cs_rank(-ts_mean(move, 22)), industry)",
  "inputs": {
    "primary_cluster": "intraday",
    "primary_variables": ["vwap_first_hour", "vwap_last_hour"],
    "secondary_clusters": ["price_volume"],
    "secondary_variables": ["industry"]
  },
  "metadata": {
    "hypothesis": "Persistent late-session weakness tends to reverse on the following trading day.",
    "neutralized": true,
    "mechanism_classification": "intraday path reversal",
    "persistence_rationale": "Late-session inventory pressure is not fully unwound before the next tradable period.",
    "behavioral_axes": {
      "information_timing": "last hour",
      "economic_behavior": "reversal",
      "horizon": "monthly state",
      "conditioning_state": "none",
      "exposure_treatment": "industry-neutral",
      "expected_turnover": "medium"
    }
  },
  "lineage": {
    "family_id": "intraday-vwap-reversal",
    "root_candidate_id": "intraday-vwap-reversal-base",
    "parent_candidate_id": "intraday-vwap-reversal-base",
    "generation": 1,
    "stage": "full-fan",
    "changes": {
      "window": {"from": 5, "to": 22},
      "neutralization": {"from": "raw", "to": "industry"}
    }
  },
  "required_lookback": 22,
  "slow_lookback_buffered": 27,
  "runs": {
    "fast": {"status": "pending", "result": null, "error": null},
    "slow": {"status": "not_eligible", "result": null, "error": null}
  }
}
```

`code` is the complete TrexSim paste buffer: helper definitions followed by `alpha = ...`. It must
not contain imports. The runner prepends `# Hypothesis: <metadata.hypothesis>` to the submitted Fast
expression. Slow reads that saved Fast expression and therefore preserves the same comment.

## Identity, inputs, and lineage

- `candidate_id`: unique lowercase hyphenated identifier; the filename must match it.
- `title`: concise human-readable description.
- `inputs.primary_cluster`: cluster that owns the core mechanism.
- `inputs.primary_variables`: variables that form the core signal.
- `inputs.secondary_clusters` / `secondary_variables`: external conditioners, interactions, and
  grouping keys. Use empty arrays when there are none.
- `metadata.hypothesis`: concise economic claim being tested.
- `metadata.neutralized`: boolean describing the submitted code, not the intended idea.
- `metadata.mechanism_classification`: explicit economic mechanism, not merely an operator name.
- `metadata.persistence_rationale`: why the information should remain predictive until the next
  tradable period.
- `metadata.behavioral_axes`: generation-time coverage descriptors for information timing,
  economic behavior, horizon, conditioning state, exposure treatment, and expected turnover.
  These fields support mechanism planning but never substitute for measured PNL correlation.
  Existing historical records may omit this object; new roots and variants should include it.
- `lineage.family_id`: stable identifier shared by the root and every variant.
- `lineage.root_candidate_id`: original candidate in the family.
- `lineage.parent_candidate_id`: immediate source candidate, or `null` for the root.
- `lineage.generation`: `0` for a root, then parent generation plus one.
- `lineage.stage`: `base`, `potential-rescue`, `full-fan`, or `manual`.
- `lineage.changes`: machine-readable description of what changed from the parent. Use `{}` for a
  root. A variant should change a small number of explicit axes rather than silently rewriting the
  mechanism.

To find a candidate's children, scan records whose `lineage.parent_candidate_id` equals its ID. To
find siblings, scan the shared `lineage.family_id`. Never infer family relationships from names.

## Candidate lifecycle

Top-level `status` is one of:

```text
draft
fast_error
fast_rejected
potential
fast_promoted
slow_error
slow_rejected
qualified
submitted
```

After Fast ingestion the tooling assigns:

- `fast_error` when submission/execution fails or TrexSim returns an invalid result such as blank
  IR, a `0x0` stock book, or no daily-PNL series. The raw response is archived when available.
- `fast_rejected` for Fast IR < 0.035.
- `potential` for 0.035 <= Fast IR < 0.05. The agent may create one bounded rescue fan; the
  original candidate is not Slow-eligible.
- `fast_promoted` for Fast IR >= 0.05, and marks Slow `pending`.

After Slow ingestion it assigns `qualified` only for Slow IR > 0.07; otherwise `slow_rejected`.
Competition submission is separate and may later change `qualified` to `submitted`.

Each `runs.fast` / `runs.slow` envelope has:

```json
{
  "status": "pending",
  "result": null,
  "error": null
}
```

Run status is `pending`, `not_eligible`, `success`, or `error`. A successful result is stored inside
`result`; infrastructure failures are recorded in `error`, so `null` never ambiguously means both
pending and failed. After an attempted run, the envelope also has `provenance`: SHA-256 hashes of
the complete candidate buffer and its pre-`alpha` prefix, the Git commit when this workspace is a
checkout (otherwise `null`), and the batch mode, manifest hash, size, and timestamp. The complete
buffer hash covers every inline helper, so no separate helper registry hash is needed.

## Successful run result

```json
{
  "status": "success",
  "result": {
    "id": "123456",
    "ir": 0.081,
    "turnover": 0.74,
    "ir_tvr": 0.094,
    "return": 0.061,
    "mode": "os",
    "lookback": 27,
    "archive_json": "alphas/research/results/intraday-vwap-reversal-industry-22d/slow-123456.json",
    "archive_pnl_csv": "alphas/research/results/intraday-vwap-reversal-industry-22d/slow-123456.pnl.csv"
  },
  "error": null
}
```

The archived raw JSON remains the source for simulation date/window, drawdown, booksize, stock
count, liquidity, region, and simulator configuration. Do not duplicate those fields in the compact
candidate record.

## Durable reservoir

Every result ingestion atomically rebuilds `alphas/research/reservoir.json`. It is a derived,
machine-readable index containing all candidates whose status is `qualified` or `submitted`, their
Slow run and PNL archive paths, and current code provenance. The individual candidate records are
the source of truth; do not hand-edit the reservoir. Downstream clustering and pool optimization
may add their own artifacts, but cluster assignment, scaling, and decorrelation values are absent
or `null` until those stages actually run.

The reservoir is intentionally broader than the submission frontier. Correlation never changes a
Slow passer back to a rejected status. A separate optimized-pool artifact records which qualified
candidates can currently coexist and in which order.

## Fast behavioral analysis

After a bounded root Fast batch, use archived Fast daily PNL to measure behavior before allocating
rescue and full-fan work. The primary iterative comparison is within the active cluster. A secondary
check compares promising representatives with the corresponding Fast runs of the actual
submitted/selected global frontier.

Do not use every qualified reservoir member as a blocker: many qualified candidates are mutually
incompatible and will never be selected together. Evaluate candidates jointly with the same
correlation/quality logic as the final pool optimizer.

The existing correlation tool accepts Fast archives and explicit TrexSim IDs:

```bash
python3 scripts/trexsim-correlate-local.py \
  --source all --mode fast --ids <comma-separated-fast-ids> \
  --start 2020-01-08 --end 2021-12-30 \
  --output alphas/research/<cluster>-fast-correlation.json
```

Keep Fast analysis artifacts distinct from the canonical Slow matrix. Fast correlation guides
variant allocation; Slow correlation provides final submission evidence. Record the active cluster,
candidate IDs, frontier IDs, window, behavioral clusters, and the reason each family did or did not
receive follow-up budget in the campaign notes or accompanying analysis report.

## Running candidates

Validate records and inspect the pending manifests without modifying them:

```bash
node scripts/trexsim-research-manifest.js fast
node scripts/trexsim-research-manifest.js slow
```

Execute pending candidates through the authenticated persistent runner:

```bash
node scripts/trexsim-run.js research-fast
node scripts/trexsim-run.js research-slow
```

An optional comma-separated candidate-ID argument restricts either command. Fast emits candidates
whose Fast run is `pending`. Slow emits only candidates with Fast IR >= 0.05 whose Slow run is
`pending`. Raw responses and daily PNL are archived under
`alphas/research/results/<candidate_id>/`.

## Campaign, reporting, and final-pool optimization

Initialize and maintain the resumable cluster sweep:

```bash
node scripts/trexsim-research-campaign.js init
node scripts/trexsim-research-campaign.js set intraday generate_roots "Create 40 intraday roots"
node scripts/trexsim-research-campaign.js sync
node scripts/trexsim-research-campaign.js show
```

Summarize lifecycle counts and qualified Slow metrics by cluster:

```bash
node scripts/trexsim-research-summary.js
node scripts/trexsim-research-summary.js --json
```

Build a combined legacy + research Slow correlation matrix and select a maximum valid pool:

```bash
python3 scripts/trexsim-correlate-local.py \
  --source all --mode slow --ir-min 0.07 --ir-strict \
  --start 2020-01-08 --end 2021-12-30 \
  --output alphas/research/slow-correlation.json

python3 scripts/trexsim-optimize-pool.py \
  alphas/research/slow-correlation.json \
  --output alphas/research/optimal-pool.json
```

> **Window vs submission correlation.** `--start 2020-01-08 --end 2021-12-30` gives *window* correlation (TrexSim's Compute Correlation report). The Submit gate uses *full-history* correlation; check any list you intend to submit with `python3 scripts/submission/subcorr.py --check <file>`.


The optimizer selects a maximum-cardinality compatible subset of eligible Slow alphas, writes a
valid weak-to-strong submission order, and emits JSON plus Markdown reports. Its default analysis
assumes the eligible pool may be rebuilt in that order; it does not model an immutable existing
submission prefix. Manifest validation also checks parent/root/family/generation links and lifecycle
consistency across candidate records.
