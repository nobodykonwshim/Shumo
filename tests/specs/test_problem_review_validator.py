import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "skills" / "math_modeling" / "validation" / "problem_review_validator.py"
SCHEMA_PATH = ROOT / "skills" / "math_modeling" / "specs" / "problem_review.schema.json"

spec = importlib.util.spec_from_file_location("problem_review_validator", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class ProblemReviewValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    def fixture(self, root: Path, *, problem_id="problem1", sequence_index=1, status="pending"):
        project = {
            "project": {"id": "demo_project"},
            "question_delivery": {
                "mode": "sequential_review",
                "problem_order": ["problem1", "problem2"],
            },
        }
        (root / "demo").mkdir(exist_ok=True)
        (root / "demo" / "project.yaml").write_text(
            yaml.safe_dump(project, sort_keys=False), encoding="utf-8"
        )
        artifact_path = root / "demo" / f"{problem_id}.tex"
        artifact_path.write_text("reviewed artifact\n", encoding="utf-8")
        digest = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        return {
            "schema_version": "1.0",
            "review_id": f"REVIEW-{problem_id}",
            "project_id": "demo_project",
            "project_config_path": "demo/project.yaml",
            "problem_id": problem_id,
            "sequence_index": sequence_index,
            "previous_review_path": None,
            "artifacts": [
                {
                    "id": f"ART-{problem_id}",
                    "role": "latex_section",
                    "path": f"demo/{problem_id}.tex",
                    "sha256": digest,
                }
            ],
            "review": {
                "revision": 1,
                "status": status,
                "authority": "user",
                "feedback": [],
                "reviewed_at": None,
            },
            "next_problem_id": "problem2" if sequence_index == 1 else None,
            "notes": [],
        }

    def validate(self, review, root):
        return module.validate_review(review, self.schema, repo_root=root)

    def test_pending_review_blocks_next_problem(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = self.validate(self.fixture(root), root)
        self.assertEqual(report["validation_status"], "pass")
        self.assertFalse(report["advance_allowed"])

    def test_changes_requested_blocks_next_problem(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = self.validate(self.fixture(root, status="changes_requested"), root)
        self.assertEqual(report["validation_status"], "pass")
        self.assertFalse(report["advance_allowed"])

    def test_approved_first_problem_opens_gate(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = self.validate(self.fixture(root, status="approved"), root)
        self.assertEqual(report["validation_status"], "pass")
        self.assertTrue(report["advance_allowed"])

    def test_later_problem_requires_approved_previous_review(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            review = self.fixture(root, problem_id="problem2", sequence_index=2, status="approved")
            previous = self.fixture(root, problem_id="problem1", sequence_index=1, status="pending")
            previous_path = root / "demo" / "problem1.review.yaml"
            previous_path.write_text(yaml.safe_dump(previous, sort_keys=False), encoding="utf-8")
            review["previous_review_path"] = "demo/problem1.review.yaml"
            report = self.validate(review, root)
        self.assertEqual(report["validation_status"], "fail")
        self.assertFalse(report["advance_allowed"])
        self.assertTrue(any(item["code"] == "previous_review_not_approved" for item in report["errors"]))

    def test_hash_change_invalidates_approval(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            review = self.fixture(root, status="approved")
            (root / "demo" / "problem1.tex").write_text("changed\n", encoding="utf-8")
            report = self.validate(review, root)
        self.assertEqual(report["validation_status"], "fail")
        self.assertFalse(report["advance_allowed"])
        self.assertTrue(report["stale_artifacts"])


if __name__ == "__main__":
    unittest.main()
