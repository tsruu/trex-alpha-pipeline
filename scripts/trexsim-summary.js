#!/usr/bin/env node
// Print summary table for alphas 31-101 from md files
const fs = require('fs');
const path = require('path');
const rows = [];
for (let n = 31; n <= 101; n++) {
  const nn = String(n).padStart(2, '0');
  const f = path.join(__dirname, '..', 'alphas', `101-alpha-${nn}.md`);
  const c = fs.readFileSync(f, 'utf8');
  const idM = c.match(/\| Fast OS \| v1 \| 2026-09-19 \| (\d+) \|/);
  const irM = c.match(/\| IR \| ([\d.-]+) \|/);
  if (idM && irM) {
    const ir = parseFloat(irM[1]);
    rows.push({ n, id: idM[1], ir: irM[1], qual: ir > 0.07 ? 'Yes' : 'No' });
  } else {
    rows.push({ n, id: 'pending', ir: '-', qual: '-' });
  }
}
console.log('| Alpha | TrexSim ID | IR | IR>0.07? |');
console.log('|------|------------|-----|----------|');
rows.forEach(r => console.log(`| ${r.n} | ${r.id} | ${r.ir} | ${r.qual} |`));
const quals = rows.filter(r => r.qual === 'Yes').map(r => r.n);
console.log('\nQualifiers (IR>0.07):', quals.join(', ') || 'none');
