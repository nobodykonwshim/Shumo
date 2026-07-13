#!/usr/bin/env python3
"""Reproduce case001 Problem 1-3 and audit the frozen Problem-4 route package."""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent

THETA = math.radians(120.0)
PHI = THETA / 2.0
ALPHA = math.radians(1.5)
NM = 1852.0


def half_widths(depth_m: float, slope_rad: float) -> tuple[float, float]:
    deep = depth_m * math.sin(PHI) / math.cos(PHI + slope_rad)
    shallow = depth_m * math.sin(PHI) / math.cos(PHI - slope_rad)
    return deep, shallow


def problem1() -> dict:
    offsets = [-800, -600, -400, -200, 0, 200, 400, 600, 800]
    depths = [70.0 - x * math.tan(ALPHA) for x in offsets]
    widths = [sum(half_widths(d, ALPHA)) for d in depths]
    overlap = [None]
    for i in range(1, len(offsets)):
        _, prev_shallow = half_widths(depths[i - 1], ALPHA)
        curr_deep, _ = half_widths(depths[i], ALPHA)
        eta = (prev_shallow + curr_deep - 200.0 / math.cos(ALPHA)) / widths[i]
        overlap.append(100.0 * eta)
    return {"offsets_m": offsets, "depths_m": depths, "widths_m": widths, "overlap_percent": overlap}


def problem2() -> dict:
    betas = [0, 45, 90, 135, 180, 225, 270, 315]
    distances_nm = [0, 0.3, 0.6, 0.9, 1.2, 1.5, 1.8, 2.1]
    matrix: list[list[float]] = []
    for beta_deg in betas:
        beta = math.radians(beta_deg)
        gamma = math.atan(abs(math.tan(ALPHA) * math.sin(beta)))
        row = []
        for distance_nm in distances_nm:
            depth = 120.0 + distance_nm * NM * math.tan(ALPHA) * math.cos(beta)
            row.append(sum(half_widths(depth, gamma)))
        matrix.append(row)
    return {"betas_degree": betas, "distances_nm": distances_nm, "coverage_width_m": matrix}


def overlap_fraction(previous_x: float, current_x: float, center_depth: float = 110.0) -> float:
    previous_depth = center_depth - previous_x * math.tan(ALPHA)
    current_depth = center_depth - current_x * math.tan(ALPHA)
    _, previous_shallow = half_widths(previous_depth, ALPHA)
    current_deep, current_shallow = half_widths(current_depth, ALPHA)
    current_width = current_deep + current_shallow
    return (previous_shallow + current_deep - (current_x - previous_x) / math.cos(ALPHA)) / current_width


def problem3() -> dict:
    west, east = -3704.0, 3704.0
    center_depth = 110.0
    lo, hi = west, east
    for _ in range(80):
        x = (lo + hi) / 2.0
        depth = center_depth - x * math.tan(ALPHA)
        deep, _ = half_widths(depth, ALPHA)
        if x - deep * math.cos(ALPHA) <= west:
            lo = x
        else:
            hi = x
    positions = [lo]

    while True:
        previous = positions[-1]
        prev_depth = center_depth - previous * math.tan(ALPHA)
        _, prev_shallow = half_widths(prev_depth, ALPHA)
        if previous + prev_shallow * math.cos(ALPHA) >= east:
            break
        lo, hi = previous, east
        for _ in range(80):
            x = (lo + hi) / 2.0
            if overlap_fraction(previous, x, center_depth) >= 0.10:
                lo = x
            else:
                hi = x
        positions.append(lo)

    last_depth = center_depth - positions[-1] * math.tan(ALPHA)
    _, last_shallow = half_widths(last_depth, ALPHA)
    previous_depth = center_depth - positions[-2] * math.tan(ALPHA)
    _, previous_shallow = half_widths(previous_depth, ALPHA)
    return {
        "line_count": len(positions),
        "positions_m": positions,
        "total_length_m": 3704.0 * len(positions),
        "east_overshoot_m": positions[-1] + last_shallow * math.cos(ALPHA) - east,
        "line_33_shortfall_m": east - (positions[-2] + previous_shallow * math.cos(ALPHA)),
    }


def audit_problem4() -> dict:
    metrics = json.loads((ROOT / "data/problem4_final_metrics.json").read_text(encoding="utf-8"))
    with (ROOT / "data/problem4_route_station_matrix.csv").open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    exact_sum = sum(float(row["exact_length_m"]) for row in rows)
    minimum_radius = min(float(row["minimum_curvature_radius_m"]) for row in rows)
    assert len(rows) == metrics["required_metrics"]["survey_line_count"] == 61
    assert abs(exact_sum - metrics["required_metrics"]["total_survey_line_length_m"]) < 1e-3
    assert abs(minimum_radius - metrics["additional_metrics"]["minimum_curvature_radius_m"]) < 1e-6
    return {"route_count": len(rows), "length_m": exact_sum, "minimum_radius_m": minimum_radius}


def main() -> None:
    result = {
        "problem1": problem1(),
        "problem2": problem2(),
        "problem3": problem3(),
        "problem4_audit": audit_problem4(),
    }
    (ROOT / "reproduced_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["problem3"], ensure_ascii=False, indent=2))
    print(json.dumps(result["problem4_audit"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
