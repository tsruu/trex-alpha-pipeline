#!/usr/bin/env node
// Archive generic research-candidate results and update their reservoir records.
// Usage: node scripts/trexsim-ingest-research-results.js <results.json>

const fs = require('fs');
const path = require('path');
const {
  codeProvenance,
  invalidSimulationReason,
  rebuildReservoir,
} = require('./trexsim-research-state');

const resultsFile = process.argv[2];
if (!resultsFile) throw new Error('Usage: node scripts/trexsim-ingest-research-results.js <results.json>');
const input = JSON.parse(fs.readFileSync(resultsFile, 'utf8'));
const results = Array.isArray(input) ? input : input?.results || input?.result?.value;
if (!Array.isArray(results)) throw new Error('Results must be an array or browser CDP result.value');
const batchProvenance = input?.batch || null;

const root = path.resolve(__dirname, '..');
const candidateRoot = path.join(root, 'alphas', 'research', 'candidates');
const resultRoot = path.join(root, 'alphas', 'research', 'results');

function csvCell(value) {
  const text = String(value ?? '');
  return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

function metric(value) {
  if (value === undefined || value === null || value === '') return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : value;
}

for (const result of results) {
  const candidateId = result.n;
  if (typeof candidateId !== 'string') throw new Error('Generic research result is missing a string candidate ID');
  const recordPath = path.join(candidateRoot, `${candidateId}.json`);
  if (!fs.existsSync(recordPath)) throw new Error(`${candidateId}: no candidate record found`);
  const record = JSON.parse(fs.readFileSync(recordPath, 'utf8'));
  record.runs ||= {};

  if (result.error || !result.raw) {
    const failedMode = result.requested_mode;
    if (!['fast', 'slow'].includes(failedMode)) {
      throw new Error(`${candidateId}: failed result is missing requested_mode`);
    }
    record.runs[failedMode] = {
      status: 'error',
      result: null,
      error: String(result.error || `simulation ended with status ${result.status || 'unknown'}`),
      provenance: {
        ...codeProvenance(record.code, root),
        batch: batchProvenance,
      },
    };
    record.status = `${failedMode}_error`;
    if (failedMode === 'fast') {
      record.runs.slow = { status: 'not_eligible', result: null, error: null };
    }
    fs.writeFileSync(recordPath, `${JSON.stringify(record, null, 2)}\n`);
    process.stdout.write(`recorded ${failedMode} error for ${candidateId}\n`);
    continue;
  }

  const raw = result.raw;
  const id = String(raw.alpha_id || result.id);
  const mode = raw.is_slow_mode || raw.mode === 'os' || raw.mode === 'os_slow' ? 'slow' : 'fast';
  const directory = path.join(resultRoot, candidateId);
  fs.mkdirSync(directory, { recursive: true });

  const jsonPath = path.join(directory, `${mode}-${id}.json`);
  fs.writeFileSync(jsonPath, `${JSON.stringify(raw, null, 2)}\n`);
  let series;
  try {
    const parsed = typeof raw.simresdata === 'string' ? JSON.parse(raw.simresdata) : raw.simresdata;
    series = parsed?.[0]?.data || [];
  } catch (error) {
    series = null;
  }
  const csvPath = path.join(directory, `${mode}-${id}.pnl.csv`);
  if (Array.isArray(series)) {
    const fields = [...new Set(series.flatMap(Object.keys))].filter(field => field !== 'timestamps');
    const rows = [['date', 'timestamp', ...fields], ...series.map(row => [
      row.timestamps ? new Date(row.timestamps * 1000).toISOString().slice(0, 10) : '',
      row.timestamps ?? '',
      ...fields.map(field => row[field] ?? ''),
    ])];
    fs.writeFileSync(csvPath, `${rows.map(row => row.map(csvCell).join(',')).join('\n')}\n`);
  }

  const invalidReason = invalidSimulationReason(raw, series);
  if (invalidReason) {
    record.runs[mode] = {
      status: 'error',
      result: null,
      error: `${invalidReason}; raw response archived at ${path.relative(root, jsonPath)}`,
      provenance: {
        ...codeProvenance(record.code, root),
        batch: batchProvenance,
      },
    };
    record.status = `${mode}_error`;
    if (mode === 'fast') {
      record.runs.slow = { status: 'not_eligible', result: null, error: null };
    }
    fs.writeFileSync(recordPath, `${JSON.stringify(record, null, 2)}\n`);
    process.stdout.write(`recorded invalid ${mode} result for ${candidateId}: ${invalidReason}\n`);
    continue;
  }

  const metrics = raw.stats_data?.metrics || {};
  const run = {
    id,
    ir: metric(metrics.ir),
    turnover: metric(metrics.tvr),
    ir_tvr: metric(metrics.ir_tvr),
    return: metric(metrics.ret),
    mode: raw.mode,
    lookback: metric(raw.lookback ?? result.lookback),
    archive_json: path.relative(root, jsonPath),
    archive_pnl_csv: path.relative(root, csvPath),
  };
  record.runs[mode] = {
    status: 'success', result: run, error: null,
    provenance: {
      ...codeProvenance(record.code, root),
      batch: batchProvenance,
    },
  };
  if (mode === 'fast') {
    const fastIr = Number(run.ir);
    if (fastIr >= 0.05) {
      record.status = 'fast_promoted';
      record.runs.slow = { status: 'pending', result: null, error: null };
    } else if (fastIr >= 0.035) {
      record.status = 'potential';
      record.runs.slow = { status: 'not_eligible', result: null, error: null };
    } else {
      record.status = 'fast_rejected';
      record.runs.slow = { status: 'not_eligible', result: null, error: null };
    }
  } else {
    record.status = Number(run.ir) > 0.07 ? 'qualified' : 'slow_rejected';
  }
  fs.writeFileSync(recordPath, `${JSON.stringify(record, null, 2)}\n`);
  process.stdout.write(`archived ${candidateId}: ${path.relative(root, jsonPath)}\n`);
}

const reservoir = rebuildReservoir(root);
process.stdout.write(`reservoir updated: ${reservoir.members.length} qualified member(s)\n`);
