#!/usr/bin/env python3
"""Gate-check a single alpha against the qualified pool.

Answers the one question the research loop asks each iteration: does this
candidate clear the competition gate against the alphas already in the pool?

Rules (from the competition spec):
  1. Qualify:  slow IR must be >= --ir-min (default 0.07).
  2. Correlation: <= --corr-max (default 0.50) to every pool member, OR,
     where it exceeds that, its IR/sqrt(TVR) must be at least
     (1 + --override) x the correlated member's IR/sqrt(TVR).

Reuses the exact math verified in trexsim-correlate-local.py: Pearson on
aligned daily `dailypnl`, dates intersected and clipped to the window.

Usage:
  python3 scripts/trexsim-gate.py <alpha-number-or-slow-id> [options]

Examples:
  python3 scripts/trexsim-gate.py 94
  python3 scripts/trexsim-gate.py 321991 --pool-ids 317051,320045,321410

Prints one JSON verdict object to stdout; a one-line human summary to stderr.
Exit code 0 = PASS, 2 = FAIL, 1 = usage/data error.
"""

import argparse
import csv
import glob
import json
import math
import os
import sys
from pathlib import Path


def pearson(xs, ys):
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    denominator = math.sqrt(
        sum((x - mean_x) ** 2 for x in xs) * sum((y - mean_y) ** 2 for y in ys)
    )
    if denominator == 0:
        raise RuntimeError("zero variance in a PNL series; cannot correlate")
    return numerator / denominator


def load_series(csv_path):
    with open(csv_path, newline="") as fh:
        return {
            row["date"]: float(row["dailypnl"])
            for row in csv.DictReader(fh)
            if row.get("date") and row.get("dailypnl") not in (None, "")
        }


def ir_sqrt_tvr(metrics):
    """IR/sqrt(TVR): prefer the archived ir_tvr, else derive from ir and tvr."""
    val = metrics.get("ir_tvr")
    if val not in (None, ""):
        try:
            return float(val)
        except ValueError:
            pass
    ir, tvr = metrics.get("ir"), metrics.get("tvr")
    if ir in (None, "") or tvr in (None, ""):
        return None
    tvr = float(tvr)
    if tvr <= 0:
        return None
    return float(ir) / math.sqrt(tvr)


def discover(results_root, prefix="slow-"):
    """Map TrexSim id -> archive metadata for every slow result on disk."""
    archives = {}
    for path in glob.glob(os.path.join(results_root, "101-alpha-*", f"{prefix}*.json")):
        raw = json.load(open(path))
        ident = str(raw.get("alpha_id") or "")
        if not ident:
            continue
        metrics = raw.get("stats_data", {}).get("metrics", {}) or {}
        folder = os.path.dirname(path)
        csvs = glob.glob(os.path.join(folder, f"{prefix}{ident}.pnl.csv"))
        if not csvs:
            continue
        archives[ident] = {
            "alpha_number": int(Path(folder).name.rsplit("-", 1)[-1]),
            "csv_path": csvs[0],
            "ir": float(metrics["ir"]) if metrics.get("ir") not in (None, "") else None,
            "ir_tvr": ir_sqrt_tvr(metrics),
        }
    return archives


def resolve_candidate(token, archives, results_root):
    """Accept an alpha number (2-digit folder) or a slow TrexSim id."""
    if token in archives:
        return token
    if token.isdigit() and len(token) <= 3:  # looks like an alpha number
        folder = os.path.join(results_root, f"101-alpha-{int(token):02d}")
        ids = [
            i for i, a in archives.items()
            if a["alpha_number"] == int(token)
        ]
        if ids:
            return max(ids, key=int)  # newest run for that alpha
    raise RuntimeError(
        f"'{token}' is not an archived slow id or an alpha with a slow result"
    )


def corr_in_window(a, b, series, start, end):
    dates = sorted(
        d for d in (set(series[a]) & set(series[b])) if start <= d <= end
    )
    if not dates:
        raise RuntimeError(f"no common dates in window for {a} and {b}")
    return (
        pearson([series[a][d] for d in dates], [series[b][d] for d in dates]),
        len(dates),
    )


def main():
    p = argparse.ArgumentParser(description="Gate-check one alpha against the pool.")
    p.add_argument("candidate", help="Alpha number (e.g. 94) or slow TrexSim id.")
    p.add_argument("--start", default="2020-01-08", help="Inclusive YYYY-MM-DD.")
    p.add_argument("--end", default="2021-12-30", help="Inclusive YYYY-MM-DD.")
    p.add_argument("--ir-min", type=float, default=0.07)
    p.add_argument("--corr-max", type=float, default=0.50)
    p.add_argument("--override", type=float, default=0.20,
                   help="Required fractional IR/sqrt(TVR) edge over a >corr-max member.")
    p.add_argument("--pool-ids", help="Comma-separated slow ids to use as the pool. "
                   "Default: every slow archive with IR >= --ir-min.")
    p.add_argument("--results-root", default="alphas/results")
    args = p.parse_args()

    archives = discover(args.results_root)
    if not archives:
        print("no slow archives found under " + args.results_root, file=sys.stderr)
        return 1

    try:
        cand = resolve_candidate(args.candidate.strip(), archives, args.results_root)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1
    c = archives[cand]

    # Build the pool.
    if args.pool_ids:
        pool = [i.strip() for i in args.pool_ids.split(",") if i.strip() and i.strip() != cand]
        missing = [i for i in pool if i not in archives]
        if missing:
            print("pool ids with no slow archive: " + ",".join(missing), file=sys.stderr)
            return 1
    else:
        pool = sorted(
            (i for i, a in archives.items()
             if i != cand and a["ir"] is not None and a["ir"] >= args.ir_min),
            key=int,
        )

    # Load only the series we need.
    need = [cand] + pool
    series = {i: load_series(archives[i]["csv_path"]) for i in need}

    ir_ok = c["ir"] is not None and c["ir"] >= args.ir_min

    collisions = []      # members over corr-max that the candidate does NOT beat
    overridden = []      # members over corr-max that the candidate DOES beat
    max_corr, max_corr_id = -2.0, None
    for m in pool:
        corr, n = corr_in_window(cand, m, series, args.start, args.end)
        if corr > max_corr:
            max_corr, max_corr_id = corr, m
        if corr > args.corr_max:
            edge_ok = (
                c["ir_tvr"] is not None
                and archives[m]["ir_tvr"] is not None
                and c["ir_tvr"] >= (1 + args.override) * archives[m]["ir_tvr"]
            )
            rec = {
                "id": m,
                "alpha_number": archives[m]["alpha_number"],
                "corr": round(corr, 4),
                "n_days": n,
                "cand_ir_tvr": None if c["ir_tvr"] is None else round(c["ir_tvr"], 4),
                "member_ir_tvr": None if archives[m]["ir_tvr"] is None else round(archives[m]["ir_tvr"], 4),
                "required_ir_tvr": None if archives[m]["ir_tvr"] is None else round((1 + args.override) * archives[m]["ir_tvr"], 4),
            }
            (overridden if edge_ok else collisions).append(rec)

    corr_ok = len(collisions) == 0
    verdict = "PASS" if (ir_ok and corr_ok) else "FAIL"

    out = {
        "verdict": verdict,
        "candidate": {
            "id": cand,
            "alpha_number": c["alpha_number"],
            "ir": c["ir"],
            "ir_tvr": None if c["ir_tvr"] is None else round(c["ir_tvr"], 4),
        },
        "ir_ok": ir_ok,
        "corr_ok": corr_ok,
        "max_corr": round(max_corr, 4),
        "max_corr_id": max_corr_id,
        "pool_size": len(pool),
        "window": {"start": args.start, "end": args.end},
        "thresholds": {"ir_min": args.ir_min, "corr_max": args.corr_max, "override": args.override},
        "blocking_collisions": collisions,
        "cleared_by_override": overridden,
    }
    print(json.dumps(out, indent=2))

    # Human one-liner to stderr.
    if verdict == "PASS":
        note = "clears" if not overridden else f"clears ({len(overridden)} via IR/sqrt(TVR) override)"
        msg = f"PASS alpha {c['alpha_number']} (id {cand}): IR {c['ir']}, max corr {max_corr:.3f} -> {note}"
    elif not ir_ok:
        msg = f"FAIL alpha {c['alpha_number']} (id {cand}): IR {c['ir']} < {args.ir_min}"
    else:
        worst = max(collisions, key=lambda r: r["corr"])
        msg = (f"FAIL alpha {c['alpha_number']} (id {cand}): {worst['corr']:.3f} with "
               f"alpha {worst['alpha_number']} (id {worst['id']}); "
               f"IR/sqrt(TVR) {worst['cand_ir_tvr']} < {worst['required_ir_tvr']} needed")
    print(msg, file=sys.stderr)
    return 0 if verdict == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
