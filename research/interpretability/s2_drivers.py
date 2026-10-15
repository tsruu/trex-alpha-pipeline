"""Step 2b: which eigen-directions of the ingredient PnL matrix are real (above the Marchenko-Pastur noise edge),
are they stable across halves, and what are they made of (motifs of top-loading ingredients)."""
import json, re, numpy as np, pandas as pd
from collections import Counter
A='research/hypothesis-audit'; OUT='research/interpretability'
ing=pd.read_csv(f'{A}/ingredient-catalog.csv'); wt=pd.read_csv(f'{OUT}/ingredient-weights.csv').set_index('name').pool_weight
def rd(p):
    try: d=pd.read_csv(re.sub(r'^.*?/trex-alpha/','',p))
    except Exception: return None
    return pd.Series(pd.to_numeric(d['dailypnl'],errors='coerce').values,index=pd.to_datetime(d['date']))
pnl={r.name:rd(r.pnl_path) for r in ing.itertuples() if isinstance(r.pnl_path,str) and wt.get(r.name,0)>0}
pnl={k:v for k,v in pnl.items() if v is not None}
mot={r.name:(json.loads(r.features).get('motifs',[]) if isinstance(r.features,str) else []) for r in ing.itertuples()}
D=pd.concat(pnl,axis=1).loc['2006':'2021']; names=list(D.columns)
Z=D/D.std()          # scale only; keep means so driver returns are meaningful
def eig(Zp):
    C=Zp.corr(min_periods=500).fillna(0).values; np.fill_diagonal(C,1)
    ev,V=np.linalg.eigh(C); o=np.argsort(ev)[::-1]; return ev[o],V[:,o],C
ev,V,C=eig(Z); N=len(names); T=int(D.notna().sum(1).gt(N*0.5).sum())
edge=(1+np.sqrt(N/T))**2
K=int((ev>edge).sum())
print(f'N={N} T(dense days)={T}  MP noise edge={edge:.2f}  eigenvalues above edge: {K}  (share of total var {ev[:K].sum()/ev.sum():.1%})')
# stability: principal angles between top-K subspaces of two halves
e1,V1,_=eig(Z.loc[:'2013']); e2,V2,_=eig(Z.loc['2014':])
k=min(K,10); s=np.linalg.svd(V1[:,:k].T@V2[:,:k],compute_uv=False)
print(f'subspace overlap 2006-13 vs 2014-21 (top {k}): cosines {np.round(s,2).tolist()}')
F=Z.fillna(0).values@V[:,:K]        # factor return series (approx)
comb=Z.mean(1).values               # combined alpha proxy (equal-risk across ingredients actually used)
w=np.array([wt[n] for n in names]); combw=(Z.fillna(0).values*w).sum(1)
Fz=np.column_stack([F[:,j]*np.sign(V[np.argmax(abs(V[:,j])),j]) for j in range(K)])
beta=np.linalg.lstsq(Fz,combw,rcond=None)[0]; fit=Fz@beta
ret_share=beta*Fz.mean(0)/combw.mean(); resid=combw-fit
print(f'pool IR {combw.mean()/combw.std():.3f}; fitted-by-drivers IR {fit.mean()/fit.std():.3f}; residual IR {resid.mean()/resid.std():.3f}; residual share of pool mean {resid.mean()/combw.mean():.1%}')
rows=[]
for j in range(min(K,12)):
    load=V[:,j]; sgn=np.sign(load[np.argmax(abs(load))]); load=load*sgn
    top=np.argsort(-load)[:12]
    m=Counter(x for i in top for x in mot[names[i]]).most_common(3)
    ir=F[:,j].mean()/F[:,j].std()*sgn
    rows.append(dict(pc=j+1,eig=round(ev[j],2),var_share=round(ev[j]/ev.sum(),3),
        corr_with_pool=round(np.corrcoef(F[:,j]*sgn,combw)[0,1],2),factor_daily_ir=round(ir,3),pool_risk_share=round(np.corrcoef(F[:,j]*sgn,combw)[0,1]**2,3),pool_return_share=round(ret_share[j],3),
        top_motifs='; '.join(f'{a}({b})' for a,b in m), top_ingredients=', '.join(names[i] for i in top[:4])))
R=pd.DataFrame(rows); print(R.drop(columns='top_ingredients').to_string(index=False))
R.to_csv(f'{OUT}/drivers-pca.csv',index=False)
pd.DataFrame(V[:,:K],index=names).to_csv(f'{OUT}/drivers-loadings.csv')
print('pool PnL variance explained by the',K,'real drivers: %.1f%%'%(100*np.corrcoef(combw, F@np.linalg.lstsq(F,combw,rcond=None)[0])[0,1]**2))
