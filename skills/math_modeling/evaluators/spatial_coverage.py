#!/usr/bin/env python3
"""Independent spatial evaluator for multibeam survey-line plans.

The evaluator deliberately has no route-generation logic. It accepts a terrain,
a rectangular evaluation region, an instrument opening angle, and already-created
survey lines. It reports line length, rasterized uncovered area, overlap-excess
centerline length, boundary violations, and grid-resolution sensitivity.

Only Python's standard library is required.
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

_EPS = 1e-12


class EvaluationError(ValueError):
    """Raised when the evaluation input or geometry is invalid."""


@dataclass(frozen=True)
class Region:
    xmin: float
    xmax: float
    ymin: float
    ymax: float

    def __post_init__(self) -> None:
        if not (self.xmax > self.xmin and self.ymax > self.ymin):
            raise EvaluationError("Region bounds must satisfy xmax>xmin and ymax>ymin")

    @property
    def area(self) -> float:
        return (self.xmax - self.xmin) * (self.ymax - self.ymin)


@dataclass(frozen=True)
class Segment:
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def dx(self) -> float:
        return self.x2 - self.x1

    @property
    def dy(self) -> float:
        return self.y2 - self.y1

    @property
    def length(self) -> float:
        return math.hypot(self.dx, self.dy)

    def unit_tangent(self) -> tuple[float, float]:
        length = self.length
        if length <= _EPS:
            raise EvaluationError("Survey-line segments must have positive length")
        return self.dx / length, self.dy / length

    def point_at(self, u: float) -> tuple[float, float]:
        return self.x1 + u * self.dx, self.y1 + u * self.dy


@dataclass(frozen=True)
class SurveyLine:
    line_id: str
    points: tuple[tuple[float, float], ...]

    def __post_init__(self) -> None:
        if len(self.points) < 2:
            raise EvaluationError(f"Line {self.line_id!r} must have at least two points")
        for segment in self.segments:
            if segment.length <= _EPS:
                raise EvaluationError(f"Line {self.line_id!r} contains a zero-length segment")

    @property
    def segments(self) -> tuple[Segment, ...]:
        return tuple(
            Segment(x1, y1, x2, y2)
            for (x1, y1), (x2, y2) in zip(self.points, self.points[1:])
        )

    @property
    def length(self) -> float:
        return sum(segment.length for segment in self.segments)


class Terrain:
    def depth_gradient(self, x: float, y: float) -> tuple[float, float, float]:
        """Return positive-down depth and horizontal depth gradient dD/dx,dD/dy."""
        raise NotImplementedError


@dataclass(frozen=True)
class PlaneTerrain(Terrain):
    depth_at_origin: float
    origin_x: float
    origin_y: float
    gradient_x: float
    gradient_y: float

    def depth_gradient(self, x: float, y: float) -> tuple[float, float, float]:
        depth = (
            self.depth_at_origin
            + self.gradient_x * (x - self.origin_x)
            + self.gradient_y * (y - self.origin_y)
        )
        return depth, self.gradient_x, self.gradient_y


@dataclass(frozen=True)
class GridTerrain(Terrain):
    x: tuple[float, ...]
    y: tuple[float, ...]
    depth: tuple[tuple[float, ...], ...]

    def __post_init__(self) -> None:
        if len(self.x) < 2 or len(self.y) < 2:
            raise EvaluationError("Grid terrain requires at least 2 x-values and 2 y-values")
        if any(b <= a for a, b in zip(self.x, self.x[1:])):
            raise EvaluationError("Grid x coordinates must be strictly increasing")
        if any(b <= a for a, b in zip(self.y, self.y[1:])):
            raise EvaluationError("Grid y coordinates must be strictly increasing")
        if len(self.depth) != len(self.y):
            raise EvaluationError("Grid depth row count must match y coordinate count")
        if any(len(row) != len(self.x) for row in self.depth):
            raise EvaluationError("Every grid depth row must match x coordinate count")

    @staticmethod
    def _locate(values: Sequence[float], value: float) -> tuple[int, float]:
        if value < values[0] - _EPS or value > values[-1] + _EPS:
            raise EvaluationError(
                f"Point coordinate {value} lies outside terrain grid [{values[0]}, {values[-1]}]"
            )
        if value >= values[-1]:
            return len(values) - 2, 1.0
        lo, hi = 0, len(values) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if values[mid] <= value:
                lo = mid
            else:
                hi = mid
        span = values[lo + 1] - values[lo]
        return lo, (value - values[lo]) / span

    def depth_gradient(self, x: float, y: float) -> tuple[float, float, float]:
        i, tx = self._locate(self.x, x)
        j, ty = self._locate(self.y, y)
        x0, x1 = self.x[i], self.x[i + 1]
        y0, y1 = self.y[j], self.y[j + 1]
        d00 = self.depth[j][i]
        d10 = self.depth[j][i + 1]
        d01 = self.depth[j + 1][i]
        d11 = self.depth[j + 1][i + 1]
        depth = (
            (1 - tx) * (1 - ty) * d00
            + tx * (1 - ty) * d10
            + (1 - tx) * ty * d01
            + tx * ty * d11
        )
        ddx = ((1 - ty) * (d10 - d00) + ty * (d11 - d01)) / (x1 - x0)
        ddy = ((1 - tx) * (d01 - d00) + tx * (d11 - d10)) / (y1 - y0)
        return depth, ddx, ddy


@dataclass(frozen=True)
class EvaluationSettings:
    opening_angle_deg: float
    grid_nx: int = 100
    grid_ny: int = 100
    along_step_m: float = 5.0
    cross_track_samples: int = 101
    overlap_threshold: float = 0.20
    overlap_length_policy: str = "per_line"
    sensitivity_grid_sizes: tuple[int, ...] = (50, 100, 200)

    def __post_init__(self) -> None:
        if not (0 < self.opening_angle_deg < 180):
            raise EvaluationError("opening_angle_deg must lie strictly between 0 and 180")
        if self.grid_nx <= 0 or self.grid_ny <= 0:
            raise EvaluationError("grid_nx and grid_ny must be positive")
        if self.along_step_m <= 0:
            raise EvaluationError("along_step_m must be positive")
        if self.cross_track_samples < 5:
            raise EvaluationError("cross_track_samples must be at least 5")
        if not (0 <= self.overlap_threshold < 1):
            raise EvaluationError("overlap_threshold must lie in [0,1)")
        if self.overlap_length_policy != "per_line":
            raise EvaluationError("Only overlap_length_policy='per_line' is currently supported")
        if any(size <= 0 for size in self.sensitivity_grid_sizes):
            raise EvaluationError("sensitivity grid sizes must be positive")


@dataclass(frozen=True)
class Swath:
    left_m: float
    right_m: float

    @property
    def width_m(self) -> float:
        return self.left_m + self.right_m


def _swath_at(
    terrain: Terrain,
    x: float,
    y: float,
    tangent_x: float,
    tangent_y: float,
    opening_angle_deg: float,
) -> Swath:
    depth, grad_x, grad_y = terrain.depth_gradient(x, y)
    if depth <= 0:
        raise EvaluationError(f"Non-positive depth {depth} at ({x}, {y})")
    normal_x, normal_y = -tangent_y, tangent_x
    cross_slope = grad_x * normal_x + grad_y * normal_y
    tan_half = math.tan(math.radians(opening_angle_deg) / 2.0)
    left_denominator = 1.0 + cross_slope * tan_half
    right_denominator = 1.0 - cross_slope * tan_half
    if left_denominator <= _EPS or right_denominator <= _EPS:
        raise EvaluationError(
            "Beam/terrain geometry is singular: a swath denominator is non-positive"
        )
    left = depth * tan_half / left_denominator
    right = depth * tan_half / right_denominator
    return Swath(left_m=left, right_m=right)


def _projection_on_segment(segment: Segment, x: float, y: float) -> tuple[float, float, float] | None:
    length_sq = segment.dx * segment.dx + segment.dy * segment.dy
    if length_sq <= _EPS:
        return None
    u = ((x - segment.x1) * segment.dx + (y - segment.y1) * segment.dy) / length_sq
    if u < 0.0 or u > 1.0:
        return None
    px, py = segment.point_at(u)
    tx, ty = segment.unit_tangent()
    nx, ny = -ty, tx
    signed_cross_track = (x - px) * nx + (y - py) * ny
    return px, py, signed_cross_track


def _point_covered_by_line(
    x: float,
    y: float,
    line: SurveyLine,
    terrain: Terrain,
    opening_angle_deg: float,
) -> bool:
    for segment in line.segments:
        projection = _projection_on_segment(segment, x, y)
        if projection is None:
            continue
        px, py, signed_q = projection
        tx, ty = segment.unit_tangent()
        swath = _swath_at(terrain, px, py, tx, ty, opening_angle_deg)
        if -swath.left_m - _EPS <= signed_q <= swath.right_m + _EPS:
            return True
    return False


def _coverage_counts(
    region: Region,
    terrain: Terrain,
    lines: Sequence[SurveyLine],
    opening_angle_deg: float,
    nx: int,
    ny: int,
) -> tuple[int, int, int]:
    covered = 0
    uncovered = 0
    multi = 0
    dx = (region.xmax - region.xmin) / nx
    dy = (region.ymax - region.ymin) / ny
    for j in range(ny):
        y = region.ymin + (j + 0.5) * dy
        for i in range(nx):
            x = region.xmin + (i + 0.5) * dx
            count = sum(
                1
                for line in lines
                if _point_covered_by_line(x, y, line, terrain, opening_angle_deg)
            )
            if count == 0:
                uncovered += 1
            else:
                covered += 1
                if count > 1:
                    multi += 1
    return covered, uncovered, multi


def _clipped_segment_length(segment: Segment, region: Region) -> float:
    """Liang-Barsky clipping length inside an axis-aligned rectangle."""
    p = (-segment.dx, segment.dx, -segment.dy, segment.dy)
    q = (
        segment.x1 - region.xmin,
        region.xmax - segment.x1,
        segment.y1 - region.ymin,
        region.ymax - segment.y1,
    )
    u1, u2 = 0.0, 1.0
    for pi, qi in zip(p, q):
        if abs(pi) <= _EPS:
            if qi < 0:
                return 0.0
            continue
        r = qi / pi
        if pi < 0:
            if r > u2:
                return 0.0
            u1 = max(u1, r)
        else:
            if r < u1:
                return 0.0
            u2 = min(u2, r)
    return max(0.0, u2 - u1) * segment.length


def _line_outside_length(line: SurveyLine, region: Region) -> float:
    inside = sum(_clipped_segment_length(segment, region) for segment in line.segments)
    return max(0.0, line.length - inside)


def _other_lines_overlap_fraction(
    line_index: int,
    segment: Segment,
    u: float,
    terrain: Terrain,
    lines: Sequence[SurveyLine],
    settings: EvaluationSettings,
) -> float:
    x, y = segment.point_at(u)
    tx, ty = segment.unit_tangent()
    nx, ny = -ty, tx
    swath = _swath_at(terrain, x, y, tx, ty, settings.opening_angle_deg)
    width = swath.width_m
    hit = 0
    samples = settings.cross_track_samples
    for k in range(samples):
        q = -swath.left_m + (k + 0.5) * width / samples
        sx, sy = x + q * nx, y + q * ny
        if any(
            idx != line_index
            and _point_covered_by_line(
                sx, sy, other_line, terrain, settings.opening_angle_deg
            )
            for idx, other_line in enumerate(lines)
        ):
            hit += 1
    return hit / samples


def _excess_overlap_length_per_line(
    terrain: Terrain,
    lines: Sequence[SurveyLine],
    settings: EvaluationSettings,
) -> tuple[float, dict[str, float]]:
    per_line: dict[str, float] = {}
    total = 0.0
    for line_index, line in enumerate(lines):
        excess_length = 0.0
        for segment in line.segments:
            interval_count = max(1, math.ceil(segment.length / settings.along_step_m))
            interval_length = segment.length / interval_count
            for interval_index in range(interval_count):
                u = (interval_index + 0.5) / interval_count
                fraction = _other_lines_overlap_fraction(
                    line_index, segment, u, terrain, lines, settings
                )
                if fraction > settings.overlap_threshold + _EPS:
                    excess_length += interval_length
        per_line[line.line_id] = excess_length
        total += excess_length
    return total, per_line


def evaluate(
    region: Region,
    terrain: Terrain,
    lines: Sequence[SurveyLine],
    settings: EvaluationSettings,
) -> dict[str, Any]:
    if not lines:
        raise EvaluationError("At least one survey line is required")

    covered, uncovered, multi = _coverage_counts(
        region,
        terrain,
        lines,
        settings.opening_angle_deg,
        settings.grid_nx,
        settings.grid_ny,
    )
    total_cells = covered + uncovered
    total_length = sum(line.length for line in lines)
    outside_by_line = {
        line.line_id: _line_outside_length(line, region) for line in lines
    }
    outside_total = sum(outside_by_line.values())
    overlap_excess, overlap_by_line = _excess_overlap_length_per_line(
        terrain, lines, settings
    )

    sensitivity = []
    for size in settings.sensitivity_grid_sizes:
        _, uncovered_s, multi_s = _coverage_counts(
            region, terrain, lines, settings.opening_angle_deg, size, size
        )
        count = size * size
        sensitivity.append(
            {
                "grid_nx": size,
                "grid_ny": size,
                "uncovered_area_percent": 100.0 * uncovered_s / count,
                "multiply_covered_area_percent": 100.0 * multi_s / count,
            }
        )

    return {
        "schema_version": 1,
        "evaluator": "independent_multibeam_spatial_coverage",
        "independence_contract": {
            "contains_route_generation": False,
            "candidate_score_reuse": False,
            "input_is_precomputed_line_plan": True,
        },
        "metric_semantics": {
            "uncovered_area": "fraction of rectangular raster cell centers covered by zero swaths",
            "multiply_covered_area": "fraction of raster cell centers covered by at least two swaths",
            "excess_overlap_length": (
                "sum of each survey line's sampled centerline length where more than the "
                "configured threshold of that line's local swath is covered by other lines"
            ),
            "overlap_length_counting_policy": settings.overlap_length_policy,
        },
        "settings": {
            "opening_angle_deg": settings.opening_angle_deg,
            "grid_nx": settings.grid_nx,
            "grid_ny": settings.grid_ny,
            "along_step_m": settings.along_step_m,
            "cross_track_samples": settings.cross_track_samples,
            "overlap_threshold": settings.overlap_threshold,
            "overlap_length_policy": settings.overlap_length_policy,
        },
        "results": {
            "survey_line_count": len(lines),
            "total_survey_line_length_m": total_length,
            "uncovered_area_percent": 100.0 * uncovered / total_cells,
            "multiply_covered_area_percent": 100.0 * multi / total_cells,
            "excess_overlap_length_m": overlap_excess,
            "excess_overlap_length_by_line_m": overlap_by_line,
            "outside_region_line_length_m": outside_total,
            "outside_region_line_length_by_line_m": outside_by_line,
            "boundary_violation": outside_total > 1e-9,
        },
        "grid_sensitivity": sensitivity,
    }


def _parse_terrain(data: dict[str, Any]) -> Terrain:
    terrain_type = data.get("type")
    if terrain_type == "plane":
        origin = data.get("origin", [0.0, 0.0])
        gradient = data.get("gradient", [0.0, 0.0])
        return PlaneTerrain(
            depth_at_origin=float(data["depth_at_origin"]),
            origin_x=float(origin[0]),
            origin_y=float(origin[1]),
            gradient_x=float(gradient[0]),
            gradient_y=float(gradient[1]),
        )
    if terrain_type == "grid":
        return GridTerrain(
            x=tuple(float(value) for value in data["x"]),
            y=tuple(float(value) for value in data["y"]),
            depth=tuple(
                tuple(float(value) for value in row) for row in data["depth"]
            ),
        )
    raise EvaluationError("terrain.type must be 'plane' or 'grid'")


def load_config(path: Path) -> tuple[Region, Terrain, list[SurveyLine], EvaluationSettings]:
    data = json.loads(path.read_text(encoding="utf-8"))
    region_data = data["region"]
    region = Region(
        xmin=float(region_data["xmin"]),
        xmax=float(region_data["xmax"]),
        ymin=float(region_data["ymin"]),
        ymax=float(region_data["ymax"]),
    )
    terrain = _parse_terrain(data["terrain"])
    lines = [
        SurveyLine(
            line_id=str(line["id"]),
            points=tuple((float(p[0]), float(p[1])) for p in line["points"]),
        )
        for line in data["lines"]
    ]
    evaluation_data = data.get("evaluation", {})
    settings = EvaluationSettings(
        opening_angle_deg=float(data["instrument"]["opening_angle_deg"]),
        grid_nx=int(evaluation_data.get("grid_nx", 100)),
        grid_ny=int(evaluation_data.get("grid_ny", 100)),
        along_step_m=float(evaluation_data.get("along_step_m", 5.0)),
        cross_track_samples=int(evaluation_data.get("cross_track_samples", 101)),
        overlap_threshold=float(evaluation_data.get("overlap_threshold", 0.20)),
        overlap_length_policy=str(
            evaluation_data.get("overlap_length_policy", "per_line")
        ),
        sensitivity_grid_sizes=tuple(
            int(value)
            for value in evaluation_data.get(
                "sensitivity_grid_sizes", [50, 100, 200]
            )
        ),
    )
    return region, terrain, lines, settings


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Independently evaluate a precomputed multibeam survey-line plan."
    )
    parser.add_argument("--config", required=True, type=Path, help="JSON evaluation config")
    parser.add_argument("--output", type=Path, help="Optional report JSON path")
    args = parser.parse_args(argv)

    try:
        region, terrain, lines, settings = load_config(args.config)
        report = evaluate(region, terrain, lines, settings)
    except (OSError, KeyError, TypeError, json.JSONDecodeError, EvaluationError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 2

    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
