#!/usr/bin/env python3
"""Turn alphas/submission/{set,reserve}.json + docs.json into commented Slow jobs (one final run per alpha).
Only comments are added/removed, so results are identical to an uncommented run (checked on 3 alphas, exp CT1).
Order: new composites (SUBN, unverified) first, then verified set members (SUBV), then reserves (SUBR)."""
import json, re, os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')); os.chdir(ROOT)
S = json.load(open('alphas/submission/set.json')); R = json.load(open('alphas/submission/reserve.json')); D = json.load(open('alphas/submission/docs.json'))
q = json.load(open('alphas/validation/queue.json')); st = json.load(open('alphas/composites/state.json'))['ingested']
orig_lb = {}
for j in q:
    if j.get('mode') == 'os' and j.get('status') == 'done':
        orig_lb[st.get(f"{j['exp']}/{j['name']}") or j['name']] = j['lookback']
def clean(code):
    code = re.sub(r'^# Hypothesis:.*\n', '', code)                  # replaced by the new documentation header
    code = re.sub(r'^# packed composite .*\n', '', code)
    return code.lstrip('\n')
jobs, problems = [], []
for grp, L, exp, pr in (('set', S, None, None), ('reserve', R, 'SUBR', 1.0)):
    for c in L:
        e = exp or ('SUBN' if c['new'] else 'SUBV'); p = pr or (3.0 if c['new'] else 2.0)
        lb = orig_lb.get(c['name'], c['lookback'])
        if not c['new'] and c['name'] in orig_lb and orig_lb[c['name']] != c['lookback']: problems.append((c['name'], c['lookback'], orig_lb[c['name']]))
        code = D[c['name']] + '\n' + clean(c['code'])
        compile(code, c['name'], 'exec')
        jobs.append(dict(exp=e, name=c['name'], mode='os', code=code, lookback=int(lb), priority=p, notify=True))
out = 'alphas/validation/requests/2026-09-26-submission-jobs.json'
json.dump(jobs, open(out, 'w'))
from collections import Counter
print(out, len(jobs), dict(Counter(j['exp'] for j in jobs)), '| lookback mismatches used original:', len(problems), problems[:3])
