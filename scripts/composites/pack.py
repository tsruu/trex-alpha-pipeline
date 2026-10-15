import os as _os
_REPO=_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
_WORK=_os.path.join(_REPO,'alphas','composites')
import json,os,numpy as np,pandas as pd,pickle,sys
lib=pickle.load(open(_os.path.join(_WORK,'library.pkl'),'rb'))
os.chdir((_REPO+'/alphas'))
pool=[(r.get('alpha') or r.get('name')) for r in json.load(open('research/optimal-pool.json'))['submission_order']]
P=pd.DataFrame({k:v['pnl'] for k,v in lib.items()}).sort_index()
W=(P.index>='2020-01-08')&(P.index<='2021-12-30')
def ir(x): return x.mean()/x.std()
IR={k:lib[k]['ir'] for k in lib}
comp=[k for k in lib if IR[k]>=0.03]
Pz=P[comp].fillna(0.0); sd=Pz.std(); Q=Pz/sd
C=Q[W].corr()
# dedupe near-identical components (window corr>0.9): keep higher IR
comp_sorted=sorted(comp,key=lambda k:-IR[k]); keep=[]
for k in comp_sorted:
    if all(C.loc[k,j]<=0.9 for j in keep): keep.append(k)
comp=keep; print('components after dedupe',len(comp))
BAR=float(sys.argv[1]) if len(sys.argv)>1 else 0.085; CORR=float(sys.argv[2]) if len(sys.argv)>2 else 0.45
rng=np.random.default_rng(7); cands=[]
Qv=Q[comp].values; Cc=C.loc[comp,comp].values
for k in (2,3,4):
    for _ in range(20000):
        idx=rng.choice(len(comp),k,replace=False)
        if Cc[np.ix_(idx,idx)][np.triu_indices(k,1)].max()>0.5: continue
        w=rng.dirichlet(np.ones(k)*2)
        x=Qv[:,idx]@w
        e=x.mean()/x.std()
        if e>=BAR: cands.append((e,[comp[i] for i in idx],w,x))
cands.sort(key=lambda t:-t[0]); print('candidates',len(cands))
chosen={p:P[p].fillna(0.0).values[W] for p in pool}
out=[]
for e,names,w,x in cands:
    xw=x[W]
    cs=[np.corrcoef(xw,y)[0,1] for y in chosen.values()]
    if max(cs)<=CORR:
        key='+'.join(names); chosen[key]=xw
        mp=max(np.corrcoef(xw,P[p].fillna(0.0).values[W])[0,1] for p in pool)
        out.append(dict(components=names,risk_w=[float(v) for v in w],pos_w=[float(v/sd[n]) for v,n in zip(w,names)],est_ir=float(e),
                        est_max_pool_corr=float(mp),est_max_corr_all=float(max(cs)),lookback=max(lib[n]['lookback'] for n in names),
                        comp_ir=[IR[n] for n in names]))
print('packed',len(out))
json.dump(out,open(_os.path.join(_WORK,'packed.json'),'w'),indent=1)
from collections import Counter
print('size dist',Counter(len(o['components']) for o in out))
print('component reuse top',Counter(n for o in out for n in o['components']).most_common(8))
