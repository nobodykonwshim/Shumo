#!/usr/bin/env python3
"""Resolve the conditional problem-4 selection using exact candidate geometry."""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


def load_validator(module_path: Path):
    spec = importlib.util.spec_from_file_location("case001_route_feasibility", module_path)
    if not spec or not spec.loader:
        raise RuntimeError(f"Cannot load feasibility validator: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve(
    validator,
    primary_plan: dict[str, Any],
    fallback_plan: dict[str, Any],
    *,
    heading_tolerance_deg: float = 1e-6,
    minimum_turn_radius_m: float | None = None,
) -> dict[str, Any]:
    primary_report = validator.validate_plan(
        primary_plan,
        heading_tolerance_deg=heading_tolerance_deg,
        minimum_turn_radius_m=minimum_turn_radius_m,
    )

    fallback_report = None
    if primary_report["status"] == "pass":
        selected = str(primary_plan.get("candidate_id"))
        resolution = "primary_retained"
    else:
        fallback_report = validator.validate_plan(
            fallback_plan,
            heading_tolerance_deg=heading_tolerance_deg,
            minimum_turn_radius_m=minimum_turn_radius_m,
        )
        if fallback_report["status"] != "pass":
            raise RuntimeError("Primary failed and fallback route is not feasible")
        selected = str(fallback_plan.get("candidate_id"))
        resolution = "fallback_selected"

    return {
        "schema_version": 1,
        "case_id": "case001",
        "problem_id": "problem4",
        "stage": "H3_candidate_feasibility_resolution",
        "status": "resolved",
        "conditional_primary": str(primary_plan.get("candidate_id")),
        "fallback_candidate": str(fallback_plan.get("candidate_id")),
        "selected_candidate": selected,
        "resolution": resolution,
        "criteria": {
            "exact_polyline_requires_c1_continuity": True,
            "heading_tolerance_deg": heading_tolerance_deg,
            "minimum_turn_radius_m": minimum_turn_radius_m,
            "inter_line_connector_policy": (
                "not_part_of_reported_survey_line_length; no vessel-specific boundary or "
                "turning-radius constraint is supplied by the problem"
            ),
        },
        "primary_feasibility": primary_report,
        "fallback_feasibility": fallback_report,
        "claims": {
            "global_optimality": False,
            "reported_feasibility_scope": "within_each_reported_survey_line",
            "implicit_smoothing_used": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validator", required=True, type=Path)
    parser.add_argument("--primary", required=True, type=Path)
    parser.add_argument("--fallback", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--heading-tolerance-deg", type=float, default=1e-6)
    parser.add_argument("--minimum-turn-radius-m", type=float)
    args = parser.parse_args()

    validator = load_validator(args.validator)
    report = resolve(
        validator,
        read_json(args.primary),
        read_json(args.fallback),
        heading_tolerance_deg=args.heading_tolerance_deg,
        minimum_turn_radius_m=args.minimum_turn_radius_m,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(report["selected_candidate"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
