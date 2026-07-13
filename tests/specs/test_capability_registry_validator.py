import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "skills" / "math_modeling" / "validation" / "capability_registry_validator.py"
SCHEMA_PATH = ROOT / "skills" / "math_modeling" / "specs" / "capability_registry.schema.json"

spec = importlib.util.spec_from_file_location("capability_registry_validator", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class CapabilityRegistryValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.base = {
            "schema_version": 1,
            "registry_id": "demo_registry",
            "product_boundary": "reusable_skill",
            "case_studies_are": "fixtures",
            "status_values": ["planned", "prototype", "validated", "reusable", "deprecated"],
            "capabilities": [
                {
                    "capability_id": "demo_capability",
                    "name": "Demo capability",
                    "status": "validated",
                    "owner_path": "skills/math_modeling/demo.md",
                    "contract": {"inputs": "demo_input", "outputs": "demo_output"},
                    "generic_tests": ["tests/specs/test_demo.py"],
                    "demonstrated_by": ["tests/case_demo/"],
                    "limits": ["demo limit"],
                }
            ],
            "backlog": [
                {"capability_id": "future_capability", "priority": "medium", "reason": "future work"}
            ],
        }

    def validate(self, registry, **kwargs):
        return module.validate_registry(registry, self.schema, **kwargs)

    def test_valid_registry_passes_without_path_check(self):
        report = self.validate(copy.deepcopy(self.base))
        self.assertEqual(report["status"], "pass")

    def test_duplicate_capability_id_fails(self):
        registry = copy.deepcopy(self.base)
        registry["capabilities"].append(copy.deepcopy(registry["capabilities"][0]))
        report = self.validate(registry)
        self.assertTrue(any(error["code"] == "duplicate_capability_id" for error in report["errors"]))

    def test_active_capability_cannot_remain_in_backlog(self):
        registry = copy.deepcopy(self.base)
        registry["backlog"][0]["capability_id"] = "demo_capability"
        report = self.validate(registry)
        self.assertTrue(any(error["code"] == "active_capability_still_in_backlog" for error in report["errors"]))

    def test_owner_must_be_inside_skill(self):
        registry = copy.deepcopy(self.base)
        registry["capabilities"][0]["owner_path"] = "tests/case_demo/owner.md"
        report = self.validate(registry)
        self.assertTrue(any(error["code"] == "owner_outside_skill" for error in report["errors"]))

    def test_missing_generic_test_is_warning_not_failure(self):
        registry = copy.deepcopy(self.base)
        registry["capabilities"][0]["generic_tests"] = []
        report = self.validate(registry)
        self.assertEqual(report["status"], "pass")
        self.assertTrue(any(warning["code"] == "missing_generic_test" for warning in report["warnings"]))

    def test_path_check_accepts_complete_registry(self):
        registry = copy.deepcopy(self.base)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for relative in ["skills/math_modeling/demo.md", "tests/specs/test_demo.py"]:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("ok\n", encoding="utf-8")
            (root / "tests/case_demo").mkdir(parents=True)
            report = self.validate(registry, repo_root=root, check_paths=True)
        self.assertEqual(report["status"], "pass")

    def test_path_check_detects_missing_evidence(self):
        registry = copy.deepcopy(self.base)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            owner = root / "skills/math_modeling/demo.md"
            owner.parent.mkdir(parents=True)
            owner.write_text("ok\n", encoding="utf-8")
            report = self.validate(registry, repo_root=root, check_paths=True)
        self.assertTrue(any(error["code"] == "missing_registry_path" for error in report["errors"]))


if __name__ == "__main__":
    unittest.main()
