#!/usr/bin/env node
// Consume the API batch results (array of {n,id,status,period,ir,tvr,dd,ret,ir_tvr,booksize,numstks,liq,liqn,region})
// and write each alpha's md via trexsim-update-results.js. Idempotent: skips alphas already carrying a Fast OS row.
// Usage: node trexsim-api-save.js <results.json>
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const results = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const upd = path.join(__dirname, 'trexsim-update-results.js');

const fmtWindow = (p) => {
  if (!p) return 'n/a';
  const m = p.match(/^(\d{4})(\d{2})(\d{2})-(\d{4})(\d{2})(\d{2})$/);
  if (!m) return p;
  return `${m[1]}-${m[2]}-${m[3]} — ${m[4]}-${m[5]}-${m[6]}`;
};

const na = (v) => (v === undefined || v === null || v === '') ? 'n/a' : String(v);

for (const r of results) {
  const nn = String(r.n).padStart(2, '0');
  const file = path.join(__dirname, '..', 'alphas', `101-alpha-${nn}.md`);
  const content = fs.readFileSync(file, 'utf8');
  if (/\| Fast OS \| v1 \| 2026-09-19 \| \d+ \|/.test(content)) { console.log(`skip ${nn}: already has Fast OS row`); continue; }
  if (r.error) { console.log(`ERROR ${nn}: ${r.error}`); continue; }
  if (!r.id) { console.log(`ERROR ${nn}: no id`); continue; }

  const empty = na(r.ir) === 'n/a' || r.numstks === '0x0';
  const irNum = parseFloat(r.ir);
  const note = empty
    ? 'Fast OS via API returned an empty book (no metrics) — likely insufficient fast-window warmup for its high-lookback terms; needs Slow OS.'
    : `Fast OS via API; IR ${na(r.ir)} ${irNum > 0.07 ? 'clears' : 'does not clear'} the 0.07 qualifying bar.`;

  execFileSync('node', [upd, String(r.n), String(r.id), fmtWindow(r.period),
    na(r.ir), na(r.tvr), na(r.dd), na(r.ret), na(r.ir_tvr),
    na(r.booksize), na(r.numstks), na(r.liq), na(r.liqn), na(r.region), note], { stdio: 'inherit' });
}
