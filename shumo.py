#!/usr/bin/env python3
"""Unified command-line entry point for Shumo Skill operations."""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
PROJECT_STATUS_MODULE = ROOT / "skills" / "math_modeling" / "validation" / "project_status_calculator.py"


def _load_project_status_module():
    spec = importlib.util.spec_from_file_location("shumo_project_status_calculator", PROJECT_STATUS_MODULE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load project status calculator from {PROJECT_STATUS_MODULE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="shumo.py", description="Shumo mathematical-modeling Skill CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser(
        "validate-project",
        help="validate cross-artifact consistency and calculate project lifecycle status",
    )
    validate.add_argument("project", type=Path, help="path to a project_status.yaml record")
    validate.add_argument("--repo-root", type=Path, default=ROOT)
    validate.add_argument("--check-paths", action="store_true")
    validate.add_argument("--expect-status")
    validate.add_argument("--output", type=Path)

    args = parser.parse_args(argv)
    if args.command == "validate-project":
        module = _load_project_status_module()
        forwarded = [
            "--project", str(args.project),
            "--repo-root", str(args.repo_root),
        ]
        if args.check_paths:
            forwarded.append("--check-paths")
        if args.expect_status:
            forwarded.extend(["--expect-status", args.expect_status])
        if args.output:
            forwarded.extend(["--output", str(args.output)])
        return int(module.main(forwarded))

    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
