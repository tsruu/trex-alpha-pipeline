#!/usr/bin/env python3
"""Build the compact Markdown catalog described by BUILD_DATA_MAP.md."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
THEMES = (
    "cash",
    "earnings",
    "net_income",
    "expenses",
    "sales",
    "equity",
    "debt",
    "assets",
    "year",
)
CLUSTER_ORDER = (
    "price_volume",
    "intraday",
    "fundamental_cash",
    "fundamental_earnings",
    "fundamental_net_income",
    "fundamental_expenses",
    "fundamental_sales",
    "fundamental_equity",
    "fundamental_debt",
    "fundamental_assets",
    "fundamental_year",
    "seasonality",
    "macro",
)
MACRO_GROUPS = {
    "GROUP_fred",
    "GROUP_daily_idx",
    "GROUP_daily_idx_derived",
    "GROUP_daily_etf_returns",
}
TECHNICAL_PRICE_GROUPS = {
    "GROUP_backoffice",
    "GROUP_backoffice_derived",
}
COVERED = {
    "open",
    "high",
    "low",
    "close",
    "volume",
    "mktcap",
    "industry",
    "sector",
    "subindustry",
    "ret1",
    "ret5",
    "ret10",
    "ret20",
}
OPTIONAL_COVERED = {"adv", "vwap"}
SPARSE_COVERAGE_THRESHOLD = 500

CLUSTER_DETAILS = {
    "price_volume": (
        "Price / Volume",
        "EXPLORED — all 101 alphas live here.",
        "Use mainly to combine with another cluster, or as the base signal you transform "
        "(neutralize / condition / re-weight / re-horizon). Low lookahead risk.",
    ),
    "intraday": (
        "Intraday",
        "Open — 101 never use intraday timing.",
        "First/last-hour fields; close cousin of price/volume, easy to reason about; "
        "low lookahead risk.",
    ),
    "seasonality": (
        "Seasonality",
        "Open.",
        "Calendar effects (options-expiry, month/quarter ends, FOMC/earnings proximity); "
        "low turnover; best as a conditioner/gate on another signal.",
    ),
    "macro": (
        "Macro / Index",
        "Open — all market-wide (must interact).",
        "Every series is market-wide (1D) — cannot rank stocks alone; interact with a "
        "stock-level variable or use to tilt/condition; includes SPX/VIX/GLD. FRED macro "
        "observations are forward-filled daily, so CPI/GDP/unemployment carry no true "
        "day-to-day information; index and ETF series do carry daily changes.",
    ),
}


def fundamental_details(theme: str) -> tuple[str, str, str]:
    return (
        f"Fundamental — {theme.replace('_', ' ').title()}",
        "Open — richest whitespace (only market cap is used by the 101, once).",
        "Reporting-lag / lookahead risk — watch the fast-vs-slow gap; quarterly/annual "
        "variables behave as step-functions (low turnover); cross-sec, so rankable.",
    )


def load_items(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = payload.get("items")
    if not isinstance(items, list):
        raise ValueError(f"{path} must contain an 'items' array")
    if any(not isinstance(item, dict) for item in items):
        raise ValueError("Every item in the input must be an object")
    return items


def load_themes(path: Path, fundamental_names: set[str]) -> dict[str, str]:
    mapping = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(mapping, dict):
        raise ValueError(f"{path} must contain an object")
    unknown_themes = sorted(set(mapping.values()) - set(THEMES))
    if unknown_themes:
        raise ValueError(f"Unknown fundamental themes: {', '.join(unknown_themes)}")
    mapped_names = set(mapping)
    missing = sorted(fundamental_names - mapped_names)
    extra = sorted(mapped_names - fundamental_names)
    if missing:
        raise ValueError(
            "Fundamental variables missing from fundamental_themes.json: "
            + ", ".join(missing)
        )
    if extra:
        raise ValueError(
            "fundamental_themes.json contains variables not in the input: "
            + ", ".join(extra)
        )
    return mapping


def cluster_for(item: dict[str, Any], themes: dict[str, str]) -> str:
    data_type = item.get("data_types")
    group = item.get("groupname")
    if data_type == "Technical" and group in TECHNICAL_PRICE_GROUPS:
        return "price_volume"
    if data_type == "Technical" and group == "GROUP_intra1":
        return "intraday"
    if data_type == "Fundamental":
        return f"fundamental_{themes[item['varname']]}"
    if data_type == "Seasonality":
        return "seasonality"
    if data_type in {"Macro", "ETF"}:
        return "macro"
    raise ValueError(
        f"Cannot classify {item.get('varname', '<unnamed>')}: "
        f"data_types={data_type!r}, groupname={group!r}"
    )


def short_description(description: str) -> str:
    text = " ".join(str(description).split())
    text = re.sub(
        r"^This (?:variable|field)\s+"
        r"(?:represents|provides|indicates|reflects|is|includes|measures)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    sentence = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)[0].strip()
    if len(sentence) > 78:
        sentence = sentence[:77].rstrip() + "…"
    return sentence.replace("|", "\\|")


def frequency(value: Any) -> str:
    try:
        days = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid update_frequency: {value!r}") from exc
    if days <= 3:
        return "daily"
    if days <= 40:
        return "monthly"
    if days <= 100:
        return "quarterly"
    return "annual"


def row(item: dict[str, Any], cluster: str) -> tuple[str, str, str, str]:
    name = item["varname"]
    marker = " ⬤" if name in COVERED | OPTIONAL_COVERED else ""
    dimension = (
        "market-wide"
        if cluster == "macro" or item.get("groupname") in MACRO_GROUPS
        else "cross-sec"
        if item.get("dimensions") == "2D"
        else "market-wide"
    )
    return (
        f"`{name}`{marker}",
        short_description(item.get("description", "")),
        dimension,
        frequency(item.get("update_frequency")),
    )


def caveat(item: dict[str, Any]) -> str:
    flags: list[str] = []
    if item.get("is_derived") == 1:
        flags.append("derived")
    if item.get("delay_0") == 0:
        flags.append("`delay_0=0`: timing review; do not auto-delay")
    try:
        coverage = float(item.get("coverage"))
    except (TypeError, ValueError):
        coverage = None
    if coverage is not None and coverage < SPARSE_COVERAGE_THRESHOLD:
        flags.append(f"sparse coverage ({coverage:g})")
    if item.get("empty_value") != "" and item.get("empty_value") is not None:
        flags.append(f"missing encoded as `{item['empty_value']}`")
    if item.get("adjfactor_type"):
        flags.append("corporate-action adjusted")
    if item.get("groupname") == "GROUP_fred":
        flags.append("forward-filled; underlying cadence is slower")
    return "; ".join(flags) if flags else "—"


def table(
    items: list[dict[str, Any]], cluster: str, *, include_caveat: bool = False
) -> str:
    lines = [
        "| var | what it is | dim | freq | caveat |"
        if include_caveat
        else "| var | what it is | dim | freq |",
        "|---|---|---|---|---|" if include_caveat else "|---|---|---|---|",
    ]
    for item in sorted(items, key=lambda value: value["varname"]):
        values = row(item, cluster)
        if include_caveat:
            values += (caveat(item),)
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def validate(items: list[dict[str, Any]], clusters: dict[str, list[dict[str, Any]]]) -> None:
    expected = {
        "price_volume": 16,
        "intraday": 30,
        "fundamental": 175,
        "seasonality": 18,
        "macro": 16,
    }
    actual = {
        "price_volume": len(clusters.get("price_volume", [])),
        "intraday": len(clusters.get("intraday", [])),
        "fundamental": sum(
            len(clusters.get(f"fundamental_{theme}", [])) for theme in THEMES
        ),
        "seasonality": len(clusters.get("seasonality", [])),
        "macro": len(clusters.get("macro", [])),
    }
    if len(items) == 255 and actual != expected:
        raise ValueError(f"Cluster counts do not match expected counts: {actual}")
    names = [item["varname"] for item in items]
    name_clusters: dict[str, set[str]] = {}
    for cluster, cluster_items in clusters.items():
        for item in cluster_items:
            name_clusters.setdefault(item["varname"], set()).add(cluster)
    cross_cluster_duplicates = sorted(
        name for name, memberships in name_clusters.items() if len(memberships) > 1
    )
    if cross_cluster_duplicates:
        raise ValueError(
            "Variables appear in multiple clusters: "
            + ", ".join(cross_cluster_duplicates)
        )
    clustered_names = [
        item["varname"] for cluster_items in clusters.values() for item in cluster_items
    ]
    if sorted(names) != sorted(clustered_names):
        raise ValueError("Cluster membership does not cover each input variable exactly once")
    if any(row(item, "macro")[2] != "market-wide" for item in clusters["macro"]):
        raise ValueError("Macro variables must all be market-wide")
    expected_marked = {
        item["varname"]
        for item in items
        if item["varname"] in COVERED | OPTIONAL_COVERED
    }
    if len(expected_marked) != len(COVERED | (OPTIONAL_COVERED & set(names))):
        raise ValueError("Covered-variable marker set is inconsistent")
    if len(expected_marked) != 13 + len(OPTIONAL_COVERED & set(names)):
        raise ValueError(f"Expected covered variables are missing, found {len(expected_marked)}")


def render_index(clusters: dict[str, list[dict[str, Any]]]) -> str:
    total = sum(len(values) for values in clusters.values())
    lines = [
        f"# Alpha Data Catalog — {total} variables",
        "",
        "_The full lookup for the research agent. Keep this file in context; open "
        "clusters/<file>.md for the cluster you're working in._",
        "",
        "## How to use this",
        "- Work in one cluster/subcluster at a time. Generate the core of each alpha from "
        "its variables (open the relevant cluster file for depth).",
        "- You may pull one term from another cluster for a conditioner, neutralizer, or "
        "interaction; keep the main signal in your assigned cluster.",
        "- A strong novel move is crossing two distant clusters in one formula, such as a "
        "price/volume reversal gated by a seasonality flag.",
        "- `dim` = `cross-sec` (varies per stock and is rankable) or `market-wide` (one "
        "series that must be interacted). `freq` is the update cadence.",
        "- Cluster files add a `caveat` column for actionable metadata such as timing, "
        "derivation, sparse coverage, missing-value encoding, adjustments, and forward-fill.",
        "- ⬤ marks variables used by the 101 alphas; treat them as picked-over.",
        "",
        "## Clusters at a glance",
        "| file | vars | status |",
        "|---|---:|---|",
    ]
    for cluster in CLUSTER_ORDER:
        title, status, _ = (
            CLUSTER_DETAILS[cluster]
            if cluster in CLUSTER_DETAILS
            else fundamental_details(cluster.removeprefix("fundamental_"))
        )
        del title
        lines.append(
            f"| `clusters/{cluster}.md` | {len(clusters[cluster])} | {status} |"
        )
    for cluster in CLUSTER_ORDER:
        title, _, _ = (
            CLUSTER_DETAILS[cluster]
            if cluster in CLUSTER_DETAILS
            else fundamental_details(cluster.removeprefix("fundamental_"))
        )
        lines.extend(
            [
                "",
                f"## {title}  ({len(clusters[cluster])})",
                "",
                table(clusters[cluster], cluster),
            ]
        )
    return "\n".join(lines) + "\n"


def render_cluster(cluster: str, items: list[dict[str, Any]]) -> str:
    title, status, notes = (
        CLUSTER_DETAILS[cluster]
        if cluster in CLUSTER_DETAILS
        else fundamental_details(cluster.removeprefix("fundamental_"))
    )
    return (
        f"# {title}  ({len(items)} vars)\n\n"
        f"**Status:** {status}\n"
        f"**Notes:** {notes}\n\n"
        "⬤ = used by the 101 alphas.\n\n"
        "Caveats are emitted only when raw metadata changes how a field should be "
        "handled. `delay_0=0` requests a timing review; it never means to add "
        "`ts_delay` automatically.\n\n"
        f"{table(items, cluster, include_caveat=True)}\n"
    )


def build(input_path: Path, themes_path: Path, output_dir: Path) -> None:
    items = load_items(input_path)
    fundamentals = {
        item["varname"] for item in items if item.get("data_types") == "Fundamental"
    }
    themes = load_themes(themes_path, fundamentals)
    clusters: dict[str, list[dict[str, Any]]] = {name: [] for name in CLUSTER_ORDER}
    for item in items:
        cluster = cluster_for(item, themes)
        clusters[cluster].append(item)
    validate(items, clusters)

    output_dir.mkdir(parents=True, exist_ok=True)
    cluster_dir = output_dir / "clusters"
    cluster_dir.mkdir(parents=True, exist_ok=True)
    for old_file in cluster_dir.glob("*.md"):
        old_file.unlink()
    (output_dir / "_INDEX.md").write_text(
        render_index(clusters), encoding="utf-8", newline="\n"
    )
    for cluster in CLUSTER_ORDER:
        (cluster_dir / f"{cluster}.md").write_text(
            render_cluster(cluster, clusters[cluster]),
            encoding="utf-8",
            newline="\n",
        )
    print(f"Built {len(items)} variables across {len(CLUSTER_ORDER)} cluster files.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", type=Path, default=ROOT / "data-distribution.json"
    )
    parser.add_argument(
        "--themes", type=Path, default=ROOT / "fundamental_themes.json"
    )
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data-map")
    args = parser.parse_args()
    build(args.input, args.themes, args.output_dir)


if __name__ == "__main__":
    main()
