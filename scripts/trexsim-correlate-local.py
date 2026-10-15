#!/usr/bin/env python3
"""Compute TrexSim-compatible correlations from legacy and research archives."""

import argparse
import csv
import glob
import json
import math
import os
from pathlib import Path


def numeric_sort(value):
    try:
        return (0, int(value))
    except ValueError:
        return (1, value)


def metric_number(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def ir_sqrt_tvr(metrics):
    stored = metric_number(metrics.get("ir_tvr"))
    if stored is not None:
        return stored
    ir = metric_number(metrics.get("ir"))
    tvr = metric_number(metrics.get("tvr"))
    if ir is None or tvr is None or tvr <= 0:
        return None
    return ir / math.sqrt(tvr)


def matching_csv(json_path, mode, ident):
    path = json_path.parent / f"{mode}-{ident}.pnl.csv"
    if not path.exists():
        raise RuntimeError(f"missing PNL CSV for {json_path}: expected {path}")
    return path


def discover_legacy(root, mode):
    archives = {}
    pattern = os.path.join(root, "101-alpha-*", f"{mode}-*.json")
    for name in glob.glob(pattern):
        json_path = Path(name)
        raw = json.loads(json_path.read_text())
        ident = str(raw.get("alpha_id") or "")
        if not ident:
            continue
        metrics = raw.get("stats_data", {}).get("metrics", {}) or {}
        alpha_number = int(json_path.parent.name.rsplit("-", 1)[-1])
        archives[ident] = {
            "source": "legacy",
            "name": f"101-alpha-{alpha_number:02d}",
            "alpha_number": alpha_number,
            "candidate_id": None,
            "id": ident,
            "ir": metric_number(metrics.get("ir")),
            "tvr": metric_number(metrics.get("tvr")),
            "ir_tvr": ir_sqrt_tvr(metrics),
            "raw": raw,
            "json_path": json_path,
            "csv_path": matching_csv(json_path, mode, ident),
        }
    return archives


def discover_research(root, repo_root, mode):
    archives = {}
    candidate_dir = Path(root) / "candidates"
    if not candidate_dir.exists():
        return archives
    for record_path in sorted(candidate_dir.glob("*.json")):
        record = json.loads(record_path.read_text())
        candidate_id = record.get("candidate_id")
        envelope = record.get("runs", {}).get(mode, {}) or {}
        result = envelope.get("result") or {}
        if envelope.get("status") != "success" or not result.get("id"):
            continue
        ident = str(result["id"])
        json_path = Path(result.get("archive_json") or "")
        csv_path = Path(result.get("archive_pnl_csv") or "")
        if not json_path.is_absolute():
            json_path = repo_root / json_path
        if not csv_path.is_absolute():
            csv_path = repo_root / csv_path
        if not json_path.exists() or not csv_path.exists():
            raise RuntimeError(
                f"{candidate_id}: successful {mode} run references missing archive files"
            )
        raw = json.loads(json_path.read_text())
        metrics = raw.get("stats_data", {}).get("metrics", {}) or {}
        compact_metrics = {
            "ir": result.get("ir", metrics.get("ir")),
            "tvr": result.get("turnover", metrics.get("tvr")),
            "ir_tvr": result.get("ir_tvr", metrics.get("ir_tvr")),
        }
        archives[ident] = {
            "source": "research",
            "name": candidate_id,
            "alpha_number": None,
            "candidate_id": candidate_id,
            "id": ident,
            "ir": metric_number(compact_metrics["ir"]),
            "tvr": metric_number(compact_metrics["tvr"]),
            "ir_tvr": ir_sqrt_tvr(compact_metrics),
            "raw": raw,
            "json_path": json_path,
            "csv_path": csv_path,
        }
    return archives


def discover_archives(source, legacy_root, research_root, repo_root, mode):
    archives = {}
    groups = []
    if source in ("legacy", "all"):
        groups.append(discover_legacy(legacy_root, mode))
    if source in ("research", "all"):
        groups.append(discover_research(research_root, repo_root, mode))
    for group in groups:
        for ident, item in group.items():
            if ident in archives:
                raise RuntimeError(f"duplicate TrexSim ID {ident} across archive sources")
            archives[ident] = item
    return archives


def pearson(xs, ys):
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    denominator = math.sqrt(
        sum((x - mean_x) ** 2 for x in xs)
        * sum((y - mean_y) ** 2 for y in ys)
    )
    if denominator == 0:
        raise RuntimeError("zero-variance PNL series cannot be correlated")
    return numerator / denominator


def load_series(csv_path):
    with csv_path.open(newline="") as csv_file:
        return {
            row["date"]: float(row["dailypnl"])
            for row in csv.DictReader(csv_file)
            if row.get("date") and row.get("dailypnl") not in (None, "")
        }


def main():
    parser = argparse.ArgumentParser(
        description="Compute correlations from legacy and/or research TrexSim PNL archives."
    )
    parser.add_argument("--mode", choices=("fast", "slow"), default="slow")
    parser.add_argument("--source", choices=("legacy", "research", "all"), default="legacy")
    parser.add_argument("--ir-min", type=float)
    parser.add_argument(
        "--ir-strict", action="store_true",
        help="Use IR > --ir-min instead of the default inclusive comparison.",
    )
    parser.add_argument("--ids", help="Comma-separated TrexSim IDs, in report order.")
    parser.add_argument("--start", required=True, help="Inclusive YYYY-MM-DD date.")
    parser.add_argument("--end", required=True, help="Inclusive YYYY-MM-DD date.")
    parser.add_argument("--results-root", default="alphas/results",
                        help="Legacy results root (kept for backwards compatibility).")
    parser.add_argument("--research-root", default="alphas/research")
    parser.add_argument("--output", required=True)
    parser.add_argument("--browser-report-url")
    args = parser.parse_args()

    repo_root = Path.cwd().resolve()
    archives = discover_archives(
        args.source,
        args.results_root,
        args.research_root,
        repo_root,
        args.mode,
    )

    def meets_threshold(item):
        if args.ir_min is None:
            return True
        if item["ir"] is None:
            return False
        return item["ir"] > args.ir_min if args.ir_strict else item["ir"] >= args.ir_min

    if args.ids:
        ids = [ident.strip() for ident in args.ids.split(",") if ident.strip()]
    else:
        if args.ir_min is None:
            parser.error("either --ids or --ir-min is required")
        ids = sorted(
            (ident for ident, item in archives.items() if meets_threshold(item)),
            key=numeric_sort,
        )

    if len(ids) < 2:
        raise RuntimeError("at least two archived IDs are required")

    selected = []
    series = {}
    for ident in ids:
        if ident not in archives:
            raise RuntimeError(
                f"no archived {args.mode} result found for ID {ident} in source={args.source}"
            )
        item = archives[ident]
        if args.ir_min is not None and not meets_threshold(item):
            comparator = ">" if args.ir_strict else ">="
            raise RuntimeError(f"ID {ident} does not meet IR {comparator} {args.ir_min}")
        series[ident] = load_series(item["csv_path"])
        selected.append({
            "source": item["source"],
            "name": item["name"],
            "alpha_number": item["alpha_number"],
            "candidate_id": item["candidate_id"],
            "id": ident,
            "ir": item["ir"],
            "tvr": item["tvr"],
            "ir_tvr": item["ir_tvr"],
            "source_json": str(item["json_path"]),
            "source_pnl_csv": str(item["csv_path"]),
            "raw_time_period": item["raw"].get("stats_data", {}).get("time_period"),
        })

    matrix = []
    observations = []
    for left in ids:
        row = []
        for right in ids:
            dates = sorted(
                date for date in set(series[left]) & set(series[right])
                if args.start <= date <= args.end
            )
            if not dates:
                raise RuntimeError(f"no common dates for {left} and {right}")
            observations.append(len(dates))
            row.append(pearson(
                [series[left][date] for date in dates],
                [series[right][date] for date in dates],
            ))
        matrix.append(row)

    result = {
        "description": "Local TrexSim-compatible correlation matrix from archived PNL.",
        "selection": {
            "mode": f"{args.mode.title()} OS",
            "source": args.source,
            "ir_min": args.ir_min,
            "ir_comparison": ">" if args.ir_strict else ">=",
            "run_count": len(ids),
        },
        "correlation_window": {
            "start": args.start,
            "end": args.end,
            "source": "TrexSim Compute Correlation report",
        },
        "method": "Pearson correlation of aligned daily dailypnl values.",
        "browser_report_url": args.browser_report_url,
        "observation_count": {
            "min": min(observations),
            "max": max(observations),
            "all_equal": len(set(observations)) == 1,
        },
        "alpha_ids": ids,
        "alphas": selected,
        "matrix": matrix,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    matrix_csv = output.with_suffix(".matrix.csv")
    with matrix_csv.open("w", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["id", *ids])
        for ident, row in zip(ids, matrix):
            writer.writerow([ident, *[f"{value:.16g}" for value in row]])

    print(json.dumps({
        "json": str(output),
        "csv": str(matrix_csv),
        "runs": len(ids),
        "sources": sorted({item["source"] for item in selected}),
    }))


if __name__ == "__main__":
    main()
