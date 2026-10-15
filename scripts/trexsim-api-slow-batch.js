#!/usr/bin/env node
// Emit a CDP Runtime.evaluate expression for Slow OS runs via the authenticated TrexSim tab.
// Usage: node trexsim-api-slow-batch.js <batch.json> [pool]
//   batch.json: [{n, fast_id, lookback}]
//   pool: overlapping Slow simulations; defaults to 1 because Slow runs are expensive.
const fs = require('fs');

const [, , batchFile, poolArg] = process.argv;
const batch = JSON.parse(fs.readFileSync(batchFile, 'utf8'));
const pool = parseInt(poolArg || '1', 10);

const expr = `new Promise(async resolve => {
  const batch = ${JSON.stringify(batch)};
  window.__trexSlowBatchState = {status:'running', startedAt:Date.now(), results:null};
  const csrf = window.CSRF_TOKEN;
  const post = (params) => fetch('/trexsim/pysim/alpha/', {
    method:'POST',
    headers:{'Content-Type':'application/x-www-form-urlencoded'},
    body:new URLSearchParams({csrfmiddlewaretoken:csrf, ...params}).toString()
  }).then(r => r.json());
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  let submitQueue = Promise.resolve();
  const waitForSubmitSlot = async () => {
    let release;
    const previous = submitQueue;
    submitQueue = new Promise(r => { release = r; });
    await previous;
    return release;
  };
  const runOne = async ({n, fast_id, lookback}) => {
    const t0 = Date.now();
    let release;
    try {
      const fast = await fetch('/trexsim/pysim/alpha/' + fast_id + '/?format=json').then(r => r.json());
      release = await waitForSubmitSlot();
      if (window.__trexGateAcquire) await window.__trexGateAcquire();
      let sub;
      try {
        sub = await post({
        post_type:'simulate',
        action:'submit',
        alpha_id:String(fast_id),
        alpha_expression:fast.expression,
        region_universe:fast.region_universe,
        neut:fast.neut,
        delay:fast.delay,
        mode:'os',
        lookback:String(lookback),
        slippage:fast.slippage ? 'yes' : 'no',
        slippage_value:String(fast.slippage_value ?? '0.1'),
        liq_uni_sim:fast.liq_uni_sim ? 'yes' : 'no'
      });
      } finally { if (window.__trexGateRelease) await window.__trexGateRelease(); }
      await sleep(3000);
      release();
      release = null;
      if (sub.status !== 'success') return {n, fast_id, lookback, error:'submit', sub};

      const id = String(sub.alpha_id);
      let status;
      let tries = 0;
      do {
        await sleep(5000);
        status = await post({post_type:'get_result', alpha_id:id});
        tries++;
      } while ((status.status === 'created' || status.status === 'running') && tries < 720);

      let result;
      if (status.status === 'success') {
        result = await fetch('/trexsim/pysim/alpha/' + id + '/?format=json').then(r => r.json());
      }
      const metrics = result?.stats_data?.metrics || {};
      return {
        n, fast_id, lookback, id, status:status.status,
        secs:((Date.now()-t0)/1000).toFixed(1),
        period:result?.stats_data?.time_period || null,
        os_limit_exceeded:result?.os_limit_exceeded,
        ir:metrics.ir, tvr:metrics.tvr, dd:metrics.dd, ret:metrics.ret,
        ir_tvr:metrics.ir_tvr, booksize:metrics.booksize, numstks:metrics.numstks,
        liq:metrics.liq, liqn:metrics.liqn, region:metrics.region
      };
    } catch (error) {
      if (release) release();
      return {n, fast_id, lookback, error:String(error), secs:((Date.now()-t0)/1000).toFixed(1)};
    }
  };
  const results = [];
  let index = 0;
  const worker = async () => {
    while (index < batch.length) results.push(await runOne(batch[index++]));
  };
  await Promise.all(Array.from({length:${pool}}, worker));
  results.sort((a,b) => String(a.n).localeCompare(String(b.n), undefined, {numeric:true}));
  window.__trexSlowBatchState = {status:'done', finishedAt:Date.now(), results};
  resolve(results);
})`;

process.stdout.write(expr);
