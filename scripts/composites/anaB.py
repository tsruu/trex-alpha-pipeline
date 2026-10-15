import os as _os
_REPO=_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
_WORK=_os.path.join(_REPO,'alphas','composites')
import os,sys,numpy as np,pandas as pd,json
V=_os.path.join(_REPO,'alphas/validation')
def rd(f):
    s=pd.read_csv(f).set_index('date')['dailypnl']; s.index=pd.to_datetime(s.index); return s
def ir(x): return x.mean()/x.std()
W=lambda s:(s.index>='2020-01-08')&(s.index<='2021-12-30')
for parent,pf,pieces in [('41',f'{V}/A2/41-raw.fast.pnl.csv',['par0','par1','vixhi','vixlo']),('pk007',f'{V}/A1/pk007.fast.pnl.csv',['par0','par1','vixhi','vixlo','m4_0','m4_1','m4_2','m4_3'])]:
    P=rd(pf); print(f'== {parent}: parent IR {ir(P):.3f} n={len(P)}')
    S={}
    for g in pieces:
        s=rd(f'{V}/B/{parent}-{g}.fast.pnl.csv'); S[g]=s
        s2=s.reindex(P.index)
        active=(s2.abs()>0)
        # predicted piece = parent masked by the piece's active days
        pred=P.where(active,0.0)
        df=pd.concat([s2.fillna(0),pred],axis=1)
        print(f'  {g:6s} len={len(s)} active_frac={active.mean():.2f} IR(reported-series incl zeros)={ir(s2.fillna(0)):.3f} IR(active only)={ir(s2[active]):.3f} '
              f'pred IR={ir(pred):.3f} corr(piece,masked parent)={df.corr().iloc[0,1]:.3f} corr(piece,parent)[win]={np.corrcoef(s2.fillna(0)[W(P)],P[W(P)])[0,1]:.3f}')
    D=pd.DataFrame(S).reindex(P.index).fillna(0)
    print('  window corr among pieces:\n',D[W(D)].corr().round(3).to_string())
