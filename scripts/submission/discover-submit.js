#!/usr/bin/env node
'use strict';
// One-off: find how TrexSim's "Submit" button talks to the server. Logs in with .env (same as the worker),
// loads one alpha page and its JavaScript, and prints every code snippet that mentions submitting or the
// pool-correlation check. Submits NOTHING. Usage: node scripts/submission/discover-submit.js <alpha id>
const fs = require('fs'), path = require('path');
const root = path.resolve(__dirname, '..', '..'); const BASE = 'https://www.trexsim.com';
const id = process.argv[2] || '433138';
let cookies = {};
const setCookies = res => { for (const c of (res.headers.getSetCookie ? res.headers.getSetCookie() : [])) { const [kv] = c.split(';'); const i = kv.indexOf('='); cookies[kv.slice(0, i).trim()] = kv.slice(i + 1).trim(); } };
const ck = () => Object.entries(cookies).map(([k, v]) => `${k}=${v}`).join('; ');
async function req(url, opts = {}) {
  const res = await fetch(url.startsWith('http') ? url : BASE + url, { redirect: 'manual', ...opts, headers: { 'User-Agent': 'Mozilla/5.0', Cookie: ck(), ...(opts.headers || {}) } });
  setCookies(res);
  if (res.status >= 300 && res.status < 400 && res.headers.get('location')) return req(res.headers.get('location').replace(BASE, ''));
  return res;
}
const env = {}; for (const l of fs.readFileSync(path.join(root, '.env'), 'utf8').split('\n')) { const m = l.match(/^\s*([A-Za-z_]\w*)\s*=\s*(.*)\s*$/); if (m) env[m[1]] = m[2].replace(/^['"]|['"]$/g, ''); }
(async () => {
  let html = await (await req('/trexsim/pysim/?next=/trexsim/pysim/alpha/')).text();
  const tok = (html.match(/name="csrfmiddlewaretoken" value="([^"]+)"/) || [])[1];
  await req('/trexsim/pysim/?next=/trexsim/pysim/alpha/', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded', Referer: BASE + '/trexsim/pysim/' },
    body: new URLSearchParams({ csrfmiddlewaretoken: tok, username: env.trexsim_username, password: env.trexsim_password, agree_terms: 'on' }).toString() });
  html = await (await req(`/trexsim/pysim/alpha/${id}/`)).text();
  const out = [`# alpha page ${id}: ${html.length} bytes`];
  const srcs = [...html.matchAll(/<script[^>]*src="([^"]+)"/g)].map(m => m[1]);
  out.push('# scripts: ' + srcs.join(' '));
  const texts = [['page', html]];
  for (const s of srcs) { try { texts.push([s, await (await req(s.startsWith('http') ? s : (s.startsWith('/') ? s : '/' + s))).text()]); } catch (e) { out.push('# failed ' + s); } }
  const pat = /submi|max_corr|maxCorr|correlat|portfolio|pool/gi; const seen = new Set();
  for (const [name, t] of texts) {
    for (const m of t.matchAll(pat)) {
      const snip = t.slice(Math.max(0, m.index - 220), m.index + 220).replace(/\s+/g, ' ');
      const key = snip.slice(150, 290); if (seen.has(key)) continue; seen.add(key);
      out.push(`--- ${name} @${m.index}\n${snip}`);
      if (seen.size > 120) break;
    }
  }
  const file = path.join(root, 'logs', `discover-submit-${id}.txt`); fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, out.join('\n')); console.log(`wrote ${file} (${out.length} entries); nothing was submitted`);
})().catch(e => { console.error(e); process.exit(1); });
