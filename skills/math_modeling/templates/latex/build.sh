#!/usr/bin/env bash
set -euo pipefail

if [[ -f make_figures.py ]]; then
  python make_figures.py
fi

xelatex -interaction=nonstopmode -halt-on-error main.tex
xelatex -interaction=nonstopmode -halt-on-error main.tex
python ../../validation/latex_paper_validator.py --tex main.tex
