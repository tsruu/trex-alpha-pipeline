#!/bin/bash
# Save simulation error to alpha markdown
set -e
N="$1"
MSG="$2"
DIR="$(cd "$(dirname "$0")/.." && pwd)"
NN=$(printf '%02d' "$N")
FILE="$DIR/alphas/101-alpha-${NN}.md"
node -e "
const fs=require('fs');
const f=process.argv[1];
const msg=process.argv[2];
let c=fs.readFileSync(f,'utf8');
const runBlock=\`#### 2026-09-19 — v1

| | |
|---|---|
| Mode | Fast OS |
| Status | Error |

Note: Simulation error: \${msg}\`;
c=c.replace(/\| Mode \| Version \| Date \| TrexSim ID \| URL \|\n\|---\|---\|---\|---\|---\|\n\| _None yet\._ \|  \|  \|  \|  \|/,
  '| Mode | Version | Date | TrexSim ID | URL |\\n|---|---|---|---|---|\\n| Fast OS | v1 | 2026-09-19 | error | n/a |');
c=c.replace(/### Fast OS\\n\\n_None yet\\./, '### Fast OS\\n\\n'+runBlock);
fs.writeFileSync(f,c);
console.log('Recorded error for alpha', process.argv[3]);
" "$FILE" "$MSG" "$N"
