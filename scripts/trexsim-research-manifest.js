#!/usr/bin/env node
// Validate generic research candidates and emit a Fast or Slow TrexSim API manifest.
// Usage: node scripts/trexsim-research-manifest.js <fast|slow> [candidate-ids-csv]

const fs = require('fs');
const path = require('path');
const {
  findFutureAccessViolations,
  formatFutureAccessViolations,
} = require('./trexsim-expression-safety');
const { submittedCode } = require('./trexsim-research-state');

const [mode, requestedCsv] = process.argv.slice(2);
if (!['fast', 'slow'].includes(mode)) {
  throw new Error('Usage: node scripts/trexsim-research-manifest.js <fast|slow> [candidate-ids-csv]');
}

const root = process.env.TREXSIM_ROOT ? path.resolve(process.env.TREXSIM_ROOT) : path.resolve(__dirname, '..');
const directory = path.join(root, 'alphas', 'research', 'candidates');
// v3: when the Fast triage has written a Slow queue, the Slow manifest follows it exactly
// (eligibility, priority order, and nightly cap). Without a queue the legacy gate applies.
const queuePath = path.join(root, 'alphas', 'research', 'slow-queue.json');
const slowQueue = mode === 'slow' && fs.existsSync(queuePath) ? JSON.parse(fs.readFileSync(queuePath, 'utf8')) : null;
const queuePosition = new Map((slowQueue?.entries || []).map((entry, index) => [entry.candidate_id, index]));
const queueExcluded = new Set((slowQueue?.excluded || []).map(entry => entry.candidate_id));
const staleQueue = [];
const requested = requestedCsv ? new Set(requestedCsv.split(',').filter(Boolean)) : null;
const files = fs.existsSync(directory)
  ? fs.readdirSync(directory).filter(file => file.endsWith('.json')).sort()
  : [];
const errors = [];
const manifest = [];
const records = new Map();
const candidateStatuses = new Set([
  'draft', 'fast_error', 'fast_rejected', 'potential', 'fast_promoted',
  'slow_error', 'slow_rejected', 'qualified', 'submitted',
]);
const runStatuses = new Set(['pending', 'not_eligible', 'success', 'error']);

function isPositiveInteger(value) {
  return Number.isInteger(value) && value > 0;
}

function isStringArray(value) {
  return Array.isArray(value) && value.every(item => typeof item === 'string' && item.length > 0);
}

for (const file of files) {
  const source = path.join(directory, file);
  let candidate;
  try {
    candidate = JSON.parse(fs.readFileSync(source, 'utf8'));
  } catch (error) {
    errors.push(`${file}: invalid JSON (${error.message})`);
    continue;
  }

  const id = candidate.candidate_id;
  if (typeof id === 'string') records.set(id, candidate);
  if (requested && !requested.has(id)) continue;
  // Records whose Slow run already succeeded are history, not work: they never enter a manifest, so the
  // submission-time checks below (code safety, lookback buffer, ...) do not apply. Composite records
  // (cmp-*) fail them spuriously (right-aligned padding `out[:, -n:]` looks like future access) and would
  // otherwise make the whole manifest exit 1, i.e. an empty nightly Slow queue. Lineage/status checks still run.
  if (candidate.runs?.slow?.status === 'success' && candidate.runs?.slow?.result?.id) continue;
  if (typeof id !== 'string' || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(id)) {
    errors.push(`${file}: candidate_id must be lowercase hyphenated text`);
    continue;
  }
  if (file !== `${id}.json`) {
    errors.push(`${id}: filename must be ${id}.json`);
    continue;
  }
  if (typeof candidate.title !== 'string' || !candidate.title.trim()) {
    errors.push(`${id}: title must be non-empty text`);
    continue;
  }
  if (!candidateStatuses.has(candidate.status)) {
    errors.push(`${id}: invalid top-level status '${candidate.status}'`);
    continue;
  }
  if (typeof candidate.code !== 'string' || !/(^|\n)\s*alpha\s*=/.test(candidate.code)) {
    errors.push(`${id}: code must be a complete TrexSim buffer containing alpha = ...`);
    continue;
  }
  if (/^\s*(import|from)\s/m.test(candidate.code)) {
    errors.push(`${id}: code must not contain imports`);
    continue;
  }
  const futureAccess = findFutureAccessViolations(candidate.code);
  if (futureAccess.length) {
    errors.push(`${id}: future-data access is not allowed (${formatFutureAccessViolations(futureAccess).join('; ')})`);
    continue;
  }
  if (!isPositiveInteger(candidate.required_lookback) || !isPositiveInteger(candidate.slow_lookback_buffered)) {
    errors.push(`${id}: required_lookback and slow_lookback_buffered must be positive integers`);
    continue;
  }
  const minimumBuffer = candidate.required_lookback >= 100 ? 10 : 5;
  if (candidate.slow_lookback_buffered < candidate.required_lookback + minimumBuffer) {
    errors.push(`${id}: slow_lookback_buffered must include the ${minimumBuffer}-day convention buffer`);
    continue;
  }
  if (
    typeof candidate.inputs?.primary_cluster !== 'string'
    || !candidate.inputs.primary_cluster
    || !isStringArray(candidate.inputs.primary_variables)
    || candidate.inputs.primary_variables.length === 0
    || !isStringArray(candidate.inputs.secondary_clusters)
    || !isStringArray(candidate.inputs.secondary_variables)
  ) {
    errors.push(`${id}: inputs requires primary_cluster plus primary/secondary variable and cluster arrays`);
    continue;
  }
  if (!candidate.metadata?.hypothesis || typeof candidate.metadata.neutralized !== 'boolean') {
    errors.push(`${id}: metadata requires hypothesis and boolean neutralized`);
    continue;
  }
  const lineage = candidate.lineage;
  if (
    !lineage
    || typeof lineage.family_id !== 'string'
    || typeof lineage.root_candidate_id !== 'string'
    || !(lineage.parent_candidate_id === null || typeof lineage.parent_candidate_id === 'string')
    || !Number.isInteger(lineage.generation)
    || lineage.generation < 0
    || !['base', 'potential-rescue', 'full-fan', 'manual'].includes(lineage.stage)
    || !lineage.changes
    || typeof lineage.changes !== 'object'
    || Array.isArray(lineage.changes)
  ) {
    errors.push(`${id}: lineage requires family/root/parent IDs, generation, stage, and changes object`);
    continue;
  }
  if (lineage.generation === 0 && (lineage.parent_candidate_id !== null || lineage.root_candidate_id !== id)) {
    errors.push(`${id}: a generation-0 root must have parent null and root_candidate_id equal to candidate_id`);
    continue;
  }
  if (lineage.generation > 0 && !lineage.parent_candidate_id) {
    errors.push(`${id}: a variant must name its parent_candidate_id`);
    continue;
  }

  const fast = candidate.runs?.fast;
  const slow = candidate.runs?.slow;
  if (!fast || !slow || !runStatuses.has(fast.status) || !runStatuses.has(slow.status)) {
    errors.push(`${id}: runs.fast and runs.slow require valid status/result/error envelopes`);
    continue;
  }
  if (mode === 'fast' && fast.status === 'pending' && !fast.result?.id) {
    manifest.push({
      n: id,
      code: submittedCode(candidate.code, candidate.metadata.hypothesis),
      ...(candidate.settings ? { settings: candidate.settings } : {}),
    });
  }
  if (mode === 'slow' && fast.status === 'success' && fast.result?.id && !slow.result?.id) {
    const entry = { n: id, fast_id: String(fast.result.id), lookback: candidate.slow_lookback_buffered };
    if (slowQueue) {
      if (queuePosition.has(id) && ['pending', 'not_eligible'].includes(slow.status)) {
        manifest.push(entry);
      } else if (slow.status === 'pending' && !queuePosition.has(id) && !queueExcluded.has(id)) {
        staleQueue.push(id);
      }
    } else if (Number(fast.result.ir) >= 0.05 && slow.status === 'pending') {
      manifest.push(entry);
    }
  }
}

function selectedForValidation(id) {
  return !requested || requested.has(id);
}

function successfulIr(envelope) {
  return envelope?.status === 'success' ? Number(envelope.result?.ir) : NaN;
}

for (const [id, candidate] of records) {
  if (!selectedForValidation(id)) continue;
  const lineage = candidate.lineage || {};
  const rootRecord = records.get(lineage.root_candidate_id);
  if (!rootRecord) {
    errors.push(`${id}: root candidate '${lineage.root_candidate_id}' does not exist`);
  } else if (
    rootRecord.lineage?.generation !== 0
    || rootRecord.lineage?.root_candidate_id !== lineage.root_candidate_id
    || rootRecord.lineage?.family_id !== lineage.family_id
  ) {
    errors.push(`${id}: root candidate is inconsistent with this candidate's lineage`);
  }

  if (lineage.generation > 0) {
    const parent = records.get(lineage.parent_candidate_id);
    if (!parent) {
      errors.push(`${id}: parent candidate '${lineage.parent_candidate_id}' does not exist`);
    } else {
      if (parent.lineage?.family_id !== lineage.family_id) {
        errors.push(`${id}: parent and child must share family_id`);
      }
      if (parent.lineage?.root_candidate_id !== lineage.root_candidate_id) {
        errors.push(`${id}: parent and child must share root_candidate_id`);
      }
      if (parent.lineage?.generation + 1 !== lineage.generation) {
        errors.push(`${id}: generation must equal parent generation + 1`);
      }
    }
  }

  const fast = candidate.runs?.fast;
  const slow = candidate.runs?.slow;
  const fastIr = successfulIr(fast);
  const slowIr = successfulIr(slow);
  const consistent = (
    (candidate.status === 'draft' && fast?.status === 'pending' && slow?.status === 'not_eligible')
    || (candidate.status === 'fast_error' && fast?.status === 'error' && slow?.status === 'not_eligible')
    || (candidate.status === 'fast_rejected' && fast?.status === 'success' && fastIr < 0.035 && slow?.status === 'not_eligible')
    || (candidate.status === 'potential' && fast?.status === 'success' && fastIr >= 0.035 && fastIr < 0.05 && slow?.status === 'not_eligible')
    || (candidate.status === 'fast_promoted' && fast?.status === 'success' && fastIr >= 0.05 && slow?.status === 'pending')
    || (candidate.status === 'slow_error' && slow?.status === 'error')
    || (candidate.status === 'slow_rejected' && slow?.status === 'success' && slowIr <= 0.07)
    || (['qualified', 'submitted'].includes(candidate.status) && slow?.status === 'success' && slowIr > 0.07)
  );
  if (!consistent) errors.push(`${id}: top-level status and Fast/Slow run states are inconsistent`);
}

if (errors.length) {
  process.stderr.write(`${errors.join('\n')}\n`);
  process.exitCode = 1;
} else {
  if (slowQueue) {
    manifest.sort((left, right) => queuePosition.get(left.n) - queuePosition.get(right.n));
    const cap = Number(slowQueue.cap);
    if (!requested && Number.isInteger(cap) && cap > 0 && manifest.length > cap) manifest.length = cap;
    if (staleQueue.length) {
      process.stderr.write(`warning: ${staleQueue.length} Slow-pending candidate(s) are not in slow-queue.json; `
        + `run python3 scripts/trexsim-fast-triage.py first (${staleQueue.slice(0, 5).join(', ')}${staleQueue.length > 5 ? ', ...' : ''})\n`);
    }
  }
  process.stdout.write(`${JSON.stringify(manifest, null, 2)}\n`);
}
