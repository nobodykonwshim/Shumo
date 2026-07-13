#!/usr/bin/env python3
"""Run feasibility and spatial evaluation for refined candidate-C variants."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def run(command: list[str], *, allowed_codes: set[int] = {0}) -> int:
    completed = subprocess.run(command, check=False)
    if completed.returncode not in allowed_codes:
        raise RuntimeError(
            f"Command failed with exit code {completed.returncode}: {' '.join(command)}"
        )
    return completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variants-dir", required=True, type=Path)
    parser.add_argument("--spatial-evaluator", required=True, type=Path)
    parser.add_argument("--feasibility-validator", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--candidate-a-length-m", type=float, default=620420.0)
    args = parser.parse_args()

    variants = sorted(args.variants_dir.glob("P4-CAND-C-SMOOTH-*.json"))
    if not variants:
        raise ValueError("No refined candidate-C variants were found")

    records = []
    for candidate_path in variants:
        stem = candidate_path.stem
        feasibility_path = args.variants_dir / f"{stem}_feasibility.json"
        spatial_path = args.variants_dir / f"{stem}_spatial.json"
        run(
            [
                sys.executable,
                str(args.feasibility_validator),
                "--candidate",
                str(candidate_path),
                "--output",
                str(feasibility_path),
            ],
            allowed_codes={0, 2},
        )
        run(
            [
                sys.executable,
                str(args.spatial_evaluator),
                "--config",
                str(candidate_path),
                "--output",
                str(spatial_path),
            ]
        )
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        feasibility = json.loads(feasibility_path.read_text(encoding="utf-8"))
        spatial = json.loads(spatial_path.read_text(encoding="utf-8"))
        spatial_results = spatial["results"]
        diagnostics = candidate["refinement_diagnostics"]
        crossing_count = diagnostics["adjacent_line_crossing_check"]["crossing_count"]
        feasible = (
            feasibility["status"] == "pass"
            and crossing_count == 0
            and spatial_results["uncovered_area_percent"] == 0.0
            and spatial_results["boundary_violation"] is False
        )
        exact_length = feasibility["results"]["total_length_m"]
        records.append(
            {
                "candidate_id": candidate["candidate_id"],
                "trim_fraction": candidate["smoothing"]["trim_fraction"],
                "feasible": feasible,
                "feasibility_status": feasibility["status"],
                "hard_corner_count": feasibility["results"]["hard_corner_count"],
                "minimum_curvature_radius_m": feasibility["results"][
                    "minimum_curvature_radius_m"
                ],
                "crossing_count": crossing_count,
                "minimum_adjacent_separation_m": diagnostics[
                    "adjacent_line_crossing_check"
                ]["minimum_separation_m"],
                "exact_total_survey_line_length_m": exact_length,
                "spatial_sampled_total_length_m": spatial_results[
                    "total_survey_line_length_m"
                ],
                "uncovered_area_percent": spatial_results["uncovered_area_percent"],
                "excess_overlap_length_m": spatial_results[
                    "excess_overlap_length_m"
                ],
                "boundary_violation": spatial_results["boundary_violation"],
                "length_below_candidate_a": exact_length < args.candidate_a_length_m,
                "candidate_path": str(candidate_path),
                "feasibility_report": str(feasibility_path),
                "spatial_report": str(spatial_path),
            }
        )

    feasible_records = [record for record in records if record["feasible"]]
    best = (
        min(feasible_records, key=lambda record: record["exact_total_survey_line_length_m"])
        if feasible_records
        else None
    )
    summary = {
        "schema_version": 1,
        "objective": "minimum exact total survey-line length subject to tangent continuity, finite curvature, noncrossing, zero sampled uncovered area and no boundary violation",
        "candidate_a_reference_length_m": args.candidate_a_length_m,
        "variants": records,
        "best_feasible_refined_c": best,
        "human_gate_required": True,
        "final_selection_made": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if best is not None else 2


if __name__ == "__main__":
    raise SystemExit(main())
