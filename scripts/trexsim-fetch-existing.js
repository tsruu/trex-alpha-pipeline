#!/usr/bin/env node
// Emit a CDP expression that fetches saved result JSON by Fast OS ID.
// It never submits or reruns an alpha.
// Usage: node trexsim-fetch-existing.js <pool> [alpha-numbers-csv]
const fs = require('fs');
const path = require('path');

const pool = Number(process.argv[2] || 3);
const requested = process.argv[3]
  ? new Set(process.argv[3].split(',').map(Number))
  : null;
const alphasDir = path.join(__dirname, '..', 'alphas');
const runs = [];

for (let n = 1; n <= 101; n += 1) {
  if (requested && !requested.has(n)) continue;
  const file = path.join(alphasDir, `101-alpha-${String(n).padStart(2, '0')}.md`);
  if (!fs.existsSync(file)) continue;
  const content = fs.readFileSync(file, 'utf8');
  const id = content.match(/\| Fast OS \| v1 \| [^|]+ \| (\d+) \|/);
  if (id) runs.push({ n, id: id[1] });
}

const expression = `new Promise(async resolve => {
  const runs = ${JSON.stringify(runs)};
  const pool = ${pool};
  const results = [];
  let index = 0;
  const worker = async () => {
    while (index < runs.length) {
      const run = runs[index++];
      try {
        const response = await fetch('/trexsim/pysim/alpha/' + run.id + '/?format=json');
        results.push({ ...run, raw: await response.json() });
      } catch (error) {
        results.push({ ...run, error: String(error) });
      }
    }
  };
  await Promise.all(Array.from({ length: pool }, worker));
  results.sort((a, b) => a.n - b.n);
  resolve(results);
})`;

process.stdout.write(expression);
