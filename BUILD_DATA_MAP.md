# Build Spec: Alpha Data-Map Catalog

**You are a coding agent. Your job: read the competition's variable metadata file and generate a
two-tier Markdown catalog that a *separate* alpha-research agent will use as its lookup for what
data exists. Write a small, re-runnable script (Python recommended) that produces the output
deterministically, so the catalog can be regenerated whenever the data changes.**

This spec is self-contained. It includes the clustering methodology — do not assume any prior
clustering exists.

---

## 1. Objective & who consumes the output

A downstream research agent generates trading alphas (formulas over these variables) and works
**one cluster/subcluster at a time**. It needs:

- A single always-in-context index of **every** variable, so it knows what exists everywhere and
  can pull a single term from another cluster for a conditioner / neutralizer / interaction.
- A per-cluster file it opens for depth when assigned to that cluster.

So the catalog must be compact, natively readable (Markdown, not raw JSON), and organized by
cluster. Keep exactly the fields defined in §4 — no more. The other metadata fields are noise for
this purpose and must be dropped.

---

## 2. Input

A JSON file (call it `data-distribution.json`) with an `items` array of 255 objects. Each object has
these keys (the catalog uses the bolded keys directly or to derive caveats):

`varname`* , **`groupname`**, **`is_derived`**, **`adjfactor_type`**, **`delay_0`**, **`dimensions`** ("2D"/"1D"),
`value_type`, **`coverage`**, **`update_frequency`** (a number, days between updates), **`empty_value`**,
`lower_bound`, `upper_bound`, `units`, **`data_types`** (Fundamental/Technical/Seasonality/Macro/ETF),
`author`, `birthday`, `num_comments`, **`description`**, **`keywords`**.

(*`varname` is the exact token used in formulas — always preserve it verbatim.)

---

## 3. Clustering methodology

### 3a. Top-level clusters (deterministic, by `data_types` + `groupname`)

Assign each variable to exactly one cluster:

| cluster | rule |
|---|---|
| `price_volume` | `data_types == Technical` AND `groupname` in {`GROUP_backoffice`, `GROUP_backoffice_derived`} |
| `intraday` | `data_types == Technical` AND `groupname == GROUP_intra1` |
| `fundamental` | `data_types == Fundamental` (then subcluster per §3b) |
| `seasonality` | `data_types == Seasonality` |
| `macro` | `data_types` in {`Macro`, `ETF`} |

Expected counts: price_volume 16, intraday 30, fundamental 175, seasonality 18, macro 16 (= 255).

### 3b. Fundamental subclusters (the fundamental family is too big to be one bucket)

Split the 175 fundamental variables into these **9 canonical financial-statement themes**. Classify
each variable into **exactly one** theme by reading its `varname` + `description` + `keywords` and
choosing the best fit. These are semantic categories — use judgment, don't keyword-match blindly.

| theme (file suffix) | covers | approx count |
|---|---|---|
| `cash` | cash, cash & equivalents, cash flow (operating/investing/financing), free cash flow, marketable securities | ~32 |
| `earnings` | EPS, net/operating earnings, earnings growth, EBIT/EBITDA where framed as earnings | ~21 |
| `net_income` | net income, profit/loss lines, income-to-X ratios, margins framed on net income | ~20 |
| `expenses` | operating expenses, COGS, SG&A, interest expense, tax, depreciation/amortization | ~20 |
| `sales` | revenue, sales, top-line growth, sales-per-share, gross-margin-on-sales | ~16 |
| `equity` | shareholders' equity, book value, retained earnings, comprehensive income, equity ratios | ~23 |
| `debt` | total/long/short-term debt, leverage ratios, liabilities, coverage ratios | ~18 |
| `assets` | total/current assets, receivables, inventory, PP&E, intangibles, asset ratios | ~16 |
| `year` | year-over-year / growth / percentage-change variables not tied to one statement line | ~9 |

Counts are sanity targets, not hard constraints — being off by a few is fine, but a wildly
different split (e.g. 100 in one theme) means the classification went wrong; re-check.

**Persist the assignment** to `fundamental_themes.json` ( `{ "<varname>": "<theme>", ... }` ) so the
build is deterministic and the mapping is inspectable/editable. The build script reads this file; it
does **not** re-classify on every run. Do the classification once, then only edit the JSON if a
variable is misfiled.

---

## 4. Per-variable fields

The always-in-context `_INDEX.md` remains compact and emits exactly four columns:

1. **`var`** — the exact `varname`, in backticks. Append ` ⬤` if it is in the 101-covered set (§5c).
2. **`what it is`** — one short line. Take `description`, strip a leading boilerplate opener
   (`This variable represents/provides/indicates/reflects/is/includes/measures `), keep the first
   sentence, trim to ~78 chars with a trailing `…` if longer.
3. **`dim`** — `cross-sec` if `dimensions == "2D"`, else `market-wide`. **Override (§5b):** force
   `market-wide` for every macro/index variable regardless of stored dimension.
4. **`freq`** — bucket `update_frequency` (numeric days): `<=3` → `daily`, `<=40` → `monthly`,
   `<=100` → `quarterly`, else `annual`.
Why these four: `var` is the formula token; `what it is` gives the agent the idea; `dim` tells it
whether the variable can rank stocks (`cross-sec`) or must be interacted (`market-wide`); `freq`
flags step-function / reporting-lag variables.

Cluster files add a fifth **`caveat`** column. Emit semicolon-separated flags only when metadata
changes how a field should be handled; otherwise emit `—`:

- `derived` when `is_derived == 1`.
- `` `delay_0=0`: timing review; do not auto-delay `` when `delay_0 == 0`. This flag does not imply
  any mechanical `ts_delay` transformation.
- `sparse coverage (<N>)` when numeric `coverage < 500`.
- `missing encoded as <value>` when `empty_value` is non-empty.
- `corporate-action adjusted` when `adjfactor_type` is non-empty.
- `forward-filled; underlying cadence is slower` for `GROUP_fred` only.

Keep `units`, bounds, raw coverage above the severe-sparsity threshold, and provenance metadata in
`data-distribution.json` for on-demand inspection rather than expanding the always-visible index.

---

## 5. Rules that MUST be applied (these fix real data traps)

### 5a. Technical split
`GROUP_intra1` is intraday and goes in its own cluster; the 101 alphas never use intraday timing, so
keeping it separate is what surfaces it as opportunity. Do not merge it into price_volume.

### 5b. Macro/index dimension override + forward-fill caveat
Variables in `GROUP_fred`, `GROUP_daily_idx`, `GROUP_daily_idx_derived`, `GROUP_daily_etf_returns`
are single **market-wide** series (one value shared by all stocks) — even though several are stored
as `dimensions == "2D"`. Force their `dim` to `market-wide`. They cannot rank stocks alone; the
research agent must interact them with a stock-level variable or use them to tilt/condition.
FRED observations are forward-filled daily, so `update_frequency` reads ~1 (`daily`) even for
CPI/GDP/unemployment whose true cadence is monthly/quarterly — there is no real day-to-day
information in them. Daily index and ETF fields do contain daily information. Put this distinction
in the macro cluster file's Notes and emit the per-field FRED caveat (see §4 and §6).

### 5c. The 101-covered set (mark with ⬤)
These 13 variables are what Kakushadze's 101 alphas actually use; mark them so the research agent
treats them as picked-over:
`open, high, low, close, volume, mktcap, industry, sector, subindustry, ret1, ret5, ret10, ret20`
(If `vwap` exists in a future data version, add it. `adv` is derived from volume — mark if present.)

---

## 6. Output files & exact format

Create a directory `data-map/` containing `_INDEX.md` and `clusters/<name>.md`.

### File list
```
data-map/
  _INDEX.md
  clusters/price_volume.md
  clusters/intraday.md
  clusters/fundamental_cash.md
  clusters/fundamental_earnings.md
  clusters/fundamental_net_income.md
  clusters/fundamental_expenses.md
  clusters/fundamental_sales.md
  clusters/fundamental_equity.md
  clusters/fundamental_debt.md
  clusters/fundamental_assets.md
  clusters/fundamental_year.md
  clusters/seasonality.md
  clusters/macro.md
```
(Fundamental file names are `fundamental_<theme>.md`. Omit any theme that ends up empty.)

### Variable table formats

The index uses the compact four-column format:
```
| var | what it is | dim | freq |
|---|---|---|---|
| `close` ⬤ | the adjusted closing price of stocks, accounting for corporate actions… | cross-sec | daily |
| `cash_flow_per_share` | net operating cash flow generated per share | cross-sec | quarterly |
| `close_spx` | the closing price of the S&P 500 index | market-wide | daily |
```
Sort rows by `varname`. Use `cross-sec`/`market-wide` and `daily`/`monthly`/`quarterly`/`annual`
exactly (the research agent's prompt keys off these tokens).

Cluster files append `| caveat |` to the header and one caveat cell to every row. Use `—` when no
caveat applies.

### Cluster file layout (`clusters/<name>.md`)
```
# <Title>  (<N> vars)

**Status:** <one line: explored vs open>
**Notes:** <mechanism hints + watch-outs; see below>

⬤ = used by the 101 alphas.

Caveats are emitted only when raw metadata changes how a field should be handled. `delay_0=0`
requests a timing review; it never means to add `ts_delay` automatically.

<the variable table for this cluster>
```
Status + Notes text per cluster:
- **price_volume** — Status: `EXPLORED — all 101 alphas live here.` Notes: use mainly to *combine*
  with another cluster, or as the base signal you transform (neutralize / condition / re-weight /
  re-horizon). Low lookahead risk.
- **intraday** — Status: `Open — 101 never use intraday timing.` Notes: first/last-hour fields;
  close cousin of price/volume, easy to reason about; low lookahead risk.
- **fundamental_\*** — Status: `Open — richest whitespace (only market cap is used by the 101, once).`
  Notes: reporting-lag / lookahead risk — watch the fast-vs-slow gap; quarterly/annual vars behave
  as step-functions (low turnover); cross-sec, so rankable.
- **seasonality** — Status: `Open.` Notes: calendar effects (options-expiry, month/quarter ends,
  FOMC/earnings proximity); low turnover; best as a conditioner/gate on another signal.
- **macro** — Status: `Open — all market-wide (must interact).` Notes: every series is market-wide
  (1D) — cannot rank stocks alone; interact with a stock-level variable or use to tilt/condition;
  FRED observations are forward-filled daily, so CPI/GDP/unemployment carry no true day-to-day
  information, while daily index and ETF series do.

### `_INDEX.md` layout
```
# Alpha Data Catalog — 255 variables

_The full lookup for the research agent. Keep this file in context; open clusters/<file>.md for the
cluster you're working in._

## How to use this
- You work in one cluster/subcluster at a time. Generate the *core* of each alpha from its variables
  (open clusters/<file>.md for depth).
- You MAY pull one term from another cluster for a conditioner, neutralizer, or interaction — keep
  the main signal in your assigned cluster. Every variable is listed below, so a reach-out term
  needs no extra file-open.
- Best novel move: cross two distant clusters in one formula (e.g. price/volume reversal *gated by*
  a seasonality flag). The 101 essentially never do this.
- Columns: dim = cross-sec (varies per stock → rankable) or market-wide (one series → must interact,
  can't rank alone); freq = update cadence (quarterly/annual ⇒ step-function, low turnover,
  reporting-lag risk).
- Cluster files add a caveat column for actionable timing, derivation, coverage, missing-value,
  adjustment, and forward-fill metadata.
- ⬤ marks the ~13 variables the 101 alphas already use — treat as picked-over.

## Clusters at a glance
<table: | file | vars | status |>

## <one section per cluster, in the file-list order above>
### <Title>  (<N>)
<the variable table for that cluster>
```

---

## 7. Validation before you finish

- Total variables across all files == 255; no variable appears in two clusters.
- Cluster counts match §3a (price_volume 16, intraday 30, fundamental 175, seasonality 18, macro 16).
- Every macro-cluster row shows `market-wide` (none `cross-sec`).
- `close`, `open`, `volume` show `freq = daily` (not `—`); if you see `—`, you passed the wrong value
  to the bucketing function — pass `update_frequency`, not the whole record.
- Exactly the 13 covered variables (§5c) carry ⬤.
- `_INDEX.md` is well under ~10k tokens (it should be ~330 lines).

---

## 8. Notes for maintenance
- Re-running the script must reproduce byte-identical output (sort deterministically; read the
  persisted `fundamental_themes.json` rather than re-classifying).
- If the data file gains variables, they flow in automatically except fundamental ones, which need a
  line added to `fundamental_themes.json`.
- The fundamental subclusters are thematic and approximate; they're for "work roughly in this area,"
  not rigid boundaries. A harder grouping (empirical correlation of computed alpha returns) can
  replace §3b later without changing the output format.
