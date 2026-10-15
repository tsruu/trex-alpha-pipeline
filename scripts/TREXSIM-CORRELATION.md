# TrexSim correlation calculations

This documents how to reproduce TrexSim's **Compute Correlation** values from
the legacy archives in `alphas/results/` and generic research archives in
`alphas/research/results/`. The local calculation is intended
to match TrexSim's displayed number, not to choose a different or "ideal"
historical window.

## What is archived

Each ingested run has two relevant files:

```text
alphas/results/101-alpha-NN/slow-ID.json
alphas/results/101-alpha-NN/slow-ID.pnl.csv
```

The JSON contains the run metadata and metrics, including:

- `stats_data.metrics.ir` — used for IR filtering.
- `stats_data.time_period` — the full simulation period.
- `simresdata` — the original daily PNL series.

The CSV is the convenient local input. Its important columns are:

- `date` — ISO date, for example `2020-01-08`.
- `dailypnl` — daily PNL used for the correlation.

Do not use cumulative PNL, the plotted PNG, IR, or the full simulation period
as the correlation input.

## Exact TrexSim-compatible workflow

The browser report supplies two things that must be preserved:

1. The selected TrexSim IDs and their order.
2. The report's inclusive `start_date` and `end_date`.

For the current Slow OS report with `IR >= 0.07`, TrexSim selected 25 IDs and
used:

```text
start_date = 20200108
end_date   = 20211230
```

The corresponding local dates are `2020-01-08` and `2021-12-30`.

Run the reusable local calculator from the repository root:

```bash
python3 scripts/trexsim-correlate-local.py \
  --mode slow \
  --ir-min 0.07 \
  --ids 317051,320045,320749,320805,320837,320883,321227,321360,321410,321426,321457,321495,321502,321515,321518,321550,321631,321694,321727,321771,321804,321924,321948,321991,322072 \
  --start 2020-01-08 \
  --end 2021-12-30 \
  --browser-report-url 'https://www.trexsim.com/trexsim/pysim/compute_correlation?alpha_ids=317051,320045,320749,320805,320837,320883,321227,321360,321410,321426,321457,321495,321502,321515,321518,321550,321631,321694,321727,321771,321804,321924,321948,321991,322072' \
  --output alphas/results/slow-correlation-ir-ge-0.07.json
```

The command writes:

- `alphas/results/slow-correlation-ir-ge-0.07.json` — metadata, selected
  runs, source paths, observation counts, and the numeric matrix.
- `alphas/results/slow-correlation-ir-ge-0.07.matrix.csv` — a square matrix
  with TrexSim IDs as both row and column labels.

For the autoresearch reservoir, use `--source research`. To optimize a pool containing both the
original 101 and new research candidates, use `--source all` and the strict competition IR floor:

```bash
python3 scripts/trexsim-correlate-local.py \
  --source all --mode slow --ir-min 0.07 --ir-strict \
  --start 2020-01-08 --end 2021-12-30 \
  --output alphas/research/slow-correlation.json

python3 scripts/trexsim-optimize-pool.py \
  alphas/research/slow-correlation.json \
  --output alphas/research/optimal-pool.json
```

If the IDs are not already known, the threshold can select all matching
archives automatically:

```bash
python3 scripts/trexsim-correlate-local.py \
  --mode slow \
  --ir-min 0.07 \
  --start 2020-01-08 \
  --end 2021-12-30 \
  --output /tmp/slow-correlation.json
```

For exact parity, prefer passing `--ids` copied from the browser report. This
prevents a later archive or a different list ordering from changing the
selection.

## Calculation

For every pair of selected runs:

1. Load each run's `date -> dailypnl` mapping from its CSV.
2. Take the intersection of the two date sets.
3. Keep only dates between the report's start and end dates, inclusive.
4. Compute ordinary Pearson correlation on the two aligned daily PNL vectors.

For vectors `x` and `y`, the calculation is:

```text
mean_x = average(x)
mean_y = average(y)

correlation =
  sum((x_i - mean_x) * (y_i - mean_y)) /
  sqrt(sum((x_i - mean_x)^2) * sum((y_i - mean_y)^2))
```

The diagonal is a run correlated with itself and should be 1.0. With `n`
selected runs there are `n * (n - 1) / 2` unique off-diagonal pairs. The
current 25-run calculation therefore has 300 unique pairs and 500 aligned
observations per pair.

## Browser-side validation

To obtain the canonical comparison:

1. Open the authenticated Alphas page.
2. Set **Per page** high enough that every target row is visible together
   (the current page supports `items_per_page=200`).
3. Clear stale selections before selecting the target set.
4. Select rows by TrexSim result ID, not by alpha number or expression text.
5. Verify the selected ID set.
6. Click **Compute Correlation**.
7. Save the report URL and read `react-context` from the report page.
8. Use `correlation_matrix.alpha_ids`, `start_date`, `end_date`, and
   `correlation_matrix.values` as the browser reference.

Correlation is read-only: it does not submit or rerun simulations. Keep the
authenticated tab open for the browser reference step, but the local
calculation itself needs no browser.

## Validation rules and common mistakes

- Use `dailypnl`, not cumulative PNL.
- Use the report's window, not the full `stats_data.time_period`.
- Treat the end date as inclusive.
- Use the exact Slow OS archive; do not accidentally pair a `fast-ID` file
  with a Slow OS selection.
- Use result IDs, because alpha numbers and TrexSim IDs are different.
- Clear selections when reusing the Alphas page; selection state can survive
  navigation.
- Allow approximately `1e-12` difference for floating-point comparison.
- A materially larger difference usually means the selected IDs, date window,
  mode, or PNL field differs.
