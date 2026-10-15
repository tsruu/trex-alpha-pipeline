#!/usr/bin/env python3
"""Submission correlation: the correlation TrexSim's submission gate actually uses.

Two different correlations exist in this project; do not mix them up.

  submission correlation  Pearson correlation of two alphas' Slow daily PnL over their FULL history, on the dates
                          both have (pairwise overlap). This is what the "Max Correlation to Pool" check on the
                          Submit dialog uses; it reproduces the site's numbers to 3 decimals (0.555, 0.585, 0.601 ...).
                          Admission: <= 0.50 against every submitted alpha, or IR/sqrt(TVR) >= 1.2x every alpha it
                          exceeds 0.50 with. Order matters.
  window correlation      the same but restricted to 2020-01-08..2021-12-30. This is what TrexSim's "Compute
                          Correlation" report shows (and what trexsim-correlate-local.py / the pool optimizer use).
                          Useful for diversity work; NOT sufficient for submission.

Usage:
  python3 scripts/submission/subcorr.py --check alphas/submission/final.json
      walks final.json['final'] in order and reports every alpha the gate would reject
"""
import argparse, json, os, re, sys
import numpy as np, pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
MIN_OVERLAP = 250          # days both alphas must share for a correlation to count
CAP, OVERRIDE = 0.50, 1.2


def submission_corr_matrix(pnl: dict) -> pd.DataFrame:
    """pnl: name -> daily PnL Series (date index). Full history, pairwise overlap."""
    return pd.DataFrame(pnl).corr(min_periods=MIN_OVERLAP)


def admissible(name, pool, C, q):
    """Would `name` pass the gate given everything in `pool` is already submitted?"""
    hi = [m for m in pool if C.loc[name, m] > CAP]
    return all(q[name] >= OVERRIDE * q[m] for m in hi), hi


def plan_order(prefix, candidates, C, q):
    """Greedy admission order after a fixed, already-submitted prefix: repeatedly admit the admissible candidate
    that blocks the fewest remaining candidates. Returns (order, left_out)."""
    pool, left, order = list(prefix), [c for c in candidates if c not in prefix], []
    while True:
        ok = [n for n in left if admissible(n, pool, C, q)[0]]
        if not ok: return order, left
        best = min(ok, key=lambda n: int((C.loc[n, [k for k in left if k != n]] > CAP).sum()))
        pool.append(best); left.remove(best); order.append(best)


def load_pnl_and_q():
    """Slow PnL + IR/sqrt(TVR) for every qualified alpha and every finished final-run job."""
    fix = lambda p: os.path.join(ROOT, re.sub(r'^.*?/trex-alpha/', '', p))
    rd = lambda f: (lambda s: s.set_axis(pd.to_datetime(s['date']))['dailypnl'])(pd.read_csv(f))
    pnl, q = {}, {}
    for a in json.load(open(os.path.join(ROOT, 'alphas/research/slow-correlation.json')))['alphas']:
        pnl[a['name']] = rd(fix(a['source_pnl_csv'])); q[a['name']] = float(a['ir']) / np.sqrt(float(a['tvr']))
    for j in json.load(open(os.path.join(ROOT, 'alphas/validation/queue.json'))):
        if j.get('exp') in ('SUBN', 'SUBV', 'SUBR', 'SUBX', 'NDX', 'ADD', 'NDY') and j.get('status') == 'done' and j['name'] not in pnl:
            f = os.path.join(ROOT, 'alphas/validation', j['exp'], f"{j['name']}.slow.pnl.csv")
            if os.path.exists(f): pnl[j['name']] = rd(f); q[j['name']] = float(j['ir']) / np.sqrt(float(j['tvr']))
    return pnl, q


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--check', required=True); a = ap.parse_args()
    order = json.load(open(a.check))['final']; pnl, q = load_pnl_and_q()
    missing = [n for n in order if n not in pnl]
    C = submission_corr_matrix({n: pnl[n] for n in order if n in pnl}); pool, bad = [], []
    for n in order:
        if n not in pnl: continue
        ok, hi = admissible(n, pool, C, q)
        if ok: pool.append(n)
        else: bad.append((n, hi[:3], round(float(C.loc[n, hi].max()), 3)))
    print(f'{len(pool)} of {len(order)} pass in order; {len(bad)} would be rejected; {len(missing)} without PnL yet')
    for b in bad: print('  reject', *b)
