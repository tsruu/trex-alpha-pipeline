# Running the TrexSim setup on the Azure VM

The VM runs three services and one timer. The VM is the only machine that runs them, and the only
writer of run data. Everyone else (the Mac, Claude, Codex) pulls from GitHub, and pushes code or
docs only.

| Unit | What it runs | Log |
|---|---|---|
| `trex-search` | `scripts/trexsim-search.js --tag run1` (Fast only, around the clock) | `alphas/search/log.txt`, `logs/search.out` |
| `trex-worker` | `scripts/composites/sim-queue-worker.js --slow 6 --fast 2`: composites (first), search keepers, mined components | `logs/worker.log` |
| `trex-cycle` | `scripts/composites/cycle-loop.sh` hourly: ingest results, pool + frontier refresh, keeper triage, repack, mining | `alphas/composites/cycle.log`, `logs/cycle.out` |
| `trex-sync.timer` | `deploy/sync.sh` hourly: writes `ops/status.md`, commits, pushes | `logs/sync.log` |

There is no nightly window: the search never pauses, and its keepers are Slow-run by the worker as they appear.
After changing anything in `deploy/systemd/`, run `bash deploy/install-units.sh` and restart the affected service.

## Everyday commands (on the VM, inside the repo)

    bash deploy/status.sh                          # services, pool size, log tails, memory, disk
    sudo systemctl restart trex-search             # pick up code changes (after git pull)
    sudo systemctl restart trex-worker trex-cycle
    journalctl -u trex-search -n 50                # service-level errors
    sudo systemctl start trex-sync                 # push right now instead of waiting for the hour

Stopping gracefully (these do not restart until you start them again):

    touch alphas/search/STOP                       # search stops after its current batch
    touch alphas/validation/STOP-WORKER            # worker stops within ~10 s; submitted jobs resume later
    touch alphas/composites/STOP-CYCLE             # cycle loop stops at its next wake-up
    # then remove STOP-WORKER / STOP-CYCLE before `sudo systemctl start ...` (the search removes its own)

Everything, immediately: `sudo systemctl stop trex-search trex-worker trex-cycle`.

## Changing code

Push code from the Mac (or anywhere), then on the VM: `git pull` and restart the affected service.
Running processes do not reload code on their own. Do not push changes to run-data files
(`alphas/**`) from anywhere but the VM, or the hourly rebase will conflict (sync then logs the
conflict and skips the push until it is resolved).

## Pausing or ending

- Pause billing for compute: `az vm deallocate -g trex-rg -n trex-vm` (disk is kept; ~$5/month).
  Resume: `az vm start -g trex-rg -n trex-vm` (the services start on boot; the public IP stays).
- Delete everything when the competition is over: `az group delete -n trex-rg`.
