import os as _os
_REPO=_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
_WORK=_os.path.join(_REPO,'alphas','composites')
import json,glob,os,numpy as np,pandas as pd
os.chdir((_REPO+'/alphas'))
p=json.load(open('research/optimal-pool.json'))
pool={}
for r in p['submission_order']:
    name=r.get('alpha') or r.get('name') or r.get('id'); rid=str(r.get('trexsim_id') or r.get('id'))
    src='results' if name.startswith('101-') else 'research/results'
    f=glob.glob(f'{src}/{name}/slow-{rid}.pnl.csv') or glob.glob(f'{src}/{name}/slow-*.pnl.csv')
    s=pd.read_csv(f[0]).set_index('date')['dailypnl']; pool[name]=s
P=pd.DataFrame(pool)
ev={}
for l in open('search/evals.jsonl'):
    d=json.loads(l)
    if d.get('ir') is None: continue
    ev[d['hash']]=d
hits=[h for h,d in ev.items() if abs(d['ir'])>=0.065 and os.path.exists(f'search/pnl/{h}.csv')]
S={}
for h in hits:
    s=pd.read_csv(f'search/pnl/{h}.csv').set_index('date')['dailypnl']
    S[h]=s*np.sign(ev[h]['ir'])  # orient positive
H=pd.DataFrame(S).reindex(P.index)
print('pool',P.shape,'hits',H.shape)
irs=pd.Series({h:abs(ev[h]['ir']) for h in H.columns})
tv=pd.Series({h:ev[h].get('tvr',1) for h in H.columns})
# correlation of hits to pool
C=pd.concat([H,P],axis=1).corr()
hp=C.loc[H.columns,P.columns].max(axis=1)
print('hits with max corr to pool <=0.5:', (hp<=0.5).sum())
def greedy(cols, thr=0.5, order=None):
    chosen=[]
    for c in (order if order is not None else cols):
        if all(C.loc[c,x]<=thr for x in chosen): chosen.append(c)
    return chosen
free=[h for h in H.columns if hp[h]<=0.5]
for bar in (0.065,0.075,0.085):
    cand=[h for h in free if irs[h]>=bar]
    ch=greedy(cand, order=sorted(cand,key=lambda h:-irs[h]))
    print(f'Fast|IR|>={bar}: free-of-pool {len(cand)}, greedy independent set (<=0.5, no override) {len(ch)}')
# PCA of all hits + pool
X=pd.concat([H,P],axis=1).dropna(axis=0,how='any')
Z=(X-X.mean())/X.std()
ev_=np.linalg.eigvalsh(np.corrcoef(Z.T.values))[::-1]
print('n series',Z.shape[1],'top eigen share',np.round(ev_[:10]/ev_.sum(),3), 'cum5',round(ev_[:5].sum()/ev_.sum(),3))
# families of greedy set
cand=[h for h in free if irs[h]>=0.075]
ch=greedy(cand, order=sorted(cand,key=lambda h:-irs[h]))
from collections import Counter
print(Counter(tuple(ev[h]['families']) if len(ev[h]['families'])==1 else 'multi' for h in ch).most_common(15))
for h in ch[:40]: print(h, round(irs[h],3), round(tv[h],2), round(hp[h],2), ev[h]['families'], ev[h]['code'].split('alpha = ')[1][:140])
