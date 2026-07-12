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
            "nonzero_heading_change_requires_unbounded_curvature",
            report["reasons"],
        )

    def test_explicit_quadratic_geometry_passes_even_with_sampled_points(self):
        plan = {
            "candidate_id": "P4-CAND-C-SMOOTH-20",
            "route_family": "quadratic",
            "lines": [
                {
                    "id": "C-001",
                    "points": [[0, 0], [0, 8], [1, 9], [2, 10], [10, 10]],
                    "geometry_segments": [
                        {"type": "line", "p0": [0, 0], "p1": [0, 8]},
                        {
                            "type": "quadratic_bezier",
                            "p0": [0, 8],
                            "p1": [0, 10],
                            "p2": [2, 10],
                        },
                        {"type": "line", "p0": [2, 10], "p1": [10, 10]},
                    ],
                }
            ],
        }
        report = module.validate_plan(plan)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["results"]["hard_corner_count"], 0)
        self.assertGreater(report["results"]["minimum_curvature_radius_m"], 0)

    def test_minimum_radius_can_reject_explicit_curve(self):
        plan = {
            "candidate_id": "curve",
            "lines": [
                {
                    "id": "curve",
                    "geometry_segments": [
                        {
                            "type": "quadratic_bezier",
                            "p0": [0, 0],
                            "p1": [0, 1],
                            "p2": [1, 1],
                        }
                    ],
                }
            ],
        }
        diagnostic = module.validate_plan(plan)
        radius = diagnostic["results"]["minimum_curvature_radius_m"]
        report = module.validate_plan(plan, minimum_turn_radius_m=radius + 1.0)
        self.assertEqual(report["status"], "fail")
        self.assertIn(
            "minimum_curvature_radius_below_frozen_turn_radius", report["reasons"]
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
