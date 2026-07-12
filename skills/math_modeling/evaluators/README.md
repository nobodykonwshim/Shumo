# Independent mathematical-modeling evaluators

This directory contains deterministic tools for evaluating already-created data, models or route plans. The tools do not choose a final modeling route and do not encode a competition-specific fallback decision.

Case-specific acceptance rules belong in `tests/caseXXX/`; reusable evaluator behavior belongs here.

## 1. Workbook adapter

`xlsx_depth_grid.py` reads a rectangular coordinate/depth matrix directly from an XLSX ZIP/XML package using only Python's standard library. It validates the matrix, converts nautical miles to metres when configured and writes a normalized terrain bundle.

```bash
python skills/math_modeling/evaluators/xlsx_depth_grid.py \
  --input tests/case001/local/problem/附件.xlsx \
  --output tests/case001/local/generated/attachment_terrain.json
```

The adapter fails on missing cells, malformed relationships, non-increasing axes, non-positive depths and non-finite values. It does not generate routes or fit a surface beyond the declared source grid.

## 2. Spatial evaluator

`spatial_coverage.py` evaluates a precomputed line plan. Its input declares:

- a rectangular region;
- an inline or external terrain bundle;
- an instrument opening angle;
- precomputed route geometry;
- sampling and overlap policy.

```bash
python skills/math_modeling/evaluators/spatial_coverage.py \
  --config tests/evaluators/fixtures/flat_complete.json \
  --output /tmp/spatial_report.json
```

The report includes:

- total line length;
- sampled uncovered-area percentage;
- sampled multiply-covered-area percentage;
- excessive-overlap centreline length;
- line length outside the region;
- grid-resolution sensitivity;
- an explicit independence contract.

Overlap semantics are injected by the case contract. For example, case001 uses `ordered_previous_line`; that convention is not a universal rule of the evaluator.

## 3. Explicit route geometry

`skills/math_modeling/geometry/route_geometry.py` provides versioned straight and cubic Bézier segments with deterministic length, tangent, curvature and sampling operations.

The geometry layer exists so that a route can be represented as an explicit finite-curvature object rather than an implicitly smoothed polyline.

## 4. Route feasibility evaluator

`route_feasibility.py` evaluates a precomputed route for tangent continuity and finite-curvature properties.

```bash
python skills/math_modeling/evaluators/route_feasibility.py \
  --candidate <candidate.json> \
  --output <feasibility.json>
```

For a raw polyline, a nonzero heading change at an interior vertex is reported as an exact-geometry failure. That finding applies to the supplied geometry only. It does not reject the underlying route family and does not select a fallback candidate.

For explicit straight/Bézier geometry, the evaluator reports route length, hard-corner count and minimum curvature radius. A minimum operational turning radius is applied only when the case supplies and freezes one.

A failed route may be refined into a new versioned candidate, but the new geometry must be independently re-evaluated for coverage, overlap, boundary compliance and crossings.

## Independence rules

Reusable evaluators must:

- accept precomputed candidates;
- avoid route generation and winner selection;
- expose mathematical and sampling semantics;
- return detectable failure states;
- avoid inventing missing physical constraints;
- remain usable without importing a case directory.

## Tests

```bash
python -m unittest discover -s tests/evaluators -p 'test_*.py' -v
```

The suite covers analytic coverage, overlap, boundary behavior, terrain interpolation, XLSX parsing, explicit route geometry, straight-line feasibility, hard polyline corners and optional turning-radius diagnostics.

## Remaining limits

- Raster coverage is a sampling estimate unless a separate continuous proof is provided.
- Overlap length is controlled by along-track and cross-track sampling.
- Case-specific acceptance thresholds must be declared outside the evaluator.
- Inter-line transit connectors require a separate route-planning contract.
- Passing an evaluator does not prove global optimality or justify a final human decision.
