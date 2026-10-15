import os as _os
_REPO=_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
_WORK=_os.path.join(_REPO,'alphas','composites')
import json,os,glob,numpy as np,pandas as pd,pickle
os.chdir((_REPO+'/alphas'))
lib={}
for f in sorted(glob.glob('research/results/*/slow-*.json')+glob.glob('results/101-alpha-*/slow-*.json')+glob.glob('research-archive/**/slow-*.json',recursive=True)):
    name=f.split('/')[-2]
    if name in lib or name.startswith('smoke'): continue
    try: d=json.load(open(f))
    except: continue
    pf=f.replace('.json','.pnl.csv')
    if not os.path.exists(pf): continue
    s=pd.read_csv(pf).set_index('date')['dailypnl']; s.index=pd.to_datetime(s.index)
    if len(s)<1500: continue
    m=d['stats_data']['metrics']
    fast=None
    fj=glob.glob(os.path.dirname(f)+'/fast-*.pnl.csv')
    lib[name]=dict(code=d['expression'],lookback=int(d.get('lookback') or 300),ir=float(m['ir']),tvr=float(m['tvr']),slow_id=d['alpha_id'],pnl=s,fast_pnl_file=fj[0] if fj else None,src=f)
print(len(lib))
IR=pd.Series({k:v['ir'] for k,v in lib.items()})
print((IR>=0.03).sum(), (IR>0.07).sum())
pickle.dump(lib,open(_os.path.join(_WORK,'library.pkl'),'wb'))
