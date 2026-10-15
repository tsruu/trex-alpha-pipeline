"""Step 5: (a) does driver 1 / last-hour reversal pay more in turbulent markets? (b) what is driver 7 made of?"""
import json, re, numpy as np, pandas as pd
A='research/hypothesis-audit'; OUT='research/interpretability'
def rdp(p):
    d=pd.read_csv(re.sub(r'^.*?/trex-alpha/','',p)); return pd.Series(pd.to_numeric(d['dailypnl'],errors='coerce').values,index=pd.to_datetime(d['date']))
ref={k:rdp(f'alphas/validation/REF/ref-{k}.fast.pnl.csv') for k in ['size','lowvol','mom-12-1','lasthour-rev','firsthour-rev','str-1d']}
ing=pd.read_csv(f'{A}/ingredient-catalog.csv').set_index('name'); wt=pd.read_csv(f'{OUT}/ingredient-weights.csv').set_index('name').pool_weight
L=pd.read_csv(f'{OUT}/drivers-loadings.csv',index_col=0)
pn={}
for n in L.index:
    try: pn[n]=rdp(ing.loc[n,'pnl_path'])
    except Exception: pass
D=pd.concat(pn,axis=1)[L.index]; Z=(D/D.std()).fillna(0)
F=pd.DataFrame(Z.values@L.values,index=Z.index); F=F*np.sign([L.iloc[np.argmax(abs(L[c].values))][c] for c in L.columns])
# (a) turbulence proxy: trailing 21d volatility of slow, dollar-neutral factor books (size, low-vol, 12-1 momentum), lagged 1 day
slow=pd.concat([ref['size'],ref['lowvol'],ref['mom-12-1']],axis=1); slow=slow/slow.std()
turb=slow.abs().mean(1).rolling(21).mean().shift(1).dropna()
q=pd.qcut(turb,3,labels=['calm','mid','turbulent'])
print('(a) daily IR by turbulence tercile (proxy known only from past data)')
for name,s in [('driver1',F[0]),('driver7',F[6]),('ref lasthour-rev',ref['lasthour-rev']),('ref str-1d',ref['str-1d']),('ref firsthour-rev',ref['firsthour-rev'])]:
    x=pd.concat([s.rename('r'),q.rename('reg')],axis=1).dropna(); g=x.groupby(x.columns[1],observed=True)[x.columns[0]]
    ir=(g.mean()/g.std()).round(3).to_dict()
    # half-sample check
    h=[ (lambda y:(y.groupby(y.columns[1],observed=True)[y.columns[0]].mean()/y.groupby(y.columns[1],observed=True)[y.columns[0]].std()).round(3).to_dict())(x.loc[a:b]) for a,b in [('2006','2013'),('2014','2021')]]
    print(f'  {name:18s} all={ir}  2006-13={h[0]}  2014-21={h[1]}')
# (b) driver 7 composition
l=L.iloc[:,6]; l=l*np.sign(l.iloc[np.argmax(abs(l.values))]); top=l.sort_values(ascending=False).head(10)
print('\n(b) driver 7 top-loading ingredients')
for n,v in top.items():
    f=json.loads(ing.loc[n,'features']) if isinstance(ing.loc[n,'features'],str) else {}
    leaves='; '.join(f"{x.get('tf','')}({x.get('primitive_expression','')[:70]},{x.get('w','')})" for x in f.get('leaves',[]))
    print(f"  {v:.2f} w={wt.get(n,0):.4f} {n}: sign={ing.loc[n,'sign']} ops={f.get('operators')} gates={f.get('gates')} | {leaves[:230]}")
