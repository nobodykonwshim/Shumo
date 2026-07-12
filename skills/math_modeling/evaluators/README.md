# Independent multibeam evaluators

This directory contains deterministic tools that evaluate already-created data or line plans. They contain no route generation, optimization, terrain fitting or candidate scoring logic.

## 1. Workbook adapter

`xlsx_depth_grid.py` reads the official depth workbook directly from the XLSX ZIP/XML package using only Python's standard library. It validates the expected coordinate/depth matrix, converts nautical miles to metres and writes a normalized terrain bundle.

```bash
python skills/math_modeling/evaluators/xlsx_depth_grid.py \
  --input tests/case001/local/problem/附件.xlsx \
  --output tests/case001/local/generated/attachment_terrain.json
```

The adapter fails on missing depth cells, nonuniform or non-increasing axes, non-positive depths, unexpected headings, malformed XLSX relationships or non-finite values. It does not smooth, interpolate beyond the source grid, fit surfaces or generate routes.

## 2. Spatial evaluator

`spatial_coverage.py` evaluates a precomputed multibeam line plan. Its JSON config contains:

- an axis-aligned rectangular region in metres;
- either an inline plane/grid terrain or `terrain_file` pointing to an adapter bundle;
- a transducer opening angle;
- one or more precomputed survey polylines;
- raster, along-track and cross-track sampling settings.

The regular grid uses positive-down depth and `depth[j][i]` ordering for `y[j], x[i]`. Coordinates must be strictly increasing.

```bash
python skills/math_modeling/evaluators/spatial_coverage.py \
  --config tests/evaluators/fixtures/flat_complete.json \
  --output /tmp/spatial_report.json
```

It reports:

- total survey-line length;
- rasterized uncovered-area percentage;
- rasterized multiply-covered-area percentage;
- excessive-overlap centerline length;
- line length outside the target rectangle;
- grid-resolution sensitivity;
- an explicit independence contract.

## Frozen problem-4 overlap convention

The case001 reporting policy is `ordered_previous_line`:

1. input lines must be ordered by spatial adjacency of survey strips;
2. the first line contributes zero excessive-overlap length;
3. for each later line, sample its centreline;
4. at each sample, compute the fraction of that line's local swath covered by the immediately preceding line;
5. count the sampled centreline interval once when that fraction is greater than 20%.

This avoids counting one physical adjacent-pair overlap on both lines and matches the ordered phrase “与前一条测线”. The older `per_line` policy remains available only for compatibility and may double-count.

## Geometry

At a sampled line point, the terrain is locally approximated by its depth gradient. In the vertical plane normal to the line, with signed slope `s` and half-opening tangent `t`, horizontal half-swaths are:

```text
left  = D t / (1 + s t)
right = D t / (1 - s t)
```

A non-positive denominator is rejected as singular beam/terrain geometry.

## Tests

```bash
python -m unittest discover -s tests/evaluators -p 'test_*.py' -v
```

The suite covers analytic coverage/overlap/boundary cases, grid interpolation, singular geometry, external terrain bundles, XLSX parsing, unit conversion and malformed/missing workbook data.

## Remaining limits

- Coverage area is a cell-centre raster estimate; every final result must include grid sensitivity.
- Overlap length is an along-line/cross-track sampling estimate controlled by `along_step_m` and `cross_track_samples`.
- The evaluator accepts precomputed plans only and must remain independent from Route Explorer.
- A real attachment smoke test validates ingestion and runtime, not route quality.
