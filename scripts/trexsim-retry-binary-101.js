#!/usr/bin/env node
// One-off: retry the 12 101 alphas which returned an empty Fast book after
// ending in a raw boolean comparison. It changes only those alpha markdown
// files, appending a v2 that turns the final comparison into +/-1 via np.where.
// Usage: node scripts/trexsim-retry-binary-101.js [--dry-run]

const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');

const root = path.resolve(__dirname, '..');
const alphaDirectory = path.join(root, 'alphas');
const resultDirectory = path.join(alphaDirectory, 'results');
const lockFile = path.join(root, '.trexsim-runner.lock');
const profileDirectory = process.env.TREXSIM_BROWSER_PROFILE
  ? path.resolve(process.env.TREXSIM_BROWSER_PROFILE)
  : path.join(root, '.trexsim-browser');
const alphaPage = 'https://www.trexsim.com/trexsim/pysim/alpha';
const targets = [61, 62, 64, 65, 68, 74, 75, 79, 81, 86, 95, 99];
const dryRun = process.argv.slice(2).includes('--dry-run');

function fail(message) {
  throw new Error(message);
}

function loadEnvironment() {
  const envFile = path.join(root, '.env');
  if (fs.existsSync(envFile)) process.loadEnvFile(envFile);
}

function alphaPath(number) {
  return path.join(alphaDirectory, `101-alpha-${String(number).padStart(2, '0')}.md`);
}

function v1Code(content, number) {
  const match = content.match(/### v1\s*\n\n```python\n([\s\S]*?)\n```/);
  if (!match) fail(`Alpha ${number} has no v1 Python block.`);
  return match[1];
}

function rewriteBinaryFinal(code, number) {
  // The target code ends with either `(condition).astype(float)` or
  // `(condition) * -1`. Keep all helper logic and convert only that final
  // comparison to an explicit two-sided float signal.
  const match = code.match(/^alpha\s*=\s*\(([\s\S]+)\)\s*(?:\.astype\(float\)|\*\s*-1)\s*(?:#.*)?$/m);
  if (!match) fail(`Alpha ${number} does not have the expected final binary expression.`);
  const condition = match[1].trim();
  return code.replace(match[0], `alpha = np.where(\n    ${condition},\n    1.0,\n    -1.0,\n)`);
}

function v2Code(content, number) {
  const existing = content.match(/### v2\s*\n\n```python\n([\s\S]*?)\n```/);
  return existing ? existing[1] : rewriteBinaryFinal(v1Code(content, number), number);
}

function appendV2(number, code) {
  const file = alphaPath(number);
  const content = fs.readFileSync(file, 'utf8');
  if (/### v2\s*\n\n```python\n/.test(content)) return false;
  const marker = '\n## Results\n';
  const block = `\n### v2\n\n\`\`\`python\n${code}\n\`\`\`\n\n`;
  if (!content.includes(marker)) fail(`Alpha ${number} has no Results section.`);
  fs.writeFileSync(file, content.replace(marker, `${block}${marker}`));
  return true;
}

function lock() {
  try {
    fs.writeFileSync(lockFile, `${JSON.stringify({ pid: process.pid, startedAt: new Date().toISOString(), task: 'binary-101-v2-retry' })}\n`, { flag: 'wx' });
  } catch (error) {
    if (error.code === 'EEXIST') fail('Another TrexSim runner is active; retry after it finishes.');
    throw error;
  }
}

function unlock() {
  fs.rmSync(lockFile, { force: true });
}

function browserOptions(chromium) {
  const options = { headless: process.env.TREXSIM_HEADLESS === '1' };
  const defaultExecutable = chromium.executablePath();
  const armExecutable = defaultExecutable.replace('chrome-mac-x64', 'chrome-mac-arm64');
  if (!fs.existsSync(defaultExecutable) && process.platform === 'darwin' && process.arch === 'arm64' && fs.existsSync(armExecutable)) {
    options.executablePath = armExecutable;
  }
  return options;
}

async function authenticate(page) {
  await page.goto(alphaPage, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(500);
  const usernameField = await page.getByLabel('Username', { exact: true }).count()
    ? page.getByLabel('Username', { exact: true }) : page.locator('#email');
  if (await usernameField.count()) {
    const username = process.env.trexsim_username || process.env.TREXSIM_USERNAME;
    const password = process.env.trexsim_password || process.env.TREXSIM_PASSWORD;
    if (!username || !password) fail('TrexSim login is required but credentials are missing from .env.');
    await usernameField.fill(username);
    const passwordField = await page.getByLabel('Password', { exact: true }).count()
      ? page.getByLabel('Password', { exact: true }) : page.locator('#password');
    await passwordField.fill(password);
    const acknowledgement = page.getByLabel('I acknowledge and agree.', { exact: true });
    if (!(await acknowledgement.isChecked())) await acknowledgement.click({ force: true });
    await page.getByRole('button', { name: 'Sign in', exact: true }).click();
    await page.waitForFunction(() => document.title === 'Trexquant Competition', undefined, { timeout: 30_000 });
  }
  await page.goto(alphaPage, { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => Boolean(window.CSRF_TOKEN), undefined, { timeout: 30_000 });
}

async function submit(page, manifest) {
  return page.evaluate(async (batch) => {
    const csrf = window.CSRF_TOKEN;
    const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
    const post = params => fetch('/trexsim/pysim/alpha/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-CSRFToken': csrf },
      body: new URLSearchParams(params).toString(),
    }).then(response => response.json());
    const results = [];
    for (const { n, code } of batch) {
      const submitted = await post({
        csrfmiddlewaretoken: csrf, post_type: 'simulate', action: 'submit', alpha_id: 'none',
        alpha_expression: code, region_universe: 'US:TOP1000', neut: 'industry', delay: '0',
        mode: 'os_fast', lookback: '300', slippage: 'no', slippage_value: '0.1', liq_uni_sim: 'no',
      });
      await sleep(3000);
      if (submitted.status !== 'success') {
        results.push({ n, status: submitted.status || 'submit_error', error: submitted });
        continue;
      }
      const id = String(submitted.alpha_id);
      let status;
      for (let attempt = 0; attempt < 80; attempt += 1) {
        await sleep(1500);
        status = await post({ csrfmiddlewaretoken: csrf, post_type: 'get_result', alpha_id: id });
        if (status.status !== 'running') break;
      }
      const response = await fetch(`/trexsim/pysim/alpha/${id}/?format=json`);
      results.push({ n, id, status: status?.status || 'unknown', raw: response.ok ? await response.json() : null, fetch_status: response.status });
    }
    return results;
  }, manifest);
}

function value(input) {
  return input === undefined || input === null || input === '' ? 'n/a' : String(input);
}

function period(value) {
  const match = value?.match(/^(\d{4})(\d{2})(\d{2})-(\d{4})(\d{2})(\d{2})$/);
  return match ? `${match[1]}-${match[2]}-${match[3]} — ${match[4]}-${match[5]}-${match[6]}` : 'n/a';
}

function archiveAndDocument(result) {
  const number = result.n;
  const id = String(result.raw?.alpha_id || result.id);
  if (!result.raw) return { alpha: number, id, status: result.status, error: `result fetch failed (${result.fetch_status})` };
  const directory = path.join(resultDirectory, `101-alpha-${String(number).padStart(2, '0')}`);
  fs.mkdirSync(directory, { recursive: true });
  fs.writeFileSync(path.join(directory, `fast-${id}.json`), `${JSON.stringify(result.raw, null, 2)}\n`);
  let rows = [];
  try {
    const data = typeof result.raw.simresdata === 'string' ? JSON.parse(result.raw.simresdata) : result.raw.simresdata;
    rows = data?.[0]?.data || [];
  } catch {}
  const columns = [...new Set(rows.flatMap(Object.keys))];
  const csv = [
    ['date', 'timestamp', ...columns.filter(column => column !== 'timestamps')],
    ...rows.map(row => [
      row.timestamps ? new Date(row.timestamps * 1000).toISOString().slice(0, 10) : '', row.timestamps ?? '',
      ...columns.filter(column => column !== 'timestamps').map(column => row[column] ?? ''),
    ]),
  ].map(row => row.map(cell => {
    const text = String(cell);
    return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
  }).join(',')).join('\n');
  fs.writeFileSync(path.join(directory, `fast-${id}.pnl.csv`), `${csv}\n`);

  const metrics = result.raw.stats_data?.metrics || {};
  const date = result.raw.simulated_on?.slice(0, 10) || new Date().toISOString().slice(0, 10);
  const empty = !metrics.ir || metrics.numstks === '0x0';
  const note = empty
    ? 'Fast OS v2 returned an empty book (no metrics); raw response is archived for review.'
    : `Fast OS v2 result archived; IR ${metrics.ir} ${Number(metrics.ir) > 0.07 ? 'clears' : 'does not clear'} the 0.07 qualifying bar.`;
  const url = `https://www.trexsim.com/trexsim/pysim/alpha/${id}`;
  const runBlock = `#### ${date} — v2\n\n| | |\n|---|---|\n| TrexSim ID | ${id} |\n| URL | ${url} |\n| Mode | Fast OS |\n| Plots | PNL, Num Stocks, Booksize (on that URL) |\n| Window | ${period(result.raw.stats_data?.time_period)} |\n| IR | ${value(metrics.ir)} |\n| TVR | ${value(metrics.tvr)} |\n| DD | ${value(metrics.dd)} |\n| Ret | ${value(metrics.ret)} |\n| IR/sqrt(TVR) | ${value(metrics.ir_tvr)} |\n| Booksize | ${value(metrics.booksize)} |\n| NumStks | ${value(metrics.numstks)} |\n| Liq | ${value(metrics.liq)} |\n| LiqN | ${value(metrics.liqn)} |\n| Region | ${value(metrics.region)} |\n\nNote: ${note}`;
  const file = alphaPath(number);
  let markdown = fs.readFileSync(file, 'utf8');
  const row = `| Fast OS | v2 | ${date} | ${id} | ${url} |`;
  if (!markdown.includes(`| Fast OS | v2 |`)) markdown = markdown.replace('|---|---|---|---|---|', `|---|---|---|---|---|\n${row}`);
  if (!markdown.includes(`#### ${date} — v2`)) markdown = markdown.replace(/(### Fast OS\n\n[\s\S]*?)(\n### Slow OS)/, `$1\n\n${runBlock}$2`);
  fs.writeFileSync(file, markdown);
  return { alpha: number, id, status: result.status, ir: metrics.ir || null, numstks: metrics.numstks || null, url };
}

async function main() {
  loadEnvironment();
  const manifest = targets.map(number => {
    const content = fs.readFileSync(alphaPath(number), 'utf8');
    return { n: number, code: v2Code(content, number) };
  });
  if (dryRun) {
    process.stdout.write(`${JSON.stringify({ mode: 'dry-run', targets, formulas: manifest.map(item => ({ alpha: item.n, code: item.code })) }, null, 2)}\n`);
    return;
  }
  for (const item of manifest) appendV2(item.n, item.code);
  lock();
  let context;
  try {
    const { chromium } = require('playwright');
    context = await chromium.launchPersistentContext(profileDirectory, browserOptions(chromium));
    const page = context.pages()[0] || await context.newPage();
    await authenticate(page);
    const results = await submit(page, manifest);
    const summary = results.map(archiveAndDocument);
    process.stdout.write(`${JSON.stringify({ mode: 'fast-binary-v2-retry', targets, results: summary }, null, 2)}\n`);
  } finally {
    if (context) await context.close();
    unlock();
  }
}

main().catch(error => {
  unlock();
  process.stderr.write(`Binary 101 v2 retry failed: ${error.message}\n`);
  process.exitCode = 1;
});
