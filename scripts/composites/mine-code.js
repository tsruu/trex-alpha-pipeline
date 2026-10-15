#!/usr/bin/env node
'use strict';
// Render Slow-ready code for search hits (component mining).
// stdin: JSON array of hashes. stdout: JSON array of {hash, code, lookback, sign} for hits whose stored tree still
// renders to the exact evaluated code under the current grammar (older trees whose primitives changed are skipped).
// Negative-IR hits are rendered with the sign flipped, matching the sign-adjusted PnL saved in alphas/search/pnl/.
const fs = require('fs');
const path = require('path');
const G = require('../search/grammar');
const root = path.resolve(__dirname, '..', '..');
const want = new Set(JSON.parse(fs.readFileSync(0, 'utf8')));
const P = G.primitives(root);
const byName = Object.fromEntries(P.map(p => [p.name, p]));
const out = [];
for (const line of fs.readFileSync(path.join(root, 'alphas/search/evals.jsonl'), 'utf8').split('\n')) {
  if (!line.trim()) continue;
  let e; try { e = JSON.parse(line); } catch { continue; }
  if (!want.has(e.hash) || e.ir == null || !e.tree) continue;
  want.delete(e.hash);
  try {
    if (G.toCode(e.tree, byName, e.sign) !== e.code) continue;          // grammar drifted since evaluation
    const sign = e.ir < 0 ? -e.sign : e.sign;
    const req = G.lookback(e.tree, byName) + 1;
    out.push({ hash: e.hash, code: G.toCode(e.tree, byName, sign), lookback: req + (req >= 100 ? 10 : 5), sign });
  } catch { /* primitive no longer exists */ }
}
process.stdout.write(JSON.stringify(out));
