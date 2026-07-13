import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "skills" / "math_modeling" / "validation" / "modeling_decision_validator.py"
SCHEMA_PATH = ROOT / "skills" / "math_modeling" / "specs" / "modeling_decision.schema.json"
EXAMPLE_PATH = ROOT / "skills" / "math_modeling" / "specs" / "modeling_decision.example.yaml"
CASE_PATH = ROOT / "tests" / "case001" / "artifacts" / "modeling" / "problem3.model-decision.yaml"

spec = importlib.util.spec_from_file_location("modeling_decision_validator", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class ModelingDecisionValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.valid = yaml.safe_load(EXAMPLE_PATH.read_text(encoding="utf-8"))
        cls.case = yaml.safe_load(CASE_PATH.read_text(encoding="utf-8"))

    def validate(self, document, **kwargs):
        return module.validate_modeling_decision(document, self.schema, **kwargs)

    def test_generic_example_passes(self):
        report = self.validate(copy.deepcopy(self.valid))
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["error_count"], 0)

    def test_frozen_case_demonstration_passes_with_paths(self):
        report = self.validate(copy.deepcopy(self.case), repo_root=ROOT, check_paths=True)
        self.assertEqual(report["status"], "pass")

    def test_requires_at_least_two_candidate_routes(self):
        document = copy.deepcopy(self.valid)
        document["candidate_routes"] = document["candidate_routes"][:1]
        document["comparison_matrix"] = document["comparison_matrix"][:1]
        report = self.validate(document)
        self.assertTrue(any(error["code"] == "schema_violation" for error in report["errors"]))

    def test_duplicate_candidate_id_is_rejected(self):
        document = copy.deepcopy(self.valid)
        document["candidate_routes"][1]["id"] = document["candidate_routes"][0]["id"]
        report = self.validate(document)
        self.assertTrue(any(error["code"] == "duplicate_id" for error in report["errors"]))

    def test_incomplete_comparison_row_is_rejected(self):
        document = copy.deepcopy(self.valid)
        document["comparison_matrix"][0]["assessments"].pop()
        report = self.validate(document)
        self.assertTrue(any(error["code"] == "incomplete_comparison_row" for error in report["errors"]))

    def test_unknown_recommended_candidate_is_rejected(self):
        document = copy.deepcopy(self.valid)
        document["recommendation"]["selected_candidate_id"] = "ROUTE-UNKNOWN"
        report = self.validate(document)
        self.assertTrue(any(error["code"] == "unknown_recommended_candidate" for error in report["errors"]))

    def test_retroactive_decision_record_is_rejected(self):
        document = copy.deepcopy(self.valid)
        document["declared_before_implementation"] = False
        report = self.validate(document)
        self.assertTrue(any(error["code"] == "retroactive_model_selection" for error in report["errors"]))

    def test_rejected_candidate_requires_reason(self):
        document = copy.deepcopy(self.valid)
        document["candidate_routes"][2]["status"] = "rejected"
        report = self.validate(document)
        self.assertTrue(any(error["code"] == "missing_rejection_reason" for error in report["errors"]))

    def test_frozen_record_requires_human_approval(self):
        document = copy.deepcopy(self.case)
        document["human_checkpoint"]["status"] = "pending"
        report = self.validate(document)
        self.assertTrue(any(error["code"] == "frozen_without_human_approval" for error in report["errors"]))

    def test_recommended_candidate_cannot_fail_hard_criterion(self):
        document = copy.deepcopy(self.valid)
        row = next(
            row for row in document["comparison_matrix"]
            if row["candidate_id"] == document["recommendation"]["selected_candidate_id"]
        )
        assessment = next(item for item in row["assessments"] if item["criterion_id"] == "CRIT-NO-LEAKAGE")
        assessment["rating"] = "fail"
        report = self.validate(document)
        self.assertTrue(any(error["code"] == "recommended_candidate_fails_hard_criterion" for error in report["errors"]))

    def test_missing_repository_path_is_rejected(self):
        document = copy.deepcopy(self.valid)
        document["provenance"]["source_paths"] = ["missing/problem.md"]
        with tempfile.TemporaryDirectory() as temp_dir:
            report = self.validate(document, repo_root=Path(temp_dir), check_paths=True)
        self.assertTrue(any(error["code"] == "missing_repository_path" for error in report["errors"]))


if __name__ == "__main__":
    unittest.main()
