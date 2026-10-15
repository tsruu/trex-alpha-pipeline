#!/usr/bin/env bash
# Checks the server can run everything before the services start. Submits nothing.
set -uo pipefail
cd "$(dirname "$0")/.."
ok=1
echo "== time zone: $(timedatectl show -p Timezone --value)  local time: $(date)"
python3 -c "import numpy, pandas, scipy, requests; print('python deps ok')" || ok=0
node -e "require('playwright').chromium.launch().then(b => b.close()).then(() => console.log('headless chromium ok'))" || ok=0
[ -f .env ] && echo ".env present" || { echo "!! .env missing"; ok=0; }
# HTTP login through the worker with an empty temporary queue (logs in, finds nothing, exits).
T="$(mktemp -d)"; echo '[]' > "$T/queue.json"
timeout 90 node scripts/composites/sim-queue-worker.js --queue "$T/queue.json" --until-empty 2>&1 | tail -3
rm -rf "$T"
[ "$ok" = 1 ] && echo "== smoke test passed (check that 'logged in' appears above)" || echo "== smoke test FAILED"
