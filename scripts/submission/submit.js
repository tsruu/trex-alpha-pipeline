#!/usr/bin/env node
'use strict';
// Submit the final list to the competition, exactly as the site's "Submit" -> "Submit Alpha" buttons do:
//   1. POST /trexsim/pysim/alpha/     post_type=check_submission_validity  (the "Max Correlation to Pool" box)
//   2. POST /trexsim/pysim/alphalist/ alpha_submit_production=true, alphaid=<id>, + the form fields the site
//      pre-fills from post_type=get_last_sub_info (the "Submit Alpha" button)
// An alpha whose check says eligible=false (red verdict; the site disables the button) is NOT submitted and is
// reported. Progress is kept in alphas/submission/submitted.json, so re-running skips what is already in.
//
// Usage (on the server, where .env holds the login):
//   node scripts/submission/submit.js --dry-run        # checks only, submits nothing
//   node scripts/submission/submit.js --limit 1        # submit one, then stop (first test)
//   node scripts/submission/submit.js                  # submit everything whose commented Slow run is done
const fs = require('fs'), path = require('path');
const root = path.resolve(__dirname, '..', '..'); const BASE = 'https://www.trexsim.com';
const argv = process.argv.slice(2); const flag = k => argv.includes(k); const opt = (k, d) => { const i = argv.indexOf(k); return i >= 0 ? argv[i + 1] : d; };
const DRY = flag('--dry-run'), LIMIT = Number(opt('--limit', 1e9)), ONLY = opt('--only', null), GAP = Number(opt('--gap-ms', 3000));
const NTFY = process.env.NTFY_URL || 'https://ntfy.sh/trex-alpha';
const SUB = path.join(root, 'alphas/submission'); const DONE_F = path.join(SUB, 'submitted.json'); const LOG_F = path.join(SUB, 'submission-log.jsonl');
const sleep = ms => new Promise(r => setTimeout(r, ms));
const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a);

// ---- HTTP session (same login as the queue worker)
let cookies = {}, csrf = null;
const setCookies = res => { for (const c of (res.headers.getSetCookie ? res.headers.getSetCookie() : [])) { const [kv] = c.split(';'); const i = kv.indexOf('='); cookies[kv.slice(0, i).trim()] = kv.slice(i + 1).trim(); } };
const ck = () => Object.entries(cookies).map(([k, v]) => `${k}=${v}`).join('; ');
async function req(url, opts = {}) {
  for (let a = 0; a < 5; a++) {
    try {
      const res = await fetch(BASE + url, { redirect: 'manual', ...opts, headers: { 'User-Agent': 'Mozilla/5.0', Cookie: ck(), ...(opts.headers || {}) } });
      setCookies(res);
      if (res.status >= 300 && res.status < 400 && res.headers.get('location')) return req(res.headers.get('location').replace(BASE, ''));
      return res;
    } catch (e) { await sleep(3000 * (a + 1)); }
  }
  throw new Error('request failed ' + url);
}
async function login() {
  const env = {}; for (const l of fs.readFileSync(path.join(root, '.env'), 'utf8').split('\n')) { const m = l.match(/^\s*([A-Za-z_]\w*)\s*=\s*(.*)\s*$/); if (m) env[m[1]] = m[2].replace(/^['"]|['"]$/g, ''); }
  let html = await (await req('/trexsim/pysim/?next=/trexsim/pysim/alpha/')).text();
  const tok = (html.match(/name="csrfmiddlewaretoken" value="([^"]+)"/) || [])[1];
  await req('/trexsim/pysim/?next=/trexsim/pysim/alpha/', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded', Referer: BASE + '/trexsim/pysim/' },
    body: new URLSearchParams({ csrfmiddlewaretoken: tok, username: env.trexsim_username, password: env.trexsim_password, agree_terms: 'on' }).toString() });
  html = await (await req('/trexsim/pysim/alpha/')).text();
  csrf = (html.match(/CSRF_TOKEN\s*=\s*['"]([^'"]+)/) || [])[1];
  if (!csrf) throw new Error('login failed');
}
async function post(url, p) {
  const r = await req(url, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-CSRFToken': csrf, Referer: BASE + '/trexsim/pysim/alpha/' },
    body: new URLSearchParams({ csrfmiddlewaretoken: csrf, ...p }).toString() });
  const t = await r.text();
  try { return JSON.parse(t); } catch { if (/login|sign in/i.test(t)) { await login(); return post(url, p); } return { status: 'bad-response', http: r.status, message: t.slice(0, 200) }; }
}

// ---- what to submit: final list -> id of its COMMENTED Slow run (final run groups SUBN / SUBV / SUBR / SUBX)
const final = JSON.parse(fs.readFileSync(path.join(SUB, 'final.json'), 'utf8')).final;
const runs = {};
for (const j of JSON.parse(fs.readFileSync(path.join(root, 'alphas/validation/queue.json'), 'utf8')))
  if (['SUBN', 'SUBV', 'SUBR', 'SUBX', 'NDX', 'ADD', 'NDY'].includes(j.exp) && j.mode === 'os' && !(runs[j.name] && runs[j.name].status === 'done' && j.status !== 'done')) runs[j.name] = j;
const done = fs.existsSync(DONE_F) ? JSON.parse(fs.readFileSync(DONE_F, 'utf8')) : {};
const record = e => fs.appendFileSync(LOG_F, JSON.stringify({ at: new Date().toISOString(), ...e }) + '\n');

(async () => {
  await login(); log('logged in');
  const info = await post('/trexsim/pysim/alpha/', { post_type: 'get_last_sub_info' });
  log(`account: total_os_allowed=${info.total_os_allowed}, submitted so far=${info.num_alphas_submitted || 0}`);
  const tally = { submitted: 0, already: 0, not_ready: 0, ineligible: 0, failed: 0 }; const problems = [];
  let n = 0;
  for (const name of final) {
    if (ONLY && name !== ONLY) continue;
    if (done[name]) { tally.already++; continue; }
    const j = runs[name];
    if (!j || j.status !== 'done' || !j.id) { tally.not_ready++; if (!DRY) { log('stopping at', name, '(run not finished; order matters)'); break; } continue; }
    if (n >= LIMIT) break;
    const v = await post('/trexsim/pysim/alpha/', { post_type: 'check_submission_validity', alpha_id: String(j.id) });
    if (v.status !== 'success' || v.eligible === false) {
      tally.ineligible++; problems.push(`${name} (${j.id}): ${v.verdict || v.message || v.status} corr ${v.submission_corr} vs ${v.correlated_alpha_id}`);
      record({ name, id: j.id, result: 'ineligible', validity: v }); log('INELIGIBLE', name, j.id, v.verdict || v.message); continue;
    }
    if (DRY) { log('ok (dry-run)', name, j.id, `corr ${v.submission_corr}`); n++; continue; }
    const s = await post('/trexsim/pysim/alphalist/', { alpha_submit_production: 'true', alphaid: String(j.id), alphaname: info.alpha_name || 'alpha',
      alphakw: info.alpha_kw || '', alphades: info.alpha_des || '', authorname: info.authorname || '', username: info.username || '', authoremail: info.authoremail || '' });
    n++;
    if (s.status === 'failed' || s.status === 'bad-response' || !s.alpha_id) {
      tally.failed++; problems.push(`${name} (${j.id}): ${s.message || s.status}`); record({ name, id: j.id, result: 'failed', response: s });
      log('FAILED', name, j.id, s.message || s.status);
      if (/limit|allowed|quota|exceed/i.test(s.message || '')) { log('stopping: submission limit reached'); break; }
    } else {
      tally.submitted++; done[name] = { id: String(j.id), submitted_id: s.alpha_id, at: new Date().toISOString(), corr: v.submission_corr };
      fs.writeFileSync(DONE_F, JSON.stringify(done, null, 1)); record({ name, id: j.id, result: 'submitted', response: s, corr: v.submission_corr });
      log('submitted', name, j.id, `corr ${v.submission_corr}`);
    }
    await sleep(GAP);
  }
  const summary = `${DRY ? 'DRY RUN: ' : ''}submitted ${tally.submitted}, already in ${tally.already}, ineligible ${tally.ineligible}, failed ${tally.failed}, ` +
    `run not finished yet ${tally.not_ready} (of ${final.length})`;
  log(summary); if (problems.length) console.log('problems:\n  ' + problems.join('\n  '));
  if (!DRY && LIMIT > 1) { try { await fetch(NTFY, { method: 'POST', body: summary, headers: { Title: 'trex-alpha: submission run', Tags: problems.length ? 'warning' : 'white_check_mark' } }); } catch {} }
})().catch(e => { console.error(e); process.exit(1); });
