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
    return re.sub(r"(?<!\\)%.*", "", text)


def _plain_text(block: str) -> str:
    block = re.sub(r"\\(?:begin|end)\{[^}]+\}", " ", block)
    block = re.sub(r"\\[A-Za-z@]+(?:\[[^\]]*\])?", " ", block)
    block = block.replace("{", " ").replace("}", " ")
    block = re.sub(r"\$.*?\$", " ", block, flags=re.S)
    block = re.sub(r"\s+", " ", block)
    return block.strip()


def _short_prose_blocks(clean: str) -> list[str]:
    body = clean.split("\\appendix", 1)[0]
    results: list[str] = []
    for block in re.split(r"\n\s*\n", body):
        if any(token in block for token in (
            "\\section", "\\subsection", "\\subsubsection", "\\caption",
            "\\begin{table", "\\begin{figure", "\\begin{tikzpicture",
            "\\begin{modelsummary}", "\\begin{solvercontract}", "\\keyequation",
            "\\begin{cnabstract}", "\\keywords", "\\papertitle",
        )):
            continue
        plain = _plain_text(block)
        chinese_count = len(re.findall(r"[\u4e00-\u9fff]", plain))
        if 6 <= chinese_count < 35:
            results.append(plain[:80])
    return results


def validate_tex(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    clean = strip_comments(text)
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    if not re.search(r"\\documentclass(?:\[[^\]]*\])?\{shumo-cumcm2025\}", clean):
        errors.append(issue("wrong_document_class", "main source must use shumo-cumcm2025"))
    if "\\tableofcontents" in clean:
        errors.append(issue("table_of_contents_forbidden", "CUMCM electronic paper must not contain a table of contents"))
    if re.search(r"\\author\s*\{", clean):
        errors.append(issue("author_field_forbidden", "electronic paper must not expose author identity"))
    for term in IDENTITY_TERMS:
        if term in clean:
            errors.append(issue("identity_or_front_matter_forbidden", f"forbidden electronic-paper term found: {term}"))

    body_target_match = re.search(r"\\paperbodytarget\{(\d+)\}\{(\d+)\}", clean)
    body_target: tuple[int, int] | None = None
    if not body_target_match:
        errors.append(issue("body_page_target_required", "declare the intended body-page range with \\paperbodytarget{min}{max}"))
    else:
        body_target = (int(body_target_match.group(1)), int(body_target_match.group(2)))
        if body_target[0] <= 0 or body_target[1] < body_target[0]:
            errors.append(issue("invalid_body_page_target", f"invalid body page range: {body_target}"))
        if body_target[1] > 30:
            warnings.append(issue("body_page_target_large", f"declared body target extends beyond 30 pages: {body_target}", severity="warning"))

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
        abstract_chars = len(re.sub(r"\\[A-Za-z@]+(?:\[[^\]]*\])?\{?", "", abstract_text))
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

    model_body = clean
    if "\\section{模型建立与求解}" in clean:
        model_body = clean.split("\\section{模型建立与求解}", 1)[1]
        model_body = model_body.split("\\section{模型检验", 1)[0]
    problem_sections = re.findall(r"\\subsection\{问题(?:[一二三四五六七八九十]+|\d+)[^}]*\}", model_body)
    model_summaries = re.findall(r"\\begin\{modelsummary\}(?:\[[^\]]*\])?", clean)
    solver_blocks = re.findall(r"\\begin\{solvercontract\}(?:\[[^\]]*\])?(.*?)\\end\{solvercontract\}", clean, flags=re.S)
    if problem_sections:
        if len(model_summaries) < len(problem_sections):
            errors.append(issue(
                "model_summary_missing",
                f"each problem subsection requires a modelsummary block: {len(model_summaries)} summaries for {len(problem_sections)} problems",
            ))
        if len(solver_blocks) < len(problem_sections):
            errors.append(issue(
                "solver_contract_missing",
                f"each problem subsection requires a solvercontract block: {len(solver_blocks)} contracts for {len(problem_sections)} problems",
            ))

    for index, block in enumerate(solver_blocks, start=1):
        required_groups = {
            "input_or_initialization": ("\\item[输入]", "\\item[初始化]"),
            "precision": ("\\item[精度]", "\\item[生成精度]", "\\item[评估精度]"),
            "interval_or_stopping": ("\\item[搜索区间]", "\\item[停止区间]", "\\item[停止条件]", "\\item[计算顺序]", "\\item[递推]", "\\item[生成精度]", "\\item[评估精度]"),
            "special_cases": ("\\item[特殊情况]", "\\item[异常处理]"),
        }
        for group, alternatives in required_groups.items():
            if not any(token in block for token in alternatives):
                errors.append(issue(
                    "solver_contract_incomplete",
                    f"solvercontract {index} lacks {group}; expected one of {alternatives}",
                ))

    numbered_equations = len(re.findall(r"\\begin\{equation\*?\}", clean))
    semantic_equations = re.findall(r"\\keyequation\{([^}]+)\}", clean)
    equation_labels = re.findall(r"\\label\{(eq:[^}]+)\}", clean)
    if numbered_equations and not equation_labels:
        errors.append(issue("numbered_equation_without_label", "every numbered equation must have a semantic label"))
    for label in semantic_equations + equation_labels:
        if not re.search(rf"\\(?:eqref|ref|cref)\{{{re.escape(label)}\}}", clean):
            warnings.append(issue("unreferenced_equation", f"numbered equation is not cited in prose: {label}", severity="warning"))

    fig_blocks = re.findall(r"\\begin\{figure\}.*?\\end\{figure\}", clean, flags=re.S)
    for index, block in enumerate(fig_blocks, start=1):
        if "\\caption{" not in block or "\\label{fig:" not in block:
            errors.append(issue("figure_caption_or_label_missing", f"figure {index} lacks a caption or fig: label"))
    table_blocks = re.findall(r"\\begin\{(?:table|longtable)\}.*?\\end\{(?:table|longtable)\}", clean, flags=re.S)
    for index, block in enumerate(table_blocks, start=1):
        if "\\caption{" not in block and index > 1:
            warnings.append(issue("table_caption_missing", f"table-like block {index} has no caption", severity="warning"))

    for graphic in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", clean):
        suffix = Path(graphic).suffix.lower()
        if suffix in RASTER_EXTENSIONS:
            warnings.append(issue("raster_figure", f"raster figure used: {graphic}; vector PDF/SVG/EPS is preferred", severity="warning"))

    short_blocks = _short_prose_blocks(clean)
    if len(short_blocks) > 3:
        warnings.append(issue(
            "fragmented_short_paragraphs",
            f"found {len(short_blocks)} short prose blocks; merge adjacent ideas into cohesive paragraphs. Examples: {short_blocks[:3]}",
            severity="warning",
        ))

    if "\\clearpage\n\\section{" in clean and "\\clearpage\n\\appendix" not in clean:
        warnings.append(issue("appendix_boundary_unclear", "use an explicit clear page before appendix", severity="warning"))

    result = {
        "validator": "shumo_latex_paper_validator",
        "tex": str(path),
        "status": "pass" if not errors else "fail",
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "body_page_target": body_target,
            "problem_section_count": len(problem_sections),
            "model_summary_count": len(model_summaries),
            "solver_contract_count": len(solver_blocks),
            "semantic_equation_count": len(set(semantic_equations + equation_labels)),
            "figure_count": len(fig_blocks),
            "table_like_count": len(table_blocks),
            "short_prose_block_count": len(short_blocks),
        },
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tex", required=True, type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--fail-on-warning", action="store_true")
    args = parser.parse_args()
    result = validate_tex(args.tex)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"{result['status']}: {args.tex} ({result['error_count']} errors, {result['warning_count']} warnings)")
        for item in result["errors"] + result["warnings"]:
            print(f"[{item['severity']}] {item['code']}: {item['message']}")
    if result["status"] != "pass":
        return 1
    if args.fail_on_warning and result["warning_count"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
