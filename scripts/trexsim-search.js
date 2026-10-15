#!/usr/bin/env node
// Formula search through the TrexSim Fast API. No LLM in the loop.
//
// Continuous mode (default): each batch mixes
//   ~45% fresh random formulas (families chosen by a bandit rewarding hits in NEW PnL regions),
//   ~25% turnover/robustness variants of hits (smoothing, window steps) to raise IR/sqrt(turnover),
//   ~20% mutations of near-misses that sit in empty regions (<= 0.5 corr to pool and keepers),
//   ~10% composites of 2-3 mutually uncorrelated near-misses.
// Mutation never targets filled regions, so the search spreads out instead of collapsing.
// With --slow-hours A-B it pauses once a night in that local-hour window: triage, the Slow queue,
// the pool rebuild, then resumes with the updated pool.
//
//   node scripts/trexsim-search.js [--hours 1000] [--slow-hours 1-7] [--batch 24] [--pool 4] [--tag run1]
//   node scripts/trexsim-search.js --pilot 300 --tag pilot1      # pure random, stratified
//   node scripts/trexsim-search.js --report           # progress, any time
//   node scripts/trexsim-search.js --analyze [--tag pilot1]   # hit rate + spread report
//   touch alphas/search/STOP                           # stop gracefully after the current batch
//
// Each batch mixes fresh random formulas (families chosen by a UCB bandit on past hit rates),
// mutations of elites and near-misses, and crossovers of elites. Every result is logged.
// A formula is kept when Fast IR >= keep-ir and it is not a near-duplicate of the frontier
// or of an earlier keeper (PnL correlation, with the 1.2x IR/sqrt(turnover) ladder allowed).
// Keepers are written as candidate records (`search-<hash>`) so the existing
// triage -> Slow queue -> optimizer pipeline picks them up. Strong negative results are
// re-run with the sign flipped, so Slow always runs the exact promoted code.

const fs = require('fs');
const path = require('path');
const G = require('./search/grammar');
const { findFutureAccessViolations } = require('./trexsim-expression-safety');

const root = path.resolve(__dirname, '..');
const dir = path.join(root, 'alphas', 'search');
const F = {
  evals: path.join(dir, 'evals.jsonl'), archive: path.join(dir, 'archive.json'), parents: path.join(dir, 'near-misses.json'),
  bandit: path.join(dir, 'bandit.json'), log: path.join(dir, 'log.txt'), status: path.join(dir, 'status.json'),
  board: path.join(dir, 'leaderboard.md'), stop: path.join(dir, 'STOP'), pnl: path.join(dir, 'pnl'),
};
const lockFile = path.join(root, '.trexsim-runner.lock');
const appUrl = 'https://www.trexsim.com/trexsim/pysim/alpha';

const argv = process.argv.slice(2);
const arg = (k, d) => { const i = argv.indexOf(`--${k}`); return i >= 0 ? argv[i + 1] : d; };
const PILOT = Number(arg('pilot', 0));
const CFG = {
  hours: Number(arg('hours', PILOT ? 12 : 1000)), maxEvals: Number(arg('max-evals', PILOT || 1e9)), tag: arg('tag', PILOT ? 'pilot' : 'search'), batch: Number(arg('batch', 24)),
  pool: Number(arg('pool', 4)), seed: Number(arg('seed', Date.now() % 1e9)), keepIr: Number(arg('keep-ir', 0.065)),
  nearIr: 0.03, maxCorr: 0.5, dupCorr: 0.9, ladderUp: 1.3, ladderDown: 0.77, freshShare: Number(arg('fresh', 0.45)),
  crossShare: 0.12, maxSize: 9, maxCompositeSize: 16, variantsPerHit: 12, mutationsPerParent: 20,
  mix: { fresh: 0.50, tvr: 0.20, mut: 0.25, comp: 0.05 }, perRoot: Number(arg('per-root', 16)), slowHours: arg('slow-hours', null), slowDry: argv.includes('--slow-dry'),
  window: ['2020-01-08', '2021-12-30'],
};

fs.mkdirSync(F.pnl, { recursive: true });
const readJson = (f, d) => { try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch { return d; } };
const writeJson = (f, v) => { fs.writeFileSync(`${f}.tmp`, `${JSON.stringify(v, null, 2)}\n`); fs.renameSync(`${f}.tmp`, f); };
const now = () => new Date().toISOString().replace('T', ' ').slice(0, 19);
function log(line) { const s = `[${now()}] ${line}`; fs.appendFileSync(F.log, `${s}\n`); process.stdout.write(`${s}\n`); }

// ---------------------------------------------------------------- report mode
function report() {
  const st = readJson(F.status, null);
  if (!st) { console.log('No search has run yet.'); return; }
  const lines = [
    `state: ${st.state}   running since ${st.run_started_at}   last batch ${st.last_batch_at}`,
    `evals: ${st.evals_total} total, ${st.evals_this_run} this run (${st.rate_per_hour}/h); valid ${st.valid_total}, errors ${st.errors_total}`,
    `hits: |IR|>=${CFG.keepIr} ${st.hits_total}; keepers ${st.keepers} (${st.keepers_this_run} this run); flips pending ${st.flips_pending}`,
    `reject reasons: ${JSON.stringify(st.rejects)}`,
    `best families (novel hits/tries): ${st.top_families.map(f => `${f.family} ${f.hits}/${f.tries}`).join(', ')}`,
    `by origin (tries / |IR|>=0.05 / novel / kept): ${Object.entries(st.origins || {}).map(([k, v]) => `${k} ${v.tries}/${v.hits}/${v.novel}/${v.kept}`).join(', ')}`,
    `slow cycles: ${(st.slow_cycles || []).map(c => `${c.date} ${c.status} pool ${c.pool_before}->${c.pool_after}`).join('; ') || 'none yet'}`,
    `last batch: ${st.last_batch}`,
  ];
  console.log(lines.join('\n'));
  if (fs.existsSync(F.log)) console.log('\nrecent log:\n' + fs.readFileSync(F.log, 'utf8').trim().split('\n').slice(-8).join('\n'));
}
if (argv.includes('--report')) { report(); process.exit(0); }
if (argv.includes('--analyze')) { require('./search/analyze')(root, dir, arg('tag', null)); process.exit(0); }

// ---------------------------------------------------------------- state
const P = G.primitives(root);
const byName = Object.fromEntries(P.map(p => [p.name, p]));
const FAMILIES = [...new Set(P.map(p => p.family))];
const r = G.rng(CFG.seed);
const seen = new Set();
let evalsTotal = 0, validTotal = 0, errorsTotal = 0, hitsTotal = 0;
if (fs.existsSync(F.evals)) {
  for (const line of fs.readFileSync(F.evals, 'utf8').split('\n')) {
    if (!line) continue;
    const e = JSON.parse(line); seen.add(e.hash); evalsTotal++;
    if (e.error) errorsTotal++; else { validTotal++; if (Math.abs(e.ir) >= CFG.keepIr) hitsTotal++; }
  }
}
const archive = readJson(F.archive, []);          // keepers
let near = readJson(F.parents, []);               // near-miss parents
const bandit = readJson(F.bandit, Object.fromEntries(FAMILIES.map(f => [f, { tries: 0, hits: 0 }])));
for (const f of FAMILIES) bandit[f] ||= { tries: 0, hits: 0 };
const flipQueue = [];
const originStats = readJson(path.join(dir, 'origins.json'), {});
let lastSlow = readJson(path.join(dir, 'slow-cycles.json'), []);
let runEvalsGlobal = 0;
const rejects = {};

// ---------------------------------------------------------------- PnL + correlation
const inWindow = d => d >= CFG.window[0] && d <= CFG.window[1];
function readPnl(file) {
  const out = {};
  for (const line of fs.readFileSync(file, 'utf8').split('\n').slice(1)) {
    const [d, , v] = line.split(','); if (d && v !== undefined && v !== '' && inWindow(d)) out[d] = Number(v);
  }
  return out;
}
function corr(a, b) {
  let n = 0, sa = 0, sb = 0, saa = 0, sbb = 0, sab = 0;
  for (const d in a) { const y = b[d]; if (y === undefined) continue; const x = a[d]; n++; sa += x; sb += y; saa += x * x; sbb += y * y; sab += x * y; }
  if (n < 60) return null;
  const va = saa - sa * sa / n, vb = sbb - sb * sb / n;
  return va > 0 && vb > 0 ? (sab - sa * sb / n) / Math.sqrt(va * vb) : null;
}
function loadFrontier() {
  const doc = readJson(path.join(root, 'alphas/factory/master-frontier.json'), {});
  const rows = [...(doc.fixed_already_submitted_prefix || []), ...(doc.legacy_selected_baseline || []), ...(doc.current_live_research_candidates || [])];
  const out = [];
  for (const row of rows) {
    let file = null;
    if (row.source_category === 'legacy') {
      const d = path.join(root, 'alphas/results', row.name || '');
      const slow = readJson(path.join(d, `slow-${row.id}.json`), null);
      if (slow && fs.existsSync(d)) {
        for (const f of fs.readdirSync(d).filter(x => /^fast-.*\.json$/.test(x))) {
          const raw = readJson(path.join(d, f), {});
          if ((raw.expression || '').trim() === (slow.expression || '').trim()) { file = path.join(d, f.replace('.json', '.pnl.csv')); break; }
        }
      }
    } else {
      const rec = readJson(path.join(root, 'alphas/research/candidates', `${row.id}.json`), null);
      const p = rec?.runs?.fast?.result?.archive_pnl_csv;
      if (p) file = path.join(root, p);
    }
    if (file && fs.existsSync(file)) out.push({ id: row.name || row.id, q: Number(row.ir_sqrt_turnover), pnl: readPnl(file) });
  }
  return out;
}
let frontier = loadFrontier();
let frontierMtime = 0;
// Parents built from primitives that were removed from the grammar are dropped.
const treeOk = t => t.t === 'leaf' ? !!byName[t.p] : treeOk(t.a) && (!t.b || treeOk(t.b));
// Rebuild the parent pool from the full eval history: every |IR| >= nearIr result with saved PnL,
// at most 2 per lineage root, so weak-but-novel near-misses are not crowded out by one strong trade.
function rebuildNear() {
  const byRoot = new Map();
  if (!fs.existsSync(F.evals)) return [];
  for (const line of fs.readFileSync(F.evals, 'utf8').split('\n')) {
    if (!line) continue; const e = JSON.parse(line);
    if (e.error || !Number.isFinite(e.ir) || Math.abs(e.ir) < CFG.nearIr || !e.tree || !treeOk(e.tree)) continue;
    if (!fs.existsSync(path.join(dir, 'pnl', `${e.hash}.csv`))) continue;
    const root = e.root || (/^(tvr|mut|flip):/.test(e.origin || '') ? e.origin.split(':')[1] : e.hash);
    const entry = { hash: e.hash, tree: e.tree, sign: e.ir < 0 ? -e.sign : e.sign, ir: Math.abs(e.ir), q: Math.abs(e.q || 0), tvr: e.tvr, origin: e.origin, root };
    const list = byRoot.get(root) || []; list.push(entry); list.sort((a, b) => b.ir - a.ir); byRoot.set(root, list.slice(0, 2));
  }
  return [...byRoot.values()].flat().sort((a, b) => b.ir - a.ir).slice(0, 3000);
}
near = rebuildNear();
// Lineage roots: every variant/mutation inherits its parent's root; a root gets at most perRoot
// follow-ups in total, so one strong trade cannot eat the budget (pilot run: 730 variants of one).
const rootUse = new Map();
const primStats = readJson(path.join(dir, 'primitives.json'), {});
if (fs.existsSync(F.evals)) {
  for (const line of fs.readFileSync(F.evals, 'utf8').split('\n')) {
    if (!line) continue; const e = JSON.parse(line);
    if (e.root && e.root !== e.hash) rootUse.set(e.root, (rootUse.get(e.root) || 0) + 1);
  }
}
const leafNames = (t, o = []) => { if (t.t === 'leaf') o.push(t.p); else { leafNames(t.a, o); if (t.b) leafNames(t.b, o); } return o; };
G.setLeafWeight(name => { const s = primStats[name] || { tries: 0, novel: 0 }; return (s.novel + 1) / (s.tries + 10) * 10 + 0.2; });
const archivePnl = new Map(archive.filter(k => !k.replaced_by).map(k => [k.hash, readPnl(path.join(dir, k.pnl))]));

// ---------------------------------------------------------------- generation
function pickFamily() {
  const total = FAMILIES.reduce((s, f) => s + bandit[f].tries, 0) + 1;
  const score = f => { const b = bandit[f]; return (b.hits + 1) / (b.tries + 2) + Math.sqrt(2 * Math.log(total) / (b.tries + 1)) * 0.15; };
  const ws = FAMILIES.map(score); const sum = ws.reduce((a, b) => a + b, 0);
  let x = r() * sum; for (let i = 0; i < FAMILIES.length; i++) { x -= ws[i]; if (x <= 0) return FAMILIES[i]; }
  return FAMILIES[0];
}
function tournament(list, key) { let best = null; for (let i = 0; i < 3; i++) { const c = G.pick(r, list); if (!best || key(c) > key(best)) best = c; } return best; }
let stratum = 0;
const pnlCache = new Map();
function pnlOf(hash) {
  if (!pnlCache.has(hash)) { const f = path.join(dir, 'pnl', `${hash}.csv`); pnlCache.set(hash, fs.existsSync(f) ? readPnl(f) : null); if (pnlCache.size > 3000) pnlCache.delete(pnlCache.keys().next().value); }
  return pnlCache.get(hash);
}
let regionVersion = 0; // bumps when keepers or the frontier change
function maxCorrToKnown(pnl) {
  let m = -1;
  for (const f of frontier) { const c = corr(pnl, f.pnl); if (c !== null && c > m) m = c; }
  for (const [, kp] of archivePnl) { const c = corr(pnl, kp); if (c !== null && c > m) m = c; }
  return m;
}
function isNovel(entry) {
  if (entry.novelV === regionVersion) return entry.novel;
  const pnl = pnlOf(entry.hash);
  entry.novel = !!pnl && maxCorrToKnown(pnl) <= CFG.maxCorr; entry.novelV = regionVersion;
  return entry.novel;
}
function tournament(list, key) { let best = null; for (let i = 0; i < 3; i++) { const c = G.pick(r, list); if (!best || key(c) > key(best)) best = c; } return best; }
function fresh() { return { tree: G.randomTree(r, P, { family: pickFamily() }), sign: 1, origin: 'fresh' }; }
function proposal() {
  if (PILOT) {
    const family = FAMILIES[stratum++ % FAMILIES.length];
    return { tree: G.randomTree(r, P, { family }), sign: 1, origin: `fresh:${family}` };
  }
  const x = r(), m = CFG.mix;
  if (x < m.fresh) return fresh();
  if (x < m.fresh + m.tvr) {
    const hits = near.filter(n => n.ir >= 0.05 && (n.tvrKids || 0) < CFG.variantsPerHit && (rootUse.get(n.root || n.hash) || 0) < CFG.perRoot);
    if (!hits.length) return fresh();
    const p = tournament(hits, n => n.ir + (n.q || 0));
    p.tvrKids = (p.tvrKids || 0) + 1; const root = p.root || p.hash; rootUse.set(root, (rootUse.get(root) || 0) + 1);
    return { tree: G.tvrVariant(r, p.tree, byName), sign: p.sign, origin: `tvr:${p.hash}`, root };
  }
  const candidates = near.filter(n => (n.kids || 0) < CFG.mutationsPerParent && (rootUse.get(n.root || n.hash) || 0) < CFG.perRoot);
  const pool = []; for (let i = 0; i < 40 && candidates.length; i++) { const c = G.pick(r, candidates); if (isNovel(c)) pool.push(c); }
  if (!pool.length) return fresh();
  if (x < m.fresh + m.tvr + m.mut) {
    const p = tournament(pool, n => n.ir); p.kids = (p.kids || 0) + 1; const root = p.root || p.hash; rootUse.set(root, (rootUse.get(root) || 0) + 1);
    return { tree: G.mutate(r, p.tree, P, byName), sign: p.sign, origin: `mut:${p.hash}`, root };
  }
  const parts = [];
  for (const c of pool.sort((u, v) => v.ir - u.ir)) {
    if (parts.length >= (r() < 0.5 ? 2 : 3)) break;
    const pc = pnlOf(c.hash);
    if (parts.every(q => { const cc = corr(pc, pnlOf(q.hash)); return cc !== null && Math.abs(cc) < 0.3; })) parts.push(c);
  }
  if (parts.length < 2) return fresh();
  return { tree: G.compose(parts), sign: 1, origin: `comp:${parts.map(q => q.hash).join('+')}`, composite: true };
}
function buildBatch() {
  const items = [];
  while (flipQueue.length && items.length < CFG.batch) items.push(flipQueue.shift());
  let guard = 0;
  const want = Math.min(CFG.batch, Math.max(0, CFG.maxEvals - runEvalsGlobal));
  while (items.length < want && guard++ < CFG.batch * 50) {
    const p = proposal();
    if (G.size(p.tree) > (p.composite ? CFG.maxCompositeSize : CFG.maxSize)) continue;
    const hash = G.hashTree(p.tree, p.sign);
    if (seen.has(hash) || items.some(i => i.hash === hash)) continue;
    const code = G.toCode(p.tree, byName, p.sign);
    if (findFutureAccessViolations(code).length) continue;
    items.push({ ...p, hash, code });
  }
  return items;
}

// ---------------------------------------------------------------- browser
function loadEnv() { const f = path.join(root, '.env'); if (fs.existsSync(f)) process.loadEnvFile(f); }
async function openPage(chromium) {
  const profile = process.env.TREXSIM_BROWSER_PROFILE ? path.resolve(process.env.TREXSIM_BROWSER_PROFILE) : path.join(root, '.trexsim-browser');
  const opts = { headless: process.env.TREXSIM_HEADLESS !== '0' };
  const exe = chromium.executablePath(), arm = exe.replace('chrome-mac-x64', 'chrome-mac-arm64');
  if (!fs.existsSync(exe) && process.platform === 'darwin' && fs.existsSync(arm)) opts.executablePath = arm;
  const context = await chromium.launchPersistentContext(profile, opts);
  await require('./submit-gate').expose(context);
  const page = context.pages()[0] || await context.newPage();
  await page.goto(appUrl, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(500);
  const user = page.getByLabel('Username', { exact: true });
  const field = await user.count() ? user : page.locator('#email');
  if (await field.count()) {
    if (!process.env.trexsim_username || !process.env.trexsim_password) throw new Error('Login required but .env credentials are missing');
    await field.fill(process.env.trexsim_username);
    const pw = page.getByLabel('Password', { exact: true });
    await (await pw.count() ? pw : page.locator('#password')).fill(process.env.trexsim_password);
    const ack = page.getByLabel('I acknowledge and agree.', { exact: true });
    if (!(await ack.isChecked())) await ack.click({ force: true });
    await page.getByRole('button', { name: 'Sign in', exact: true }).click();
    await page.waitForFunction(() => document.title === 'Trexquant Competition', undefined, { timeout: 30000 });
    await page.goto(appUrl, { waitUntil: 'domcontentloaded' });
  }
  await page.waitForFunction(() => Boolean(window.CSRF_TOKEN), undefined, { timeout: 30000 });
  return { context, page };
}
async function evaluateBatch(page, items, pool) {
  return page.evaluate(async ({ items, pool }) => {
    const csrf = window.CSRF_TOKEN;
    const post = p => fetch('/trexsim/pysim/alpha/', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-CSRFToken': csrf }, body: new URLSearchParams(p).toString() }).then(r => r.json());
    const sleep = ms => new Promise(r => setTimeout(r, ms));
    let chain = Promise.resolve();
    const slot = () => { let rel; const prev = chain; chain = new Promise(r => { rel = r; }); return prev.then(() => rel); };
    const one = async it => {
      try {
        const rel = await slot();
        let sub;
        try {
          if (window.__trexGateAcquire) await window.__trexGateAcquire();
          try { sub = await post({ csrfmiddlewaretoken: csrf, post_type: 'simulate', action: 'submit', alpha_id: 'none', alpha_expression: it.code, region_universe: 'US:TOP1000', neut: 'industry', delay: '0', mode: 'os_fast', lookback: '300', slippage: 'no', slippage_value: '0.1', liq_uni_sim: 'no' }); }
          finally { if (window.__trexGateRelease) await window.__trexGateRelease(); }
        }
        finally { await sleep(2500); rel(); }
        if (sub.status !== 'success') return { hash: it.hash, error: `submit: ${sub.error || sub.status}` };
        let st, tries = 0;
        do { await sleep(1500); st = await post({ csrfmiddlewaretoken: csrf, post_type: 'get_result', alpha_id: String(sub.alpha_id) }); tries++; } while ((st.status === 'running' || st.status === 'created') && tries < 400);
        const res = await fetch(`/trexsim/pysim/alpha/${sub.alpha_id}/?format=json`).then(r => r.json());
        const m = (res.stats_data && res.stats_data.metrics) || {};
        let rows = [];
        try { const s = typeof res.simresdata === 'string' ? JSON.parse(res.simresdata) : res.simresdata; rows = (s && s[0] && s[0].data) || []; } catch (e) {}
        return { hash: it.hash, id: String(sub.alpha_id), os_limit: !!res.os_limit_exceeded, ir: m.ir, tvr: m.tvr, ir_tvr: m.ir_tvr, ret: m.ret, numstks: m.numstks, pnl: rows.map(x => [x.timestamps, x.dailypnl]) };
      } catch (e) { return { hash: it.hash, error: String(e).slice(0, 200) }; }
    };
    const out = []; let i = 0;
    await Promise.all(Array.from({ length: pool }, async () => { while (i < items.length) { const it = items[i++]; out.push(await one(it)); } }));
    return out;
  }, { items: items.map(({ hash, code }) => ({ hash, code })), pool });
}

// ---------------------------------------------------------------- judging and promotion
const DATA_VARS = new Set(JSON.parse(fs.readFileSync(path.join(root, 'data-distribution.json'), 'utf8')).items.map(x => x.varname));
const clusterOf = fam => fam.startsWith('pv_') ? 'price_volume' : fam.startsWith('id_') ? 'intraday' : fam.startsWith('fund_') ? `fundamental_${fam.slice(5)}` : fam.startsWith('season') ? 'seasonality' : 'macro';
function judge(item, res, pnlByDate, q) {
  for (const f of frontier) {
    const c = corr(pnlByDate, f.pnl);
    if (c !== null && c > CFG.maxCorr) {
      const ratio = f.q > 0 ? q / f.q : 1;
      if (!(ratio >= CFG.ladderUp || ratio <= CFG.ladderDown)) return { ok: false, why: 'frontier-dead', detail: `${f.id} corr ${c.toFixed(2)}` };
    }
  }
  let replace = null;
  for (const k of archive) {
    if (k.replaced_by) continue;
    const c = corr(pnlByDate, archivePnl.get(k.hash) || {});
    if (c === null || c <= CFG.maxCorr) continue;
    const ratio = k.q > 0 ? q / k.q : 1;
    const ladder = (ratio >= CFG.ladderUp || ratio <= CFG.ladderDown) && c < CFG.dupCorr;
    if (ladder) continue;
    if (Number(res.ir) > k.ir && !replace) { replace = k; continue; }
    return { ok: false, why: 'archive-dup', detail: `${k.hash} corr ${c.toFixed(2)}` };
  }
  const maxFrontier = Math.max(-1, ...frontier.map(f => corr(pnlByDate, f.pnl) ?? -1));
  return { ok: true, replace, maxFrontier };
}
function promote(item, res, pnlRows, maxFrontier) {
  const cid = `search-${item.hash}`;
  const resDir = path.join(root, 'alphas/research/results', cid);
  fs.mkdirSync(resDir, { recursive: true });
  const csv = `date,timestamp,dailypnl\n${pnlRows.map(([ts, v]) => `${new Date(ts * 1000).toISOString().slice(0, 10)},${ts},${v}`).join('\n')}\n`;
  const pnlRel = `alphas/research/results/${cid}/fast-${res.id}.pnl.csv`, jsonRel = `alphas/research/results/${cid}/fast-${res.id}.json`;
  fs.writeFileSync(path.join(root, pnlRel), csv);
  fs.writeFileSync(path.join(root, jsonRel), `${JSON.stringify({ alpha_id: res.id, mode: 'os_fast', expression: item.code, stats_data: { metrics: { ir: res.ir, tvr: res.tvr, ir_tvr: res.ir_tvr, ret: res.ret, numstks: res.numstks } } }, null, 2)}\n`);
  const fams = G.families(item.tree, byName);
  const vars = [...new Set((item.code.match(/[a-z_][a-z0-9_]*/g) || []).filter(v => DATA_VARS.has(v)))].sort();
  const req = G.lookback(item.tree, byName) + 1;
  const rec = {
    candidate_id: cid, title: `Search find ${item.hash} (${fams.join(' + ')})`, status: 'fast_promoted', code: item.code,
    inputs: { primary_cluster: clusterOf(fams[0]), primary_variables: vars.length ? vars : ['close'], secondary_clusters: [...new Set(fams.slice(1).map(clusterOf))].filter(c => c !== clusterOf(fams[0])), secondary_variables: [] },
    metadata: { hypothesis: `Evolutionary search find combining ${fams.join(', ')}.`, neutralized: false, mechanism_classification: 'evolutionary search',
      behavioral_axes: { economic_behavior: 'search', information_timing: fams.join('+'), horizon: 'search', conditioning_state: item.tree.t === 'gate' ? item.tree.g : 'none', expected_turnover: Number(res.tvr) < 0.3 ? 'low' : Number(res.tvr) < 1 ? 'medium' : 'high' },
      search: { tree: item.tree, sign: item.sign, origin: item.origin, max_frontier_corr: +maxFrontier.toFixed(3) } },
    lineage: { family_id: cid, root_candidate_id: cid, parent_candidate_id: null, generation: 0, stage: 'manual', changes: { purpose: 'search', origin: item.origin } },
    required_lookback: req, slow_lookback_buffered: req + (req >= 100 ? 10 : 5),
    runs: { fast: { status: 'success', result: { id: res.id, ir: Number(res.ir), turnover: Number(res.tvr), ir_tvr: Number(res.ir_tvr), return: Number(res.ret), mode: 'os_fast', lookback: 300, archive_json: jsonRel, archive_pnl_csv: pnlRel }, error: null }, slow: { status: 'pending', result: null, error: null } },
  };
  fs.writeFileSync(path.join(root, 'alphas/research/candidates', `${cid}.json`), `${JSON.stringify(rec, null, 2)}\n`);
  return cid;
}

function writeStatus(state, runStart, runEvals, keepersRun, lastBatch) {
  const hours = (Date.now() - runStart) / 3.6e6;
  const fams = FAMILIES.map(f => ({ family: f, ...bandit[f], rate: bandit[f].tries ? bandit[f].hits / bandit[f].tries : 0 })).sort((a, b) => b.rate - a.rate);
  const live = archive.filter(k => !k.replaced_by);
  writeJson(F.status, {
    state, run_started_at: new Date(runStart).toISOString(), last_batch_at: new Date().toISOString(), config: CFG,
    evals_total: evalsTotal, evals_this_run: runEvals, rate_per_hour: Math.round(runEvals / Math.max(hours, 1e-3)),
    valid_total: validTotal, errors_total: errorsTotal, hits_total: hitsTotal, keepers: live.length, keepers_this_run: keepersRun,
    flips_pending: flipQueue.length, rejects, top_families: fams.slice(0, 8), origins: originStats, slow_cycles: lastSlow.slice(-3), last_batch: lastBatch,
  });
  const top = [...live].sort((a, b) => b.ir - a.ir);
  const md = [
    `# Search leaderboard — ${now()}`, '',
    `Evals ${evalsTotal} (valid ${validTotal}, errors ${errorsTotal}); hits |IR|>=${CFG.keepIr}: ${hitsTotal}; keepers ${live.length}. State: ${state}.`, '',
    '## Keepers (promoted to alphas/research/candidates as search-<hash>)', '',
    '| # | candidate | Fast IR | tvr | q | max frontier corr | families | found |', '|---|---|---|---|---|---|---|---|',
    ...top.map((k, i) => `| ${i + 1} | \`search-${k.hash}\` | ${k.ir.toFixed(3)} | ${k.tvr.toFixed(2)} | ${k.q.toFixed(3)} | ${k.maxFrontier.toFixed(2)} | ${k.families.join(', ')} | ${k.at} |`),
    '', '## Family hit rates (|IR| >= 0.035)', '', '| family | tries | hits | rate |', '|---|---|---|---|',
    ...fams.map(f => `| ${f.family} | ${f.tries} | ${f.hits} | ${(100 * f.rate).toFixed(1)}% |`), '',
  ];
  fs.writeFileSync(F.board, md.join('\n'));
}

// ---------------------------------------------------------------- main loop
// ---------------------------------------------------------------- nightly Slow cycle
const { spawnSync } = require('child_process');
function inSlowWindow() {
  if (!CFG.slowHours) return false;
  const [a, b] = CFG.slowHours.split('-').map(Number); const h = new Date().getHours();
  return a <= b ? h >= a && h < b : h >= a || h < b;
}
function poolSize() { return (readJson(path.join(root, 'alphas/research/optimal-pool.json'), {}).submission_order || []).length || null; }
function runSlowCycle() {
  const date = new Date().toISOString().slice(0, 10);
  const cycleLog = path.join(dir, 'slow-cycle.log');
  const env = { ...process.env, TREXSIM_HEADLESS: process.env.TREXSIM_HEADLESS || '1' };
  const step = (label, cmd, args, hours = 1) => {
    log(`  slow cycle: ${label}`);
    fs.appendFileSync(cycleLog, `\n[${now()}] $ ${cmd} ${args.join(' ')}\n`);
    if (CFG.slowDry) return true;
    const out = spawnSync(cmd, args, { cwd: root, env, encoding: 'utf8', timeout: hours * 3.6e6, maxBuffer: 1 << 28 });
    fs.appendFileSync(cycleLog, `${out.stdout || ''}${out.stderr || ''}exit ${out.status}\n`);
    if (out.status !== 0) log(`  slow cycle: ${label} exited ${out.status} (see alphas/search/slow-cycle.log)`);
    return out.status === 0;
  };
  const before = poolSize();
  const cycle = { date, started: now(), pool_before: before };
  step('triage', 'python3', ['scripts/trexsim-fast-triage.py']);
  const man = spawnSync(process.execPath, ['scripts/trexsim-research-manifest.js', 'slow'], { cwd: root, encoding: 'utf8' });
  let pending = 0; try { pending = JSON.parse(man.stdout).length; } catch {}
  cycle.slow_runs = pending;
  if (pending) {
    step(`Slow queue (${pending} runs, ~${Math.round(pending * 5 / 6) / 10} h)`, process.execPath, ['scripts/trexsim-run.js', 'research-slow'], 11);
    step('Slow correlation', 'python3', ['scripts/trexsim-correlate-local.py', '--source', 'all', '--mode', 'slow', '--ir-min', '0.07', '--ir-strict', '--start', '2020-01-08', '--end', '2021-12-30', '--output', 'alphas/research/slow-correlation.json']);
    step('pool optimizer', 'python3', ['scripts/trexsim-optimize-pool.py', 'alphas/research/slow-correlation.json', '--output', 'alphas/research/optimal-pool.json']);
    step('campaign sync', process.execPath, ['scripts/trexsim-research-campaign.js', 'sync']);
    step('factory refresh', process.execPath, ['scripts/trexsim-refresh-factory-context.js']);
    step('triage', 'python3', ['scripts/trexsim-fast-triage.py']);
  }
  cycle.pool_after = poolSize(); cycle.finished = now(); cycle.status = CFG.slowDry ? 'dry-run' : 'done';
  lastSlow.push(cycle); writeJson(path.join(dir, 'slow-cycles.json'), lastSlow);
  log(`slow cycle done: ${pending} Slow runs, max pool ${before} -> ${cycle.pool_after}`);
  frontier = loadFrontier(); regionVersion++;
}

function acquireLock() {
  if (fs.existsSync(lockFile)) {
    const l = readJson(lockFile, {});
    let alive = false; try { process.kill(l.pid, 0); alive = true; } catch (e) { alive = e.code === 'EPERM'; }
    if (alive && l.pid !== process.pid) throw new Error(`Another TrexSim runner holds ${lockFile} (pid ${l.pid}). Stop it first.`);
    fs.rmSync(lockFile, { force: true });
  }
  fs.writeFileSync(lockFile, `${JSON.stringify({ pid: process.pid, startedAt: new Date().toISOString(), tool: 'search' })}\n`, { flag: 'wx' });
}

async function main() {
  acquireLock();
  const release = () => fs.rmSync(lockFile, { force: true });
  process.on('SIGINT', () => { log('SIGINT: stopping'); release(); process.exit(130); });
  if (fs.existsSync(F.stop)) fs.rmSync(F.stop);

  loadEnv();
  const { chromium } = require('playwright');
  let { context, page } = await openPage(chromium);
  const runStart = Date.now(); let runEvals = 0, keepersRun = 0, failStreak = 0;
  log(`search start: seed ${CFG.seed}, ${P.length} primitives, frontier ${frontier.length}, archive ${archive.filter(k => !k.replaced_by).length}, evals so far ${evalsTotal}`);
  writeStatus('running', runStart, 0, 0, 'starting');
  try {
    while (true) {
      if (fs.existsSync(F.stop)) { log('STOP file found'); break; }
      if ((Date.now() - runStart) / 3.6e6 >= CFG.hours) { log('time budget reached'); break; }
      if (runEvals >= CFG.maxEvals) { log('eval budget reached'); break; }
      const today = new Date().toISOString().slice(0, 10);
      if (inSlowWindow() && !lastSlow.some(c => c.date === today)) {
        log('entering nightly Slow window: pausing search');
        try { await context.close(); } catch {}
        release();
        try { runSlowCycle(); } catch (e) { log(`slow cycle error: ${e.message}`); }
        acquireLock();
        ({ context, page } = await openPage(chromium));
        log('search resumed');
        continue;
      }
      // No nightly window on the VM: the hourly composite cycle refreshes the pool and master-frontier.json,
      // so reload the frontier whenever that file changes.
      const fm = (() => { try { return fs.statSync(path.join(root, 'alphas/factory/master-frontier.json')).mtimeMs; } catch { return 0; } })();
      if (fm && fm !== frontierMtime) { if (frontierMtime) { frontier = loadFrontier(); regionVersion++; log(`frontier reloaded (${frontier.length})`); } frontierMtime = fm; }
      const items = buildBatch();
      const t0 = Date.now();
      let results;
      try { results = await evaluateBatch(page, items, CFG.pool); failStreak = 0; }
      catch (e) {
        failStreak++; log(`batch failed (${failStreak}): ${String(e.message).slice(0, 200)}; reopening browser`);
        if (failStreak >= 5) throw e;
        try { await context.close(); } catch {}
        ({ context, page } = await openPage(chromium)); continue;
      }
      const byHash = new Map(items.map(i => [i.hash, i]));
      let valid = 0, hits = 0, kept = 0, flips = 0, best = null, osLimit = false, errs = 0;
      for (const res of results) {
        const item = byHash.get(res.hash); seen.add(res.hash); evalsTotal++; runEvals++; runEvalsGlobal++;
        const ir = Number(res.ir);
        const rec = { hash: res.hash, root: item.root || res.hash, tag: CFG.tag, at: new Date().toISOString(), origin: item.origin, sign: item.sign, families: G.families(item.tree, byName), size: G.size(item.tree), id: res.id || null, code: item.code, tree: item.tree };
        if (res.os_limit) osLimit = true;
        if (res.error || !Number.isFinite(ir) || String(res.numstks || '').trim() === '0x0' || !res.pnl?.length) {
          errorsTotal++; errs++; fs.appendFileSync(F.evals, `${JSON.stringify({ ...rec, error: res.error || 'invalid' })}\n`); continue;
        }
        validTotal++; valid++;
        const tvr = Number(res.tvr), q = Number.isFinite(Number(res.ir_tvr)) ? Number(res.ir_tvr) : ir / Math.sqrt(Math.max(tvr, 1e-6));
        let maxFrontierCorr = null, novelHit = false;
        if (Math.abs(ir) >= CFG.nearIr) {
          const sgn = ir < 0 ? -1 : 1, rows = [], signed = {};
          for (const [ts, v] of res.pnl) { const d = new Date(ts * 1000).toISOString().slice(0, 10); if (inWindow(d)) { rows.push(`${d},0,${sgn * Number(v)}`); signed[d] = sgn * Number(v); } }
          fs.writeFileSync(path.join(dir, 'pnl', `${res.hash}.csv`), `date,timestamp,dailypnl\n${rows.join('\n')}\n`);
          maxFrontierCorr = +Math.max(-1, ...frontier.map(f => corr(signed, f.pnl) ?? -1)).toFixed(3);
          novelHit = Math.abs(ir) >= 0.035 && maxCorrToKnown(signed) <= CFG.maxCorr;
        }
        fs.appendFileSync(F.evals, `${JSON.stringify({ ...rec, ir, tvr, q, max_frontier_corr: maxFrontierCorr, novel: novelHit })}\n`);
        // The bandit rewards hits in NEW regions only, so it cannot keep feeding a crowded area.
        for (const f of rec.families) { bandit[f].tries++; if (novelHit) bandit[f].hits++; }
        if (!item.root) for (const pn of new Set(leafNames(item.tree))) { const ps = primStats[pn] ||= { tries: 0, novel: 0 }; ps.tries++; if (novelHit) ps.novel++; }
        const os = originStats[item.origin.split(':')[0]] ||= { tries: 0, hits: 0, novel: 0, kept: 0 };
        os.tries++; if (Math.abs(ir) >= CFG.keepIr) os.hits++; if (novelHit) os.novel++;
        if (!best || Math.abs(ir) > Math.abs(best.ir)) best = { ir, hash: res.hash };
        if (Math.abs(ir) >= CFG.nearIr) { near.push({ hash: res.hash, tree: item.tree, sign: ir < 0 ? -item.sign : item.sign, ir: Math.abs(ir), q: Math.abs(q), tvr, origin: item.origin, root: item.root || res.hash }); }
        if (Math.abs(ir) >= CFG.keepIr) hits++, hitsTotal++;
        if (ir <= -CFG.keepIr && !PILOT) {
          const fh = G.hashTree(item.tree, -item.sign);
          if (!seen.has(fh)) { flipQueue.push({ tree: item.tree, sign: -item.sign, hash: fh, code: G.toCode(item.tree, byName, -item.sign), origin: `flip:${res.hash}`, root: item.root || res.hash }); flips++; }
          continue;
        }
        if (ir < CFG.keepIr) continue;
        const pnlByDate = {}; for (const [ts, v] of res.pnl) { const d = new Date(ts * 1000).toISOString().slice(0, 10); if (inWindow(d)) pnlByDate[d] = Number(v); }
        const verdict = judge(item, res, pnlByDate, q);
        if (!verdict.ok) { rejects[verdict.why] = (rejects[verdict.why] || 0) + 1; log(`  reject ${res.hash} IR ${ir.toFixed(3)}: ${verdict.why} (${verdict.detail})`); continue; }
        const pnlFile = `pnl/${res.hash}.csv`;
        fs.writeFileSync(path.join(dir, pnlFile), `date,timestamp,dailypnl\n${Object.entries(pnlByDate).map(([d, v]) => `${d},0,${v}`).join('\n')}\n`);
        const cid = promote(item, res, res.pnl, verdict.maxFrontier);
        const keeper = { hash: res.hash, candidate_id: cid, tree: item.tree, sign: item.sign, ir, tvr, q, maxFrontier: verdict.maxFrontier, families: rec.families, pnl: pnlFile, at: now() };
        if (verdict.replace) { verdict.replace.replaced_by = res.hash; archivePnl.delete(verdict.replace.hash); log(`  REPLACE ${verdict.replace.hash} -> ${res.hash}`); }
        archive.push(keeper); archivePnl.set(res.hash, pnlByDate); kept++; keepersRun++; regionVersion++; os.kept++;
        log(`  KEEP ${cid} IR ${ir.toFixed(3)} tvr ${tvr.toFixed(2)} q ${q.toFixed(3)} maxFrontierCorr ${verdict.maxFrontier.toFixed(2)} [${rec.families.join(', ')}]`);
      }
      if (near.length > 4000) near = rebuildNear();
      writeJson(F.archive, archive); writeJson(F.parents, near); writeJson(F.bandit, bandit); writeJson(path.join(dir, 'origins.json'), originStats); writeJson(path.join(dir, 'primitives.json'), primStats);
      const secs = ((Date.now() - t0) / 1000).toFixed(0);
      const summary = `batch ${items.length} in ${secs}s | valid ${valid} err ${errs} | |IR|>=${CFG.keepIr}: ${hits} | kept ${kept} | flips ${flips} | best ${best ? best.ir.toFixed(3) : '-'} | total evals ${evalsTotal}, keepers ${archive.filter(k => !k.replaced_by).length}`;
      log(summary);
      writeStatus('running', runStart, runEvals, keepersRun, summary);
      if (osLimit) { log('TrexSim reports os_limit_exceeded; stopping'); break; }
      if (errs === items.length && items.length) { failStreak++; if (failStreak >= 3) { log('three all-error batches in a row; stopping'); break; } }
    }
  } finally {
    writeStatus('stopped', runStart, runEvals, keepersRun, 'stopped');
    log(`search stop: ${runEvals} evals this run, ${keepersRun} keepers this run`);
    try { await context.close(); } catch {}
    release();
  }
}
main().catch(e => { log(`search failed: ${e.message}`); try { const l = readJson(lockFile, {}); if (l.pid === process.pid) fs.rmSync(lockFile, { force: true }); } catch {} process.exitCode = 1; });
