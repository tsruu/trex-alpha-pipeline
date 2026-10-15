"""Score candidate PnLs on what they add beyond the pool's existing drivers and the 47 reference factors.
Usage: python3 research/interpretability/residual_ir.py <pnl.csv> [<pnl.csv> ...]
       python3 research/interpretability/residual_ir.py --exp SEED-D1      (all alphas/validation/SEED-D1/*.pnl.csv)
For each file: raw IR (train 2006-13 / test 2014-21), residual IR after regressing on
[top-10 pool drivers + 47 refs] fitted on train only, correlation with driver 1 and driver 7, and the top loadings."""
import sys, glob, json, numpy as np, pandas as pd
src=open('research/interpretability/s3_attribution.py').read().split("def r2_of")[0]
exec(src)   # R (26 refs), F (driver PnLs, sign-aligned), rd
ext=[f['name'] for f in json.load(open('research/interpretability/reference-ext-factors.json')) if f['name'].startswith('ref-x')]
for n in ext:
    s=rd(f'alphas/validation/REF/{n}.fast.pnl.csv')
    if s is not None and s.notna().sum()>1000 and s.std()>0: R[n.replace('ref-x-','x_')]=s/s.std()
# Refs that start late (six fundamental/size refs begin 2011-09) earn 0 before their start. Without this fill the
# row filter below silently shrank the train window to 2011-09..2013-12 (fixed 2026-10-10).
X=pd.concat([F.iloc[:,:10].add_prefix('drv'),R.fillna(0)],axis=1)
SPLIT=pd.Timestamp('2013-12-31')
def score(path):
    y=rd(path)
    if y is None or y.notna().sum()<500: return dict(file=path,error='unreadable/short')
    Z=X.reindex(y.index); m=Z.notna().all(1)&y.notna(); Z=Z[m]; yy=y[m]
    same=[c for c in Z.columns if not c.startswith('drv') and abs(np.corrcoef(Z[c],yy)[0,1])>0.999]
    Z=Z.drop(columns=same)             # a reference identical to the candidate would absorb it (residual 0)
    tr=(Z.index<=SPLIT)
    A=np.column_stack([np.ones(len(Z)),Z.values]); b,*_=np.linalg.lstsq(A[tr],yy.values[tr],rcond=None)
    res=yy.values-A[:,1:]@b[1:]          # keep the intercept inside the residual return
    ir=lambda v: v.mean()/v.std()
    t=b[1:]/ (np.sqrt(np.diag(np.linalg.pinv(A[tr].T@A[tr]))[1:]*np.var(yy.values[tr]-A[tr]@b)))
    top=sorted(zip(Z.columns,t),key=lambda z:-abs(z[1]))[:3]
    return dict(file=path.split('/')[-1],raw_ir_train=round(ir(yy.values[tr]),3),raw_ir_test=round(ir(yy.values[~tr]),3),
        resid_ir_train=round(ir(res[tr]),3),resid_ir_test=round(ir(res[~tr]),3),
        corr_d1=round(np.corrcoef(yy,Z['drv0'])[0,1],2),corr_d7=round(np.corrcoef(yy,Z['drv6'])[0,1],2),
        top=', '.join(f'{a}({c:+.0f}t)' for a,c in top))
if __name__=='__main__':
    a=sys.argv[1:]
    files=sorted(glob.glob(f'alphas/validation/{a[1]}/*.pnl.csv')) if a and a[0]=='--exp' else a
    out=pd.DataFrame([score(f) for f in files]); pd.set_option('display.width',250); print(out.to_string(index=False))
