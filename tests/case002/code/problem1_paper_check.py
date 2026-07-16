#!/usr/bin/env python3
"""Static and numerical consistency checks for problem-1 revision-2 LaTeX."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


REQUIRED_LABELS = {
    "eq:p1-motion",
    "eq:p1-bomb",
    "eq:p1-smoke",
    "eq:p1-view-matrix",
    "eq:p1-perspective",
    "eq:p1-smoke-conic",
    "eq:p1-coverage",
    "eq:p1-duration",
    "tab:p1-projection-results",
}

ANALYSIS_HEADINGS = (
    r"\section{问题分析}",
    r"\subsection{问题一分析}",
)

MODEL_HEADINGS = (
    r"\section{模型的建立与求解}",
    r"\subsection{问题一的模型建立与求解}",
    r"\subsubsection{问题模型建立}",
    r"\subsubsection{模型求解}",
    r"\subsubsection{结果分析}",
)


def rounded(value: float) -> str:
    return f"{value:.3f}"


def extract_macros(tex: str) -> dict[str, str]:
    return dict(
        re.findall(
            r"\\providecommand\{\\([A-Za-z]+)\}\{([^{}]*)\}",
            tex,
        )
    )


def ordered(text: str, tokens: tuple[str, ...]) -> bool:
    offset = -1
    for token in tokens:
        offset = text.find(token, offset + 1)
        if offset < 0:
            return False
    return True


def add_error(errors: list[dict[str, str]], code: str, message: str) -> None:
    errors.append({"code": code, "message": message})


def check(
    analysis_path: Path,
    model_path: Path,
    result_path: Path,
    *,
    repo_root: Path,
) -> dict:
    analysis = analysis_path.read_text(encoding="utf-8")
    model = model_path.read_text(encoding="utf-8")
    combined = analysis + "\n" + model
    result = json.loads(result_path.read_text(encoding="utf-8"))
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    if not ordered(analysis, ANALYSIS_HEADINGS):
        add_error(errors, "analysis_heading_contract", str(ANALYSIS_HEADINGS))
    if not ordered(model, MODEL_HEADINGS):
        add_error(errors, "model_heading_contract", str(MODEL_HEADINGS))

    labels = re.findall(r"\\label\{([^}]+)\}", combined)
    duplicates = sorted({label for label in labels if labels.count(label) > 1})
    if duplicates:
        add_error(errors, "duplicate_labels", str(duplicates))
    missing_labels = sorted(REQUIRED_LABELS - set(labels))
    if missing_labels:
        add_error(errors, "missing_labels", str(missing_labels))

    references = set(re.findall(r"\\(?:eqref|ref|cref)\{([^}]+)\}", combined))
    unresolved = sorted(references - set(labels))
    if unresolved:
        add_error(errors, "unresolved_references", str(unresolved))
    unreferenced_equations = sorted(
        label for label in labels if label.startswith("eq:") and label not in references
    )
    if unreferenced_equations:
        add_error(errors, "unreferenced_equations", str(unreferenced_equations))

    for environment in ("equation", "table", "tabular", "cases", "bmatrix"):
        begins = len(re.findall(rf"\\begin\{{{environment}\}}", combined))
        ends = len(re.findall(rf"\\end\{{{environment}\}}", combined))
        if begins != ends:
            add_error(
                errors,
                "unbalanced_environment",
                f"{environment}: {begins} begins, {ends} ends",
            )

    for token in (
        r"\papertitle",
        r"\keywords",
        r"\begin{cnabstract}",
        r"\tableofcontents",
    ):
        if token in combined:
            add_error(errors, "out_of_scope_front_matter", token)

    for token in (
        r"\section{模型假设}",
        r"\subsection{模型假设}",
        r"\begin{assumption}",
    ):
        if token in combined:
            add_error(errors, "assumptions_must_stay_in_registry", token)

    # Problem analysis is qualitative. Parameter values are reserved for the
    # result macros and table, never introduced in chapter 2.
    analysis_without_comments = re.sub(r"(?m)(?<!\\)%.*$", "", analysis)
    analysis_numbers = re.findall(r"(?<![A-Za-z])\d+(?:\.\d+)?", analysis_without_comments)
    if analysis_numbers:
        add_error(
            errors,
            "numeric_parameter_in_analysis",
            str(sorted(set(analysis_numbers))),
        )

    macros = extract_macros(model)
    coverage = result["full_projection_coverage"]
    expected_results = {
        "PoneCoverageStart": rounded(coverage["start_s"]),
        "PoneCoverageEnd": rounded(coverage["end_s"]),
        "PoneCoverageDuration": rounded(coverage["duration_s"]),
    }
    for name, value in expected_results.items():
        if macros.get(name) != value:
            add_error(
                errors,
                "result_macro_mismatch",
                f"{name}: expected {value}, found {macros.get(name)!r}",
            )

    exact_hand_checks = {
        "PoneReleasePoint": r"(17620,\,0,\,1800)",
        "PoneBurstTime": "5.1",
        "PoneBurstPoint": r"(17188,\,0,\,1736.496)",
    }
    for name, value in exact_hand_checks.items():
        if macros.get(name) != value:
            add_error(
                errors,
                "hand_check_macro_mismatch",
                f"{name}: expected {value}, found {macros.get(name)!r}",
            )

    if r"\mathrm s" not in model and r"\mathrm{s}" not in model:
        add_error(errors, "time_unit_missing", "model section does not show seconds")
    if r"\mathrm m" not in model and r"\mathrm{m}" not in model:
        add_error(errors, "length_unit_missing", "model section does not show metres")

    sys.path.insert(0, str(repo_root / "skills" / "math_modeling" / "validation"))
    from symbolic_latex_validator import validate_symbolic_latex  # noqa: PLC0415

    symbolic = validate_symbolic_latex(analysis, model, problem_name="问题一")
    if symbolic["status"] != "pass":
        for issue in symbolic["errors"]:
            add_error(
                errors,
                f"symbolic_contract:{issue['code']}",
                issue["message"],
            )

    validation = result.get("validation", {})
    if not validation.get("all_required_checks_pass"):
        add_error(errors, "numerical_validation_failed", str(validation))

    return {
        "schema_version": 2,
        "validator": "case002_problem1_paper_check",
        "analysis_tex": str(analysis_path),
        "model_tex": str(model_path),
        "result": str(result_path),
        "status": "pass" if not errors else "fail",
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "label_count": len(labels),
            "equation_label_count": len(
                [label for label in labels if label.startswith("eq:")]
            ),
            "result_macros_checked": len(expected_results),
            "coverage_duration_s": coverage["duration_s"],
            "symbolic_contract_status": symbolic["status"],
            "projection_containment_pass": validation.get(
                "projection_containment_midpoint_pass"
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis-tex", type=Path, required=True)
    parser.add_argument("--model-tex", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = check(
        args.analysis_tex,
        args.model_tex,
        args.result,
        repo_root=args.repo_root,
    )
    output = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
