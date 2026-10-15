"""Resumable TrexSim job queue: each `tick` call submits/polls for up to N seconds, then exits.
Jobs persist in QFILE so work survives the shell's time limit."""
import os as _os
_REPO=_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
_WORK=_os.path.join(_REPO,'alphas','composites')
import json,os,sys,time,pickle,fcntl,subprocess
sys.path.insert(0,_os.path.dirname(_os.path.abspath(__file__)))
from trex_http import Trex, metrics, pnl, BASE
OUT=_os.path.join(_REPO,'alphas/validation')
QFILE=os.path.join(OUT,'queue.json'); CK=_os.path.join(_WORK,'cookies.pkl')
def load():
    if not os.path.exists(QFILE): return []
    result=subprocess.run(['cat',QFILE],capture_output=True,text=True,timeout=10,check=True)
    return json.loads(result.stdout)
def save(q):
    tmp=QFILE+f'.{os.getpid()}.tmp'
    with open(tmp,'w') as f: json.dump(q,f,indent=0)
    os.replace(tmp,QFILE)
def save_updates(jobs):
    updates={(j['exp'],j['name'],j['mode']):j for j in jobs}
    q=load()
    for i,j in enumerate(q):
        key=(j['exp'],j['name'],j['mode'])
        if key in updates: q[i]=updates[key]
    save(q)
def add(jobs):
    os.makedirs(OUT,exist_ok=True); q=load(); names={(j['exp'],j['name'],j['mode']) for j in q}
    n=0
    for j in jobs:
        if (j['exp'],j['name'],j['mode']) in names: continue
        j.setdefault('status','pending'); j.setdefault('lookback',300); q.append(j); n+=1
    save(q); print('added',n,'queue size',len(q))
def session():
    t=Trex.__new__(Trex)
    import requests,threading,re
    t.s=requests.Session(); t.s.headers['User-Agent']='Mozilla/5.0'; t.submit_lock=threading.Lock(); t.last_submit=0
    if os.path.exists(CK):
        t.s.cookies.update(pickle.load(open(CK,'rb')))
        r=t.s.get(BASE+'/trexsim/pysim/alpha/',timeout=30); m=re.search(r"CSRF_TOKEN\s*=\s*['\"]([^'\"]+)",r.text)
        if m: t.csrf=m.group(1); return t
    print('Logging in to TrexSim...',flush=True)
    t.login()
    os.makedirs(_WORK,exist_ok=True)
    with open(CK,'wb') as f: pickle.dump(t.s.cookies,f)
    print('Logged in.',flush=True)
    return t
def finish(t,j,st):
    res=t.result(j['id']); d=os.path.join(OUT,j['exp']); os.makedirs(d,exist_ok=True)
    tag='fast' if j['mode']=='os_fast' else 'slow'
    m=metrics(res); j.update(status='done' if st=='success' else 'error:'+str(st),finished=time.time(),**m,
        period=(res.get('stats_data') or {}).get('time_period'),secs=round(time.time()-j['submitted'],1))
    try: pnl(res).to_csv(os.path.join(d,f"{j['name']}.{tag}.pnl.csv"),header=['dailypnl'],index_label='date')
    except Exception as e: j['pnl_error']=str(e)[:200]
    res.pop('simresdata',None); json.dump(res,open(os.path.join(d,f"{j['name']}.{tag}.json"),'w'))
def tick(seconds=150, fast_inflight=4, slow_inflight=1, exp=None):
    selected=lambda j: exp is None or j['exp']==exp
    q=[j for j in load() if selected(j)]
    if not any(j['status'] in ('pending','submitted') for j in q):
        print('No active jobs'+(f' for {exp}' if exp else '')+'.',flush=True); return
    t=session(); t0=time.time()
    last_progress=0
    while time.time()-t0<seconds:
        q=[j for j in load() if selected(j)]
        for j in q:
            if j['status']!='submitted': continue
            st=t.post({'post_type':'get_result','alpha_id':j['id']}).get('status')
            if st and st not in ('created','running'):
                finish(t,j,st); save_updates([j])
                print('Finished',j['exp'],j['name'],j['status'],'ir=',j.get('ir'),flush=True)
        for mode,cap in (('os_fast',fast_inflight),('os',slow_inflight)):
            infl=sum(1 for j in q if j['status']=='submitted' and j['mode']==mode)
            for j in q:
                if infl>=cap or time.time()-t0>seconds-10: break
                if j['status']!='pending' or j['mode']!=mode: continue
                sub=None
                for attempt in range(6):
                    sub=t._submit({'alpha_id':str(j.get('fast_id','none')),'alpha_expression':j['code'],'region_universe':'US:TOP1000','neut':'industry','delay':'0','mode':mode,'lookback':str(j['lookback']),'slippage':'no','slippage_value':'0.1','liq_uni_sim':'no'})
                    if sub.get('status')=='success': break
                    time.sleep(5)
                if sub.get('status')=='success': j.update(status='submitted',id=str(sub['alpha_id']),submitted=time.time()); infl+=1
                else: j.update(status='error:submit',detail=str(sub)[:300])
                save_updates([j])
                print(j['status'],j['exp'],j['name'],'id=',j.get('id'),j.get('detail',''),flush=True)
        if not any(j['status'] in ('pending','submitted') for j in q): break
        if time.time()-last_progress>=30:
            from collections import Counter
            print('Progress:',dict(Counter(j['status'] for j in q)),
                  'elapsed',round(time.time()-t0),'s',flush=True)
            last_progress=time.time()
        time.sleep(4)
    q=[j for j in load() if selected(j)]; from collections import Counter
    print('queue:',dict(Counter(j['status'] for j in q)),flush=True)
def report(exp=None):
    for j in load():
        if exp and j['exp']!=exp: continue
        print(f"{j['exp']:22s} {j['name']:28s} {j['mode']:7s} {j['status']:10s} ir={j.get('ir')} tvr={j.get('tvr')} secs={j.get('secs')} id={j.get('id')}")
if __name__=='__main__':
    cmd=sys.argv[1]
    if cmd=='tick': tick(float(sys.argv[2]) if len(sys.argv)>2 else 150)
    elif cmd=='report': report(sys.argv[2] if len(sys.argv)>2 else None)
