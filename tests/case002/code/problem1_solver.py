#!/usr/bin/env python3
"""Solve 2025 CUMCM A problem 1 with a full-cylinder occlusion test.

The primary predicate requires the smoke sphere to intersect every segment from
missile M1 to every point of the true cylindrical target.  A target-centre
line-of-sight predicate is reported only as a looser comparison.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from scipy.optimize import brentq


@dataclass(frozen=True)
class Parameters:
    missile_initial_m: tuple[float, float, float] = (20000.0, 0.0, 2000.0)
    missile_speed_m_per_s: float = 300.0
    uav_initial_m: tuple[float, float, float] = (17800.0, 0.0, 1800.0)
    uav_speed_m_per_s: float = 120.0
    release_time_s: float = 1.5
    burst_delay_s: float = 3.6
    gravity_m_per_s2: float = 9.8
    smoke_radius_m: float = 10.0
    smoke_settling_speed_m_per_s: float = 3.0
    smoke_active_duration_s: float = 20.0
    target_bottom_center_m: tuple[float, float, float] = (0.0, 200.0, 0.0)
    target_radius_m: float = 7.0
    target_height_m: float = 10.0


@dataclass(frozen=True)
class Mesh:
    name: str
    theta_count: int
    vertical_count: int
    radial_count: int


MESHES = (
    Mesh("coarse", 180, 17, 17),
    Mesh("standard", 360, 31, 31),
    Mesh("fine", 720, 61, 61),
)


def missile_position(t_s: float, p: Parameters) -> np.ndarray:
    initial = np.asarray(p.missile_initial_m, dtype=float)
    direction = -initial / np.linalg.norm(initial)
    return initial + p.missile_speed_m_per_s * t_s * direction


def uav_position(t_s: float, p: Parameters) -> np.ndarray:
    initial = np.asarray(p.uav_initial_m, dtype=float)
    return initial + np.array([-p.uav_speed_m_per_s * t_s, 0.0, 0.0])


def burst_time(p: Parameters) -> float:
    return p.release_time_s + p.burst_delay_s


def bomb_position(t_s: float, p: Parameters) -> np.ndarray:
    if t_s < p.release_time_s:
        raise ValueError("bomb motion is only defined after release")
    tau = t_s - p.release_time_s
    return uav_position(p.release_time_s, p) + np.array(
        [-p.uav_speed_m_per_s * tau, 0.0, -0.5 * p.gravity_m_per_s2 * tau**2]
    )


def smoke_center(t_s: float, p: Parameters) -> np.ndarray:
    t_burst = burst_time(p)
    if not (t_burst <= t_s <= t_burst + p.smoke_active_duration_s):
        raise ValueError("smoke center requested outside its active interval")
    center = bomb_position(t_burst, p).copy()
    center[2] -= p.smoke_settling_speed_m_per_s * (t_s - t_burst)
    return center


def cylinder_boundary_points(mesh: Mesh, p: Parameters) -> np.ndarray:
    """Sample side and both caps; duplicated rim points are harmless."""
    theta = np.linspace(0.0, 2.0 * np.pi, mesh.theta_count, endpoint=False)
    cos_theta = np.cos(theta)
    sin_theta = np.sin(theta)
    bottom = np.asarray(p.target_bottom_center_m, dtype=float)

    z_values = np.linspace(0.0, p.target_height_m, mesh.vertical_count)
    theta_side, z_side = np.meshgrid(theta, z_values, indexing="ij")
    side = np.column_stack(
        (
            bottom[0] + p.target_radius_m * np.cos(theta_side).ravel(),
            bottom[1] + p.target_radius_m * np.sin(theta_side).ravel(),
            bottom[2] + z_side.ravel(),
        )
    )

    radii = np.linspace(0.0, p.target_radius_m, mesh.radial_count)
    theta_cap, radius_cap = np.meshgrid(theta, radii, indexing="ij")
    cap_xy = np.column_stack(
        (
            bottom[0] + radius_cap.ravel() * np.cos(theta_cap).ravel(),
            bottom[1] + radius_cap.ravel() * np.sin(theta_cap).ravel(),
        )
    )
    lower = np.column_stack((cap_xy, np.full(cap_xy.shape[0], bottom[2])))
    upper = np.column_stack(
        (cap_xy, np.full(cap_xy.shape[0], bottom[2] + p.target_height_m))
    )
    return np.vstack((side, lower, upper))


def distances_to_sight_segments(
    smoke: np.ndarray, missile: np.ndarray, target_points: np.ndarray
) -> np.ndarray:
    segment = target_points - missile
    smoke_from_missile = smoke - missile
    denominator = np.einsum("ij,ij->i", segment, segment)
    fraction = np.einsum("ij,j->i", segment, smoke_from_missile) / denominator
    fraction = np.clip(fraction, 0.0, 1.0)
    nearest = missile + fraction[:, None] * segment
    return np.linalg.norm(smoke - nearest, axis=1)


def full_target_max_distance(
    t_s: float, target_points: np.ndarray, p: Parameters
) -> tuple[float, np.ndarray]:
    distances = distances_to_sight_segments(
        smoke_center(t_s, p), missile_position(t_s, p), target_points
    )
    index = int(np.argmax(distances))
    return float(distances[index]), target_points[index]


def centre_line_distance(t_s: float, p: Parameters) -> float:
    bottom = np.asarray(p.target_bottom_center_m, dtype=float)
    target_centre = bottom + np.array([0.0, 0.0, 0.5 * p.target_height_m])
    return float(
        distances_to_sight_segments(
            smoke_center(t_s, p), missile_position(t_s, p), target_centre[None, :]
        )[0]
    )


def find_positive_intervals(
    margin: Callable[[float], float], start_s: float, end_s: float, scan_step_s: float
) -> list[tuple[float, float]]:
    count = int(np.ceil((end_s - start_s) / scan_step_s))
    times = np.linspace(start_s, end_s, count + 1)
    values = np.asarray([margin(float(t)) for t in times])
    roots: list[float] = []
    for index in range(len(times) - 1):
        left_value = values[index]
        right_value = values[index + 1]
        if left_value == 0.0:
            roots.append(float(times[index]))
        if left_value * right_value < 0.0:
            roots.append(
                float(
                    brentq(
                        margin,
                        float(times[index]),
                        float(times[index + 1]),
                        xtol=1.0e-11,
                        rtol=1.0e-13,
                    )
                )
            )
    if values[-1] == 0.0:
        roots.append(float(times[-1]))

    boundaries = [start_s] + sorted(set(round(root, 12) for root in roots)) + [end_s]
    intervals: list[tuple[float, float]] = []
    for left, right in zip(boundaries[:-1], boundaries[1:]):
        midpoint = 0.5 * (left + right)
        if margin(midpoint) >= 0.0:
            intervals.append((left, right))
    return intervals


def sole_interval(intervals: list[tuple[float, float]], label: str) -> tuple[float, float]:
    if len(intervals) != 1:
        raise RuntimeError(f"expected one {label} interval, received {intervals}")
    return intervals[0]


def solve(p: Parameters, scan_step_s: float = 0.02) -> dict:
    t_burst = burst_time(p)
    active_end = t_burst + p.smoke_active_duration_s
    release = uav_position(p.release_time_s, p)
    burst = bomb_position(t_burst, p)

    convergence = []
    mesh_intervals: dict[str, tuple[float, float]] = {}
    previous_duration = None
    for mesh in MESHES:
        target_points = cylinder_boundary_points(mesh, p)

        def full_margin(t_s: float) -> float:
            maximum, _ = full_target_max_distance(t_s, target_points, p)
            return p.smoke_radius_m - maximum

        interval = sole_interval(
            find_positive_intervals(full_margin, t_burst, active_end, scan_step_s),
            f"full-target/{mesh.name}",
        )
        mesh_intervals[mesh.name] = interval
        duration = interval[1] - interval[0]
        convergence.append(
            {
                **asdict(mesh),
                "boundary_point_count": int(target_points.shape[0]),
                "start_s": interval[0],
                "end_s": interval[1],
                "duration_s": duration,
                "duration_change_from_previous_s": (
                    None if previous_duration is None else duration - previous_duration
                ),
            }
        )
        previous_duration = duration

    standard_points = cylinder_boundary_points(MESHES[1], p)

    def standard_margin(t_s: float) -> float:
        maximum, _ = full_target_max_distance(t_s, standard_points, p)
        return p.smoke_radius_m - maximum

    scan_convergence = []
    scan_intervals: dict[float, tuple[float, float]] = {
        scan_step_s: mesh_intervals[MESHES[1].name]
    }
    for step in (0.05, 0.01):
        scan_intervals[step] = sole_interval(
            find_positive_intervals(standard_margin, t_burst, active_end, step),
            f"time-scan/{step}",
        )
    for step in (0.05, scan_step_s, 0.01):
        interval = scan_intervals[step]
        scan_convergence.append(
            {
                "scan_step_s": step,
                "start_s": interval[0],
                "end_s": interval[1],
                "duration_s": interval[1] - interval[0],
            }
        )

    fine_mesh = MESHES[-1]
    fine_points = cylinder_boundary_points(fine_mesh, p)
    full_start, full_end = mesh_intervals[fine_mesh.name]
    start_distance, start_worst = full_target_max_distance(full_start, fine_points, p)
    end_distance, end_worst = full_target_max_distance(full_end, fine_points, p)

    centre_interval = sole_interval(
        find_positive_intervals(
            lambda t_s: p.smoke_radius_m - centre_line_distance(t_s, p),
            t_burst,
            active_end,
            scan_step_s,
        ),
        "target-centre line-of-sight",
    )
    full_duration = full_end - full_start
    centre_duration = centre_interval[1] - centre_interval[0]
    convergence_change = abs(
        convergence[-1]["duration_s"] - convergence[-2]["duration_s"]
    )
    scan_duration_change = max(item["duration_s"] for item in scan_convergence) - min(
        item["duration_s"] for item in scan_convergence
    )

    report = {
        "schema_version": 1,
        "project_id": "case002",
        "problem_id": "problem1",
        "method": {
            "primary_predicate": "max over full cylindrical target of distance from smoke centre to missile-target sight segment <= smoke radius",
            "comparison_predicate": "distance from smoke centre to missile-target-geometric-centre sight segment <= smoke radius",
            "scan_step_s": scan_step_s,
            "root_method": "Brent bracketing root refinement",
            "root_xtol_s": 1.0e-11,
            "target_surface_sampling": "cylinder side plus both circular caps",
        },
        "parameters": asdict(p),
        "hand_calculation": {
            "release_point_m": release.tolist(),
            "burst_absolute_time_s": t_burst,
            "burst_point_m": burst.tolist(),
            "smoke_active_interval_s": [t_burst, active_end],
        },
        "full_cylinder": {
            "start_s": full_start,
            "end_s": full_end,
            "duration_s": full_duration,
            "boundary_distance_at_start_m": start_distance,
            "boundary_distance_at_end_m": end_distance,
            "worst_target_point_at_start_m": start_worst.tolist(),
            "worst_target_point_at_end_m": end_worst.tolist(),
        },
        "target_centre_line_of_sight": {
            "target_point_m": [0.0, 200.0, 5.0],
            "start_s": centre_interval[0],
            "end_s": centre_interval[1],
            "duration_s": centre_duration,
        },
        "comparison": {
            "centre_minus_full_duration_s": centre_duration - full_duration,
            "full_to_centre_duration_ratio": full_duration / centre_duration,
        },
        "mesh_convergence": convergence,
        "time_scan_convergence": scan_convergence,
        "validation": {
            "release_point_hand_check_pass": bool(
                np.allclose(release, np.array([17620.0, 0.0, 1800.0]), atol=1.0e-12)
            ),
            "burst_time_hand_check_pass": bool(abs(t_burst - 5.1) <= 1.0e-12),
            "burst_point_hand_check_pass": bool(
                np.allclose(burst, np.array([17188.0, 0.0, 1736.496]), atol=1.0e-9)
            ),
            "inside_active_window_pass": bool(
                t_burst <= full_start <= full_end <= active_end
            ),
            "mesh_duration_change_below_0_001_s_pass": bool(convergence_change < 0.001),
            "mesh_duration_change_s": convergence_change,
            "scan_duration_change_below_0_001_s_pass": bool(scan_duration_change < 0.001),
            "scan_duration_change_s": scan_duration_change,
            "full_duration_not_above_centre_pass": bool(full_duration <= centre_duration),
            "boundary_residual_max_m": max(
                abs(start_distance - p.smoke_radius_m),
                abs(end_distance - p.smoke_radius_m),
            ),
            "all_required_checks_pass": False,
        },
    }
    checks = report["validation"]
    checks["all_required_checks_pass"] = all(
        checks[key]
        for key in (
            "release_point_hand_check_pass",
            "burst_time_hand_check_pass",
            "burst_point_hand_check_pass",
            "inside_active_window_pass",
            "mesh_duration_change_below_0_001_s_pass",
            "scan_duration_change_below_0_001_s_pass",
            "full_duration_not_above_centre_pass",
        )
    ) and checks["boundary_residual_max_m"] < 1.0e-7
    if not checks["all_required_checks_pass"]:
        raise RuntimeError(f"problem 1 validation failed: {checks}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scan-step", type=float, default=0.02)
    args = parser.parse_args()
    if args.scan_step <= 0:
        parser.error("--scan-step must be positive")
    report = solve(Parameters(), scan_step_s=args.scan_step)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
