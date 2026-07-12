# Independent spatial evaluator

`spatial_coverage.py` evaluates an already-created multibeam survey-line plan. It contains no route-generation or optimization logic and must not import candidate scoring code.

## Inputs

A UTF-8 JSON file containing:

- an axis-aligned rectangular region in metres;
- a terrain represented either as a plane or a regular grid;
- a transducer opening angle;
- one or more precomputed survey polylines;
- raster, along-track and cross-track sampling settings.

The regular grid uses positive-down depth and `depth[j][i]` ordering for `y[j], x[i]`. Coordinates must be strictly increasing.

## Outputs

The evaluator reports:

- total survey-line length;
- rasterized uncovered-area percentage;
- rasterized multiply-covered-area percentage;
- length of each survey line for which more than the configured fraction of its local swath is already covered by other lines;
- line length outside the target rectangle;
- grid-resolution sensitivity results;
- an explicit independence contract.

The current `excess_overlap_length_m` policy is `per_line`: an overlap can contribute once on each participating survey line. This is deliberately explicit because the contest phrase “重叠率超过 20% 部分的总长度” is otherwise ambiguous. A project must freeze its reporting convention before comparing candidate plans.

## Geometry

At a sampled line point, the terrain is locally approximated by its depth gradient. In the vertical plane normal to the line, with signed slope `s` and half-opening tangent `t`, the horizontal half-swaths are

```text
left  = D t / (1 + s t)
right = D t / (1 - s t)
```

A non-positive denominator is treated as an invalid or singular beam/terrain configuration.

## Run

```bash
python skills/math_modeling/evaluators/spatial_coverage.py \
  --config tests/evaluators/fixtures/flat_complete.json \
  --output /tmp/spatial_report.json
```

Run the analytic regression tests with:

```bash
python -m unittest discover -s tests/evaluators -v
```

## Phase-1 limits

- The core accepts plane or JSON regular-grid terrain; direct `附件.xlsx` ingestion is not yet part of this module.
- Coverage area is a cell-centre raster estimate, so grid sensitivity must be reported.
- Overlap length is an along-line sampling estimate controlled by `along_step_m` and `cross_track_samples`.
- The evaluator accepts precomputed line plans only. It must remain independent from Route Explorer and optimization implementations.
- Passing the synthetic tests does not unblock problem 4 by itself. The real attachment adapter, metric convention approval, performance check and Agent tool contracts are still required.
