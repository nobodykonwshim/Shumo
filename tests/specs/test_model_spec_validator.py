import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "skills" / "math_modeling" / "validation" / "model_spec_validator.py"
SCHEMA_PATH = ROOT / "skills" / "math_modeling" / "specs" / "model_spec.schema.json"
EXAMPLE_PATH = ROOT / "skills" / "math_modeling" / "specs" / "model_spec.example.yaml"

spec = importlib.util.spec_from_file_location("model_spec_validator", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class ModelSpecValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.valid = yaml.safe_load(EXAMPLE_PATH.read_text(encoding="utf-8"))

    def validate(self, document, **kwargs):
        return module.validate_model_spec(document, self.schema, **kwargs)

    def test_generic_example_passes(self):
        report = self.validate(copy.deepcopy(self.valid))
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["error_count"], 0)

    def test_missing_required_section_fails_schema(self):
        document = copy.deepcopy(self.valid)
        del document["objective"]
        report = self.validate(document)
        self.assertEqual(report["status"], "fail")
        self.assertTrue(any(error["code"] == "schema_violation" for error in report["errors"]))

    def test_duplicate_semantic_id_is_rejected(self):
        document = copy.deepcopy(self.valid)
        document["outputs"][0]["id"] = document["constraints"][0]["id"]
        report = self.validate(document)
        self.assertTrue(any(error["code"] == "duplicate_id" for error in report["errors"]))

    def test_unresolved_reference_is_rejected(self):
        document = copy.deepcopy(self.valid)
        document["validation"]["checks"][0]["target_ids"].append("UNKNOWN-ID")
        report = self.validate(document)
        self.assertTrue(any(error["code"] == "unresolved_reference" for error in report["errors"]))

    def test_nondeterministic_algorithm_requires_randomness_contract(self):
        document = copy.deepcopy(self.valid)
        document["algorithm"]["deterministic"] = False
        report = self.validate(document)
        self.assertTrue(any(error["code"] == "missing_randomness_contract" for error in report["errors"]))

    def test_solved_status_requires_required_checks_to_pass(self):
        document = copy.deepcopy(self.valid)
        document["status"] = "solved"
        document["human_checkpoints"][0]["status"] = "approved"
        report = self.validate(document)
        self.assertTrue(any(error["code"] == "unsatisfied_required_validation" for error in report["errors"]))

    def test_repository_path_check_detects_missing_file(self):
        document = copy.deepcopy(self.valid)
        document["provenance"]["source_artifacts"] = [
            {
                "id": "SRC-REPOSITORY-MISSING",
                "location": "missing/input.csv",
                "availability": "repository",
                "role": "authoritative_input",
            }
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            report = self.validate(document, repo_root=Path(temp_dir), check_paths=True)
        self.assertTrue(any(error["code"] == "missing_repository_path" for error in report["errors"]))

    def test_repository_path_check_accepts_existing_file(self):
        document = copy.deepcopy(self.valid)
        document["provenance"]["source_artifacts"] = [
            {
                "id": "SRC-REPOSITORY-EXISTING",
                "location": "fixtures/input.csv",
                "availability": "repository",
                "role": "authoritative_input",
            }
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = root / "fixtures" / "input.csv"
            path.parent.mkdir(parents=True)
            path.write_text("value\n1\n", encoding="utf-8")
            report = self.validate(document, repo_root=root, check_paths=True)
        self.assertEqual(report["status"], "pass")


if __name__ == "__main__":
    unittest.main()
