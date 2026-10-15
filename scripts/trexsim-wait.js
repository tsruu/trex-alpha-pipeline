#!/usr/bin/env node
// Block until the running TrexSim batch finishes, polling the runner lock every 30 s inside this
// one process (no agent turns spent). A call returns early only when --max-minutes is reached, so
// the number of agent wake-ups is ceil(remaining time / max-minutes): set it as high as the shell
// tool's timeout allows (e.g. 180 for a whole night in one call).
//
// Usage: node scripts/trexsim-wait.js --mode slow|fast --runs N [--max-minutes M] [--checkpoints]
//   --runs         number of runs in the batch (from the manifest preview)
//   --max-minutes  cap on a single call so it fits your shell tool's timeout (default 60)
// Exit codes: 0 finished, 10 still running (call again), 3 runner died (stale lock),
// 4 no runner detected (launch failed or was killed).

const fs = require('fs');
const path = require('path');

const root = process.env.TREXSIM_ROOT ? path.resolve(process.env.TREXSIM_ROOT) : path.resolve(__dirname, '..');
const lockFile = path.join(root, '.trexsim-runner.lock');
const logDir = path.join(root, 'alphas', 'research', 'logs');
const args = Object.fromEntries(process.argv.slice(2).reduce((pairs, value, index, all) => {
  if (value.startsWith('--')) pairs.push([value.slice(2), all[index + 1]]);
  return pairs;
}, []));
const mode = args.mode === 'fast' ? 'fast' : 'slow';
const runs = Number(args.runs);
const perRunMinutes = Number(args['per-run-minutes'] || (mode === 'slow' ? 5 : 0.25));
const maxMinutes = Number(args['max-minutes'] || 60);
const pollMs = Number(process.env.TREXSIM_WAIT_POLL_MS || 30_000);

function readLock() {
  if (!fs.existsSync(lockFile)) return null;
  try { return JSON.parse(fs.readFileSync(lockFile, 'utf8')); } catch { return { pid: null, startedAt: null }; }
}
function alive(pid) {
  if (!pid) return true;
  try { process.kill(pid, 0); return true; } catch (error) { return error.code === 'EPERM'; }
}
function latestLogTail() {
  if (!fs.existsSync(logDir)) return null;
  const logs = fs.readdirSync(logDir).filter(name => name.endsWith('.log')).sort();
  if (!logs.length) return null;
  const file = path.join(logDir, logs[logs.length - 1]);
  return { file: path.relative(root, file), tail: fs.readFileSync(file, 'utf8').trim().split('\n').slice(-5) };
}
function report(status, extra = {}) {
  process.stdout.write(`${JSON.stringify({ status, mode, ...extra }, null, 2)}\n`);
}

function logFinished(log) {
  // The runner's last stdout line is a JSON summary; an empty or partial log means it never finished.
  if (!log || !log.tail.length) return false;
  try { return typeof JSON.parse(log.tail[log.tail.length - 1]) === 'object'; } catch { return false; }
}

let lock = readLock();
if (!lock) {
  // The runner takes a few seconds to create its lock after launch, so allow a start-up grace
  // period before deciding. A finished run is recognised from its log, never from a missing lock.
  const graceEnd = Date.now() + Number(process.env.TREXSIM_WAIT_GRACE_MS || 120_000);
  while (!lock && Date.now() < graceEnd) {
    const log = latestLogTail();
    if (logFinished(log)) { report('finished', { note: 'Runner finished; see log tail.', log }); process.exit(0); }
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 2000);
    lock = readLock();
  }
  if (!lock) {
    const log = latestLogTail();
    if (logFinished(log)) { report('finished', { note: 'Runner finished; see log tail.', log }); process.exit(0); }
    report('not-running', {
      note: 'No runner lock appeared and the latest log has no final summary. The launch failed or the '
        + 'process was killed when the launching command returned. Relaunch the runner as a foreground '
        + 'command (see the prompt), not with nohup/&.',
      log,
    });
    process.exit(4);
  }
}
if (!alive(lock.pid)) {
  report('stale-lock', { note: `Runner pid ${lock.pid} is gone but ${path.basename(lockFile)} remains. Check the log, then remove the lock.`, log: latestLogTail() });
  process.exit(3);
}

const started = lock.startedAt ? Date.parse(lock.startedAt) : Date.now();
const etaMinutes = Number.isFinite(runs) && runs > 0 ? runs * perRunMinutes : null;
const elapsed = () => (Date.now() - started) / 60000;
function nextCheckpoint() {
  if (!etaMinutes) return elapsed() + Math.min(30, maxMinutes);
  const fractions = [1 / 3, 2 / 3, 1];
  for (let f = 1.25; f < 10; f += 0.25) fractions.push(f);
  const e = elapsed();
  const margin = Math.min(0.5, etaMinutes * 0.05);
  const next = fractions.map(f => f * etaMinutes).find(point => point > e + margin);
  return next ?? e + etaMinutes * 0.25;
}
// --checkpoints returns at 1/3, 2/3 and 100% of the ETA; by default the call waits for completion,
// limited only by --max-minutes (set it to the longest your shell tool allows).
const useCheckpoints = process.argv.includes('--checkpoints');
const deadline = useCheckpoints ? Math.min(nextCheckpoint(), elapsed() + maxMinutes) : elapsed() + maxMinutes;

(function poll() {
  const current = readLock();
  if (!current) {
    report('finished', { elapsed_minutes: Math.round(elapsed()), eta_minutes: etaMinutes, log: latestLogTail() });
    process.exit(0);
  }
  if (!alive(current.pid)) {
    report('stale-lock', { elapsed_minutes: Math.round(elapsed()), log: latestLogTail() });
    process.exit(3);
  }
  if (elapsed() >= deadline) {
    const remaining = etaMinutes ? Math.max(0, Math.round(etaMinutes - elapsed())) : null;
    report('running', {
      elapsed_minutes: Math.round(elapsed()),
      eta_minutes: etaMinutes,
      estimated_remaining_minutes: remaining,
      next_step: 'Call this script again with the same arguments; do not poll any other way.',
    });
    process.exit(10);
  }
  setTimeout(poll, Math.min(pollMs, Math.max(1000, (deadline - elapsed()) * 60000)));
})();
