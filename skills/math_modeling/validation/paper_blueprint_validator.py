#!/usr/bin/env python3
"""Validate paper blueprints against frozen model specifications and ownership rules."""
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


class PaperBlueprintError(ValueError):
    """Raised for unreadable blueprint inputs."""


def _load_document(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PaperBlueprintError(f"cannot read document {path}: {exc}") from exc
    try:
        if path.suffix.lower() == ".json":
            data = json.loads(text)
        else:
            if yaml is None:
                raise PaperBlueprintError(
                    "PyYAML is required for YAML paper blueprints; JSON remains supported"
                )
            data = yaml.safe_load(text)
    except (json.JSONDecodeError, ValueError) as exc:
        raise PaperBlueprintError(f"cannot parse document {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise PaperBlueprintError("document root must be an object")
    return data


def _load_schema(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PaperBlueprintError(f"cannot read schema {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise PaperBlueprintError("schema root must be an object")
    return data


def _format_json_path(parts: Iterable[Any]) -> str:
    result = "$"
    for part in parts:
        result += f"[{part}]" if isinstance(part, int) else f".{part}"
    return result


def _schema_errors(document: dict[str, Any], schema: dict[str, Any]) -> list[dict[str, str]]:
    if Draft202012Validator is None:
        raise PaperBlueprintError("jsonschema is required to validate paper blueprints")
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


def _spec_inventory(spec: dict[str, Any]) -> dict[str, Any]:
    models = {
        item.get("id") for item in spec.get("model_components", [])
        if isinstance(item.get("id"), str)
    }
    formulas = {
        item.get("id") for item in spec.get("formulas", [])
        if isinstance(item.get("id"), str)
    }
    outputs = {
        item.get("id") for item in spec.get("outputs", [])
        if isinstance(item.get("id"), str)
    }
    all_ids = set(models) | set(formulas) | set(outputs)
    for item in spec.get("objective", {}).get("metrics", []):
        if isinstance(item.get("id"), str):
            all_ids.add(item["id"])
    for item in spec.get("inputs", []):
        if isinstance(item.get("id"), str):
            all_ids.add(item["id"])
    for group in ("variables", "parameters"):
        for item in spec.get("symbols", {}).get(group, []):
            if isinstance(item.get("id"), str):
                all_ids.add(item["id"])
    for section in ("assumptions", "constraints", "human_checkpoints"):
        for item in spec.get(section, []):
            if isinstance(item.get("id"), str):
                all_ids.add(item["id"])
    for item in spec.get("validation", {}).get("checks", []):
        if isinstance(item.get("id"), str):
            all_ids.add(item["id"])
    for item in spec.get("algorithm", {}).get("steps", []):
        if isinstance(item.get("id"), str):
            all_ids.add(item["id"])
    return {
        "status": spec.get("status"),
        "models": models,
        "formulas": formulas,
        "outputs": outputs,
        "all_ids": all_ids,
        "allowed_claims": set(spec.get("claims", {}).get("allowed", [])),
        "forbidden_claims": set(spec.get("claims", {}).get("forbidden", [])),
    }


def _duplicates(values: list[str]) -> set[str]:
    seen: set[str] = set()
    duplicate: set[str] = set()
    for value in values:
        if value in seen:
            duplicate.add(value)
        seen.add(value)
    return duplicate


def _semantic_errors(
    document: dict[str, Any],
    *,
    specs: dict[str, dict[str, Any]] | None = None,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    source_specs = document.get("source_specs", [])
    source_ids = [item.get("spec_id") for item in source_specs if isinstance(item.get("spec_id"), str)]
    for duplicate in sorted(_duplicates(source_ids)):
        errors.append({
            "code": "duplicate_source_spec",
            "path": "$.source_specs",
            "message": f"source spec {duplicate!r} is declared more than once",
        })
    source_id_set = set(source_ids)

    sections = document.get("sections", [])
    section_ids = [item.get("id") for item in sections if isinstance(item.get("id"), str)]
    for duplicate in sorted(_duplicates(section_ids)):
        errors.append({
            "code": "duplicate_section_id",
            "path": "$.sections",
            "message": f"section id {duplicate!r} is declared more than once",
        })
    orders = [item.get("order") for item in sections if isinstance(item.get("order"), int)]
    for duplicate in sorted(_duplicates([str(value) for value in orders])):
        errors.append({
            "code": "duplicate_section_order",
            "path": "$.sections",
            "message": f"section order {duplicate} is used more than once",
        })
    section_id_set = set(section_ids)

    block_ids: list[str] = []
    for section in sections:
        for block in section.get("content_blocks", []):
            block_id = block.get("id")
            if isinstance(block_id, str):
                block_ids.append(block_id)
    for duplicate in sorted(_duplicates(block_ids)):
        errors.append({
            "code": "duplicate_content_block_id",
            "path": "$.sections",
            "message": f"content block id {duplicate!r} is declared more than once",
        })

    checkpoint_ids = [
        item.get("id") for item in document.get("human_checkpoints", [])
        if isinstance(item.get("id"), str)
    ]
    claim_ids = [
        item.get("id") for item in document.get("claims", [])
        if isinstance(item.get("id"), str)
    ]
    for duplicate in sorted(_duplicates(checkpoint_ids + claim_ids + block_ids + section_ids)):
        errors.append({
            "code": "duplicate_blueprint_id",
            "path": "$",
            "message": f"blueprint id {duplicate!r} is reused across sections, blocks, claims or checkpoints",
        })

    for group_name in ("model_placements", "formula_placements", "output_placements"):
        for index, item in enumerate(document.get(group_name, [])):
            if item.get("source_spec_id") not in source_id_set:
                errors.append({
                    "code": "unknown_source_spec",
                    "path": f"$.{group_name}[{index}].source_spec_id",
                    "message": f"source spec {item.get('source_spec_id')!r} is not declared",
                })
            if item.get("owner_section_id") not in section_id_set:
                errors.append({
                    "code": "unknown_owner_section",
                    "path": f"$.{group_name}[{index}].owner_section_id",
                    "message": f"owner section {item.get('owner_section_id')!r} is not declared",
                })

    for index, claim in enumerate(document.get("claims", [])):
        if claim.get("source_spec_id") not in source_id_set:
            errors.append({
                "code": "unknown_claim_source_spec",
                "path": f"$.claims[{index}].source_spec_id",
                "message": f"source spec {claim.get('source_spec_id')!r} is not declared",
            })
        if claim.get("owner_section_id") not in section_id_set:
            errors.append({
                "code": "unknown_claim_owner_section",
                "path": f"$.claims[{index}].owner_section_id",
                "message": f"owner section {claim.get('owner_section_id')!r} is not declared",
            })
        if claim.get("status") == "qualified" and not claim.get("qualification"):
            errors.append({
                "code": "missing_claim_qualification",
                "path": f"$.claims[{index}].qualification",
                "message": "qualified claims must state the qualification",
            })

    formula_labels = [
        item.get("label") for item in document.get("formula_placements", [])
        if isinstance(item.get("label"), str)
    ]
    output_labels = [
        item.get("label") for item in document.get("output_placements", [])
        if isinstance(item.get("label"), str)
    ]
    for duplicate in sorted(_duplicates(formula_labels + output_labels)):
        errors.append({
            "code": "duplicate_paper_label",
            "path": "$",
            "message": f"paper label {duplicate!r} is assigned more than once",
        })

    formula_owners: dict[tuple[str, str], list[int]] = {}
    for index, item in enumerate(document.get("formula_placements", [])):
        key = (str(item.get("source_spec_id")), str(item.get("formula_id")))
        if item.get("mode") in {"define", "appendix"}:
            formula_owners.setdefault(key, []).append(index)
            if not item.get("label"):
                errors.append({
                    "code": "missing_formula_label",
                    "path": f"$.formula_placements[{index}].label",
                    "message": "defined or appendix formulas require a locked paper label",
                })
    for key, owners in formula_owners.items():
        if len(owners) > 1:
            errors.append({
                "code": "multiple_formula_owners",
                "path": "$.formula_placements",
                "message": f"formula {key[1]!r} from {key[0]!r} has multiple definition owners",
            })

    model_owners: dict[tuple[str, str], list[int]] = {}
    for index, item in enumerate(document.get("model_placements", [])):
        key = (str(item.get("source_spec_id")), str(item.get("model_id")))
        if item.get("mode") in {"define", "appendix"}:
            model_owners.setdefault(key, []).append(index)
    for key, owners in model_owners.items():
        if len(owners) > 1:
            errors.append({
                "code": "multiple_model_owners",
                "path": "$.model_placements",
                "message": f"model {key[1]!r} from {key[0]!r} has multiple definition owners",
            })

    if specs is not None:
        inventories = {spec_id: _spec_inventory(spec) for spec_id, spec in specs.items()}
        declared_by_id = {item.get("spec_id"): item for item in source_specs}
        for spec_id, inventory in inventories.items():
            source = declared_by_id.get(spec_id, {})
            if document.get("status") in {"frozen", "validated"} and inventory["status"] in {
                "draft", "blocked", "deprecated"
            }:
                errors.append({
                    "code": "unfrozen_source_spec",
                    "path": "$.source_specs",
                    "message": f"frozen blueprint cannot depend on source spec {spec_id!r} with status {inventory['status']!r}",
                })
            require_complete = (
                source.get("required_for_writing", True)
                and source.get("role") not in {"reference_only", "excluded"}
            )
            model_items = [
                item for item in document.get("model_placements", [])
                if item.get("source_spec_id") == spec_id
            ]
            formula_items = [
                item for item in document.get("formula_placements", [])
                if item.get("source_spec_id") == spec_id
            ]
            output_items = [
                item for item in document.get("output_placements", [])
                if item.get("source_spec_id") == spec_id
            ]
            for item in model_items:
                if item.get("model_id") not in inventory["models"]:
                    errors.append({
                        "code": "unknown_model_id",
                        "path": "$.model_placements",
                        "message": f"model {item.get('model_id')!r} is absent from source spec {spec_id!r}",
                    })
            for item in formula_items:
                if item.get("formula_id") not in inventory["formulas"]:
                    errors.append({
                        "code": "unknown_formula_id",
                        "path": "$.formula_placements",
                        "message": f"formula {item.get('formula_id')!r} is absent from source spec {spec_id!r}",
                    })
            for item in output_items:
                if item.get("output_id") not in inventory["outputs"]:
                    errors.append({
                        "code": "unknown_output_id",
                        "path": "$.output_placements",
                        "message": f"output {item.get('output_id')!r} is absent from source spec {spec_id!r}",
                    })

            if require_complete:
                placed_models = {item.get("model_id") for item in model_items}
                placed_formulas = {item.get("formula_id") for item in formula_items}
                placed_outputs = {item.get("output_id") for item in output_items}
                for missing in sorted(inventory["models"] - placed_models):
                    errors.append({
                        "code": "unplaced_model",
                        "path": "$.model_placements",
                        "message": f"model {missing!r} from {spec_id!r} lacks define, reference, appendix or omit disposition",
                    })
                for missing in sorted(inventory["formulas"] - placed_formulas):
                    errors.append({
                        "code": "unplaced_formula",
                        "path": "$.formula_placements",
                        "message": f"formula {missing!r} from {spec_id!r} lacks define, reference, appendix or omit disposition",
                    })
                for missing in sorted(inventory["outputs"] - placed_outputs):
                    errors.append({
                        "code": "unplaced_output",
                        "path": "$.output_placements",
                        "message": f"output {missing!r} from {spec_id!r} lacks a paper representation or omit disposition",
                    })
                for formula_id in inventory["formulas"]:
                    items = [item for item in formula_items if item.get("formula_id") == formula_id]
                    non_omit = [item for item in items if item.get("mode") != "omit"]
                    owners = [item for item in items if item.get("mode") in {"define", "appendix"}]
                    if non_omit and len(owners) != 1:
                        errors.append({
                            "code": "missing_formula_owner",
                            "path": "$.formula_placements",
                            "message": f"included formula {formula_id!r} from {spec_id!r} requires exactly one definition owner",
                        })
                for model_id in inventory["models"]:
                    items = [item for item in model_items if item.get("model_id") == model_id]
                    non_omit = [item for item in items if item.get("mode") != "omit"]
                    owners = [item for item in items if item.get("mode") in {"define", "appendix"}]
                    if non_omit and len(owners) != 1:
                        errors.append({
                            "code": "missing_model_owner",
                            "path": "$.model_placements",
                            "message": f"included model {model_id!r} from {spec_id!r} requires exactly one definition owner",
                        })

            for index, claim in enumerate(document.get("claims", [])):
                if claim.get("source_spec_id") != spec_id:
                    continue
                text = claim.get("text")
                status = claim.get("status")
                if status in {"allowed", "qualified"} and text not in inventory["allowed_claims"]:
                    errors.append({
                        "code": "claim_not_allowed_by_model_spec",
                        "path": f"$.claims[{index}].text",
                        "message": f"claim is not listed as allowed in source spec {spec_id!r}",
                    })
                if status == "forbidden" and text not in inventory["forbidden_claims"]:
                    errors.append({
                        "code": "claim_not_forbidden_by_model_spec",
                        "path": f"$.claims[{index}].text",
                        "message": f"forbidden claim is not listed in source spec {spec_id!r}",
                    })

        all_known_ids = set(section_ids) | set(block_ids)
        for inventory in inventories.values():
            all_known_ids.update(inventory["all_ids"])
        for s_index, section in enumerate(sections):
            for b_index, block in enumerate(section.get("content_blocks", [])):
                for r_index, source_id in enumerate(block.get("source_ids", [])):
                    if source_id not in all_known_ids:
                        errors.append({
                            "code": "unresolved_content_source",
                            "path": f"$.sections[{s_index}].content_blocks[{b_index}].source_ids[{r_index}]",
                            "message": f"content source {source_id!r} is not declared by a section or source spec",
                        })

    if document.get("status") in {"frozen", "validated"}:
        for index, checkpoint in enumerate(document.get("human_checkpoints", [])):
            if checkpoint.get("status") == "pending":
                errors.append({
                    "code": "pending_blueprint_checkpoint",
                    "path": f"$.human_checkpoints[{index}].status",
                    "message": "frozen or validated blueprints cannot retain pending human checkpoints",
                })

    return errors, warnings


def _path_errors(
    document: dict[str, Any],
    repo_root: Path,
) -> tuple[list[dict[str, str]], dict[str, dict[str, Any]]]:
    errors: list[dict[str, str]] = []
    specs: dict[str, dict[str, Any]] = {}
    candidates: list[tuple[str, str, str | None]] = []
    for index, source in enumerate(document.get("source_specs", [])):
        candidates.append((
            f"$.source_specs[{index}].path",
            source.get("path", ""),
            source.get("spec_id"),
        ))
    for index, path in enumerate(document.get("evidence_paths", [])):
        candidates.append((f"$.evidence_paths[{index}]", path, None))
    for index, checkpoint in enumerate(document.get("human_checkpoints", [])):
        if checkpoint.get("record"):
            candidates.append((f"$.human_checkpoints[{index}].record", checkpoint["record"], None))

    root = repo_root.resolve()
    for json_path, raw_path, spec_id in candidates:
        if not raw_path or "://" in raw_path:
            continue
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
            continue
        if spec_id:
            try:
                spec = _load_document(candidate)
            except PaperBlueprintError as exc:
                errors.append({
                    "code": "unreadable_source_spec",
                    "path": json_path,
                    "message": str(exc),
                })
                continue
            if spec.get("spec_id") != spec_id:
                errors.append({
                    "code": "source_spec_id_mismatch",
                    "path": json_path,
                    "message": f"expected {spec_id!r}, found {spec.get('spec_id')!r}",
                })
            else:
                specs[spec_id] = spec
    return errors, specs


def validate_paper_blueprint(
    document: dict[str, Any],
    schema: dict[str, Any],
    *,
    repo_root: Path | None = None,
    check_paths: bool = False,
) -> dict[str, Any]:
    errors = _schema_errors(document, schema)
    warnings: list[dict[str, str]] = []
    specs = None
    if not errors and check_paths:
        if repo_root is None:
            raise PaperBlueprintError("repo_root is required when check_paths is enabled")
        path_errors, loaded_specs = _path_errors(document, repo_root)
        errors.extend(path_errors)
        specs = loaded_specs
    if not errors:
        semantic_errors, semantic_warnings = _semantic_errors(document, specs=specs)
        errors.extend(semantic_errors)
        warnings.extend(semantic_warnings)
    return {
        "schema_version": 1,
        "validator": "shumo_paper_blueprint_validator",
        "blueprint_id": document.get("blueprint_id"),
        "status": "pass" if not errors else "fail",
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a Shumo paper blueprint")
    parser.add_argument("--blueprint", required=True, type=Path)
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "specs" / "paper_blueprint.schema.json",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--check-paths", action="store_true")
    args = parser.parse_args(argv)

    try:
        document = _load_document(args.blueprint)
        schema = _load_schema(args.schema)
        report = validate_paper_blueprint(
            document, schema, repo_root=args.repo_root, check_paths=args.check_paths
        )
    except PaperBlueprintError as exc:
        report = {
            "schema_version": 1,
            "validator": "shumo_paper_blueprint_validator",
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
