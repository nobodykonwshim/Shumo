#!/usr/bin/env python3
"""Validate Shumo model specifications against schema and semantic rules."""
from __future__ import annotations

import argparse
import json
import math
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


class ModelSpecError(ValueError):
    """Raised for unreadable model specification inputs."""


def _load_document(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ModelSpecError(f"cannot read specification {path}: {exc}") from exc

    try:
        if path.suffix.lower() == ".json":
            data = json.loads(text)
        else:
            if yaml is None:
                raise ModelSpecError(
                    "PyYAML is required for YAML model specifications; JSON remains supported"
                )
            data = yaml.safe_load(text)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ModelSpecError(f"cannot parse specification {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ModelSpecError("model specification root must be an object")
    return data


def _load_schema(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ModelSpecError(f"cannot read schema {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ModelSpecError("schema root must be an object")
    return data


def _format_json_path(parts: Iterable[Any]) -> str:
    result = "$"
    for part in parts:
        result += f"[{part}]" if isinstance(part, int) else f".{part}"
    return result


def _schema_errors(document: dict[str, Any], schema: dict[str, Any]) -> list[dict[str, str]]:
    if Draft202012Validator is None:
        raise ModelSpecError("jsonschema is required to validate model specifications")
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(document), key=lambda error: list(error.absolute_path))
    return [
        {
            "code": "schema_violation",
            "path": _format_json_path(error.absolute_path),
            "message": error.message,
        }
        for error in errors
    ]


def _iter_addressable(document: dict[str, Any]):
    yield "spec", document.get("spec_id"), "$.spec_id"
    yield "problem", document.get("problem_id"), "$.problem_id"

    for index, item in enumerate(document.get("objective", {}).get("metrics", [])):
        yield "objective_metric", item.get("id"), f"$.objective.metrics[{index}].id"
    for index, item in enumerate(document.get("inputs", [])):
        yield "input", item.get("id"), f"$.inputs[{index}].id"
    for group in ("variables", "parameters"):
        for index, item in enumerate(document.get("symbols", {}).get(group, [])):
            yield group[:-1], item.get("id"), f"$.symbols.{group}[{index}].id"
    for section in (
        "assumptions", "model_components", "formulas", "constraints",
        "outputs", "human_checkpoints",
    ):
        for index, item in enumerate(document.get(section, [])):
            yield section.rstrip("s"), item.get("id"), f"$.{section}[{index}].id"
    for index, item in enumerate(document.get("algorithm", {}).get("steps", [])):
        yield "algorithm_step", item.get("id"), f"$.algorithm.steps[{index}].id"
    for index, item in enumerate(document.get("validation", {}).get("checks", [])):
        yield "validation_check", item.get("id"), f"$.validation.checks[{index}].id"
    for index, item in enumerate(document.get("provenance", {}).get("source_artifacts", [])):
        yield "source_artifact", item.get("id"), f"$.provenance.source_artifacts[{index}].id"


def _semantic_errors(document: dict[str, Any]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    id_locations: dict[str, tuple[str, str]] = {}
    for kind, item_id, path in _iter_addressable(document):
        if not isinstance(item_id, str):
            continue
        if item_id in id_locations:
            previous_kind, previous_path = id_locations[item_id]
            errors.append({
                "code": "duplicate_id",
                "path": path,
                "message": f"id {item_id!r} duplicates {previous_kind} at {previous_path}",
            })
        else:
            id_locations[item_id] = (kind, path)

    known_ids = set(id_locations)
    symbol_ids = {
        item.get("id")
        for group in ("variables", "parameters")
        for item in document.get("symbols", {}).get(group, [])
        if isinstance(item.get("id"), str)
    }

    references: list[tuple[str, str, set[str]]] = []
    for index, item in enumerate(document.get("objective", {}).get("metrics", [])):
        formula_id = item.get("formula_id")
        if formula_id:
            references.append((f"$.objective.metrics[{index}].formula_id", formula_id, known_ids))
    for index, item in enumerate(document.get("assumptions", [])):
        check_id = item.get("validation_check_id")
        if check_id:
            references.append((f"$.assumptions[{index}].validation_check_id", check_id, known_ids))
    for section in ("model_components", "outputs"):
        for index, item in enumerate(document.get(section, [])):
            for ref_index, ref in enumerate(item.get("depends_on", [])):
                references.append((f"$.{section}[{index}].depends_on[{ref_index}]", ref, known_ids))
    for index, item in enumerate(document.get("formulas", [])):
        for ref_index, ref in enumerate(item.get("symbols", [])):
            references.append((f"$.formulas[{index}].symbols[{ref_index}]", ref, symbol_ids))
    for index, item in enumerate(document.get("constraints", [])):
        for ref_index, ref in enumerate(item.get("symbols", [])):
            references.append((f"$.constraints[{index}].symbols[{ref_index}]", ref, symbol_ids))
    for index, item in enumerate(document.get("algorithm", {}).get("steps", [])):
        for field in ("uses", "produces"):
            for ref_index, ref in enumerate(item.get(field, [])):
                references.append((f"$.algorithm.steps[{index}].{field}[{ref_index}]", ref, known_ids))
    for index, item in enumerate(document.get("validation", {}).get("checks", [])):
        for ref_index, ref in enumerate(item.get("target_ids", [])):
            references.append((f"$.validation.checks[{index}].target_ids[{ref_index}]", ref, known_ids))
    sensitivity = document.get("validation", {}).get("sensitivity_policy", {})
    for index, ref in enumerate(sensitivity.get("parameters", [])):
        references.append((f"$.validation.sensitivity_policy.parameters[{index}]", ref, symbol_ids))

    for path, ref, allowed in references:
        if ref not in allowed:
            errors.append({
                "code": "unresolved_reference",
                "path": path,
                "message": f"reference {ref!r} does not resolve to an allowed id",
            })

    primary_metrics = [
        metric for metric in document.get("objective", {}).get("metrics", [])
        if metric.get("priority") == "primary"
    ]
    if not primary_metrics:
        errors.append({
            "code": "missing_primary_metric",
            "path": "$.objective.metrics",
            "message": "at least one objective metric must have priority 'primary'",
        })

    algorithm = document.get("algorithm", {})
    if algorithm.get("deterministic") is False and not algorithm.get("randomness"):
        errors.append({
            "code": "missing_randomness_contract",
            "path": "$.algorithm.randomness",
            "message": "non-deterministic algorithms must declare seed_policy and replications",
        })
    if algorithm.get("deterministic") is True and algorithm.get("randomness"):
        warnings.append({
            "code": "unused_randomness_contract",
            "path": "$.algorithm.randomness",
            "message": "deterministic algorithm declares randomness; confirm that this is intentional",
        })

    if document.get("status") == "blocked" and not document.get("blockers"):
        errors.append({
            "code": "missing_blocker",
            "path": "$.blockers",
            "message": "blocked specifications must list at least one blocker",
        })

    if document.get("status") == "solved":
        for index, check in enumerate(document.get("validation", {}).get("checks", [])):
            if check.get("required") and check.get("status") not in {"pass", "not_applicable"}:
                errors.append({
                    "code": "unsatisfied_required_validation",
                    "path": f"$.validation.checks[{index}].status",
                    "message": "solved specifications require every required validation check to pass",
                })
        for index, checkpoint in enumerate(document.get("human_checkpoints", [])):
            if checkpoint.get("status") == "pending":
                errors.append({
                    "code": "pending_human_checkpoint",
                    "path": f"$.human_checkpoints[{index}].status",
                    "message": "solved specifications cannot retain a pending human checkpoint",
                })

    for index, item in enumerate(document.get("symbols", {}).get("parameters", [])):
        range_value = item.get("range")
        if isinstance(range_value, list) and len(range_value) == 2:
            if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in range_value):
                errors.append({
                    "code": "invalid_parameter_range",
                    "path": f"$.symbols.parameters[{index}].range",
                    "message": "parameter range values must be finite numbers",
                })
            elif range_value[0] > range_value[1]:
                errors.append({
                    "code": "reversed_parameter_range",
                    "path": f"$.symbols.parameters[{index}].range",
                    "message": "parameter range lower bound must not exceed upper bound",
                })

    return errors, warnings


def _path_errors(document: dict[str, Any], repo_root: Path) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    candidates: list[tuple[str, str]] = []

    for index, artifact in enumerate(document.get("provenance", {}).get("source_artifacts", [])):
        if artifact.get("availability") == "repository":
            candidates.append((f"$.provenance.source_artifacts[{index}].location", artifact.get("location", "")))
    for index, path in enumerate(document.get("provenance", {}).get("evidence_paths", [])):
        candidates.append((f"$.provenance.evidence_paths[{index}]", path))
    for index, entrypoint in enumerate(document.get("implementation", {}).get("entrypoints", [])):
        if entrypoint.get("availability", "repository") == "repository":
            candidates.append((f"$.implementation.entrypoints[{index}].path", entrypoint.get("path", "")))

    resolved_root = repo_root.resolve()
    for json_path, raw_path in candidates:
        if not raw_path:
            continue
        candidate = (repo_root / raw_path).resolve()
        try:
            candidate.relative_to(resolved_root)
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


def validate_model_spec(
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
                raise ModelSpecError("repo_root is required when check_paths is enabled")
            errors.extend(_path_errors(document, repo_root))

    return {
        "schema_version": 1,
        "validator": "shumo_model_spec_validator",
        "spec_id": document.get("spec_id"),
        "status": "pass" if not errors else "fail",
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a Shumo model specification")
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "specs" / "model_spec.schema.json",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--check-paths", action="store_true")
    args = parser.parse_args(argv)

    try:
        document = _load_document(args.spec)
        schema = _load_schema(args.schema)
        report = validate_model_spec(
            document,
            schema,
            repo_root=args.repo_root,
            check_paths=args.check_paths,
        )
    except ModelSpecError as exc:
        report = {
            "schema_version": 1,
            "validator": "shumo_model_spec_validator",
            "spec_id": None,
            "status": "error",
            "error_count": 1,
            "warning_count": 0,
            "errors": [{"code": "validator_error", "path": "$", "message": str(exc)}],
            "warnings": [],
        }

    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0 if report["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
