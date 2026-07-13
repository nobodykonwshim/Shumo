# case001 LaTeX paper delivery

The reviewed paper is authored from LaTeX and delivered as PDF.

Build order:

```bash
python solve_case001.py
python make_figures.py
xelatex -interaction=nonstopmode -halt-on-error main.tex
xelatex -interaction=nonstopmode -halt-on-error main.tex
python skills/math_modeling/validation/latex_paper_validator.py --tex main.tex
```

The final electronic PDF has 20 pages in total. Page 1 contains the title, Chinese abstract and keywords; the body starts on page 2; there is no table of contents; the appendix starts after the 12-page paper body and references.

The source package and final PDF are local deliverables whose hashes are recorded in `PAPER_SOURCE_MANIFEST.yaml`.

## Figure-source disclosure

The user-selected preferred drawing tools are Visio for flowcharts, MindMaster for mind maps, Edraw/AxGlyph for vector diagrams, and ArcGIS for geographic maps. These proprietary applications were not available in the automated execution environment. The current paper therefore uses TikZ for flowcharts and Matplotlib PDF output for quantitative vector figures. This fallback is explicitly disclosed and is not represented as proprietary-tool authorship.
