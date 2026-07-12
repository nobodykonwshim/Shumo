import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "skills"
    / "math_modeling"
    / "evaluators"
    / "route_feasibility.py"
)
spec = importlib.util.spec_from_file_location("route_feasibility", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class RouteFeasibilityTests(unittest.TestCase):
    def test_two_point_straight_line_passes(self):
        plan = {
            "candidate_id": "P4-CAND-A",
            "route_family": "straight",
            "lines": [{"id": "A-001", "points": [[0, 0], [0, 100]]}],
        }
        report = module.validate_plan(plan)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["results"]["hard_corner_count"], 0)

    def test_piecewise_linear_bend_fails_exact_curvature(self):
        plan = {
            "candidate_id": "P4-CAND-C",
            "route_family": "curved_polyline",
            "lines": [{"id": "C-001", "points": [[0, 0], [1, 1], [1, 2]]}],
        }
        report = module.validate_plan(plan)
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["results"]["hard_corner_count"], 1)
        self.assertIn(
            "nonzero_heading_change_at_polyline_vertices_requires_unbounded_curvature",
            report["reasons"],
        )
        self.assertEqual(
            report["decision"]["fallback_candidate_on_fail"], "P4-CAND-A"
        )

    def test_collinear_multi_point_line_passes(self):
        plan = {
            "candidate_id": "P4-CAND-X",
            "lines": [{"id": "X", "points": [[0, 0], [0, 1], [0, 2]]}],
        }
        report = module.validate_plan(plan)
        self.assertEqual(report["status"], "pass")

    def test_minimum_radius_can_fail_diagnostic_threshold(self):
        plan = {
            "candidate_id": "P4-CAND-C",
            "lines": [{"id": "C", "points": [[1, 0], [0, 1], [-1, 0]]}],
        }
        report = module.validate_plan(plan, minimum_turn_radius_m=2.0)
        self.assertEqual(report["status"], "fail")
        self.assertAlmostEqual(
            report["results"]["minimum_three_point_circumradius_m"], 1.0
        )
        self.assertIn(
            "sampled_circumradius_below_frozen_minimum_turn_radius",
            report["reasons"],
        )

    def test_duplicate_point_is_rejected(self):
        plan = {
            "candidate_id": "bad",
            "lines": [{"id": "bad", "points": [[0, 0], [0, 0]]}],
        }
        with self.assertRaisesRegex(ValueError, "distinct"):
            module.validate_plan(plan)


if __name__ == "__main__":
    unittest.main()
