#!/usr/bin/env bash
# Run the composite cycle every hour (ingest -> pool -> screen -> repack). Stop with Ctrl-C
# or by creating alphas/composites/STOP-CYCLE. Extra cycle.py flags can be put in alphas/composites/cycle-args
# (one line, e.g. "--no-repack"); it is re-read every hour, so no service edit/restart is needed.
cd "$(dirname "$0")/../.."
while [ ! -f alphas/composites/STOP-CYCLE ]; do
  EXTRA=$(cat alphas/composites/cycle-args 2>/dev/null)
  python3 scripts/composites/cycle.py $EXTRA "$@" || echo "cycle.py failed (exit $?) — see alphas/composites/cycle.log"
  sleep "${CYCLE_SECONDS:-3600}"
done
