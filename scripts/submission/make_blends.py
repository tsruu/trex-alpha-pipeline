#!/usr/bin/env python3
"""Equal-weight themed blends screened on SUBMISSION correlation (next batch after NDX; default exp NDY).

Pieces: every Slow-validated single in the component library (search / mine / hand-written intraday; no legacy-101
or xcombo piece) + the NDM singles. A blend = 2-4 pieces with the SAME theme set, equal risk weights
(pos_w = (1/k)/sd, sd = std of the piece's Slow daily PnL). Its Slow PnL is estimated as the same-weighted sum of the
piece PnLs (NDX: realized/estimated IR median 1.01, min 0.78).

Kept if: est IR >= --min-ir (0.095), >= 1100 days, summed piece Slow time <= 1500 s, and est submission correlation
(full history, pairwise overlap >= 250 days) <= --cap (0.45, margin under the site's 0.50) with EVERY alpha in
final.json['final'] (submitted + planned add-ons) and with every blend already chosen. Pieces reused <= --reuse.
Greedy by est IR/sqrt(k)-free score = est IR. Output: alphas/submission/<exp>-set.json and
alphas/submission/doc-inputs-<exp>.json (for comments); the jobs are written by --jobs once docs-<exp>.json exists.
"""
import argparse, importlib.util, itertools, json, os, random, re, sys, collections, time
import numpy as np, pandas as pd
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')); os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, 'scripts/submission'))
from subcorr import load_pnl_and_q
spec = importlib.util.spec_from_file_location('cy', 'scripts/composites/cycle.py'); cy = importlib.util.module_from_spec(spec); spec.loader.exec_module(cy)
ap = argparse.ArgumentParser()
ap.add_argument('--exp', default='NDY'); ap.add_argument('--n', type=int, default=60); ap.add_argument('--samples', type=int, default=40000)
ap.add_argument('--cap', type=float, default=0.45); ap.add_argument('--min-ir', type=float, default=0.095); ap.add_argument('--reuse', type=int, default=2)
ap.add_argument('--seed', type=int, default=11); ap.add_argument('--jobs', action='store_true'); ap.add_argument('--priority', type=float, default=4.0)
a = ap.parse_args(); EXP = a.exp.upper(); low = EXP.lower(); SUB = 'alphas/submission'

if a.jobs:
    S = json.load(open(f'{SUB}/{low}-set.json')); D = json.load(open(f'{SUB}/docs-{low}.json'))
    jobs = []
    for i, c in enumerate(S):
        doc = D[c['name']]; assert all(l.startswith('#') for l in doc.split('\n'))
        code = doc.rstrip('\n') + '\n' + re.sub(r'^# packed composite .*\n', '', c['code'])
        compile(code, c['name'], 'exec')
        jobs.append(dict(exp=EXP, name=c['name'], mode='os', code=code, lookback=c['lookback'], priority=round(a.priority - i / 1000, 3), notify=True))
    out = f'alphas/validation/requests/{time.strftime("%Y-%m-%d")}-{low}-jobs.json'; json.dump(jobs, open(out, 'w')); print(out, len(jobs)); sys.exit()

# ---------------------------------------------------------------- themes (same rules as build_set.py)
fam = {}
for l in open('alphas/search/evals.jsonl'):
    try: e = json.loads(l)
    except Exception: continue
    if e.get('families'): fam[e['hash']] = e['families']
def theme(f):
    if f.startswith('id_'): return 'intraday'
    if f.startswith('pv_'): return 'pricevol'
    if f.startswith(('fund_', 'season_')): return 'fundamental'
    return f

# ---------------------------------------------------------------- pieces
lib = cy.build_library(); P = {}
for n, x in lib.items():
    if n.startswith(('101-', 'xcombo')): continue
    if n.startswith(('search-', 'mine-')): th = tuple(sorted({theme(f) for f in fam.get(n.split('-', 1)[1], ['?'])}))
    elif n.startswith('intraday'): th = ('intraday',)
    else: continue
    if '?' in th: continue
    P[n] = dict(code=x['code'], lookback=x['lookback'], pnl=x['pnl'], ir=x['ir'], secs=x['slow_secs'], th=th)
for j in json.load(open('alphas/validation/queue.json')):
    if j['exp'] == 'NDM' and j['mode'] == 'os' and j['status'] == 'done':
        f = f"alphas/validation/NDM/{j['name']}.slow.pnl.csv"
        if not os.path.exists(f): continue
        s = cy.read_pnl(f)
        if len(s) < 1000: continue
        th = tuple(sorted({theme(f) for f in j['meta_nd']['fams']}))
        P['ndm-' + j['name']] = dict(code=j['code'], lookback=int(j['lookback']), pnl=s, ir=float(j['ir']), secs=int(j.get('secs') or 900), th=th)
P = {n: x for n, x in P.items() if x['ir'] >= 0.03 and x['pnl'].std() > 0}
print('pieces', len(P), collections.Counter(x['th'] for x in P.values()).most_common(8))

# ---------------------------------------------------------------- pool (submitted + planned add-ons), full history
pnl, q = load_pnl_and_q()
final = json.load(open(f'{SUB}/final.json'))['final']
pool = pd.DataFrame({n: pnl[n] for n in final if n in pnl}); print('pool', pool.shape[1], 'of', len(final))
names = list(P); idx = pool.index.union(pd.DatetimeIndex(sorted(set().union(*[P[n]['pnl'].index for n in names]))))
Q = pd.DataFrame({n: P[n]['pnl'] for n in names}).reindex(idx); QV = Q.notna().values; sd = Q.std().values; Q0 = Q.fillna(0).values
PP = pool.reindex(idx); PM = PP.notna().values.astype(float); P0 = PP.fillna(0).values
Sp, Sp2 = None, None

def est(W):
    """W: K x C weights -> (E T x C est PnL with NaN where no piece is live)."""
    E = Q0 @ W; live = (QV.astype(float) @ (W != 0).astype(float)) > 0
    return np.where(live, E, np.nan)
def corr_to(E, P0, PM):
    """pairwise-overlap Pearson of each column of E (T x C) with each column of P0 (T x N) -> N x C."""
    V = (~np.isnan(E)).astype(float); E0 = np.nan_to_num(E)
    n = PM.T @ V; se = PM.T @ E0; se2 = PM.T @ (E0 ** 2); sp = P0.T @ V; sp2 = (P0 ** 2).T @ V; sep = P0.T @ E0
    cov = sep - se * sp / np.maximum(n, 1); ve = se2 - se ** 2 / np.maximum(n, 1); vp = sp2 - sp ** 2 / np.maximum(n, 1)
    c = cov / np.sqrt(np.maximum(ve * vp, 1e-30)); c[n < 250] = np.nan; return c

# ---------------------------------------------------------------- candidates
rng = random.Random(a.seed); groups = collections.defaultdict(list)
for i, n in enumerate(names): groups[P[n]['th']].append(i)
groups = {t: g for t, g in groups.items() if len(g) >= 2}
seen, cands = set(), []
gl = list(groups); gw = [len(groups[t]) for t in gl]
for _ in range(a.samples * 3):
    if len(cands) >= a.samples: break
    t = rng.choices(gl, gw)[0]; g = groups[t]; k = rng.choice([2, 3, 3, 4, 4])
    if len(g) < k: continue
    c = tuple(sorted(rng.sample(g, k)))
    if c in seen or sum(P[names[i]]['secs'] for i in c) > 1500: continue
    if not any(names[i].startswith('ndm-') for i in c) and rng.random() < 0.5: continue    # lean toward the orthogonal NDM pieces
    seen.add(c); cands.append(c)
print('candidates', len(cands))
keep = []
for b in range(0, len(cands), 2000):
    cs = cands[b:b + 2000]; W = np.zeros((len(names), len(cs)))
    for j, c in enumerate(cs):
        for i in c: W[i, j] = (1 / len(c)) / sd[i]
    E = est(W); m = np.nanmean(E, 0); s = np.nanstd(E, 0); ir = m / s; days = (~np.isnan(E)).sum(0)
    ok = (ir >= a.min_ir) & (days >= 1100)
    if not ok.any(): continue
    C = corr_to(E[:, ok], P0, PM); mx = np.nanmax(C, 0)
    for j, jj in enumerate(np.where(ok)[0]):
        if mx[j] <= a.cap: keep.append((float(ir[jj]), cs[jj], float(mx[j])))
keep.sort(key=lambda x: -x[0]); print('pass IR + pool corr', len(keep))

# ---------------------------------------------------------------- greedy: mutual corr, piece reuse
chosen, use = [], collections.Counter(); CH = np.zeros((len(idx), 0)); CHM = np.zeros((len(idx), 0))
for ir_, c, mx in keep:
    if len(chosen) >= a.n: break
    if any(use[i] >= a.reuse for i in c): continue
    W = np.zeros((len(names), 1))
    for i in c: W[i, 0] = (1 / len(c)) / sd[i]
    E = est(W)
    if CH.shape[1]:
        cc = corr_to(E, CH, CHM)
        if np.nanmax(cc) > a.cap: continue
    CH = np.hstack([CH, np.nan_to_num(E)]); CHM = np.hstack([CHM, (~np.isnan(E)).astype(float)])
    for i in c: use[i] += 1
    chosen.append(dict(comps=[names[i] for i in c], pos_w=[float(W[i, 0]) for i in c], est_ir=ir_, est_corr_pool=mx, themes=list(P[names[c[0]]]['th'])))
print('chosen', len(chosen))

# ---------------------------------------------------------------- render + outputs
lib2 = {n: dict(code=P[n]['code'], lookback=P[n]['lookback']) for n in names}
out, inputs = [], []
for i, ch in enumerate(chosen):
    nm = f'nyb-{i:03d}' if low == 'ndy' else f'{low}b-{i:03d}'
    code = cy.render(lib2, ch['comps'], ch['pos_w'], nm)
    lb = max(P[n]['lookback'] for n in ch['comps']) + 10
    out.append(dict(name=nm, kind='composite', code=code, lookback=lb, **ch))
    inputs.append(dict(name=nm, kind='equal-weight themed blend', themes=ch['themes'], est_ir=round(ch['est_ir'], 3),
                       parts=[dict(slot=f'_c{k}', source=n) for k, n in enumerate(ch['comps'])], code=re.sub(r'^# packed composite .*\n', '', code)))
json.dump(out, open(f'{SUB}/{low}-set.json', 'w'), indent=1); json.dump(inputs, open(f'{SUB}/doc-inputs-{low}.json', 'w'), indent=1)
irs = sorted(x['est_ir'] for x in out)
print(f'{SUB}/{low}-set.json', len(out), 'est IR median', round(irs[len(irs) // 2], 3) if irs else None,
      'themes', collections.Counter('+'.join(x['themes']) for x in out).most_common())
