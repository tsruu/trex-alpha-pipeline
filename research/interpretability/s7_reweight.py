"""Step 7: does managing the pool at the driver level help OUT OF SAMPLE?
Everything (scaling, PCA, cluster membership, weights) is fitted on 2006-2013 only and evaluated on 2014-2021."""
import numpy as np, pandas as pd
src=open('research/interpretability/s3_attribution.py').read().split("R=pd.concat(ref")[0]
exec(src)  # rd, wt, paths
ing=pd.read_csv(f'{A}/ingredient-catalog.csv'); wt=pd.read_csv(f'{OUT}/ingredient-weights.csv').set_index('name').pool_weight
pn={r.name:rd(r.pnl_path) for r in ing.itertuples() if isinstance(r.pnl_path,str) and wt.get(r.name,0)>0}
D=pd.concat({k:v for k,v in pn.items() if v is not None},axis=1).loc['2006':'2021']
TR,TE=D.loc[:'2013'],D.loc['2014':]
keep=TR.notna().sum().gt(500)&TE.notna().sum().gt(500); D=D.loc[:,keep]; TR,TE=D.loc[:'2013'],D.loc['2014':]
s=TR.std(); Z=(D/s).fillna(0); names=list(D.columns); N=len(names)
w0=np.array([wt[n] for n in names]); w0=w0/w0.sum()
C=(TR/s).corr(min_periods=300).fillna(0).values; np.fill_diagonal(C,1)
ev,V=np.linalg.eigh(C); o=np.argsort(ev)[::-1]; ev,V=ev[o],V[:,o]
T=int(TR.notna().sum(1).gt(N*0.5).sum()); K=int((ev>(1+np.sqrt(N/T))**2).sum())
# cluster = driver (among top 10) explaining the largest share of the ingredient's variance, if that share > 10%
share=(V[:,:10]**2)*ev[:10]            # variance of ingredient i explained by driver k (corr-matrix units)
best=share.argmax(1); cl=np.where(share.max(1)>0.10,best,-1)
def port(w): return Z.values@w
def ir(x): return x.mean()/x.std()
def stats(w,lab):
    p=pd.Series(port(w),index=Z.index); a,b=p.loc[:'2013'],p.loc['2014':]
    return dict(scheme=lab,ir_train=round(ir(a),3),ir_test=round(ir(b),3)),p
def risk_contrib(w,mask_fn):
    S=np.cov(Z.loc[:'2013'].values.T); tot=w@S@w
    return {c:(w*mask_fn(c))@S@w/tot for c in sorted(set(cl))}
S=np.cov(Z.loc[:'2013'].values.T); mu=Z.loc[:'2013'].values.mean(0)
def shares(w):
    tot=w@S@w; out={}
    for c in sorted(set(cl)):
        m=(cl==c).astype(float); out[c]=((w*m)@S@w/tot, (w*m)@mu/(w@mu))
    return out
sh0=shares(w0)
print(f'N={N} train T={T} K(real drivers, train)={K}')
print('cluster sizes:',{int(c):int((cl==c).sum()) for c in sorted(set(cl))})
print('baseline train risk/return share by cluster (-1 = no dominant driver):')
for c,(r,m) in sh0.items(): print(f'  cluster {c:>2}: risk {r:6.1%}  return {m:6.1%}')
rows=[];P={}
r,p=stats(w0,'baseline (current weights)'); rows.append(r); P['base']=p
# V1: shrink the driver-1 cluster until its train risk share equals its train return share
w1=w0.copy(); m=(cl==0)
for k in np.linspace(1,0.05,96):
    w=w0.copy(); w[m]*=k
    rr,mm=shares(w)[0]
    if rr<=mm: w1=w; break
r,p=stats(w1/w1.sum(),f'V1 cap driver-1 cluster at its return share (scale {k:.2f})'); rows.append(r); P['v1']=p
# V2: equal risk per bucket (10 driver clusters + 1 'no dominant driver' bucket), keep relative weights inside buckets
w2=np.zeros(N)
for c in sorted(set(cl)):
    m=(cl==c); wc=np.where(m,w0,0)
    if wc.sum()==0: continue
    v=np.sqrt(wc@S@wc); w2+=wc/v
r,p=stats(w2/w2.sum(),'V2 equal risk per driver bucket'); rows.append(r); P['v2']=p
# V3: risk budget proportional to train return share (more aggressive, more overfit-prone)
w3=np.zeros(N)
for c,(rs,ms) in sh0.items():
    m=(cl==c); wc=np.where(m,w0,0)
    if wc.sum()==0 or ms<=0: continue
    w3+=wc/np.sqrt(wc@S@wc)*ms
r,p=stats(w3/w3.sum(),'V3 risk budget proportional to train return share'); rows.append(r); P['v3']=p
R=pd.DataFrame(rows); print(R.to_string(index=False))
# block bootstrap of test-period IR difference vs baseline
rng=np.random.default_rng(0); b=P['base'].loc['2014':].values; n=len(b); L=63
for k in ['v1','v2','v3']:
    x=P[k].loc['2014':].values; d=[]
    for _ in range(1000):
        st=rng.integers(0,n-L,n//L+1); idx=np.concatenate([np.arange(s0,s0+L) for s0 in st])[:n]
        d.append(ir(x[idx])-ir(b[idx]))
    d=np.array(d); print(f'{k}: test IR diff {ir(x)-ir(b):+.3f}  bootstrap SE {d.std():.3f}  P(diff<=0) {np.mean(d<=0):.2f}')
# drawdown and driver-1 share on test
for k in ['base','v1','v2']:
    x=P[k].loc['2014':]; x=x/x.std(); cum=x.cumsum(); dd=(cum-cum.cummax()).min()
    print(f'{k}: test max drawdown {dd:.1f} daily-SD units')
R.to_csv('research/interpretability/reweight-holdout.csv',index=False)
