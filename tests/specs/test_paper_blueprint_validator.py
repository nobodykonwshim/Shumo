import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "skills" / "math_modeling" / "validation" / "paper_blueprint_validator.py"
SCHEMA_PATH = ROOT / "skills" / "math_modeling" / "specs" / "paper_blueprint.schema.json"
EXAMPLE_PATH = ROOT / "skills" / "math_modeling" / "specs" / "paper_blueprint.example.yaml"

spec = importlib.util.spec_from_file_location("paper_blueprint_validator", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class PaperBlueprintValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.valid = yaml.safe_load(EXAMPLE_PATH.read_text(encoding="utf-8"))

    def validate(self, document, **kwargs):
        return module.validate_paper_blueprint(document, self.schema, **kwargs)

    def test_generic_example_passes_schema_and_semantics(self):
        report = self.validate(copy.deepcopy(self.valid))
        self.assertEqual(report["status"], "pass")

    def test_generic_example_passes_with_source_spec_paths(self):
        report = self.validate(copy.deepcopy(self.valid), repo_root=ROOT, check_paths=True)
        self.assertEqual(report["status"], "pass")

    def test_duplicate_formula_label_is_rejected(self):
        document = copy.deepcopy(self.valid)
        duplicate = copy.deepcopy(document["formula_placements"][0])
        duplicate["formula_id"] = "F-SECOND"
        document["formula_placements"].append(duplicate)
        report = self.validate(document)
        self.assertTrue(any(error["code"] == "duplicate_paper_label" for error in report["errors"]))

    def test_multiple_formula_owners_are_rejected(self):
        document = copy.deepcopy(self.valid)
        duplicate = copy.deepcopy(document["formula_placements"][0])
        duplicate["owner_section_id"] = "SEC-DEMO-RESULTS"
        duplicate["label"] = "eq:demo-total-cost-copy"
        document["formula_placements"].append(duplicate)
        report = self.validate(document)
        self.assertTrue(any(error["code"] == "multiple_formula_owners" for error in report["errors"]))

    def test_unknown_owner_section_is_rejected(self):
        document = copy.deepcopy(self.valid)
        document["model_placements"][0]["owner_section_id"] = "SEC-UNKNOWN"
        report = self.validate(document)
        self.assertTrue(any(error["code"] == "unknown_owner_section" for error in report["errors"]))

    def test_frozen_blueprint_cannot_keep_pending_checkpoint(self):
        document = copy.deepcopy(self.valid)
        document["status"] = "frozen"
        report = self.validate(document)
        self.assertTrue(any(error["code"] == "pending_blueprint_checkpoint" for error in report["errors"]))

    def test_writing_drift_flags_are_schema_constants(self):
        document = copy.deepcopy(self.valid)
        document["writing_constraints"]["recomputation_forbidden"] = False
        report = self.validate(document)
        self.assertTrue(any(error["code"] == "schema_violation" for error in report["errors"]))

    def test_unplaced_formula_is_detected_against_source_spec(self):
        document = copy.deepcopy(self.valid)
        document["formula_placements"] = []
        report = self.validate(document, repo_root=ROOT, check_paths=True)
        self.assertTrue(any(error["code"] == "unplaced_formula" for error in report["errors"]))

    def test_claim_must_be_allowed_by_source_spec(self):
        document = copy.deepcopy(self.valid)
        document["claims"][0]["text"] = "An unsupported new claim."
        report = self.validate(document, repo_root=ROOT, check_paths=True)
        self.assertTrue(any(error["code"] == "claim_not_allowed_by_model_spec" for error in report["errors"]))


if __name__ == "__main__":
    unittest.main()
