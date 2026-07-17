#!/usr/bin/env python3
"""Validate a hash-bound sequential problem-review gate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import jsonschema
import yaml


class ReviewValidationError(RuntimeError):
    """Raised when the validator cannot load its declared inputs."""


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ReviewValidationError(f"cannot load YAML {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ReviewValidationError(f"YAML root must be a mapping: {path}")
    return data


def load_schema(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReviewValidationError(f"cannot load JSON schema {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ReviewValidationError(f"schema root must be an object: {path}")
    return data


def _safe_path(root: Path, raw_path: str) -> Path:
    resolved = (root / raw_path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ReviewValidationError(f"path escapes repository root: {raw_path}") from exc
    return resolved


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_review(
    review: dict[str, Any],
    schema: dict[str, Any],
    *,
    repo_root: Path,
) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    stale_artifacts: list[dict[str, str]] = []

    validator = jsonschema.Draft202012Validator(schema)
    for failure in sorted(validator.iter_errors(review), key=lambda item: list(item.path)):
        path = "$" + "".join(f"[{part}]" if isinstance(part, int) else f".{part}" for part in failure.path)
        errors.append({"code": "schema_error", "path": path, "message": failure.message})

    problem_id = review.get("problem_id")
    next_problem_id = review.get("next_problem_id")
    status = (review.get("review") or {}).get("status")
    sequence_index = review.get("sequence_index")

    if not errors:
        try:
            project_path = _safe_path(repo_root, review["project_config_path"])
            project = load_yaml(project_path)
        except ReviewValidationError as exc:
            project = {}
            errors.append({"code": "project_config_error", "path": "$.project_config_path", "message": str(exc)})

        delivery = project.get("question_delivery") if isinstance(project, dict) else None
        order = delivery.get("problem_order") if isinstance(delivery, dict) else None
        if not isinstance(order, list) or not order:
            errors.append({
                "code": "missing_problem_order",
                "path": "$.project_config_path",
                "message": "project config must declare non-empty question_delivery.problem_order",
            })
        elif delivery.get("mode") != "sequential_review":
            errors.append({
                "code": "sequential_review_disabled",
                "path": "$.project_config_path",
                "message": "question_delivery.mode must be sequential_review",
            })
        elif sequence_index > len(order) or order[sequence_index - 1] != problem_id:
            errors.append({
                "code": "problem_order_mismatch",
                "path": "$.sequence_index",
                "message": "problem_id does not match the configured sequence index",
            })
        else:
            expected_next = order[sequence_index] if sequence_index < len(order) else None
            if next_problem_id != expected_next:
                errors.append({
                    "code": "next_problem_mismatch",
                    "path": "$.next_problem_id",
                    "message": f"expected next_problem_id {expected_next!r}",
                })

        for index, artifact in enumerate(review["artifacts"]):
            try:
                artifact_path = _safe_path(repo_root, artifact["path"])
                if not artifact_path.is_file():
                    raise ReviewValidationError(f"artifact is missing: {artifact['path']}")
                actual = _sha256(artifact_path)
                if actual != artifact["sha256"]:
                    stale_artifacts.append({
                        "id": artifact["id"],
                        "path": artifact["path"],
                        "expected_sha256": artifact["sha256"],
                        "actual_sha256": actual,
                    })
            except ReviewValidationError as exc:
                errors.append({
                    "code": "artifact_path_error",
                    "path": f"$.artifacts[{index}].path",
                    "message": str(exc),
                })

        if stale_artifacts:
            errors.append({
                "code": "stale_artifacts",
                "path": "$.artifacts",
                "message": "one or more reviewed artifacts changed after the recorded revision",
            })

        previous_path = review.get("previous_review_path")
        if sequence_index == 1 and previous_path is not None:
            errors.append({
                "code": "unexpected_previous_review",
                "path": "$.previous_review_path",
                "message": "the first problem must not declare a previous review",
            })
        if sequence_index > 1:
            if not previous_path:
                errors.append({
                    "code": "missing_previous_review",
                    "path": "$.previous_review_path",
                    "message": "later problems must declare the immediately previous review",
                })
            else:
                try:
                    previous = load_yaml(_safe_path(repo_root, previous_path))
                    previous_status = (previous.get("review") or {}).get("status")
                    if previous.get("sequence_index") != sequence_index - 1 or previous_status != "approved":
                        errors.append({
                            "code": "previous_review_not_approved",
                            "path": "$.previous_review_path",
                            "message": "the immediately previous problem must have an approved review",
                        })
                except ReviewValidationError as exc:
                    errors.append({
                        "code": "previous_review_error",
                        "path": "$.previous_review_path",
                        "message": str(exc),
                    })

    record_valid = not errors
    advance_allowed = record_valid and status == "approved"
    if record_valid and not advance_allowed:
        warnings.append({
            "code": "review_gate_closed",
            "path": "$.review.status",
            "message": f"review status {status!r} keeps the next problem locked",
        })

    return {
        "schema_version": 1,
        "validator": "shumo_problem_review_validator",
        "validation_status": "pass" if record_valid else "fail",
        "advance_allowed": advance_allowed,
        "current_problem": problem_id,
        "next_problem": next_problem_id,
        "review_status": status,
        "stale_artifacts": stale_artifacts,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "specs" / "problem_review.schema.json",
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    try:
        report = validate_review(
            load_yaml(args.review),
            load_schema(args.schema),
            repo_root=args.repo_root.resolve(),
        )
        if report["validation_status"] != "pass":
            exit_code = 1
        elif report["advance_allowed"]:
            exit_code = 0
        else:
            exit_code = 2
    except ReviewValidationError as exc:
        report = {
            "schema_version": 1,
            "validator": "shumo_problem_review_validator",
            "validation_status": "error",
            "advance_allowed": False,
            "error_count": 1,
            "warning_count": 0,
            "errors": [{"code": "validator_error", "path": "$", "message": str(exc)}],
            "warnings": [],
            "stale_artifacts": [],
        }
        exit_code = 1

    output = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
