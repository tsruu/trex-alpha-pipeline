#!/usr/bin/env node
// Focused checks for durable reservoir persistence and candidate provenance.

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const {
  codeProvenance,
  invalidSimulationReason,
  rebuildReservoir,
  reservoirPath,
  submittedCode,
} = require('./trexsim-research-state');

assert.strictEqual(
  submittedCode('alpha = close', '  Mean   reversion\n hypothesis  '),
  '# Hypothesis: Mean reversion hypothesis\nalpha = close',
);
assert.strictEqual(
  submittedCode('# Hypothesis: Existing\nalpha = close', 'Replacement'),
  '# Hypothesis: Existing\nalpha = close',
);
assert.strictEqual(invalidSimulationReason({ stats_data: { metrics: { ir: 0.1, numstks: '900x1000' } } }, [{}]), null);
assert.match(invalidSimulationReason({ stats_data: { metrics: { ir: '', numstks: '0x0' } } }, []), /blank IR/);
assert.match(invalidSimulationReason({ stats_data: { metrics: { ir: 0, numstks: '0x0' } } }, [{}]), /0x0/);
assert.match(invalidSimulationReason({ stats_data: { metrics: { ir: 0.1, numstks: '900x1000' } } }, []), /no daily PNL/);
assert.match(invalidSimulationReason({ os_limit_exceeded: true }, []), /OS limit/);

const root = fs.mkdtempSync(path.join(os.tmpdir(), 'trexsim-state-'));
try {
  const directory = path.join(root, 'alphas', 'research', 'candidates');
  fs.mkdirSync(directory, { recursive: true });
  const code = 'def gate(x):\n    return x\n\nalpha = gate(close)';
  fs.writeFileSync(path.join(directory, 'qualified.json'), `${JSON.stringify({
    candidate_id: 'qualified', title: 'Qualified', status: 'qualified', code,
    inputs: { primary_cluster: 'price_volume' }, metadata: { hypothesis: 'test' },
    lineage: { family_id: 'family', root_candidate_id: 'qualified', parent_candidate_id: null, generation: 0 },
    runs: { slow: { status: 'success', result: { ir: 0.08 } } },
  })}\n`);
  fs.writeFileSync(path.join(directory, 'draft.json'), `${JSON.stringify({
    candidate_id: 'draft', title: 'Draft', status: 'draft', code,
  })}\n`);

  const provenance = codeProvenance(code, root);
  assert.match(provenance.candidate_code_sha256, /^[a-f0-9]{64}$/);
  assert.match(provenance.pre_alpha_code_sha256, /^[a-f0-9]{64}$/);
  assert.strictEqual(provenance.git_commit, null);

  const reservoir = rebuildReservoir(root);
  assert.strictEqual(reservoir.schema_version, 1);
  assert.deepStrictEqual(reservoir.members.map(member => member.candidate_id), ['qualified']);
  assert.strictEqual(reservoir.members[0].provenance.candidate_code_sha256, provenance.candidate_code_sha256);
  assert.strictEqual(reservoir.members[0].provenance.pre_alpha_code_sha256, provenance.pre_alpha_code_sha256);
  assert.ok(fs.existsSync(reservoirPath(root)));
  JSON.parse(fs.readFileSync(reservoirPath(root), 'utf8'));
  console.log('research state checks passed');
} finally {
  fs.rmSync(root, { recursive: true, force: true });
}
