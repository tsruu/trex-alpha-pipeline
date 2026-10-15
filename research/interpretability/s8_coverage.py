"""Step 8: how much of the pool do the two refined one-line signals explain?
Regress the pool PnL (s3: equal-risk ingredient pool, Slow, 2006-21) on the Fast PnLs of
d1-subind (closing-price reversal) and d7-both (first + last hour skew), and variants.
Reports, full sample and per half: R^2, beta t-stats, share of pool mean explained
(sum_k b_k * mean(x_k) / mean(pool)), the pool's residual IR (intercept kept in the residual),
and an out-of-sample version (betas fitted 2006-13, scored 2014-21).
Also: how well each one-liner tracks its PCA driver (corr), and the same regression with the 47 refs added.
Run from the repo root: python3 research/interpretability/s8_coverage.py"""
import warnings; warnings.filterwarnings('ignore')
import json, numpy as np, pandas as pd
src=open('research/interpretability/s3_attribution.py').read().split("def r2_of")[0]
exec(src)   # R (26 refs), F (driver PnLs), pool, rd
for n in [f['name'] for f in json.load(open('research/interpretability/reference-ext-factors.json')) if f['name'].startswith('ref-x')]:
    s=rd(f'alphas/validation/REF/{n}.fast.pnl.csv')
    if s is not None and s.notna().sum()>1000 and s.std()>0: R[n.replace('ref-x-','x_')]=s/s.std()
V='alphas/validation'
sig={k:rd(f'{V}/{p}.fast.pnl.csv') for k,p in [('d1_subind','SEED-D1/d1-subind'),('d1_base','SEED-D1/d1-base'),('d1_vixhi','SEED-D1/d1-vix-hi'),
     ('d1_lag1','SEED-D1/d1-lag1'),('d7_both','SEED-D7/d7-both'),('d7_base','SEED-D7/d7-base'),('d7_fh','SEED-D7/d7-fh')]}
S=pd.concat(sig,axis=1); S=S/S.std()
SPLIT=pd.Timestamp('2013-12-31'); ir=lambda v: v.mean()/v.std()
def fit(y,X,train=None):
    d=pd.concat([y.rename('y'),X],axis=1).dropna(); yy=d.pop('y'); A=np.column_stack([np.ones(len(d)),d.values])
    tr=np.ones(len(d),bool) if train is None else (d.index<=train)
    b,*_=np.linalg.lstsq(A[tr],yy.values[tr],rcond=None); fitted=A[:,1:]@b[1:]; res=yy.values-fitted
    e=yy.values[tr]-A[tr]@b; t=b/np.sqrt(np.diag(np.linalg.pinv(A[tr].T@A[tr]))*e.var())
    out={}
    for lab,m in [('full',np.ones(len(d),bool)),('0613',d.index<=SPLIT),('1421',d.index>SPLIT)]:
        if train is not None and lab!='1421': continue
        yv=yy.values[m]; out[lab]=dict(r2=1-np.var(yv-A[m]@b)/np.var(yv) if train is None else 1-np.var(yv-A[m]@b)/np.var(yv),
            ret_share=fitted[m].mean()/yv.mean(),pool_ir=ir(yv),resid_ir=ir(res[m]),n=m.sum())
    return out,dict(zip(['const']+list(d.columns),np.round(t,1)))
pd.set_option('display.width',250)
specs={'d1-subind':['d1_subind'],'d7-both':['d7_both'],'d1-subind + d7-both':['d1_subind','d7_both'],
       'd1-base + d7-base':['d1_base','d7_base'],'d1-subind + d1-vix-hi + d7-both':['d1_subind','d1_vixhi','d7_both'],
       'd1-subind + d1-lag1 + d7-both':['d1_subind','d1_lag1','d7_both'],
       'PCA driver 1 + driver 7':None}
rows=[]; tstats={}
for name,cols in specs.items():
    X=S[cols] if cols else F[[0,6]].rename(columns={0:'drv1',6:'drv7'})
    o,t=fit(pool,X); oo,_=fit(pool,X,SPLIT); tstats[name]=t
    for lab,v in o.items(): rows.append(dict(spec=name,sample=lab,**{k:round(x,3) if k!='n' else x for k,x in v.items()}))
    v=oo['1421']; rows.append(dict(spec=name,sample='OOS 14-21 (betas 06-13)',**{k:round(x,3) if k!='n' else x for k,x in v.items()}))
T=pd.DataFrame(rows); print('POOL on the one-liners (pool = Slow ingredient pool; IR daily)'); print(T.to_string(index=False))
print('\nt-stats (full sample):'); [print(f'  {k}: {v}') for k,v in tstats.items()]
# one-liner vs its PCA driver
J=pd.concat([S,F[[0,1,6]].rename(columns={0:'drv1',1:'drv2',6:'drv7'})],axis=1).dropna()
print('\ncorr of one-liners with PCA drivers:'); print(J.corr().loc[['d1_subind','d1_base','d7_both','d7_base','d7_fh'],['drv1','drv2','drv7']].round(2))
for d,c in [('drv1',['d1_subind']),('drv7',['d7_both']),('drv1',['d1_subind','d1_lag1','d1_vixhi']),('drv7',['d7_both','d7_base','d7_fh'])]:
    o,_=fit(F[0 if d=='drv1' else 6],S[c]); print(f'  {d} on {c}: R2 {o["full"]["r2"]:.3f}, return share {o["full"]["ret_share"]:.2f}, residual IR {o["full"]["resid_ir"]:.3f} (own IR {o["full"]["pool_ir"]:.3f})')
# add the 47 refs: what do the one-liners add beyond known factors, and vice versa
RF=R.fillna(0)   # refs that start late (2008-11) earn 0 before their start
for name,X in [('47 refs',RF),('47 refs + d1-subind + d7-both',pd.concat([RF,S[['d1_subind','d7_both']]],axis=1))]:
    o,_=fit(pool,X); oo,_=fit(pool,X,SPLIT)
    print(f'\nPOOL on {name}: R2 full {o["full"]["r2"]:.3f}, return share {o["full"]["ret_share"]:.2f}, residual IR {o["full"]["resid_ir"]:.3f} '
          f'(halves {o["0613"]["resid_ir"]:.3f} / {o["1421"]["resid_ir"]:.3f}); OOS 14-21 R2 {oo["1421"]["r2"]:.3f}, resid IR {oo["1421"]["resid_ir"]:.3f}')
T.to_csv('research/interpretability/coverage-oneliners.csv',index=False)
