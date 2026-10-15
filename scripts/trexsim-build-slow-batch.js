#!/usr/bin/env node
// Build a deterministic manifest for Slow OS alphas that have no recorded Slow OS result.
// Usage: node trexsim-build-slow-batch.js [alpha-numbers-csv] > /tmp/trex-slow-pending.json
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
  if (/\| Slow OS \| v1 \| [^|]+ \| \d+ \|/.test(content)) continue;

  const fast = content.match(/\| Fast OS \| v1 \| [^|]+ \| (\d+) \|/);
  if (!fast) continue;
  const lookback = content.match(/-\s*Slow OS:\s*(\d+)d\s*\(buffered\)/);
  if (!lookback) throw new Error(`Alpha ${n} has no buffered Slow OS lookback.`);

  batch.push({ n, fast_id: fast[1], lookback: Number(lookback[1]) });
}

process.stdout.write(`${JSON.stringify(batch, null, 2)}\n`);
