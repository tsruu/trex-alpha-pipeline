"""Step 11: screen every family (s9 clusters at CUT 0.8, >= 3 members) to choose which ones to describe and test.
For each family: size (risk / return share), IR full and per half with the change in SE units, years with positive IR,
R^2 on the 47 refs and residual IR, the best leave-one-out member correlation, split-half stability (from clusters.csv)
and cut robustness (min Jaccard of the best match at the other cuts).
Output: family-screen.csv. Run from the repo root: python3 research/interpretability/s11_family_screen.py"""
import warnings; warnings.filterwarnings('ignore')
import json, numpy as np, pandas as pd
OUT='research/interpretability'
exec(open(f'{OUT}/s10_families.py').read().split("# ---------------- formulas")[0])   # Z, Zf, W, names, cs, part, P, risk, retsh, ir, se_ir, R, corr, cluster
for n in [f['name'] for f in json.load(open(f'{OUT}/reference-ext-factors.json')) if f['name'].startswith('ref-x')]:
    s_=rd(f'alphas/validation/REF/{n}.fast.pnl.csv')
    if s_ is not None and s_.notna().sum()>1000 and s_.std()>0: R[n.replace('ref-x-','x_')]=s_/s_.std()
stab=pd.read_csv(f'{OUT}/clusters.csv').set_index('cl').stab
C=corr(Z); other={cut:cluster(C,cut) for cut in (0.7,0.75,0.85)}
rows=[]
for k,c in enumerate(cs):
    if len(c)<3: continue
    s=part[k]; s=s[s.index>=s.ne(0).idxmax()]; a,b=s[:'2013'],s['2014':]
    yr=s.groupby(s.index.year).apply(ir)
    d=pd.concat([s.rename('f'),R.fillna(0)],axis=1).dropna(); A_=np.column_stack([np.ones(len(d)),d.drop(columns='f').values]); b_,*_=np.linalg.lstsq(A_,d.f.values,rcond=None)
    fam=Zf.iloc[:,c].values@W[c]; loo=max(np.corrcoef(Zf.iloc[:,i].values,fam-W[i]*Zf.iloc[:,i].values)[0,1] for i in c)
    jac=min(max(len(set(c)&set(x))/len(set(c)|set(x)) for x in other[cut]) for cut in other)
    rows.append(dict(cl=k,n=len(c),risk=round(risk[k],3),ret=round(retsh[k],3),ir=round(ir(s),3),ir_0613=round(ir(a),3),ir_1421=round(ir(b),3),
        change_z=round((ir(b)-ir(a))/np.sqrt(se_ir(a)**2+se_ir(b)**2),1),yrs_pos=f'{int((yr>0).sum())}/{len(yr)}',
        r2_refs=round(1-np.var(d.f.values-A_@b_)/d.f.var(),2),resid_ir=round(ir(pd.Series(d.f.values-A_[:,1:]@b_[1:])),3),
        best_loo=round(loo,2),half_stab=stab.get(k,np.nan),cut_jacc=round(jac,2)))
T=pd.DataFrame(rows).sort_values('risk',ascending=False)
T.to_csv(f'{OUT}/family-screen.csv',index=False); pd.set_option('display.width',250); print(T.to_string(index=False))
