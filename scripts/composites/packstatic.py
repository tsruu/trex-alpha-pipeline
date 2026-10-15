import os as _os
_REPO=_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
_WORK=_os.path.join(_REPO,'alphas','composites')
import json,os,glob,re,numpy as np,pandas as pd,pickle,sys
A=(_REPO+'/alphas/')
lib=pickle.load(open(_os.path.join(_WORK,'library.pkl'),'rb'))
pool=[(r.get('alpha') or r.get('name')) for r in json.load(open(A+'research/optimal-pool.json'))['submission_order']]
S={};code={};irs={}
for f in glob.glob(A+'research/results/fund-probe-*/fast-*.json'):
    d=json.load(open(f)); e=d['expression']
    if re.search(r'ts_',e.split('alpha =')[-1]): continue
    try: ir=float(d['stats_data']['metrics']['ir'])
    except: continue
    if abs(ir)<0.012: continue
    s=pd.read_csv(f.replace('.json','.pnl.csv')).set_index('date')['dailypnl']; s.index=pd.to_datetime(s.index)
    n=f.split('/')[-2]; S[n]=s*np.sign(ir); code[n]=e; irs[n]=abs(ir)
P=pd.DataFrame(S).sort_index().fillna(0); W=(P.index>='2020-01-08')&(P.index<='2021-12-30')
print('static fund components',P.shape[1],'median pairwise window corr',round(np.median(P[W].corr().values[np.triu_indices(P.shape[1],1)]),3),
      'full-period median corr',round(np.median(P.corr().values[np.triu_indices(P.shape[1],1)]),3))
sd=P.std(); Q=P/sd; names=list(P.columns); Qv=Q.values
C=Q[W].corr().values
# pool pnl
PP={p:lib[p]['pnl'].reindex(P.index).fillna(0).values[W] for p in pool}
rng=np.random.default_rng(3); out=[]; chosen=dict(PP)
best=[]
for k in (4,5,6,7,8):
    for _ in range(40000):
        idx=rng.choice(len(names),k,replace=False)
        if C[np.ix_(idx,idx)][np.triu_indices(k,1)].max()>0.5: continue
        w=rng.dirichlet(np.ones(k)*3); x=Qv[:,idx]@w; e=x.mean()/x.std()
        if e>=0.085: best.append((e,idx,w,x))
best.sort(key=lambda t:-t[0]); print('static combos >=0.085:',len(best), 'max est', round(best[0][0],3) if best else None)
for e,idx,w,x in best:
    xw=x[W]; cs=[np.corrcoef(xw,y)[0,1] for y in chosen.values()]
    if max(cs)<=0.42:
        nm=[names[i] for i in idx]; chosen['+'.join(nm)]=xw
        out.append(dict(components=nm,codes=[code[n] for n in nm],pos_w=[float(v/sd[n]) for v,n in zip(w,nm)],est_ir=float(e),est_max_corr=float(max(cs))))
print('static composites packed',len(out))
for o in out[:10]: print(round(o['est_ir'],3),round(o['est_max_corr'],2),[n[11:] for n in o['components']])
json.dump(out,open(_os.path.join(_WORK,'packed_static.json'),'w'),indent=1)
mu=Q.mean().values; Sg=np.cov(Qv.T)
wopt=np.linalg.solve(Sg,mu); x=Qv@wopt
print('max-Sharpe IR of all static comps (in-sample, unconstrained):',round(x.mean()/x.std(),3), ' long-only weights:', end=' ')
from scipy.optimize import minimize
f=lambda w: -(Qv@np.abs(w)).mean()/(Qv@np.abs(w)).std()
r=minimize(f,np.ones(len(mu))/len(mu),method='L-BFGS-B'); print(round(-r.fun,3))
