"""Step 6: re-run the attribution with the extended reference library (reference-ext-factors.json) and compare with the original 26.
Also reports the timing tests (tim-*)."""
import json, glob, numpy as np, pandas as pd
src=open('research/interpretability/s3_attribution.py').read().split("rows=[attr(pool")[0]
exec(src)   # builds R (26 refs), PRICE, Z, F, pool, wt, rd
OLD=list(R.columns)
EXT=[f['name'] for f in json.load(open('research/interpretability/reference-ext-factors.json')) if f['name'].startswith('ref-x')]
new={}
for n in EXT:
    p=f'alphas/validation/REF/{n}.fast.pnl.csv'
    try: s=rd(p)
    except Exception: s=None
    if s is not None and s.notna().sum()>1000 and s.std()>0: new[n.replace('ref-x-','x_')]=s
RX=pd.concat([R,pd.concat(new,axis=1)],axis=1); RX[list(new)]=RX[list(new)]/RX[list(new)].std()
print('extended factors loaded:',len(new),{k:round(v.mean()/v.std(),3) for k,v in new.items()})
def fit(y,cols,train=None):
    X=RX[cols].reindex(y.index); m=X.notna().all(1)&y.notna(); X=X[m]; yy=y[m]
    Xc=np.column_stack([np.ones(len(X)),X.values]); n,k=Xc.shape
    tr=np.ones(n,bool) if train is None else (X.index<=train)
    b,*_=np.linalg.lstsq(Xc[tr],yy.values[tr],rcond=None); res=yy.values-Xc@b
    r2=1-res[tr].var()/yy.values[tr].var(); adj=1-(1-r2)*(tr.sum()-1)/(tr.sum()-k)
    oos=None if train is None else 1-res[~tr].var()/yy.values[~tr].var()
    se=np.sqrt(np.diag(np.linalg.pinv(Xc[tr].T@Xc[tr]))*res[tr].var()); t=b/se
    top=sorted(zip(cols,t[1:]),key=lambda z:-abs(z[1]))[:4]
    return dict(r2=round(r2,3),adj_r2=round(adj,3),oos_r2=None if oos is None else round(oos,3),
                alpha_ir=round((b[0]+res[tr]).mean()/res[tr].std(),3) if train is None else None,top=', '.join(f'{a}({c:+.1f}t)' for a,c in top))
ALL=OLD+list(new)
rows=[]
for lab,y in [('POOL',pool)]+[(f'driver{j+1}',F[j]) for j in range(10)]:
    a=fit(y,OLD); b=fit(y,ALL); ao=fit(y,OLD,pd.Timestamp('2013-12-31')); bo=fit(y,ALL,pd.Timestamp('2013-12-31'))
    rows.append(dict(series=lab,own_ir=round(y.mean()/y.std(),3),r2_26=a['r2'],r2_ext=b['r2'],adj_26=a['adj_r2'],adj_ext=b['adj_r2'],
        oos_r2_26=ao['oos_r2'],oos_r2_ext=bo['oos_r2'],alpha_ir_26=a['alpha_ir'],alpha_ir_ext=b['alpha_ir'],top_ext=b['top']))
T=pd.DataFrame(rows); pd.set_option('display.width',250); print(T.drop(columns='top_ext').to_string(index=False))
print(T[['series','top_ext']].to_string(index=False))
T.to_csv('research/interpretability/attribution-extended.csv',index=False)
# ingredient level
w=[];r26=[];rx=[]
for n in Z.columns:
    y=Z[n].dropna()
    if y.notna().sum()<1000: continue
    w.append(wt.get(n,0)); r26.append(fit(y,OLD)['adj_r2']); rx.append(fit(y,ALL)['adj_r2'])
w=np.array(w); print('ingredients: pool-weighted adj R2 26=%.3f ext=%.3f'%(np.average(r26,weights=w),np.average(rx,weights=w)))
# timing
lh=rd('alphas/validation/REF/ref-lasthour-rev.fast.pnl.csv'); lc=rd('alphas/validation/REF/tim-lh-from-close.fast.pnl.csv')
print('timing: corr(lasthour-rev, rebuilt-from-close) = %.3f'%pd.concat([lh,lc],axis=1).dropna().corr().iloc[0,1])
for n in ['tim-fwd-ret1','tim-fwd2-ret1','tim-fwd-gap1','tim-fwd-gap2','tim-fwd-lh','tim-lh-from-close']:
    s=rd(f'alphas/validation/REF/{n}.fast.pnl.csv'); print(n, round(s.mean()/s.std(),3))
