#!/usr/bin/env bash
# Hourly (trex-sync.timer): write ops/status.md, commit everything, rebase on the remote, push.
# The server is the only writer of run data. People and agents push code/docs only.
set -uo pipefail
cd "$(dirname "$0")/.."
mkdir -p ops logs
{
  echo "# Server status — $(date '+%Y-%m-%d %H:%M %Z')"
  echo
  echo '```'
  for s in trex-search trex-worker trex-cycle; do printf '%-12s %s\n' "$s" "$(systemctl is-active $s.service)"; done
  echo
  grep -m1 'Selected maximum pool' alphas/research/optimal-pool.md 2>/dev/null
  echo; echo "-- search (alphas/search/log.txt)"; tail -n 3 alphas/search/log.txt 2>/dev/null
  echo; echo "-- worker (logs/worker.log)"; tail -n 5 logs/worker.log 2>/dev/null
  echo; echo "-- cycle (alphas/composites/cycle.log)"; tail -n 6 alphas/composites/cycle.log 2>/dev/null
  echo; echo "-- machine"; uptime; free -m | head -3; df -h / | tail -1
  echo '```'
} > ops/status.md
git add -A
git commit -q -m "server sync $(date '+%Y-%m-%d %H:%M %Z')" || true
if ! git pull -q --rebase --autostash; then
  git rebase --abort 2>/dev/null
  echo "$(date) sync: rebase conflict, push skipped" >> logs/sync.log; exit 1
fi
git push -q && echo "$(date) sync ok" >> logs/sync.log || { echo "$(date) sync: push failed" >> logs/sync.log; exit 1; }
