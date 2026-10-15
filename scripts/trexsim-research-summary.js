#!/usr/bin/env node
// Summarize the generic alpha-research reservoir by primary cluster.

const fs = require('fs');
const path = require('path');

const jsonOutput = process.argv.includes('--json');
const root = path.resolve(__dirname, '..');
const directory = path.join(root, 'alphas', 'research', 'candidates');
const files = fs.existsSync(directory)
  ? fs.readdirSync(directory).filter(file => file.endsWith('.json')).sort()
  : [];

const candidates = files.map(file => {
  const record = JSON.parse(fs.readFileSync(path.join(directory, file), 'utf8'));
  record.__file = file;
  return record;
});

function number(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function summarize(records) {
  const fastSuccess = records.filter(item => item.runs?.fast?.status === 'success');
  const slowSuccess = records.filter(item => item.runs?.slow?.status === 'success');
  const qualified = records.filter(item => item.status === 'qualified' || item.status === 'submitted');
  const qualifiedIrs = qualified.map(item => number(item.runs?.slow?.result?.ir)).filter(value => value !== null);
  const qualifiedTvrs = qualified.map(item => number(item.runs?.slow?.result?.turnover)).filter(value => value !== null);
  return {
    candidates: records.length,
    roots: records.filter(item => item.lineage?.generation === 0).length,
    families: new Set(records.map(item => item.lineage?.family_id).filter(Boolean)).size,
    potential: records.filter(item => item.status === 'potential').length,
    fast_promoted: records.filter(item => number(item.runs?.fast?.result?.ir) >= 0.05).length,
    fast_success: fastSuccess.length,
    fast_pending: records.filter(item => item.runs?.fast?.status === 'pending').length,
    slow_success: slowSuccess.length,
    slow_pending: records.filter(item => item.runs?.slow?.status === 'pending').length,
    qualified: qualified.length,
    errors: records.filter(item => ['fast_error', 'slow_error'].includes(item.status)).length,
    qualified_avg_ir: qualifiedIrs.length
      ? qualifiedIrs.reduce((sum, value) => sum + value, 0) / qualifiedIrs.length : null,
    qualified_avg_tvr: qualifiedTvrs.length
      ? qualifiedTvrs.reduce((sum, value) => sum + value, 0) / qualifiedTvrs.length : null,
  };
}

const byCluster = new Map();
for (const candidate of candidates) {
  const cluster = candidate.inputs?.primary_cluster || 'unknown';
  if (!byCluster.has(cluster)) byCluster.set(cluster, []);
  byCluster.get(cluster).push(candidate);
}
const clusters = Object.fromEntries(
  [...byCluster.entries()].sort(([left], [right]) => left.localeCompare(right))
    .map(([cluster, records]) => [cluster, summarize(records)])
);
const report = { generated_at: new Date().toISOString(), overall: summarize(candidates), clusters };

if (jsonOutput) {
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
  process.exit(0);
}

const headers = ['Cluster', 'Roots', 'Families', 'Potential', 'Fast+', 'Slow', 'Qualified', 'Pending F/S', 'Errors', 'Avg IR/TVR'];
const rows = Object.entries(clusters).map(([cluster, item]) => [
  cluster, item.roots, item.families, item.potential, item.fast_promoted,
  item.slow_success, item.qualified, `${item.fast_pending}/${item.slow_pending}`, item.errors,
  item.qualified_avg_ir === null ? '-' : `${item.qualified_avg_ir.toFixed(3)}/${item.qualified_avg_tvr.toFixed(3)}`,
]);
rows.push([
  'TOTAL', report.overall.roots, report.overall.families, report.overall.potential,
  report.overall.fast_promoted, report.overall.slow_success, report.overall.qualified,
  `${report.overall.fast_pending}/${report.overall.slow_pending}`, report.overall.errors,
  report.overall.qualified_avg_ir === null
    ? '-' : `${report.overall.qualified_avg_ir.toFixed(3)}/${report.overall.qualified_avg_tvr.toFixed(3)}`,
]);
const widths = headers.map((header, index) => Math.max(
  header.length, ...rows.map(row => String(row[index]).length)
));
const line = row => row.map((value, index) => String(value).padEnd(widths[index])).join('  ');
process.stdout.write(`${line(headers)}\n${line(widths.map(width => '-'.repeat(width)))}\n`);
for (const row of rows) process.stdout.write(`${line(row)}\n`);
