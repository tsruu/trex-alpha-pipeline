#!/usr/bin/env node
// Persist and synchronize the cluster-sweep campaign state.

const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const root = path.resolve(__dirname, '..');
const researchRoot = path.join(root, 'alphas', 'research');
const statePath = path.join(researchRoot, 'campaign.json');
const clusterOrder = [
  'intraday', 'seasonality', 'fundamental_cash', 'fundamental_earnings',
  'fundamental_sales', 'fundamental_net_income', 'fundamental_assets',
  'fundamental_debt', 'fundamental_equity', 'fundamental_expenses',
  'fundamental_year', 'macro', 'price_volume',
];
const phases = new Set([
  'not_started', 'generate_roots', 'fast_screen', 'generate_variants',
  'fast_variants', 'slow_confirm', 'complete',
]);

function freshState() {
  return {
    schema_version: 1,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    current_cluster: null,
    phase: 'not_started',
    next_action: 'Select the first cluster and generate root candidates.',
    cluster_order: clusterOrder,
    clusters: Object.fromEntries(clusterOrder.map(cluster => [cluster, {
      status: 'not_started', counts: {},
    }])),
  };
}

function loadState() {
  return fs.existsSync(statePath) ? JSON.parse(fs.readFileSync(statePath, 'utf8')) : freshState();
}

function saveState(state) {
  fs.mkdirSync(researchRoot, { recursive: true });
  state.updated_at = new Date().toISOString();
  fs.writeFileSync(statePath, `${JSON.stringify(state, null, 2)}\n`);
}

function syncCounts(state) {
  const output = execFileSync(process.execPath, [path.join(__dirname, 'trexsim-research-summary.js'), '--json'], {
    cwd: root, encoding: 'utf8',
  });
  const summary = JSON.parse(output);
  for (const cluster of state.cluster_order) {
    state.clusters[cluster] ||= { status: 'not_started', counts: {} };
    state.clusters[cluster].counts = summary.clusters[cluster] || {};
  }
  state.overall_counts = summary.overall;
}

const [command = 'show', cluster, phase, ...actionParts] = process.argv.slice(2);
const state = loadState();

if (command === 'init') {
  if (fs.existsSync(statePath)) throw new Error(`${path.relative(root, statePath)} already exists`);
  syncCounts(state);
  saveState(state);
} else if (command === 'set') {
  if (!cluster || !state.cluster_order.includes(cluster)) throw new Error('set requires a known cluster');
  if (!phase || !phases.has(phase)) throw new Error(`unknown phase: ${phase || ''}`);
  state.current_cluster = phase === 'complete' ? null : cluster;
  state.phase = phase;
  state.clusters[cluster] ||= { status: 'not_started', counts: {} };
  state.clusters[cluster].status = phase;
  if (actionParts.length) state.next_action = actionParts.join(' ');
  syncCounts(state);
  saveState(state);
} else if (command === 'sync') {
  syncCounts(state);
  saveState(state);
} else if (command !== 'show') {
  throw new Error('Usage: trexsim-research-campaign.js <init|show|sync|set cluster phase [next action]>');
}

process.stdout.write(`${JSON.stringify(state, null, 2)}\n`);
