#!/usr/bin/env bash
# (Re)install the systemd units from deploy/systemd/ and reload systemd. Safe to re-run after a git pull.
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)"; ME="$(id -un)"
for f in "$DIR"/deploy/systemd/*; do
  sed "s#@USER@#$ME#g; s#@DIR@#$DIR#g" "$f" | sudo tee "/etc/systemd/system/$(basename "$f")" >/dev/null
done
sudo systemctl daemon-reload
echo "units installed; restart the changed services to apply"
