#!/usr/bin/env python3
"""Deterministic feasibility checks for explicit or polyline survey routes.

Polyline-only inputs are evaluated exactly as piecewise-linear paths. Inputs
that provide ``geometry_segments`` are evaluated using their explicit line and
quadratic-Bezier geometry; any accompanying ``points`` are treated only as a
sampling representation for independent spatial evaluation.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Sequence

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from skills.math_modeling.geometry.route_geometry import point, validate_explicit_geometry

_EPS = 1e-12


def _segment(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float, float]:
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    if length <= _EPS:
        raise ValueError("Consecutive route points must be distinct")
    return dx / length, dy / length, length


def _turn_angle_deg(u0: tuple[float, float], u1: tuple[float, float]) -> float:
    dot = max(-1.0, min(1.0, u0[0] * u1[0] + u0[1] * u1[1]))
    cross = u0[0] * u1[1] - u0[1] * u1[0]
    return math.degrees(math.atan2(abs(cross), dot))


def _circumradius(
    a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]
) -> float | None:
    ab, bc, ca = math.dist(a, b), math.dist(b, c), math.dist(c, a)
    twice_area = abs(
        (b[0] - a[0]) * (c[1] - a[1])
        - (b[1] - a[1]) * (c[0] - a[0])
    )
    if twice_area <= _EPS:
        return None
    return ab * bc * ca / (2.0 * twice_area)


def _validate_polyline_line(
    line: dict[str, Any], *, heading_tolerance_deg: float
) -> dict[str, Any]:
    raw_points = line.get("points")
    if not isinstance(raw_points, list) or len(raw_points) < 2:
        raise ValueError("Each line must contain at least two points")
    points = [point(raw) for raw in raw_points]
    segments = [_segment(points[i], points[i + 1]) for i in range(len(points) - 1)]
    corners: list[dict[str, Any]] = []
    sampled_radii: list[float] = []
    for i in range(1, len(points) - 1):
        angle = _turn_angle_deg(segments[i - 1][:2], segments[i][:2])
        radius = _circumradius(points[i - 1], points[i], points[i + 1])
        if radius is not None:
            sampled_radii.append(radius)
        if angle > heading_tolerance_deg:
            corners.append(
                {
                    "vertex_index": i,
                    "point": [points[i][0], points[i][1]],
                    "heading_change_deg": angle,
                    "three_point_circumradius_m": radius,
                }
            )
    return {
        "line_id": str(line.get("id", "")),
        "geometry_mode": "exact_polyline",
        "point_count": len(points),
        "segment_count": len(segments),
        "length_m": sum(segment[2] for segment in segments),
        "hard_corner_count": len(corners),
        "c1_continuous": len(corners) == 0,
        "minimum_curvature_radius_m": min(sampled_radii) if sampled_radii else None,
        "corners": corners,
    }


def validate_line(
    line: dict[str, Any], *, heading_tolerance_deg: float
) -> dict[str, Any]:
    raw_geometry = line.get("geometry_segments")
    if raw_geometry is None:
        return _validate_polyline_line(line, heading_tolerance_deg=heading_tolerance_deg)
    if not isinstance(raw_geometry, list) or not raw_geometry:
        raise ValueError("geometry_segments must be a non-empty list")
    report = validate_explicit_geometry(
        raw_geometry, heading_tolerance_deg=heading_tolerance_deg
    )
    return {
        "line_id": str(line.get("id", "")),
        "geometry_mode": "explicit_line_and_quadratic_bezier",
        "point_count": len(line.get("points", [])),
        "segment_count": report["segment_count"],
        "length_m": report["length_m"],
        "hard_corner_count": report["hard_corner_count"],
        "c1_continuous": report["c1_continuous"],
        "minimum_curvature_radius_m": report["minimum_curvature_radius_m"],
        "corners": report["hard_corners"],
    }


def validate_plan(
    plan: dict[str, Any],
    *,
    heading_tolerance_deg: float = 1e-6,
    minimum_turn_radius_m: float | None = None,
) -> dict[str, Any]:
    if heading_tolerance_deg < 0 or not math.isfinite(heading_tolerance_deg):
        raise ValueError("heading_tolerance_deg must be finite and non-negative")
    if minimum_turn_radius_m is not None and (
        minimum_turn_radius_m <= 0 or not math.isfinite(minimum_turn_radius_m)
    ):
        raise ValueError("minimum_turn_radius_m must be finite and positive")

    lines = plan.get("lines")
    if not isinstance(lines, list) or not lines:
        raise ValueError("Candidate plan must contain a non-empty lines list")
    line_reports = [
        validate_line(line, heading_tolerance_deg=heading_tolerance_deg) for line in lines
    ]
    hard_corner_count = sum(report["hard_corner_count"] for report in line_reports)
    finite_radii = [
        report["minimum_curvature_radius_m"]
        for report in line_reports
        if report["minimum_curvature_radius_m"] is not None
    ]
    minimum_radius = min(finite_radii) if finite_radii else None
    radius_pass = (
        minimum_turn_radius_m is None
        or minimum_radius is None
        or minimum_radius + 1e-9 >= minimum_turn_radius_m
    )
    tangent_pass = hard_corner_count == 0
    passed = tangent_pass and radius_pass

    reasons: list[str] = []
    if not tangent_pass:
        reasons.append("nonzero_heading_change_requires_unbounded_curvature")
    if not radius_pass:
        reasons.append("minimum_curvature_radius_below_frozen_turn_radius")
    if passed:
        reasons.append("route_geometry_is_tangent_continuous_with_finite_curvature")

    return {
        "schema_version": 2,
        "candidate_id": plan.get("candidate_id"),
        "route_family": plan.get("route_family"),
        "status": "pass" if passed else "fail",
        "criteria": {
            "route_requires_tangent_continuity": True,
            "heading_tolerance_deg": heading_tolerance_deg,
            "minimum_turn_radius_m": minimum_turn_radius_m,
            "explicit_geometry_preferred_over_sampled_points": True,
        },
        "results": {
            "line_count": len(line_reports),
            "total_length_m": sum(report["length_m"] for report in line_reports),
            "hard_corner_count": hard_corner_count,
            "minimum_curvature_radius_m": minimum_radius,
            "within_line_curvature_pass": passed,
            "inter_line_connectors_checked": False,
        },
        "reasons": reasons,
        "required_follow_up_if_failed": [
            "retain the route family for explicit geometry refinement when length remains competitive",
            "generate a versioned tangent-continuous replacement rather than applying implicit smoothing",
            "rerun complete spatial coverage, overlap, boundary and crossing evaluation",
        ],
        "line_reports": line_reports,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--heading-tolerance-deg", type=float, default=1e-6)
    parser.add_argument("--minimum-turn-radius-m", type=float)
    args = parser.parse_args()
    plan = json.loads(args.candidate.read_text(encoding="utf-8"))
    report = validate_plan(
        plan,
        heading_tolerance_deg=args.heading_tolerance_deg,
        minimum_turn_radius_m=args.minimum_turn_radius_m,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(report["status"])
    return 0 if report["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
