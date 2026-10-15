import os as _os
_REPO=_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
_WORK=_os.path.join(_REPO,'alphas','composites')
import json,os,numpy as np,pandas as pd
os.chdir(_os.path.join(_REPO,'alphas/search'))
ev={}
for l in open('evals.jsonl'):
    e=json.loads(l)
    if e.get('ir') is not None: ev[e['hash']]=e
hs=[h for h,e in ev.items() if abs(e['ir'])>=0.065 and os.path.exists(f'pnl/{h}.csv')]
X=np.column_stack([pd.read_csv(f'pnl/{h}.csv')['dailypnl'].values*np.sign(ev[h]['ir']) for h in hs])
Z=(X-X.mean(0))/X.std(0)
U,S,Vt=np.linalg.svd(Z-Z.mean(0),full_matrices=False)
share=S**2/(S**2).sum(); print('PC share',np.round(share[:8],3))
ir_win=X.mean(0)/X.std(0)
print('median window IR of hits (2020-21):',round(np.median(ir_win),3))
for k in (1,3,5,10):
    Xs=X/X.std(0); F=Xs@Vt[:k].T   # factor return series WITH their means
    D=np.column_stack([np.ones(len(F)),F]); B=np.linalg.lstsq(D,X,rcond=None)[0]
    R=X-F@B[1:]   # residual keeps intercept
    rir=R.mean(0)/R.std(0)
    print(f'k={k}: median residual IR {np.median(rir):.3f}, share resid IR>=0.5*orig {np.mean(rir>=0.5*ir_win):.2f}, resid IR>0.07 count {np.sum(rir>0.07)}')
# how do the pool's PnL load on top PCs? which PC carries the mean return?
Xs=X/X.std(0); FF=Xs@Vt[:5].T; pcs_ir=[FF[:,i].mean()/FF[:,i].std() for i in range(5)]
print('IR of PC series (sign arbitrary):',np.round(np.abs(pcs_ir),3))
