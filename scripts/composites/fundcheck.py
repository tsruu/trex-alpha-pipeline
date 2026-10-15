import os as _os
_REPO=_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
_WORK=_os.path.join(_REPO,'alphas','composites')
import json,os,numpy as np,pandas as pd,re
os.chdir(_os.path.join(_REPO,'alphas/search'))
ev={}
for l in open('evals.jsonl'):
    e=json.loads(l)
    if e.get('ir') is not None: ev[e['hash']]=e
def leaves(n,o):
    if n['t']=='leaf': o.append(n)
    for k in ('a','b'):
        if k in n: leaves(n[k],o)
    return o
prims=json.load(open('primitives.json')) if os.path.exists('primitives.json') else None
single=[h for h,e in ev.items() if e['size']==1 and abs(e['ir'])>=0.05 and all(f.startswith('fund_') for f in e['families']) and os.path.exists(f'pnl/{h}.csv')]
print('single-leaf fundamental hits |IR|>=0.05:',len(single))
from collections import Counter
tfc=Counter(leaves(ev[h]['tree'],[])[0]['tf'] for h in single); print('transforms',tfc)
S=pd.DataFrame({h:pd.read_csv(f'pnl/{h}.csv')['dailypnl']*np.sign(ev[h]['ir']) for h in single})
C=S.corr().values; iu=np.triu_indices(len(single),1)
print('pairwise corr among single-leaf fund hits: median',round(np.median(C[iu]),3),' share>0.5',round((C[iu]>0.5).mean(),3))
for tf in tfc:
    idx=[i for i,h in enumerate(single) if leaves(ev[h]['tree'],[])[0]['tf']==tf]
    if len(idx)>2:
        sub=C[np.ix_(idx,idx)]; j=np.triu_indices(len(idx),1)
        print(f'  tf={tf}: n={len(idx)} median corr {np.median(sub[j]):.3f} share>0.5 {(sub[j]>0.5).mean():.2f}')
# greedy independent count among them
order=sorted(range(len(single)),key=lambda i:-abs(ev[single[i]]['ir'])); ch=[]
for i in order:
    if all(C[i,j]<=0.5 for j in ch): ch.append(i)
print('greedy <=0.5 regions among single fund hits:',len(ch))
for i in ch[:25]:
    e=ev[single[i]]; l=leaves(e['tree'],[])[0]; print(' ',round(e['ir'],3),round(e['tvr'],3),l['p'],l['tf'])
