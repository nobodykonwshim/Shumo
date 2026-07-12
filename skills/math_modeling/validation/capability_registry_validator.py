#!/usr/bin/env python3
"""Validate the Shumo capability registry and its repository evidence paths."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover
    Draft202012Validator = None


class RegistryError(ValueError):
    pass


def load_yaml(path: Path) -> dict[str, Any]:
    if yaml is None:
        raise RegistryError("PyYAML is required to validate the capability registry")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RegistryError(f"cannot read registry {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RegistryError("capability registry root must be an object")
    return data


def load_schema(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RegistryError(f"cannot read registry schema {path}: {exc}") from exc
    return data


def validate_registry(
    registry: dict[str, Any],
    schema: dict[str, Any],
    *,
    repo_root: Path | None = None,
    check_paths: bool = False,
) -> dict[str, Any]:
    if Draft202012Validator is None:
        raise RegistryError("jsonschema is required to validate the capability registry")

    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    validator = Draft202012Validator(schema)
    for error in sorted(validator.iter_errors(registry), key=lambda item: list(item.absolute_path)):
        path = "$" + "".join(
            f"[{part}]" if isinstance(part, int) else f".{part}"
            for part in error.absolute_path
        )
        errors.append({"code": "schema_violation", "path": path, "message": error.message})

    if not errors:
        capabilities = registry.get("capabilities", [])
        backlog = registry.get("backlog", [])
        active_ids: dict[str, int] = {}
        backlog_ids: dict[str, int] = {}
        allowed_statuses = set(registry.get("status_values", []))

        for index, capability in enumerate(capabilities):
            capability_id = capability["capability_id"]
            if capability_id in active_ids:
                errors.append({
                    "code": "duplicate_capability_id",
                    "path": f"$.capabilities[{index}].capability_id",
                    "message": f"capability id duplicates index {active_ids[capability_id]}",
                })
            else:
                active_ids[capability_id] = index

            if capability["status"] not in allowed_statuses:
                errors.append({
                    "code": "undeclared_status",
                    "path": f"$.capabilities[{index}].status",
                    "message": f"status {capability['status']!r} is not declared in status_values",
                })
            if not capability["owner_path"].startswith("skills/math_modeling/"):
                errors.append({
                    "code": "owner_outside_skill",
                    "path": f"$.capabilities[{index}].owner_path",
                    "message": "capability owner_path must be under skills/math_modeling/",
                })
            if capability["status"] in {"validated", "reusable"} and not capability["demonstrated_by"]:
                errors.append({
                    "code": "missing_demonstration",
                    "path": f"$.capabilities[{index}].demonstrated_by",
                    "message": "validated and reusable capabilities require demonstration evidence",
                })
            if capability["status"] in {"validated", "reusable"} and not capability["generic_tests"]:
                warnings.append({
                    "code": "missing_generic_test",
                    "path": f"$.capabilities[{index}].generic_tests",
                    "message": "validated or reusable capability has no machine-executable generic test",
                })

        for index, item in enumerate(backlog):
            capability_id = item["capability_id"]
            if capability_id in backlog_ids:
                errors.append({
                    "code": "duplicate_backlog_id",
                    "path": f"$.backlog[{index}].capability_id",
                    "message": f"backlog id duplicates index {backlog_ids[capability_id]}",
                })
            else:
                backlog_ids[capability_id] = index
            if capability_id in active_ids:
                errors.append({
                    "code": "active_capability_still_in_backlog",
                    "path": f"$.backlog[{index}].capability_id",
                    "message": "active capabilities must be removed from backlog",
                })

        if check_paths:
            if repo_root is None:
                raise RegistryError("repo_root is required when check_paths is enabled")
            root = repo_root.resolve()
            for index, capability in enumerate(capabilities):
                path_fields: list[tuple[str, str]] = [
                    (f"$.capabilities[{index}].owner_path", capability["owner_path"]),
                ]
                if capability.get("validator"):
                    path_fields.append((f"$.capabilities[{index}].validator", capability["validator"]))
                path_fields.extend(
                    (f"$.capabilities[{index}].generic_tests[{item_index}]", path)
                    for item_index, path in enumerate(capability["generic_tests"])
                )
                path_fields.extend(
                    (f"$.capabilities[{index}].demonstrated_by[{item_index}]", path)
                    for item_index, path in enumerate(capability["demonstrated_by"])
                )
                for json_path, raw_path in path_fields:
                    resolved = (root / raw_path).resolve()
                    try:
                        resolved.relative_to(root)
                    except ValueError:
                        errors.append({
                            "code": "path_outside_repository",
                            "path": json_path,
                            "message": f"path escapes repository root: {raw_path}",
                        })
                        continue
                    if not resolved.exists():
                        errors.append({
                            "code": "missing_registry_path",
                            "path": json_path,
                            "message": f"registered path does not exist: {raw_path}",
                        })

    return {
        "schema_version": 1,
        "validator": "shumo_capability_registry_validator",
        "registry_id": registry.get("registry_id"),
        "status": "pass" if not errors else "fail",
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Shumo capability registry")
    parser.add_argument("--registry", type=Path, default=Path("skills/math_modeling/CAPABILITY_REGISTRY.yaml"))
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "specs" / "capability_registry.schema.json",
    )
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--check-paths", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    try:
        report = validate_registry(
            load_yaml(args.registry),
            load_schema(args.schema),
            repo_root=args.repo_root,
            check_paths=args.check_paths,
        )
    except RegistryError as exc:
        report = {
            "schema_version": 1,
            "validator": "shumo_capability_registry_validator",
            "registry_id": None,
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
