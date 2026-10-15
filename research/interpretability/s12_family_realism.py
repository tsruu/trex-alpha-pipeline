"""Step 12: would I trade each family in the real world? (10 families chosen in s11; no new simulations)
Per family, from its members' own Slow simulation stats (pool-weighted):
  turnover (tvr: dollars traded per day / book), annual return (ret, on book), IR/sqrt(tvr),
  break-even cost = daily return / daily turnover, in basis points per dollar traded (the simulator charged no costs).
From the exact pool decomposition (family PnL = sum of w_i z_i):
  share of the pool's loss on its worst 5% of days vs the family's normal risk share ("down-day share / risk share"),
  and the family's own worst-day size in daily SDs.
Output: family-realism.csv. Run from the repo root: python3 research/interpretability/s12_family_realism.py"""
import warnings; warnings.filterwarnings('ignore')
import json, re, numpy as np, pandas as pd
OUT='research/interpretability'
exec(open(f'{OUT}/s10_families.py').read().split("# ---------------- formulas")[0])   # cs, part, P, risk, retsh, W, names, cat, ir, Z
TEN={0:'closing-price reversal',1:'earnings yield vs own history',2:'last-hour skewness',5:'current-liabilities share',
     4:'wide range on high-volume days',11:'approaching earnings',20:'many small trades at the close',12:'overnight gap reversal',
     6:'short-term move x profitability',8:'intraday reversal (101 formulas)'}
def stats(n):
    p=re.sub(r'^.*?/trex-alpha/','',str(cat.loc[n,'source_json']))
    try: t=json.load(open(p)).get('title','')
    except Exception: return None
    g=lambda k: float(re.search(rf'\b{k}\s+(-?[\d.]+)',t).group(1)) if re.search(rf'\b{k}\s+(-?[\d.]+)',t) else np.nan
    return dict(ret=g('ret'),tvr=g('tvr'),dd=g('dd'))
bad=P.quantile(0.05); worst=P<=bad
rows=[]
for k,name in TEN.items():
    c=cs[k]; S=pd.DataFrame([dict(w=W[i],**(stats(names[i]) or {})) for i in c]).dropna()
    w=S.w/S.w.sum(); ret=(w*S.ret).sum(); tvr=(w*S.tvr).sum()
    be=(S.ret/252)/S.tvr*1e4                       # per member, bps per dollar traded
    down=part[k][worst].sum()/P[worst].sum()
    s=part[k]; s=s[s.index>=s.ne(0).idxmax()]
    rows.append(dict(cl=k,family=name,members=len(c),risk_share=round(risk[k],3),turnover=round(tvr,2),ann_return=round(ret,3),
        ir_per_sqrt_tvr=round(ir(s)/np.sqrt(tvr),3),breakeven_bps=round((ret/252)/tvr*1e4,1),
        breakeven_bps_member_range=f'{be.min():.1f}-{be.max():.1f}',down_day_share=round(down,3),down_vs_risk=round(down/risk[k],2),
        worst_day_sd=round(s.min()/s.std(),1)))
T=pd.DataFrame(rows); T.to_csv(f'{OUT}/family-realism.csv',index=False)
pd.set_option('display.width',250); print(T.to_string(index=False))
print(f'\npool worst 5% of days: {worst.sum()} days (daily PnL <= {bad/P.std():.2f} SD). down_vs_risk > 1 = over-represented on bad days.')
