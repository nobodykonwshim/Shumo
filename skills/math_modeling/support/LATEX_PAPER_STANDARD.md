# Shumo LaTeX paper-writing standard

## 1. Source-of-truth rule

All formal mathematical-modeling papers must use LaTeX as the only editable paper source.

```text
frozen modeling package
-> paper blueprint
-> main.tex + class + vector figures + data tables
-> XeLaTeX build
-> PDF preflight and page render
-> PDF delivery
```

DOCX is not a primary paper source. It may be generated only when a user separately requests a Word copy, and it must not replace the reviewed LaTeX source.

## 2. CUMCM 2025 electronic-paper format

The default format is derived from the user-supplied `format2025.doc` and must satisfy:

- A4 paper;
- top, bottom, left and right margins each at least 2.5 cm;
- the electronic PDF does not contain the commitment page or numbering page;
- page 1 is the title, Chinese abstract and keywords;
- the abstract, including title and keywords, fits on one page;
- Arabic page numbering starts at 1 on the abstract page and is centered in the footer;
- the body starts on page 2;
- no table of contents;
- the body should normally remain within 20 pages; appendices are not included in this preferred limit;
- the appendix lists support-material files and includes complete runnable source code used by the model;
- no team, school, region or other identity information appears in the electronic paper or support files;
- every external result or public source is cited in the text and listed in the references;
- the final paper is a single PDF no larger than 20 MB.

When a competition or regional rule conflicts with this default, the newer or more specific official rule controls and the override must be recorded.

## 3. Formula policy

- Only a core model equation, a formula cited later, or a formula that carries a principal conclusion receives a displayed number.
- Every numbered formula has a semantic `\label{eq:...}` and is cited in the prose.
- Auxiliary transformations, intermediate equalities and one-use substitutions remain inline or use unnumbered display math.
- Every symbol is introduced before or at its first use; global symbols also appear in the symbol table.
- Units, domains, sign conventions and coordinate directions are stated before formulas depend on them.
- A derivation may omit routine algebra, but it may not skip a modeling assumption, variable definition or logical implication.

The provided class exposes `\keyequation{label}{formula}` for numbered core formulas. Ordinary `\[ ... \]` is used for unnumbered relations.

## 4. Structure and expression

The normal order is:

1. title, abstract and keywords;
2. problem restatement;
3. problem analysis;
4. assumptions;
5. symbol table;
6. model establishment, solution and result analysis for each subproblem;
7. model validation and discussion;
8. model evaluation;
9. conclusion;
10. references;
11. appendix and support-material file list.

Each subproblem must identify the question being answered, derive the model, state the solution procedure, report quantitative results, interpret those results and directly answer the corresponding task. Writing must use connected paragraphs rather than a sequence of short unsupported statements.

## 4.1 Complete calculable model chain

Every subproblem must be written as a complete calculable chain rather than a sequence of conclusions. The paper must:

- define the coordinate convention, data domain, units and sign convention before formulas use them;
- introduce every symbol before or at its first formula occurrence;
- show how each intermediate variable is obtained from previously defined inputs or formulas;
- give explicit formulas for quantities required by the algorithm, including interpolation, projection, objective, constraints, stopping conditions and validation metrics;
- state feasibility domains and singular cases;
- avoid phrases such as “similarly obtained” when the omitted relation is necessary for independent reproduction.

A derivation may keep one-use algebraic identities inline, but the complete dependency chain from input to output must remain visible.

## 4.2 Model summary and solver contract

Each problem subsection must contain exactly identifiable model and solver summaries. The class provides:

```latex
\begin{modelsummary}[问题一模型归纳]
...
\end{modelsummary}

\begin{solvercontract}[问题一算法求解说明]
\item[输入] ...
\item[搜索区间] ...
\item[精度] ...
\item[特殊情况] ...
\end{solvercontract}
```

The model summary states the input-to-state-to-output mapping, objective, constraints and claim boundary. The solver contract states inputs or initialization, calculation order or search interval, numerical precision, stopping criteria and special-case handling. A named algorithm without these details is incomplete.

## 4.3 Paragraph cohesion and result depth

Body text must use cohesive paragraphs. A sequence of one-sentence paragraphs or short declarative fragments is not acceptable. Each result analysis should normally include:

1. the quantitative result;
2. the mathematical or physical reason for the observed trend;
3. a direct answer to the corresponding task;
4. an uncertainty, boundary or failure discussion where applicable.

The static validator warns when prose is excessively fragmented.

## 4.4 Declared body-page target

Every paper declares its intended body-page range with `\paperbodytarget{min}{max}`. The default CUMCM baseline remains “normally within 20 pages”. A user may explicitly request a different project target; that override must be recorded rather than silently represented as the official default. The compiled PDF, not the source declaration, determines actual compliance.

## 5. Figure and table policy

- Every figure and table is cited in the body before or near its appearance.
- Every figure has a numbered caption, axis labels, units, legend when needed, and a short interpretation in the prose.
- Every table uses a consistent three-line style unless the content requires a different scientific layout.
- Figure and table numbering is automatic in LaTeX; manual numbering is forbidden.
- Preferred editable sources are:
  - flowcharts: Microsoft Visio;
  - mind maps: MindMaster;
  - vector geometry and schematic diagrams: Edraw or AxGlyph;
  - geographic maps: ArcGIS.
- Editable source files and exported vector assets must be retained in support materials.
- The paper includes vector PDF/SVG/EPS assets whenever possible. Raster PNG/JPEG is reserved for inherently raster data.
- When the required proprietary application is unavailable in an automated environment, TikZ/PGFPlots may be used as a declared deterministic vector fallback; the output must not be misrepresented as having been authored in Visio, MindMaster, Edraw, AxGlyph or ArcGIS.

## 6. Validation and discussion

Every result section must include applicable checks such as:

- analytic limit or dimensional consistency;
- structural symmetry or invariance;
- independent recalculation;
- boundary and feasibility checks;
- residual, error or constraint violation;
- predeclared parameter, grid, step-size or initial-value sensitivity;
- comparison with a baseline or conservative fallback.

Unfavorable validation results remain in the paper. Sampled evidence must not be described as a proof, route-family optimality must not be described as global optimality, and omitted physical constraints must be stated.

## 7. Build and delivery gate

The standard build is:

```bash
python make_figures.py
xelatex -interaction=nonstopmode -halt-on-error main.tex
xelatex -interaction=nonstopmode -halt-on-error main.tex
python skills/math_modeling/validation/latex_paper_validator.py --tex main.tex
```

Before delivery:

- the PDF opens successfully;
- all pages are rendered to images and visually inspected;
- there is no clipped text, overlap, blank accidental page, broken glyph, missing reference or unresolved label;
- the first page contains only title, abstract and keywords;
- there is no table of contents or identity information;
- the main body and appendix boundary is recorded;
- numerical values match frozen artifacts;
- final PDF size is below the competition limit.

The user-facing default delivery is PDF. LaTeX source or a source package may accompany it, but does not replace the PDF.
