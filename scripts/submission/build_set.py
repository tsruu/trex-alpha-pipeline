#!/usr/bin/env python3
"""Build the submission set: logic first, then correlation.

Candidates, in order of how clearly their logic can be stated:
  tier 1  hand-written intraday hypotheses; single-theme search/mined formulas
  tier 2  NEW themed composites: every component shares one theme (intraday / fundamental / price-volume)
  tier 3  interaction singles (a formula spanning two themes)
  tier 4  NEW themed composites whose components all share the same two-theme interaction
  tier 5  existing composites with <= 2 themes and no legacy-101 piece
  tier 6  existing composites with 3 themes and no legacy-101 piece
  tier 7  last-resort fill: existing composites with a legacy-101 piece or 4+ themes
Legacy 101 singles (published 2015, decayed) are excluded.

Greedy: walk tiers in order; inside a tier prefer the candidate with the lowest summed |corr| to the set so far.
A candidate joins if its 2020-01-08..2021-12-30 PnL correlation with every member is <= 0.5 (<= 0.45 for new
composites, whose PnL is still an estimate). New composites need estimated IR >= 0.095 (realized/estimate has
10th pct 0.93), use each component at most PIECE_REUSE times, and keep summed component Slow time <= 1500 s.
Output: alphas/submission/set.json (+ set-summary.md).
"""
import importlib.util, json, os, re, sys, collections, argparse
import numpy as np, pandas as pd
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
spec = importlib.util.spec_from_file_location('cy', os.path.join(ROOT, 'scripts/composites/cycle.py')); cy = importlib.util.module_from_spec(spec); spec.loader.exec_module(cy)
ap = argparse.ArgumentParser(); ap.add_argument('--target', type=int, default=270); ap.add_argument('--samples', type=int, default=12000)
ap.add_argument('--piece-reuse', type=int, default=5); ap.add_argument('--reserve', type=int, default=40); ap.add_argument('--seed', type=int, default=7); a = ap.parse_args()
os.chdir(ROOT); W0, W1 = cy.W0, cy.W1
fix = lambda p: os.path.join(ROOT, re.sub(r'^.*?/trex-alpha/', '', p))

# ---------------------------------------------------------------- themes
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
def piece_themes(n):
    if n.startswith(('search-', 'mine-')): return tuple(sorted({theme(f) for f in fam.get(n.split('-', 1)[1], ['?'])}))
    if n.startswith('intraday'): return ('intraday',)
    return (n.split('-')[0],)
def piece_fams(n):
    if n.startswith(('search-', 'mine-')): return sorted(set(fam.get(n.split('-', 1)[1], [])))
    return ['intraday_hypothesis'] if n.startswith('intraday') else [n.split('-')[0]]
BAD = ('101', 'xcombo', '?')

# ---------------------------------------------------------------- existing qualified alphas
lib = cy.build_library()
cj = json.load(open('alphas/research/slow-correlation.json'))
def rec(n):
    p = f'alphas/research/candidates/{n}.json'
    return json.load(open(p)) if os.path.exists(p) else None
items = []
for x in cj['alphas']:
    n = x['name']; r = rec(n); s = cy.read_pnl(fix(x['source_pnl_csv']))
    if n.startswith('cmp-'):
        comps = r['metadata']['composite']['components']; th = sorted({t for c in comps for t in piece_themes(c)})
        bad = any(c.startswith(('101', 'xcombo')) for c in comps)
        tier = 7 if bad or len(th) >= 4 else 5 if len(th) <= 2 else 6
        items.append(dict(name=n, kind='composite', tier=tier, comps=comps, themes=th, fams=sorted({f for c in comps for f in piece_fams(c)}),
                          pnl=s, ir=float(x['ir']), tvr=float(x['tvr']), code=r['code'], lookback=r.get('slow_lookback_buffered') or r.get('required_lookback'), new=False))
    else:
        th = piece_themes(n)
        if any(t in BAD for t in th): continue
        tier = 1 if (n.startswith('intraday') or len(th) == 1) else 3
        code = (lib.get(n) or {}).get('code') or (r or {}).get('code')
        lb = (lib.get(n) or {}).get('lookback') or (r or {}).get('slow_lookback_buffered')
        items.append(dict(name=n, kind='single', tier=tier, comps=[n], themes=list(th), fams=piece_fams(n), pnl=s, ir=float(x['ir']),
                          tvr=float(x['tvr']), code=code, lookback=lb, new=False))
print('existing candidates by tier:', dict(collections.Counter(i['tier'] for i in items)))

# ---------------------------------------------------------------- new themed composites
P = pd.DataFrame({k: v['pnl'] for k, v in lib.items()}).sort_index(); Wm = (P.index >= W0) & (P.index <= W1)
Q = P.fillna(0.0); sd = Q.std(); Q = Q / sd
rng = np.random.default_rng(a.seed); new = []
groups = collections.defaultdict(list)
for k in lib:
    th = piece_themes(k)
    if lib[k]['ir'] >= 0.03 and not any(t in BAD for t in th): groups[th].append(k)
for th, comp in groups.items():
    if len(comp) < 2: continue
    Qv = Q[comp].values; Cc = np.corrcoef(Qv[Wm].T); rt = np.array([lib[c]['slow_secs'] for c in comp]); seen = set()
    for k in (2, 3, 4):
        for _ in range(a.samples):
            idx = rng.choice(len(comp), k, replace=False); key = tuple(sorted(idx))
            if key in seen or rt[idx].sum() > 1500 or Cc[np.ix_(idx, idx)][np.triu_indices(k, 1)].max() > 0.5: continue
            seen.add(key); w = rng.dirichlet(np.ones(k) * 2); x = Qv[:, idx] @ w; e = x.mean() / x.std()
            if e >= 0.095:
                names = [comp[i] for i in idx]
                new.append(dict(name=None, kind='composite', tier=2 if len(th) == 1 else 4, comps=names, themes=list(th),
                                fams=sorted({f for c in names for f in piece_fams(c)}), pnl=pd.Series(x, index=P.index), ir=float(e),
                                tvr=None, pos_w=[float(v / sd[n]) for v, n in zip(w, names)], est_secs=int(rt[idx].sum()),
                                lookback=max(lib[n]['lookback'] for n in names), new=True))
by = collections.defaultdict(list)
for n in new: by[tuple(n['themes'])].append(n)
new = [n for g in by.values() for n in (g if len(g) <= 1200 else [g[i] for i in rng.choice(len(g), 1200, replace=False)])]   # random thin (memory)
print('new themed composite candidates:', dict(collections.Counter((tuple(n['themes']), n['tier']) for n in new)))

# ---------------------------------------------------------------- greedy selection
def win(s): return s[(s.index >= W0) & (s.index <= W1)]
idx_all = pd.date_range(W0, W1, freq='B')
base_idx = win(items[0]['pnl']).index
for it in items + new:
    v = win(it['pnl']).reindex(base_idx).fillna(0.0).values; v = v - v.mean(); it['z'] = v / (np.linalg.norm(v) or 1)
cands = items + new
ZZ = np.array([c['z'] for c in cands], dtype=np.float32); CC = ZZ @ ZZ.T
capv = np.array([0.45 if c['new'] else 0.5 for c in cands], dtype=np.float32)
conf = (CC > np.minimum.outer(capv, capv)); np.fill_diagonal(conf, False)
alive = np.ones(len(cands), bool); chosen = []; use = collections.Counter()
tiers = np.array([c['tier'] for c in cands])
for tier in range(1, 8):
    while len(chosen) < a.target:
        ok = np.where(alive & (tiers == tier))[0]
        ok = [i for i in ok if not cands[i]['new'] or all(use[p] < a.piece_reuse for p in cands[i]['comps'])]
        if not ok: break
        if tier <= 6 and chosen:        # logic tiers: take the most different candidate (lowest summed |corr| to the set)
            score = np.abs(CC[ok][:, chosen]).sum(axis=1)
        else:                           # fill tiers: take the candidate that blocks the fewest others (maximises count)
            score = conf[ok][:, alive].sum(axis=1)
        i = ok[int(np.argmin(score))]; chosen.append(i); alive[i] = False; alive &= ~conf[i]
        if cands[i]['new']:
            for p in cands[i]['comps']: use[p] += 1
    print(f'after tier {tier}: {len(chosen)}')
sel = [cands[i] for i in chosen]

# reserve: verified existing composites outside the set that are <= 0.5 with every VERIFIED member (so any of them
# can replace a new composite that fails), and <= 0.5 with each other; logic tiers first, then fewest conflicts
ver = [i for i in chosen if not cands[i]['new']]
res_ok = [i for i in range(len(cands)) if not cands[i]['new'] and cands[i]['kind'] == 'composite' and i not in set(chosen)
          and not conf[i, ver].any()]
reserve = []
for i in sorted(res_ok, key=lambda i: (cands[i]['tier'], conf[i, res_ok].sum())):
    if len(reserve) >= a.reserve: break
    if not conf[i, reserve].any(): reserve.append(i)
print(f'reserve: {len(reserve)} verified composites (from {len(res_ok)} compatible)')

# ---------------------------------------------------------------- output
for k, c in enumerate(sel):
    if c['new']:
        c['name'] = f"thm-{k:03d}"; c['code'] = cy.render(lib, c['comps'], c['pos_w'], c['name'])
out = [{k: v for k, v in c.items() if k not in ('pnl', 'z')} for c in sel]
json.dump(out, open('alphas/submission/set.json', 'w'), indent=1)
json.dump([{k: v for k, v in cands[i].items() if k not in ('pnl', 'z')} for i in reserve], open('alphas/submission/reserve.json', 'w'), indent=1)
S = np.array([c['z'] for c in sel]) @ np.array([c['z'] for c in sel]).T; iu = np.triu_indices(len(sel), 1)
summary = [f'# Submission set ({len(sel)})', '', f'Mean pairwise corr (2020-21 window): {S[iu].mean():.3f}; max {S[iu].max():.3f}', '',
           '| tier | kind | count |', '|---|---|---:|']
for (t, kd, nw), n in sorted(collections.Counter((c['tier'], c['kind'], c['new']) for c in sel).items()):
    summary.append(f'| {t} | {kd}{" (new)" if nw else ""} | {n} |')
summary += ['', 'Themes: ' + ', '.join(f'{k} {v}' for k, v in collections.Counter(' + '.join(c['themes']) for c in sel).most_common())]
open('alphas/submission/set-summary.md', 'w').write('\n'.join(summary) + '\n'); print('\n'.join(summary))
