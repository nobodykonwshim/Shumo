#!/usr/bin/env python3
"""Deterministic geometric feasibility checks for precomputed survey polylines.

This module does not generate or smooth routes. It evaluates the exact polyline
geometry supplied by a candidate plan. A non-zero heading change at an interior
polyline vertex is a hard corner; following that exact path requires an
instantaneous heading change (unbounded curvature), so it is not a finite-turn-
radius vessel path unless a separate smoothing step is performed and the
smoothed route is re-evaluated for coverage and overlap.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Sequence

_EPS = 1e-12


def _point(raw: Sequence[float]) -> tuple[float, float]:
    if len(raw) != 2:
        raise ValueError("Each route point must contain exactly two coordinates")
    x, y = float(raw[0]), float(raw[1])
    if not math.isfinite(x) or not math.isfinite(y):
        raise ValueError("Route coordinates must be finite")
    return x, y


def _segment(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float, float]:
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    if length <= _EPS:
        raise ValueError("Consecutive route points must be distinct")
    return dx / length, dy / length, length


def _turn_angle_deg(
    u0: tuple[float, float], u1: tuple[float, float]
) -> float:
    dot = max(-1.0, min(1.0, u0[0] * u1[0] + u0[1] * u1[1]))
    cross = u0[0] * u1[1] - u0[1] * u1[0]
    return math.degrees(math.atan2(abs(cross), dot))


def _circumradius(
    a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]
) -> float | None:
    ab = math.dist(a, b)
    bc = math.dist(b, c)
    ca = math.dist(c, a)
    twice_area = abs(
        (b[0] - a[0]) * (c[1] - a[1])
        - (b[1] - a[1]) * (c[0] - a[0])
    )
    if twice_area <= _EPS:
        return None
    return ab * bc * ca / (2.0 * twice_area)


def validate_line(
    line: dict[str, Any], *, heading_tolerance_deg: float
) -> dict[str, Any]:
    raw_points = line.get("points")
    if not isinstance(raw_points, list) or len(raw_points) < 2:
        raise ValueError("Each line must contain at least two points")
    points = [_point(raw) for raw in raw_points]
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
        "point_count": len(points),
        "length_m": sum(segment[2] for segment in segments),
        "hard_corner_count": len(corners),
        "c1_continuous_exact_polyline": len(corners) == 0,
        "minimum_three_point_circumradius_m": min(sampled_radii) if sampled_radii else None,
        "corners": corners,
    }


def validate_plan(
    plan: dict[str, Any],
    *,
    heading_tolerance_deg: float = 1e-6,
    minimum_turn_radius_m: float | None = None,
) -> dict[str, Any]:
    if heading_tolerance_deg < 0 or not math.isfinite(heading_tolerance_deg):
        raise ValueError("heading_tolerance_deg must be finite and non-negative")
    if minimum_turn_radius_m is not None:
        if minimum_turn_radius_m <= 0 or not math.isfinite(minimum_turn_radius_m):
            raise ValueError("minimum_turn_radius_m must be finite and positive")

    lines = plan.get("lines")
    if not isinstance(lines, list) or not lines:
        raise ValueError("Candidate plan must contain a non-empty lines list")
    line_reports = [
        validate_line(line, heading_tolerance_deg=heading_tolerance_deg) for line in lines
    ]
    hard_corner_count = sum(report["hard_corner_count"] for report in line_reports)
    finite_radii = [
        report["minimum_three_point_circumradius_m"]
        for report in line_reports
        if report["minimum_three_point_circumradius_m"] is not None
    ]
    minimum_sampled_radius = min(finite_radii) if finite_radii else None
    radius_pass = (
        minimum_turn_radius_m is None
        or minimum_sampled_radius is None
        or minimum_sampled_radius + 1e-9 >= minimum_turn_radius_m
    )
    exact_polyline_pass = hard_corner_count == 0
    passed = exact_polyline_pass and radius_pass

    reasons: list[str] = []
    if not exact_polyline_pass:
        reasons.append(
            "nonzero_heading_change_at_polyline_vertices_requires_unbounded_curvature"
        )
    if not radius_pass:
        reasons.append("sampled_circumradius_below_frozen_minimum_turn_radius")
    if passed:
        reasons.append("exact_survey_line_geometry_has_no_detected_curvature_violation")

    return {
        "schema_version": 1,
        "candidate_id": plan.get("candidate_id"),
        "route_family": plan.get("route_family"),
        "status": "pass" if passed else "fail",
        "decision": {
            "selected_candidate_on_pass": plan.get("candidate_id"),
            "fallback_candidate_on_fail": "P4-CAND-A",
        },
        "criteria": {
            "exact_polyline_requires_c1_continuity": True,
            "heading_tolerance_deg": heading_tolerance_deg,
            "minimum_turn_radius_m": minimum_turn_radius_m,
        },
        "results": {
            "line_count": len(line_reports),
            "hard_corner_count": hard_corner_count,
            "minimum_three_point_circumradius_m": minimum_sampled_radius,
            "within_line_curvature_pass": passed,
            "inter_line_connectors_checked": False,
        },
        "reasons": reasons,
        "required_follow_up_if_failed": [
            "select P4-CAND-A as the frozen fallback baseline",
            "do not repair P4-CAND-C by implicit smoothing",
            "if C is reconsidered, generate an explicit finite-radius smoothed route and rerun spatial coverage and overlap evaluation",
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
