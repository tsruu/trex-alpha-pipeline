#!/usr/bin/env node
const fs = require('fs');
const path = require('path');

const [alphaNum, id, window, ir, tvr, dd, ret, irSqrt, booksize, numStks, liq, liqN, region, note, date, modeArg, lookbackArg, submitArg] = process.argv.slice(2);
if (!alphaNum || !id) {
  console.error('Usage: node trexsim-update-results.js <num> <id> <window> <ir> <tvr> <dd> <ret> <irSqrt> <booksize> <numStks> <liq> <liqN> <region> <note> [date] [fast|slow] [lookback] [submitted]');
  process.exit(1);
}

const nn = String(alphaNum).padStart(2, '0');
const file = path.join(__dirname, '..', 'alphas', `101-alpha-${nn}.md`);
const url = `https://www.trexsim.com/trexsim/pysim/alpha/${id}`;
let content = fs.readFileSync(file, 'utf8');
const runDate = date || new Date().toISOString().slice(0, 10);
const mode = modeArg === 'slow' ? 'Slow OS' : 'Fast OS';
const lookback = lookbackArg || null;
const submit = submitArg === 'submitted' ? 'Submitted' : null;

const indexRow = `| ${mode} | v1 | ${runDate} | ${id} | ${url} |`;
const runBlock = `#### ${runDate} — v1

| | |
|---|---|
| TrexSim ID | ${id} |
| URL | ${url} |
| Mode | ${mode} |
${mode === 'Slow OS' ? `| Lookback | ${lookback} |${submit ? `\n| Submit | ${submit} |` : ''}\n` : ''}| Plots | PNL, Num Stocks, Booksize (on that URL) |
| Window | ${window} |
| IR | ${ir} |
| TVR | ${tvr} |
| DD | ${dd} |
| Ret | ${ret} |
| IR/sqrt(TVR) | ${irSqrt} |
| Booksize | ${booksize} |
| NumStks | ${numStks} |
| Liq | ${liq} |
| LiqN | ${liqN} |
| Region | ${region} |

Note: ${note}`;

if (!content.includes(`| ${mode} | v1 |`)) {
  const header = '| Mode | Version | Date | TrexSim ID | URL |';
  const separator = '|---|---|---|---|---|';
  if (content.includes(`${header}\n${separator}`)) {
    content = content.replace(
      `${header}\n${separator}`,
      `${header}\n${separator}\n${indexRow}`
    );
  } else {
    content = content.replace(header, `${header}\n${indexRow}`);
  }
}
content = content.replace(
  new RegExp(`### ${mode}\\n\\n(?:_None yet\\._|_Not run per request\\._)`),
  `### ${mode}\n\n${runBlock}`
);
fs.writeFileSync(file, content);
console.log(`Updated alpha ${nn}: ID ${id}, IR ${ir}`);
