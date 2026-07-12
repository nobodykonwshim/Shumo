#!/usr/bin/env python3
"""Generate the three bounded case001 problem-4 candidate families.

This is a candidate artifact, not an evaluator. It never reads reference papers,
never selects a winner and never changes the frozen evaluator settings.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Sequence


def load_spatial(module_path: Path):
    spec = importlib.util.spec_from_file_location("case001_spatial_coverage", module_path)
    if not spec or not spec.loader:
        raise RuntimeError(f"Cannot load evaluator module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def linspace(start: float, stop: float, count: int) -> list[float]:
    if count == 1:
        return [start]
    return [start + (stop - start) * i / (count - 1) for i in range(count)]


def interpolate(values: Sequence[float], t: float) -> float:
    if len(values) == 1:
        return float(values[0])
    position = t * (len(values) - 1)
    index = min(int(position), len(values) - 2)
    fraction = position - index
    return float(values[index] * (1 - fraction) + values[index + 1] * fraction)


def swath_bounds(spatial, terrain, q: float, along: float, orientation: str):
    if orientation == "vertical":
        swath = spatial._swath_at(terrain, q, along, 0.0, 1.0, 120.0)
    else:
        swath = spatial._swath_at(terrain, along, q, 1.0, 0.0, 120.0)
    return q - swath.left_m, q + swath.right_m, swath.width_m


def place_parallel(
    spatial,
    terrain,
    orientation: str,
    along_min: float,
    along_max: float,
    cross_min: float,
    cross_max: float,
    target_overlap: float,
    sample_count: int,
) -> list[float]:
    along_values = linspace(along_min, along_max, sample_count)

    def first_line_ok(q: float) -> bool:
        return max(
            swath_bounds(spatial, terrain, q, along, orientation)[0]
            for along in along_values
        ) <= cross_min + 1e-9

    low, high = cross_min, cross_max
    for _ in range(60):
        middle = (low + high) / 2
        if first_line_ok(middle):
            low = middle
        else:
            high = middle
    positions = [low]

    for _ in range(500):
        previous = positions[-1]
        previous_upper = [
            swath_bounds(spatial, terrain, previous, along, orientation)[1]
            for along in along_values
        ]
        if min(previous_upper) >= cross_max - 1e-6:
            return positions

        def minimum_overlap(q: float) -> float:
            values = []
            for upper, along in zip(previous_upper, along_values):
                current_lower, _, current_width = swath_bounds(
                    spatial, terrain, q, along, orientation
                )
                values.append((upper - current_lower) / current_width)
            return min(values)

        low = previous + 1e-6
        high = cross_max
        if minimum_overlap(low) < target_overlap:
            raise RuntimeError("No feasible next line after the previous line")
        if minimum_overlap(high) >= target_overlap:
            next_position = high
        else:
            for _ in range(60):
                middle = (low + high) / 2
                if minimum_overlap(middle) >= target_overlap:
                    low = middle
                else:
                    high = middle
            next_position = low
        if next_position - previous < 1e-4:
            raise RuntimeError("Line placement stalled")
        positions.append(next_position)
    raise RuntimeError("Line placement exceeded 500 lines")


def place_at_station(spatial, terrain, y: float, target_overlap: float) -> list[float]:
    return place_parallel(
        spatial, terrain, "vertical", y, y, 0.0, 7408.0, target_overlap, 1
    )


def candidate_payload(
    candidate_id,
    route_family,
    lines,
    assumptions,
    tradeoffs,
    limitations,
    terrain_file,
    gate_token,
):
    return {
        "admission_id": "ADM-P4-ROUTE-001",
        "assumptions": assumptions,
        "candidate_id": candidate_id,
        "evaluation": {
            "along_step_m": 150.0,
            "cross_track_samples": 31,
            "grid_nx": 50,
            "grid_ny": 60,
            "overlap_length_policy": "ordered_previous_line",
            "overlap_threshold": 0.2,
            "sensitivity_grid_sizes": [30, 50, 70],
        },
        "expected_tradeoffs": tradeoffs,
        "gate_token_sha256": gate_token,
        "instrument": {"opening_angle_deg": 120.0},
        "limitations": limitations,
        "lines": lines,
        "reference_access": "quarantined",
        "region": {"xmax": 7408.0, "xmin": 0.0, "ymax": 9260.0, "ymin": 0.0},
        "route_family": route_family,
        "schema_version": 1,
        "task_id": "A-P4-ROUTE-01",
        "terrain_file": terrain_file,
    }


def generate(spatial, terrain, terrain_file: str, gate_token: str):
    target = 0.10
    vertical = place_parallel(
        spatial, terrain, "vertical", 0.0, 9260.0, 0.0, 7408.0, target, 151
    )
    horizontal = place_parallel(
        spatial, terrain, "horizontal", 0.0, 7408.0, 0.0, 9260.0, target, 151
    )

    station_y = linspace(0.0, 9260.0, 11)
    station_positions = [place_at_station(spatial, terrain, y, target) for y in station_y]
    line_count = max(len(positions) for positions in station_positions)
    curves = [[] for _ in range(line_count)]
    for y, positions in zip(station_y, station_positions):
        for index, t in enumerate(linspace(0.0, 1.0, line_count)):
            curves[index].append([interpolate(positions, t), y])

    return [
        candidate_payload(
            "P4-CAND-A",
            "global_north_south_conservative_adaptive",
            [
                {"id": f"A-{i+1:03d}", "points": [[q, 0.0], [q, 9260.0]]}
                for i, q in enumerate(vertical)
            ],
            [
                "Use one global north-south orientation.",
                "Place each next line at the largest spacing whose minimum sampled overlap with the previous line is 10% across the full north-south extent.",
            ],
            [
                "Simple ordered adjacency and full-height implementation.",
                "Conservative worst-case spacing may create excess overlap and extra length where terrain is deeper.",
            ],
            [
                "No proof of global optimality.",
                "Line placement uses sampled along-track terrain rather than continuous extrema.",
            ],
            terrain_file,
            gate_token,
        ),
        candidate_payload(
            "P4-CAND-B",
            "global_east_west_conservative_adaptive",
            [
                {"id": f"B-{i+1:03d}", "points": [[0.0, q], [7408.0, q]]}
                for i, q in enumerate(horizontal)
            ],
            [
                "Use one global east-west orientation.",
                "Place each next line at the largest spacing whose minimum sampled overlap with the previous line is 10% across the full east-west extent.",
            ],
            [
                "Tests the orthogonal global orientation independently.",
                "May exploit north-south terrain structure differently but uses more cross-region traversals.",
            ],
            [
                "No proof of global optimality.",
                "Line placement uses sampled along-track terrain rather than continuous extrema.",
            ],
            terrain_file,
            gate_token,
        ),
        candidate_payload(
            "P4-CAND-C",
            "terrain_responsive_curved_north_south",
            [
                {"id": f"C-{i+1:03d}", "points": points}
                for i, points in enumerate(curves)
            ],
            [
                "At 11 north-south stations, independently construct west-to-east line positions with 10% local ordered overlap.",
                "Interpolate normalized line indices across stations to form non-crossing curved polylines.",
            ],
            [
                "Adapts line density and shape to local terrain.",
                "Curvature increases line length and interpolation may create local coverage or overlap artifacts.",
            ],
            [
                "No vessel-turning or curvature constraint is modeled.",
                "No proof of global optimality.",
                "The fixed line count is the maximum stationwise count.",
            ],
            terrain_file,
            gate_token,
        ),
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--terrain", required=True, type=Path)
    parser.add_argument("--evaluator", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--terrain-file-in-config",
        default="../../local/generated/attachment_terrain.json",
    )
    parser.add_argument("--gate-token", required=True)
    args = parser.parse_args()

    spatial = load_spatial(args.evaluator)
    bundle = json.loads(args.terrain.read_text(encoding="utf-8"))
    terrain = spatial._parse_terrain(bundle["terrain"])
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for candidate in generate(
        spatial, terrain, args.terrain_file_in_config, args.gate_token
    ):
        path = args.output_dir / f"{candidate['candidate_id']}.json"
        path.write_text(
            json.dumps(candidate, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
