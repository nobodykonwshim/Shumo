import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "skills" / "math_modeling" / "validation" / "sensitivity_policy_validator.py"
SCHEMA_PATH = ROOT / "skills" / "math_modeling" / "specs" / "sensitivity_policy.schema.json"
EXAMPLE_PATH = ROOT / "skills" / "math_modeling" / "specs" / "sensitivity_policy.example.yaml"

spec = importlib.util.spec_from_file_location("sensitivity_policy_validator", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class SensitivityPolicyValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.valid = yaml.safe_load(EXAMPLE_PATH.read_text(encoding="utf-8"))

    def validate(self, document, **kwargs):
        return module.validate_sensitivity_policy(document, self.schema, **kwargs)

    def test_generic_example_passes(self):
        report = self.validate(copy.deepcopy(self.valid))
        self.assertEqual(report["status"], "pass")

    def test_skill_default_thresholds_are_forbidden(self):
        document = copy.deepcopy(self.valid)
        document["governance"]["default_thresholds_used"] = True
        report = self.validate(document)
        self.assertTrue(any(error["code"] == "schema_violation" for error in report["errors"]))

    def test_post_result_declaration_is_forbidden(self):
        document = copy.deepcopy(self.valid)
        document["governance"]["declared_before_final_result"] = False
        report = self.validate(document)
        self.assertTrue(any(error["code"] == "schema_violation" for error in report["errors"]))

    def test_unresolved_rule_metric_is_rejected(self):
        document = copy.deepcopy(self.valid)
        document["scope"]["acceptance_rules"][0]["metric_ids"].append("UNKNOWN-METRIC")
        report = self.validate(document)
        self.assertTrue(any(error["code"] == "unresolved_metric_reference" for error in report["errors"]))

    def test_executed_policy_requires_required_rule_results(self):
        document = copy.deepcopy(self.valid)
        document["status"] = "executed"
        document["governance"]["freeze_record"] = "records/freeze.yaml"
        document["execution"]["status"] = "completed"
        document["execution"]["evidence_paths"] = ["records/result.json"]
        report = self.validate(document)
        self.assertTrue(any(error["code"] == "missing_required_rule_result" for error in report["errors"]))

    def test_executed_policy_with_result_passes_semantics(self):
        document = copy.deepcopy(self.valid)
        document["status"] = "executed"
        document["governance"]["freeze_record"] = "records/freeze.yaml"
        document["execution"] = {
            "status": "completed",
            "evidence_paths": ["records/result.json"],
            "results": [
                {
                    "rule_id": "SENS-RULE-REPORT",
                    "status": "pass",
                    "summary": "All declared perturbations and metrics were reported.",
                }
            ],
        }
        report = self.validate(document)
        self.assertEqual(report["status"], "pass")

    def test_model_spec_targets_are_checked_when_paths_enabled(self):
        document = copy.deepcopy(self.valid)
        document["scope"]["perturbations"][0]["target_id"] = "UNKNOWN-PARAMETER"
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            model_path = repo / "skills/math_modeling/specs/model_spec.example.yaml"
            model_path.parent.mkdir(parents=True)
            model_path.write_text(
                "schema_version: '1.0'\n"
                "spec_id: MODEL-DEMO-TRANSPORT-01\n"
                "problem_id: demo_transport\n"
                "objective: {metrics: []}\n"
                "inputs: []\n"
                "symbols: {variables: [], parameters: []}\n"
                "assumptions: []\n"
                "model_components: []\n"
                "formulas: []\n"
                "constraints: []\n"
                "algorithm: {steps: []}\n"
                "outputs: []\n"
                "validation: {checks: []}\n"
                "human_checkpoints: []\n",
                encoding="utf-8",
            )
            report = self.validate(document, repo_root=repo, check_paths=True)
        self.assertTrue(any(error["code"] == "unresolved_model_target" for error in report["errors"]))

    def test_post_result_amendment_cannot_replace_original_rule(self):
        document = copy.deepcopy(self.valid)
        document["amendments"] = [
            {
                "id": "AMEND-POST",
                "timing": "post_result",
                "reason": "Observed result was inconvenient.",
                "approved_by": "team",
                "preserves_original_rule": False,
                "record": "records/amendment.yaml",
            }
        ]
        report = self.validate(document)
        self.assertTrue(any(error["code"] == "post_result_rule_replacement" for error in report["errors"]))


if __name__ == "__main__":
    unittest.main()
