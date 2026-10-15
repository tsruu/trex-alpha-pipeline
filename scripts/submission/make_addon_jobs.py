#!/usr/bin/env python3
"""Add-on submission (alphas/submission/addon-order.json, positions 281..393).

  --inputs   write alphas/submission/doc-inputs-addon.json: code + part notes for every add-on that still needs a
             comment (the 52 composites without one and the 7 legacy 101 singles). Comments are written from it
             into alphas/submission/docs-addon.json (same light Thesis / Parts|Signal / Built format as docs.json).
  (default)  write alphas/validation/requests/2026-09-29-addon-jobs.json: one commented Slow job per not-ready
             add-on, exp ADD, in add-on order (priority decreasing with position so the worker runs them in order).
             Code = the exact code of the alpha's finished Slow run (composites: the queue job behind the cmp id;
             legacy 101: the Slow version in alphas/101-alpha-NN.md), with only comment lines added/removed.
Comments never change PnL (checked, exp CT1)."""
import json, os, re, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')); os.chdir(ROOT)
SUB = 'alphas/submission'
order = json.load(open(f'{SUB}/addon-order.json'))['order']
need = [x for x in order if not x['ready']]
q = json.load(open('alphas/validation/queue.json'))
ing = json.load(open('alphas/composites/state.json'))['ingested']
inv = {}
for k, v in ing.items(): inv.setdefault(v, []).append(k)
byk = {}
for j in q: byk.setdefault(f"{j['exp']}/{j['name']}", []).append(j)
docs = {}
for f in ('docs.json', 'docs-extras.json', 'docs-ndm.json'): docs.update(json.load(open(f'{SUB}/{f}')))
# comments already written for the 9 cancelled reserve runs (SUBR): reuse them verbatim
subr = {j['name']: j['code'] for j in q if j['exp'] == 'SUBR'}
def header(code):
    out = []
    for l in code.split('\n'):
        if l.startswith('#'): out.append(l)
        else: break
    return '\n'.join(out)
def clean(code):
    code = re.sub(r'^# Hypothesis:.*\n', '', code)
    code = re.sub(r'^# packed composite .*\n', '', code)
    return code.lstrip('\n')

def source(x):
    """(code, lookback, slow_run_id) of the alpha's finished Slow run."""
    n = x['name']
    if n.startswith('101-alpha-'):
        md = open(f'alphas/{n}.md').read()
        ver = re.search(r'^\| Slow OS \| (v\d+) \| [^|]+\| (\d+) \|', md, re.M)
        v, rid = ver.group(1), ver.group(2)
        code = re.search(rf'^### {v}\s*\n+```python\n(.*?)```', md, re.M | re.S).group(1)
        slow = md[md.index('### Slow OS'):]
        lb = int(re.search(r'^\| Lookback \| (\d+) \|', slow, re.M).group(1))
        return code.rstrip('\n') + '\n', lb, rid
    js = [j for k in inv.get(n, []) for j in byk.get(k, []) if j['mode'] == 'os' and j['status'] == 'done']
    assert len(js) == 1, (n, len(js))
    return js[0]['code'], int(js[0]['lookback']), str(js[0]['id'])

if '--inputs' in sys.argv:
    out = []
    for x in need:
        if x['name'] in subr: continue
        code, lb, rid = source(x)
        parts = []
        for m in re.finditer(r'^def (_c\d+)\(.*?\):\n    # (\S+)\n', code, re.M):
            parts.append(dict(slot=m.group(1), source=m.group(2), existing_comment=docs.get(m.group(2))))
        out.append(dict(name=x['name'], kind=x['kind'], slow_ir=x['slow_ir'], tvr=x['tvr'], slow_run=rid,
                        parts=parts, code=clean(code)))
    json.dump(out, open(f'{SUB}/doc-inputs-addon.json', 'w'), indent=1)
    print(f'{SUB}/doc-inputs-addon.json', len(out), 'alphas need a comment;', sum(x['name'] in subr for x in need), 'reuse SUBR comments')
    sys.exit()

D = json.load(open(f'{SUB}/docs-addon.json')) if os.path.exists(f'{SUB}/docs-addon.json') else {}
jobs, missing = [], []
for x in need:
    n = x['name']; code, lb, rid = source(x)
    doc = header(subr[n]) if n in subr else D.get(n)
    if not doc: missing.append(n); continue
    assert all(l.startswith('#') for l in doc.split('\n')), n
    full = doc.rstrip('\n') + '\n' + clean(code)
    compile(full, n, 'exec')
    jobs.append(dict(exp='ADD', name=n, mode='os', code=full, lookback=lb, priority=round(5 + (400 - x['pos']) / 100, 2), notify=True))
if missing: sys.exit(f'no comment yet for {len(missing)}: {missing[:5]}')
out = 'alphas/validation/requests/2026-09-29-addon-jobs.json'
json.dump(jobs, open(out, 'w'))
print(out, len(jobs), 'jobs, exp ADD, positions', need[0]['pos'], '..', need[-1]['pos'])
