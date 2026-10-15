#!/usr/bin/env python3
"""Submission order past the 280 that keeps the COMBINED IR (full history) as high as possible at every step.

Combined alpha = equal-risk average of the alphas' Slow daily PnL (each scaled to unit std; averaged over the
alphas live on each date). Same measure as combined_ir.py.

Greedy: at each step, among candidates the submission gate would admit (subcorr.admissible, full-history corr
<= 0.50 or IR/sqrt(TVR) >= 1.2x), take the one giving the highest combined IR after it is added. Any candidate
the greedy path strands is re-inserted at the latest position where the whole order still passes the gate, so
the count stays at the maximum. Stopping at any point is gate-safe (fewer members only relaxes the check).

Candidates: final.json['final'][280:] plus any finished ADD/NDY/NDZ run not yet in final (real PnL only).
  python3 scripts/submission/quality_order.py                 # report, writes quality-order.json/.md
  python3 scripts/submission/quality_order.py --ready-first   # only commented-run alphas until none admissible
  python3 scripts/submission/quality_order.py --apply         # also set final.json['final'] = 280 + this order
"""
import argparse, json, os, sys
import numpy as np, pandas as pd
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')); os.chdir(ROOT); sys.path.insert(0, 'scripts/submission')
import subcorr as sc
ap = argparse.ArgumentParser(); ap.add_argument('--ready-first', action='store_true'); ap.add_argument('--apply', action='store_true')
ap.add_argument('--base', type=int, default=280); ap.add_argument('--themed-only', action='store_true',
                help='only themed equal-weight blends (ndb-/nyb-/thm-), new-direction singles and search/mine/intraday singles; no cmp- grab-bag composites, no legacy 101/xcombo')
ap.add_argument('--rank', choices=('ir', 'corr'), default='ir', help='ir: highest combined IR next (in-sample); corr: lowest mean |corr| to the pool next (the deck\'s rule: rank by correlation, not past IR)')
a = ap.parse_args()
TAG = ('-themed' if a.themed_only else '') + ('-corr' if a.rank == 'corr' else '')
SUB = 'alphas/submission'; FP = f'{SUB}/final.json'
pnl, q = sc.load_pnl_and_q(); F = json.load(open(FP)); final = F['final']; base = final[:a.base]
Q = json.load(open('alphas/validation/queue.json'))
def stocks(j):
    v = [int(x) for x in str(j.get('numstks') or '').replace('x', ' ').split() if x.isdigit()]; return min(v) if v else 0
def qualifies(n, j=None):      # site rules: Slow IR > 0.07, >= 1000 valid days, >= 100 stocks
    d = int((pnl[n].fillna(0) != 0).sum()); return d >= 1000 and (j is None or (float(j.get('ir') or 0) > 0.07 and stocks(j) >= 100))
extra = [j['name'] for j in Q if j.get('exp') in ('ADD', 'NDY', 'NDZ') and j.get('status') == 'done' and j['name'] not in final and j['name'] in pnl
         and qualifies(j['name'], j)]
cands = [n for n in final[a.base:] if n in pnl and qualifies(n)] + extra
if a.themed_only: cands = [n for n in cands if n.startswith(('ndb-', 'nyb-', 'thm-', 'ndm-', 'search-', 'mine-', 'intraday'))]
ready = {j['name'] for j in Q if j.get('exp') in ('SUBN', 'SUBV', 'SUBR', 'SUBX', 'NDX', 'ADD', 'NDY', 'NDZ')
         and j.get('status') == 'done' and '# Thesis' in (j.get('code') or '')}
names = base + cands
P = pd.DataFrame({n: pnl[n] for n in names}).sort_index(); Z = (P / P.std()).fillna(0.0); L = P.notna().astype(float)
C = sc.submission_corr_matrix({n: pnl[n] for n in names})
Cn = C.values; ix = {n: i for i, n in enumerate(C.index)}; qv = np.array([q[n] for n in C.index])
def admi(n, pidx):             # vectorised subcorr.admissible: corr <= CAP with all, or IR/sqrt(TVR) >= OVERRIDE x every member it exceeds CAP with
    r = Cn[ix[n], pidx]; hi = r > sc.CAP
    return bool(np.all(qv[ix[n]] >= sc.OVERRIDE * qv[pidx[hi]]))
S0, N0 = Z[base].sum(1).values, L[base].sum(1).values; Zc, Lc = Z[cands].values, L[cands].values
idx = {n: i for i, n in enumerate(cands)}
ir = lambda v: float(v.mean() / v.std())

pool, left, order = list(base), list(range(len(cands))), []; S, N = S0.copy(), N0.copy(); pidx = np.array([ix[m] for m in base])
while left:
    ok = [i for i in left if admi(cands[i], pidx)]
    if a.ready_first: ok = [i for i in ok if cands[i] in ready] or ok
    if not ok: break
    if a.rank == 'corr': i = min(ok, key=lambda j: float(np.nanmean(np.abs(Cn[ix[cands[j]], pidx]))))
    else: M = (S[:, None] + Zc[:, ok]) / np.maximum(N[:, None] + Lc[:, ok], 1); i = ok[int(np.argmax(M.mean(0) / M.std(0)))]
    S += Zc[:, i]; N += Lc[:, i]; pool.append(cands[i]); pidx = np.append(pidx, ix[cands[i]]); left.remove(i); order.append(cands[i])

def valid(o):
    p = np.array([ix[m] for m in base])
    for n in o:
        if not admi(n, p): return False
        p = np.append(p, ix[n])
    return True
stranded = [cands[i] for i in left]
for x in list(stranded):
    pos = [p for p in range(len(order), -1, -1) if valid(order[:p] + [x] + order[p:])]
    if pos: order.insert(pos[0], x); stranded.remove(x)

S, N = S0.copy(), N0.copy(); curve = [ir(S / np.maximum(N, 1))]; rows = []
pool = list(base)
for k, n in enumerate(order, a.base + 1):
    i = idx[n]; before = curve[-1]; S += Zc[:, i]; N += Lc[:, i]; curve.append(ir(S / np.maximum(N, 1)))
    hi = [m for m in pool if C.loc[n, m] > sc.CAP]; mx = float(C.loc[n, pool].max()); pool.append(n)
    ratio = min(q[n] / q[m] for m in hi) if hi else None
    rows.append(dict(pos=k, name=n, ready=n in ready, combined_ir=round(curve[-1], 4), delta=round(curve[-1] - before, 4),
                     max_corr_to_pool=round(mx, 3), override=None if ratio is None else round(ratio, 2),
                     thin_margin=bool((ratio is not None and ratio < 1.25) or (not hi and mx > 0.48))))
b0 = curve[0]; peak = int(np.argmax(curve)); even = max(k for k, v in enumerate(curve) if v >= b0)
print(f'{len(order)} alphas ordered ({len(stranded)} stranded: {stranded}); combined IR full history at {a.base}: {b0:.4f}')
print(f'peak {max(curve):.4f} at {a.base + peak}; stays >= the {a.base} level through {a.base + even}; all: {curve[-1]:.4f}')
fr = next((r['pos'] for r in rows if not r['ready']), None); print('first alpha still needing its commented run:', fr)
out = dict(method=__doc__.split('\n\n')[0:3], base=a.base, baseline_ir=round(b0, 4), peak=dict(pos=a.base + peak, ir=round(max(curve), 4)),
           break_even_pos=a.base + even, order=rows, stranded=stranded)
json.dump(out, open(f'{SUB}/quality-order{TAG}.json', 'w'), indent=1)
md = ['# Quality order (combined IR, full history)', '', f'Baseline at {a.base}: **{b0:.4f}**. Peak **{max(curve):.4f}** at {a.base + peak}. '
      f'At or above baseline through **{a.base + even}**. All {a.base + len(order)}: {curve[-1]:.4f}.', '',
      '| # | alpha | ready | combined IR | Δ | max corr | override | thin |', '|---:|---|---|---:|---:|---:|---|---|']
md += [f"| {r['pos']} | {r['name']} | {'yes' if r['ready'] else 'needs run'} | {r['combined_ir']:.4f} | {r['delta']:+.4f} | {r['max_corr_to_pool']:.3f} | "
       f"{'%.2fx' % r['override'] if r['override'] else '—'} | {'⚠' if r['thin_margin'] else ''} |" for r in rows]
open(f'{SUB}/quality-order{TAG}.md', 'w').write('\n'.join(md) + '\n')
if a.apply:
    F.setdefault('final_count_order', final); F['final'] = base + order
    F['note'] += f' v5: order past {a.base} set by quality_order.py (max combined IR, full history, at every step).'
    json.dump(F, open(FP, 'w'), indent=1); print('final.json updated:', len(F['final']))
