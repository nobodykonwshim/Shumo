#!/usr/bin/env python3
"""Static and numerical consistency checks for the problem-1 LaTeX fragment."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


REQUIRED_LABELS = {
    "eq:p1-missile",
    "eq:p1-uav",
    "eq:p1-bomb",
    "eq:p1-smoke",
    "eq:p1-occlusion",
    "eq:p1-duration",
    "tab:p1-results",
    "tab:p1-results-centre",
}

REQUIRED_HEADINGS = (
    "问题一题目解读",
    "模型假设",
    "运动关系与遮蔽判据",
    "数值求解",
    "结果与简短分析",
    "针对问题一的摘要素材",
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


def check(tex_path: Path, result_path: Path) -> dict:
    tex = tex_path.read_text(encoding="utf-8")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    labels = re.findall(r"\\label\{([^}]+)\}", tex)
    duplicates = sorted({label for label in labels if labels.count(label) > 1})
    if duplicates:
        errors.append({"code": "duplicate_labels", "message": str(duplicates)})
    missing_labels = sorted(REQUIRED_LABELS - set(labels))
    if missing_labels:
        errors.append({"code": "missing_labels", "message": str(missing_labels)})

    references = set(re.findall(r"\\(?:eqref|ref)\{([^}]+)\}", tex))
    missing_references = sorted(references - set(labels))
    if missing_references:
        errors.append({"code": "unresolved_references", "message": str(missing_references)})
    unreferenced_equations = sorted(
        label for label in labels if label.startswith("eq:") and label not in references
    )
    if unreferenced_equations:
        errors.append({"code": "unreferenced_equations", "message": str(unreferenced_equations)})

    for heading in REQUIRED_HEADINGS:
        if heading not in tex:
            errors.append({"code": "missing_heading", "message": heading})

    for environment in ("equation", "enumerate", "table", "tabular"):
        begins = len(re.findall(rf"\\begin\{{{environment}\}}", tex))
        ends = len(re.findall(rf"\\end\{{{environment}\}}", tex))
        if begins != ends:
            errors.append(
                {
                    "code": "unbalanced_environment",
                    "message": f"{environment}: {begins} begins, {ends} ends",
                }
            )

    forbidden = ("\\papertitle", "\\keywords", "\\begin{cnabstract}", "\\tableofcontents")
    for token in forbidden:
        if token in tex:
            errors.append({"code": "out_of_scope_front_matter", "message": token})

    macros = extract_macros(tex)
    expected = {
        "PoneFullStart": rounded(result["full_cylinder"]["start_s"]),
        "PoneFullEnd": rounded(result["full_cylinder"]["end_s"]),
        "PoneFullDuration": rounded(result["full_cylinder"]["duration_s"]),
        "PoneCentreStart": rounded(result["target_centre_line_of_sight"]["start_s"]),
        "PoneCentreEnd": rounded(result["target_centre_line_of_sight"]["end_s"]),
        "PoneCentreDuration": rounded(result["target_centre_line_of_sight"]["duration_s"]),
        "PoneDurationDifference": rounded(result["comparison"]["centre_minus_full_duration_s"]),
    }
    for name, value in expected.items():
        if macros.get(name) != value:
            errors.append(
                {
                    "code": "result_macro_mismatch",
                    "message": f"{name}: expected {value}, found {macros.get(name)!r}",
                }
            )

    exact_strings = {
        "PoneReleasePoint": r"(17620,\,0,\,1800)",
        "PoneBurstTime": "5.1",
        "PoneBurstPoint": r"(17188,\,0,\,1736.496)",
    }
    for name, value in exact_strings.items():
        if macros.get(name) != value:
            errors.append(
                {
                    "code": "hand_check_macro_mismatch",
                    "message": f"{name}: expected {value}, found {macros.get(name)!r}",
                }
            )

    if "\\mathrm s" not in tex and "\\mathrm{s}" not in tex:
        errors.append({"code": "time_unit_missing", "message": "LaTeX fragment does not show second units"})
    if "\\mathrm m" not in tex and "\\mathrm{m}" not in tex:
        errors.append({"code": "length_unit_missing", "message": "LaTeX fragment does not show metre units"})

    return {
        "schema_version": 1,
        "validator": "case002_problem1_paper_check",
        "tex": str(tex_path),
        "result": str(result_path),
        "status": "pass" if not errors else "fail",
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "label_count": len(labels),
            "equation_label_count": len([label for label in labels if label.startswith("eq:")]),
            "result_macros_checked": len(expected),
            "full_duration_s": result["full_cylinder"]["duration_s"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tex", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = check(args.tex, args.result)
    output = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
