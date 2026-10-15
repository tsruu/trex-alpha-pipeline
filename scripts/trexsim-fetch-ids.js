#!/usr/bin/env node
// Emit a CDP expression that fetches full result JSON for explicit TrexSim IDs.
// Usage: node trexsim-fetch-ids.js <results.json>
const fs = require('fs');
const input = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const runs = input.map(({ n, id }) => ({ n, id: String(id) }));
const expression = `new Promise(async resolve => {
  const runs = ${JSON.stringify(runs)};
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
  await Promise.all(Array.from({ length: 3 }, worker));
  results.sort((a, b) => a.n - b.n);
  resolve(results);
})`;
process.stdout.write(expression);
