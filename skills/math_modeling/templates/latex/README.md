# Shumo CUMCM 2025 LaTeX template

## Files

- `shumo-cumcm2025.cls`: A4 layout, 2.5 cm margins, Chinese typography, footer page numbers, captions, tables, listings and equation conventions.
- `main.tex`: minimal electronic-paper skeleton.
- `build.sh`: XeLaTeX build entrypoint.

## Build

```bash
bash build.sh
```

The electronic PDF starts with the abstract page, contains no table of contents, and excludes the commitment and numbering pages.

## Authoring rules

- Use `\keyequation{eq:semantic-id}{...}` only for equations cited later or carrying a core model conclusion.
- Use `\[...\]` or inline math for auxiliary derivations.
- Use `booktabs` tables and automatic figure/table numbering.
- Export Visio, MindMaster, Edraw/AxGlyph and ArcGIS drawings as vector PDF/SVG/EPS and retain editable sources in support materials.
- Run `latex_paper_validator.py` before delivery.
