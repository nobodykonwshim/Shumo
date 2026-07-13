# case001 final delivery

## Status

```text
full case solution: complete pending user audit
problem 1: solved
problem 2: solved
problem 3: solved within the declared contour-parallel straight-line family
problem 4: recommended finite-curvature plan selected with conservative fallback
paper source of truth: LaTeX
paper delivery: PDF
PR: Draft
merge authorized: no
```

This record supersedes the earlier case-cycle label `partial / demonstration_complete` for the **competition deliverable**. The earlier label remains valid only for the bounded Skill-extraction cycle; it is not the status of the completed case solution.

## Paper source and format

The authoritative paper is under:

```text
tests/case001/final_delivery/latex/
```

It is built with XeLaTeX from modular `main.tex` and `sections/*.tex` sources using `shumo-cumcm2025.cls`. The electronic PDF follows the user-supplied CUMCM 2025 baseline and the explicit complete-formula revision:

- A4 and 2.5 cm margins;
- title, Chinese abstract and keywords on page 1;
- body starts on page 2;
- no table of contents;
- centered Arabic page numbers;
- body and references occupy pages 2-21, exactly 20 pages;
- appendices occupy pages 22-28;
- complete runnable source and support-material list in appendices;
- no identity information;
- PDF below 20 MB.

Every problem includes a complete calculable dependency chain, a model-summary block, an algorithm/solver contract with precision and special-case handling, quantitative result analysis and an applicable validation discussion. DOCX files generated in an earlier iteration are historical artifacts and are no longer the paper source of truth.

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

## Reproducibility

The LaTeX source directory includes:

- the complete modular paper source and class;
- complete result-reproduction and audit code;
- vector-figure generation code;
- route-summary rows;
- frozen problem-4 metric and route data;
- source and delivery hashes in `PAPER_SOURCE_MANIFEST.yaml`.

The route generator and evaluator remain separate. Geometry feasibility, spatial coverage, sensitivity and final claim boundaries are recorded independently.

## Figure-source disclosure

Visio, MindMaster, Edraw/AxGlyph and ArcGIS are the preferred editable drawing tools established by the user. They were not available in the automated execution environment. The current paper uses TikZ for flowcharts and Matplotlib vector PDF for quantitative figures, and this fallback is disclosed rather than misrepresented as proprietary-tool output.
