#!/usr/bin/env python3
"""Check that the local Slow correlation matrix matches TrexSim's own Compute Correlation, and that the
optimizer's pool is still valid when judged with TrexSim's numbers.

Read-only: one login plus GET requests to /trexsim/pysim/compute_correlation. It submits nothing, so it does
not touch the submit gate or compete with the search/worker. Run on the server, from the repo root:

    python3 scripts/check-correlation-parity.py

Inputs:  alphas/research/slow-correlation.json (local matrix), alphas/research/optimal-pool.json (plan)
Outputs: alphas/research/correlation-parity.json (full comparison) and a printed summary.
"""
import csv, html, itertools, json, math, os, re, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'composites'))
from trex_http import Trex, BASE, ROOT  # noqa: E402

CORR = os.path.join(ROOT, 'alphas', 'research', 'slow-correlation.json')
POOL = os.path.join(ROOT, 'alphas', 'research', 'optimal-pool.json')
OUT = os.path.join(ROOT, 'alphas', 'research', 'correlation-parity.json')
DUMP = os.path.join(ROOT, 'logs', 'compute_correlation.html')
LIMIT, OVERRIDE = 0.5, 1.2


def find_key(obj, key):
    if isinstance(obj, dict):
        if key in obj: return obj[key]
        for v in obj.values():
            r = find_key(v, key)
            if r is not None: return r
    elif isinstance(obj, list):
        for v in obj:
            r = find_key(v, key)
            if r is not None: return r
    return None


def parse_context(text):
    pats = [r'<script[^>]*id=["\']react-context["\'][^>]*>(.*?)</script>',
            r'(?:data-)?react-context=["\']([^"\']*)["\']',
            r'react-context["\']?\s*[:=]\s*(\{.*?\})\s*;?\s*</script>']
    for p in pats:
        for m in re.finditer(p, text, re.S):
            raw = html.unescape(m.group(1)).strip()
            try:
                ctx = json.loads(raw)
            except Exception:
                continue
            if find_key(ctx, 'correlation_matrix') is not None:
                return ctx
    return None


def fetch(trex, ids):
    url = f"{BASE}/trexsim/pysim/compute_correlation?alpha_ids={','.join(ids)}"
    r = trex.s.get(url, timeout=180)
    ctx = parse_context(r.text) if r.status_code == 200 else None
    if ctx is None:
        os.makedirs(os.path.dirname(DUMP), exist_ok=True)
        open(DUMP, 'w').write(r.text)
        raise RuntimeError(f'could not read the correlation report (HTTP {r.status_code}); page saved to {DUMP}')
    cm = find_key(ctx, 'correlation_matrix')
    rids = [str(x) for x in cm['alpha_ids']]
    vals = cm['values']
    window = (str(find_key(ctx, 'start_date')), str(find_key(ctx, 'end_date')))
    out = {}
    for i, a in enumerate(rids):
        for j, b in enumerate(rids):
            if i < j and vals[i][j] is not None:
                out[frozenset((a, b))] = float(vals[i][j])
    return out, window, rids


def main():
    local = json.load(open(CORR)); pool = json.load(open(POOL))
    ids = [str(x) for x in local['alpha_ids']]
    L = {}
    for i, a in enumerate(ids):
        for j, b in enumerate(ids):
            if i < j: L[frozenset((a, b))] = float(local['matrix'][i][j])
    print(f'local matrix: {len(ids)} Slow alphas, {len(L)} pairs, window {local["correlation_window"]["start"]}..{local["correlation_window"]["end"]}')

    trex = Trex(); print('logged in; requesting TrexSim Compute Correlation (read-only)')
    T, windows, missing = {}, set(), set()
    try:
        got, w, rids = fetch(trex, ids); T.update(got); windows.add(w)
    except Exception as e:
        print(f'full request failed ({e}); falling back to chunks')
        chunks = [ids[k:k + 30] for k in range(0, len(ids), 30)]
        for a, b in itertools.combinations_with_replacement(range(len(chunks)), 2):
            sub = chunks[a] if a == b else chunks[a] + chunks[b]
            got, w, rids = fetch(trex, sub); T.update(got); windows.add(w); time.sleep(2)
    missing = set(L) - set(T)
    print(f'TrexSim returned {len(T)} pairs; window(s) {sorted(windows)}; pairs missing from TrexSim: {len(missing)}')

    diffs = sorted(((abs(L[k] - T[k]), k) for k in L if k in T), key=lambda x: -x[0])
    flips = [k for k in L if k in T and (L[k] > LIMIT) != (T[k] > LIMIT)]
    near = [k for k in L if k in T and abs(T[k] - LIMIT) < 0.02]
    maxd = diffs[0][0] if diffs else float('nan')
    print(f'\nmax |local - TrexSim| = {maxd:.2e}   mean = {sum(d for d, _ in diffs) / max(1, len(diffs)):.2e}')
    print(f'pairs differing by > 1e-6: {sum(d > 1e-6 for d, _ in diffs)}   by > 0.01: {sum(d > 0.01 for d, _ in diffs)}')
    print(f'pairs whose > 0.50 decision flips: {len(flips)}')
    for d, k in diffs[:5]:
        a, b = sorted(k); print(f'  {a}-{b}: local {L[k]:.6f}  TrexSim {T[k]:.6f}  diff {d:.2e}')

    # Re-validate the planned pool with TrexSim's own numbers.
    order = pool['submission_order']; q = {str(x['id']): float(x['ir_tvr']) for x in order}
    ir = {str(x['id']): float(x['ir']) for x in order}
    # TrexSim reports IR and IR/sqrt(TVR) rounded to 3 decimals. IR itself is mean/std of the full-period daily
    # PnL, so recompute it unrounded and use the stricter of the rounded and unrounded override ratios.
    raw_ir, raw_q = {}, {}
    for a in local['alphas']:
        pth = a['source_pnl_csv']; pth = os.path.join(ROOT, pth[pth.index('alphas/'):]) if 'alphas/' in pth else pth
        try:
            x = [float(r['dailypnl']) for r in csv.DictReader(open(pth)) if r['dailypnl'] not in ('', 'nan')]
            m = sum(x) / len(x); sd = math.sqrt(sum((v - m) ** 2 for v in x) / (len(x) - 1))
            raw_ir[str(a['id'])] = m / sd; raw_q[str(a['id'])] = (m / sd) / math.sqrt(float(a['tvr']))
        except Exception as e:
            print('  could not recompute IR for', a['id'], e)
    irdev = max((abs(raw_ir[k] - ir[k]) for k in ir if k in raw_ir), default=float('nan'))
    print(f'\nIR recomputed from daily PnL vs TrexSim (rounded): max |diff| {irdev:.5f} (0.0005 = rounding only)')
    print(f'lowest unrounded IR in the pool: {min(raw_ir[k] for k in ir if k in raw_ir):.5f} (must be > 0.07)')
    violations, tight = [], []
    for i, x in enumerate(order):
        a = str(x['id'])
        for y in order[:i]:
            b = str(y['id']); c = T.get(frozenset((a, b)))
            if c is None: violations.append((a, b, None, 'no TrexSim value')); continue
            if c > LIMIT:
                ratio = min(q[a] / q[b] if q[b] > 0 else float('inf'),
                            raw_q[a] / raw_q[b] if a in raw_q and b in raw_q and raw_q[b] > 0 else float('inf'))
                if ratio < OVERRIDE: violations.append((a, b, c, f'override ratio {ratio:.3f} < 1.2'))
                elif ratio < 1.25: tight.append((a, b, c, f'override ratio {ratio:.3f}'))
            elif c > LIMIT - 0.02: tight.append((a, b, c, 'correlation within 0.02 of 0.50'))
    low_ir = [a for a in ir if min(ir[a], raw_ir.get(a, 1)) <= 0.0705]
    print(f'\nplanned pool: {len(order)} alphas; violations under TrexSim numbers: {len(violations)}')
    for v in violations[:20]: print('  VIOLATION', v)
    print(f'borderline admissions (still valid, but close): {len(tight)}; pool members with IR <= 0.0705: {len(low_ir)}')
    for t in tight[:20]: print('  close:', t)

    ok = not violations and not flips and not missing and maxd < 1e-6
    print('\nRESULT:', 'PASS - local correlations match TrexSim and the pool is valid under its numbers' if ok else 'CHECK THE DETAILS ABOVE')
    json.dump({'checked_at': time.strftime('%Y-%m-%d %H:%M %Z'), 'n_alphas': len(ids), 'n_pairs': len(L),
               'trexsim_windows': sorted(windows), 'max_abs_diff': maxd, 'decision_flips': [sorted(k) for k in flips],
               'missing_pairs': [sorted(k) for k in missing], 'near_limit_pairs': len(near),
               'pool_size': len(order), 'pool_violations': violations, 'pool_borderline': tight, 'pool_low_ir': low_ir,
               'top_diffs': [{'pair': sorted(k), 'local': L[k], 'trexsim': T[k]} for _, k in diffs[:20]], 'pass': ok},
              open(OUT, 'w'), indent=1)
    print(f'details: {os.path.relpath(OUT, ROOT)}')


if __name__ == '__main__':
    main()
