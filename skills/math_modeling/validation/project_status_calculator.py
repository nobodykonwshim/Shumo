#!/usr/bin/env python3
"""Calculate and validate the lifecycle status of a Shumo modeling project."""
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


PROJECT_STATES = {
    "needs_model_candidates",
    "waiting_for_human_decision",
    "ready_for_implementation",
    "ready_for_validation",
    "ready_for_paper",
    "blocked",
    "demonstration_complete",
}


class ProjectStatusError(ValueError):
    """Raised when a project or artifact document cannot be read."""


def _load_document(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ProjectStatusError(f"cannot read {path}: {exc}") from exc
    try:
        if path.suffix.lower() == ".json":
            data = json.loads(text)
        else:
            if yaml is None:
                raise ProjectStatusError("PyYAML is required for YAML project records")
            data = yaml.safe_load(text)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ProjectStatusError(f"cannot parse {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ProjectStatusError(f"document root must be an object: {path}")
    return data


def _format_json_path(parts: Iterable[Any]) -> str:
    result = "$"
    for part in parts:
        result += f"[{part}]" if isinstance(part, int) else f".{part}"
    return result


def _issue(code: str, path: str, message: str) -> dict[str, str]:
    return {"code": code, "path": path, "message": message}


def _schema_errors(document: dict[str, Any], schema: dict[str, Any]) -> list[dict[str, str]]:
    if Draft202012Validator is None:
        raise ProjectStatusError("jsonschema is required to validate project status records")
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(document), key=lambda error: list(error.absolute_path))
    return [
        _issue("schema_violation", _format_json_path(error.absolute_path), error.message)
        for error in errors
    ]


def _resolve_repo_path(repo_root: Path, raw_path: str) -> Path:
    root = repo_root.resolve()
    candidate = (repo_root / raw_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ProjectStatusError(f"repository path escapes repo root: {raw_path}") from exc
    return candidate


def _load_repo_artifact(
    repo_root: Path,
    raw_path: str,
    json_path: str,
    errors: list[dict[str, str]],
) -> dict[str, Any] | None:
    try:
        path = _resolve_repo_path(repo_root, raw_path)
    except ProjectStatusError as exc:
        errors.append(_issue("path_outside_repository", json_path, str(exc)))
        return None
    if not path.exists():
        errors.append(_issue("missing_repository_path", json_path, f"repository path does not exist: {raw_path}"))
        return None
    try:
        return _load_document(path)
    except ProjectStatusError as exc:
        errors.append(_issue("invalid_artifact", json_path, str(exc)))
        return None


def _check_declared_path(
    repo_root: Path,
    raw_path: str,
    json_path: str,
    errors: list[dict[str, str]],
) -> None:
    try:
        path = _resolve_repo_path(repo_root, raw_path)
    except ProjectStatusError as exc:
        errors.append(_issue("path_outside_repository", json_path, str(exc)))
        return
    if not path.exists():
        errors.append(_issue("missing_repository_path", json_path, f"repository path does not exist: {raw_path}"))


def _required_checks_pass(model_spec: dict[str, Any]) -> tuple[bool, list[str]]:
    failures: list[str] = []
    for check in model_spec.get("validation", {}).get("checks", []):
        if check.get("required") and check.get("status") not in {"pass", "not_applicable"}:
            failures.append(str(check.get("id", "unknown-check")))
    return not failures, failures


def _pending_checkpoints(document: dict[str, Any]) -> list[str]:
    pending: list[str] = []
    checkpoint = document.get("human_checkpoint")
    if isinstance(checkpoint, dict) and checkpoint.get("status") == "pending":
        pending.append(str(checkpoint.get("decision", checkpoint.get("id", "human checkpoint"))))
    for item in document.get("human_checkpoints", []):
        if isinstance(item, dict) and item.get("status") == "pending":
            pending.append(str(item.get("decision", item.get("id", "human checkpoint"))))
    return pending


def _check_sensitivity_policy(
    policy: dict[str, Any],
    path_label: str,
    repo_root: Path,
    check_paths: bool,
    errors: list[dict[str, str]],
    warnings: list[dict[str, str]],
) -> bool:
    """Return True when the policy still requires execution or repair."""
    status = policy.get("status")
    execution = policy.get("execution", {})
    needs_validation = status != "executed" or execution.get("status") != "completed"
    if status == "executed":
        required_rule_ids = {
            rule.get("id")
            for rule in policy.get("scope", {}).get("acceptance_rules", [])
            if rule.get("required") and isinstance(rule.get("id"), str)
        }
        result_by_id = {
            result.get("rule_id"): result
            for result in execution.get("results", [])
            if isinstance(result, dict)
        }
        for rule_id in sorted(required_rule_ids):
            result = result_by_id.get(rule_id)
            if result is None:
                errors.append(_issue(
                    "missing_sensitivity_result",
                    path_label,
                    f"executed sensitivity policy lacks a result for required rule {rule_id!r}",
                ))
            elif result.get("status") != "pass":
                errors.append(_issue(
                    "failed_sensitivity_rule",
                    path_label,
                    f"required sensitivity rule {rule_id!r} did not pass",
                ))
        if check_paths:
            for index, raw_path in enumerate(execution.get("evidence_paths", [])):
                _check_declared_path(
                    repo_root,
                    raw_path,
                    f"{path_label}.execution.evidence_paths[{index}]",
                    errors,
                )
    else:
        warnings.append(_issue(
            "sensitivity_not_executed",
            path_label,
            "sensitivity policy is not fully executed",
        ))
    return needs_validation


def _check_blueprint(
    blueprint: dict[str, Any],
    blueprint_path: str,
    model_spec: dict[str, Any] | None,
    model_spec_path: str | None,
    errors: list[dict[str, str]],
    warnings: list[dict[str, str]],
) -> None:
    if model_spec is None or model_spec_path is None:
        errors.append(_issue(
            "blueprint_without_model_spec",
            blueprint_path,
            "paper blueprint is present without a linked model specification",
        ))
        return

    source_spec_id = model_spec.get("spec_id")
    source_entries = blueprint.get("source_specs", [])
    matching = [
        entry for entry in source_entries
        if entry.get("spec_id") == source_spec_id and entry.get("path") == model_spec_path
    ]
    if not matching:
        errors.append(_issue(
            "untraceable_blueprint_source",
            blueprint_path,
            "paper blueprint does not trace to the linked model specification path and id",
        ))

    if model_spec.get("status") != "solved":
        errors.append(_issue(
            "blueprint_references_unfrozen_model",
            blueprint_path,
            f"paper blueprint references model status {model_spec.get('status')!r}, not 'solved'",
        ))

    allowed = set(model_spec.get("claims", {}).get("allowed", []))
    forbidden = set(model_spec.get("claims", {}).get("forbidden", []))
    for index, claim in enumerate(blueprint.get("claims", [])):
        text = claim.get("text")
        status = claim.get("status")
        if status == "allowed" and text not in allowed:
            errors.append(_issue(
                "unsupported_paper_claim",
                f"{blueprint_path}.claims[{index}]",
                "allowed paper claim is not allowed by the source model specification",
            ))
        if status == "forbidden" and text not in forbidden:
            errors.append(_issue(
                "untraceable_forbidden_claim",
                f"{blueprint_path}.claims[{index}]",
                "forbidden paper claim is not declared by the source model specification",
            ))

    pending = _pending_checkpoints(blueprint)
    if pending:
        warnings.append(_issue(
            "paper_checkpoint_pending",
            blueprint_path,
            "paper blueprint still requires human architecture approval",
        ))
    if blueprint.get("status") == "frozen" and pending:
        errors.append(_issue(
            "frozen_blueprint_with_pending_checkpoint",
            blueprint_path,
            "a frozen paper blueprint cannot retain a pending human checkpoint",
        ))


def calculate_project_status(
    project: dict[str, Any],
    schema: dict[str, Any],
    *,
    repo_root: Path,
    check_paths: bool = False,
    expected_status_override: str | None = None,
) -> dict[str, Any]:
    errors = _schema_errors(project, schema)
    warnings: list[dict[str, str]] = []
    completed: list[str] = []
    pending_human: list[str] = []
    status_reasons: list[str] = []
    artifact_summary = {
        "problem_bundles": len(project.get("problem_bundles", [])),
        "loaded_decisions": 0,
        "loaded_model_specs": 0,
        "loaded_sensitivity_policies": 0,
        "loaded_paper_blueprints": 0,
    }

    if errors:
        return {
            "schema_version": 1,
            "calculator": "shumo_project_status_calculator",
            "project_id": project.get("project_id"),
            "validation_status": "fail",
            "project_status": "blocked",
            "status_reasons": ["project status record violates its structural schema"],
            "completed": completed,
            "pending_human_decisions": pending_human,
            "blockers": [error["message"] for error in errors],
            "next_valid_actions": [],
            "artifact_summary": artifact_summary,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "errors": errors,
            "warnings": warnings,
        }

    any_missing_candidates = False
    any_ready_for_implementation = False
    any_needs_validation = False

    for bundle_index, bundle in enumerate(project.get("problem_bundles", [])):
        prefix = f"$.problem_bundles[{bundle_index}]"
        problem_id = bundle.get("problem_id")
        decision_path = bundle.get("modeling_decision_path")
        spec_path = bundle.get("model_spec_path")
        blueprint_path = bundle.get("paper_blueprint_path")

        decision: dict[str, Any] | None = None
        model_spec: dict[str, Any] | None = None

        if decision_path:
            decision = _load_repo_artifact(repo_root, decision_path, f"{prefix}.modeling_decision_path", errors)
            if decision is not None:
                artifact_summary["loaded_decisions"] += 1
                if decision.get("project_id") != project.get("project_id"):
                    errors.append(_issue(
                        "project_id_mismatch",
                        f"{prefix}.modeling_decision_path",
                        "modeling decision project_id does not match project status record",
                    ))
                if decision.get("problem_id") != problem_id:
                    errors.append(_issue(
                        "problem_id_mismatch",
                        f"{prefix}.modeling_decision_path",
                        "modeling decision problem_id does not match bundle problem_id",
                    ))
                candidates = decision.get("candidate_routes", [])
                if not candidates:
                    any_missing_candidates = True
                selected_id = decision.get("recommendation", {}).get("selected_candidate_id")
                selected_candidates = [item for item in candidates if item.get("id") == selected_id]
                if not selected_id or not selected_candidates:
                    any_missing_candidates = True
                    errors.append(_issue(
                        "missing_selected_candidate",
                        f"{prefix}.modeling_decision_path",
                        "decision recommendation does not resolve to a candidate route",
                    ))
                elif selected_candidates[0].get("status") != "selected":
                    errors.append(_issue(
                        "selected_candidate_status_mismatch",
                        f"{prefix}.modeling_decision_path",
                        "recommended candidate is not marked selected",
                    ))

                checkpoint = decision.get("human_checkpoint", {})
                recommendation = decision.get("recommendation", {})
                if recommendation.get("requires_human_decision") or checkpoint.get("status") == "pending":
                    pending_human.append(str(checkpoint.get("decision", f"approve model route for {problem_id}")))
                if decision.get("status") == "frozen" and checkpoint.get("status") != "approved":
                    errors.append(_issue(
                        "frozen_decision_without_approval",
                        f"{prefix}.modeling_decision_path",
                        "a frozen modeling decision requires an approved human checkpoint",
                    ))
                if decision.get("status") == "frozen" and checkpoint.get("status") == "approved":
                    completed.append(f"{problem_id}: modeling decision frozen and approved")
        else:
            any_missing_candidates = True

        if spec_path:
            model_spec = _load_repo_artifact(repo_root, spec_path, f"{prefix}.model_spec_path", errors)
            if model_spec is not None:
                artifact_summary["loaded_model_specs"] += 1
                if decision is None:
                    errors.append(_issue(
                        "model_spec_without_decision",
                        f"{prefix}.model_spec_path",
                        "model specification exists without a modeling decision record",
                    ))
                if model_spec.get("problem_id") != problem_id:
                    errors.append(_issue(
                        "problem_id_mismatch",
                        f"{prefix}.model_spec_path",
                        "model specification problem_id does not match bundle problem_id",
                    ))

                traceability = bundle.get("traceability")
                if decision is not None and traceability:
                    selected_id = decision.get("recommendation", {}).get("selected_candidate_id")
                    if traceability.get("selected_candidate_id") != selected_id:
                        errors.append(_issue(
                            "selected_route_traceability_mismatch",
                            f"{prefix}.traceability.selected_candidate_id",
                            "bundle traceability does not match the selected decision candidate",
                        ))
                    component_ids = {
                        item.get("id") for item in model_spec.get("model_components", [])
                        if isinstance(item, dict)
                    }
                    for component_id in traceability.get("model_component_ids", []):
                        if component_id not in component_ids:
                            errors.append(_issue(
                                "missing_model_component_trace",
                                f"{prefix}.traceability.model_component_ids",
                                f"selected route trace references missing model component {component_id!r}",
                            ))

                spec_status = model_spec.get("status")
                if spec_status == "blocked":
                    errors.append(_issue(
                        "blocked_model_spec",
                        f"{prefix}.model_spec_path",
                        "linked model specification is blocked",
                    ))
                elif spec_status == "draft":
                    any_ready_for_implementation = True
                elif spec_status == "partial":
                    any_needs_validation = True
                elif spec_status == "solved":
                    checks_pass, failed_checks = _required_checks_pass(model_spec)
                    if not checks_pass:
                        any_needs_validation = True
                        errors.append(_issue(
                            "unsatisfied_required_validation",
                            f"{prefix}.model_spec_path",
                            f"solved model has unsatisfied required checks: {', '.join(failed_checks)}",
                        ))
                    spec_pending = _pending_checkpoints(model_spec)
                    if spec_pending:
                        pending_human.extend(spec_pending)
                        errors.append(_issue(
                            "solved_model_with_pending_checkpoint",
                            f"{prefix}.model_spec_path",
                            "solved model specification retains a pending human checkpoint",
                        ))
                    if checks_pass and not spec_pending:
                        completed.append(f"{problem_id}: model solved and required validation passed")
                else:
                    any_ready_for_implementation = True
        elif decision is not None and not pending_human:
            any_ready_for_implementation = True

        for policy_index, policy_path in enumerate(bundle.get("sensitivity_policy_paths", [])):
            policy = _load_repo_artifact(
                repo_root,
                policy_path,
                f"{prefix}.sensitivity_policy_paths[{policy_index}]",
                errors,
            )
            if policy is not None:
                artifact_summary["loaded_sensitivity_policies"] += 1
                if _check_sensitivity_policy(
                    policy,
                    f"{prefix}.sensitivity_policy_paths[{policy_index}]",
                    repo_root,
                    check_paths,
                    errors,
                    warnings,
                ):
                    any_needs_validation = True
                else:
                    completed.append(f"{problem_id}: sensitivity policy executed")

        if blueprint_path:
            blueprint = _load_repo_artifact(repo_root, blueprint_path, f"{prefix}.paper_blueprint_path", errors)
            if blueprint is not None:
                artifact_summary["loaded_paper_blueprints"] += 1
                if blueprint.get("project_id") != project.get("project_id"):
                    errors.append(_issue(
                        "project_id_mismatch",
                        f"{prefix}.paper_blueprint_path",
                        "paper blueprint project_id does not match project status record",
                    ))
                _check_blueprint(blueprint, blueprint_path, model_spec, spec_path, errors, warnings)
                completed.append(f"{problem_id}: paper blueprint is traceable to the model specification")

        if check_paths:
            for evidence_index, evidence_path in enumerate(bundle.get("evidence_paths", [])):
                _check_declared_path(
                    repo_root,
                    evidence_path,
                    f"{prefix}.evidence_paths[{evidence_index}]",
                    errors,
                )

    for policy_index, policy_path in enumerate(project.get("supporting_artifacts", {}).get("sensitivity_policy_paths", [])):
        label = f"$.supporting_artifacts.sensitivity_policy_paths[{policy_index}]"
        policy = _load_repo_artifact(repo_root, policy_path, label, errors)
        if policy is not None:
            artifact_summary["loaded_sensitivity_policies"] += 1
            if _check_sensitivity_policy(policy, label, repo_root, check_paths, errors, warnings):
                any_needs_validation = True
            else:
                completed.append(f"supporting sensitivity policy executed: {policy.get('policy_id', policy_path)}")

    if check_paths:
        for evidence_index, evidence_path in enumerate(project.get("supporting_artifacts", {}).get("evidence_paths", [])):
            _check_declared_path(
                repo_root,
                evidence_path,
                f"$.supporting_artifacts.evidence_paths[{evidence_index}]",
                errors,
            )

    waiting_external = [
        item for item in project.get("external_dependencies", [])
        if item.get("status") == "waiting" and item.get("blocks_current_cycle")
    ]
    for item in waiting_external:
        errors.append(_issue(
            "blocking_external_dependency",
            "$.external_dependencies",
            f"external dependency is waiting and blocks this cycle: {item.get('description')}",
        ))

    valid_demo_stop = False
    lifecycle = project.get("lifecycle", {})
    stop_path = lifecycle.get("stop_record_path")
    stop_status = lifecycle.get("stop_status")
    if stop_path:
        stop_record = _load_repo_artifact(repo_root, stop_path, "$.lifecycle.stop_record_path", errors)
        if stop_record is not None:
            recorded_status = stop_record.get("status")
            if recorded_status != stop_status:
                errors.append(_issue(
                    "stop_status_mismatch",
                    "$.lifecycle.stop_status",
                    f"declared stop status {stop_status!r} does not match stop record status {recorded_status!r}",
                ))
            record_project_id = stop_record.get("project_id", stop_record.get("case_id"))
            if record_project_id != project.get("project_id"):
                errors.append(_issue(
                    "stop_record_project_mismatch",
                    "$.lifecycle.stop_record_path",
                    "stop record does not belong to this project",
                ))
            valid_demo_stop = recorded_status == "demonstration_complete" and record_project_id == project.get("project_id")
            if valid_demo_stop:
                completed.append("development-cycle stop record confirms demonstration_complete")
    elif stop_status is not None:
        errors.append(_issue(
            "missing_stop_record",
            "$.lifecycle.stop_record_path",
            "a lifecycle stop status requires a stop record path",
        ))

    if errors:
        calculated_status = "blocked"
        status_reasons.append("one or more cross-artifact consistency or evidence checks failed")
    elif valid_demo_stop:
        calculated_status = "demonstration_complete"
        status_reasons.append("the declared development goal is complete and a valid stop record freezes the cycle")
    elif any_missing_candidates:
        calculated_status = "needs_model_candidates"
        status_reasons.append("at least one required problem bundle lacks a complete candidate-model decision")
    elif pending_human:
        calculated_status = "waiting_for_human_decision"
        status_reasons.append("a modeling decision requiring human authority remains unresolved")
    elif any_ready_for_implementation:
        calculated_status = "ready_for_implementation"
        status_reasons.append("model selection is available but implementation or executable specification is incomplete")
    elif any_needs_validation:
        calculated_status = "ready_for_validation"
        status_reasons.append("implementation artifacts exist but required validation or sensitivity execution remains")
    else:
        calculated_status = "ready_for_paper"
        status_reasons.append("the linked modeling package is solved, validated and traceable for paper preparation")

    expected_status = expected_status_override or project.get("expected_status")
    if expected_status not in PROJECT_STATES:
        errors.append(_issue(
            "invalid_expected_status",
            "$.expected_status",
            f"unknown expected status {expected_status!r}",
        ))
    elif calculated_status != expected_status:
        errors.append(_issue(
            "project_status_drift",
            "$.expected_status",
            f"calculated status {calculated_status!r} does not match expected status {expected_status!r}",
        ))

    next_actions = [
        {
            "id": item.get("id"),
            "description": item.get("description"),
            "authority": item.get("authority"),
        }
        for item in project.get("next_actions", [])
        if item.get("when_status") == calculated_status
    ]

    return {
        "schema_version": 1,
        "calculator": "shumo_project_status_calculator",
        "project_id": project.get("project_id"),
        "cycle_id": project.get("cycle_id"),
        "validation_status": "pass" if not errors else "fail",
        "project_status": calculated_status,
        "expected_status": expected_status,
        "status_reasons": status_reasons,
        "completed": sorted(set(completed)),
        "pending_human_decisions": sorted(set(pending_human)),
        "blockers": [error["message"] for error in errors],
        "next_valid_actions": next_actions,
        "external_dependencies": project.get("external_dependencies", []),
        "artifact_summary": artifact_summary,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Calculate a Shumo project lifecycle status")
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "specs" / "project_status.schema.json",
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--check-paths", action="store_true")
    parser.add_argument("--expect-status", choices=sorted(PROJECT_STATES))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    project = _load_document(args.project)
    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    report = calculate_project_status(
        project,
        schema,
        repo_root=args.repo_root,
        check_paths=args.check_paths,
        expected_status_override=args.expect_status,
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["validation_status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
