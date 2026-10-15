"""Step 9: name the pool's drivers from the ingredients themselves (no guessed formulas).
1. Cluster the ingredients on PnL correlation (average linkage, distance 1-corr); a cluster = a set of real alphas.
2. Exact pool decomposition: pool = sum over clusters of sum_{i in c} w_i z_i  -> risk share = cov(part, pool)/var(pool), return share.
3. Name each cluster by what its members use: data fields, motifs, origin, vs the whole pool (enrichment).
4. Stability: re-cluster on 2006-13 and 2014-21 separately; best Jaccard match per full-sample cluster.
5. Coverage: how many clusters reach 50/80% of pool risk and return.
Run from repo root. numpy/pandas only."""
import warnings; warnings.filterwarnings('ignore')
import json, collections, numpy as np, pandas as pd
src=open('research/interpretability/s3_attribution.py').read().split("def r2_of")[0]
exec(src)                                           # Z (ingredient PnL, unit std), wt, pool, F, ing? (re-read below)
cat=pd.read_csv('research/hypothesis-audit/ingredient-catalog.csv').set_index('name')
names=list(Z.columns); N=len(names); W=np.array([wt.get(n,0.0) for n in names])
Zf=Z.fillna(0)
def corr(D): C=D.corr(min_periods=300).fillna(0).values; np.fill_diagonal(C,1); return C
def cluster(C, cut):
    # average-linkage agglomerative clustering on distance 1-C; stop when the closest pair has avg corr < 1-cut
    cl=[[i] for i in range(len(C))]; S=C.copy(); np.fill_diagonal(S,-9); size=np.ones(len(C))
    act=np.ones(len(C),bool)
    while True:
        S2=np.where(act[:,None]&act[None,:],S,-9); i,j=np.unravel_index(np.argmax(S2),S2.shape)
        if S2[i,j] < 1-cut: break
        # merge j into i (average linkage update)
        S[i,:]=(S[i,:]*size[i]+S[j,:]*size[j])/(size[i]+size[j]); S[:,i]=S[i,:]; S[i,i]=-9
        size[i]+=size[j]; act[j]=False; S[j,:]=-9; S[:,j]=-9; cl[i]+=cl[j]; cl[j]=[]
    return [c for c in cl if c]
C=corr(Z)
for cut in (0.7,0.75,0.8,0.85):
    cs=cluster(C,cut); big=[c for c in cs if len(c)>=3]
    print(f'cut avg-corr>{1-cut:.2f}: {len(cs)} clusters, {len(big)} with >=3 members covering {sum(map(len,big))} ingredients')
CUT=0.8                                              # merge while average within-cluster corr > 0.20
cs=sorted(cluster(C,CUT),key=lambda c:-W[c].sum())
part=pd.DataFrame({k:Zf.iloc[:,c].values@W[c] for k,c in enumerate(cs)},index=Z.index)
P=part.sum(1); vP=P.var(); mP=P.mean()
risk=part.apply(lambda s: np.cov(s,P)[0,1]/vP); ret=part.mean()/mP
# halves stability
def lab(cs_): 
    m={}
    for k,c in enumerate(cs_):
        for i in c: m[i]=k
    return m
h1=cluster(corr(Z.loc[:'2013']),CUT); h2=cluster(corr(Z.loc['2014':]),CUT)
def best_jacc(c,cs_): s=set(c); return max(len(s&set(d))/len(s|set(d)) for d in cs_)
# enrichment
feat={}
for n in names:
    try: f=json.loads(cat.loc[n,'features'])
    except Exception: f={}
    feat[n]=f
def tally(idx,key):
    cnt=collections.Counter(); 
    for i in idx:
        for x in set(feat[names[i]].get(key,[]) or []): cnt[x]+=1
    return cnt
allf=tally(range(N),'fields'); allm=tally(range(N),'motifs')
def origin(n): return n.split('-')[0] if '-' in n else n
rows=[]
for k,c in enumerate(cs):
    if risk[k]<0.01 and len(c)<5: continue
    zc=Zf.iloc[:,c].values@W[c]; s=pd.Series(zc,index=Z.index)
    ir=lambda x:x.mean()/x.std()
    fc=tally(c,'fields'); mc=tally(c,'motifs')
    enr=sorted([(f,fc[f]/len(c),allf[f]/N) for f in fc if fc[f]/len(c)>=0.3],key=lambda t:-(t[1]/max(t[2],0.02)))[:5]
    within=C[np.ix_(c,c)][np.triu_indices(len(c),1)].mean() if len(c)>1 else 1.0
    rows.append(dict(cl=k,n=len(c),risk=round(risk[k],3),ret=round(ret[k],3),ir=round(ir(s),3),ir_0613=round(ir(s[:'2013']),3),ir_1421=round(ir(s['2014':]),3),
        within_corr=round(within,2),stab=round(min(best_jacc(c,h1),best_jacc(c,h2)),2),
        origin=dict(collections.Counter(origin(names[i]) for i in c).most_common(3)),
        motifs=', '.join(f'{m}({mc[m]})' for m,_ in mc.most_common(2)),
        fields=', '.join(f'{f} {a:.0%} (pool {b:.0%})' for f,a,b in enr),
        top=', '.join(names[i] for i in sorted(c,key=lambda i:-W[i])[:3])))
T=pd.DataFrame(rows); pd.set_option('display.width',400); pd.set_option('display.max_colwidth',120)
print(f'\n{len(cs)} clusters at avg-corr > {1-CUT:.2f}; listed: risk>=1% or n>=5. Exact decomposition: shares sum to 1.')
print(T[['cl','n','risk','ret','ir','ir_0613','ir_1421','within_corr','stab','origin']].to_string(index=False))
print(); print(T[['cl','motifs','fields','top']].to_string(index=False))
o=np.argsort(-risk.values); cr=np.cumsum(risk.values[o])
print('\nclusters needed for 50% / 80% of pool risk:',int(np.searchsorted(cr,0.5)+1),'/',int(np.searchsorted(cr,0.8)+1),' (total clusters',len(cs),')')
print('share of risk / return in clusters with >=3 members: %.2f / %.2f'%(risk[[k for k,c in enumerate(cs) if len(c)>=3]].sum(),ret[[k for k,c in enumerate(cs) if len(c)>=3]].sum()))
# map clusters to PCA drivers 1,7,2
print('\ncorr of cluster PnL with PCA drivers 1 / 2 / 7:')
for r in rows[:12]:
    s=part[r['cl']]; print(f"  cl{r['cl']:>3} n={r['n']:>3}: {s.corr(F[0]):+.2f} {s.corr(F[1]):+.2f} {s.corr(F[6]):+.2f}")
T.to_csv('research/interpretability/clusters.csv',index=False)
json.dump({str(k):[names[i] for i in c] for k,c in enumerate(cs)},open('research/interpretability/cluster-members.json','w'),indent=0)
