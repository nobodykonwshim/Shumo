#!/usr/bin/env python3
"""Solve 2025 CUMCM A problem 1 with a perspective-projection coverage model."""

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
    target_geometric_center_m: tuple[float, float, float]
    view_up: tuple[float, float, float]
    normalized_focal_length: float


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
    "target_geometric_center_m": "PAR-TARGET-GEOMETRIC-CENTER",
    "view_up": "PAR-VIEW-UP",
    "normalized_focal_length": "PAR-NORMALIZED-FOCAL-LENGTH",
}

VECTOR_FIELDS = {
    "missile_initial_m",
    "fake_target_m",
    "uav_initial_m",
    "uav_direction",
    "target_bottom_center_m",
    "target_geometric_center_m",
    "view_up",
}

REQUIRED_ASSUMPTION_IDS = {
    "A-P1-MISSILE-UNIFORM",
    "A-P1-UAV-UNIFORM",
    "A-P1-BALLISTIC",
    "A-P1-NO-DRIFT",
    "A-P1-SPHERE",
    "A-P1-TARGET-CYLINDER",
    "A-P1-PINHOLE-VIEW",
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
    parameters = Parameters(**values)

    derived_center = np.asarray(parameters.target_bottom_center_m, dtype=float).copy()
    derived_center[2] += 0.5 * parameters.target_height_m
    if not np.allclose(
        derived_center,
        np.asarray(parameters.target_geometric_center_m, dtype=float),
        atol=1.0e-12,
    ):
        raise ValueError("registered target geometric centre is inconsistent with cylinder geometry")
    return parameters


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
    inherited_velocity = p.uav_speed_m_per_s * unit(np.asarray(p.uav_direction, dtype=float))
    gravity = np.array([0.0, 0.0, -p.gravity_m_per_s2])
    return uav_position(p.release_time_s, p) + inherited_velocity * tau + 0.5 * gravity * tau**2


def smoke_center(t_s: float, p: Parameters) -> np.ndarray:
    t_burst = burst_time(p)
    active_end = t_burst + p.smoke_active_duration_s
    if not (t_burst <= t_s <= active_end):
        raise ValueError("smoke center requested outside its active interval")
    center = bomb_position(t_burst, p).copy()
    center[2] -= p.smoke_settling_speed_m_per_s * (t_s - t_burst)
    return center


def target_geometric_center(p: Parameters) -> np.ndarray:
    return np.asarray(p.target_geometric_center_m, dtype=float)


def cylinder_boundary_points(mesh: Mesh, p: Parameters) -> np.ndarray:
    """Sample the side and both caps of the fixed target cylinder."""
    theta = np.linspace(0.0, 2.0 * np.pi, mesh.theta_count, endpoint=False)
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
    cap_x = bottom[0] + radius_cap.ravel() * np.cos(theta_cap).ravel()
    cap_y = bottom[1] + radius_cap.ravel() * np.sin(theta_cap).ravel()
    lower = np.column_stack((cap_x, cap_y, np.full(cap_x.shape, bottom[2])))
    upper = np.column_stack(
        (cap_x, cap_y, np.full(cap_x.shape, bottom[2] + p.target_height_m))
    )
    return np.vstack((side, lower, upper))


def camera_frame(t_s: float, p: Parameters) -> np.ndarray:
    """Rows are horizontal, vertical, and optical-axis unit vectors."""
    missile = missile_position(t_s, p)
    normal = unit(target_geometric_center(p) - missile)
    up = unit(np.asarray(p.view_up, dtype=float))
    horizontal_raw = np.cross(up, normal)
    if np.linalg.norm(horizontal_raw) < 1.0e-12:
        up = np.array([0.0, 1.0, 0.0])
        horizontal_raw = np.cross(up, normal)
    horizontal = unit(horizontal_raw)
    vertical = unit(np.cross(normal, horizontal))
    return np.vstack((horizontal, vertical, normal))


def perspective_projection(
    t_s: float, points: np.ndarray, p: Parameters
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Map world points to normalized image-plane coordinates."""
    missile = missile_position(t_s, p)
    rotation = camera_frame(t_s, p)
    camera = (rotation @ (points - missile).T).T
    depth = camera[:, 2]
    if np.any(depth <= 0.0):
        raise ValueError("target point lies behind the missile camera plane")
    focal = p.normalized_focal_length
    image = focal * camera[:, :2] / depth[:, None]
    homogeneous = np.column_stack((image, np.ones(image.shape[0])))
    return image, homogeneous, depth


def smoke_projection_conic(t_s: float, p: Parameters) -> tuple[np.ndarray, np.ndarray]:
    """Return image-plane conic matrix and smoke centre in camera coordinates."""
    missile = missile_position(t_s, p)
    rotation = camera_frame(t_s, p)
    center_camera = rotation @ (smoke_center(t_s, p) - missile)
    focal = p.normalized_focal_length
    calibration_inverse = np.diag([1.0 / focal, 1.0 / focal, 1.0])
    angular = np.outer(center_camera, center_camera) - (
        float(np.dot(center_camera, center_camera)) - p.smoke_radius_m**2
    ) * np.eye(3)
    conic = calibration_inverse.T @ angular @ calibration_inverse
    return conic, center_camera


def distances_to_sight_segments(
    smoke: np.ndarray, missile: np.ndarray, target_points: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    sight = target_points - missile
    smoke_from_missile = smoke - missile
    denominator = np.einsum("ij,ij->i", sight, sight)
    raw_fraction = np.einsum("ij,j->i", sight, smoke_from_missile) / denominator
    fraction = np.clip(raw_fraction, 0.0, 1.0)
    nearest = missile + fraction[:, None] * sight
    return np.linalg.norm(smoke - nearest, axis=1), fraction


def coverage_metrics(
    t_s: float, target_points: np.ndarray, p: Parameters
) -> dict[str, object]:
    """Evaluate equivalent 3-D segment and 2-D perspective coverage tests."""
    missile = missile_position(t_s, p)
    smoke = smoke_center(t_s, p)
    distances, fractions = distances_to_sight_segments(smoke, missile, target_points)
    worst_index = int(np.argmax(distances))

    _, homogeneous, target_depth = perspective_projection(t_s, target_points, p)
    conic, center_camera = smoke_projection_conic(t_s, p)
    conic_values = np.einsum("ij,jk,ik->i", homogeneous, conic, homogeneous)

    focal = p.normalized_focal_length
    rays = np.column_stack(
        (
            homogeneous[:, 0] / focal,
            homogeneous[:, 1] / focal,
            np.ones(homogeneous.shape[0]),
        )
    )
    ray_norm2 = np.einsum("ij,ij->i", rays, rays)
    ray_center = rays @ center_camera
    discriminant = ray_center**2 - ray_norm2 * (
        float(np.dot(center_camera, center_camera)) - p.smoke_radius_m**2
    )
    sqrt_disc = np.sqrt(np.maximum(discriminant, 0.0))
    near = (ray_center - sqrt_disc) / ray_norm2
    far = (ray_center + sqrt_disc) / ray_norm2
    segment_intersection = (
        (discriminant >= -1.0e-9)
        & (np.maximum(near, 0.0) <= np.minimum(far, target_depth) + 1.0e-9)
    )

    return {
        "max_segment_distance_m": float(distances[worst_index]),
        "worst_target_point_m": target_points[worst_index],
        "projection_fraction_at_worst": float(fractions[worst_index]),
        "min_projected_conic_value": float(np.min(conic_values)),
        "min_ray_discriminant": float(np.min(discriminant)),
        "all_projected_points_inside_smoke_conic": bool(np.all(conic_values >= -1.0e-9)),
        "all_rays_intersect_smoke_before_target": bool(np.all(segment_intersection)),
        "rotation_matrix": camera_frame(t_s, p),
        "smoke_center_camera_m": center_camera,
    }


def find_positive_intervals(
    margin: Callable[[float], float], start_s: float, end_s: float, scan_step_s: float
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


def sole_interval(intervals: list[tuple[float, float]], label: str) -> tuple[float, float]:
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

    meshes = {mesh.name: cylinder_boundary_points(mesh, p) for mesh in MESHES}

    def margin_for(points: np.ndarray) -> Callable[[float], float]:
        def margin(t_s: float) -> float:
            metrics = coverage_metrics(t_s, points, p)
            return p.smoke_radius_m - float(metrics["max_segment_distance_m"])

        return margin

    coarse_margin = margin_for(meshes["coarse"])
    scan_convergence = []
    coarse_intervals: dict[float, tuple[float, float]] = {}
    for scan_step in (0.05, 0.02, 0.01):
        interval = sole_interval(
            find_positive_intervals(coarse_margin, t_burst, active_end, scan_step),
            f"projection/{scan_step}",
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

    mesh_convergence = []
    mesh_intervals: dict[str, tuple[float, float]] = {
        "coarse": coarse_intervals[0.02]
    }
    estimate_start, estimate_end = mesh_intervals["coarse"]
    for mesh in MESHES[1:]:
        margin = margin_for(meshes[mesh.name])
        start = refine_near(margin, estimate_start, t_burst, active_end)
        end = refine_near(margin, estimate_end, t_burst, active_end)
        mesh_intervals[mesh.name] = (start, end)
        estimate_start, estimate_end = start, end

    previous_duration = None
    for mesh in MESHES:
        start, end = mesh_intervals[mesh.name]
        duration = end - start
        mesh_convergence.append(
            {
                **asdict(mesh),
                "boundary_point_count": int(meshes[mesh.name].shape[0]),
                "start_s": start,
                "end_s": end,
                "duration_s": duration,
                "duration_change_from_previous_s": (
                    None if previous_duration is None else duration - previous_duration
                ),
            }
        )
        previous_duration = duration

    start_s, end_s = mesh_intervals["fine"]
    midpoint_s = 0.5 * (start_s + end_s)
    start_metrics = coverage_metrics(start_s, meshes["fine"], p)
    end_metrics = coverage_metrics(end_s, meshes["fine"], p)
    midpoint_metrics = coverage_metrics(midpoint_s, meshes["fine"], p)
    duration_s = end_s - start_s
    scan_change = max(item["duration_s"] for item in scan_convergence) - min(
        item["duration_s"] for item in scan_convergence
    )
    mesh_change = abs(
        mesh_convergence[-1]["duration_s"] - mesh_convergence[-2]["duration_s"]
    )

    report = {
        "schema_version": 3,
        "project_id": "case002",
        "problem_id": "problem1",
        "definition_revision": 2,
        "method": {
            "primary_predicate": "full target perspective projection is covered by the smoke-sphere shadow projection and every covered ray intersects smoke before the target",
            "camera_origin": "missile position",
            "camera_normal": "missile-to-target-geometric-centre sight direction",
            "projection": "pinhole perspective projection through a time-dependent orthonormal view matrix",
            "smoke_projection": "image-plane conic induced by the tangent cone from missile to smoke sphere",
            "equivalent_numeric_margin": "smoke radius minus maximum distance over missile-to-target-point sight segments",
            "root_method": "Brent bracketing root refinement",
        },
        "parameters": asdict(p),
        "hand_calculation": {
            "release_point_m": release.tolist(),
            "burst_absolute_time_s": t_burst,
            "burst_point_m": burst.tolist(),
            "smoke_active_interval_s": [t_burst, active_end],
        },
        "full_projection_coverage": {
            "start_s": start_s,
            "end_s": end_s,
            "duration_s": duration_s,
            "midpoint_s": midpoint_s,
            "max_segment_distance_at_start_m": start_metrics["max_segment_distance_m"],
            "max_segment_distance_at_end_m": end_metrics["max_segment_distance_m"],
            "worst_target_point_at_start_m": start_metrics["worst_target_point_m"].tolist(),
            "worst_target_point_at_end_m": end_metrics["worst_target_point_m"].tolist(),
            "midpoint_all_projected_points_inside_smoke_conic": midpoint_metrics[
                "all_projected_points_inside_smoke_conic"
            ],
            "midpoint_all_rays_intersect_smoke_before_target": midpoint_metrics[
                "all_rays_intersect_smoke_before_target"
            ],
            "midpoint_min_projected_conic_value": midpoint_metrics[
                "min_projected_conic_value"
            ],
            "view_rotation_matrix_at_midpoint": midpoint_metrics[
                "rotation_matrix"
            ].tolist(),
            "smoke_center_camera_at_midpoint_m": midpoint_metrics[
                "smoke_center_camera_m"
            ].tolist(),
        },
        "time_scan_convergence": scan_convergence,
        "mesh_convergence": mesh_convergence,
        "validation": {
            "release_point_hand_check_pass": bool(
                np.allclose(release, np.array([17620.0, 0.0, 1800.0]), atol=1.0e-12)
            ),
            "burst_time_hand_check_pass": bool(abs(t_burst - 5.1) <= 1.0e-12),
            "burst_point_hand_check_pass": bool(
                np.allclose(burst, np.array([17188.0, 0.0, 1736.496]), atol=1.0e-9)
            ),
            "inside_active_window_pass": bool(t_burst <= start_s <= end_s <= active_end),
            "projection_containment_midpoint_pass": bool(
                midpoint_metrics["all_projected_points_inside_smoke_conic"]
                and midpoint_metrics["all_rays_intersect_smoke_before_target"]
            ),
            "view_matrix_orthonormal_residual": float(
                np.linalg.norm(
                    midpoint_metrics["rotation_matrix"]
                    @ midpoint_metrics["rotation_matrix"].T
                    - np.eye(3)
                )
            ),
            "boundary_residual_max_m": max(
                abs(float(start_metrics["max_segment_distance_m"]) - p.smoke_radius_m),
                abs(float(end_metrics["max_segment_distance_m"]) - p.smoke_radius_m),
            ),
            "scan_duration_change_s": scan_change,
            "scan_duration_change_below_0_001_s_pass": bool(scan_change < 0.001),
            "mesh_duration_change_s": mesh_change,
            "mesh_duration_change_below_0_001_s_pass": bool(mesh_change < 0.001),
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
            "projection_containment_midpoint_pass",
            "scan_duration_change_below_0_001_s_pass",
            "mesh_duration_change_below_0_001_s_pass",
        )
    ) and checks["view_matrix_orthonormal_residual"] < 1.0e-10 and checks[
        "boundary_residual_max_m"
    ] < 1.0e-7
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
