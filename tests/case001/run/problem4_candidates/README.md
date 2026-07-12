# Problem 4 bounded candidate set

This directory records the outputs of admitted task `A-P4-ROUTE-01`.

## Reproduce expanded plans

The official workbook is local-only. After creating the normalized terrain bundle, run:

```bash
python tests/case001/run/problem4_candidates/generate_candidates.py \
  --terrain tests/case001/local/generated/attachment_terrain.json \
  --evaluator skills/math_modeling/evaluators/spatial_coverage.py \
  --output-dir tests/case001/run/problem4_candidates/generated \
  --gate-token fb6ad580bf4ed679cea0714eb64e1d65ebaa20e4367be38bf4584db83ffc051c
```

Then evaluate each generated JSON with `spatial_coverage.py` using its frozen settings. Full expanded plans and full reports are not committed; their SHA-256 values and result summaries are recorded in `candidate_set_manifest.yaml`.

## Boundaries

- Same-problem references and web solutions were unavailable during generation.
- The generator does not select a winner.
- The evaluator contains no route-generation logic.
- No candidate is claimed globally optimal.
- Candidate C requires an additional vessel-curvature feasibility model before it can be selected.
