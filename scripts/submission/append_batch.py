#!/usr/bin/env python3
"""After a batch of commented Slow runs finishes (e.g. exp NDY), append the ones that fit to final.json['final'].

Qualifies: Slow IR > 0.07, >= 1000 valid (non-zero PnL) days, >= 100 average stocks.
Fits: by REALIZED submission correlation (full history) against everything already in final.json['final']
(submitted + planned) and the batch members appended before it, with safety margins: corr <= 0.495, or
IR/sqrt(TVR) >= 1.22x every member it exceeds 0.495 with. Greedy order = fewest-blocking first (subcorr.plan_order logic).
  python3 scripts/submission/append_batch.py --exp NDY            # report only
  python3 scripts/submission/append_batch.py --exp NDY --write    # append to final.json
"""
import argparse, json, os, sys
import numpy as np
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')); os.chdir(ROOT); sys.path.insert(0, 'scripts/submission')
from subcorr import load_pnl_and_q, submission_corr_matrix
ap = argparse.ArgumentParser(); ap.add_argument('--exp', required=True); ap.add_argument('--write', action='store_true')
ap.add_argument('--cap', type=float, default=0.495); ap.add_argument('--override', type=float, default=1.22); a = ap.parse_args()
F = 'alphas/submission/final.json'; fin = json.load(open(F)); final = fin['final']
pnl, q = load_pnl_and_q()
jobs = [j for j in json.load(open('alphas/validation/queue.json')) if j['exp'] == a.exp.upper() and j['mode'] == 'os']
pending = [j['name'] for j in jobs if j['status'] != 'done']
cand, dq = [], []
for j in jobs:
    if j['status'] != 'done' or j['name'] in final: continue
    s = pnl.get(j['name']); stk = float(str(j.get('numstks') or '0x0').split('x')[0])
    days = int((s.fillna(0) != 0).sum()) if s is not None else 0
    if s is None or float(j['ir']) <= 0.07 or days < 1000 or stk < 100: dq.append((j['name'], j.get('ir'), days, stk)); continue
    cand.append(j['name'])
C = submission_corr_matrix({n: pnl[n] for n in final + cand if n in pnl})
def ok(n, pool):
    hi = [m for m in pool if C.loc[n, m] > a.cap]
    return all(q[n] >= a.override * q[m] for m in hi)
pool, left, order = [n for n in final if n in pnl], list(cand), []
while True:
    adm = [n for n in left if ok(n, pool)]
    if not adm: break
    best = min(adm, key=lambda n: int((C.loc[n, [k for k in left if k != n]] > a.cap).sum()))
    pool.append(best); left.remove(best); order.append(best)
print(f'{a.exp}: {len(jobs)} jobs, {len(pending)} not finished, {len(dq)} not qualified, {len(cand)} qualified -> {len(order)} fit, {len(left)} held back')
for n in left: print('  held back', n, 'max corr', round(float(C.loc[n, pool].max()), 3))
if a.write and order:
    fin['final'] = final + order; fin.setdefault('batches_appended', {})[a.exp.upper()] = order
    json.dump(fin, open(F, 'w'), indent=1); print('final.json now', len(fin['final']))
