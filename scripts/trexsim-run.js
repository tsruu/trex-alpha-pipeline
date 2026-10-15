#!/usr/bin/env node
// Run legacy or generic-research Fast/Slow OS simulations in a persistent local browser.
// Usage: node scripts/trexsim-run.js <fast|slow|research-fast|research-slow> [ids-csv]

const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const { gitCommit, sha256 } = require('./trexsim-research-state');

const root = path.resolve(__dirname, '..');
const appUrl = 'https://www.trexsim.com/trexsim/pysim/alpha';
const lockFile = path.join(root, '.trexsim-runner.lock');
const profileDirectory = process.env.TREXSIM_BROWSER_PROFILE
  ? path.resolve(process.env.TREXSIM_BROWSER_PROFILE)
  : path.join(root, '.trexsim-browser');

let lockHeld = false;

function fail(message) {
  throw new Error(message);
}

function loadLocalEnvironment() {
  const envFile = path.join(root, '.env');
  if (fs.existsSync(envFile)) process.loadEnvFile(envFile);
}

function acquireLock() {
  try {
    fs.writeFileSync(lockFile, `${JSON.stringify({ pid: process.pid, startedAt: new Date().toISOString() })}\n`, {
      flag: 'wx',
    });
    lockHeld = true;
  } catch (error) {
    if (error.code === 'EEXIST') {
      fail(`Another TrexSim runner owns ${lockFile}. Wait for it to finish before starting another run.`);
    }
    throw error;
  }
}

function releaseLock() {
  if (lockHeld) fs.rmSync(lockFile, { force: true });
  lockHeld = false;
}

function runNode(script, args) {
  try {
    return execFileSync(process.execPath, [path.join(__dirname, script), ...args], {
      cwd: root,
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'inherit'],
    });
  } catch (error) {
    const detail = error.stderr?.toString().trim() || error.message;
    fail(`${script} failed: ${detail}`);
  }
}

function parseArgs() {
  const [mode, numbers] = process.argv.slice(2);
  if (!['fast', 'slow', 'research-fast', 'research-slow'].includes(mode)) {
    fail('Usage: node scripts/trexsim-run.js <fast|slow|research-fast|research-slow> [ids-csv]');
  }
  const research = mode.startsWith('research-');
  const validIds = research
    ? /^[a-z0-9]+(?:-[a-z0-9]+)*(?:,[a-z0-9]+(?:-[a-z0-9]+)*)*$/
    : /^\d+(,\d+)*$/;
  if (numbers && !validIds.test(numbers)) {
    fail(research
      ? 'candidate IDs must be comma-separated lowercase hyphenated strings'
      : 'alpha-numbers-csv must contain comma-separated integers, for example: 6,12,18');
  }
  return { mode, numbers, research };
}

function buildManifest(mode, numbers) {
  const research = mode.startsWith('research-');
  const actualMode = mode.endsWith('fast') ? 'fast' : 'slow';
  const script = research
    ? 'trexsim-research-manifest.js'
    : actualMode === 'fast' ? 'trexsim-build-fast-batch.js' : 'trexsim-build-slow-batch.js';
  const args = research ? [actualMode, ...(numbers ? [numbers] : [])] : (numbers ? [numbers] : []);
  const output = runNode(script, args);
  return JSON.parse(output);
}

function loadPlaywright() {
  try {
    return require('playwright');
  } catch {
    fail('Playwright is not installed. Run `npm install` followed by `npx playwright install chromium`.');
  }
}

function browserLaunchOptions(chromium) {
  const options = {
    headless: process.env.TREXSIM_HEADLESS === '1',
  };
  const defaultExecutable = chromium.executablePath();
  const armExecutable = defaultExecutable.replace('chrome-mac-x64', 'chrome-mac-arm64');
  if (
    !fs.existsSync(defaultExecutable)
    && process.platform === 'darwin'
    && process.arch === 'arm64'
    && fs.existsSync(armExecutable)
  ) {
    options.executablePath = armExecutable;
  }
  return options;
}

async function ensureAuthenticated(page, credentials) {
  await page.goto(appUrl, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(500);

  // TrexSim's login fields may be labeled accessibly or only expose stable DOM IDs.
  const labeledUsername = page.getByLabel('Username', { exact: true });
  const usernameField = await labeledUsername.count() ? labeledUsername : page.locator('#email');
  if (await usernameField.count()) {
    if (!credentials.username || !credentials.password) {
      fail('TrexSim login is required, but trexsim_username or trexsim_password is missing from .env.');
    }

    await usernameField.fill(credentials.username);
    const labeledPassword = page.getByLabel('Password', { exact: true });
    const passwordField = await labeledPassword.count() ? labeledPassword : page.locator('#password');
    await passwordField.fill(credentials.password);
    const acknowledgement = page.getByLabel('I acknowledge and agree.', { exact: true });
    if (!(await acknowledgement.isChecked())) await acknowledgement.click({ force: true });
    await page.getByRole('button', { name: 'Sign in', exact: true }).click();
    await page.waitForFunction(
      () => document.title === 'Trexquant Competition',
      undefined,
      { timeout: 30_000 },
    );
  }

  await page.goto(appUrl, { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => Boolean(window.CSRF_TOKEN), undefined, { timeout: 30_000 });
}

async function runSimulation(page, mode, manifest, tempDirectory) {
  const manifestFile = path.join(tempDirectory, `${mode}-pending.json`);
  fs.writeFileSync(manifestFile, `${JSON.stringify(manifest)}\n`);

  const script = mode.endsWith('fast')
    ? 'trexsim-api-batch.js'
    : 'trexsim-api-slow-batch.js';
  const pool = mode.endsWith('fast')
    ? process.env.TREXSIM_FAST_POOL || '4'
    : process.env.TREXSIM_SLOW_POOL || '1';
  const expression = runNode(script, [manifestFile, pool]);
  return page.evaluate(expression);
}

async function fetchRawResults(page, completedRuns) {
  return page.evaluate(async (runs) => {
    const results = [];
    let index = 0;
    const worker = async () => {
      while (index < runs.length) {
        const run = runs[index++];
        try {
          const response = await fetch(`/trexsim/pysim/alpha/${run.id}/?format=json`);
          if (!response.ok) throw new Error(`HTTP ${response.status}`);
          results.push({ ...run, raw: await response.json() });
        } catch (error) {
          results.push({ ...run, error: String(error) });
        }
      }
    };
    await Promise.all(Array.from({ length: Math.min(3, runs.length) }, worker));
    results.sort((left, right) => String(left.n).localeCompare(String(right.n), undefined, { numeric: true }));
    return results;
  }, completedRuns);
}

function archiveResults(results, tempDirectory, research, batch) {
  const resultsFile = path.join(tempDirectory, 'results.json');
  const payload = research ? { batch, results } : results;
  fs.writeFileSync(resultsFile, `${JSON.stringify(payload)}\n`);
  runNode(research ? 'trexsim-ingest-research-results.js' : 'trexsim-ingest-results.js', [resultsFile]);
}

function summarize(run) {
  const metrics = run.raw?.stats_data?.metrics || {};
  return {
    alpha: run.n,
    id: String(run.raw?.alpha_id || run.id),
    status: run.status,
    url: `https://www.trexsim.com/trexsim/pysim/alpha/${run.raw?.alpha_id || run.id}`,
    ir: metrics.ir ?? null,
    tvr: metrics.tvr ?? null,
    ret: metrics.ret ?? null,
    dd: metrics.dd ?? null,
  };
}

async function main() {
  loadLocalEnvironment();
  const { mode, numbers, research } = parseArgs();
  const manifest = buildManifest(mode, numbers);
  if (!manifest.length) {
    process.stdout.write(`${JSON.stringify({ mode, status: 'no_pending_runs', requested: numbers || 'all', results: [] })}\n`);
    return;
  }

  acquireLock();
  const { chromium } = loadPlaywright();
  const tempDirectory = fs.mkdtempSync(path.join(root, '.trexsim-run-'));
  let context;
  try {
    context = await chromium.launchPersistentContext(profileDirectory, browserLaunchOptions(chromium));
    await require('./submit-gate').expose(context);
    const page = context.pages()[0] || await context.newPage();
    await ensureAuthenticated(page, {
      username: process.env.trexsim_username || process.env.TREXSIM_USERNAME,
      password: process.env.trexsim_password || process.env.TREXSIM_PASSWORD,
    });

    const submitted = await runSimulation(page, mode, manifest, tempDirectory);
    const fetchable = submitted.filter((run) => run.id);
    const unfinishedRuns = submitted.filter((run) => !run.id || run.status !== 'success');
    const unfinished = unfinishedRuns
      .map(({ n, id, status, error }) => ({ alpha: n, id: id || null, status: status || null, error: error || null }));
    const actualMode = mode.endsWith('fast') ? 'fast' : 'slow';
    const batch = {
      manifest_sha256: sha256(JSON.stringify(manifest)),
      mode: actualMode,
      candidate_count: manifest.length,
      created_at: new Date().toISOString(),
      git_commit: gitCommit(root),
    };
    const rawResults = (await fetchRawResults(page, fetchable))
      .map((run) => ({ ...run, requested_mode: actualMode }));
    const failuresWithoutResults = unfinishedRuns.filter((run) => !run.id && run.status !== 'skipped');
    const researchFailures = failuresWithoutResults.map((run) => ({
      ...run,
      requested_mode: actualMode,
      error: run.error || `simulation ended with status ${run.status || 'unknown'}`,
    }));
    archiveResults(research ? [...rawResults, ...researchFailures] : rawResults, tempDirectory, research, batch);

    process.stdout.write(`${JSON.stringify({
      mode,
      status: unfinished.length ? 'partial' : 'complete',
      requested: numbers || 'all',
      ...(research ? { batch } : {}),
      results: rawResults.map(summarize),
      unfinished,
    })}\n`);
  } finally {
    if (context) await context.close();
    fs.rmSync(tempDirectory, { recursive: true, force: true });
    releaseLock();
  }
}

main().catch((error) => {
  releaseLock();
  process.stderr.write(`TrexSim runner failed: ${error.message}\n`);
  process.exitCode = 1;
});
