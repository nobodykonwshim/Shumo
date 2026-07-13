#!/usr/bin/env python3
"""Explicit line and quadratic-Bezier route geometry utilities.

The helpers in this module separate executable curve geometry from the sampled
polyline used by rasterized spatial evaluators. A refined route can therefore
be checked for exact tangent continuity and finite curvature while still being
sampled deterministically for coverage and overlap calculations.
"""
from __future__ import annotations

import math
from typing import Any, Sequence

_EPS = 1e-12
Point = tuple[float, float]


def point(raw: Sequence[float]) -> Point:
    if len(raw) != 2:
        raise ValueError("Each point must contain exactly two coordinates")
    x, y = float(raw[0]), float(raw[1])
    if not math.isfinite(x) or not math.isfinite(y):
        raise ValueError("Coordinates must be finite")
    return x, y


def _sub(a: Point, b: Point) -> Point:
    return a[0] - b[0], a[1] - b[1]


def _add(a: Point, b: Point) -> Point:
    return a[0] + b[0], a[1] + b[1]


def _scale(a: Point, factor: float) -> Point:
    return a[0] * factor, a[1] * factor


def _norm(a: Point) -> float:
    return math.hypot(a[0], a[1])


def _unit(a: Point) -> Point:
    length = _norm(a)
    if length <= _EPS:
        raise ValueError("Geometry contains a zero-length direction")
    return a[0] / length, a[1] / length


def _as_list(p: Point) -> list[float]:
    return [p[0], p[1]]


def segment_start(segment: dict[str, Any]) -> Point:
    kind = segment.get("type")
    if kind in {"line", "quadratic_bezier"}:
        return point(segment["p0"])
    raise ValueError(f"Unsupported geometry segment type: {kind!r}")


def segment_end(segment: dict[str, Any]) -> Point:
    kind = segment.get("type")
    if kind == "line":
        return point(segment["p1"])
    if kind == "quadratic_bezier":
        return point(segment["p2"])
    raise ValueError(f"Unsupported geometry segment type: {kind!r}")


def segment_point(segment: dict[str, Any], t: float) -> Point:
    if not 0.0 <= t <= 1.0:
        raise ValueError("Segment parameter must lie in [0,1]")
    kind = segment.get("type")
    p0 = segment_start(segment)
    if kind == "line":
        p1 = segment_end(segment)
        return p0[0] + t * (p1[0] - p0[0]), p0[1] + t * (p1[1] - p0[1])
    if kind == "quadratic_bezier":
        p1 = point(segment["p1"])
        p2 = segment_end(segment)
        u = 1.0 - t
        return (
            u * u * p0[0] + 2.0 * u * t * p1[0] + t * t * p2[0],
            u * u * p0[1] + 2.0 * u * t * p1[1] + t * t * p2[1],
        )
    raise ValueError(f"Unsupported geometry segment type: {kind!r}")


def segment_derivative(segment: dict[str, Any], t: float) -> Point:
    kind = segment.get("type")
    p0 = segment_start(segment)
    if kind == "line":
        return _sub(segment_end(segment), p0)
    if kind == "quadratic_bezier":
        p1 = point(segment["p1"])
        p2 = segment_end(segment)
        return _scale(
            _add(_scale(_sub(p1, p0), 1.0 - t), _scale(_sub(p2, p1), t)),
            2.0,
        )
    raise ValueError(f"Unsupported geometry segment type: {kind!r}")


def segment_second_derivative(segment: dict[str, Any]) -> Point:
    kind = segment.get("type")
    if kind == "line":
        return 0.0, 0.0
    if kind == "quadratic_bezier":
        p0 = segment_start(segment)
        p1 = point(segment["p1"])
        p2 = segment_end(segment)
        return 2.0 * (p2[0] - 2.0 * p1[0] + p0[0]), 2.0 * (
            p2[1] - 2.0 * p1[1] + p0[1]
        )
    raise ValueError(f"Unsupported geometry segment type: {kind!r}")


def _simpson(f, a: float, b: float, n: int = 64) -> float:
    h = (b - a) / n
    total = f(a) + f(b)
    for i in range(1, n):
        total += (4.0 if i % 2 else 2.0) * f(a + i * h)
    return total * h / 3.0


def segment_length(segment: dict[str, Any]) -> float:
    kind = segment.get("type")
    if kind == "line":
        length = math.dist(segment_start(segment), segment_end(segment))
    elif kind == "quadratic_bezier":
        length = _simpson(lambda t: _norm(segment_derivative(segment, t)), 0.0, 1.0)
    else:
        raise ValueError(f"Unsupported geometry segment type: {kind!r}")
    if length <= _EPS or not math.isfinite(length):
        raise ValueError("Geometry segments must have finite positive length")
    return length


def segment_minimum_radius(segment: dict[str, Any], *, samples: int = 401) -> float | None:
    if segment.get("type") == "line":
        return None
    second = segment_second_derivative(segment)
    minimum = math.inf
    for i in range(samples):
        t = i / (samples - 1)
        first = segment_derivative(segment, t)
        speed = _norm(first)
        if speed <= _EPS:
            raise ValueError("Curve derivative vanishes; curvature is not finite")
        cross = abs(first[0] * second[1] - first[1] * second[0])
        if cross <= _EPS:
            continue
        minimum = min(minimum, speed**3 / cross)
    return None if math.isinf(minimum) else minimum


def heading_change_deg(a: Point, b: Point) -> float:
    ua, ub = _unit(a), _unit(b)
    dot = max(-1.0, min(1.0, ua[0] * ub[0] + ua[1] * ub[1]))
    cross = ua[0] * ub[1] - ua[1] * ub[0]
    return math.degrees(math.atan2(abs(cross), dot))


def geometry_length(segments: Sequence[dict[str, Any]]) -> float:
    if not segments:
        raise ValueError("Explicit geometry must contain at least one segment")
    return sum(segment_length(segment) for segment in segments)


def validate_explicit_geometry(
    segments: Sequence[dict[str, Any]],
    *,
    heading_tolerance_deg: float = 1e-6,
    position_tolerance_m: float = 1e-6,
    curvature_samples: int = 401,
) -> dict[str, Any]:
    if not segments:
        raise ValueError("Explicit geometry must contain at least one segment")
    hard_corners: list[dict[str, Any]] = []
    minimum_radius = math.inf
    for index, segment in enumerate(segments):
        segment_length(segment)
        radius = segment_minimum_radius(segment, samples=curvature_samples)
        if radius is not None:
            minimum_radius = min(minimum_radius, radius)
        if index == 0:
            continue
        previous = segments[index - 1]
        join_a = segment_end(previous)
        join_b = segment_start(segment)
        gap = math.dist(join_a, join_b)
        if gap > position_tolerance_m:
            raise ValueError(
                f"Geometry segments {index - 1} and {index} are disconnected by {gap} m"
            )
        angle = heading_change_deg(
            segment_derivative(previous, 1.0), segment_derivative(segment, 0.0)
        )
        if angle > heading_tolerance_deg:
            hard_corners.append(
                {"join_index": index, "point": _as_list(join_a), "heading_change_deg": angle}
            )
    return {
        "segment_count": len(segments),
        "length_m": geometry_length(segments),
        "hard_corner_count": len(hard_corners),
        "c1_continuous": not hard_corners,
        "minimum_curvature_radius_m": None if math.isinf(minimum_radius) else minimum_radius,
        "hard_corners": hard_corners,
    }


def smooth_polyline_quadratic(
    raw_points: Sequence[Sequence[float]], *, trim_fraction: float
) -> list[dict[str, Any]]:
    """Replace every interior vertex with a tangent-continuous quadratic fillet."""
    if not (0.0 < trim_fraction < 0.5) or not math.isfinite(trim_fraction):
        raise ValueError("trim_fraction must be finite and lie strictly in (0,0.5)")
    points = [point(value) for value in raw_points]
    if len(points) < 2:
        raise ValueError("A route requires at least two points")
    lengths = [math.dist(a, b) for a, b in zip(points, points[1:])]
    if any(length <= _EPS for length in lengths):
        raise ValueError("Consecutive route points must be distinct")
    if len(points) == 2:
        return [{"type": "line", "p0": _as_list(points[0]), "p1": _as_list(points[1])}]

    entries: list[Point] = []
    exits: list[Point] = []
    for i in range(1, len(points) - 1):
        vertex = points[i]
        incoming = _unit(_sub(vertex, points[i - 1]))
        outgoing = _unit(_sub(points[i + 1], vertex))
        trim = trim_fraction * min(lengths[i - 1], lengths[i])
        entries.append(_sub(vertex, _scale(incoming, trim)))
        exits.append(_add(vertex, _scale(outgoing, trim)))

    segments: list[dict[str, Any]] = []
    current = points[0]
    for i, (entry, exit_) in enumerate(zip(entries, exits), start=1):
        if math.dist(current, entry) <= _EPS:
            raise ValueError("Smoothing trim leaves no positive straight segment")
        segments.append({"type": "line", "p0": _as_list(current), "p1": _as_list(entry)})
        segments.append(
            {
                "type": "quadratic_bezier",
                "p0": _as_list(entry),
                "p1": _as_list(points[i]),
                "p2": _as_list(exit_),
            }
        )
        current = exit_
    if math.dist(current, points[-1]) <= _EPS:
        raise ValueError("Smoothing trim leaves no positive final straight segment")
    segments.append({"type": "line", "p0": _as_list(current), "p1": _as_list(points[-1])})
    validate_explicit_geometry(segments)
    return segments


def sample_geometry(
    segments: Sequence[dict[str, Any]], *, curve_subdivisions: int = 6
) -> list[list[float]]:
    if curve_subdivisions < 2:
        raise ValueError("curve_subdivisions must be at least two")
    sampled: list[list[float]] = [_as_list(segment_start(segments[0]))]
    for segment in segments:
        values = (
            [segment_end(segment)]
            if segment.get("type") == "line"
            else [segment_point(segment, i / curve_subdivisions) for i in range(1, curve_subdivisions + 1)]
        )
        for value in values:
            if math.dist(point(sampled[-1]), value) > _EPS:
                sampled.append(_as_list(value))
    return sampled


def x_at_y(segments: Sequence[dict[str, Any]], y: float) -> float:
    """Evaluate x on a route whose explicit segments are monotone in y."""
    for segment in segments:
        start, end = segment_start(segment), segment_end(segment)
        lower, upper = sorted((start[1], end[1]))
        if y < lower - 1e-9 or y > upper + 1e-9:
            continue
        if segment.get("type") == "line":
            t = (y - start[1]) / (end[1] - start[1])
            return segment_point(segment, max(0.0, min(1.0, t)))[0]
        increasing = end[1] > start[1]
        lo, hi = 0.0, 1.0
        for _ in range(70):
            mid = 0.5 * (lo + hi)
            value = segment_point(segment, mid)[1]
            if (value < y) == increasing:
                lo = mid
            else:
                hi = mid
        return segment_point(segment, 0.5 * (lo + hi))[0]
    raise ValueError(f"y={y} is outside the route's monotone-y range")


def minimum_adjacent_separation(
    line_geometries: Sequence[Sequence[dict[str, Any]]],
    *,
    ymin: float,
    ymax: float,
    samples: int = 401,
) -> dict[str, Any]:
    if len(line_geometries) < 2:
        return {"minimum_separation_m": None, "crossing_count": 0, "samples": samples}
    minimum = math.inf
    crossings: list[dict[str, Any]] = []
    for j in range(samples):
        y = ymin + (ymax - ymin) * j / (samples - 1)
        xs = [x_at_y(geometry, y) for geometry in line_geometries]
        for i, (left, right) in enumerate(zip(xs, xs[1:])):
            separation = right - left
            minimum = min(minimum, separation)
            if separation <= 0.0:
                crossings.append(
                    {
                        "y": y,
                        "left_line_index": i,
                        "right_line_index": i + 1,
                        "separation_m": separation,
                    }
                )
    return {
        "minimum_separation_m": minimum,
        "crossing_count": len(crossings),
        "samples": samples,
        "crossings": crossings[:100],
    }
