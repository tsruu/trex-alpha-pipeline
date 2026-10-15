"""Queue TrexSim jobs the way the VM expects: drop a JSON array into alphas/validation/inbox/.
The running worker (scripts/composites/sim-queue-worker.js) merges inbox files into queue.json (dedup on exp+name+mode).
Usage:  python3 research/interpretability/enqueue.py jobs.json
jobs.json: [{"exp":"SEED","name":"d1-closevwap-base","mode":"os_fast","code":"alpha = cs_rank(-(close / (vwap_last_hour + 1e-9) - 1))","lookback":30}, ...]
mode: "os_fast" (Fast, ~15-30 s) or "os" (Slow, minutes; needs a lookback >= the longest window used + a margin)."""
import json, os, sys, time
ROOT=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
jobs=json.load(open(sys.argv[1]))
for j in jobs:
    assert {'exp','name','mode','code'}<=set(j), j
    assert j['mode'] in ('os_fast','os'), j['mode']
    j.setdefault("lookback",300); j.setdefault("status","pending"); j.setdefault("notify",True)  # worker pings ntfy + syncs when an exp group finishes
inbox=os.path.join(ROOT,'alphas/validation/inbox'); os.makedirs(inbox,exist_ok=True)
p=os.path.join(inbox,f"{int(time.time()*1000)}-{jobs[0]['exp'].lower()}.json")
json.dump(jobs,open(p,'w'),indent=1); print('wrote',len(jobs),'jobs ->',p)
