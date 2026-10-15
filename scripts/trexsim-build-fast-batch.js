#!/usr/bin/env node
// Build a deterministic manifest for Fast OS alphas that have no recorded Fast OS result.
// Usage: node trexsim-build-fast-batch.js [alpha-numbers-csv] > /tmp/trex-fast-pending.json
const fs = require('fs');
const path = require('path');

const requested = process.argv[2]
  ? new Set(process.argv[2].split(',').map(Number))
  : null;
const directory = path.join(__dirname, '..', 'alphas');
const batch = [];

for (let n = 1; n <= 101; n += 1) {
  if (requested && !requested.has(n)) continue;
  const file = path.join(directory, `101-alpha-${String(n).padStart(2, '0')}.md`);
  if (!fs.existsSync(file)) continue;
  const content = fs.readFileSync(file, 'utf8');
  if (/\| Fast OS \| v1 \| [^|]+ \| \d+ \|/.test(content)) continue;
  const code = content.match(/### v1\s*\n\n```python\n([\s\S]*?)\n```/);
  if (!code) throw new Error(`Alpha ${n} has no v1 Python block.`);
  batch.push({ n, code: code[1] });
}

process.stdout.write(`${JSON.stringify(batch, null, 2)}\n`);
