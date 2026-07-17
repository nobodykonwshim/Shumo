#!/usr/bin/env python3
"""Solve 2025 CUMCM A problem 1 with the cylinder-silhouette edge test."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import yaml
from scipy.optimize import brentq


@dataclass(frozen=True)
class Parameters:
    missile_initial_m: tuple[float, float, float]
    fake_target_m: tuple[float, float, float]
    missile_speed_m_per_s: float
    uav_initial_m: tuple[float, float, float]
    uav_direction: tuple[float, float, float]
    uav_speed_m_per_s: float
    release_time_s: float
    burst_delay_s: float
    gravity_m_per_s2: float
    smoke_radius_m: float
    smoke_settling_speed_m_per_s: float
    smoke_active_duration_s: float
    target_bottom_center_m: tuple[float, float, float]
    target_radius_m: float
    target_height_m: float


PARAMETER_IDS = {
    "missile_initial_m": "PAR-M1-P0",
    "fake_target_m": "PAR-FAKE-TARGET",
    "missile_speed_m_per_s": "PAR-MISSILE-SPEED",
    "uav_initial_m": "PAR-FY1-P0",
    "uav_direction": "PAR-FY1-DIRECTION",
    "uav_speed_m_per_s": "PAR-FY1-P1-SPEED",
    "release_time_s": "PAR-P1-RELEASE-TIME",
    "burst_delay_s": "PAR-P1-BURST-DELAY",
    "gravity_m_per_s2": "PAR-GRAVITY",
    "smoke_radius_m": "PAR-SMOKE-RADIUS",
    "smoke_settling_speed_m_per_s": "PAR-SMOKE-SETTLING-SPEED",
    "smoke_active_duration_s": "PAR-SMOKE-ACTIVE-DURATION",
    "target_bottom_center_m": "PAR-TARGET-BOTTOM-CENTER",
    "target_radius_m": "PAR-TARGET-RADIUS",
    "target_height_m": "PAR-TARGET-HEIGHT",
}

VECTOR_FIELDS = {
    "missile_initial_m",
    "fake_target_m",
    "uav_initial_m",
    "uav_direction",
    "target_bottom_center_m",
}

REQUIRED_ASSUMPTION_IDS = {
    "A-P1-MISSILE-UNIFORM",
    "A-P1-UAV-UNIFORM",
    "A-P1-BALLISTIC",
    "A-P1-NO-DRIFT",
    "A-P1-SPHERE",
    "A-P1-TARGET-CYLINDER",
    "A-P1-EDGE-SILHOUETTE",
}


def load_yaml_mapping(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"registry root must be a mapping: {path}")
    return data


def load_parameters(path: Path) -> Parameters:
    registry = load_yaml_mapping(path)
    entries = registry.get("parameters")
    if not isinstance(entries, list):
        raise ValueError(f"parameter registry has no parameters list: {path}")
    by_id = {entry.get("id"): entry.get("value") for entry in entries}
    missing = sorted(set(PARAMETER_IDS.values()) - set(by_id))
    if missing:
        raise ValueError(f"parameter registry is missing ids: {missing}")

    values: dict[str, object] = {}
    for field, parameter_id in PARAMETER_IDS.items():
        raw = by_id[parameter_id]
        if field in VECTOR_FIELDS:
            if not isinstance(raw, list) or len(raw) != 3:
                raise ValueError(f"{parameter_id} must be a three-vector")
            values[field] = tuple(float(value) for value in raw)
        else:
            values[field] = float(raw)
    return Parameters(**values)


def load_assumption_ids(path: Path) -> list[str]:
    registry = load_yaml_mapping(path)
    entries = registry.get("assumptions")
    if not isinstance(entries, list):
        raise ValueError(f"assumption registry has no assumptions list: {path}")
    accepted = {
        entry.get("id")
        for entry in entries
        if entry.get("status") == "accepted" and isinstance(entry.get("id"), str)
    }
    missing = sorted(REQUIRED_ASSUMPTION_IDS - accepted)
    if missing:
        raise ValueError(f"required assumptions are not accepted: {missing}")
    return sorted(REQUIRED_ASSUMPTION_IDS)


@dataclass(frozen=True)
class Resolution:
    name: str
    arc_count: int
    line_count: int


RESOLUTIONS = (
    Resolution("coarse", 181, 41),
    Resolution("standard", 361, 81),
    Resolution("fine", 721, 161),
)


def unit(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    if norm == 0.0:
        raise ValueError("zero vector has no direction")
    return vector / norm


def missile_position(t_s: float, p: Parameters) -> np.ndarray:
    initial = np.asarray(p.missile_initial_m, dtype=float)
    direction = unit(np.asarray(p.fake_target_m, dtype=float) - initial)
    return initial + p.missile_speed_m_per_s * t_s * direction


def uav_position(t_s: float, p: Parameters) -> np.ndarray:
    initial = np.asarray(p.uav_initial_m, dtype=float)
    direction = unit(np.asarray(p.uav_direction, dtype=float))
    return initial + p.uav_speed_m_per_s * t_s * direction


def burst_time(p: Parameters) -> float:
    return p.release_time_s + p.burst_delay_s


def bomb_position(t_s: float, p: Parameters) -> np.ndarray:
    if t_s < p.release_time_s:
        raise ValueError("bomb motion is only defined after release")
    tau = t_s - p.release_time_s
    inherited_velocity = p.uav_speed_m_per_s * unit(
        np.asarray(p.uav_direction, dtype=float)
    )
    gravity = np.array([0.0, 0.0, -p.gravity_m_per_s2])
    return (
        uav_position(p.release_time_s, p)
        + inherited_velocity * tau
        + 0.5 * gravity * tau**2
    )


def smoke_center(t_s: float, p: Parameters) -> np.ndarray:
    t_burst = burst_time(p)
    active_end = t_burst + p.smoke_active_duration_s
    if not (t_burst <= t_s <= active_end):
        raise ValueError("smoke center requested outside its active interval")
    center = bomb_position(t_burst, p).copy()
    center[2] -= p.smoke_settling_speed_m_per_s * (t_s - t_burst)
    return center


def circle_points(
    bottom: np.ndarray,
    height_m: float,
    radius_m: float,
    radial: np.ndarray,
    transverse: np.ndarray,
    angles: np.ndarray,
) -> np.ndarray:
    horizontal = radius_m * (
        np.cos(angles)[:, None] * radial
        + np.sin(angles)[:, None] * transverse
    )
    points = bottom + horizontal
    points[:, 2] += height_m
    return points


def cylinder_silhouette_edges(
    t_s: float,
    resolution: Resolution,
    p: Parameters,
) -> dict[str, object]:
    """Return the exact two rim arcs and two side tangency generators."""
    missile = missile_position(t_s, p)
    bottom = np.asarray(p.target_bottom_center_m, dtype=float)
    vertical = np.array([0.0, 0.0, 1.0])
    horizontal_to_missile = missile - bottom
    horizontal_to_missile[2] = 0.0
    horizontal_distance = float(np.linalg.norm(horizontal_to_missile))
    if horizontal_distance <= p.target_radius_m:
        raise ValueError("missile horizontal projection lies inside the target cylinder")
    if missile[2] <= bottom[2] + p.target_height_m:
        raise ValueError("two-arc silhouette selection requires the missile above the cylinder")

    radial = horizontal_to_missile / horizontal_distance
    transverse = unit(np.cross(vertical, radial))
    tangent_angle = float(np.arccos(p.target_radius_m / horizontal_distance))

    top_far_angles = np.linspace(
        tangent_angle,
        2.0 * np.pi - tangent_angle,
        resolution.arc_count,
    )
    bottom_near_angles = np.linspace(
        -tangent_angle,
        tangent_angle,
        resolution.arc_count,
    )
    top_far = circle_points(
        bottom,
        p.target_height_m,
        p.target_radius_m,
        radial,
        transverse,
        top_far_angles,
    )
    bottom_near = circle_points(
        bottom,
        0.0,
        p.target_radius_m,
        radial,
        transverse,
        bottom_near_angles,
    )

    tangent_plus = circle_points(
        bottom,
        0.0,
        p.target_radius_m,
        radial,
        transverse,
        np.array([tangent_angle]),
    )[0]
    tangent_minus = circle_points(
        bottom,
        0.0,
        p.target_radius_m,
        radial,
        transverse,
        np.array([-tangent_angle]),
    )[0]
    heights = np.linspace(0.0, p.target_height_m, resolution.line_count)
    side_plus = tangent_plus + heights[:, None] * vertical
    side_minus = tangent_minus + heights[:, None] * vertical

    points = np.vstack((top_far, bottom_near, side_plus, side_minus))
    curve_names = np.concatenate(
        (
            np.full(top_far.shape[0], "top_far_arc", dtype=object),
            np.full(bottom_near.shape[0], "bottom_near_arc", dtype=object),
            np.full(side_plus.shape[0], "side_tangent_plus", dtype=object),
            np.full(side_minus.shape[0], "side_tangent_minus", dtype=object),
        )
    )

    tangent_offsets = np.vstack((tangent_plus - bottom, tangent_minus - bottom))
    tangent_rays = np.vstack(
        (
            missile[:2] - tangent_plus[:2],
            missile[:2] - tangent_minus[:2],
        )
    )
    tangency_residual = float(
        np.max(np.abs(np.einsum("ij,ij->i", tangent_rays, tangent_offsets[:, :2])))
    )
    radial_residual = float(
        np.max(
            np.abs(
                np.linalg.norm(points[:, :2] - bottom[:2], axis=1)
                - p.target_radius_m
            )
        )
    )

    return {
        "points": points,
        "curve_names": curve_names,
        "horizontal_distance_m": horizontal_distance,
        "tangent_angle_rad": tangent_angle,
        "radial_unit": radial,
        "transverse_unit": transverse,
        "tangency_residual_m2": tangency_residual,
        "cylinder_radial_residual_m": radial_residual,
    }


def distances_to_sight_segments(
    smoke: np.ndarray,
    missile: np.ndarray,
    target_points: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    sight = target_points - missile
    smoke_from_missile = smoke - missile
    denominator = np.einsum("ij,ij->i", sight, sight)
    raw_fraction = np.einsum("ij,j->i", sight, smoke_from_missile) / denominator
    fraction = np.clip(raw_fraction, 0.0, 1.0)
    nearest = missile + fraction[:, None] * sight
    return np.linalg.norm(smoke - nearest, axis=1), fraction


def edge_metrics(
    t_s: float,
    resolution: Resolution,
    p: Parameters,
) -> dict[str, object]:
    missile = missile_position(t_s, p)
    smoke = smoke_center(t_s, p)
    geometry = cylinder_silhouette_edges(t_s, resolution, p)
    points = geometry["points"]
    distances, fractions = distances_to_sight_segments(smoke, missile, points)
    worst_index = int(np.argmax(distances))
    return {
        "max_edge_segment_distance_m": float(distances[worst_index]),
        "worst_edge_point_m": points[worst_index],
        "worst_curve": str(geometry["curve_names"][worst_index]),
        "segment_fraction_at_worst": float(fractions[worst_index]),
        "edge_point_count": int(points.shape[0]),
        "horizontal_distance_m": geometry["horizontal_distance_m"],
        "tangent_angle_rad": geometry["tangent_angle_rad"],
        "tangency_residual_m2": geometry["tangency_residual_m2"],
        "cylinder_radial_residual_m": geometry["cylinder_radial_residual_m"],
    }


def find_positive_intervals(
    margin: Callable[[float], float],
    start_s: float,
    end_s: float,
    scan_step_s: float,
) -> list[tuple[float, float]]:
    count = int(np.ceil((end_s - start_s) / scan_step_s))
    times = np.linspace(start_s, end_s, count + 1)
    values = np.asarray([margin(float(t)) for t in times])
    roots: list[float] = []
    for index in range(len(times) - 1):
        if values[index] == 0.0:
            roots.append(float(times[index]))
        if values[index] * values[index + 1] < 0.0:
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
        if margin(0.5 * (left + right)) >= 0.0:
            intervals.append((left, right))
    return intervals


def sole_interval(
    intervals: list[tuple[float, float]],
    label: str,
) -> tuple[float, float]:
    if len(intervals) != 1:
        raise RuntimeError(f"expected one {label} interval, received {intervals}")
    return intervals[0]


def refine_near(
    margin: Callable[[float], float],
    estimate: float,
    lower_limit: float,
    upper_limit: float,
) -> float:
    width = 0.05
    for _ in range(8):
        left = max(lower_limit, estimate - width)
        right = min(upper_limit, estimate + width)
        if margin(left) * margin(right) <= 0.0:
            return float(brentq(margin, left, right, xtol=1.0e-11, rtol=1.0e-13))
        width *= 2.0
    raise RuntimeError(f"could not bracket root near {estimate}")


def solve(p: Parameters) -> dict:
    t_burst = burst_time(p)
    active_end = t_burst + p.smoke_active_duration_s
    release = uav_position(p.release_time_s, p)
    burst = bomb_position(t_burst, p)

    def margin_for(resolution: Resolution) -> Callable[[float], float]:
        def margin(t_s: float) -> float:
            metrics = edge_metrics(t_s, resolution, p)
            return p.smoke_radius_m - float(
                metrics["max_edge_segment_distance_m"]
            )

        return margin

    coarse_margin = margin_for(RESOLUTIONS[0])
    scan_convergence = []
    coarse_intervals: dict[float, tuple[float, float]] = {}
    for scan_step in (0.05, 0.02, 0.01):
        interval = sole_interval(
            find_positive_intervals(coarse_margin, t_burst, active_end, scan_step),
            f"edge/{scan_step}",
        )
        coarse_intervals[scan_step] = interval
        scan_convergence.append(
            {
                "scan_step_s": scan_step,
                "start_s": interval[0],
                "end_s": interval[1],
                "duration_s": interval[1] - interval[0],
            }
        )

    resolution_convergence = []
    resolution_intervals: dict[str, tuple[float, float]] = {
        "coarse": coarse_intervals[0.02]
    }
    estimate_start, estimate_end = resolution_intervals["coarse"]
    for resolution in RESOLUTIONS[1:]:
        margin = margin_for(resolution)
        start = refine_near(margin, estimate_start, t_burst, active_end)
        end = refine_near(margin, estimate_end, t_burst, active_end)
        resolution_intervals[resolution.name] = (start, end)
        estimate_start, estimate_end = start, end

    previous_duration = None
    for resolution in RESOLUTIONS:
        start, end = resolution_intervals[resolution.name]
        duration = end - start
        point_count = 2 * resolution.arc_count + 2 * resolution.line_count
        resolution_convergence.append(
            {
                **asdict(resolution),
                "edge_point_count": point_count,
                "start_s": start,
                "end_s": end,
                "duration_s": duration,
                "duration_change_from_previous_s": (
                    None if previous_duration is None else duration - previous_duration
                ),
            }
        )
        previous_duration = duration

    fine = RESOLUTIONS[-1]
    start_s, end_s = resolution_intervals[fine.name]
    midpoint_s = 0.5 * (start_s + end_s)
    start_metrics = edge_metrics(start_s, fine, p)
    end_metrics = edge_metrics(end_s, fine, p)
    midpoint_metrics = edge_metrics(midpoint_s, fine, p)
    duration_s = end_s - start_s
    scan_change = max(item["duration_s"] for item in scan_convergence) - min(
        item["duration_s"] for item in scan_convergence
    )
    resolution_change = abs(
        resolution_convergence[-1]["duration_s"]
        - resolution_convergence[-2]["duration_s"]
    )
    boundary_residual = max(
        abs(start_metrics["max_edge_segment_distance_m"] - p.smoke_radius_m),
        abs(end_metrics["max_edge_segment_distance_m"] - p.smoke_radius_m),
    )
    tangency_residual = max(
        start_metrics["tangency_residual_m2"],
        midpoint_metrics["tangency_residual_m2"],
        end_metrics["tangency_residual_m2"],
    )
    radial_residual = max(
        start_metrics["cylinder_radial_residual_m"],
        midpoint_metrics["cylinder_radial_residual_m"],
        end_metrics["cylinder_radial_residual_m"],
    )

    report = {
        "schema_version": 4,
        "project_id": "case002",
        "problem_id": "problem1",
        "definition_revision": 3,
        "method": {
            "primary_predicate": "maximum smoke-centre distance to missile-to-silhouette-edge-point segments is at most the smoke radius",
            "target_edge": "top far rim arc, bottom near rim arc, and two exact side tangency generators",
            "edge_construction": "horizontal radial plane through the missile and cylinder axis with exact circle tangency correction",
            "projection_model_used": False,
            "whole_surface_sampling_used": False,
            "root_method": "Brent bracketing root refinement",
        },
        "parameters": asdict(p),
        "hand_calculation": {
            "release_point_m": release.tolist(),
            "burst_absolute_time_s": t_burst,
            "burst_point_m": burst.tolist(),
            "smoke_active_interval_s": [t_burst, active_end],
        },
        "full_edge_occlusion": {
            "start_s": start_s,
            "end_s": end_s,
            "duration_s": duration_s,
            "midpoint_s": midpoint_s,
            "max_edge_segment_distance_at_start_m": start_metrics[
                "max_edge_segment_distance_m"
            ],
            "max_edge_segment_distance_at_end_m": end_metrics[
                "max_edge_segment_distance_m"
            ],
            "worst_edge_point_at_start_m": start_metrics[
                "worst_edge_point_m"
            ].tolist(),
            "worst_edge_point_at_end_m": end_metrics[
                "worst_edge_point_m"
            ].tolist(),
            "worst_curve_at_start": start_metrics["worst_curve"],
            "worst_curve_at_end": end_metrics["worst_curve"],
            "midpoint_max_edge_segment_distance_m": midpoint_metrics[
                "max_edge_segment_distance_m"
            ],
            "midpoint_worst_curve": midpoint_metrics["worst_curve"],
            "fine_edge_point_count": midpoint_metrics["edge_point_count"],
        },
        "time_scan_convergence": scan_convergence,
        "edge_resolution_convergence": resolution_convergence,
        "validation": {
            "release_point_hand_check_pass": bool(
                np.allclose(release, np.array([17620.0, 0.0, 1800.0]), atol=1.0e-12)
            ),
            "burst_time_hand_check_pass": bool(abs(t_burst - 5.1) <= 1.0e-12),
            "burst_point_hand_check_pass": bool(
                np.allclose(
                    burst,
                    np.array([17188.0, 0.0, 1736.496]),
                    atol=1.0e-9,
                )
            ),
            "inside_active_window_pass": bool(
                t_burst <= start_s <= end_s <= active_end
            ),
            "missile_above_target_pass": bool(
                missile_position(active_end, p)[2]
                > p.target_bottom_center_m[2] + p.target_height_m
            ),
            "exact_tangency_residual_m2": tangency_residual,
            "exact_tangency_pass": bool(tangency_residual < 1.0e-8),
            "cylinder_radial_residual_m": radial_residual,
            "cylinder_edge_geometry_pass": bool(radial_residual < 1.0e-10),
            "boundary_residual_max_m": boundary_residual,
            "scan_duration_change_s": scan_change,
            "scan_duration_change_below_0_001_s_pass": bool(scan_change < 0.001),
            "edge_resolution_duration_change_s": resolution_change,
            "edge_resolution_change_below_0_001_s_pass": bool(
                resolution_change < 0.001
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
            "missile_above_target_pass",
            "exact_tangency_pass",
            "cylinder_edge_geometry_pass",
            "scan_duration_change_below_0_001_s_pass",
            "edge_resolution_change_below_0_001_s_pass",
        )
    ) and checks["boundary_residual_max_m"] < 1.0e-7
    if not checks["all_required_checks_pass"]:
        raise RuntimeError(f"problem 1 validation failed: {checks}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--parameters",
        type=Path,
        default=Path("tests/case002/registry/parameters.yaml"),
    )
    parser.add_argument(
        "--assumptions",
        type=Path,
        default=Path("tests/case002/registry/assumptions.yaml"),
    )
    args = parser.parse_args()
    parameters = load_parameters(args.parameters)
    assumption_ids = load_assumption_ids(args.assumptions)
    report = solve(parameters)
    report["registry_sources"] = {
        "parameters": str(args.parameters.as_posix()),
        "assumptions": str(args.assumptions.as_posix()),
        "loaded_assumption_ids": assumption_ids,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
