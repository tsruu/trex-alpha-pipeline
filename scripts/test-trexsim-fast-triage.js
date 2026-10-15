#!/usr/bin/env node
// Synthetic end-to-end check: Fast triage buckets + Slow gate + queue-driven Slow manifest.

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');

const root = fs.mkdtempSync(path.join(os.tmpdir(), 'trexsim-triage-'));
const scripts = __dirname;
const write = (file, value) => {
  const target = path.join(root, file);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, typeof value === 'string' ? value : `${JSON.stringify(value, null, 2)}\n`);
};

let seed = 12345;
const rand = () => { seed = (seed * 1103515245 + 12345) % 2147483648; return seed / 2147483648 - 0.5; };
const days = Array.from({ length: 200 }, (_, i) => new Date(Date.UTC(2020, 1, 1) + i * 86400000).toISOString().slice(0, 10));
const noise = () => days.map(() => rand());
const F = noise(); const G = noise(); const H = noise(); const K = noise();
const mix = (base, eps) => base.map(v => v + eps * rand());
const csv = series => `date,timestamp,dailypnl\n${days.map((d, i) => `${d},0,${series[i]}`).join('\n')}\n`;

write('alphas/factory/state.json', { budgets: { slow: { nightly_cap: 3 } } });
write('alphas/factory/master-frontier.json', {
  legacy_selected_baseline: [{ id: '900', name: '101-alpha-99', source_category: 'legacy', slow_ir: 0.09, ir_sqrt_turnover: 0.08 }],
  current_live_research_candidates: [], fixed_already_submitted_prefix: [],
});
write('alphas/results/101-alpha-99/slow-900.json', { expression: 'alpha = X' });
write('alphas/results/101-alpha-99/fast-800.json', { expression: 'alpha = X' });
write('alphas/results/101-alpha-99/fast-800.pnl.csv', csv(F));

function candidate(id, { fastIr, q, series, code, slow }) {
  const pnl = `alphas/research/results/${id}/fast-${id}.pnl.csv`;
  write(pnl, csv(series));
  const promoted = fastIr >= 0.05;
  const status = slow ? (slow > 0.07 ? 'qualified' : 'slow_rejected') : promoted ? 'fast_promoted' : 'potential';
  write(`alphas/research/candidates/${id}.json`, {
    candidate_id: id, title: id, status, code,
    required_lookback: 6, slow_lookback_buffered: 11,
    inputs: { primary_cluster: 'test', primary_variables: ['close'], secondary_clusters: [], secondary_variables: [] },
    metadata: { hypothesis: `hypothesis ${id}`, neutralized: false },
    lineage: { family_id: id, root_candidate_id: id, parent_candidate_id: null, generation: 0, stage: 'base', changes: {} },
    runs: {
      fast: { status: 'success', result: { id: `f-${id}`, ir: fastIr, turnover: 1, ir_tvr: q, archive_pnl_csv: pnl }, error: null },
      slow: slow
        ? { status: 'success', result: { id: `s-${id}`, ir: slow, turnover: 1, ir_tvr: slow }, error: null }
        : { status: promoted ? 'pending' : 'not_eligible', result: null, error: null },
    },
  });
}

const ts = 'alpha = ts_mean(close, 5)';
const flat = 'alpha = close / open';
candidate('a-new', { fastIr: 0.08, q: 0.08, series: G, code: ts });
candidate('b-ladder', { fastIr: 0.1, q: 0.12, series: mix(F, 0.2), code: ts });
candidate('c-dead', { fastIr: 0.08, q: 0.08, series: mix(F, 0.2), code: ts });
candidate('d-static', { fastIr: 0.06, q: 0.06, series: K, code: flat });
candidate('e-potential', { fastIr: 0.047, q: 0.047, series: H, code: ts });
candidate('f-potential-low', { fastIr: 0.04, q: 0.04, series: noise(), code: ts });
candidate('g-dead-batch', { fastIr: 0.079, q: 0.079, series: mix(G, 0.2), code: ts });
candidate('h-done', { fastIr: 0.09, q: 0.09, series: noise(), code: ts, slow: 0.08 });

execFileSync('python3', [path.join(scripts, 'trexsim-fast-triage.py'), '--root', root], { stdio: 'pipe' });
const queue = JSON.parse(fs.readFileSync(path.join(root, 'alphas/research/slow-queue.json'), 'utf8'));
const order = queue.entries.map(e => `${e.tier}:${e.candidate_id}`);
assert.deepStrictEqual(order, ['1:a-new', '2:b-ladder', '4:e-potential', '5:c-dead', '5:g-dead-batch']);
assert.deepStrictEqual(
  Object.fromEntries(queue.excluded.map(e => [e.candidate_id, e.reason])),
  { 'd-static': 'static-below-floor', 'f-potential-low': 'potential-below-gate' },
);
const report = JSON.parse(fs.readFileSync(path.join(root, 'alphas/research/triage/latest.json'), 'utf8'));
const seedTargets = Object.fromEntries(report.seeds.map(s => [s.candidate_id, s.target]));
assert.strictEqual(seedTargets['c-dead'], 'escape-dead-zone');
assert.strictEqual(seedTargets['g-dead-batch'], 'escape-dead-zone');
assert.strictEqual(seedTargets['d-static'], 'clear-ir-floor');
const summaryText = fs.readFileSync(path.join(root, 'alphas/research/triage/latest-summary.md'), 'utf8');
assert.ok(summaryText.includes('## Slow queue (cap 3'));
assert.ok(summaryText.includes('## What worked'));
assert.ok(summaryText.includes('## Top 10 by Fast IR'));
assert.ok(report.learning.latest_slow_results.length === 0 || report.learning.latest_slow_batch !== undefined);

const manifest = JSON.parse(execFileSync(process.execPath, [path.join(scripts, 'trexsim-research-manifest.js'), 'slow'], {
  env: { ...process.env, TREXSIM_ROOT: root }, encoding: 'utf8',
}));
assert.deepStrictEqual(manifest.map(row => row.n), ['a-new', 'b-ladder', 'e-potential']);

fs.rmSync(path.join(root, 'alphas/research/slow-queue.json'));
const legacy = JSON.parse(execFileSync(process.execPath, [path.join(scripts, 'trexsim-research-manifest.js'), 'slow'], {
  env: { ...process.env, TREXSIM_ROOT: root }, encoding: 'utf8',
}));
assert.deepStrictEqual(legacy.map(row => row.n).sort(), ['a-new', 'b-ladder', 'c-dead', 'd-static', 'g-dead-batch']);

fs.rmSync(root, { recursive: true, force: true });
process.stdout.write('fast triage checks passed\n');
