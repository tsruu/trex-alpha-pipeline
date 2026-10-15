#!/usr/bin/env node
// Archive raw TrexSim responses, export PNL CSV, and optionally update alpha markdown.
// Usage: node trexsim-ingest-results.js <results.json> [--archive-only]
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const [resultsFile, ...flags] = process.argv.slice(2);
if (!resultsFile) {
  console.error('Usage: node trexsim-ingest-results.js <results.json> [--archive-only]');
  process.exit(1);
}

const archiveOnly = flags.includes('--archive-only');
const input = JSON.parse(fs.readFileSync(resultsFile, 'utf8'));
const results = Array.isArray(input) ? input : input?.result?.value;
if (!Array.isArray(results)) {
  console.error('Results must be an array or a browser CDP response containing result.value.');
  process.exit(1);
}
const root = path.join(__dirname, '..');
const update = path.join(__dirname, 'trexsim-update-results.js');

function csvCell(value) {
  const text = String(value ?? '');
  return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

function formatPeriod(period) {
  const match = period?.match(/^(\d{4})(\d{2})(\d{2})-(\d{4})(\d{2})(\d{2})$/);
  return match
    ? `${match[1]}-${match[2]}-${match[3]} — ${match[4]}-${match[5]}-${match[6]}`
    : 'n/a';
}

function value(input) {
  return input === undefined || input === null || input === '' ? 'n/a' : String(input);
}

for (const result of results) {
  const nn = String(result.n).padStart(2, '0');
  if (result.error) {
    console.error(`alpha ${nn}: ${result.error}`);
    continue;
  }
  if (!result.raw) {
    console.error(`alpha ${nn}: missing raw response`);
    continue;
  }

  const raw = result.raw;
  const id = String(raw.alpha_id || result.id);
  const mode = raw.is_slow_mode || raw.mode === 'os_slow' ? 'slow' : 'fast';
  const directory = path.join(root, 'alphas', 'results', `101-alpha-${nn}`);
  fs.mkdirSync(directory, { recursive: true });

  const jsonPath = path.join(directory, `${mode}-${id}.json`);
  fs.writeFileSync(jsonPath, `${JSON.stringify(raw, null, 2)}\n`);

  let series = [];
  try {
    const parsed = typeof raw.simresdata === 'string'
      ? JSON.parse(raw.simresdata)
      : raw.simresdata;
    series = parsed?.[0]?.data || [];
  } catch (error) {
    console.error(`alpha ${nn}: cannot parse simresdata: ${error}`);
  }

  const fields = [...new Set(series.flatMap(Object.keys))];
  const csvPath = path.join(directory, `${mode}-${id}.pnl.csv`);
  const rows = [
    ['date', 'timestamp', ...fields.filter(field => field !== 'timestamps')],
    ...series.map(row => [
      row.timestamps ? new Date(row.timestamps * 1000).toISOString().slice(0, 10) : '',
      row.timestamps ?? '',
      ...fields.filter(field => field !== 'timestamps').map(field => row[field] ?? ''),
    ]),
  ];
  fs.writeFileSync(csvPath, `${rows.map(row => row.map(csvCell).join(',')).join('\n')}\n`);
  console.log(`archived alpha ${nn}: ${path.relative(root, jsonPath)} and ${path.relative(root, csvPath)}`);

  if (archiveOnly) continue;

  const mdPath = path.join(root, 'alphas', `101-alpha-${nn}.md`);
  const md = fs.readFileSync(mdPath, 'utf8');
  const label = mode === 'slow' ? 'Slow OS' : 'Fast OS';
  if (new RegExp(`\\| ${label} \\| v1 \\| [^|]+ \\| \\d+ \\|`).test(md)) {
    console.log(`skip markdown alpha ${nn}: ${label} result already recorded`);
    continue;
  }

  const metrics = raw.stats_data?.metrics || {};
  const empty = !metrics.ir || metrics.numstks === '0x0';
  const note = empty
    ? `${label} returned an empty book (no metrics); raw response is archived for review.`
    : `${label} result archived; IR ${metrics.ir} ${Number(metrics.ir) > 0.07 ? 'clears' : 'does not clear'} the 0.07 qualifying bar.`;
  const date = raw.simulated_on?.slice(0, 10) || new Date().toISOString().slice(0, 10);
  const submit = raw.submission_status ? 'submitted' : '';
  execFileSync('node', [
    update,
    String(result.n),
    id,
    formatPeriod(raw.stats_data?.time_period),
    value(metrics.ir),
    value(metrics.tvr),
    value(metrics.dd),
    value(metrics.ret),
    value(metrics.ir_tvr),
    value(metrics.booksize),
    value(metrics.numstks),
    value(metrics.liq),
    value(metrics.liqn),
    value(metrics.region),
    note,
    date,
    mode,
    mode === 'slow' ? String(raw.lookback ?? result.lookback ?? '') : '',
    mode === 'slow' && submit ? submit : '',
  ], { stdio: 'inherit' });
}
