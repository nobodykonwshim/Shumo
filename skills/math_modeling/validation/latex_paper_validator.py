#!/usr/bin/env python3
"""Static policy checks for Shumo LaTeX paper sources."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

IDENTITY_TERMS = (
    "参赛学校", "参赛队员", "报名参赛队号", "赛区评阅编号", "全国评阅编号",
    "承诺书", "编号专用页",
)
RASTER_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


def issue(code: str, message: str, *, severity: str = "error") -> dict[str, str]:
    return {"severity": severity, "code": code, "message": message}


def strip_comments(text: str) -> str:
    return re.sub(r"(?<!\\\\)%.*", "", text)


def validate_tex(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    clean = strip_comments(text)
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    if not re.search(r"\\\\documentclass(?:\\[[^\\]]*\\])?\\{shumo-cumcm2025\\}", clean):
        errors.append(issue("wrong_document_class", "main source must use shumo-cumcm2025"))
    if "\\tableofcontents" in clean:
        errors.append(issue("table_of_contents_forbidden", "CUMCM 2025 electronic paper must not contain a table of contents"))
    if re.search(r"\\\\author\\s*\\{", clean):
        errors.append(issue("author_field_forbidden", "electronic paper must not expose author identity"))
    for term in IDENTITY_TERMS:
        if term in clean:
            errors.append(issue("identity_or_front_matter_forbidden", f"forbidden electronic-paper term found: {term}"))

    title_pos = clean.find("\\papertitle")
    abstract_start = clean.find("\\begin{cnabstract}")
    abstract_end = clean.find("\\end{cnabstract}")
    keyword_pos = clean.find("\\keywords")
    first_section = clean.find("\\section{")
    if min(title_pos, abstract_start, abstract_end, keyword_pos) < 0:
        errors.append(issue("missing_abstract_front_page", "title, Chinese abstract and keywords are required"))
    elif not (title_pos < abstract_start < abstract_end < keyword_pos < first_section):
        errors.append(issue("front_page_order", "required order is title -> abstract -> keywords -> body"))
    else:
        abstract_text = clean[abstract_start:abstract_end]
        abstract_chars = len(re.sub(r"\\\\[A-Za-z@]+(?:\\[[^\\]]*\\])?\\{?", "", abstract_text))
        if abstract_chars > 1800:
            warnings.append(issue("abstract_may_exceed_one_page", f"abstract source is long ({abstract_chars} characters)", severity="warning"))

    if "\\appendix" not in clean:
        errors.append(issue("appendix_required", "appendix is required for support-material list and runnable source"))
    if "支撑材料文件列表" not in clean:
        errors.append(issue("support_file_list_required", "appendix must include a support-material file list"))
    if not ("\\lstinputlisting" in clean or "\\begin{lstlisting}" in clean):
        errors.append(issue("source_code_required", "appendix must include complete runnable source code"))
    if not ("\\begin{thebibliography}" in clean or "\\bibliography{" in clean or "\\addbibresource{" in clean):
        errors.append(issue("references_required", "references are required"))

    numbered_equations = len(re.findall(r"\\\\begin\\{equation\\*?\\}", clean))
    semantic_equations = re.findall(r"\\\\keyequation\\{([^}]+)\\}", clean)
    equation_labels = re.findall(r"\\\\label\\{(eq:[^}]+)\\}", clean)
    if numbered_equations and not equation_labels:
        errors.append(issue("numbered_equation_without_label", "every numbered equation must have a semantic label"))
    for label in semantic_equations + equation_labels:
        if not re.search(rf"\\\\(?:eqref|ref|cref)\\{{{re.escape(label)}\\}}", clean):
            warnings.append(issue("unreferenced_equation", f"numbered equation is not cited in prose: {label}", severity="warning"))

    fig_blocks = re.findall(r"\\\\begin\\{figure\\}.*?\\\\end\\{figure\\}", clean, flags=re.S)
    for index, block in enumerate(fig_blocks, start=1):
        if "\\caption{" not in block or "\\label{fig:" not in block:
            errors.append(issue("figure_caption_or_label_missing", f"figure {index} lacks a caption or fig: label"))
    table_blocks = re.findall(r"\\\\begin\\{(?:table|longtable)\\}.*?\\\\end\\{(?:table|longtable)\\}", clean, flags=re.S)
    for index, block in enumerate(table_blocks, start=1):
        if "\\caption{" not in block and index > 1:
            warnings.append(issue("table_caption_missing", f"table-like block {index} has no caption", severity="warning"))

    for graphic in re.findall(r"\\\\includegraphics(?:\\[[^\\]]*\\])?\\{([^}]+)\\}", clean):
        suffix = Path(graphic).suffix.lower()
        if suffix in RASTER_EXTENSIONS:
            warnings.append(issue("raster_figure", f"raster figure used: {graphic}; vector PDF/SVG/EPS is preferred", severity="warning"))

    result = {
        "validator": "shumo_latex_paper_validator",
        "tex": str(path),
        "status": "pass" if not errors else "fail",
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "semantic_equation_count": len(set(semantic_equations + equation_labels)),
            "figure_count": len(fig_blocks),
            "table_like_count": len(table_blocks),
        },
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tex", required=True, type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = validate_tex(args.tex)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"{result['status']}: {args.tex} ({result['error_count']} errors, {result['warning_count']} warnings)")
        for item in result["errors"] + result["warnings"]:
            print(f"[{item['severity']}] {item['code']}: {item['message']}")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
