#!/usr/bin/env node

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');

const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'trexsim-api-batch-'));
try {
  const manifest = path.join(directory, 'manifest.json');
  fs.writeFileSync(manifest, `${JSON.stringify([
    { n: 1, code: '# Hypothesis: first\nalpha = close' },
    { n: 2, code: '# Hypothesis: second\nalpha = open' },
  ])}\n`);
  const expression = execFileSync(process.execPath, [
    path.join(__dirname, 'trexsim-api-batch.js'), manifest, '2', '2',
  ], { encoding: 'utf8', env: { ...process.env, TREXSIM_FAST_ERROR_LIMIT: '3' } });
  assert.doesNotThrow(() => new Function(`return ${expression};`));
  assert.match(expression, /const ERROR_LIMIT = 3/);
  assert.match(expression, /# Hypothesis: second/);
  assert.doesNotMatch(expression, /# Hypothesis: first/);
  assert.match(expression, /fast_error_circuit_open/);
  console.log('Fast batch checks passed');
} finally {
  fs.rmSync(directory, { recursive: true, force: true });
}
