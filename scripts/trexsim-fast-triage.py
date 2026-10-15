#!/usr/bin/env python3
"""Fast triage for the v3 research loop.

Run after every Fast batch has been ingested. The script does all of the triage
arithmetic so the research agent never has to:

  * buckets each Fast result against the selected frontier (new / ladder / marginal / dead),
  * resolves conflicts inside the batch (strongest first; dead-zone members are demoted),
  * groups candidates into Fast PNL neighborhoods and marks crowded ones,
  * applies the Slow gate (IR bands plus the static-formula rule),
  * writes the priority-ordered Slow queue that `trexsim-research-manifest.js slow` follows,
  * lists variant seeds with the exact IR/sqrt(turnover) each must reach.

Outputs:
  alphas/research/triage/latest.json          full machine-readable detail
  alphas/research/triage/latest-summary.md    compact summary the agent reads
  alphas/research/triage/triage-<stamp>.json  history copy
  alphas/research/slow-queue.json             ordered Slow queue (read by the manifest)

Usage:
  python3 scripts/trexsim-fast-triage.py [--root DIR] [--start YYYY-MM-DD] [--end YYYY-MM-DD] [--dry-run]
"""

import argparse
import csv
import datetime as dt
import glob
import json
import math
import os
import re
from pathlib import Path

DEFAULTS = {
    "fast_triage": {
        "new_max_corr": 0.45,
        "ladder_ratio_min": 1.3,
        "ladder_ratio_max_down": 0.77,
        "dead_zone": [0.83, 1.2],
        "neighborhood_corr": 0.5,
        "crowded_min_size": 4,
    },
    "slow": {"nightly_cap": 70},
    "slow_gate": {
        "promote_min_fast_ir": 0.05,
        "potential_min_fast_ir": 0.035,
        "static_min_fast_ir": 0.072,
        "potential_time_dependent_min_fast_ir": 0.045,
        "near_miss_slow_ir": [0.055, 0.07],
        "search_min_fast_ir": 0.065,
    },
}

TIER_NAMES = {1: "new", 2: "ladder", 3: "marginal", 4: "potential", 5: "dead"}
TIME_DEPENDENT = re.compile(r"\bts_[a-z_]+\s*\(|\bfor\b|\bwhile\b|np\.roll")
MIN_COMMON_DAYS = 20


# ---------------------------------------------------------------- helpers

def load_json(path, default=None):
    path = Path(path)
    if not path.exists():
        return default
    return json.loads(path.read_text())


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2) + "\n")
    os.replace(tmp, path)


def settings(root):
    state = load_json(root / "alphas/factory/state.json", {}) or {}
    budgets = state.get("budgets", {})
    merged = {}
    for key, base in DEFAULTS.items():
        merged[key] = {**base, **(budgets.get(key) or {})}
    return merged


def number(value):
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def quality(ir, tvr, stored=None):
    stored = number(stored)
    if stored is not None:
        return stored
    ir, tvr = number(ir), number(tvr)
    if ir is None or tvr is None or tvr <= 0:
        return None
    return ir / math.sqrt(tvr)


def load_series(path, start, end):
    series = {}
    with open(path, newline="") as handle:
        for row in csv.DictReader(handle):
            date, value = row.get("date"), number(row.get("dailypnl"))
            if date and value is not None and start <= date <= end:
                series[date] = value
    return series


def pearson(left, right):
    dates = left.keys() & right.keys()
    if len(dates) < MIN_COMMON_DAYS:
        return None
    xs = [left[d] for d in dates]
    ys = [right[d] for d in dates]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def ratio(q_candidate, q_other):
    if q_candidate is None or q_other is None or q_other <= 0 or q_candidate <= 0:
        return None
    return q_candidate / q_other


def classify_ratio(r, cfg):
    """Return 'ladder', 'marginal' or 'dead' for a correlated pair."""
    lo, hi = cfg["dead_zone"]
    if r is None:
        return "dead"
    if lo < r < hi:
        return "dead"
    if r >= cfg["ladder_ratio_min"] or r <= cfg["ladder_ratio_max_down"]:
        return "ladder"
    return "marginal"


def targets(q_blocker, cfg):
    return {
        "ladder_up_min_q": round(cfg["ladder_ratio_min"] * q_blocker, 4),
        "ladder_down_max_q": round(cfg["ladder_ratio_max_down"] * q_blocker, 4),
    }


# ---------------------------------------------------------------- loading

def load_candidates(root, start, end):
    out = []
    children = {}
    for path in sorted((root / "alphas/research/candidates").glob("*.json")):
        record = json.loads(path.read_text())
        parent = (record.get("lineage") or {}).get("parent_candidate_id")
        if parent:
            children[parent] = children.get(parent, 0) + 1
        fast = (record.get("runs") or {}).get("fast") or {}
        slow = (record.get("runs") or {}).get("slow") or {}
        result = fast.get("result") or {}
        slow_result = slow.get("result") or {}
        entry = {
            "id": record.get("candidate_id"),
            "title": record.get("title"),
            "hypothesis": (record.get("metadata") or {}).get("hypothesis"),
            "family_id": (record.get("lineage") or {}).get("family_id"),
            "stage": (record.get("lineage") or {}).get("stage"),
            "purpose": ((record.get("lineage") or {}).get("changes") or {}).get("purpose"),
            "status": record.get("status"),
            "time_dependent": bool(TIME_DEPENDENT.search(record.get("code") or "")),
            "fast_status": fast.get("status"),
            "fast_id": result.get("id"),
            "fast_ir": number(result.get("ir")),
            "fast_tvr": number(result.get("turnover")),
            "fast_q": quality(result.get("ir"), result.get("turnover"), result.get("ir_tvr")),
            "mechanism": (record.get("metadata") or {}).get("mechanism_classification"),
            "axes": (record.get("metadata") or {}).get("behavioral_axes") or {},
            "slow_batch_at": ((slow.get("provenance") or {}).get("batch") or {}).get("created_at"),
            "slow_status": slow.get("status"),
            "slow_ir": number(slow_result.get("ir")),
            "slow_q": quality(slow_result.get("ir"), slow_result.get("turnover"), slow_result.get("ir_tvr")),
            "series": None,
        }
        pnl = result.get("archive_pnl_csv")
        if fast.get("status") == "success" and pnl and (root / pnl).exists():
            entry["series"] = load_series(root / pnl, start, end)
        out.append(entry)
    for entry in out:
        entry["children"] = children.get(entry["id"], 0)
    return out


def legacy_fast_pnl(root, name, slow_id):
    directory = root / "alphas/results" / name
    slow_json = directory / f"slow-{slow_id}.json"
    if not slow_json.exists():
        return None
    expression = (load_json(slow_json) or {}).get("expression", "").strip()
    for fast_json in sorted(directory.glob("fast-*.json")):
        raw = load_json(fast_json) or {}
        if raw.get("expression", "").strip() == expression:
            csv_path = fast_json.with_name(fast_json.name.replace(".json", ".pnl.csv"))
            if csv_path.exists():
                return csv_path
    return None


def load_frontier(root, candidates, start, end):
    frontier_doc = load_json(root / "alphas/factory/master-frontier.json", {}) or {}
    by_id = {c["id"]: c for c in candidates}
    members, seen = [], set()
    groups = (
        frontier_doc.get("fixed_already_submitted_prefix", [])
        + frontier_doc.get("legacy_selected_baseline", [])
        + frontier_doc.get("current_live_research_candidates", [])
    )
    for row in groups:
        ident = str(row.get("id"))
        if ident in seen:
            continue
        seen.add(ident)
        member = {
            "id": ident,
            "name": row.get("name") or ident,
            "slow_q": number(row.get("ir_sqrt_turnover")),
            "slow_ir": number(row.get("slow_ir")),
            "pnl_source": None,
            "series": None,
        }
        if row.get("source_category") == "legacy":
            path = legacy_fast_pnl(root, row.get("name"), ident)
            if path:
                member["pnl_source"] = "fast"
            elif row.get("pnl_reference") and (root / row["pnl_reference"]).exists():
                path, member["pnl_source"] = root / row["pnl_reference"], "slow-fallback"
            if path:
                member["series"] = load_series(path, start, end)
        else:
            candidate = by_id.get(ident)
            if candidate and candidate["series"]:
                member["series"], member["pnl_source"] = candidate["series"], "fast"
        members.append(member)
    return members


# ---------------------------------------------------------------- triage

def triage(root, start, end):
    cfg_all = settings(root)
    cfg, gate, cap = cfg_all["fast_triage"], cfg_all["slow_gate"], int(cfg_all["slow"]["nightly_cap"])
    candidates = load_candidates(root, start, end)
    frontier = load_frontier(root, candidates, start, end)
    frontier_ids = {m["id"] for m in frontier}

    for c in candidates:
        ir = c["fast_ir"]
        if c["fast_status"] != "success" or ir is None:
            c["band"] = "error" if c["fast_status"] == "error" else "pending"
        elif ir >= gate["promote_min_fast_ir"]:
            c["band"] = "promoted"
        elif ir >= gate["potential_min_fast_ir"]:
            c["band"] = "potential"
        else:
            c["band"] = "rejected"

    considered = [c for c in candidates if c["band"] in ("promoted", "potential") and c["series"]]

    # --- correlation against the frontier
    for c in considered:
        links = []
        for m in frontier:
            if not m["series"]:
                continue
            rho = pearson(c["series"], m["series"])
            if rho is not None and rho > cfg["new_max_corr"]:
                r = ratio(c["fast_q"], m["slow_q"])
                links.append({"id": m["id"], "name": m["name"], "corr": round(rho, 3),
                              "blocker_q": m["slow_q"], "ratio": None if r is None else round(r, 3),
                              "relation": classify_ratio(r, cfg)})
        c["frontier_links"] = links
        if not links:
            c["bucket"] = "new"
        else:
            relations = {link["relation"] for link in links}
            c["bucket"] = "dead" if "dead" in relations else ("marginal" if "marginal" in relations else "ladder")
        c["max_frontier_corr"] = max((l["corr"] for l in links), default=None)

    # --- pairwise correlation among considered candidates
    pair = {}
    for i, a in enumerate(considered):
        for b in considered[i + 1:]:
            rho = pearson(a["series"], b["series"])
            if rho is not None:
                pair[(a["id"], b["id"])] = pair[(b["id"], a["id"])] = rho

    # --- neighborhoods (connected components above neighborhood_corr)
    parent = {c["id"]: c["id"] for c in considered}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for (a, b), rho in pair.items():
        if rho > cfg["neighborhood_corr"]:
            parent[find(a)] = find(b)
    groups = {}
    for c in considered:
        groups.setdefault(find(c["id"]), []).append(c)
    neighborhoods = []
    for index, members in enumerate(sorted(groups.values(), key=lambda g: -len(g)), start=1):
        members.sort(key=lambda c: -(c["fast_q"] or 0))
        touches = sorted({l["name"] for c in members for l in c["frontier_links"]})
        hood = {
            "neighborhood": index,
            "size": len(members),
            "members": [c["id"] for c in members],
            "best": members[0]["id"],
            "best_title": members[0]["title"],
            "best_fast_q": members[0]["fast_q"],
            "touches_frontier": touches,
            "crowded": len(members) >= cfg["crowded_min_size"] or bool(touches),
        }
        for c in members:
            c["neighborhood"] = index
        neighborhoods.append(hood)

    # --- Slow gate
    for c in candidates:
        c["slow_gate"] = None
        if c["band"] not in ("promoted", "potential"):
            continue
        if c["slow_ir"] is not None or c["slow_status"] in ("success", "error"):
            c["slow_gate"] = "done"
        elif c["band"] == "promoted":
            if not c["time_dependent"] and c["fast_ir"] < gate["static_min_fast_ir"]:
                c["slow_gate"] = "excluded:static-below-floor"
            elif c["id"].startswith("search-") and c["fast_ir"] < gate.get("search_min_fast_ir", 0.065):
                c["slow_gate"] = "excluded:search-below-floor"
            else:
                c["slow_gate"] = "eligible"
        else:
            if c["time_dependent"] and c["fast_ir"] >= gate["potential_time_dependent_min_fast_ir"]:
                c["slow_gate"] = "eligible"
            elif not c["time_dependent"]:
                c["slow_gate"] = "excluded:static-potential"
            else:
                c["slow_gate"] = "excluded:potential-below-gate"
        if c["slow_gate"] == "eligible" and not c["series"]:
            c["slow_gate"] = "eligible-no-pnl"

    # --- tiers and in-batch conflict resolution (strongest first)
    def base_tier(c):
        if c["bucket"] == "dead":
            return 5
        if c["band"] == "potential":
            return 4
        return {"new": 1, "ladder": 2, "marginal": 3}[c["bucket"]]

    eligible = [c for c in considered if c["slow_gate"] == "eligible"]
    for c in eligible:
        c["tier"] = base_tier(c)
        c["batch_blocker"] = None
    kept = []
    for c in sorted(eligible, key=lambda c: (c["tier"], -(c["fast_q"] or 0))):
        if c["tier"] == 5:
            continue
        worst = None
        for k in kept:
            rho = pair.get((c["id"], k["id"]))
            if rho is None or rho <= cfg["new_max_corr"]:
                continue
            relation = classify_ratio(ratio(c["fast_q"], k["fast_q"]), cfg)
            if relation == "dead" or (relation == "marginal" and worst is None):
                worst = (relation, k, rho)
                if relation == "dead":
                    break
        if worst and worst[0] == "dead":
            c["tier"], c["bucket"] = 5, "dead-batch"
            c["batch_blocker"] = {"id": worst[1]["id"], "corr": round(worst[2], 3), "blocker_q": worst[1]["fast_q"]}
            continue
        if worst and worst[0] == "marginal" and c["tier"] < 3:
            c["tier"] = 3
            c["batch_blocker"] = {"id": worst[1]["id"], "corr": round(worst[2], 3), "blocker_q": worst[1]["fast_q"]}
        kept.append(c)

    # --- Slow queue (overflow from the previous queue keeps its place within a tier)
    previous = load_json(root / "alphas/research/slow-queue.json", {}) or {}
    first_seen = {e["candidate_id"]: e.get("first_queued_at") for e in previous.get("entries", [])}
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    queue_rows = sorted(
        eligible,
        key=lambda c: (c["tier"], 0 if c["id"] in first_seen else 1, first_seen.get(c["id"]) or now, -(c["fast_ir"] or 0)),
    )
    entries = []
    for position, c in enumerate(queue_rows, start=1):
        entries.append({
            "position": position,
            "candidate_id": c["id"],
            "tier": c["tier"],
            "tier_name": TIER_NAMES[c["tier"]],
            "within_cap": position <= cap,
            "fast_ir": c["fast_ir"],
            "fast_q": c["fast_q"],
            "first_queued_at": first_seen.get(c["id"]) or now,
        })
    excluded = [{"candidate_id": c["id"], "reason": c["slow_gate"].split(":", 1)[1], "fast_ir": c["fast_ir"]}
                for c in candidates if (c["slow_gate"] or "").startswith("excluded")]
    queue = {"schema_version": 1, "created_at": now, "cap": cap, "entries": entries, "excluded": excluded}

    # --- seeds for the next variant round
    seeds = []

    def seed(c, target, blocker=None, note=None):
        row = {"candidate_id": c["id"], "title": c["title"], "target": target,
               "fast_ir": c["fast_ir"], "fast_q": c["fast_q"], "slow_ir": c["slow_ir"],
               "children": c.get("children", 0)}
        if blocker:
            row["blocker"] = blocker["id"]
            if blocker.get("blocker_q"):
                row.update(targets(blocker["blocker_q"], cfg))
        if note:
            row["note"] = note
        seeds.append(row)

    for c in considered:
        if c["slow_gate"] == "done":
            continue
        if c["bucket"] == "dead":
            link = min(c["frontier_links"], key=lambda l: abs((l["ratio"] or 1) - 1))
            seed(c, "escape-dead-zone", link)
        elif c["bucket"] == "dead-batch":
            seed(c, "escape-dead-zone", c["batch_blocker"])
        elif c["bucket"] == "marginal" or c.get("tier") == 3:
            link = c.get("batch_blocker") or next((l for l in c["frontier_links"] if l["relation"] == "marginal"), None)
            seed(c, "ladder", link, "inside the Fast buffer; a clearer q gap makes Slow admission safer")
        if (c["slow_gate"] or "").startswith("excluded"):
            floor = gate["potential_time_dependent_min_fast_ir"] if c["time_dependent"] else gate["static_min_fast_ir"]
            need = round(floor - (c["fast_ir"] or 0), 3)
            seed(c, "clear-ir-floor", note=f"{c['slow_gate'].split(':', 1)[1]}; needs about +{need} Fast IR")
    lo, hi = gate["near_miss_slow_ir"]
    for c in candidates:
        if c["slow_ir"] is not None and lo <= c["slow_ir"] <= hi:
            seed(c, "clear-ir-floor", note=f"Slow near-miss {c['slow_ir']}")
        elif c["slow_ir"] is not None and c["slow_ir"] > 0.07 and c["id"] not in frontier_ids:
            link = max(c.get("frontier_links") or [], key=lambda l: l["corr"], default=None)
            if link is None:
                rivals = [(pair.get((c["id"], o["id"])), o) for o in considered
                          if o["id"] != c["id"] and o["slow_ir"] is not None and o["slow_ir"] > 0.07]
                rivals = [(rho, o) for rho, o in rivals if rho is not None and rho > cfg["new_max_corr"]]
                if rivals:
                    rho, o = max(rivals, key=lambda item: item[0])
                    link = {"id": o["id"], "corr": round(rho, 3), "blocker_q": o["slow_q"]}
            seed(c, "blocked-qualifier", link, "Slow-qualified but not selected by the optimizer")
        elif c["fast_ir"] is not None and c["fast_ir"] <= -gate["potential_min_fast_ir"] and c["stage"] == "base":
            seed(c, "sign-correct", note="materially negative Fast IR; one sign-corrected child allowed")
    order = {"blocked-qualifier": 0, "clear-ir-floor": 1, "escape-dead-zone": 2, "ladder": 3, "sign-correct": 4}
    seeds.sort(key=lambda s: (order.get(s["target"], 9), s["children"], -(s["fast_ir"] or 0)))

    # --- learning view: what worked, by behavioral axis, plus Fast-vs-Slow for the latest Slow night
    pool_doc = load_json(root / "alphas/research/optimal-pool.json", {}) or {}
    in_pool = {row.get("name") for row in pool_doc.get("submission_order", []) if row.get("source") != "legacy"}
    ran = [c for c in candidates if c["band"] not in ("pending",)]
    axes_table = {}
    for axis in ("economic_behavior", "information_timing", "horizon", "conditioning_state", "expected_turnover"):
        groups_by_value = {}
        for c in ran:
            value = str(c["axes"].get(axis) or "unlabelled")
            groups_by_value.setdefault(value, []).append(c)
        rows = []
        for value, members in groups_by_value.items():
            irs = [m["fast_ir"] for m in members if m["fast_ir"] is not None]
            rows.append({
                "value": value,
                "n": len(members),
                "promoted": sum(m["band"] == "promoted" for m in members),
                "potential": sum(m["band"] == "potential" for m in members),
                "best_fast_ir": max(irs) if irs else None,
                "mean_fast_ir": round(sum(irs) / len(irs), 4) if irs else None,
                "slow_qualified": sum((m["slow_ir"] or 0) > 0.07 for m in members),
                "in_pool": sum(m["id"] in in_pool for m in members),
            })
        axes_table[axis] = sorted(rows, key=lambda r: (-(r["mean_fast_ir"] or -9), -r["n"]))
    top = sorted([c for c in ran if c["fast_ir"] is not None], key=lambda c: -c["fast_ir"])[:10]
    top_rows = [{"id": c["id"], "mechanism": c["mechanism"], "fast_ir": c["fast_ir"], "fast_q": c["fast_q"],
                 "bucket": c.get("bucket"), "neighborhood": c.get("neighborhood"), "slow_ir": c["slow_ir"]} for c in top]
    slow_done = [c for c in candidates if c["slow_ir"] is not None]
    latest_night = max((c["slow_batch_at"] or "" for c in slow_done), default=None)
    night = [c for c in slow_done if latest_night and c["slow_batch_at"] == latest_night]
    night_rows = [{"id": c["id"], "time_dependent": c["time_dependent"], "fast_ir": c["fast_ir"], "slow_ir": c["slow_ir"],
                   "delta": None if c["fast_ir"] is None else round(c["slow_ir"] - c["fast_ir"], 3),
                   "qualified": c["slow_ir"] > 0.07, "in_pool": c["id"] in in_pool}
                  for c in sorted(night, key=lambda c: -(c["slow_ir"] or 0))]
    learning = {"axes": axes_table, "top_fast": top_rows, "latest_slow_batch": latest_night, "latest_slow_results": night_rows}

    report = {
        "schema_version": 1,
        "created_at": now,
        "window": {"start": start, "end": end},
        "settings": cfg_all,
        "frontier": [{k: v for k, v in m.items() if k != "series"} for m in frontier],
        "counts": {
            "candidates": len(candidates),
            "bands": {b: sum(c["band"] == b for c in candidates) for b in ("promoted", "potential", "rejected", "error", "pending")},
            "buckets": {b: sum(c.get("bucket") == b for c in considered) for b in ("new", "ladder", "marginal", "dead", "dead-batch")},
            "queue_tiers": {TIER_NAMES[t]: sum(e["tier"] == t for e in entries) for t in TIER_NAMES},
            "queue_within_cap": sum(e["within_cap"] for e in entries),
            "queue_overflow": sum(not e["within_cap"] for e in entries),
            "excluded": {r: sum(x["reason"] == r for x in excluded) for r in sorted({x["reason"] for x in excluded})},
        },
        "neighborhoods": neighborhoods,
        "candidates": [
            {k: v for k, v in c.items() if k != "series"}
            for c in candidates if c["band"] in ("promoted", "potential")
        ],
        "seeds": seeds,
        "learning": learning,
    }
    return report, queue


# ---------------------------------------------------------------- summary

def fmt(value, digits=3):
    return "-" if value is None else f"{value:.{digits}f}"


def summary_markdown(report, queue):
    c = report["counts"]
    lines = [
        f"# Fast triage — {report['created_at']}",
        "",
        f"Window {report['window']['start']} to {report['window']['end']}. "
        f"{c['candidates']} candidates; frontier of {len(report['frontier'])} "
        f"({sum(m['pnl_source'] == 'fast' for m in report['frontier'])} with Fast PNL, "
        f"{sum(m['pnl_source'] == 'slow-fallback' for m in report['frontier'])} using Slow PNL as fallback).",
        "",
        "## Counts",
        "",
        "- Fast bands: " + ", ".join(f"{k} {v}" for k, v in c["bands"].items()),
        "- Buckets: " + ", ".join(f"{k} {v}" for k, v in c["buckets"].items()),
        "- Excluded from Slow: " + (", ".join(f"{k} {v}" for k, v in c["excluded"].items()) or "none"),
        "",
        f"## Slow queue (cap {queue['cap']}; {c['queue_within_cap']} tonight, {c['queue_overflow']} overflow)",
        "",
        "Applied automatically by `node scripts/trexsim-run.js research-slow`. Nothing to decide here.",
        "",
    ]
    for tier, name in TIER_NAMES.items():
        ids = [e["candidate_id"] for e in queue["entries"] if e["tier"] == tier]
        if ids:
            lines.append(f"- tier {tier} {name} ({len(ids)}): " + ", ".join(ids[:12]) + (" ..." if len(ids) > 12 else ""))
    crowded = [h for h in report["neighborhoods"] if h["crowded"]]
    lines += ["", f"## Crowded neighborhoods ({len(crowded)} of {len(report['neighborhoods'])}) — steer wave 2 away", ""]
    for h in crowded[:15]:
        touch = f"; overlaps frontier {', '.join(h['touches_frontier'][:3])}" if h["touches_frontier"] else ""
        lines.append(f"- N{h['neighborhood']} size {h['size']}{touch}: best `{h['best']}` (q {fmt(h['best_fast_q'])}) — {h['best_title']}")
    if not crowded:
        lines.append("- none")
    lines += ["", f"## Variant seeds (top 20 of {len(report['seeds'])})", "",
              "| seed | target | Fast IR | q | reach q ≥ (up) | or ≤ (down) | children | note |",
              "|---|---|---|---|---|---|---|---|"]
    for s in report["seeds"][:20]:
        lines.append(
            f"| `{s['candidate_id']}` | {s['target']} | {fmt(s['fast_ir'])} | {fmt(s['fast_q'])} | "
            f"{fmt(s.get('ladder_up_min_q'))} | {fmt(s.get('ladder_down_max_q'))} | {s['children']} | {s.get('note', '')} |"
        )
    if not report["seeds"]:
        lines.append("| - | - | - | - | - | - | - | - |")
    learning = report["learning"]
    lines += ["", "## What worked (by behavioral axis, from candidate metadata)", ""]
    for axis, rows in learning["axes"].items():
        cells = "; ".join(
            f"{r['value']} n{r['n']} prom {r['promoted']} meanIR {fmt(r['mean_fast_ir'])} best {fmt(r['best_fast_ir'])}"
            + (f" slowQ {r['slow_qualified']}" if r["slow_qualified"] else "") + (f" pool {r['in_pool']}" if r["in_pool"] else "")
            for r in rows[:6]
        )
        lines.append(f"- **{axis}:** {cells or '-'}")
    lines += ["", "## Top 10 by Fast IR", "", "| candidate | mechanism | Fast IR | q | bucket | N | Slow IR |", "|---|---|---|---|---|---|---|"]
    for r in learning["top_fast"]:
        lines.append(f"| `{r['id']}` | {r['mechanism'] or '-'} | {fmt(r['fast_ir'])} | {fmt(r['fast_q'])} | {r['bucket'] or '-'} | {r['neighborhood'] or '-'} | {fmt(r['slow_ir'])} |")
    if learning["latest_slow_results"]:
        rows = learning["latest_slow_results"]
        lines += ["", f"## Latest Slow night ({learning['latest_slow_batch']}): {sum(r['qualified'] for r in rows)} of {len(rows)} qualified, "
                  f"{sum(r['in_pool'] for r in rows)} in the pool", "",
                  "| candidate | ts ops | Fast IR | Slow IR | delta | qualified | in pool |", "|---|---|---|---|---|---|---|"]
        for r in rows[:30]:
            delta = "-" if r["delta"] is None else f"{r['delta']:+.3f}"
            lines.append(f"| `{r['id']}` | {'yes' if r['time_dependent'] else 'no'} | {fmt(r['fast_ir'])} | {fmt(r['slow_ir'])} | "
                         f"{delta} | {'yes' if r['qualified'] else 'no'} | {'yes' if r['in_pool'] else 'no'} |")
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    parser.add_argument("--start", default="2020-01-08")
    parser.add_argument("--end", default="2021-12-30")
    parser.add_argument("--dry-run", action="store_true", help="print the summary without writing files")
    args = parser.parse_args()
    root = Path(args.root).resolve()

    report, queue = triage(root, args.start, args.end)
    summary = summary_markdown(report, queue)
    if args.dry_run:
        print(summary)
        return
    stamp = report["created_at"].replace(":", "").replace("-", "")
    triage_dir = root / "alphas/research/triage"
    write_json(triage_dir / "latest.json", report)
    write_json(triage_dir / f"triage-{stamp}.json", report)
    (triage_dir / "latest-summary.md").write_text(summary)
    write_json(root / "alphas/research/slow-queue.json", queue)
    print(json.dumps({
        "summary": str((triage_dir / "latest-summary.md").relative_to(root)),
        "queue": "alphas/research/slow-queue.json",
        "queue_within_cap": report["counts"]["queue_within_cap"],
        "queue_overflow": report["counts"]["queue_overflow"],
        "seeds": len(report["seeds"]),
    }))


if __name__ == "__main__":
    main()
