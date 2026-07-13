# case001 LaTeX paper delivery - complete formula edition

The paper is authored from LaTeX and delivered as PDF.

Build order:

```bash
python solve_case001.py
python make_figures.py
xelatex -interaction=nonstopmode -halt-on-error main.tex
xelatex -interaction=nonstopmode -halt-on-error main.tex
python skills/math_modeling/validation/latex_paper_validator.py \
  --tex main.tex --fail-on-warning
```

The final PDF has 31 pages. Page 1 contains the title, Chinese abstract and keywords. The body starts on page 2. The body and references occupy pages 2-23, so the declared body length is 22 pages and satisfies the user-requested 20-30 page range. The appendix starts on page 24 and contains the support-material list, complete route summary and runnable source code.

Every problem section includes:

- a complete calculable formula chain;
- a model summary;
- an algorithm/solver contract with input or initialization, calculation range or stopping rule, precision and special-case handling;
- quantitative result interpretation and validation.

No table of contents or identity information is included.
