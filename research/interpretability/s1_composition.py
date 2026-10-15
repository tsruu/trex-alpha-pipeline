"""Step 1-2: what the combined alpha is made of (risk budget by data family) and how many independent bets it holds.
Inputs reused from research/hypothesis-audit (ingredient tags, blend risk shares). Run from repo root."""
import json, sys, numpy as np, pandas as pd
from collections import defaultdict
A='research/hypothesis-audit'; OUT='research/interpretability'
ing=pd.read_csv(f'{A}/ingredient-catalog.csv'); att=pd.read_csv(f'{A}/blend-attribution.csv')
sub=list(json.load(open('alphas/submission/submitted.json')))
import re
BAD=[]
def rd(p):
    p=re.sub(r'^.*?/trex-alpha/','',p)
    try: d=pd.read_csv(p)
    except Exception as e: BAD.append(p); return None
    return pd.Series(pd.to_numeric(d['dailypnl'],errors='coerce').values,index=pd.to_datetime(d['date']))
pnl={r.name:rd(r.pnl_path) for r in ing.itertuples() if isinstance(r.pnl_path,str)}; pnl={k:v for k,v in pnl.items() if v is not None}; print('unreadable PnL files:',len(BAD))
# ingredient weight in combined alpha = sum over submitted alphas of (1/N) * ingredient risk share in that alpha
w=defaultdict(float); N=len(sub); blends=set(att.alpha)
for a in sub:
    if a in blends:
        s=att[att.alpha==a]; sh=s.risk_share_common.clip(lower=0); sh=sh/sh.sum()
        for g,x in zip(s.ingredient,sh): w[g]+=x/N
    else: w[a]+=1/N
ing['pool_weight']=ing.name.map(w).fillna(0)
print('ingredients',len(ing),'with PnL',len(pnl),'weight covered %.3f'%ing.pool_weight.sum())
feat=ing.features.apply(lambda s: json.loads(s) if isinstance(s,str) else {})
def agg(key):
    acc=defaultdict(float)
    for f,wt in zip(feat,ing.pool_weight):
        vals=sorted(set(key(f))) or ['(untagged)']
        for v in vals: acc[v]+=wt/len(vals)
    return pd.Series(acc).sort_values(ascending=False)
fam=agg(lambda f:[l.get('family','?') for l in f.get('leaves',[])])
mot=agg(lambda f:f.get('motifs',[]))
print('\nRISK BUDGET BY LEAF DATA FAMILY'); print(fam.round(3).to_string())
print('\nRISK BUDGET BY MOTIF'); print(mot.round(3).to_string())
ing[['name','pool_weight','structural_archetype','pnl_cluster']].sort_values('pool_weight',ascending=False).to_csv(f'{OUT}/ingredient-weights.csv',index=False)
# effective number of bets
def spectrum(names,label):
    D=pd.concat({n:pnl[n] for n in names if n in pnl},axis=1)
    C=D.corr(min_periods=500).fillna(0).values; np.fill_diagonal(C,1)
    ev=np.clip(np.linalg.eigvalsh(C)[::-1],0,None); p=ev/ev.sum()
    pr=ev.sum()**2/(ev**2).sum(); ent=np.exp(-(p[p>0]*np.log(p[p>0])).sum())
    cum=np.cumsum(p); k=lambda t:int(np.searchsorted(cum,t)+1)
    off=C[np.triu_indices_from(C,1)]
    print(f'\n{label}: n={len(C)} meanCorr={off.mean():.3f} top5 eigen share={[round(x,3) for x in p[:5]]}')
    print(f'  effective bets: participation={pr:.0f}  entropy={ent:.0f};  PCs for 25/50/80% var = {k(.25)}/{k(.5)}/{k(.8)}')
    return D,C,ev
spectrum(sub,'320 SUBMITTED ALPHAS (need PnL in catalog)') if all(a in pnl for a in sub) else None
used=[n for n in ing.name if w.get(n,0)>0]
D,C,ev=spectrum(used,'INGREDIENTS USED IN THE 320')
