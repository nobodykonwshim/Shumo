#!/usr/bin/env python3
"""Deterministic spatial evaluator for case001 problem 4.

Input CSV format:
- first row: label followed by x coordinates in nautical miles;
- first column: y coordinates in nautical miles;
- remaining cells: positive water depths in metres.

The evaluator divides the rectangular region into equal-width vertical bands.
Inside each band it generates east-west survey segments. Local multibeam
half-widths are computed from water depth and the north-south depth gradient.
The first segment covers the southern boundary; each later segment uses the
largest spacing whose minimum ordered overlap is the requested target.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np

NM_TO_M = 1852.0


@dataclass
class Terrain:
    x_nm: np.ndarray
    y_nm: np.ndarray
    depth_m: np.ndarray
    ddepth_dx: np.ndarray
    ddepth_dy: np.ndarray


@dataclass
class SegmentFamily:
    band_id: int
    x0_nm: float
    x1_nm: float
    y_positions_m: list[float]
    profiles: list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]]
    over20_length_m: float


def load_terrain(path: Path) -> Terrain:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    if len(rows) < 3 or len(rows[0]) < 3:
        raise ValueError("terrain CSV is too small")
    x_nm = np.asarray([float(v) for v in rows[0][1:]], dtype=float)
    y_nm = np.asarray([float(row[0]) for row in rows[1:]], dtype=float)
    depth_m = np.asarray([[float(v) for v in row[1:]] for row in rows[1:]], dtype=float)
    if depth_m.shape != (len(y_nm), len(x_nm)):
        raise ValueError("coordinate and depth dimensions do not match")
    if np.isnan(depth_m).any() or (depth_m <= 0).any():
        raise ValueError("depth grid contains missing or non-positive values")
    dx_m = float(np.median(np.diff(x_nm))) * NM_TO_M
    dy_m = float(np.median(np.diff(y_nm))) * NM_TO_M
    ddepth_dy, ddepth_dx = np.gradient(depth_m, dy_m, dx_m)
    return Terrain(x_nm, y_nm, depth_m, ddepth_dx, ddepth_dy)


def beam_halves(depth_m: np.ndarray, cross_gradient: np.ndarray, opening_angle_deg: float) -> tuple[np.ndarray, np.ndarray]:
    tan_half = math.tan(math.radians(opening_angle_deg / 2.0))
    den_negative = 1.0 + cross_gradient * tan_half
    den_positive = 1.0 - cross_gradient * tan_half
    if np.any(den_negative <= 0) or np.any(den_positive <= 0):
        raise ValueError("local slope is outside the beam-intersection validity range")
    negative_half = depth_m * tan_half / den_negative
    positive_half = depth_m * tan_half / den_positive
    return negative_half, positive_half


def interpolate_rows(field: np.ndarray, y_nm: np.ndarray, y_pos_nm: float, i0: int, i1: int) -> np.ndarray:
    if y_pos_nm <= y_nm[0]:
        return field[0, i0 : i1 + 1].copy()
    if y_pos_nm >= y_nm[-1]:
        return field[-1, i0 : i1 + 1].copy()
    j = int(np.searchsorted(y_nm, y_pos_nm) - 1)
    fraction = (y_pos_nm - y_nm[j]) / (y_nm[j + 1] - y_nm[j])
    return (1.0 - fraction) * field[j, i0 : i1 + 1] + fraction * field[j + 1, i0 : i1 + 1]


def bisect_root(func, lower: float, upper: float, tolerance: float = 1e-7, max_iterations: int = 100) -> float:
    f_lower = float(func(lower))
    f_upper = float(func(upper))
    if f_lower == 0:
        return lower
    if f_upper == 0:
        return upper
    if f_lower * f_upper > 0:
        raise ValueError(f"root is not bracketed: {f_lower}, {f_upper}")
    for _ in range(max_iterations):
        middle = (lower + upper) / 2.0
        f_middle = float(func(middle))
        if abs(f_middle) < 1e-12 or upper - lower < tolerance:
            return middle
        if f_lower * f_middle <= 0:
            upper = middle
            f_upper = f_middle
        else:
            lower = middle
            f_lower = f_middle
    return (lower + upper) / 2.0


def build_horizontal_band(
    terrain: Terrain,
    band_id: int,
    x0_nm: float,
    x1_nm: float,
    target_overlap: float,
    opening_angle_deg: float,
) -> SegmentFamily:
    i0 = int(np.argmin(np.abs(terrain.x_nm - x0_nm)))
    i1 = int(np.argmin(np.abs(terrain.x_nm - x1_nm)))
    south_m = float(terrain.y_nm[0] * NM_TO_M)
    north_m = float(terrain.y_nm[-1] * NM_TO_M)

    def profile(y_position_m: float):
        y_position_nm = y_position_m / NM_TO_M
        depth = interpolate_rows(terrain.depth_m, terrain.y_nm, y_position_nm, i0, i1)
        gradient = interpolate_rows(terrain.ddepth_dy, terrain.y_nm, y_position_nm, i0, i1)
        negative_half, positive_half = beam_halves(depth, gradient, opening_angle_deg)
        return depth, gradient, negative_half, positive_half

    def first_boundary_residual(y_position_m: float) -> float:
        negative_half = profile(y_position_m)[2]
        return float(np.max(y_position_m - negative_half - south_m))

    lower = south_m
    upper = min(north_m, south_m + 1000.0)
    while first_boundary_residual(upper) < 0 and upper < north_m:
        upper = min(north_m, south_m + 1.5 * (upper - south_m) + 10.0)
    first = bisect_root(first_boundary_residual, lower, upper)

    positions = [first]
    profiles = [profile(first)]
    while float(np.min(positions[-1] + profiles[-1][3])) < north_m:
        previous_position = positions[-1]
        previous_profile = profiles[-1]

        def minimum_overlap(candidate: float) -> float:
            current = profile(candidate)
            separation = candidate - previous_position
            eta = (previous_profile[3] + current[2] - separation) / (current[2] + current[3])
            return float(np.min(eta))

        lower = previous_position + 1e-6
        upper = lower + 5.0
        while minimum_overlap(upper) >= target_overlap:
            lower = upper
            upper += 5.0
            if upper > north_m + 1000.0:
                raise RuntimeError("failed to bracket next survey segment")
        next_position = bisect_root(lambda value: minimum_overlap(value) - target_overlap, lower, upper)
        positions.append(next_position)
        profiles.append(profile(next_position))
        if len(positions) > 5000:
            raise RuntimeError("segment construction exceeded safety limit")

    along_m = terrain.x_nm[i0 : i1 + 1] * NM_TO_M
    over20_length_m = 0.0
    for index in range(1, len(positions)):
        previous = profiles[index - 1]
        current = profiles[index]
        separation = positions[index] - positions[index - 1]
        eta = (previous[3] + current[2] - separation) / (current[2] + current[3])
        midpoint_eta = (eta[:-1] + eta[1:]) / 2.0
        over20_length_m += float(np.diff(along_m)[midpoint_eta > 0.20].sum())

    return SegmentFamily(band_id, x0_nm, x1_nm, positions, profiles, over20_length_m)


def evaluate_cells(terrain: Terrain, families: Iterable[SegmentFamily]) -> dict:
    x_centres = (terrain.x_nm[:-1] + terrain.x_nm[1:]) / 2.0
    y_centres = (terrain.y_nm[:-1] + terrain.y_nm[1:]) / 2.0
    coverage = np.zeros((len(y_centres), len(x_centres)), dtype=np.int16)
    total_length_m = 0.0
    total_segments = 0
    total_over20_m = 0.0

    for family in families:
        i0 = int(np.argmin(np.abs(terrain.x_nm - family.x0_nm)))
        i1 = int(np.argmin(np.abs(terrain.x_nm - family.x1_nm)))
        columns = np.where((x_centres >= family.x0_nm - 1e-12) & (x_centres <= family.x1_nm + 1e-12))[0]
        x_nodes = terrain.x_nm[i0 : i1 + 1]
        y_m = y_centres * NM_TO_M
        for position, profile in zip(family.y_positions_m, family.profiles):
            negative_half = np.interp(x_centres[columns], x_nodes, profile[2])
            positive_half = np.interp(x_centres[columns], x_nodes, profile[3])
            lower = position - negative_half
            upper = position + positive_half
            for local_index, column in enumerate(columns):
                coverage[:, column] += ((y_m >= lower[local_index] - 1e-8) & (y_m <= upper[local_index] + 1e-8)).astype(np.int16)
        segment_length_m = (family.x1_nm - family.x0_nm) * NM_TO_M
        total_length_m += len(family.y_positions_m) * segment_length_m
        total_segments += len(family.y_positions_m)
        total_over20_m += family.over20_length_m

    return {
        "uncovered_area_percent": float(np.mean(coverage == 0) * 100.0),
        "single_covered_area_percent": float(np.mean(coverage == 1) * 100.0),
        "multi_covered_area_percent": float(np.mean(coverage >= 2) * 100.0),
        "maximum_coverage_count": int(np.max(coverage)),
        "total_line_length_m": float(total_length_m),
        "over_20_percent_overlap_length_m": float(total_over20_m),
        "segment_count": int(total_segments),
    }


def write_lines(path: Path, families: Iterable[SegmentFamily]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["segment_id", "band_id", "x_start_nm", "y_start_nm", "x_end_nm", "y_end_nm", "length_m"])
        segment_id = 1
        for family in families:
            length_m = (family.x1_nm - family.x0_nm) * NM_TO_M
            for y_position_m in family.y_positions_m:
                writer.writerow([
                    segment_id,
                    family.band_id,
                    f"{family.x0_nm:.6f}",
                    f"{y_position_m / NM_TO_M:.9f}",
                    f"{family.x1_nm:.6f}",
                    f"{y_position_m / NM_TO_M:.9f}",
                    f"{length_m:.6f}",
                ])
                segment_id += 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--terrain-csv", required=True, type=Path)
    parser.add_argument("--bands", type=int, default=4)
    parser.add_argument("--target-overlap", type=float, default=0.10)
    parser.add_argument("--opening-angle", type=float, default=120.0)
    parser.add_argument("--output-dir", required=True, type=Path)
    arguments = parser.parse_args()
    if arguments.bands < 1:
        raise SystemExit("--bands must be positive")
    if not 0 <= arguments.target_overlap < 1:
        raise SystemExit("--target-overlap must be in [0,1)")

    terrain = load_terrain(arguments.terrain_csv)
    cuts = np.linspace(float(terrain.x_nm[0]), float(terrain.x_nm[-1]), arguments.bands + 1)
    families = [
        build_horizontal_band(
            terrain,
            index + 1,
            float(cuts[index]),
            float(cuts[index + 1]),
            arguments.target_overlap,
            arguments.opening_angle,
        )
        for index in range(arguments.bands)
    ]
    metrics = evaluate_cells(terrain, families)
    metrics.update({
        "bands": arguments.bands,
        "target_overlap": arguments.target_overlap,
        "opening_angle_degree": arguments.opening_angle,
        "terrain_shape": [int(terrain.depth_m.shape[0]), int(terrain.depth_m.shape[1])],
    })
    arguments.output_dir.mkdir(parents=True, exist_ok=True)
    write_lines(arguments.output_dir / "problem4_lines.csv", families)
    with (arguments.output_dir / "problem4_metrics.json").open("w", encoding="utf-8") as handle:
        json.dump(metrics, handle, ensure_ascii=False, indent=2, sort_keys=True)
    print(json.dumps(metrics, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
