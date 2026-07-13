import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "skills" / "math_modeling" / "validation" / "project_status_calculator.py"
SCHEMA_PATH = ROOT / "skills" / "math_modeling" / "specs" / "project_status.schema.json"

spec = importlib.util.spec_from_file_location("project_status_calculator", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class ProjectStatusCalculatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    def write_yaml(self, root: Path, relative: str, document):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
        return relative

    def decision(self, *, status="frozen", human_status="approved", requires_human=False):
        return {
            "schema_version": "1.0",
            "decision_id": "DECISION-DEMO",
            "project_id": "demo_project",
            "problem_id": "demo_problem",
            "status": status,
            "candidate_routes": [
                {"id": "ROUTE-DEMO", "status": "selected"},
                {"id": "ROUTE-ALT", "status": "rejected"},
            ],
            "recommendation": {
                "selected_candidate_id": "ROUTE-DEMO",
                "requires_human_decision": requires_human,
            },
            "human_checkpoint": {
                "decision": "Approve the demo route.",
                "authority": "user",
                "status": human_status,
            },
        }

    def model_spec(self, *, status="solved", validation_status="pass"):
        return {
            "schema_version": "1.0",
            "spec_id": "MODEL-DEMO",
            "problem_id": "demo_problem",
            "status": status,
            "model_components": [{"id": "MODEL-COMPONENT-DEMO"}],
            "validation": {
                "checks": [
                    {
                        "id": "CHECK-DEMO",
                        "required": True,
                        "status": validation_status,
                    }
                ]
            },
            "human_checkpoints": [],
            "claims": {
                "allowed": ["The demo result is valid inside the declared model family."],
                "forbidden": ["The demo result is globally optimal."],
            },
        }

    def project(self, decision_path, model_path, *, expected="ready_for_paper", stop_path=None, stop_status=None):
        return {
            "schema_version": "1.0",
            "status_record_id": "STATUS-DEMO",
            "project_id": "demo_project",
            "cycle_id": "demo_cycle",
            "scope": "development_cycle",
            "declared_goal": "Exercise the project-status calculator.",
            "expected_status": expected,
            "problem_bundles": [
                {
                    "problem_id": "demo_problem",
                    "required_for_cycle": True,
                    "modeling_decision_path": decision_path,
                    "model_spec_path": model_path,
                    "sensitivity_policy_paths": [],
                    "paper_blueprint_path": None,
                    "traceability": {
                        "selected_candidate_id": "ROUTE-DEMO",
                        "model_component_ids": ["MODEL-COMPONENT-DEMO"],
                    },
                    "evidence_paths": [],
                }
            ],
            "supporting_artifacts": {
                "sensitivity_policy_paths": [],
                "evidence_paths": [],
            },
            "lifecycle": {
                "stop_record_path": stop_path,
                "stop_status": stop_status,
                "reopen_requires": [],
            },
            "external_dependencies": [],
            "next_actions": [
                {
                    "id": "ACTION-CANDIDATES",
                    "when_status": "needs_model_candidates",
                    "description": "Generate candidate routes.",
                    "authority": "external",
                },
                {
                    "id": "ACTION-HUMAN",
                    "when_status": "waiting_for_human_decision",
                    "description": "Resolve the pending decision.",
                    "authority": "user",
                },
                {
                    "id": "ACTION-IMPLEMENT",
                    "when_status": "ready_for_implementation",
                    "description": "Implement the approved route.",
                    "authority": "team",
                },
                {
                    "id": "ACTION-VALIDATE",
                    "when_status": "ready_for_validation",
                    "description": "Run required validation.",
                    "authority": "team",
                },
                {
                    "id": "ACTION-PAPER",
                    "when_status": "ready_for_paper",
                    "description": "Prepare the paper blueprint.",
                    "authority": "user",
                },
                {
                    "id": "ACTION-BLOCKED",
                    "when_status": "blocked",
                    "description": "Repair the first blocker.",
                    "authority": "team",
                },
                {
                    "id": "ACTION-STOP",
                    "when_status": "demonstration_complete",
                    "description": "Wait for the next authorized cycle.",
                    "authority": "user",
                },
            ],
            "limitations": [],
        }

    def calculate(self, project, root, **kwargs):
        return module.calculate_project_status(
            project,
            self.schema,
            repo_root=root,
            **kwargs,
        )

    def test_solved_valid_bundle_is_ready_for_paper(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            decision_path = self.write_yaml(root, "artifacts/decision.yaml", self.decision())
            model_path = self.write_yaml(root, "artifacts/model.yaml", self.model_spec())
            report = self.calculate(self.project(decision_path, model_path), root)
        self.assertEqual(report["validation_status"], "pass")
        self.assertEqual(report["project_status"], "ready_for_paper")
        self.assertEqual(report["next_valid_actions"][0]["id"], "ACTION-PAPER")

    def test_missing_decision_and_model_needs_candidates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = self.project(None, None, expected="needs_model_candidates")
            project["problem_bundles"][0].pop("traceability")
            report = self.calculate(project, root)
        self.assertEqual(report["validation_status"], "pass")
        self.assertEqual(report["project_status"], "needs_model_candidates")

    def test_pending_route_decision_waits_for_human(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            decision_path = self.write_yaml(
                root,
                "artifacts/decision.yaml",
                self.decision(status="draft", human_status="pending", requires_human=True),
            )
            project = self.project(decision_path, None, expected="waiting_for_human_decision")
            project["problem_bundles"][0].pop("traceability")
            report = self.calculate(project, root)
        self.assertEqual(report["validation_status"], "pass")
        self.assertEqual(report["project_status"], "waiting_for_human_decision")
        self.assertTrue(report["pending_human_decisions"])

    def test_model_without_decision_is_blocked(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            model_path = self.write_yaml(root, "artifacts/model.yaml", self.model_spec())
            project = self.project(None, model_path, expected="blocked")
            project["problem_bundles"][0].pop("traceability")
            report = self.calculate(project, root)
        self.assertEqual(report["project_status"], "blocked")
        self.assertTrue(any(error["code"] == "model_spec_without_decision" for error in report["errors"]))

    def test_partial_model_is_ready_for_validation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            decision_path = self.write_yaml(root, "artifacts/decision.yaml", self.decision())
            model_path = self.write_yaml(
                root,
                "artifacts/model.yaml",
                self.model_spec(status="partial", validation_status="planned"),
            )
            report = self.calculate(
                self.project(decision_path, model_path, expected="ready_for_validation"),
                root,
            )
        self.assertEqual(report["validation_status"], "pass")
        self.assertEqual(report["project_status"], "ready_for_validation")

    def test_valid_stop_record_freezes_demonstration_cycle(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            decision_path = self.write_yaml(root, "artifacts/decision.yaml", self.decision())
            model_path = self.write_yaml(root, "artifacts/model.yaml", self.model_spec())
            stop_path = self.write_yaml(
                root,
                "run/stop.yaml",
                {"case_id": "demo_project", "status": "demonstration_complete"},
            )
            project = self.project(
                decision_path,
                model_path,
                expected="demonstration_complete",
                stop_path=stop_path,
                stop_status="demonstration_complete",
            )
            report = self.calculate(project, root)
        self.assertEqual(report["validation_status"], "pass")
        self.assertEqual(report["project_status"], "demonstration_complete")

    def test_expected_status_drift_fails_without_rewriting_calculated_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            decision_path = self.write_yaml(root, "artifacts/decision.yaml", self.decision())
            model_path = self.write_yaml(root, "artifacts/model.yaml", self.model_spec())
            project = self.project(decision_path, model_path, expected="ready_for_validation")
            report = self.calculate(project, root)
        self.assertEqual(report["validation_status"], "fail")
        self.assertEqual(report["project_status"], "ready_for_paper")
        self.assertTrue(any(error["code"] == "project_status_drift" for error in report["errors"]))

    def test_missing_evidence_path_blocks_when_path_checks_are_enabled(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            decision_path = self.write_yaml(root, "artifacts/decision.yaml", self.decision())
            model_path = self.write_yaml(root, "artifacts/model.yaml", self.model_spec())
            project = self.project(decision_path, model_path, expected="blocked")
            project["problem_bundles"][0]["evidence_paths"] = ["evidence/missing.yaml"]
            report = self.calculate(project, root, check_paths=True)
        self.assertEqual(report["project_status"], "blocked")
        self.assertTrue(any(error["code"] == "missing_repository_path" for error in report["errors"]))


if __name__ == "__main__":
    unittest.main()
