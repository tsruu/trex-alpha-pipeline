"""Step 10: describe the pool's families (clusters from s9_clusters.py, CUT 0.8) for the interview. No new simulations.
Tasks (FAMILY_HANDOFF.md):
 1. per-member table: leave-one-out corr with the family PnL, pool weight, own IR (full / 06-13 / 14-21), turnover, formula, origin;
    two exemplars per family (highest LOO corr; most readable of the top 5) and the submitted alphas that contain them.
 3. yearly IR per family, 06-13 vs 14-21 with the SE of the difference.
 4. the pool's six deepest drawdowns split by family (top 10 by risk + other), same episode method as s4_drawdowns.py.
 5. robustness of the family map to the clustering cut (best Jaccard match at each other cut, and its risk share).
Outputs: family-exemplars.csv, family-refs.csv, family-yearly-ir.csv, family-drawdowns.csv, family-cut-robustness.csv (+ prints tables).
Run from the repo root: python3 research/interpretability/s10_families.py"""
import warnings; warnings.filterwarnings('ignore')
import json, os, re, numpy as np, pandas as pd
OUT='research/interpretability'; A='research/hypothesis-audit'
src=open(f'{OUT}/s9_clusters.py').read().split("C=corr(Z)")[0]
exec(src.replace("print('reference factors:'","(lambda *a,**k:None)('reference factors:'"))   # Z, Zf, W, names, N, cat, corr(), cluster(), pool
def corr(D): C=D.corr(min_periods=300).fillna(0).values.copy(); np.fill_diagonal(C,1); return C   # .copy(): pandas 3 returns read-only arrays
SCOPE=[0,1,2,5,6,3,4,7,8,14]            # handoff: first five required, rest if time allows
mem=json.load(open(f'{OUT}/cluster-members.json')); idx={n:i for i,n in enumerate(names)}
cs=[[idx[n] for n in mem[str(k)]] for k in range(len(mem))]
NAME={0:'closing-price reversal',1:'size / valuation x price',2:'last-hour skewness',3:'volume / market-state gate',4:'range / volatility',
      5:'balance sheet x size',6:'profitability / balance sheet x intraday',7:'trade activity',8:'101-formula price shape',14:'volume x high/low (101)'}
part=pd.DataFrame({k:Zf.iloc[:,c].values@W[c] for k,c in enumerate(cs)},index=Z.index); P=part.sum(1)
risk=part.apply(lambda s: np.cov(s,P)[0,1]/P.var()); retsh=part.mean()/P.mean()
ir=lambda x: x.mean()/x.std() if x.std()>0 else np.nan
def se_ir(x): return np.sqrt((1+ir(x)**2/2)/len(x))
# ---------------- formulas ----------------
def render(n):
    if n is None: return ''
    t=n.get('t')
    if t=='leaf': return f"{n['tf']}({n['p']}{','+str(n['w']) if n.get('w') else ''})"
    if t=='bin': return f"{n['op']}({render(n['a'])}, {render(n['b'])})"
    if t=='un': return f"{n['op']}{n['w'] if n.get('w') else ''}({render(n['a'])})"
    if t=='gate': return f"gate[{n['g']}]({render(n['a'])})"
    return str(n)
def nodes(n): return 0 if not isinstance(n,dict) else 1+sum(nodes(v) for v in n.values() if isinstance(v,dict))
def code(p):
    p=re.sub(r'^.*?/trex-alpha/','',p)   # the catalog stores absolute Mac paths
    try: return json.load(open(p)).get('expression') or ''
    except Exception: return ''
def short_code(c):   # drop comments/blank lines, keep it on one line
    ls=[l.strip() for l in c.splitlines() if l.strip() and not l.strip().startswith('#')]
    return ' ; '.join(ls)
blend=pd.read_csv(f'{A}/blend-attribution.csv')
subs=blend.groupby('ingredient').alpha.apply(lambda s: sorted(set(s)))
# ---------------- task 1 ----------------
rows=[]
for k in SCOPE:
    c=cs[k]; fam=Zf.iloc[:,c].values@W[c]
    for i in c:
        n=names[i]; z=Zf.iloc[:,i].values; loo=fam-W[i]*z
        zi=Z.iloc[:,i].dropna(); r=cat.loc[n] if n in cat.index else None
        tree=None
        if r is not None and isinstance(r.tree,str):
            try: tree=json.loads(r.tree)
            except Exception: tree=None
        cd=code(r.source_json) if r is not None and isinstance(r.source_json,str) else ''
        sc=short_code(cd)
        rows.append(dict(family=k,family_name=NAME.get(k,''),ingredient=n,origin=n.split('-')[0],
            loo_corr=round(np.corrcoef(z,loo)[0,1],3) if len(c)>1 else np.nan,pool_weight=round(W[i],5),
            ir=round(ir(zi),3),ir_0613=round(ir(zi[:'2013']),3),ir_1421=round(ir(zi['2014':]),3),
            turnover=r.turnover if r is not None else np.nan,
            complexity=nodes(tree) if tree else (len(re.findall(r'[a-z_]+\(',sc)) if sc else np.nan),   # tree nodes, else function calls in the code
            sign=r.sign if r is not None else np.nan,tree=render(tree) if tree else '',code=sc,
            hypothesis=r.original_hypothesis if r is not None and isinstance(r.original_hypothesis,str) else '',
            submitted_in=' '.join(subs.get(n,[]))))
E=pd.DataFrame(rows).sort_values(['family','loo_corr'],ascending=[True,False])
def pick(g):
    g=g.sort_values('loo_corr',ascending=False); a=g.iloc[0]; top=g.head(5).copy()
    top['hand']=top.origin.isin(['intraday','101']).astype(int)
    b=top.sort_values(['hand','complexity'],ascending=[False,True]).iloc[0]
    return a.ingredient,b.ingredient
EX={k:pick(E[E.family==k]) for k in SCOPE}
E['exemplar']=[('top-corr' if EX[f][0]==n else '')+('+' if EX[f][0]==n and EX[f][1]==n else '')+('readable' if EX[f][1]==n else '') for f,n in zip(E.family,E.ingredient)]
E.to_csv(f'{OUT}/family-exemplars.csv',index=False)
pd.set_option('display.width',250); pd.set_option('display.max_colwidth',140)
print('TASK 1: families in scope (risk / return share from the exact decomposition)')
for k in SCOPE:
    g=E[E.family==k]; print(f"\ncl{k} {NAME[k]}: n={len(g)}, risk {risk[k]:.3f}, return {retsh[k]:.3f}, member LOO corr median {g.loo_corr.median():.2f}")
    print(g.head(6)[['ingredient','loo_corr','pool_weight','ir','ir_0613','ir_1421','turnover','complexity','exemplar']].to_string(index=False))
# ---------------- task 1b: what each family resembles among the 47 refs ----------------
for n in [f['name'] for f in json.load(open(f'{OUT}/reference-ext-factors.json')) if f['name'].startswith('ref-x')]:
    s_=rd(f'alphas/validation/REF/{n}.fast.pnl.csv')
    if s_ is not None and s_.notna().sum()>1000 and s_.std()>0: R[n.replace('ref-x-','x_')]=s_/s_.std()
RR=[]
for k in SCOPE:
    c=pd.concat([part[k].rename('f'),R],axis=1).corr(min_periods=500)['f'].drop('f').dropna(); top=c.reindex(c.abs().sort_values(ascending=False).index)[:3]
    d=pd.concat([part[k].rename('f'),R.fillna(0)],axis=1).dropna(); A_=np.column_stack([np.ones(len(d)),d.drop(columns='f').values]); b_,*_=np.linalg.lstsq(A_,d.f.values,rcond=None)
    RR.append(dict(family=k,name=NAME[k],r2_47refs=round(1-np.var(d.f.values-A_@b_)/d.f.var(),2),ir=round(ir(d.f),3),resid_ir=round(ir(pd.Series(d.f.values-A_[:,1:]@b_[1:])),3),
                   closest=', '.join(f'{a} {v:+.2f}' for a,v in top.items())))
RR=pd.DataFrame(RR); RR.to_csv(f'{OUT}/family-refs.csv',index=False); print('\nTASK 1b: family vs 47 refs'); print(RR.to_string(index=False))
# ---------------- task 3 ----------------
Y=[]; H=[]
for k in SCOPE:
    s=part[k]; s=s[s.index>=s.ne(0).idxmax()]
    for y,v in s.groupby(s.index.year): Y.append(dict(family=k,year=y,ir=round(ir(v),3),days=len(v)))
    a,b=s[:'2013'],s['2014':]; se=np.sqrt(se_ir(a)**2+se_ir(b)**2); d=ir(b)-ir(a)
    H.append(dict(family=k,name=NAME[k],ir_0613=round(ir(a),3),ir_1421=round(ir(b),3),diff=round(d,3),se=round(se,3),z=round(d/se,1),
                  verdict='clear fall' if d/se<-2 else ('clear rise' if d/se>2 else 'within noise')))
s=P; a,b=s[:'2013'],s['2014':]; se=np.sqrt(se_ir(a)**2+se_ir(b)**2)
H.append(dict(family='pool',name='whole pool',ir_0613=round(ir(a),3),ir_1421=round(ir(b),3),diff=round(ir(b)-ir(a),3),se=round(se,3),z=round((ir(b)-ir(a))/se,1),verdict=''))
YT=pd.DataFrame(Y).pivot(index='family',columns='year',values='ir'); YT.to_csv(f'{OUT}/family-yearly-ir.csv')
HT=pd.DataFrame(H); print('\nTASK 3: IR by half (SE of the difference from sqrt((1+IR^2/2)/T) per half)'); print(HT.to_string(index=False))
print('\nyearly IR:'); print(YT.round(2).to_string())
pos=(YT.loc[SCOPE]>0).sum(1); print('\nyears with positive IR (of 16):',pos.to_dict())
# ---------------- task 4 ----------------
top10=list(risk.sort_values(ascending=False).index[:10])
G=pd.concat({f'cl{k}':part[k] for k in top10},axis=1); G['other']=P-G.sum(1)
sd=P.std(); cum=P.cumsum(); dd=cum-cum.cummax(); eps=[]; used=pd.Series(False,index=P.index)
for _ in range(6):
    t=dd[~used].idxmin(); p=cum[:t].idxmax(); eps.append((p,t)); used[p:t]=True
    nxt=cum[t:][cum[t:]>=cum[p]]; used[t:(nxt.index[0] if len(nxt) else cum.index[-1])]=True
D=[]
for p,t in sorted(eps,key=lambda e:dd[e[1]]):
    g=G[p:t].iloc[1:].sum(); tot=g.sum()   # the peak day's own PnL is not part of the loss
    D.append({'peak':p.date(),'trough':t.date(),'days':(t-p).days,'loss_daily_sd':round(tot/sd,1),**{c:round(v/tot,2) for c,v in g.items()}})
DT=pd.DataFrame(D); DT.to_csv(f'{OUT}/family-drawdowns.csv',index=False)
print('\nTASK 4: share of each drawdown by family (top 10 by risk share + other; shares sum to 1)'); print(DT.to_string(index=False))
print('risk share of the same columns:',{f'cl{k}':round(risk[k],3) for k in top10})
# ---------------- task 5 ----------------
C=corr(Z); R=[]
for cut in (0.7,0.75,0.8,0.85):
    cc=cluster(C,cut); pr=pd.DataFrame({j:Zf.iloc[:,c].values@W[c] for j,c in enumerate(cc)},index=Z.index)
    rk=pr.apply(lambda s: np.cov(s,P)[0,1]/P.var())
    for k in SCOPE:
        s=set(cs[k]); j=max(range(len(cc)),key=lambda j: len(s&set(cc[j]))/len(s|set(cc[j])))
        R.append(dict(family=k,name=NAME[k],cut=f'avg corr > {1-cut:.2f}',n_clusters=len(cc),jaccard=round(len(s&set(cc[j]))/len(s|set(cc[j])),2),
                      match_size=len(cc[j]),match_risk=round(rk[j],3),match_rank=int((rk>rk[j]).sum()+1)))
RT=pd.DataFrame(R); RT.to_csv(f'{OUT}/family-cut-robustness.csv',index=False)
print('\nTASK 5: best match of each family at each cut'); print(RT.pivot(index=['family','name'],columns='cut',values=['jaccard','match_risk','match_rank']).to_string())
