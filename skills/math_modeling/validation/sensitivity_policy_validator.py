#!/usr/bin/env python3
"""Validate case-specific sensitivity declarations without inventing universal thresholds."""
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


class SensitivityPolicyError(ValueError):
    """Raised for unreadable sensitivity-policy inputs."""


def _load_document(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SensitivityPolicyError(f"cannot read document {path}: {exc}") from exc
    try:
        if path.suffix.lower() == ".json":
            data = json.loads(text)
        else:
            if yaml is None:
                raise SensitivityPolicyError(
                    "PyYAML is required for YAML sensitivity policies; JSON remains supported"
                )
            data = yaml.safe_load(text)
    except (json.JSONDecodeError, ValueError) as exc:
        raise SensitivityPolicyError(f"cannot parse document {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SensitivityPolicyError("document root must be an object")
    return data


def _load_schema(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SensitivityPolicyError(f"cannot read schema {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SensitivityPolicyError("schema root must be an object")
    return data


def _format_json_path(parts: Iterable[Any]) -> str:
    result = "$"
    for part in parts:
        result += f"[{part}]" if isinstance(part, int) else f".{part}"
    return result


def _schema_errors(document: dict[str, Any], schema: dict[str, Any]) -> list[dict[str, str]]:
    if Draft202012Validator is None:
        raise SensitivityPolicyError("jsonschema is required to validate sensitivity policies")
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


def _model_ids(model: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for key in ("spec_id", "problem_id"):
        value = model.get(key)
        if isinstance(value, str):
            ids.add(value)
    for item in model.get("objective", {}).get("metrics", []):
        if isinstance(item.get("id"), str):
            ids.add(item["id"])
    for item in model.get("inputs", []):
        if isinstance(item.get("id"), str):
            ids.add(item["id"])
    for group in ("variables", "parameters"):
        for item in model.get("symbols", {}).get(group, []):
            if isinstance(item.get("id"), str):
                ids.add(item["id"])
    for section in (
        "assumptions", "model_components", "formulas", "constraints",
        "outputs", "human_checkpoints",
    ):
        for item in model.get(section, []):
            if isinstance(item.get("id"), str):
                ids.add(item["id"])
    for item in model.get("algorithm", {}).get("steps", []):
        if isinstance(item.get("id"), str):
            ids.add(item["id"])
    for item in model.get("validation", {}).get("checks", []):
        if isinstance(item.get("id"), str):
            ids.add(item["id"])
    return ids


def _semantic_errors(
    document: dict[str, Any],
    *,
    model_document: dict[str, Any] | None = None,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    id_locations: dict[str, str] = {}
    groups = [
        ("perturbations", "$.scope.perturbations"),
        ("metrics", "$.scope.metrics"),
        ("acceptance_rules", "$.scope.acceptance_rules"),
        ("amendments", "$.amendments"),
    ]
    for key, path in groups:
        items = document.get("scope", {}).get(key, []) if key != "amendments" else document.get(key, [])
        for index, item in enumerate(items):
            item_id = item.get("id")
            if not isinstance(item_id, str):
                continue
            current = f"{path}[{index}].id"
            if item_id in id_locations:
                errors.append({
                    "code": "duplicate_id",
                    "path": current,
                    "message": f"id {item_id!r} duplicates {id_locations[item_id]}",
                })
            else:
                id_locations[item_id] = current

    metrics = document.get("scope", {}).get("metrics", [])
    metric_ids = {item.get("id") for item in metrics if isinstance(item.get("id"), str)}
    rules = document.get("scope", {}).get("acceptance_rules", [])
    rule_ids = {item.get("id") for item in rules if isinstance(item.get("id"), str)}
    required_rule_ids = {
        item.get("id") for item in rules
        if item.get("required") is True and isinstance(item.get("id"), str)
    }

    for index, rule in enumerate(rules):
        for ref_index, metric_id in enumerate(rule.get("metric_ids", [])):
            if metric_id not in metric_ids:
                errors.append({
                    "code": "unresolved_metric_reference",
                    "path": f"$.scope.acceptance_rules[{index}].metric_ids[{ref_index}]",
                    "message": f"metric reference {metric_id!r} is not declared",
                })

    results = document.get("execution", {}).get("results", [])
    seen_result_rules: set[str] = set()
    result_status_by_rule: dict[str, str] = {}
    for index, result in enumerate(results):
        rule_id = result.get("rule_id")
        if rule_id not in rule_ids:
            errors.append({
                "code": "unresolved_rule_reference",
                "path": f"$.execution.results[{index}].rule_id",
                "message": f"rule reference {rule_id!r} is not declared",
            })
        if isinstance(rule_id, str):
            if rule_id in seen_result_rules:
                errors.append({
                    "code": "duplicate_rule_result",
                    "path": f"$.execution.results[{index}].rule_id",
                    "message": f"rule {rule_id!r} has more than one result",
                })
            seen_result_rules.add(rule_id)
            result_status_by_rule[rule_id] = str(result.get("status"))

    status = document.get("status")
    execution_status = document.get("execution", {}).get("status")
    governance = document.get("governance", {})
    if status in {"frozen", "executed", "failed", "waived"} and not governance.get("freeze_record"):
        errors.append({
            "code": "missing_freeze_record",
            "path": "$.governance.freeze_record",
            "message": f"{status} policies must record where the pre-result decision was frozen",
        })

    if status == "frozen" and execution_status not in {"planned", "blocked"}:
        errors.append({
            "code": "invalid_frozen_execution_state",
            "path": "$.execution.status",
            "message": "a frozen policy must remain planned or blocked until execution",
        })

    if status == "executed":
        if execution_status != "completed":
            errors.append({
                "code": "execution_not_completed",
                "path": "$.execution.status",
                "message": "executed policies require execution.status=completed",
            })
        if not document.get("execution", {}).get("evidence_paths"):
            errors.append({
                "code": "missing_execution_evidence",
                "path": "$.execution.evidence_paths",
                "message": "executed policies require at least one evidence path",
            })
        for rule_id in sorted(required_rule_ids):
            if result_status_by_rule.get(rule_id) not in {"pass", "fail"}:
                errors.append({
                    "code": "missing_required_rule_result",
                    "path": "$.execution.results",
                    "message": f"required rule {rule_id!r} must have an explicit pass or fail result",
                })

    if status == "failed":
        if execution_status not in {"completed", "blocked"}:
            errors.append({
                "code": "invalid_failed_execution_state",
                "path": "$.execution.status",
                "message": "failed policies require completed or blocked execution",
            })
        if not any(
            result_status_by_rule.get(rule_id) in {"fail", "blocked"}
            for rule_id in required_rule_ids
        ):
            errors.append({
                "code": "failed_without_failed_required_rule",
                "path": "$.execution.results",
                "message": "failed policy must identify a failed or blocked required rule",
            })

    if status == "waived" and execution_status != "not_required":
        errors.append({
            "code": "invalid_waiver_execution_state",
            "path": "$.execution.status",
            "message": "waived policies require execution.status=not_required",
        })

    for index, amendment in enumerate(document.get("amendments", [])):
        if amendment.get("timing") == "post_result":
            warnings.append({
                "code": "post_result_amendment",
                "path": f"$.amendments[{index}]",
                "message": (
                    "post-result amendments may clarify or schedule a new run, but cannot "
                    "retroactively replace the frozen rule or original verdict"
                ),
            })
            if amendment.get("preserves_original_rule") is not True:
                errors.append({
                    "code": "post_result_rule_replacement",
                    "path": f"$.amendments[{index}].preserves_original_rule",
                    "message": "post-result amendments must preserve the original rule and verdict",
                })

    if model_document is not None:
        expected_spec_id = document.get("model", {}).get("artifact_id")
        if model_document.get("spec_id") != expected_spec_id:
            errors.append({
                "code": "model_spec_id_mismatch",
                "path": "$.model.artifact_id",
                "message": (
                    f"policy expects {expected_spec_id!r} but referenced model declares "
                    f"{model_document.get('spec_id')!r}"
                ),
            })
        known_model_ids = _model_ids(model_document)
        for index, item in enumerate(document.get("scope", {}).get("perturbations", [])):
            target_id = item.get("target_id")
            if target_id not in known_model_ids:
                severity = "error" if item.get("target_type") in {
                    "input", "parameter", "assumption", "initial_condition"
                } else "warning"
                entry = {
                    "code": "unresolved_model_target",
                    "path": f"$.scope.perturbations[{index}].target_id",
                    "message": f"target {target_id!r} is not addressable in the referenced model spec",
                }
                (errors if severity == "error" else warnings).append(entry)
        for index, item in enumerate(metrics):
            target_id = item.get("target_id")
            if target_id not in known_model_ids:
                errors.append({
                    "code": "unresolved_model_metric_target",
                    "path": f"$.scope.metrics[{index}].target_id",
                    "message": f"metric target {target_id!r} is not addressable in the model spec",
                })

    return errors, warnings


def _is_repository_path(value: str) -> bool:
    return bool(value) and "://" not in value and not value.startswith("external:")


def _path_errors(
    document: dict[str, Any],
    repo_root: Path,
) -> tuple[list[dict[str, str]], dict[str, Any] | None]:
    errors: list[dict[str, str]] = []
    model_document: dict[str, Any] | None = None
    candidates: list[tuple[str, str]] = []

    model_path = document.get("model", {}).get("artifact_path", "")
    candidates.append(("$.model.artifact_path", model_path))
    governance = document.get("governance", {})
    if governance.get("freeze_record"):
        candidates.append(("$.governance.freeze_record", governance["freeze_record"]))
    for index, rule in enumerate(document.get("scope", {}).get("acceptance_rules", [])):
        if rule.get("source_record"):
            candidates.append((f"$.scope.acceptance_rules[{index}].source_record", rule["source_record"]))
    for index, value in enumerate(document.get("execution", {}).get("evidence_paths", [])):
        candidates.append((f"$.execution.evidence_paths[{index}]", value))
    for index, result in enumerate(document.get("execution", {}).get("results", [])):
        if result.get("evidence"):
            candidates.append((f"$.execution.results[{index}].evidence", result["evidence"]))
    for index, amendment in enumerate(document.get("amendments", [])):
        candidates.append((f"$.amendments[{index}].record", amendment.get("record", "")))

    resolved_root = repo_root.resolve()
    for json_path, raw_path in candidates:
        if not isinstance(raw_path, str) or not _is_repository_path(raw_path):
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
            continue
        if json_path == "$.model.artifact_path" and document.get("model", {}).get("artifact_kind") == "model_spec":
            try:
                model_document = _load_document(candidate)
            except SensitivityPolicyError as exc:
                errors.append({
                    "code": "unreadable_model_spec",
                    "path": json_path,
                    "message": str(exc),
                })
    return errors, model_document


def validate_sensitivity_policy(
    document: dict[str, Any],
    schema: dict[str, Any],
    *,
    repo_root: Path | None = None,
    check_paths: bool = False,
) -> dict[str, Any]:
    errors = _schema_errors(document, schema)
    warnings: list[dict[str, str]] = []
    model_document = None
    if not errors and check_paths:
        if repo_root is None:
            raise SensitivityPolicyError("repo_root is required when check_paths is enabled")
        path_errors, model_document = _path_errors(document, repo_root)
        errors.extend(path_errors)
    if not errors:
        semantic_errors, semantic_warnings = _semantic_errors(
            document, model_document=model_document
        )
        errors.extend(semantic_errors)
        warnings.extend(semantic_warnings)
    return {
        "schema_version": 1,
        "validator": "shumo_sensitivity_policy_validator",
        "policy_id": document.get("policy_id"),
        "status": "pass" if not errors else "fail",
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a Shumo sensitivity policy")
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "specs" / "sensitivity_policy.schema.json",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--check-paths", action="store_true")
    args = parser.parse_args(argv)

    try:
        document = _load_document(args.policy)
        schema = _load_schema(args.schema)
        report = validate_sensitivity_policy(
            document,
            schema,
            repo_root=args.repo_root,
            check_paths=args.check_paths,
        )
    except SensitivityPolicyError as exc:
        report = {
            "schema_version": 1,
            "validator": "shumo_sensitivity_policy_validator",
            "status": "fail",
            "error_count": 1,
            "warning_count": 0,
            "errors": [{"code": "input_error", "path": "$", "message": str(exc)}],
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
