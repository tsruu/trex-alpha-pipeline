#!/usr/bin/env node
// Emit a CDP Runtime.evaluate expression that runs a pool of Fast OS sims via the TrexSim HTTP API.
// Usage: node trexsim-api-batch.js <batch.json> <pool> [nums-csv]
//   batch.json: [{n, code}]
//   pool: concurrency
//   nums-csv: optional subset of alpha numbers to include (else all in batch.json)
const fs = require('fs');
const [, , batchFile, poolArg, numsCsv] = process.argv;
let batch = JSON.parse(fs.readFileSync(batchFile, 'utf8'));
if (numsCsv) {
  const want = new Set(numsCsv.split(',').map(s => parseInt(s, 10)));
  batch = batch.filter(b => want.has(b.n));
}
const pool = parseInt(poolArg || '4', 10);
const errorLimit = Math.max(1, parseInt(process.env.TREXSIM_FAST_ERROR_LIMIT || '5', 10));
const expr = `new Promise(async resolve => {
  const batch = ${JSON.stringify(batch)};
  window.__trexBatchState = {status:'running', startedAt:Date.now(), results:null};
  const csrf = window.CSRF_TOKEN;
  const post = (p) => fetch('/trexsim/pysim/alpha/', {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded','X-CSRFToken':csrf}, body:new URLSearchParams(p).toString()}).then(r=>r.json());
  let submitQueue = Promise.resolve();
  let nextSubmitAt = 0;
  let consecutiveFailures = 0;
  let circuitOpen = false;
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const waitForSubmitSlot = async () => {
    let release;
    const previous = submitQueue;
    submitQueue = new Promise(r => { release = r; });
    await previous;
    const wait = Math.max(0, nextSubmitAt - Date.now());
    if (wait) await sleep(wait);
    nextSubmitAt = Date.now();
    return release;
  };
  const runOne = async ({n, code, settings}) => {
    const cfg = Object.assign({region_universe:'US:TOP1000', neut:'industry', delay:'0'}, settings || {});
    const t0 = Date.now();
    let release;
    try {
      release = await waitForSubmitSlot();
      if (window.__trexGateAcquire) await window.__trexGateAcquire();
      let sub; try { sub = await post({csrfmiddlewaretoken:csrf, post_type:'simulate', action:'submit', alpha_id:'none', alpha_expression:code, region_universe:cfg.region_universe, neut:cfg.neut, delay:String(cfg.delay), mode:'os_fast', lookback:'300', slippage:'no', slippage_value:'0.1', liq_uni_sim:'no'}); } finally { if (window.__trexGateRelease) await window.__trexGateRelease(); }
      await sleep(3000);
      release();
      if (sub.status !== 'success') return {n, error:'submit', sub};
      const id = sub.alpha_id;
      let st, tries=0;
      do { await new Promise(r=>setTimeout(r,1500)); st = await post({csrfmiddlewaretoken:csrf, post_type:'get_result', alpha_id:String(id)}); tries++; } while ((st.status==='running' || st.status==='created') && tries<400);
      const res = await fetch('/trexsim/pysim/alpha/'+id+'/?format=json').then(r=>r.json());
      const m = (res.stats_data && res.stats_data.metrics) || {};
      const invalidReason = res.os_limit_exceeded
        ? 'os_limit_exceeded'
        : m.ir === undefined || m.ir === null || m.ir === '' || !Number.isFinite(Number(m.ir))
          ? 'blank_or_non_numeric_ir'
          : String(m.numstks || '').trim().toLowerCase() === '0x0' ? 'empty_0x0_book' : null;
      return {n, id, status:invalidReason ? 'invalid' : st.status, invalid_reason:invalidReason, secs:((Date.now()-t0)/1000).toFixed(1), period:(res.stats_data && res.stats_data.time_period)||null, os_limit_exceeded:res.os_limit_exceeded, ir:m.ir, tvr:m.tvr, dd:m.dd, ret:m.ret, ir_tvr:m.ir_tvr, booksize:m.booksize, numstks:m.numstks, liq:m.liq, liqn:m.liqn, region:m.region};
    } catch(e){ if (release) release(); return {n, error:String(e), secs:((Date.now()-t0)/1000).toFixed(1)}; }
  };
  const POOL = ${pool};
  const ERROR_LIMIT = ${errorLimit};
  const results = []; let i = 0;
  const worker = async () => {
    while (i < batch.length) {
      const item = batch[i++];
      if (circuitOpen) {
        results.push({n:item.n, status:'skipped', error:'fast_error_circuit_open'});
        continue;
      }
      const result = await runOne(item);
      results.push(result);
      if (result.status === 'success' && !result.error && !result.invalid_reason) consecutiveFailures = 0;
      else consecutiveFailures += 1;
      if (consecutiveFailures >= ERROR_LIMIT) circuitOpen = true;
    }
  };
  await Promise.all(Array.from({length:POOL}, worker));
  results.sort((a,b)=>String(a.n).localeCompare(String(b.n), undefined, {numeric:true}));
  window.__trexBatchState = {status:'done', finishedAt:Date.now(), results};
  resolve(results);
})`;
process.stdout.write(expr);
