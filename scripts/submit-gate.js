'use strict';
// Cross-process TrexSim submit gate. TrexSim rejects submissions < 2 s apart per account ("Too rapid
// submission"), and a rejected attempt seems to reset that timer, so independent submitters (the search, the
// nightly Slow runner, scripts/composites/sim-queue-worker.js) knock out each other's submissions.
// Every submitter takes this file lock, waits until GAP ms after the last submit by anyone, submits,
// stamps the time, and releases. Stale locks (>15 s) are broken; the gate never blocks more than ~30 s.
const fs = require('fs');
const path = require('path');
const ROOT = path.resolve(__dirname, '..');
const LOCK = path.join(ROOT, '.trexsim-submit.lock');
const STAMP = path.join(ROOT, '.trexsim-submit.stamp');
const GAP = Number(process.env.TREXSIM_SUBMIT_GAP_MS || 2300);
const sleep = ms => new Promise(r => setTimeout(r, ms));
let held = false;
async function acquire() {
  const t0 = Date.now();
  for (;;) {
    try { fs.writeFileSync(LOCK, `${process.pid} ${Date.now()}`, { flag: 'wx' }); held = true; break; } catch (e) {
      try { if (Date.now() - fs.statSync(LOCK).mtimeMs > 15000) fs.rmSync(LOCK, { force: true }); } catch {}
      if (Date.now() - t0 > 30000) break;
      await sleep(40 + Math.random() * 80);
    }
  }
  let last = 0; try { last = Number(fs.readFileSync(STAMP, 'utf8')) || 0; } catch {}
  const wait = last + GAP - Date.now(); if (wait > 0) await sleep(Math.min(wait, GAP));
  return true;
}
function release() {
  try { fs.writeFileSync(STAMP, String(Date.now())); } catch {}
  if (held) { try { fs.rmSync(LOCK, { force: true }); } catch {} held = false; }
  return true;
}
async function withGate(fn) { await acquire(); try { return await fn(); } finally { release(); } }
// Make the gate callable from browser-side code run with page.evaluate (window.__trexGateAcquire/Release).
async function expose(context) {
  try { await context.exposeFunction('__trexGateAcquire', acquire); await context.exposeFunction('__trexGateRelease', release); }
  catch (e) { /* already exposed */ }
}
module.exports = { acquire, release, withGate, expose, GAP };
