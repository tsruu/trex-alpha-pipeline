// Shared persistence and provenance helpers for generic alpha research.

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

function sha256(text) {
  return crypto.createHash('sha256').update(String(text), 'utf8').digest('hex');
}

function submittedCode(code, hypothesis) {
  const text = String(code || '');
  if (text.startsWith('# Hypothesis:')) return text;
  const comment = `# Hypothesis: ${String(hypothesis || '').replace(/\s+/g, ' ').trim()}`;
  return `${comment}\n${text}`;
}

function invalidSimulationReason(raw, series) {
  if (raw?.os_limit_exceeded) return 'TrexSim OS limit was exceeded';
  const metrics = raw?.stats_data?.metrics;
  if (!metrics || typeof metrics !== 'object') return 'simulation returned no metrics';
  if (metrics.ir === undefined || metrics.ir === null || metrics.ir === '') {
    return 'simulation returned a blank IR';
  }
  if (!Number.isFinite(Number(metrics.ir))) return 'simulation returned a non-numeric IR';
  if (String(metrics.numstks ?? '').trim().toLowerCase() === '0x0') {
    return 'simulation returned an empty 0x0 stock book';
  }
  if (!Array.isArray(series) || series.length === 0) return 'simulation returned no daily PNL series';
  return null;
}

function gitCommit(root) {
  try {
    return execFileSync('git', ['-C', root, 'rev-parse', 'HEAD'], {
      encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'],
    }).trim() || null;
  } catch {
    return null;
  }
}

function codeProvenance(code, root) {
  const text = String(code || '');
  // The prefix includes inline helpers and intermediate assignments. Hash it
  // separately because either can change while the final alpha line stays put.
  const alphaStart = text.search(/(^|\n)\s*alpha\s*=/);
  const preAlphaCode = alphaStart < 0 ? text : text.slice(0, alphaStart);
  return {
    candidate_code_sha256: sha256(text),
    pre_alpha_code_sha256: sha256(preAlphaCode),
    git_commit: gitCommit(root),
  };
}

function reservoirPath(root) {
  return path.join(root, 'alphas', 'research', 'reservoir.json');
}

function writeJsonAtomic(file, value) {
  const temporary = `${file}.tmp-${process.pid}`;
  fs.writeFileSync(temporary, `${JSON.stringify(value, null, 2)}\n`);
  fs.renameSync(temporary, file);
}

function rebuildReservoir(root) {
  const candidateRoot = path.join(root, 'alphas', 'research', 'candidates');
  const candidates = fs.existsSync(candidateRoot)
    ? fs.readdirSync(candidateRoot).filter(file => file.endsWith('.json')).sort()
      .map(file => JSON.parse(fs.readFileSync(path.join(candidateRoot, file), 'utf8')))
    : [];
  const members = candidates
    .filter(candidate => ['qualified', 'submitted'].includes(candidate.status))
    .map(candidate => ({
      candidate_id: candidate.candidate_id,
      title: candidate.title,
      code: candidate.code,
      inputs: candidate.inputs,
      metadata: candidate.metadata,
      lineage: candidate.lineage,
      required_lookback: candidate.required_lookback,
      slow_lookback_buffered: candidate.slow_lookback_buffered,
      slow: candidate.runs?.slow || null,
      provenance: codeProvenance(candidate.code, root),
    }));
  members.sort((left, right) => left.candidate_id.localeCompare(right.candidate_id));
  const reservoir = {
    schema_version: 1,
    generated_at: new Date().toISOString(),
    git_commit: gitCommit(root),
    members,
  };
  const file = reservoirPath(root);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  writeJsonAtomic(file, reservoir);
  return reservoir;
}

module.exports = {
  codeProvenance,
  gitCommit,
  invalidSimulationReason,
  rebuildReservoir,
  reservoirPath,
  sha256,
  submittedCode,
};
