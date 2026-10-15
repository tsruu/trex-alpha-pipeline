import os as _os
_REPO=_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
_WORK=_os.path.join(_REPO,'alphas','composites')
import json,os,pickle,numpy as np,pandas as pd
lib=pickle.load(open(_os.path.join(_WORK,'library.pkl'),'rb'))
V=_os.path.join(_REPO,'alphas/validation/B')
def rd(f):
    s=pd.read_csv(f).set_index('date')['dailypnl']; s.index=pd.to_datetime(s.index); return s
masks={}
for g in ['vixhi','vixlo','par0','par1','m4_0','m4_1','m4_2','m4_3']:
    s=rd(f'{V}/pk007-{g}.fast.pnl.csv'); masks[g]=s.abs()>0
def ir(x): return x.mean()/x.std()
P=pd.DataFrame({k:v['pnl'] for k,v in lib.items()}).sort_index()
rows=[]
for k in P.columns:
    s=P[k].dropna(); 
    if lib[k]['ir']<0.08: continue
    r=dict(name=k,ir=lib[k]['ir'])
    for g,m in masks.items():
        mm=m.reindex(s.index).fillna(False)
        r[g]=round(ir(s.where(mm,0.0)),3)
    rows.append(r)
df=pd.DataFrame(rows).sort_values('ir',ascending=False)
print(df.to_string(index=False))
print('alphas with both VIX pieces >0.07:',((df.vixhi>0.07)&(df.vixlo>0.07)).sum(),' both parity halves >0.07:',((df.par0>0.07)&(df.par1>0.07)).sum(), ' of',len(df))
