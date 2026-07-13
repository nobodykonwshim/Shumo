#!/usr/bin/env python3
"""Validate Shumo modeling-decision records."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover
    Draft202012Validator = None


class ModelingDecisionError(ValueError):
    """Raised for unreadable modeling-decision inputs."""


def _load_document(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ModelingDecisionError(f"cannot read decision record {path}: {exc}") from exc
    try:
        if path.suffix.lower() == ".json":
            data = json.loads(text)
        else:
            if yaml is None:
                raise ModelingDecisionError("PyYAML is required for YAML decision records")
            data = yaml.safe_load(text)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ModelingDecisionError(f"cannot parse decision record {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ModelingDecisionError("decision record root must be an object")
    return data


def _load_schema(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ModelingDecisionError(f"cannot read schema {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ModelingDecisionError("schema root must be an object")
    return data


def _format_path(parts: Iterable[Any]) -> str:
    result = "$"
    for part in parts:
        result += f"[{part}]" if isinstance(part, int) else f".{part}"
    return result


def _schema_errors(document: dict[str, Any], schema: dict[str, Any]) -> list[dict[str, str]]:
    if Draft202012Validator is None:
        raise ModelingDecisionError("jsonschema is required to validate decision records")
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(document), key=lambda error: list(error.absolute_path))
    return [
        {
            "code": "schema_violation",
            "path": _format_path(error.absolute_path),
            "message": error.message,
        }
        for error in errors
    ]


def _duplicate_errors(items: list[dict[str, Any]], section: str) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    seen: dict[str, int] = {}
    for index, item in enumerate(items):
        item_id = item.get("id")
        if not isinstance(item_id, str):
            continue
        if item_id in seen:
            errors.append({
                "code": "duplicate_id",
                "path": f"$.{section}[{index}].id",
                "message": f"id {item_id!r} duplicates $.{section}[{seen[item_id]}].id",
            })
        else:
            seen[item_id] = index
    return errors


def _semantic_errors(document: dict[str, Any]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    if document.get("declared_before_implementation") is not True:
        errors.append({
            "code": "retroactive_model_selection",
            "path": "$.declared_before_implementation",
            "message": "modeling routes and comparison rules must be declared before implementation",
        })

    candidates = document.get("candidate_routes", [])
    criteria = document.get("comparison_criteria", [])
    matrix = document.get("comparison_matrix", [])
    errors.extend(_duplicate_errors(candidates, "candidate_routes"))
    errors.extend(_duplicate_errors(criteria, "comparison_criteria"))

    candidate_ids = {item.get("id") for item in candidates if isinstance(item.get("id"), str)}
    criterion_ids = {item.get("id") for item in criteria if isinstance(item.get("id"), str)}

    row_ids: set[str] = set()
    for row_index, row in enumerate(matrix):
        candidate_id = row.get("candidate_id")
        if candidate_id not in candidate_ids:
            errors.append({
                "code": "unknown_matrix_candidate",
                "path": f"$.comparison_matrix[{row_index}].candidate_id",
                "message": f"candidate {candidate_id!r} is not declared",
            })
        if isinstance(candidate_id, str):
            if candidate_id in row_ids:
                errors.append({
                    "code": "duplicate_matrix_row",
                    "path": f"$.comparison_matrix[{row_index}].candidate_id",
                    "message": f"candidate {candidate_id!r} has more than one comparison row",
                })
            row_ids.add(candidate_id)

        assessment_ids: set[str] = set()
        for assessment_index, assessment in enumerate(row.get("assessments", [])):
            criterion_id = assessment.get("criterion_id")
            path = f"$.comparison_matrix[{row_index}].assessments[{assessment_index}].criterion_id"
            if criterion_id not in criterion_ids:
                errors.append({
                    "code": "unknown_matrix_criterion",
                    "path": path,
                    "message": f"criterion {criterion_id!r} is not declared",
                })
            if isinstance(criterion_id, str):
                if criterion_id in assessment_ids:
                    errors.append({
                        "code": "duplicate_matrix_assessment",
                        "path": path,
                        "message": f"criterion {criterion_id!r} is assessed more than once in this row",
                    })
                assessment_ids.add(criterion_id)
        missing = criterion_ids - assessment_ids
        if missing:
            errors.append({
                "code": "incomplete_comparison_row",
                "path": f"$.comparison_matrix[{row_index}].assessments",
                "message": f"missing assessments for criteria: {sorted(missing)}",
            })

    missing_rows = candidate_ids - row_ids
    if missing_rows:
        errors.append({
            "code": "missing_comparison_rows",
            "path": "$.comparison_matrix",
            "message": f"missing comparison rows for candidates: {sorted(missing_rows)}",
        })

    recommendation = document.get("recommendation", {})
    selected_id = recommendation.get("selected_candidate_id")
    fallback_id = recommendation.get("fallback_candidate_id")
    if selected_id is not None and selected_id not in candidate_ids:
        errors.append({
            "code": "unknown_recommended_candidate",
            "path": "$.recommendation.selected_candidate_id",
            "message": f"recommended candidate {selected_id!r} is not declared",
        })
    if fallback_id is not None and fallback_id not in candidate_ids:
        errors.append({
            "code": "unknown_fallback_candidate",
            "path": "$.recommendation.fallback_candidate_id",
            "message": f"fallback candidate {fallback_id!r} is not declared",
        })
    if selected_id is not None and fallback_id == selected_id:
        errors.append({
            "code": "fallback_equals_recommendation",
            "path": "$.recommendation.fallback_candidate_id",
            "message": "fallback candidate must differ from the recommended candidate",
        })

    selected_status_ids = [item.get("id") for item in candidates if item.get("status") == "selected"]
    for index, candidate in enumerate(candidates):
        status = candidate.get("status")
        if status == "rejected" and not str(candidate.get("rejection_reason", "")).strip():
            errors.append({
                "code": "missing_rejection_reason",
                "path": f"$.candidate_routes[{index}].rejection_reason",
                "message": "rejected candidates require an explicit reason",
            })
        if status == "blocked" and not candidate.get("blockers"):
            errors.append({
                "code": "missing_candidate_blocker",
                "path": f"$.candidate_routes[{index}].blockers",
                "message": "blocked candidates require at least one blocker",
            })

    checkpoint = document.get("human_checkpoint", {})
    if document.get("status") == "frozen":
        if selected_id is None:
            errors.append({
                "code": "frozen_without_selection",
                "path": "$.recommendation.selected_candidate_id",
                "message": "frozen decision records require a selected candidate",
            })
        if checkpoint.get("status") != "approved":
            errors.append({
                "code": "frozen_without_human_approval",
                "path": "$.human_checkpoint.status",
                "message": "frozen decision records require an approved human checkpoint",
            })
        if recommendation.get("requires_human_decision") is not False:
            errors.append({
                "code": "frozen_still_requires_decision",
                "path": "$.recommendation.requires_human_decision",
                "message": "a frozen record cannot still require the same human decision",
            })
        if selected_status_ids != [selected_id]:
            errors.append({
                "code": "selected_status_mismatch",
                "path": "$.candidate_routes",
                "message": "exactly the recommended candidate must have status 'selected' in a frozen record",
            })
    elif selected_status_ids:
        errors.append({
            "code": "premature_selected_status",
            "path": "$.candidate_routes",
            "message": "candidate status 'selected' is reserved for frozen, human-approved records",
        })

    hard_criteria = {item.get("id") for item in criteria if item.get("kind") == "hard"}
    if selected_id is not None:
        for row in matrix:
            if row.get("candidate_id") != selected_id:
                continue
            failed = [
                item.get("criterion_id")
                for item in row.get("assessments", [])
                if item.get("criterion_id") in hard_criteria and item.get("rating") == "fail"
            ]
            if failed:
                errors.append({
                    "code": "recommended_candidate_fails_hard_criterion",
                    "path": "$.recommendation.selected_candidate_id",
                    "message": f"recommended candidate fails hard criteria: {failed}",
                })

    soft = [item for item in criteria if item.get("kind") == "soft"]
    weighted = [item for item in soft if item.get("weight") is not None]
    if weighted and len(weighted) != len(soft):
        errors.append({
            "code": "partial_soft_weighting",
            "path": "$.comparison_criteria",
            "message": "either weight every soft criterion or leave all soft criteria unweighted",
        })
    if weighted:
        total = sum(float(item["weight"]) for item in weighted)
        if total <= 0:
            errors.append({
                "code": "nonpositive_weight_sum",
                "path": "$.comparison_criteria",
                "message": "soft-criterion weights must have a positive sum",
            })
        elif abs(total - 1.0) > 1e-9:
            warnings.append({
                "code": "weights_not_normalized",
                "path": "$.comparison_criteria",
                "message": f"soft-criterion weights sum to {total:g}, not 1; rankings must state whether normalization is applied",
            })

    return errors, warnings


def _path_errors(document: dict[str, Any], repo_root: Path) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    root = repo_root.resolve()
    entries: list[tuple[str, str]] = []
    provenance = document.get("provenance", {})
    for field in ("source_paths", "evidence_paths"):
        for index, raw_path in enumerate(provenance.get(field, [])):
            entries.append((f"$.provenance.{field}[{index}]", raw_path))
    record = document.get("human_checkpoint", {}).get("record")
    if record:
        entries.append(("$.human_checkpoint.record", record))

    for json_path, raw_path in entries:
        candidate = (repo_root / raw_path).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            errors.append({
                "code": "path_outside_repository",
                "path": json_path,
                "message": f"repository path escapes repo root: {raw_path}",
            })
            continue
        if not candidate.exists():
            errors.append({
                "code": "missing_repository_path",
                "path": json_path,
                "message": f"repository path does not exist: {raw_path}",
            })
    return errors


def validate_modeling_decision(
    document: dict[str, Any],
    schema: dict[str, Any],
    *,
    repo_root: Path | None = None,
    check_paths: bool = False,
) -> dict[str, Any]:
    errors = _schema_errors(document, schema)
    warnings: list[dict[str, str]] = []
    if not errors:
        semantic_errors, semantic_warnings = _semantic_errors(document)
        errors.extend(semantic_errors)
        warnings.extend(semantic_warnings)
        if check_paths:
            if repo_root is None:
                raise ModelingDecisionError("repo_root is required when check_paths is enabled")
            errors.extend(_path_errors(document, repo_root))
    return {
        "schema_version": 1,
        "validator": "shumo_modeling_decision_validator",
        "decision_id": document.get("decision_id"),
        "status": "pass" if not errors else "fail",
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a Shumo modeling-decision record")
    parser.add_argument("--decision", required=True, type=Path)
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "specs" / "modeling_decision.schema.json",
    )
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--check-paths", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    document = _load_document(args.decision)
    schema = _load_schema(args.schema)
    report = validate_modeling_decision(
        document,
        schema,
        repo_root=args.repo_root,
        check_paths=args.check_paths,
    )
    payload = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
