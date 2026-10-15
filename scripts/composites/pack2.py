import os as _os
_REPO=_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
_WORK=_os.path.join(_REPO,'alphas','composites')
import json,os,numpy as np,pandas as pd,pickle,sys,argparse
ap=argparse.ArgumentParser(); ap.add_argument('--bar',type=float,default=0.095); ap.add_argument('--corr',type=float,default=0.42)
ap.add_argument('--maxsecs',type=float,default=1200); ap.add_argument('--samples',type=int,default=30000); ap.add_argument('--out',default='packed2.json')
ap.add_argument('--exclude',default='')
a=ap.parse_args()
lib=pickle.load(open(_os.path.join(_WORK,'library.pkl'),'rb'))
pool=[(r.get('alpha') or r.get('name')) for r in json.load(open(_os.path.join(_REPO,'alphas/research/optimal-pool.json')))['submission_order']]
P=pd.DataFrame({k:v['pnl'] for k,v in lib.items()}).sort_index()
W=(P.index>='2020-01-08')&(P.index<='2021-12-30')
IR={k:lib[k]['ir'] for k in lib}; RT={k:(lib[k].get('slow_secs') or 600) for k in lib}
excl=set(a.exclude.split(',')) if a.exclude else set()
comp=[k for k in lib if IR[k]>=0.03 and k not in excl]
Pz=P[comp].fillna(0.0); sd=Pz.std(); Q=Pz/sd; C=Q[W].corr()
keep=[]
for k in sorted(comp,key=lambda k:-IR[k]):
    if all(C.loc[k,j]<=0.9 for j in keep): keep.append(k)
comp=keep
rng=np.random.default_rng(11); cands=[]
Qv=Q[comp].values; Cc=C.loc[comp,comp].values; rt=np.array([RT[c] for c in comp])
for k in (2,3,4):
    for _ in range(a.samples):
        idx=rng.choice(len(comp),k,replace=False)
        if rt[idx].sum()>a.maxsecs: continue
        if Cc[np.ix_(idx,idx)][np.triu_indices(k,1)].max()>0.5: continue
        w=rng.dirichlet(np.ones(k)*2); x=Qv[:,idx]@w; e=x.mean()/x.std()
        if e>=a.bar: cands.append((e,rt[idx].sum(),[comp[i] for i in idx],w,x))
# prefer high IR per runtime among admissible
cands.sort(key=lambda t:-(t[0]-a.bar)/np.sqrt(t[1]))
chosen={p:P[p].fillna(0.0).values[W] for p in pool}; out=[]
for e,secs,names,w,x in cands:
    xw=x[W]; cs=[np.corrcoef(xw,y)[0,1] for y in chosen.values()]
    if max(cs)<=a.corr:
        chosen['+'.join(names)]=xw
        out.append(dict(components=names,pos_w=[float(v/sd[n]) for v,n in zip(w,names)],risk_w=[float(v) for v in w],est_ir=float(e),est_secs=int(secs),
            est_max_corr=float(max(cs)),lookback=max(lib[n]['lookback'] for n in names)))
json.dump(out,open(_os.path.join(_WORK,a.out),'w'),indent=1)
secs=np.array([o['est_secs'] for o in out])
print(f'components {len(comp)}  admissible combos {len(cands)}  packed {len(out)}  total est Slow hours {secs.sum()/3600:.1f}  median secs {np.median(secs) if len(secs) else 0:.0f}')
