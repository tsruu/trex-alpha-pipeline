#!/usr/bin/env node
// Check one or more candidate records against every live attempt for duplicate formulas.
// The attempt index is rebuilt in memory on every call, so it can never be stale.
// Usage: node scripts/trexsim-check-factory-duplicate.js <candidate.json | directory> [...]
// Exit code 2 when any candidate has an exact formula duplicate.

const fs = require('fs');
const path = require('path');
const {
  buildAll,
  fieldFingerprint,
  formulaFingerprint,
  operatorFingerprint,
  structuralFingerprint,
} = require('./trexsim-factory-context');

const inputs = process.argv.slice(2);
if (!inputs.length) throw new Error('Usage: node scripts/trexsim-check-factory-duplicate.js <candidate.json | directory> [...]');

const files = inputs.flatMap(input => {
  const resolved = path.resolve(process.cwd(), input);
  return fs.statSync(resolved).isDirectory()
    ? fs.readdirSync(resolved).filter(name => name.endsWith('.json')).sort().map(name => path.join(resolved, name))
    : [resolved];
});

const indexText = buildAll()['alphas/factory/attempt-index.jsonl'];
const attempts = indexText.split('\n').filter(Boolean).map(line => JSON.parse(line));

function check(candidate) {
  if (typeof candidate.code !== 'string' || !candidate.code.trim()) {
    return { candidate_id: candidate.candidate_id || null, error: 'candidate must contain non-empty code', duplicate: false };
  }
  const fields = [...(candidate.inputs?.primary_variables || []), ...(candidate.inputs?.secondary_variables || [])];
  const fingerprints = {
    canonical_formula_hash: formulaFingerprint(candidate.code),
    structural_fingerprint: structuralFingerprint(candidate.code),
    field_fingerprint: fieldFingerprint(fields),
    operator_fingerprint: operatorFingerprint(candidate.code),
  };
  const other = attempts.filter(row => row.id !== candidate.candidate_id);
  const result = {
    candidate_id: candidate.candidate_id || null,
    fingerprints,
    exact_formula_matches: other.filter(row => row.canonical_formula_hash === fingerprints.canonical_formula_hash).map(row => row.id),
    structural_matches: other.filter(row => row.structural_fingerprint === fingerprints.structural_fingerprint).map(row => row.id),
    same_field_operator_matches: other.filter(row => row.field_fingerprint === fingerprints.field_fingerprint && row.operator_fingerprint === fingerprints.operator_fingerprint).map(row => row.id),
  };
  result.duplicate = result.exact_formula_matches.length > 0;
  return result;
}

const results = files.map(file => check(JSON.parse(fs.readFileSync(file, 'utf8'))));
process.stdout.write(`${JSON.stringify(results.length === 1 ? results[0] : {
  checked: results.length,
  duplicates: results.filter(r => r.duplicate).map(r => ({ candidate_id: r.candidate_id, matches: r.exact_formula_matches })),
  structural_matches: results.filter(r => r.structural_matches?.length).map(r => ({ candidate_id: r.candidate_id, matches: r.structural_matches })),
  errors: results.filter(r => r.error).map(r => ({ candidate_id: r.candidate_id, error: r.error })),
}, null, 2)}\n`);
if (results.some(r => r.duplicate)) process.exitCode = 2;
if (results.some(r => r.error)) process.exitCode = 1;
