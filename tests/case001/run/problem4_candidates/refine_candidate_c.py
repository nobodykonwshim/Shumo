#!/usr/bin/env python3
"""Generate explicit finite-curvature variants of candidate C."""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from skills.math_modeling.geometry.route_geometry import (
    minimum_adjacent_separation,
    sample_geometry,
    smooth_polyline_quadratic,
    validate_explicit_geometry,
)


def parse_fractions(text: str) -> list[float]:
    values = [float(value.strip()) for value in text.split(",") if value.strip()]
    if not values:
        raise ValueError("At least one trim fraction is required")
    if len(values) != len(set(values)):
        raise ValueError("Trim fractions must be unique")
    return values


def variant_id(fraction: float) -> str:
    return f"P4-CAND-C-SMOOTH-{round(fraction * 100):02d}"


def build_variant(
    source: dict,
    *,
    trim_fraction: float,
    curve_subdivisions: int,
    crossing_y_samples: int,
    terrain_file_in_config: str,
) -> dict:
    variant = copy.deepcopy(source)
    variant["candidate_id"] = variant_id(trim_fraction)
    variant["parent_candidate_id"] = source.get("candidate_id")
    variant["route_family"] = "terrain_responsive_quadratic_bezier_north_south"
    variant["terrain_file"] = terrain_file_in_config
    variant["smoothing"] = {
        "method": "tangent_continuous_quadratic_bezier_corner_fillet",
        "trim_fraction": trim_fraction,
        "curve_subdivisions_for_spatial_evaluation": curve_subdivisions,
        "implicit_smoothing": False,
    }
    line_geometries = []
    exact_total = 0.0
    minimum_radius = None
    for line in variant["lines"]:
        geometry = smooth_polyline_quadratic(
            line["points"], trim_fraction=trim_fraction
        )
        report = validate_explicit_geometry(geometry)
        line["source_polyline_points"] = line["points"]
        line["geometry_segments"] = geometry
        line["points"] = sample_geometry(
            geometry, curve_subdivisions=curve_subdivisions
        )
        line["exact_geometry_length_m"] = report["length_m"]
        line["minimum_curvature_radius_m"] = report[
            "minimum_curvature_radius_m"
        ]
        exact_total += report["length_m"]
        if report["minimum_curvature_radius_m"] is not None:
            minimum_radius = (
                report["minimum_curvature_radius_m"]
                if minimum_radius is None
                else min(minimum_radius, report["minimum_curvature_radius_m"])
            )
        line_geometries.append(geometry)

    region = variant["region"]
    separation = minimum_adjacent_separation(
        line_geometries,
        ymin=float(region["ymin"]),
        ymax=float(region["ymax"]),
        samples=crossing_y_samples,
    )
    variant["refinement_diagnostics"] = {
        "exact_total_survey_line_length_m": exact_total,
        "minimum_curvature_radius_m": minimum_radius,
        "hard_corner_count": 0,
        "adjacent_line_crossing_check": separation,
    }
    variant["expected_tradeoffs"] = list(variant.get("expected_tradeoffs", [])) + [
        "Removes exact-polyline hard corners while preserving the terrain-responsive line family.",
        "Each variant must be independently re-evaluated because smoothing changes coverage and overlap geometry.",
    ]
    variant["limitations"] = [
        "No vessel-specific minimum turn radius is assumed; minimum curvature radius is reported diagnostically.",
        "Inter-line connecting turns remain outside the reported survey-line objective.",
        "Noncrossing is checked on a deterministic y-grid and is not a symbolic proof.",
        "No global optimality claim is made.",
    ]
    return variant


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--trim-fractions", default="0.05,0.10,0.20,0.30,0.40")
    parser.add_argument("--curve-subdivisions", type=int, default=4)
    parser.add_argument("--crossing-y-samples", type=int, default=401)
    parser.add_argument(
        "--terrain-file-in-config",
        default="../../../../local/generated/attachment_terrain.json",
    )
    args = parser.parse_args()

    source = json.loads(args.source.read_text(encoding="utf-8"))
    if source.get("candidate_id") != "P4-CAND-C":
        raise ValueError("Source must be the original P4-CAND-C candidate")
    fractions = parse_fractions(args.trim_fractions)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "schema_version": 1,
        "source_candidate_id": source["candidate_id"],
        "objective": "minimum exact total survey-line length subject to feasibility and spatial constraints",
        "variants": [],
    }
    for fraction in fractions:
        variant = build_variant(
            source,
            trim_fraction=fraction,
            curve_subdivisions=args.curve_subdivisions,
            crossing_y_samples=args.crossing_y_samples,
            terrain_file_in_config=args.terrain_file_in_config,
        )
        path = args.output_dir / f"{variant['candidate_id']}.json"
        path.write_text(
            json.dumps(variant, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        diagnostics = variant["refinement_diagnostics"]
        manifest["variants"].append(
            {
                "candidate_id": variant["candidate_id"],
                "trim_fraction": fraction,
                "path": str(path),
                "exact_total_survey_line_length_m": diagnostics[
                    "exact_total_survey_line_length_m"
                ],
                "minimum_curvature_radius_m": diagnostics[
                    "minimum_curvature_radius_m"
                ],
                "crossing_count": diagnostics["adjacent_line_crossing_check"][
                    "crossing_count"
                ],
                "minimum_adjacent_separation_m": diagnostics[
                    "adjacent_line_crossing_check"
                ]["minimum_separation_m"],
            }
        )
    (args.output_dir / "refinement_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
