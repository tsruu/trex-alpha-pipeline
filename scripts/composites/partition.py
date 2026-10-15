import os as _os
_REPO=_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
_WORK=_os.path.join(_REPO,'alphas','composites')
import json,os,numpy as np,pandas as pd,math,itertools
os.chdir(_REPO)
d=json.load(open('alphas/research/slow-correlation.json'))
A={}; meta={}
for a in d['alphas']:
    p=a['source_pnl_csv'].split('trex-alpha/')[-1]
    import glob
    if not os.path.exists(p):
        g=glob.glob('alphas/**/'+os.path.basename(p),recursive=True)
        if not g: print('missing',p); continue
        p=g[0]
    s=pd.read_csv(p).set_index('date')['dailypnl']; s.index=pd.to_datetime(s.index)
    A[a['name']]=s; meta[a['name']]=a
P=pd.DataFrame(A)
W=(P.index>='2020-01-08')&(P.index<='2021-12-30')
def ir(s): s=s.dropna(); return s.mean()/s.std()
chk=[(n,round(ir(P[n]),3),meta[n]['ir']) for n in P.columns][:6]; print('IR check',chk)
dow=P.index.dayofweek; wk=P.index.isocalendar().week.values%2
parts={
 'weekparity2': [wk==0, wk==1],
 'dow2': [np.isin(dow,[0,1]), np.isin(dow,[2,3,4])],
 'dow5': [dow==i for i in range(5)],
 'monthhalf2': [P.index.day<=15, P.index.day>15],
}
for pname,masks in parts.items():
    rows=[]
    for n in P.columns:
        pieces=[P[n].where(m,0.0) for m in masks]
        irs=[ir(x) for x in pieces]
        cw=np.corrcoef(np.array([x[W].values for x in pieces]))
        off=cw[np.triu_indices(len(pieces),1)]
        full_corr=[np.corrcoef(x[W],P[n][W])[0,1] for x in pieces]
        rows.append((n,meta[n]['ir'],min(irs),max(irs),np.mean(off),np.mean(full_corr)))
    df=pd.DataFrame(rows,columns=['alpha','ir','min_piece_ir','max_piece_ir','corr_between_pieces','corr_piece_vs_full'])
    print('\n==',pname,'f≈',[round(m.mean(),2) for m in masks])
    print('mean ratio piece/full IR', round((df.min_piece_ir/df.ir).mean(),3), ' all pieces >0.07:', (df.min_piece_ir>0.07).sum(),'of',len(df))
    print('corr between pieces: mean',round(df.corr_between_pieces.mean(),3),'max',round(df.corr_between_pieces.max(),3),' piece-vs-full mean',round(df.corr_piece_vs_full.mean(),3))
# pool-level greedy: originals vs dow2 pieces vs weekparity pieces, no override (corr only), IR>0.07
def pool_size(series_dict):
    names=[k for k,v in series_dict.items() if ir(v)>0.07]
    names.sort(key=lambda k:-ir(series_dict[k]))
    M=pd.DataFrame({k:series_dict[k][W] for k in names}).corr()
    # simple greedy + random restarts for a better lower bound
    best=[]
    rng=np.random.default_rng(0)
    for t in range(400):
        order=names if t==0 else list(rng.permutation(names))
        ch=[]
        for c in order:
            if all(M.loc[c,x]<=0.5 for x in ch): ch.append(c)
        if len(ch)>len(best): best=ch
    return len(best), len(names)
print('\noriginals (corr-only greedy):', pool_size({n:P[n] for n in P.columns}))
for pname in ('weekparity2','dow2','dow5'):
    sd={}
    for n in P.columns:
        for i,m in enumerate(parts[pname]): sd[f'{n}#{i}']=P[n].where(m,0.0)
    print(pname,'pieces only (corr-only greedy):', pool_size(sd))
    sd.update({n:P[n] for n in P.columns})
    print(pname,'pieces + originals:', pool_size(sd))
