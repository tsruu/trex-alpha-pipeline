#!/usr/bin/env bash
# Quick live look at the running setup:  bash deploy/status.sh
cd "$(dirname "$0")/.."
for s in trex-search trex-worker trex-cycle; do printf '%-12s %s\n' "$s" "$(systemctl is-active $s.service)"; done
systemctl list-timers trex-sync.timer --no-pager | sed -n 2p
grep -m1 'Selected maximum pool' alphas/research/optimal-pool.md
echo "-- search";  tail -n 3 alphas/search/log.txt
echo "-- worker";  tail -n 5 logs/worker.log
echo "-- cycle";   tail -n 6 alphas/composites/cycle.log
echo "-- sync";    tail -n 2 logs/sync.log 2>/dev/null
echo "-- machine"; uptime; free -m | sed -n 2,3p; df -h / | tail -1
