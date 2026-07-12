import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "skills"
    / "math_modeling"
    / "geometry"
    / "route_geometry.py"
)
spec = importlib.util.spec_from_file_location("route_geometry", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class RouteGeometryTests(unittest.TestCase):
    def test_quadratic_fillet_is_tangent_continuous_and_finite(self):
        geometry = module.smooth_polyline_quadratic(
            [[0, 0], [0, 10], [10, 10]], trim_fraction=0.2
        )
        report = module.validate_explicit_geometry(geometry)
        self.assertEqual(report["hard_corner_count"], 0)
        self.assertTrue(report["c1_continuous"])
        self.assertGreater(report["minimum_curvature_radius_m"], 0.0)
        self.assertLess(report["length_m"], 20.0)

    def test_sampling_preserves_endpoints(self):
        geometry = module.smooth_polyline_quadratic(
            [[0, 0], [0, 10], [10, 10]], trim_fraction=0.2
        )
        points = module.sample_geometry(geometry, curve_subdivisions=4)
        self.assertEqual(points[0], [0.0, 0.0])
        self.assertEqual(points[-1], [10.0, 10.0])

    def test_adjacent_smoothed_lines_remain_separated(self):
        left = module.smooth_polyline_quadratic(
            [[0, 0], [1, 5], [0, 10]], trim_fraction=0.3
        )
        right = module.smooth_polyline_quadratic(
            [[5, 0], [6, 5], [5, 10]], trim_fraction=0.3
        )
        report = module.minimum_adjacent_separation(
            [left, right], ymin=0.0, ymax=10.0, samples=101
        )
        self.assertEqual(report["crossing_count"], 0)
        self.assertGreater(report["minimum_separation_m"], 4.9)

    def test_trim_fraction_must_be_below_half(self):
        with self.assertRaisesRegex(ValueError, "trim_fraction"):
            module.smooth_polyline_quadratic(
                [[0, 0], [0, 10], [10, 10]], trim_fraction=0.5
            )


if __name__ == "__main__":
    unittest.main()
