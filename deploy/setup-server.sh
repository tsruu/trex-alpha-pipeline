#!/usr/bin/env bash
# One-time setup of the TrexSim runner on a fresh Ubuntu 24.04 VM.
# Run from the cloned repo as the VM's admin user:   bash deploy/setup-server.sh
# Installs packages, Node 22, Playwright Chromium, Python deps and 4 GB swap, sets the time zone to
# Asia/Kolkata (the search's 05:00-12:00 Slow window uses local time), and installs the systemd
# services. It enables them for boot but does NOT start them; see deploy/README.md.
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)"
ME="$(id -un)"
echo "== repo $DIR, user $ME"

sudo timedatectl set-timezone Asia/Kolkata

sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y git curl ca-certificates \
  python3 python3-numpy python3-pandas python3-scipy python3-requests

if ! command -v node >/dev/null || [ "$(node -p 'process.versions.node.split(".")[0]')" -lt 22 ]; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
  sudo apt-get install -y nodejs
fi
echo "== node $(node -v), python $(python3 -V)"

cd "$DIR"
npm ci
sudo npx --yes playwright install-deps chromium
npx --yes playwright install chromium

if ! sudo swapon --show | grep -q /swapfile; then
  sudo fallocate -l 4G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
  grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi

# Mac-only state must not survive the move: stale locks and STOP files would block or stop the services.
rm -f .trexsim-runner.lock .trexsim-submit.lock alphas/search/STOP alphas/validation/STOP-WORKER alphas/composites/STOP-CYCLE
rm -rf .trexsim-browser
mkdir -p logs

git config user.name "trex-server"
git config user.email "trex-server@users.noreply.github.com"
git config pull.rebase true

chmod +x deploy/*.sh scripts/composites/cycle-loop.sh
bash deploy/install-units.sh
sudo systemctl enable trex-search.service trex-worker.service trex-cycle.service trex-sync.timer

[ -f .env ] || echo "!! .env is missing: copy it from your Mac before starting (see deploy/README.md)"
echo "== setup done. Next: bash deploy/smoke-test.sh, then start the services (deploy/README.md)."
