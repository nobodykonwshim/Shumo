#!/usr/bin/env python3
"""Executable admission gate for bounded Shumo Agent runs.

The gate consumes a strict JSON admission envelope. It does not run an Agent. It either
rejects the request with structured reasons or emits a hash-bound execution token that a
runner must require before starting the requested Agent.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

_ALLOWED_DECISIONS = {"workflow", "bounded_agent", "human_checkpoint", "blocked"}
_REQUIRED_CONTRACTS = ("environment_manifest", "tool_contracts", "prompt_contract")


class GateError(ValueError):
    pass


def _canonical_bytes(data: Any) -> bytes:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(data: Any) -> str:
    return hashlib.sha256(_canonical_bytes(data)).hexdigest()


def _nonempty(value: Any) -> bool:
    return value is not None and value != "" and value != [] and value != {}


def validate_admission(
    admission: dict[str, Any], requested_agent: str, requested_task: str | None = None
) -> list[str]:
    errors: list[str] = []
    decision = admission.get("decision")
    if decision not in _ALLOWED_DECISIONS:
        errors.append("decision must be workflow, bounded_agent, human_checkpoint or blocked")
    elif decision != "bounded_agent":
        errors.append(f"decision={decision!r} does not permit autonomous Agent execution")

    if admission.get("agent_type") != requested_agent:
        errors.append("requested agent_type does not match admission")
    if requested_task is not None and admission.get("task_id") != requested_task:
        errors.append("requested task_id does not match admission")

    for field in ("admission_id", "task_id", "task", "agent_type", "rollback_point"):
        if not _nonempty(admission.get(field)):
            errors.append(f"missing required field: {field}")

    scope = admission.get("scope")
    if not isinstance(scope, dict):
        errors.append("scope must be an object")
    else:
        if not _nonempty(scope.get("allowed_actions")):
            errors.append("scope.allowed_actions must not be empty")
        if not _nonempty(scope.get("forbidden_actions")):
            errors.append("scope.forbidden_actions must not be empty")

    budgets = admission.get("budget")
    if not isinstance(budgets, dict):
        errors.append("budget must be an object")
    else:
        for field in ("max_iterations", "max_tool_calls", "max_candidate_routes"):
            value = budgets.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                errors.append(f"budget.{field} must be a positive integer")
        hard_caps = admission.get("hard_caps", {})
        for field, value in budgets.items():
            cap = hard_caps.get(field)
            if isinstance(value, int) and isinstance(cap, int) and value > cap:
                errors.append(f"budget.{field} exceeds hard cap {cap}")

    if not _nonempty(admission.get("stop_conditions")):
        errors.append("stop_conditions must not be empty")

    contracts = admission.get("contracts")
    if not isinstance(contracts, dict):
        errors.append("contracts must be an object")
    else:
        for field in _REQUIRED_CONTRACTS:
            contract = contracts.get(field)
            if not isinstance(contract, dict):
                errors.append(f"contracts.{field} must be an object")
                continue
            if contract.get("status") != "verified":
                errors.append(f"contracts.{field}.status must be verified")
            if not _nonempty(contract.get("path")):
                errors.append(f"contracts.{field}.path is required")
            if not _nonempty(contract.get("sha256")):
                errors.append(f"contracts.{field}.sha256 is required")

    error_control = admission.get("error_control")
    if not isinstance(error_control, dict):
        errors.append("error_control must be an object")
    else:
        if error_control.get("silent_failure_risk") not in ("low", "medium"):
            errors.append("silent_failure_risk must be low or medium")
        if not _nonempty(error_control.get("detectable_failures")):
            errors.append("detectable_failures must not be empty")
        validators = error_control.get("validators")
        if not isinstance(validators, list) or not validators:
            errors.append("validators must be a non-empty list")
        else:
            for index, validator in enumerate(validators):
                if not isinstance(validator, dict) or validator.get("status") != "pass":
                    errors.append(f"validator[{index}] must have status=pass")
                elif not _nonempty(validator.get("evidence")):
                    errors.append(f"validator[{index}].evidence is required")

    reference = admission.get("reference_access")
    if not isinstance(reference, dict):
        errors.append("reference_access must be an object")
    else:
        if reference.get("state") not in ("quarantined", "released"):
            errors.append("reference_access.state must be quarantined or released")
        if reference.get("same_problem_web_search") not in ("forbidden", "released"):
            errors.append("same_problem_web_search must be forbidden or released")
        if reference.get("external_reference_paths_readable") is True and reference.get("state") != "released":
            errors.append("external references cannot be readable before release")
        if not _nonempty(reference.get("exposure_label")):
            errors.append("reference_access.exposure_label is required")

    if admission.get("human_approval", {}).get("required") is True:
        approval = admission.get("human_approval", {})
        if approval.get("status") != "approved" or not _nonempty(approval.get("approved_by")):
            errors.append("required human approval is missing")

    return errors


def issue_token(
    admission: dict[str, Any], requested_agent: str, requested_task: str | None = None
) -> dict[str, Any]:
    errors = validate_admission(admission, requested_agent, requested_task)
    if errors:
        raise GateError("; ".join(errors))
    admission_hash = _sha256(admission)
    token_payload = {
        "schema_version": 1,
        "status": "admitted",
        "admission_id": admission["admission_id"],
        "task_id": admission["task_id"],
        "agent_type": requested_agent,
        "scope": admission["scope"],
        "budget": admission["budget"],
        "stop_conditions": admission["stop_conditions"],
        "rollback_point": admission["rollback_point"],
        "reference_access": admission["reference_access"],
        "admission_sha256": admission_hash,
        "issued_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    token_payload["token_sha256"] = _sha256(token_payload)
    return token_payload


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Agent admission and issue a gate token.")
    parser.add_argument("--admission", required=True, type=Path, help="Strict JSON admission envelope")
    parser.add_argument("--agent", required=True, help="Requested Agent type")
    parser.add_argument("--task", help="Optional expected task id")
    parser.add_argument("--output", type=Path, help="Output token JSON")
    args = parser.parse_args(argv)
    try:
        admission = json.loads(args.admission.read_text(encoding="utf-8"))
        token = issue_token(admission, args.agent, args.task)
    except (OSError, json.JSONDecodeError, GateError) as exc:
        print(json.dumps({"status": "rejected", "message": str(exc)}, ensure_ascii=False))
        return 2

    text = json.dumps(token, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
