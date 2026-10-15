#!/usr/bin/env python3
"""Track the combined IR of the submitted pool as it grows past 280.

Combined alpha = equal-risk average of every alpha's Slow daily PnL (each PnL scaled to unit std, then averaged
across alphas on each date). Headline = daily IR (mean/std) over the FULL history (2006-2021); 2016-21 also shown. (2016-21 reproduces the
numbers used when NDX was trimmed: 280 -> 0.368, 322 -> 0.352.)

What it reports:
  now        combined IR of what is actually submitted (submitted.json) vs the 280 baseline
  path       combined IR after each position of final.json['final'] from 281 on (the planned submit order)
  per alpha  the change in combined IR from adding each planned alpha on top of everything before it
  NDY        (if ndy-set.json exists and NDY hasn't run yet) projection from estimated blend PnL
Each run appends one line to alphas/submission/combined-ir-history.jsonl, so the trend over the day is kept.

  python3 scripts/submission/combined_ir.py            # report + history line + chart (combined-ir.png)
"""
import json, os, sys, time
import numpy as np, pandas as pd
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')); os.chdir(ROOT); sys.path.insert(0, 'scripts/submission')
from subcorr import load_pnl_and_q
SUB = 'alphas/submission'; A, B = '2016-01-01', '2021-12-31'; BASE = 280

pnl, q = load_pnl_and_q()
F = json.load(open(f'{SUB}/final.json')); final = F['final']
submitted = list(json.load(open(f'{SUB}/submitted.json')))

# ---- optional NDY projection (estimated PnL = weighted sum of piece PnLs), only for blends not yet run/appended
est = {}
if os.path.exists(f'{SUB}/ndy-set.json'):
    ndy_set = [c for c in json.load(open(f'{SUB}/ndy-set.json')) if c['name'] not in pnl and c['name'] not in final]
    if ndy_set and not all(p in pnl for c in ndy_set for p in c['comps']):
        import importlib.util
        spec = importlib.util.spec_from_file_location('cy', 'scripts/composites/cycle.py'); cy = importlib.util.module_from_spec(spec); spec.loader.exec_module(cy)
        for k, v in cy.build_library().items(): pnl.setdefault(k, v['pnl'])
        import glob                                   # new-direction singles (NDM Slow runs) used as blend pieces
        for f in glob.glob('alphas/validation/NDM/*.slow.pnl.csv'):
            d = pd.read_csv(f); pnl.setdefault('ndm-' + os.path.basename(f).split('.')[0], d.set_index(pd.to_datetime(d['date']))['dailypnl'])
    for c in ndy_set:
        if c['name'] in pnl or c['name'] in final: continue
        comps, w = c['comps'], c['pos_w']
        if not all(p in pnl for p in comps): continue
        est[c['name']] = sum(wi * pnl[p].fillna(0) for p, wi in zip(comps, w))

allp = {**pnl, **est}
names = list(dict.fromkeys(final + submitted + list(est)))
P = pd.DataFrame({n: allp[n] for n in names if n in allp}).sort_index()
Z = (P / P.std()).fillna(0.0)          # unit-risk, missing days = flat
cnt = P.notna().astype(float)
late = (Z.index >= A) & (Z.index <= B)

def comb(members):
    m = [n for n in members if n in Z]
    s = Z[m].sum(axis=1) / cnt[m].sum(axis=1).clip(lower=1)
    return s

def irs(s):                           # (headline = FULL history, secondary = 2016-21)
    l = s[late]; return float(s.mean() / s.std()), float(l.mean() / l.std())

# path along the planned order (cumulative sums, fast)
S = Z[final].cumsum(axis=1); N = cnt[final].cumsum(axis=1).clip(lower=1)
path = []
for k in range(BASE, len(final) + 1):
    s = S.iloc[:, k - 1] / N.iloc[:, k - 1]; ir16, irf = irs(s)
    path.append(dict(n=k, name=final[k - 1], ir_full=round(ir16, 4), ir_2016_21=round(irf, 4)))
for i in range(1, len(path)): path[i]['delta'] = round(path[i]['ir_full'] - path[i - 1]['ir_full'], 4)
base16 = path[0]['ir_full']

# NDY projection on top of the full planned list
ndy = []
if est:
    names2 = final + list(est)
    S2 = Z[names2].cumsum(axis=1); N2 = cnt[names2].cumsum(axis=1).clip(lower=1)
    for k in range(len(final) + 1, len(names2) + 1):
        s = S2.iloc[:, k - 1] / N2.iloc[:, k - 1]; ir16, irf = irs(s)
        ndy.append(dict(n=k, name=names2[k - 1], ir_full=round(ir16, 4), ir_2016_21=round(irf, 4)))

now16, nowf = irs(comb(submitted))
print(f'NOW: {len(submitted)} submitted -> combined IR full history {now16:.4f} (2016-21 {nowf:.3f}); '
      f'280 baseline {base16:.3f}; change {now16 - base16:+.3f} ({(now16 / base16 - 1) * 100:+.1f}%)')
marks = [k for k in (280, 300, 325, 350, 386, len(final)) if BASE <= k <= len(final)]
print('planned path (full / 2016-21):  ' + '  '.join(f"{k}: {path[k - BASE]['ir_full']:.4f}/{path[k - BASE]['ir_2016_21']:.3f}" for k in marks))
if ndy: print(f'+ all {len(ndy)} NDY (estimated PnL, before the fit check): {ndy[-1]["n"]}: {ndy[-1]["ir_full"]:.4f}/{ndy[-1]["ir_2016_21"]:.3f}')
keep, cur_ir = [], None   # ordering for quality: see quality_order.py
rec = dict(at=time.strftime('%Y-%m-%dT%H:%M:%S'), submitted=len(submitted), ir_full=round(now16, 4), ir_2016_21=round(nowf, 4))
open(f'{SUB}/combined-ir-history.jsonl', 'a').write(json.dumps(rec) + '\n')
json.dump(dict(method=__doc__.split('\n\n')[1], now=rec, baseline_280=base16, path=path, ndy_projection=ndy),
          open(f'{SUB}/combined-ir.json', 'w'), indent=1)

try:
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot([p['n'] for p in path], [p['ir_full'] for p in path], color='#2a6fdb', lw=2, label='planned order (final.json)')
    if ndy: ax.plot([path[-1]['n']] + [p['n'] for p in ndy], [path[-1]['ir_full']] + [p['ir_full'] for p in ndy],
                    color='#2a6fdb', lw=2, ls='--', alpha=.6, label='+ NDY (estimated)')
    ax.scatter([len(submitted)], [now16], color='#d9480f', zorder=5, s=50, label=f'submitted now ({len(submitted)})')
    for x, t in ((325, 'ready 45 end'), (386, 'composites end')):
        if BASE < x <= len(final): ax.axvline(x, color='#999', lw=.8, ls=':'); ax.text(x + 1, ax.get_ylim()[1], t, fontsize=8, color='#666', va='top')
    ax.set_xlabel('alphas submitted'); ax.set_ylabel('combined IR, full history (daily)'); ax.grid(alpha=.3); ax.legend(fontsize=8, loc='lower left')
    ax.set_title('Combined IR as the pool grows past 280'); fig.tight_layout(); fig.savefig(f'{SUB}/combined-ir.png', dpi=130)
except Exception as e: print('chart skipped:', e)
