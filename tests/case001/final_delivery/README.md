# case001 final delivery

## Status

```text
full case solution: complete pending user audit
problem 1: solved
problem 2: solved
problem 3: solved within the declared contour-parallel straight-line family
problem 4: recommended finite-curvature plan selected with conservative fallback
paper: complete DOCX and PDF generated locally
PR: Draft
merge authorized: no
```

This record supersedes the earlier case-cycle label `partial / demonstration_complete` for the **competition deliverable**. The earlier label remains valid only for the bounded Skill-extraction cycle; it is not the status of the completed case solution.

## Problem 4 final recommendation

- selected candidate: `P4-CAND-C-SMOOTH-05`
- fallback: `P4-CAND-A`
- survey-line count: `61`
- explicit finite-curvature geometry length: `576726.6355123592 m`
- independent spatial-evaluator length: `576725.7292825343 m`
- nominal sampled uncovered area: `0.0%`
- route length associated with overlap above 20%: `339556.4072993089 m`
- minimum curvature radius: `225.98306382015713 m`
- hard corners: `0`
- route crossings: `0`

The `70 x 70` sensitivity grid reports `0.04081632653061224%` uncovered area. This adverse result is retained. The final paper therefore does not claim continuous coverage, global optimality, or vessel-specific turning-radius compliance.

## Conservative fallback

Candidate `P4-CAND-A` uses 67 full-height north-south lines and has a total length of `620420 m`. It remains the conservative fallback because every declared sensitivity grid reports zero sampled uncovered area.

## Local final artifacts

Binary deliverables remain local and are identified by SHA-256 in `FINAL_DELIVERY_MANIFEST.yaml`:

- complete paper in DOCX and PDF;
- official-format problem-1 workbook;
- official-format problem-2 workbook;
- problem-4 route and metrics workbook;
- machine-readable final metrics and route station matrix;
- final self-check report and combined delivery ZIP.

## Reproducibility code

The implementation and regression evidence remain on this branch. The principal reusable components are:

```text
skills/math_modeling/evaluators/xlsx_depth_grid.py
skills/math_modeling/evaluators/spatial_coverage.py
skills/math_modeling/evaluators/route_feasibility.py
skills/math_modeling/geometry/route_geometry.py
tests/case001/run/problem4_candidates/generate_candidates.py
tests/case001/run/problem4_candidates/
```

The route generator and evaluator are separate. Geometry feasibility, spatial coverage, sensitivity, and final claim boundaries are recorded independently.
