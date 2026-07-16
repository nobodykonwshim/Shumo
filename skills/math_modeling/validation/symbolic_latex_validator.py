#!/usr/bin/env python3
"""Validate symbolic per-problem LaTeX section contracts."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


BEGIN = "% SHUMO-SYMBOLIC-MODEL-BEGIN"
END = "% SHUMO-SYMBOLIC-MODEL-END"
ALLOWED_STRUCTURAL_NUMBERS = {"0", "1", "2"}


def _issue(code: str, path: str, message: str) -> dict[str, str]:
    return {"code": code, "path": path, "message": message}


def _ordered(text: str, tokens: list[str]) -> bool:
    position = -1
    for token in tokens:
        position = text.find(token, position + 1)
        if position < 0:
            return False
    return True


def validate_symbolic_latex(
    analysis_text: str,
    model_text: str,
    *,
    problem_name: str,
) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    analysis_contract = [
        r"\section{问题分析}",
        rf"\subsection{{{problem_name}分析}}",
    ]
    if not _ordered(analysis_text, analysis_contract):
        errors.append(
            _issue(
                "analysis_section_contract",
                "analysis",
                f"expected ordered headings: {analysis_contract}",
            )
        )

    model_contract = [
        r"\section{模型的建立与求解}",
        rf"\subsection{{{problem_name}的模型建立与求解}}",
        r"\subsubsection{问题模型建立}",
        r"\subsubsection{模型求解}",
        r"\subsubsection{结果分析}",
    ]
    if not _ordered(model_text, model_contract):
        errors.append(
            _issue(
                "model_section_contract",
                "model",
                f"expected ordered headings: {model_contract}",
            )
        )

    combined = analysis_text + "\n" + model_text
    for forbidden in (
        r"\section{模型假设}",
        r"\subsection{模型假设}",
        r"\begin{assumption}",
    ):
        if forbidden in combined:
            errors.append(
                _issue(
                    "registry_only_assumption_violation",
                    "latex",
                    f"assumption content must remain in the registry: {forbidden}",
                )
            )

    if model_text.count(BEGIN) != 1 or model_text.count(END) != 1:
        errors.append(
            _issue(
                "symbolic_markers",
                "model",
                "model text must contain exactly one symbolic model begin/end marker pair",
            )
        )
        symbolic_block = ""
    else:
        begin = model_text.index(BEGIN) + len(BEGIN)
        end = model_text.index(END, begin)
        symbolic_block = model_text[begin:end]

    cleaned = re.sub(r"(?<!\\)%.*", "", symbolic_block)
    cleaned = re.sub(r"\\(?:label|ref|eqref|cref)\{[^}]+\}", "", cleaned)
    numeric_tokens = re.findall(
        r"(?<![A-Za-z])\d+(?:\.\d+)?(?:[eE][+-]?\d+)?", cleaned
    )
    disallowed = sorted(
        {token for token in numeric_tokens if token not in ALLOWED_STRUCTURAL_NUMBERS}
    )
    if disallowed:
        errors.append(
            _issue(
                "numeric_parameter_in_model",
                "model.symbolic_block",
                f"case-specific numeric literals found in model establishment: {disallowed}",
            )
        )

    if symbolic_block and not (
        r"\bm" in symbolic_block or r"\boldsymbol" in symbolic_block
    ):
        errors.append(
            _issue(
                "vector_notation_missing",
                "model.symbolic_block",
                "symbolic model must use explicit vector notation",
            )
        )

    labels = re.findall(r"\\label\{([^}]+)\}", combined)
    duplicates = sorted({label for label in labels if labels.count(label) > 1})
    if duplicates:
        errors.append(_issue("duplicate_labels", "latex", str(duplicates)))
    references = set(re.findall(r"\\(?:eqref|ref|cref)\{([^}]+)\}", combined))
    unresolved = sorted(references - set(labels))
    if unresolved:
        errors.append(_issue("unresolved_references", "latex", str(unresolved)))

    return {
        "schema_version": 1,
        "validator": "shumo_symbolic_latex_validator",
        "status": "pass" if not errors else "fail",
        "problem_name": problem_name,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "label_count": len(labels),
            "symbolic_numeric_tokens": numeric_tokens,
            "disallowed_numeric_tokens": disallowed if symbolic_block else [],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis-tex", type=Path, required=True)
    parser.add_argument("--model-tex", type=Path, required=True)
    parser.add_argument("--problem-name", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = validate_symbolic_latex(
        args.analysis_tex.read_text(encoding="utf-8"),
        args.model_tex.read_text(encoding="utf-8"),
        problem_name=args.problem_name,
    )
    output = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
