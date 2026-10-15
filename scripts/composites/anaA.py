import os as _os
_REPO=_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
_WORK=_os.path.join(_REPO,'alphas','composites')
import json,os,sys,pickle,numpy as np,pandas as pd,glob
sys.path.insert(0,_os.path.dirname(_os.path.abspath(__file__)))
lib=pickle.load(open(_os.path.join(_WORK,'library.pkl'),'rb'))
from tq import load
V=_os.path.join(_REPO,'alphas/validation')
exp=sys.argv[1]; tag=sys.argv[2] if len(sys.argv)>2 else 'fast'
def rd(f):
    s=pd.read_csv(f).set_index('date')['dailypnl']; s.index=pd.to_datetime(s.index); return s
def fastpnl(n):
    f=lib[n]['fast_pnl_file']
    return rd(f) if f else None
def ir(x): x=x.dropna(); return x.mean()/x.std()
Wlo,Whi='2020-01-08','2021-12-30'
pool=[(r.get('alpha') or r.get('name')) for r in json.load(open(_os.path.join(_REPO,'alphas/research/optimal-pool.json')))['submission_order']]
rows=[]
for j in load():
    if j['exp']!=exp or not j['status']=='done': continue
    if (tag=='fast')!=(j['mode']=='os_fast'): continue
    act=rd(f"{V}/{exp}/{j['name']}.{tag}.pnl.csv")
    if j['name'].startswith('ctl'):
        if 'meta' not in j: continue
        n=j['name'].split('-',1)[1]; ref=fastpnl(n) if tag=='fast' else lib[n]['pnl']
        df=pd.concat([act,ref],axis=1).dropna()
        print(f"{j['name']}: actual IR {ir(act):.3f} component {tag} IR {ir(ref):.3f}  corr {df.corr().iloc[0,1]:.4f}  lib slow IR {lib[n]['ir']}")
        continue
    m=j['meta']; names=m['components']; w=m['pos_w']
    refs=[fastpnl(n) if tag=='fast' else lib[n]['pnl'] for n in names]
    if any(r is None for r in refs): print(j['name'],'missing component pnl'); continue
    est=sum(wi*r.reindex(act.index).fillna(0) for wi,r in zip(w,refs))
    c=np.corrcoef(est,act)[0,1]
    win=(act.index>=Wlo)&(act.index<=Whi)
    # correlation with pool (slow pnl) in window
    pc_act=max(np.corrcoef(act[win],lib[p]['pnl'].reindex(act.index[win]).fillna(0))[0,1] for p in pool)
    pc_est=max(np.corrcoef(est[win],lib[p]['pnl'].reindex(act.index[win]).fillna(0))[0,1] for p in pool)
    rows.append(dict(name=j['name'],k=len(names),est_ir=round(ir(est),3),act_ir=round(ir(act),3),ratio=round(ir(act)/ir(est),3),corr_est_act=round(c,3),
        pool_corr_est=round(pc_est,3),pool_corr_act=round(pc_act,3),slow_est=round(m['est_ir'],3),tvr=j.get('tvr'),secs=j.get('secs')))
df=pd.DataFrame(rows); print(df.to_string()); 
if len(df): print('median ratio',df.ratio.median(),' median corr',df.corr_est_act.median())
