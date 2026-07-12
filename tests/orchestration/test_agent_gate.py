from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "skills" / "math_modeling" / "orchestration" / "agent_gate.py"
spec = importlib.util.spec_from_file_location("agent_gate", MODULE_PATH)
assert spec and spec.loader
gate = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = gate
spec.loader.exec_module(gate)


def valid_admission():
    return {
        "admission_id": "ADM-P4-ROUTE-001",
        "task_id": "A-P4-ROUTE-01",
        "task": "Generate at most three candidate route families",
        "agent_type": "route_explorer",
        "decision": "bounded_agent",
        "scope": {
            "allowed_actions": ["write_candidate_json"],
            "forbidden_actions": ["modify_registry", "write_paper"],
        },
        "budget": {"max_iterations": 3, "max_tool_calls": 8, "max_candidate_routes": 3},
        "hard_caps": {"max_iterations": 4, "max_tool_calls": 12, "max_candidate_routes": 4},
        "stop_conditions": ["budget_exhausted", "no_new_evidence"],
        "rollback_point": "problem4_pre_agent",
        "contracts": {
            "environment_manifest": {"status": "verified", "path": "env.json", "sha256": "a" * 64},
            "tool_contracts": {"status": "verified", "path": "tools.json", "sha256": "b" * 64},
            "prompt_contract": {"status": "verified", "path": "prompt.json", "sha256": "c" * 64},
        },
        "error_control": {
            "silent_failure_risk": "medium",
            "detectable_failures": ["uncovered_area", "boundary_violation"],
            "validators": [
                {"name": "independent_spatial_evaluator", "status": "pass", "evidence": "report.json"}
            ],
        },
        "reference_access": {
            "state": "quarantined",
            "same_problem_web_search": "forbidden",
            "external_reference_paths_readable": False,
            "exposure_label": "reference_aware_assisted_pilot",
        },
        "human_approval": {"required": True, "status": "approved", "approved_by": "user"},
    }


class AgentGateTests(unittest.TestCase):
    def test_valid_bounded_agent_emits_hash_bound_token(self):
        admission = valid_admission()
        token = gate.issue_token(admission, "route_explorer", "A-P4-ROUTE-01")
        self.assertEqual(token["status"], "admitted")
        self.assertEqual(token["admission_sha256"], gate._sha256(admission))
        self.assertEqual(len(token["token_sha256"]), 64)

    def test_blocked_and_workflow_decisions_are_rejected(self):
        for decision in ("blocked", "workflow", "human_checkpoint"):
            admission = valid_admission()
            admission["decision"] = decision
            with self.assertRaises(gate.GateError):
                gate.issue_token(admission, "route_explorer")

    def test_unverified_contract_is_rejected(self):
        admission = valid_admission()
        admission["contracts"]["tool_contracts"]["status"] = "draft"
        with self.assertRaises(gate.GateError):
            gate.issue_token(admission, "route_explorer")

    def test_reference_leak_before_release_is_rejected(self):
        admission = valid_admission()
        admission["reference_access"]["external_reference_paths_readable"] = True
        with self.assertRaises(gate.GateError):
            gate.issue_token(admission, "route_explorer")

    def test_budget_above_hard_cap_is_rejected(self):
        admission = valid_admission()
        admission["budget"]["max_tool_calls"] = 13
        with self.assertRaises(gate.GateError):
            gate.issue_token(admission, "route_explorer")

    def test_cli_rejects_and_accepts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "admission.json"
            token_path = root / "token.json"
            rollback = root / "problem4_pre_agent"
            rollback.write_text("ready", encoding="utf-8")
            admission = valid_admission()
            for contract in admission["contracts"].values():
                contract_path = root / contract["path"]
                contract_path.write_text(contract["path"], encoding="utf-8")
                contract["sha256"] = gate._file_sha256(contract_path)
            blocked = json.loads(json.dumps(admission))
            blocked["decision"] = "blocked"
            path.write_text(json.dumps(blocked), encoding="utf-8")
            self.assertEqual(
                gate.main([
                    "--admission", str(path), "--agent", "route_explorer",
                    "--repo-root", str(root)
                ]),
                2,
            )
            path.write_text(json.dumps(admission), encoding="utf-8")
            self.assertEqual(
                gate.main([
                    "--admission", str(path), "--agent", "route_explorer",
                    "--task", "A-P4-ROUTE-01", "--output", str(token_path),
                    "--repo-root", str(root)
                ]),
                0,
            )
            self.assertEqual(json.loads(token_path.read_text())["status"], "admitted")


if __name__ == "__main__":
    unittest.main()
