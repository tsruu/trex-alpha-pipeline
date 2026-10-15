import os as _os
_REPO=_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
_WORK=_os.path.join(_REPO,'alphas','composites')
import os, re, time, json, threading, subprocess, requests
ROOT = _REPO
BASE = 'https://www.trexsim.com'
LOCK = os.path.join(ROOT, '.trexsim-runner.lock')

def load_env():
    # A bounded subprocess avoids indefinite open() hangs on synced macOS files.
    try:
        result = subprocess.run(['cat', os.path.join(ROOT, '.env')],
                                capture_output=True, text=True, timeout=10)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError('Reading .env timed out after 10s; check local file availability') from exc
    if result.returncode:
        raise RuntimeError('Cannot read .env: ' + result.stderr.strip())
    env = dict(os.environ)
    for line in result.stdout.splitlines():
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1); env[k.strip()] = v.strip().strip('"').strip("'")
    missing = [k for k in ('trexsim_username', 'trexsim_password') if not env.get(k)]
    if missing:
        raise RuntimeError('Missing credentials: ' + ', '.join(missing))
    return env

class Trex:
    def __init__(self):
        self.s = requests.Session(); self.s.headers['User-Agent'] = 'Mozilla/5.0'
        self.submit_lock = threading.Lock(); self.last_submit = 0
        self.login()
    def login(self):
        env = load_env()
        r = self.s.get(BASE + '/trexsim/pysim/?next=/trexsim/pysim/alpha/', timeout=30)
        r.raise_for_status()
        token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', r.text)
        if not token: raise RuntimeError('Login page has no CSRF form token')
        tok = token.group(1)
        r = self.s.post(BASE + '/trexsim/pysim/?next=/trexsim/pysim/alpha/', data={
            'csrfmiddlewaretoken': tok, 'username': env['trexsim_username'], 'password': env['trexsim_password'],
            'agree_terms': 'on'}, headers={'Referer': BASE + '/trexsim/pysim/'}, timeout=30)
        r = self.s.get(BASE + '/trexsim/pysim/alpha/', timeout=30)
        m = re.search(r"CSRF_TOKEN\s*=\s*['\"]([^'\"]+)", r.text)
        if not m: raise RuntimeError('login failed: no CSRF_TOKEN on app page')
        self.csrf = m.group(1)
    def post(self, p):
        p = {'csrfmiddlewaretoken': self.csrf, **p}
        for attempt in range(5):
            try:
                r = self.s.post(BASE + '/trexsim/pysim/alpha/', data=p, headers={'X-CSRFToken': self.csrf, 'Referer': BASE + '/trexsim/pysim/alpha/'}, timeout=60)
                return r.json()
            except Exception as e:
                time.sleep(3 * (attempt + 1))
        raise RuntimeError('post failed')
    def result(self, aid):
        for attempt in range(5):
            try: return self.s.get(f'{BASE}/trexsim/pysim/alpha/{aid}/?format=json', timeout=120).json()
            except Exception: time.sleep(3 * (attempt + 1))
        raise RuntimeError('result fetch failed')
    def _submit(self, params):
        with self.submit_lock:
            wait = 2.6 - (time.time() - self.last_submit)
            if wait > 0: time.sleep(wait)
            sub = self.post({'post_type': 'simulate', 'action': 'submit', **params})
            self.last_submit = time.time()
        return sub
    def run(self, code, mode='os_fast', lookback=300, alpha_id='none', poll=1.5, max_wait=3600):
        sub = self._submit({'alpha_id': str(alpha_id), 'alpha_expression': code, 'region_universe': 'US:TOP1000', 'neut': 'industry',
                            'delay': '0', 'mode': mode, 'lookback': str(lookback), 'slippage': 'no', 'slippage_value': '0.1', 'liq_uni_sim': 'no'})
        if sub.get('status') != 'success': return {'error': 'submit', 'sub': sub}
        aid = str(sub['alpha_id']); t0 = time.time()
        while True:
            time.sleep(poll)
            st = self.post({'post_type': 'get_result', 'alpha_id': aid})
            if st.get('status') not in ('created', 'running'): break
            if time.time() - t0 > max_wait: return {'error': 'timeout', 'id': aid}
        res = self.result(aid); res['_id'] = aid; res['_status'] = st.get('status'); res['_secs'] = round(time.time() - t0, 1)
        return res

def metrics(res):
    m = (res.get('stats_data') or {}).get('metrics') or {}
    return {k: m.get(k) for k in ('ir', 'tvr', 'ir_tvr', 'numstks')}

def pnl(res):
    import pandas as pd
    s = res.get('simresdata'); s = json.loads(s) if isinstance(s, str) else s
    rows = s[0]['data']
    d = pd.Series({pd.Timestamp(time.strftime('%Y-%m-%d', time.gmtime(x['timestamps']))): x['dailypnl'] for x in rows})
    return d.sort_index()

def acquire_lock(tool='claude-validation'):
    fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.write(fd, (json.dumps({'pid': os.getpid(), 'startedAt': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'tool': tool}) + '\n').encode()); os.close(fd)
