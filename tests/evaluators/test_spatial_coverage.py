from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "skills" / "math_modeling" / "evaluators" / "spatial_coverage.py"
spec = importlib.util.spec_from_file_location("spatial_coverage", MODULE_PATH)
assert spec and spec.loader
spatial = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = spatial
spec.loader.exec_module(spatial)


class SpatialCoverageEvaluatorTests(unittest.TestCase):
    def settings(self, **overrides):
        values = dict(
            opening_angle_deg=90.0,
            grid_nx=40,
            grid_ny=40,
            along_step_m=2.0,
            cross_track_samples=121,
            overlap_threshold=0.20,
            overlap_length_policy="ordered_previous_line",
            sensitivity_grid_sizes=(20, 40, 80),
        )
        values.update(overrides)
        return spatial.EvaluationSettings(**values)

    def test_flat_plane_complete_coverage_without_overlap(self):
        region = spatial.Region(0.0, 100.0, 0.0, 100.0)
        terrain = spatial.PlaneTerrain(25.0, 0.0, 0.0, 0.0, 0.0)
        lines = [
            spatial.SurveyLine("L1", ((25.0, 0.0), (25.0, 100.0))),
            spatial.SurveyLine("L2", ((75.0, 0.0), (75.0, 100.0))),
        ]
        result = spatial.evaluate(region, terrain, lines, self.settings())["results"]
        self.assertAlmostEqual(result["total_survey_line_length_m"], 200.0, places=9)
        self.assertAlmostEqual(result["uncovered_area_percent"], 0.0, places=9)
        self.assertAlmostEqual(result["multiply_covered_area_percent"], 0.0, places=9)
        self.assertAlmostEqual(result["excess_overlap_length_m"], 0.0, places=9)
        self.assertFalse(result["boundary_violation"])

    def test_ordered_overlap_counts_pair_once_on_later_line(self):
        region = spatial.Region(0.0, 100.0, 0.0, 100.0)
        terrain = spatial.PlaneTerrain(30.0, 0.0, 0.0, 0.0, 0.0)
        lines = [
            spatial.SurveyLine("L1", ((30.0, 0.0), (30.0, 100.0))),
            spatial.SurveyLine("L2", ((70.0, 0.0), (70.0, 100.0))),
        ]
        report = spatial.evaluate(region, terrain, lines, self.settings())
        result = report["results"]
        self.assertAlmostEqual(result["multiply_covered_area_percent"], 20.0, places=9)
        self.assertAlmostEqual(result["excess_overlap_length_by_line_m"]["L1"], 0.0)
        self.assertAlmostEqual(result["excess_overlap_length_by_line_m"]["L2"], 100.0)
        self.assertAlmostEqual(result["excess_overlap_length_m"], 100.0)
        self.assertEqual(
            report["metric_semantics"]["overlap_length_counting_policy"],
            "ordered_previous_line",
        )

    def test_legacy_per_line_policy_can_double_count(self):
        region = spatial.Region(0.0, 100.0, 0.0, 100.0)
        terrain = spatial.PlaneTerrain(30.0, 0.0, 0.0, 0.0, 0.0)
        lines = [
            spatial.SurveyLine("L1", ((30.0, 0.0), (30.0, 100.0))),
            spatial.SurveyLine("L2", ((70.0, 0.0), (70.0, 100.0))),
        ]
        result = spatial.evaluate(
            region,
            terrain,
            lines,
            self.settings(overlap_length_policy="per_line"),
        )["results"]
        self.assertAlmostEqual(result["excess_overlap_length_m"], 200.0)

    def test_boundary_violation_length_is_clipped_analytically(self):
        region = spatial.Region(0.0, 100.0, 0.0, 100.0)
        terrain = spatial.PlaneTerrain(25.0, 0.0, 0.0, 0.0, 0.0)
        lines = [spatial.SurveyLine("L1", ((50.0, -10.0), (50.0, 110.0)))]
        result = spatial.evaluate(region, terrain, lines, self.settings())["results"]
        self.assertAlmostEqual(result["total_survey_line_length_m"], 120.0, places=9)
        self.assertAlmostEqual(result["outside_region_line_length_m"], 20.0, places=9)
        self.assertTrue(result["boundary_violation"])

    def test_grid_bilinear_interpolation_and_gradient(self):
        terrain = spatial.GridTerrain(
            x=(0.0, 10.0),
            y=(0.0, 10.0),
            depth=((10.0, 20.0), (30.0, 40.0)),
        )
        depth, ddx, ddy = terrain.depth_gradient(5.0, 5.0)
        self.assertAlmostEqual(depth, 25.0, places=9)
        self.assertAlmostEqual(ddx, 1.0, places=9)
        self.assertAlmostEqual(ddy, 2.0, places=9)

    def test_sloped_plane_swath_matches_analytic_ray_intersection(self):
        terrain = spatial.PlaneTerrain(100.0, 0.0, 0.0, 0.1, 0.0)
        swath = spatial._swath_at(terrain, 0.0, 0.0, 0.0, 1.0, 90.0)
        self.assertAlmostEqual(swath.left_m, 100.0 / 0.9, places=9)
        self.assertAlmostEqual(swath.right_m, 100.0 / 1.1, places=9)

    def test_singular_beam_terrain_geometry_is_rejected(self):
        terrain = spatial.PlaneTerrain(100.0, 0.0, 0.0, 1.0, 0.0)
        with self.assertRaises(spatial.EvaluationError):
            spatial._swath_at(terrain, 0.0, 0.0, 0.0, 1.0, 90.0)

    def test_duplicate_line_ids_are_rejected(self):
        region = spatial.Region(0.0, 100.0, 0.0, 100.0)
        terrain = spatial.PlaneTerrain(25.0, 0.0, 0.0, 0.0, 0.0)
        lines = [
            spatial.SurveyLine("L", ((25.0, 0.0), (25.0, 100.0))),
            spatial.SurveyLine("L", ((75.0, 0.0), (75.0, 100.0))),
        ]
        with self.assertRaises(spatial.EvaluationError):
            spatial.evaluate(region, terrain, lines, self.settings())

    def test_cli_loads_external_terrain_bundle(self):
        valid = {
            "region": {"xmin": 0, "xmax": 100, "ymin": 0, "ymax": 100},
            "terrain_file": "terrain.json",
            "instrument": {"opening_angle_deg": 90},
            "lines": [
                {"id": "L1", "points": [[25, 0], [25, 100]]},
                {"id": "L2", "points": [[75, 0], [75, 100]]},
            ],
            "evaluation": {
                "grid_nx": 20,
                "grid_ny": 20,
                "along_step_m": 5,
                "cross_track_samples": 41,
                "sensitivity_grid_sizes": [10, 20],
                "overlap_length_policy": "ordered_previous_line",
            },
        }
        terrain_bundle = {
            "schema_version": 1,
            "terrain": {
                "type": "grid",
                "x": [0, 100],
                "y": [0, 100],
                "depth": [[25, 25], [25, 25]],
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "terrain.json").write_text(json.dumps(terrain_bundle), encoding="utf-8")
            config_path = root / "config.json"
            output_path = root / "report.json"
            config_path.write_text(json.dumps(valid), encoding="utf-8")
            self.assertEqual(
                spatial.main(["--config", str(config_path), "--output", str(output_path)]),
                0,
            )
            report = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertFalse(report["independence_contract"]["contains_route_generation"])
            self.assertEqual(report["schema_version"], 2)

    def test_cli_rejects_bad_geometry(self):
        invalid = {
            "region": {"xmin": 1, "xmax": 0, "ymin": 0, "ymax": 100},
            "terrain": {
                "type": "plane",
                "depth_at_origin": 25,
                "origin": [0, 0],
                "gradient": [0, 0],
            },
            "instrument": {"opening_angle_deg": 90},
            "lines": [{"id": "L1", "points": [[25, 0], [25, 100]]}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps(invalid), encoding="utf-8")
            self.assertEqual(spatial.main(["--config", str(path)]), 2)


if __name__ == "__main__":
    unittest.main()
