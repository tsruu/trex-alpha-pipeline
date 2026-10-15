#!/usr/bin/env python3
"""Composite pipeline cycle. Idempotent; run every 1-2 hours while sim-queue-worker.js runs.

  1. INGEST   finished Slow composites -> research candidate records (cmp-<hash>) + archives
  2. POOL     if anything was ingested: Slow correlation rebuild + pool optimizer
  3. SCREEN   finished Fast composites: realized vs PnL-sum estimate -> Slow jobs (inbox)
  4. REPACK   when the pipeline runs low: rebuild component library, pack new composites -> Fast jobs (inbox)
  0. KEEPERS  (replaces the search's nightly Slow window) finished keeper Slow runs -> candidate records via
              trexsim-ingest-research-results.js; then fast triage + Slow manifest -> new keeper Slow jobs (priority 0)
  5. MINE     when few Slow jobs are queued: Slow-run unrun search hits that point in new directions (components need
              not qualify alone); finished ones become library components (and candidates if Slow IR > 0.07)

The worker is the only writer of alphas/validation/queue.json; this script only reads it and drops job
files into alphas/validation/inbox/. State: alphas/composites/state.json. Log: alphas/composites/cycle.log.
Usage: python3 scripts/composites/cycle.py [--no-repack] [--pack-n 40] [--low-water 40] [--dry-run]
"""
import argparse, datetime as dt, glob, hashlib, json, os, re, shutil, subprocess, sys, textwrap, time
import numpy as np, pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
A = os.path.join(ROOT, 'alphas')
VAL = os.path.join(A, 'validation'); QFILE = os.path.join(VAL, 'queue.json'); INBOX = os.path.join(VAL, 'inbox')
WORK = os.path.join(A, 'composites'); STATE = os.path.join(WORK, 'state.json'); LOG = os.path.join(WORK, 'cycle.log')
CAND = os.path.join(A, 'research', 'candidates'); RES = os.path.join(A, 'research', 'results')
POOLF = os.path.join(A, 'research', 'optimal-pool.json')
W0, W1 = '2020-01-08', '2021-12-30'
EXCLUDE_COMPONENTS = {'101-alpha-41'}          # raw dollar-valued: TrexSim neutralization is not a mean demean
SKIP_EXPS = {'A1', 'A2', 'A4', 'A5', 'B', 'C', 'P2', 'worker-test'}   # validation experiments (duplicates/controls)

def log(*a):
    msg = dt.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S') + ' ' + ' '.join(str(x) for x in a)
    print(msg, flush=True); open(LOG, 'a').write(msg + '\n')

def jload(p, d=None):
    try: return json.load(open(p))
    except Exception: return d

def jsave(p, obj):
    tmp = p + '.tmp'; json.dump(obj, open(tmp, 'w'), indent=1); os.replace(tmp, p)

def read_pnl(p):
    s = pd.read_csv(p)
    s = s.set_index('date')['dailypnl']; s.index = pd.to_datetime(s.index); return s

def ir(x): x = x.dropna(); return float(x.mean() / x.std()) if len(x) > 10 and x.std() > 0 else 0.0

def to_inbox(jobs, tag):
    if not jobs: return
    os.makedirs(INBOX, exist_ok=True)
    p = os.path.join(INBOX, f'{int(time.time()*1000)}-{tag}.json'); jsave(p, jobs)
    log(f'inbox: {len(jobs)} {tag} job(s) -> {os.path.basename(p)}')

def is_composite(j): return bool(j.get('meta')) and j.get('exp') not in SKIP_EXPS

# ------------------------------------------------------------------ library of Slow-grade components
def build_library():
    lib = {}
    files = sorted(glob.glob(os.path.join(RES, '*', 'slow-*.json')) + glob.glob(os.path.join(A, 'results', '101-alpha-*', 'slow-*.json'))
                   + glob.glob(os.path.join(A, 'research-archive', '**', 'slow-*.json'), recursive=True))
    for f in files:
        name = f.split(os.sep)[-2]
        if name in lib or name.startswith(('smoke', 'cmp-')) or name in EXCLUDE_COMPONENTS: continue
        pf = f[:-5] + '.pnl.csv'
        if not os.path.exists(pf): continue
        try:
            d = json.load(open(f)); m = d['stats_data']['metrics']; s = read_pnl(pf)
        except Exception: continue
        if len(s) < 1500 or not str(m.get('ir', '')).strip(): continue
        rt = re.search(r'runtime\s*:\s*(\d+)', d.get('os_text', '') or '')
        fj = sorted(glob.glob(os.path.join(os.path.dirname(f), 'fast-*.pnl.csv')))
        lib[name] = dict(code=d['expression'], lookback=int(d.get('lookback') or 300), ir=float(m['ir']), tvr=float(m['tvr']),
                         pnl=s, slow_secs=int(rt.group(1)) if rt else 600, fast_pnl=fj[0] if fj else None)
    return lib

# ------------------------------------------------------------------ rendering (per-component lookback slicing in Slow)
UNIT = '''def _unit(x):
    x = cs_indneut(x, industry)
    g = np.nansum(np.abs(x), axis=0)
    x = np.where(g > 0, x / np.where(g > 0, g, 1.0), np.nan)
    return at_nan2zero(x)
def _win(L):
    T = close.shape[1]
    return None if T > 1500 else max(1, T - L)
def _pad(a, full):
    if a.shape[1] == full.shape[1]:
        return a
    out = np.full(full.shape, np.nan)
    out[:, -a.shape[1]:] = a
    return out
'''
_DV = None
def datavars(code):
    global _DV
    if _DV is None: _DV = {x['varname'] for x in json.load(open(os.path.join(ROOT, 'data-distribution.json')))['items']}
    return sorted(set(re.findall(r'\b[a-z_][a-z0-9_]*\b', code)) & _DV)

def render(lib, names, pos_w, label):
    parts = [f'# packed composite {label}: ' + ' + '.join(names), UNIT]; lines = []
    for i, n in enumerate(names):
        code = lib[n]['code'].replace('\t', '    ')
        if not re.search(r'^alpha\s*=', code, re.M): raise ValueError(n + ': no alpha =')
        dv = datavars(code)
        parts.append(f'def _c{i}({", ".join(dv)}):\n    # {n}\n' + textwrap.indent(code.rstrip() + '\nreturn alpha', '    ') + '\n')
        lines.append(f'_s{i} = _win({lib[n]["lookback"] + 5})')
        lines.append(f'_a{i} = _pad(_c{i}(' + ', '.join(f'({v} if _s{i} is None else {v}[:, _s{i}:])' for v in dv) + '), close)')
    s = ' + '.join(f'{w:.6g} * _unit(_a{i})' for i, w in enumerate(pos_w))
    code = '\n'.join(parts) + '\n'.join(lines) + f'\nalpha = {s}\nalpha = np.where(alpha == 0, np.nan, alpha)'
    compile(code, label, 'exec'); return code


# ------------------------------------------------------------------ 0. search keepers (was the nightly Slow window)
def run_step(label, cmd, timeout=1800):
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0: log(f'{label} FAILED (exit {r.returncode}):', (r.stderr or r.stdout)[-600:])
    return r

def ingest_keepers(queue, state, dry):
    done = state.setdefault('keepers', {}); results = []; keys = []
    for j in queue:
        if not j.get('keeper') or j.get('mode') != 'os': continue
        key = f"{j['exp']}/{j['name']}"
        if key in done or j.get('status') in ('pending', 'submitted'): continue
        if j.get('status') == 'done':
            rp = os.path.join(VAL, j['exp'], f"{j['name']}.slow.raw.json")
            raw = jload(rp)
            if raw is None: log('keeper ingest: missing raw result for', key); continue
            results.append({'n': j['name'], 'raw': raw, 'lookback': j.get('lookback')})
        else:
            results.append({'n': j['name'], 'requested_mode': 'slow', 'error': f"worker: {j.get('status')} {j.get('detail', '')}"[:300]})
        keys.append((key, j))
    if not results: return 0
    if dry: log(f'keeper ingest (dry): {len(results)}'); return len(results)
    tmp = os.path.join(WORK, 'keeper-results.tmp.json'); jsave(tmp, results)
    r = run_step('keeper ingest', ['node', 'scripts/trexsim-ingest-research-results.js', tmp], 600)
    if r.returncode != 0: return 0
    q = 0
    for key, j in keys:
        done[key] = round(float(j.get('ir') or 0), 4) if j.get('status') == 'done' else 'error'
        q += j.get('status') == 'done' and float(j.get('ir') or 0) > 0.07
    log(f'keeper ingest: {len(keys)} Slow result(s), {q} qualified')
    return len(keys)

def queue_keepers(queue, dry):
    if not dry: run_step('fast triage', ['python3', 'scripts/trexsim-fast-triage.py'], 900)
    r = run_step('slow manifest', ['node', 'scripts/trexsim-research-manifest.js', 'slow'], 300)
    try: entries = json.loads(r.stdout) if r.returncode == 0 else []
    except Exception: entries = []
    have = {j['name'] for j in queue if j.get('keeper')}
    jobs = []
    for e in entries:
        cid = e['n']
        if cid in have: continue
        rec = jload(os.path.join(CAND, cid + '.json'), {}) or {}
        fast = ((rec.get('runs') or {}).get('fast') or {}).get('result') or {}
        fj = jload(os.path.join(ROOT, fast.get('archive_json') or '_none_'), {}) or {}
        code = fj.get('expression') or rec.get('code')        # Slow re-runs the exact Fast expression
        if not code: continue
        jobs.append(dict(exp=None, name=cid, mode='os', code=code, lookback=int(e['lookback']), fast_id=str(e['fast_id']),
                         keeper=True, keep_raw=True, priority=0.0))
    log(f'keepers: manifest {len(entries)}, new Slow jobs {len(jobs)}')
    if dry or not jobs: return len(jobs)
    n = len({j['exp'] for j in queue if j.get('keeper')}) + 1
    for j in jobs: j['exp'] = f'S{n:03d}'
    to_inbox(jobs, 'keepers')
    return len(jobs)

def refresh_frontier():
    # what the nightly cycle did after the pool optimizer; the search reloads master-frontier.json when it changes
    run_step('campaign sync', ['node', 'scripts/trexsim-research-campaign.js', 'sync'], 600)
    run_step('factory refresh', ['node', 'scripts/trexsim-refresh-factory-context.js'], 600)

# ------------------------------------------------------------------ 1. ingest
def ingest(queue, state, dry):
    fast_by_id = {j.get('id'): j for j in queue if j.get('mode') == 'os_fast'}
    new = []
    for j in queue:
        if j.get('mode') != 'os' or j.get('status') != 'done' or not is_composite(j): continue
        key = f"{j['exp']}/{j['name']}"
        if key in state['ingested']: continue
        cid = 'cmp-' + hashlib.sha1(j['code'].encode()).hexdigest()[:12]
        src = os.path.join(VAL, j['exp'])
        sj, sp = os.path.join(src, f"{j['name']}.slow.json"), os.path.join(src, f"{j['name']}.slow.pnl.csv")
        if not (os.path.exists(sj) and os.path.exists(sp)): log('ingest: missing slow files for', key); continue
        fj = fast_by_id.get(j.get('fast_id')) or {}
        ff, fp = os.path.join(src, f"{j['name']}.fast.json"), os.path.join(src, f"{j['name']}.fast.pnl.csv")
        if dry: new.append(cid); continue
        out = os.path.join(RES, cid); os.makedirs(out, exist_ok=True)
        shutil.copy(sj, os.path.join(out, f"slow-{j['id']}.json")); shutil.copy(sp, os.path.join(out, f"slow-{j['id']}.pnl.csv"))
        runs = {'fast': {'status': 'not_eligible', 'result': None, 'error': None}}
        if fj.get('id') and os.path.exists(ff) and os.path.exists(fp):
            shutil.copy(ff, os.path.join(out, f"fast-{fj['id']}.json")); shutil.copy(fp, os.path.join(out, f"fast-{fj['id']}.pnl.csv"))
            runs['fast'] = {'status': 'success', 'error': None, 'result': {'id': str(fj['id']), 'ir': float(fj.get('ir') or 0), 'turnover': float(fj.get('tvr') or 0),
                            'ir_tvr': float(fj.get('ir_tvr') or 0), 'mode': 'os_fast', 'lookback': j.get('lookback'),
                            'archive_json': f"alphas/research/results/{cid}/fast-{fj['id']}.json", 'archive_pnl_csv': f"alphas/research/results/{cid}/fast-{fj['id']}.pnl.csv"}}
        sir = float(j.get('ir') or 0)
        runs['slow'] = {'status': 'success', 'error': None, 'result': {'id': str(j['id']), 'ir': sir, 'turnover': float(j.get('tvr') or 0),
                        'ir_tvr': float(j.get('ir_tvr') or 0), 'mode': 'os', 'lookback': j.get('lookback'),
                        'archive_json': f"alphas/research/results/{cid}/slow-{j['id']}.json", 'archive_pnl_csv': f"alphas/research/results/{cid}/slow-{j['id']}.pnl.csv"}}
        m = j['meta']
        rec = {'candidate_id': cid, 'title': f"Packed composite {j['exp']}/{j['name']} ({len(m['components'])} components)",
               'status': 'qualified' if sir > 0.07 else 'slow_rejected', 'code': j['code'],
               'inputs': {'primary_cluster': 'composite', 'primary_variables': [], 'secondary_clusters': [], 'secondary_variables': []},
               'metadata': {'hypothesis': 'PnL-algebra composite of Slow-verified alphas, weights chosen offline from their Slow PnLs.',
                            'neutralized': True, 'mechanism_classification': 'composite',
                            'composite': {'components': m['components'], 'pos_w': m['pos_w'], 'est_ir': m.get('est_ir'),
                                          'est_max_corr': m.get('est_max_corr'), 'queue_key': key}},
               'lineage': {'family_id': cid, 'root_candidate_id': cid, 'parent_candidate_id': None, 'generation': 0, 'stage': 'manual',
                           'changes': {'purpose': 'composite'}},
               'required_lookback': j.get('lookback'), 'slow_lookback_buffered': j.get('lookback'), 'runs': runs}
        jsave(os.path.join(CAND, cid + '.json'), rec)
        state['ingested'][key] = cid; new.append(cid)
        log(f"ingest {key} -> {cid}: Slow IR {sir:.3f} (est {m.get('est_ir', 0):.3f}) {'QUALIFIED' if sir > 0.07 else 'rejected'}")
    return new

# ------------------------------------------------------------------ 2. pool
def pool_names():
    p = jload(POOLF, {}) or {}
    return [(r.get('alpha') or r.get('name')) for r in p.get('submission_order', [])]

def rebuild_pool():
    before = len(pool_names())
    for cmd in (['python3', 'scripts/trexsim-correlate-local.py', '--source', 'all', '--mode', 'slow', '--ir-min', '0.07', '--ir-strict',
                 '--start', W0, '--end', W1, '--output', 'alphas/research/slow-correlation.json'],
                ['python3', 'scripts/trexsim-optimize-pool.py', 'alphas/research/slow-correlation.json', '--output', 'alphas/research/optimal-pool.json',
                 '--timeout-seconds', '900']):
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if r.returncode != 0: log('POOL STEP FAILED', ' '.join(cmd[:2]), r.stderr[-800:]); return
    log(f'pool: {before} -> {len(pool_names())}')

# ------------------------------------------------------------------ 3. screen
def screen(queue, state, lib, dry):
    have_slow = {(j['exp'], j['name']) for j in queue if j.get('mode') == 'os'}
    jobs = []
    for j in queue:
        if j.get('mode') != 'os_fast' or not is_composite(j): continue
        key = f"{j['exp']}/{j['name']}"
        if key in state['screened'] or (j['exp'], j['name']) in have_slow: state['screened'].setdefault(key, 'had-slow'); continue
        if j.get('status') != 'done':
            if str(j.get('status', '')).startswith('error'): state['screened'][key] = 'fast-error'
            continue
        m = j['meta']; names, w = m['components'], m['pos_w']
        fp = os.path.join(VAL, j['exp'], f"{j['name']}.fast.pnl.csv")
        try: act = read_pnl(fp)
        except Exception: state['screened'][key] = 'no-pnl'; continue
        refs = [read_pnl(lib[n]['fast_pnl']) if n in lib and lib[n].get('fast_pnl') else None for n in names]
        a_ir = ir(act)
        if all(r is not None for r in refs):
            # Compare only on dates every component has Fast PnL for. Component Fast PnLs start in different years
            # (lookback) and mined ones cover only 2020-21; zero-filling the gaps made good composites fail
            # (corr 0.5-0.85 with ratio > 1): 181 of 260 screen failures before 2026-09-25 were this artefact.
            idx = act.index
            for r in refs: idx = idx.intersection(r.index)
            est = sum(wi * r.reindex(idx) for wi, r in zip(w, refs)); a = act.reindex(idx)
            ratio = ir(a) / max(ir(est), 1e-9); c = float(np.corrcoef(est.values, a.values)[0, 1])
            ok = ratio >= 0.9 and c >= 0.9; why = f'ratio {ratio:.2f} corr {c:.2f}'
        else:
            ok = a_ir >= 0.09; why = f'no component Fast PnL; Fast IR {a_ir:.3f}'
        state['screened'][key] = ('pass ' if ok else 'fail ') + why
        if ok: jobs.append(dict(exp=j['exp'], name=j['name'], mode='os', code=j['code'], lookback=j['lookback'], fast_id=j['id'], meta=m,
                                priority=(m.get('est_ir', 0.1) - 0.07) / np.sqrt(max(m.get('est_secs', 900), 60))))
    jobs.sort(key=lambda x: -x['priority'])
    log(f"screen: {sum(1 for k, v in state['screened'].items() if v.startswith('pass'))} passed total; {len(jobs)} new Slow job(s)")
    if not dry: to_inbox(jobs, 'slow')


# ------------------------------------------------------------------ 3b. pool-aware Slow priorities
def pool_fit(queue, lib):
    """Re-rank pending composite Slow jobs against the CURRENT pool. Composites are packed hours before they run,
    and the pool keeps growing, so by run time many are >= 0.5 correlated with pool members (estimate = weighted sum
    of component Slow PnLs, which matches the realized Slow PnL at median corr 0.975). Writes priority.json for the
    worker: fits cleanly -> ahead of everything; 1 conflict (may still enter via the 20% override or a swap) ->
    after keepers, before mining; >= 2 conflicts -> last. Returns the set of demoted (>= 2 conflicts) keys."""
    pend = [j for j in queue if j.get('mode') == 'os' and is_composite(j) and j.get('status') == 'pending' and j.get('meta')]
    if not pend: jsave(os.path.join(VAL, 'priority.json'), {}); return set()
    try:
        cj = jload(os.path.join(A, 'research', 'slow-correlation.json'), {}); byid = {str(a['id']): a for a in cj.get('alphas', [])}
        pool = (jload(os.path.join(A, 'research', 'optimal-pool.json'), {}) or {}).get('submission_order', [])
        def win(s): return s[(s.index >= W0) & (s.index <= W1)]
        def path_of(p): return p if os.path.isabs(p) and os.path.exists(p) else os.path.join(ROOT, re.sub(r'^.*?/trex-alpha/', '', p))
        P = pd.DataFrame({str(x['id']): win(read_pnl(path_of(byid[str(x['id'])]['source_pnl_csv']))) for x in pool if str(x['id']) in byid}).fillna(0.0)
        z = lambda v: (v - v.mean()) / (np.sqrt(((v - v.mean()) ** 2).sum()) or np.nan)
        Pz = P.apply(z).fillna(0.0).values
        over, demoted, counts = {}, set(), [0, 0, 0]
        for j in pend:
            m = j['meta']
            if not all(n in lib for n in m['components']): continue
            e = sum(w * win(lib[n]['pnl']).reindex(P.index).fillna(0.0) for w, n in zip(m['pos_w'], m['components']))
            k = int(((Pz.T @ z(e).fillna(0.0).values) >= 0.5).sum())
            base = float(j.get('priority') or 0)
            key = f"{j['exp']}/{j['name']}/os"
            if k == 0: over[key] = 1.0 + base; counts[0] += 1
            elif k == 1: over[key] = -0.5 + base; counts[1] += 1
            else: over[key] = -2.0 + base; counts[2] += 1; demoted.add(f"{j['exp']}/{j['name']}")
        jsave(os.path.join(VAL, 'priority.json'), over)
        log(f'pool fit of {len(pend)} pending composites: clean {counts[0]}, 1 conflict {counts[1]}, 2+ conflicts {counts[2]} (demoted)')
        return demoted
    except Exception as ex:
        log('pool fit failed (priorities unchanged):', repr(ex)[:300]); return set()

# ------------------------------------------------------------------ 4. repack
def repack(queue, state, lib, n_new, bar, corr_cap, max_secs, samples, dry):
    P = pd.DataFrame({k: v['pnl'] for k, v in lib.items()}).sort_index()
    W = (P.index >= W0) & (P.index <= W1)
    # members every new composite must stay <= corr_cap against: current pool + every live/finished composite
    members = {}
    for n in pool_names():
        if n in P.columns: members[n] = P[n].fillna(0.0).values[W]; continue
        g = glob.glob(os.path.join(RES, n, 'slow-*.pnl.csv')) or glob.glob(os.path.join(A, 'results', n, 'slow-*.pnl.csv'))
        if g: members[n] = read_pnl(g[0]).reindex(P.index).fillna(0.0).values[W]
    failed = {k for k, v in state['screened'].items() if v.startswith('fail')}
    for j in queue:
        if not j.get('meta') or j.get('exp') in {'A2', 'A5', 'B', 'C'} or str(j.get('status', '')).startswith(('error', 'cancel')): continue
        if f"{j['exp']}/{j['name']}" in failed: continue          # never reaches Slow, so it must not block new composites
        m = j['meta']
        if not all(n in P.columns for n in m['components']): continue
        members['C:' + '+'.join(m['components']) + str(m['pos_w'][:1])] = sum(w * P[n].fillna(0.0) for w, n in zip(m['pos_w'], m['components'])).values[W]
    comp = [k for k in lib if lib[k]['ir'] >= 0.03]
    Pz = P[comp].fillna(0.0); sd = Pz.std(); Q = Pz / sd; C = Q[W].corr()
    keep = []
    for k in sorted(comp, key=lambda k: -lib[k]['ir']):
        if all(C.loc[k, j] <= 0.9 for j in keep): keep.append(k)
    comp = keep
    rng = np.random.default_rng(int(time.time()))
    Qv = Q[comp].values; Cc = C.loc[comp, comp].values; rt = np.array([lib[c]['slow_secs'] for c in comp])
    cands = []
    for k in (2, 3, 4):
        for _ in range(samples):
            idx = rng.choice(len(comp), k, replace=False)
            if rt[idx].sum() > max_secs: continue
            if Cc[np.ix_(idx, idx)][np.triu_indices(k, 1)].max() > 0.5: continue
            w = rng.dirichlet(np.ones(k) * 2); x = Qv[:, idx] @ w; e = x.mean() / x.std()
            if e >= bar: cands.append((e, int(rt[idx].sum()), idx, w, x))
    cands.sort(key=lambda t: -(t[0] - bar) / np.sqrt(t[1]))
    mem = list(members.values()); out = []
    for e, secs, idx, w, x in cands:
        if len(out) >= n_new: break
        xw = x[W]; cs = [np.corrcoef(xw, y)[0, 1] for y in mem]
        if max(cs) <= corr_cap:
            mem.append(xw); names = [comp[i] for i in idx]
            out.append(dict(components=names, pos_w=[float(v / sd[n]) for v, n in zip(w, names)], est_ir=float(e), est_secs=secs,
                            est_max_corr=float(max(cs)), lookback=max(lib[n]['lookback'] for n in names)))
    log(f'repack: library {len(lib)} (distinct components {len(comp)}), members {len(members)}, admissible {len(cands)}, new composites {len(out)}')
    if dry or not out: return len(out)
    state['packs'] += 1; exp = f"K{state['packs']:03d}"; jobs = []
    for i, m in enumerate(out):
        try: code = render(lib, m['components'], m['pos_w'], f'{exp}-{i:03d}')
        except Exception as ex: log('render failed', m['components'], ex); continue
        jobs.append(dict(exp=exp, name=f'k{i:03d}', mode='os_fast', code=code, lookback=m['lookback'], meta=m))
    to_inbox(jobs, 'fast'); jsave(os.path.join(WORK, f'{exp}.packed.json'), out)
    return len(jobs)


# ------------------------------------------------------------------ 5. mine components
SEARCH = os.path.join(A, 'search')

def ingest_mined(queue, state, dry):
    """Finished mining jobs -> alphas/research/results/mine-<hash>/ + candidate record (library picks them up)."""
    n_new = 0
    for j in queue:
        if not j.get('mine') or j.get('mode') != 'os' or j.get('status') != 'done': continue
        key = f"{j['exp']}/{j['name']}"
        if key in state.setdefault('mined', {}): continue
        cid = 'mine-' + j['name']; src = os.path.join(VAL, j['exp'])
        sj, sp = os.path.join(src, f"{j['name']}.slow.json"), os.path.join(src, f"{j['name']}.slow.pnl.csv")
        if not (os.path.exists(sj) and os.path.exists(sp)): log('mine ingest: missing slow files for', key); continue
        sir = float(j.get('ir') or 0); state['mined'][key] = round(sir, 4); n_new += 1
        if dry: continue
        out = os.path.join(RES, cid); os.makedirs(out, exist_ok=True)
        shutil.copy(sj, os.path.join(out, f"slow-{j['id']}.json")); shutil.copy(sp, os.path.join(out, f"slow-{j['id']}.pnl.csv"))
        fp = os.path.join(SEARCH, 'pnl', f"{j['name']}.csv")
        if os.path.exists(fp): shutil.copy(fp, os.path.join(out, f"fast-{j['name']}.pnl.csv"))
        mi = j['mine']
        rec = {'candidate_id': cid, 'title': f"Mined search component {j['name']}", 'status': 'qualified' if sir > 0.07 else 'slow_rejected',
               'code': j['code'], 'inputs': {'primary_cluster': 'search', 'primary_variables': [], 'secondary_clusters': [], 'secondary_variables': []},
               'metadata': {'hypothesis': 'Search hit Slow-run as a composite component (chosen for a new PnL direction, not for IR).',
                            'mechanism_classification': 'mined component', 'mine': mi},
               'lineage': {'family_id': cid, 'root_candidate_id': cid, 'parent_candidate_id': None, 'generation': 0, 'stage': 'manual',
                           'changes': {'purpose': 'component mining'}},
               'required_lookback': j.get('lookback'), 'slow_lookback_buffered': j.get('lookback'),
               'runs': {'fast': {'status': 'not_eligible', 'result': None, 'error': None},
                        'slow': {'status': 'success', 'error': None, 'result': {
                            'id': str(j['id']), 'ir': sir, 'turnover': float(j.get('tvr') or 0), 'ir_tvr': float(j.get('ir_tvr') or 0),
                            'mode': 'os', 'lookback': j.get('lookback'),
                            'archive_json': f"alphas/research/results/{cid}/slow-{j['id']}.json",
                            'archive_pnl_csv': f"alphas/research/results/{cid}/slow-{j['id']}.pnl.csv"}}}}
        jsave(os.path.join(CAND, cid + '.json'), rec)
        log(f"mine ingest {key}: Slow IR {sir:.3f} (Fast {mi.get('fast_ir', 0):.3f}){' QUALIFIED' if sir > 0.07 else ''}")
    return n_new

def mine(queue, lib, n_new, cap, min_ir, dry):
    """Queue Slow runs for unrun search hits that are <= cap correlated (Fast PnL, 2020-21) with every library
    component, every live mining job and each other. Ordered by Fast IR. Low priority: composites go first."""
    evals = {}
    for line in open(os.path.join(SEARCH, 'evals.jsonl')):
        try: e = json.loads(line)
        except Exception: continue
        if e.get('ir') is not None and abs(e['ir']) >= min_ir and e.get('tree'): evals[e['hash']] = abs(e['ir'])
    taken = {n.split('-', 1)[1] for n in lib if n.startswith(('search-', 'mine-'))}
    taken |= {j['name'] for j in queue if j.get('mine')}
    sq = jload(os.path.join(A, 'research', 'slow-queue.json'), {}) or {}
    taken |= {str(x.get('candidate_id', '')).split('-', 1)[-1] for x in sq.get('entries', [])}
    cands = [h for h in evals if h not in taken and os.path.exists(os.path.join(SEARCH, 'pnl', f'{h}.csv'))]
    if not cands: log('mine: no unrun hits left'); return 0
    P = pd.DataFrame({k: v['pnl'] for k, v in lib.items()}).sort_index(); P = P[(P.index >= W0) & (P.index <= W1)].fillna(0.0)
    live = [os.path.join(SEARCH, 'pnl', f"{j['name']}.csv") for j in queue
            if j.get('mine') and j.get('status') in ('pending', 'submitted')]
    X = pd.DataFrame({h: read_pnl(os.path.join(SEARCH, 'pnl', f'{h}.csv')) for h in cands}).reindex(P.index).fillna(0.0)
    X = X.loc[:, (X.mean() / X.std().replace(0, np.nan)) >= min_ir * 0.8]       # stored PnL must point the right way
    def z(M):
        M = M - M.mean(); n = np.sqrt((M ** 2).sum())
        return M / (n.replace(0, np.nan) if hasattr(n, 'replace') else (n or np.nan))
    Xz = z(X).fillna(0.0); Pz = z(P).fillna(0.0)
    maxlib = (Xz.T.values @ Pz.values).__abs__().max(axis=1)
    fixed = [z(read_pnl(p).reindex(P.index).fillna(0.0)).fillna(0.0).values for p in live if os.path.exists(p)]
    order = [i for i in np.argsort([-evals[h] for h in X.columns]) if maxlib[i] <= cap]
    pick, vecs = [], list(fixed)
    for i in order:
        if len(pick) >= n_new * 2: break
        v = Xz.iloc[:, i].values
        if all(abs(v @ u) <= cap for u in vecs): pick.append(i); vecs.append(v)
    hashes = [X.columns[i] for i in pick]
    r = subprocess.run(['node', 'scripts/composites/mine-code.js'], cwd=ROOT, input=json.dumps(hashes), capture_output=True, text=True)
    if r.returncode != 0: log('mine: code render failed', r.stderr[-400:]); return 0
    rendered = {x['hash']: x for x in json.loads(r.stdout)}
    mx = dict(zip(X.columns, maxlib))
    jobs = []
    for h in hashes:
        if h not in rendered or len(jobs) >= n_new: continue
        x = rendered[h]
        jobs.append(dict(exp=None, name=h, mode='os', code=x['code'], lookback=x['lookback'], priority=-1.0,
                         mine={'fast_ir': evals[h], 'max_lib_corr': round(float(mx[h]), 3), 'sign': x['sign']}))
    log(f'mine: {len(cands)} unrun hits, {len(order)} <= {cap} to the library ({P.shape[1]} components), queued {len(jobs)}')
    if dry or not jobs: return len(jobs)
    state_n = len({j['exp'] for j in queue if j.get('mine')}) + 1
    for j in jobs: j['exp'] = f'M{state_n:03d}'
    to_inbox(jobs, 'mine')
    return len(jobs)

# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--no-repack', action='store_true'); ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--pack-n', type=int, default=40); ap.add_argument('--low-water', type=int, default=40)
    ap.add_argument('--bar', type=float, default=0.095); ap.add_argument('--corr', type=float, default=0.42)
    ap.add_argument('--max-secs', type=float, default=1500); ap.add_argument('--samples', type=int, default=25000)
    ap.add_argument('--no-keepers', action='store_true'); ap.add_argument('--no-mine', action='store_true'); ap.add_argument('--mine-n', type=int, default=32)
    ap.add_argument('--mine-low', type=int, default=12); ap.add_argument('--mine-cap', type=float, default=0.5)
    ap.add_argument('--mine-min-ir', type=float, default=0.03)
    a = ap.parse_args()
    os.makedirs(WORK, exist_ok=True)
    state = jload(STATE) or {'ingested': {}, 'screened': {}, 'packs': 0}
    queue = jload(QFILE, []) or []
    if state.get('screen_v', 1) < 2:
        redo = [k for k, v in state['screened'].items() if v.startswith('fail ratio')]
        for k in redo: del state['screened'][k]
        state['screen_v'] = 2; log(f'screen v2 (common-date comparison): re-screening {len(redo)} earlier failures')
    new = ingest(queue, state, a.dry_run)
    mined = ingest_mined(queue, state, a.dry_run)
    kept = 0 if a.no_keepers else ingest_keepers(queue, state, a.dry_run)
    if (new or mined or kept) and not a.dry_run:
        rebuild_pool(); refresh_frontier()
    if not a.no_keepers: queue_keepers(queue, a.dry_run)
    lib = build_library()
    screen(queue, state, lib, a.dry_run)
    demoted = set() if a.dry_run else pool_fit(jload(QFILE, queue), lib)
    # pipeline depth = composites still to be run (pending/submitted Slow + Fast awaiting screen/run) + inbox;
    # composites demoted by pool_fit do not count (they will not fill pool slots, so they must not block repacking)
    live_slow = sum(1 for j in queue if j.get('mode') == 'os' and is_composite(j) and j.get('status') in ('pending', 'submitted')
                    and f"{j['exp']}/{j['name']}" not in demoted)
    live_fast = sum(1 for j in queue if j.get('mode') == 'os_fast' and is_composite(j) and (j.get('status') in ('pending', 'submitted')
                    or f"{j['exp']}/{j['name']}" not in state['screened']))
    inbox_n = sum(len(jload(p, []) or []) for p in glob.glob(os.path.join(INBOX, '*.json')))
    depth = live_slow + live_fast + inbox_n
    log(f'pipeline: slow pending/running {live_slow}, fast unscreened {live_fast}, inbox {inbox_n}, pool {len(pool_names())}')
    if not a.no_repack and depth < a.low_water:
        repack(queue, state, lib, a.pack_n, a.bar, a.corr, a.max_secs, a.samples, a.dry_run)
    queue = jload(QFILE, queue)          # reload: the worker may have merged this cycle's keeper jobs already
    slow_live = sum(1 for j in queue if j.get('mode') == 'os' and j.get('status') in ('pending', 'submitted') and f"{j['exp']}/{j['name']}" not in demoted)
    inbox_slow = sum(1 for p in glob.glob(os.path.join(INBOX, '*.json')) for j in (jload(p, []) or []) if j.get('mode') == 'os')
    if not a.no_mine and slow_live + inbox_slow < a.mine_low:
        mine(queue, lib, a.mine_n, a.mine_cap, a.mine_min_ir, a.dry_run)
    if not a.dry_run: jsave(STATE, state)
    mdone = [j for j in queue if j.get('mine') and j.get('mode') == 'os' and j.get('status') == 'done']
    if mdone: log(f"mining: Slow runs done {len(mdone)}, Slow IR >= 0.03: {sum(float(j.get('ir') or 0) >= 0.03 for j in mdone)}, "
                  f"> 0.07: {sum(float(j.get('ir') or 0) > 0.07 for j in mdone)}")
    done = [j for j in queue if j.get('mode') == 'os' and is_composite(j) and j.get('status') == 'done']
    q = [j for j in done if float(j.get('ir') or 0) > 0.07]
    log(f'summary: composite Slow runs done {len(done)}, qualified {len(q)}')

if __name__ == '__main__':
    main()
