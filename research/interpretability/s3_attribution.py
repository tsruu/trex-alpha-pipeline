"""Step 3-4: attribute the real drivers, the pool, and each ingredient to named reference factors.
Reference factors = canonical fundamental probes (Fast PnL, industry-neutral, 2008-21) + any ref-* price factors run later."""
import json, re, glob, os, numpy as np, pandas as pd
A='research/hypothesis-audit'; OUT='research/interpretability'
REF={'value_bm':'fund-probe-16-book-to-market','earn_yield':'fund-probe-01-earnings-yield','fcf_yield':'fund-probe-11-fcf-to-mktcap',
 'gross_prof':'fund-probe-23-gross-profitability','oper_prof':'fund-probe-24-oper-profitability','roa':'fund-probe-20-roa',
 'low_accruals':'fund-probe-32-low-accruals','low_asset_growth':'fund-probe-48-low-asset-growth','low_issuance':'fund-probe-50-low-share-issuance',
 'eps_surprise':'fund-probe-68-eps-surprise-q','low_debt':'fund-probe-18-low-debt-to-mktcap','ey_vs_history':'fund-probe-77-ey-vs-history',
 'tax_growth':'fund-probe-70-tax-growth','rd_intensity':'fund-probe-35-rd-to-mktcap'}
PRICE=[]
REF_DIRS=['alphas/validation/REF','research/interpretability/data/ref-pnl']  # second = committed copy (the VM does not have the Mac's REF run data)
_seen=set()
for f in sorted(glob.glob(REF_DIRS[0]+'/*.fast.pnl.csv'))+sorted(glob.glob(REF_DIRS[1]+'/*.fast.pnl.csv')):
    if os.path.basename(f) in _seen: continue
    _seen.add(os.path.basename(f))
    k=f.split('/')[-1].split('.')[0].replace('ref-','')
    if k in ('str-1d','str-5d','mom-12-1','mom-1m','size','lowvol','illiquidity','low-turnover','overnight-rev','intraday-rev','lasthour-rev','firsthour-rev'): REF[k]=f; PRICE.append(k)
def rd(p):
    # retry: the synced folder intermittently raises errno 35 (resource deadlock) on reads
    import io, subprocess, time
    p=re.sub(r'^.*?/trex-alpha/','',p)
    if not os.path.exists(p):
        alt=os.path.join('research/interpretability/data/ref-pnl',os.path.basename(p))
        if not os.path.exists(alt): return None
        p=alt
    for k in range(6):
        try:
            d=pd.read_csv(io.StringIO(subprocess.run(['cat',p],capture_output=True,text=True,timeout=20,check=True).stdout)); break
        except Exception:
            time.sleep(0.5*(k+1))
    else: return None
    return pd.Series(pd.to_numeric(d['dailypnl'],errors='coerce').values,index=pd.to_datetime(d['date']))
ref={}
for k,n in REF.items():
    ps=[n] if n.endswith('.csv') else sorted(glob.glob(f'alphas/research/results/{n}/slow-*.pnl.csv'))+sorted(glob.glob(f'alphas/research/results/{n}/fast-*.pnl.csv'))
    if ps: ref[k]=rd(ps[0])
R=pd.concat(ref,axis=1); R=R/R.std()
print('reference factors:',len(ref),'| own IR:',{k:round(v.mean()/v.std(),3) for k,v in R.items()})
ing=pd.read_csv(f'{A}/ingredient-catalog.csv'); wt=pd.read_csv(f'{OUT}/ingredient-weights.csv').set_index('name').pool_weight
L=pd.read_csv(f'{OUT}/drivers-loadings.csv',index_col=0)
pnl={r.name:rd(r.pnl_path) for r in ing.itertuples() if isinstance(r.pnl_path,str) and r.name in L.index}
D=pd.concat(pnl,axis=1)[L.index]; Z=D/D.std()
F=pd.DataFrame(Z.fillna(0).values@L.values,index=Z.index)
F=F*np.sign([L.iloc[np.argmax(abs(L[c].values))][c] for c in L.columns])
pool=(Z.fillna(0)*wt.reindex(L.index).values).sum(1)
def r2_of(y,cols):
    X=R[cols].reindex(y.index); m=X.notna().all(1)&y.notna(); Xc=np.column_stack([np.ones(m.sum()),X[m].values])
    b,*_=np.linalg.lstsq(Xc,y[m].values,rcond=None); return 1-(y[m].values-Xc@b).var()/y[m].var()
def attr(y,label):
    X=R.reindex(y.index); m=X.notna().all(1)&y.notna(); X=X[m]; yy=y[m]
    Xc=np.column_stack([np.ones(len(X)),X.values]); b,*_=np.linalg.lstsq(Xc,yy.values,rcond=None)
    res=yy.values-Xc@b; r2=1-res.var()/yy.var()
    se=np.sqrt(np.diag(np.linalg.inv(Xc.T@Xc))*res.var()); t=b/se
    top=sorted(zip(X.columns,b[1:]*X.std().values/yy.std(),t[1:]),key=lambda z:-abs(z[2]))[:3]
    FUND=[c for c in R.columns if c not in PRICE]
    return dict(series=label,r2=round(r2,3),r2_price=round(r2_of(y,PRICE),3),r2_fund=round(r2_of(y,FUND),3),own_ir=round(yy.mean()/yy.std(),3),alpha_ir=round(b[0]/res.std(),3),
                top=', '.join(f'{a}({c:+.1f}t)' for a,_,c in top))
rows=[attr(pool,'POOL')]+[attr(F[j],f'driver{j+1}') for j in range(12)]
T=pd.DataFrame(rows); print(T.to_string(index=False)); T.to_csv(f'{OUT}/attribution-drivers.csv',index=False)
ir=[attr(Z[n].dropna(),n) for n in Z.columns]
I=pd.DataFrame(ir); I['pool_weight']=I.series.map(wt); I.to_csv(f'{OUT}/attribution-ingredients.csv',index=False)
print('\ningredients: weighted mean R2 on all 26 refs %.3f; share of pool weight with R2>0.25: %.1f%%'%(
 np.average(I.r2,weights=I.pool_weight),100*I.pool_weight[I.r2>0.25].sum()/I.pool_weight.sum()))
print(I.sort_values('r2',ascending=False).head(8)[['series','r2','r2_price','own_ir','alpha_ir','top']].to_string(index=False))
