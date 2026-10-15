"""Step 6: which drivers caused the combined alpha's worst drawdowns, and do the big drivers fail together?"""
import re, numpy as np, pandas as pd
A='research/hypothesis-audit'; OUT='research/interpretability'
ing=pd.read_csv(f'{A}/ingredient-catalog.csv'); wt=pd.read_csv(f'{OUT}/ingredient-weights.csv').set_index('name').pool_weight
L=pd.read_csv(f'{OUT}/drivers-loadings.csv',index_col=0)
def rd(p):
    try: d=pd.read_csv(re.sub(r'^.*?/trex-alpha/','',p))
    except Exception: return None
    return pd.Series(pd.to_numeric(d['dailypnl'],errors='coerce').values,index=pd.to_datetime(d['date']))
pnl={r.name:rd(r.pnl_path) for r in ing.itertuples() if isinstance(r.pnl_path,str) and r.name in L.index}
D=pd.concat(pnl,axis=1)[L.index]; Z=(D/D.std()).fillna(0)
F=pd.DataFrame(Z.values@L.values,index=Z.index); F=F*np.sign([L.iloc[np.argmax(abs(L[c].values))][c] for c in L.columns])
pool=(Z*wt.reindex(L.index).values).sum(1)
b=np.linalg.lstsq(F.values,pool.values,rcond=None)[0]; contrib=F*b; contrib['resid']=pool-contrib.sum(1)
grp=pd.DataFrame({'d1_lateday_pressure':contrib[0],'d7_intraday_distribution':contrib[6],'d5_risk_vol':contrib[4],
                  'other_drivers':contrib.drop(columns=[0,6,4,'resid']).sum(1),'idiosyncratic':contrib['resid']})
s=pool.std(); cum=pool.cumsum(); dd=cum-cum.cummax()
# worst non-overlapping drawdown episodes (peak->trough)
eps=[]; used=pd.Series(False,index=pool.index)
for _ in range(6):
    t=dd[~used].idxmin(); p=cum[:t].idxmax(); eps.append((p,t)); used[p:t]=True
    nxt=cum[t:][cum[t:]>=cum[p]]; used[t:(nxt.index[0] if len(nxt) else cum.index[-1])]=True
rows=[]
for p,t in sorted(eps,key=lambda e:dd[e[1]]):
    g=grp[p:t].sum(); tot=g.sum()
    rows.append({'peak':p.date(),'trough':t.date(),'days':(t-p).days,'loss_in_daily_sd':round(tot/s,1),**{k:f'{v/tot:.0%}' for k,v in g.items()}})
print(pd.DataFrame(rows).to_string(index=False))
# do drivers 1 and 7 lose together? correlation of 63-day rolling sums
r=grp.rolling(63).sum().dropna()
print('\ncorr of 63d returns: d1 vs d7 %.2f, d1 vs rest %.2f'%(r.d1_lateday_pressure.corr(r.d7_intraday_distribution),
      r.d1_lateday_pressure.corr(r.drop(columns=['d1_lateday_pressure']).sum(1))))
yr=grp.groupby(grp.index.year).sum()/s; print('\nannual contribution (in daily-sd units):'); print(yr.round(0).astype(int).to_string())
