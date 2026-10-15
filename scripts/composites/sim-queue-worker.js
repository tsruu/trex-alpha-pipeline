#!/usr/bin/env node
'use strict';
// Browserless TrexSim queue worker (HTTP API only; no Playwright, no runner lock).
// Runs Fast and/or Slow jobs from a JSON queue file and saves raw results + daily PnL.
//
// Usage: node scripts/composites/sim-queue-worker.js [--queue alphas/validation/queue.json]
//          [--slow 1] [--fast 4] [--seconds N] [--until-empty] [--stop-at HH:MM(UTC)]
// Queue entries: {exp, name, mode:'os_fast'|'os', code, lookback, fast_id?, status:'pending'}
// It can run alongside the search: Slow jobs do not compete with the search's Fast queue.
// Stop it by creating alphas/validation/STOP-WORKER.
// Other tools never edit the queue directly: they drop JSON arrays of jobs into <queue dir>/inbox/,
// which this worker merges (dedup on exp+name+mode) and then deletes.
const fs = require('fs');
const path = require('path');
const root = path.resolve(__dirname, '..', '..');
const BASE = 'https://www.trexsim.com';
const arg = (k, d) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : d; };
const QFILE = path.resolve(root, arg('--queue', 'alphas/validation/queue.json'));
const OUT = path.dirname(QFILE);
const SLOW = +arg('--slow', 4), FAST = +arg('--fast', 2), SECONDS = +arg('--seconds', 0);
const UNTIL_EMPTY = process.argv.includes('--until-empty'), STOP_AT = arg('--stop-at', null);
const STOPFILE = path.join(OUT, 'STOP-WORKER');
const sleep = ms => new Promise(r => setTimeout(r, ms));
const log = (...a) => console.log(new Date().toISOString().slice(0, 19), ...a);

let cookies = {};
function setCookies(res) {
  const raw = res.headers.getSetCookie ? res.headers.getSetCookie() : [];
  for (const c of raw) { const [kv] = c.split(';'); const i = kv.indexOf('='); cookies[kv.slice(0, i).trim()] = kv.slice(i + 1).trim(); }
}
const cookieHeader = () => Object.entries(cookies).map(([k, v]) => `${k}=${v}`).join('; ');
async function req(url, opts = {}) {
  for (let a = 0; a < 6; a++) {
    try {
      const res = await fetch(BASE + url, { redirect: 'manual', ...opts, headers: { 'User-Agent': 'Mozilla/5.0', Cookie: cookieHeader(), ...(opts.headers || {}) } });
      setCookies(res);
      if (res.status >= 300 && res.status < 400 && res.headers.get('location')) return req(res.headers.get('location').replace(BASE, ''), { method: 'GET' });
      return res;
    } catch (e) { await sleep(3000 * (a + 1)); }
  }
  throw new Error('request failed ' + url);
}
let csrf = null;
function loadEnv() {
  const env = {};
  for (const line of fs.readFileSync(path.join(root, '.env'), 'utf8').split('\n')) {
    const m = line.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$/); if (m) env[m[1]] = m[2].replace(/^['"]|['"]$/g, '');
  }
  return env;
}
async function login() {
  const env = loadEnv();
  let r = await req('/trexsim/pysim/?next=/trexsim/pysim/alpha/'); let html = await r.text();
  const tok = (html.match(/name="csrfmiddlewaretoken" value="([^"]+)"/) || [])[1];
  await req('/trexsim/pysim/?next=/trexsim/pysim/alpha/', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded', Referer: BASE + '/trexsim/pysim/' },
    body: new URLSearchParams({ csrfmiddlewaretoken: tok, username: env.trexsim_username, password: env.trexsim_password, agree_terms: 'on' }).toString() });
  r = await req('/trexsim/pysim/alpha/'); html = await r.text();
  csrf = (html.match(/CSRF_TOKEN\s*=\s*['"]([^'"]+)/) || [])[1];
  if (!csrf) throw new Error('login failed');
  log('logged in');
}
async function post(p) {
  const r = await req('/trexsim/pysim/alpha/', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-CSRFToken': csrf, Referer: BASE + '/trexsim/pysim/alpha/' },
    body: new URLSearchParams({ csrfmiddlewaretoken: csrf, ...p }).toString() });
  const t = await r.text();
  try { return JSON.parse(t); } catch { if (/login|sign in/i.test(t)) { await login(); return post(p); } return { status: 'bad-response', text: t.slice(0, 200) }; }
}
const INBOX = path.join(OUT, 'inbox');
function mergeInbox() {
  if (!fs.existsSync(INBOX)) return;
  const files = fs.readdirSync(INBOX).filter(f => f.endsWith('.json')).sort();
  if (!files.length) return;
  const q = load(); const seen = new Set(q.map(j => `${j.exp}|${j.name}|${j.mode}`)); let n = 0;
  for (const f of files) {
    const p = path.join(INBOX, f);
    let jobs; try { jobs = JSON.parse(fs.readFileSync(p, 'utf8')); } catch (e) { log('bad inbox file', f); fs.renameSync(p, p + '.bad'); continue; }
    for (const j of jobs) { const k = `${j.exp}|${j.name}|${j.mode}`; if (seen.has(k)) continue; seen.add(k); q.push({ status: 'pending', lookback: 300, ...j }); n++; }
    fs.rmSync(p);
  }
  save(q); log('merged', n, 'jobs from', files.length, 'inbox file(s)');
}
const load = () => (fs.existsSync(QFILE) ? JSON.parse(fs.readFileSync(QFILE, 'utf8')) : []);
function save(q) { const tmp = QFILE + '.tmp'; fs.writeFileSync(tmp, JSON.stringify(q, null, 0)); fs.renameSync(tmp, QFILE); }
const gate = require('../submit-gate');
async function submit(j) {
  // Every submitter (search, nightly Slow runner, this worker) goes through scripts/submit-gate.js so
  // submissions stay > 2 s apart. A few retries cover submitters that do not use the gate.
  let sub;
  for (let a = 0; a < 6; a++) {
    sub = await gate.withGate(() => post({ post_type: 'simulate', action: 'submit', alpha_id: String(j.fast_id || 'none'), alpha_expression: j.code,
      region_universe: 'US:TOP1000', neut: 'industry', delay: '0', mode: j.mode, lookback: String(j.lookback || 300), slippage: j.slippage || 'no',
      slippage_value: String(j.slippage_value ?? '0.1'), liq_uni_sim: 'no' }));
    if (sub.status === 'success') return sub;
    if (!/rapid/i.test(String(sub.error || ''))) return sub;
    await sleep(3000 + Math.random() * 4000);
  }
  return { ...sub, rapid: true };
}
async function finish(j, st) {
  const r = await req(`/trexsim/pysim/alpha/${j.id}/?format=json`); const res = await r.json();
  const m = (res.stats_data && res.stats_data.metrics) || {};
  const dir = path.join(OUT, j.exp); fs.mkdirSync(dir, { recursive: true });
  const tag = j.mode === 'os_fast' ? 'fast' : 'slow';
  Object.assign(j, { status: st === 'success' ? 'done' : 'error:' + st, ir: m.ir, tvr: m.tvr, ir_tvr: m.ir_tvr, numstks: m.numstks,
    period: res.stats_data && res.stats_data.time_period, secs: Math.round((Date.now() / 1000 - j.submitted) * 10) / 10, finished: Date.now() / 1000 });
  try {
    const s = typeof res.simresdata === 'string' ? JSON.parse(res.simresdata) : res.simresdata;
    const rows = (s && s[0] && s[0].data) || [];
    fs.writeFileSync(path.join(dir, `${j.name}.${tag}.pnl.csv`), 'date,dailypnl\n' + rows.map(x => `${new Date(x.timestamps * 1000).toISOString().slice(0, 10)},${x.dailypnl}`).join('\n') + '\n');
  } catch (e) { j.pnl_error = String(e).slice(0, 200); }
  // keep_raw jobs (search keepers) keep the full response so trexsim-ingest-research-results.js can archive them.
  if (j.keep_raw) fs.writeFileSync(path.join(dir, `${j.name}.${tag}.raw.json`), JSON.stringify(res));
  delete res.simresdata; fs.writeFileSync(path.join(dir, `${j.name}.${tag}.json`), JSON.stringify(res));
  log('done', j.exp, j.name, j.mode, 'ir', j.ir, 'tvr', j.tvr, 'secs', j.secs);
}

// ---- batch notifications (ntfy). Jobs with notify:true are grouped by exp; when a group has nothing pending or
// running, the worker runs deploy/sync.sh (so results reach GitHub) and posts one message to NTFY_URL.
const NTFY_URL = process.env.NTFY_URL || 'https://ntfy.sh/trex-alpha';
const NOTIFIED = path.join(OUT, 'notified.json');
async function notifyBatches(q) {
  let done = []; try { done = JSON.parse(fs.readFileSync(NOTIFIED, 'utf8')); } catch {}
  const groups = {};
  for (const j of q) if (j.notify) (groups[j.exp] ||= []).push(j);
  for (const [exp, js] of Object.entries(groups)) {
    if (done.includes(exp) || js.some(j => ['pending', 'submitted'].includes(j.status))) continue;
    const ok = js.filter(j => j.status === 'done'), bad = js.length - ok.length;
    const slow = ok.filter(j => j.mode === 'os').slice(0, 5).map(j => `${j.name} IR ${j.ir}`).join('; ');
    const sync = require('child_process').spawnSync('bash', ['deploy/sync.sh'], { cwd: root, encoding: 'utf8', timeout: 180000 });
    const msg = `${exp} finished: ${ok.length}/${js.length} done${bad ? `, ${bad} failed` : ''}. ${slow}${slow ? '. ' : ''}` +
      (sync.status === 0 ? 'Synced to GitHub - pull on the Mac.' : 'Sync failed - run deploy/sync.sh.');
    try { await fetch(NTFY_URL, { method: 'POST', body: msg, headers: { Title: `trex-alpha: ${exp} done`, Tags: bad ? 'warning' : 'white_check_mark' } }); log('notified', exp); }
    catch (e) { log('notify failed', exp, String(e).slice(0, 200)); }
    done.push(exp); fs.writeFileSync(NOTIFIED, JSON.stringify(done));
  }
}
(async () => {
  await login(); const t0 = Date.now();
  for (;;) {
   try {
    if (fs.existsSync(STOPFILE)) { log('STOP-WORKER found'); break; }
    if (SECONDS && Date.now() - t0 > SECONDS * 1000) break;
    if (STOP_AT) { const [h, mi] = STOP_AT.split(':').map(Number); const n = new Date(); if (n.getUTCHours() * 60 + n.getUTCMinutes() >= h * 60 + mi && n.getUTCHours() * 60 + n.getUTCMinutes() < h * 60 + mi + 5) { log('stop-at reached'); break; } }
    mergeInbox();
    let q = load();
    for (const j of q.filter(j => j.status === 'submitted')) {
      const st = (await post({ post_type: 'get_result', alpha_id: j.id })).status;
      if (st && !['created', 'running'].includes(st)) { await finish(j, st); save(q); }
    }
    await notifyBatches(load());
    for (const [mode, cap] of [['os_fast', FAST], ['os', SLOW]]) {
      q = load(); let infl = q.filter(j => j.status === 'submitted' && j.mode === mode).length;
      // Highest priority first (composites > default 0 > mining jobs at -1); stable, so queue order breaks ties.
      // priority.json (written by cycle.py each hour) overrides a job's priority, e.g. demoting composites that
      // the current pool no longer has room for.
      let over = {}; try { over = JSON.parse(fs.readFileSync(path.join(OUT, 'priority.json'), 'utf8')); } catch {}
      const pr = j => over[`${j.exp}/${j.name}/${j.mode}`] ?? j.priority ?? 0;
      for (const j of [...q].sort((a, b) => pr(b) - pr(a))) {
        if (infl >= cap) break;
        if (j.status !== 'pending' || j.mode !== mode) continue;
        const sub = await submit(j);
        if (sub && sub.status === 'success') { Object.assign(j, { status: 'submitted', id: String(sub.alpha_id), submitted: Date.now() / 1000 }); infl++; log('submitted', j.exp, j.name, mode, j.id); }
        else if (sub && sub.rapid) { log('submit collided with the search; will retry', j.exp, j.name); }
        else { j.status = 'error:submit'; j.detail = JSON.stringify(sub).slice(0, 300); }
        save(q);
      }
    }
    q = load();
    if (UNTIL_EMPTY && !q.some(j => ['pending', 'submitted'].includes(j.status))) { log('queue empty'); break; }
   } catch (e) { log('loop error (continuing):', String(e).slice(0, 300)); await sleep(30000); try { await login(); } catch (e2) { log('relogin failed', String(e2).slice(0, 200)); } }
    await sleep(8000);
  }
})().catch(e => { console.error(e); process.exit(1); });
