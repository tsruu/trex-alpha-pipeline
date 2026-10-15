'use strict';
// Pilot analysis: hit rates and how spread out the hits are.
const fs = require('fs');
const path = require('path');

module.exports = function analyze(root, dir, tag) {
  const evals = fs.readFileSync(path.join(dir, 'evals.jsonl'), 'utf8').split('\n').filter(Boolean).map(JSON.parse)
    .filter(e => !tag || e.tag === tag);
  const valid = evals.filter(e => !e.error);
  const readPnl = f => { const o = {}; if (!fs.existsSync(f)) return o; for (const l of fs.readFileSync(f, 'utf8').split('\n').slice(1)) { const [d, , v] = l.split(','); if (d && v) o[d] = Number(v); } return o; };
  const corr = (a, b) => { let n = 0, sa = 0, sb = 0, saa = 0, sbb = 0, sab = 0; for (const d in a) { const y = b[d]; if (y === undefined) continue; const x = a[d]; n++; sa += x; sb += y; saa += x * x; sbb += y * y; sab += x * y; } if (n < 60) return 0; const va = saa - sa * sa / n, vb = sbb - sb * sb / n; return va > 0 && vb > 0 ? (sab - sa * sb / n) / Math.sqrt(va * vb) : 0; };
  const shape = e => e.tree?.t || '?';
  const rate = (list, thr) => list.length ? (100 * list.filter(e => Math.abs(e.ir) >= thr).length / list.length).toFixed(1) + '%' : '-';
  const lines = [`# Search pilot report${tag ? ` (${tag})` : ''} — ${new Date().toISOString().slice(0, 16)}`, '',
    `Evaluated ${evals.length}; valid ${valid.length}; errors ${evals.length - valid.length}.`,
    `Hit rate |IR|>=0.05: ${rate(valid, 0.05)}; >=0.07: ${rate(valid, 0.07)}; near-miss >=0.03: ${rate(valid, 0.03)}. (Negative IR counts: a sign flip gives the same |IR|.)`, ''];
  const group = (key) => { const g = {}; for (const e of valid) for (const k of [].concat(key(e))) (g[k] ||= []).push(e); return g; };
  for (const [title, key] of [['family', e => e.families], ['formula shape', shape]]) {
    lines.push(`## By ${title}`, '', `| ${title} | n | |IR|>=0.03 | |IR|>=0.05 | best |IR| |`, '|---|---|---|---|---|');
    for (const [k, list] of Object.entries(group(key)).sort((a, b) => b[1].length - a[1].length))
      lines.push(`| ${k} | ${list.length} | ${rate(list, 0.03)} | ${rate(list, 0.05)} | ${Math.max(...list.map(e => Math.abs(e.ir))).toFixed(3)} |`);
    lines.push('');
  }
  // Spread: greedy regions among hits and near-misses (signed PnL stored by the search).
  for (const thr of [0.05, 0.03]) {
    const pts = valid.filter(e => Math.abs(e.ir) >= thr).sort((a, b) => Math.abs(b.ir) - Math.abs(a.ir))
      .map(e => ({ e, pnl: readPnl(path.join(dir, 'pnl', `${e.hash}.csv`)) })).filter(p => Object.keys(p.pnl).length);
    const regions = [];
    for (const p of pts) { const home = regions.find(rg => corr(p.pnl, rg[0].pnl) > 0.5); if (home) home.push(p); else regions.push([p]); }
    lines.push(`## Regions among |IR| >= ${thr} (${pts.length} formulas)`, '',
      `${regions.length} distinct regions (a formula joins a region if its PnL correlates > 0.5 with the region's best member); ${regions.filter(rg => (rg[0].e.max_frontier_corr ?? 1) <= 0.5).length} of them are also <= 0.5 correlated with every current pool alpha.`, '');
    for (const rg of regions.slice(0, 25)) lines.push(`- ${rg.length} member(s); best |IR| ${Math.abs(rg[0].e.ir).toFixed(3)}, max pool corr ${rg[0].e.max_frontier_corr ?? '-'} [${rg[0].e.families.join(', ')}] \`${rg[0].e.code.split('\n').pop().slice(0, 140)}\``);
    lines.push('');
  }
  const text = lines.join('\n');
  fs.writeFileSync(path.join(dir, `pilot-report${tag ? '-' + tag : ''}.md`), text);
  console.log(text);
};
