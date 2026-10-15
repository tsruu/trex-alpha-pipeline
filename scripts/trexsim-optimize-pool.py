#!/usr/bin/env python3
"""Choose a maximum-cardinality valid Trexquant submission pool and order.

Competition-pool assumption: previously submitted alphas can be deleted and then
resubmitted in the optimizer's desired order. The current submitted pool is
therefore intentionally NOT treated as a fixed prefix. This solver optimizes the
entire eligible set from scratch and emits the order in which to rebuild it.
"""

import argparse
import json
import math
import time
from pathlib import Path


def quality(alpha):
    stored = alpha.get("ir_tvr")
    if stored not in (None, ""):
        return float(stored)
    ir = float(alpha["ir"])
    tvr = float(alpha["tvr"])
    if tvr <= 0:
        raise RuntimeError(f"{alpha['id']}: turnover must be positive")
    return ir / math.sqrt(tvr)


def connected_components(vertices, adjacency):
    unseen = set(vertices)
    components = []
    while unseen:
        start = unseen.pop()
        component = {start}
        stack = [start]
        while stack:
            current = stack.pop()
            neighbors = adjacency[current] & unseen
            unseen -= neighbors
            component |= neighbors
            stack.extend(neighbors)
        components.append(sorted(component))
    return components


def solve_independent_component(vertices, conflict_sets, qualities, deadline):
    """Exact branch-and-bound MIS, with quality sum as a same-count tie-break."""
    local = list(vertices)
    position = {vertex: index for index, vertex in enumerate(local)}
    conflict_masks = []
    for vertex in local:
        mask = 0
        for neighbor in conflict_sets[vertex]:
            if neighbor in position:
                mask |= 1 << position[neighbor]
        conflict_masks.append(mask)

    best_mask = 0
    best_count = 0
    best_quality = -1.0
    calls = 0
    timed_out = False

    def update(mask, count, score):
        nonlocal best_mask, best_count, best_quality
        if count > best_count or (count == best_count and score > best_quality):
            best_mask, best_count, best_quality = mask, count, score

    # Seed a useful lower bound by repeatedly taking the lowest-degree vertex.
    available = (1 << len(local)) - 1
    seed = 0
    seed_score = 0.0
    while available:
        choices = [i for i in range(len(local)) if available & (1 << i)]
        vertex = min(choices, key=lambda i: (conflict_masks[i] & available).bit_count())
        seed |= 1 << vertex
        seed_score += qualities[local[vertex]]
        available &= ~(1 << vertex)
        available &= ~conflict_masks[vertex]
    update(seed, seed.bit_count(), seed_score)

    def search(available_mask, chosen_mask, chosen_count, chosen_quality):
        nonlocal calls, timed_out
        calls += 1
        if deadline and calls % 1024 == 0 and time.monotonic() >= deadline:
            timed_out = True
            return
        if chosen_count + available_mask.bit_count() < best_count:
            return

        # Isolated vertices in the remaining conflict graph are always safe to include.
        isolated = 0
        probe = available_mask
        while probe:
            bit = probe & -probe
            vertex = bit.bit_length() - 1
            if conflict_masks[vertex] & available_mask == 0:
                isolated |= bit
            probe ^= bit
        if isolated:
            probe = isolated
            while probe:
                bit = probe & -probe
                vertex = bit.bit_length() - 1
                chosen_quality += qualities[local[vertex]]
                probe ^= bit
            chosen_mask |= isolated
            chosen_count += isolated.bit_count()
            available_mask &= ~isolated

        if not available_mask:
            update(chosen_mask, chosen_count, chosen_quality)
            return

        vertices_left = [i for i in range(len(local)) if available_mask & (1 << i)]
        vertex = max(
            vertices_left,
            key=lambda i: (conflict_masks[i] & available_mask).bit_count(),
        )
        bit = 1 << vertex
        search(
            available_mask & ~bit & ~conflict_masks[vertex],
            chosen_mask | bit,
            chosen_count + 1,
            chosen_quality + qualities[local[vertex]],
        )
        if not timed_out:
            search(available_mask & ~bit, chosen_mask, chosen_count, chosen_quality)

    search((1 << len(local)) - 1, 0, 0, 0.0)
    selected = [local[i] for i in range(len(local)) if best_mask & (1 << i)]
    return selected, calls, not timed_out


def markdown_report(result):
    lines = [
        "# Optimized Trexquant Alpha Pool",
        "",
        f"- Eligible Slow alphas: {result['counts']['eligible']}",
        f"- Selected maximum pool: {result['counts']['selected']}",
        f"- Excluded by pair conflicts: {result['counts']['excluded']}",
        f"- Optimality proven: {'yes' if result['solver']['optimality_proven'] else 'no'}",
        "",
        "## Submission order",
        "",
        "| # | Alpha | Source | TrexSim ID | IR | TVR | IR/√TVR | Admission |",
        "|---:|---|---|---:|---:|---:|---:|---|",
    ]
    for item in result["submission_order"]:
        lines.append(
            f"| {item['order']} | {item['name']} | {item['source']} | {item['id']} | "
            f"{item['ir']:.4f} | {item['tvr']:.4f} | {item['ir_tvr']:.4f} | {item['admission']} |"
        )
    lines.extend(["", "## Excluded", "", "| Alpha | TrexSim ID | Blocking selected alphas |", "|---|---:|---|"])
    for item in result["excluded"]:
        blockers = ", ".join(
            f"{blocker['name']} ({blocker['corr']:.3f})" for blocker in item["blockers"]
        )
        lines.append(f"| {item['name']} | {item['id']} | {blockers} |")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(
        description="Find a maximum valid pool and deterministic submission order."
    )
    parser.add_argument("correlation_json")
    parser.add_argument("--ir-min", type=float, default=0.07)
    parser.add_argument("--corr-max", type=float, default=0.50)
    parser.add_argument("--override", type=float, default=0.20)
    parser.add_argument("--timeout-seconds", type=float, default=0,
                        help="0 means no timeout; otherwise return the best proven-or-found pool.")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    source = json.loads(Path(args.correlation_json).read_text())
    ids = [str(value) for value in source.get("alpha_ids", [])]
    matrix = source.get("matrix", [])
    alpha_by_id = {str(item["id"]): item for item in source.get("alphas", [])}
    if len(matrix) != len(ids) or any(len(row) != len(ids) for row in matrix):
        raise RuntimeError("correlation matrix dimensions do not match alpha_ids")
    missing = [ident for ident in ids if ident not in alpha_by_id]
    if missing:
        raise RuntimeError("correlation metadata missing IDs: " + ",".join(missing))

    eligible_ids = []
    qualities = {}
    for ident in ids:
        alpha = alpha_by_id[ident]
        if alpha.get("ir") is None or float(alpha["ir"]) <= args.ir_min:
            continue
        if alpha.get("tvr") is None and alpha.get("ir_tvr") is None:
            raise RuntimeError(f"{ident}: TVR or IR/sqrt(TVR) is required")
        qualities[ident] = quality(alpha)
        eligible_ids.append(ident)

    index = {ident: ids.index(ident) for ident in eligible_ids}
    conflicts = {ident: set() for ident in eligible_ids}
    conflict_details = []
    compatible_overrides = []
    ratio = 1 + args.override
    for left_pos, left in enumerate(eligible_ids):
        for right in eligible_ids[left_pos + 1:]:
            corr = float(matrix[index[left]][index[right]])
            if corr <= args.corr_max:
                continue
            left_beats = qualities[left] >= ratio * qualities[right]
            right_beats = qualities[right] >= ratio * qualities[left]
            detail = {
                "left": left,
                "right": right,
                "corr": corr,
                "left_ir_tvr": qualities[left],
                "right_ir_tvr": qualities[right],
            }
            if left_beats or right_beats:
                detail["required_order"] = [right, left] if left_beats else [left, right]
                compatible_overrides.append(detail)
            else:
                conflicts[left].add(right)
                conflicts[right].add(left)
                conflict_details.append(detail)

    components = connected_components(eligible_ids, conflicts)
    deadline = time.monotonic() + args.timeout_seconds if args.timeout_seconds > 0 else None
    selected = []
    solver_calls = 0
    optimality_proven = True
    for component in components:
        chosen, calls, proven = solve_independent_component(
            component, conflicts, qualities, deadline
        )
        selected.extend(chosen)
        solver_calls += calls
        optimality_proven = optimality_proven and proven
        if deadline and time.monotonic() >= deadline:
            optimality_proven = False

    selected_set = set(selected)
    ordered_ids = sorted(selected, key=lambda ident: (qualities[ident], ident))
    submission_order = []
    accepted = []
    for order, ident in enumerate(ordered_ids, 1):
        correlated = []
        for previous in accepted:
            corr = float(matrix[index[ident]][index[previous]])
            if corr > args.corr_max:
                if qualities[ident] < ratio * qualities[previous]:
                    raise RuntimeError(
                        f"internal verification failed: {ident} cannot follow {previous}"
                    )
                correlated.append({"id": previous, "corr": corr})
        alpha = alpha_by_id[ident]
        admission = "first" if not accepted else (
            f"override against {len(correlated)}" if correlated else "correlation"
        )
        submission_order.append({
            "order": order,
            "id": ident,
            "name": alpha.get("name") or alpha.get("candidate_id") or ident,
            "source": alpha.get("source", "unknown"),
            "ir": float(alpha["ir"]),
            "tvr": float(alpha["tvr"]),
            "ir_tvr": qualities[ident],
            "admission": admission,
            "correlated_prior": correlated,
        })
        accepted.append(ident)

    excluded = []
    for ident in eligible_ids:
        if ident in selected_set:
            continue
        alpha = alpha_by_id[ident]
        blockers = []
        for blocker in sorted(conflicts[ident] & selected_set):
            blockers.append({
                "id": blocker,
                "name": alpha_by_id[blocker].get("name") or blocker,
                "corr": float(matrix[index[ident]][index[blocker]]),
                "ir_tvr": qualities[blocker],
            })
        excluded.append({
            "id": ident,
            "name": alpha.get("name") or alpha.get("candidate_id") or ident,
            "source": alpha.get("source", "unknown"),
            "ir": float(alpha["ir"]),
            "tvr": float(alpha["tvr"]),
            "ir_tvr": qualities[ident],
            "blockers": blockers,
        })

    result = {
        "description": "Maximum-cardinality pool under Trexquant correlation and override rules.",
        "input": str(Path(args.correlation_json)),
        "thresholds": {
            "slow_ir_strictly_greater_than": args.ir_min,
            "correlation_max": args.corr_max,
            "ir_tvr_override_multiplier": ratio,
        },
        "counts": {
            "matrix_runs": len(ids),
            "eligible": len(eligible_ids),
            "selected": len(selected),
            "excluded": len(excluded),
            "incompatible_pairs": len(conflict_details),
            "override_compatible_pairs": len(compatible_overrides),
        },
        "solver": {
            "method": "exact branch-and-bound maximum independent set by conflict component",
            "optimality_proven": optimality_proven,
            "search_calls": solver_calls,
        },
        "submission_order": submission_order,
        "excluded": excluded,
        "incompatible_pairs": conflict_details,
        "override_compatible_pairs": compatible_overrides,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    markdown = output.with_suffix(".md")
    markdown.write_text(markdown_report(result))
    print(json.dumps({
        "json": str(output),
        "markdown": str(markdown),
        "eligible": len(eligible_ids),
        "selected": len(selected),
        "optimality_proven": optimality_proven,
    }))


if __name__ == "__main__":
    main()
