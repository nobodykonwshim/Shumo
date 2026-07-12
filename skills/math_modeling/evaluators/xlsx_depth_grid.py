#!/usr/bin/env python3
"""Deterministically convert the CUMCM multibeam attachment workbook to grid JSON.

The adapter uses only Python's standard library. It reads the XLSX package directly,
validates the expected coordinate/depth matrix, converts nautical miles to metres,
and writes a normalized terrain bundle consumable by ``spatial_coverage.py``.

It deliberately performs no terrain fitting, smoothing, route generation or scoring.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Sequence
from zipfile import BadZipFile, ZipFile

_MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_CELL_REF = re.compile(r"^([A-Z]+)([1-9][0-9]*)$")


class AdapterError(ValueError):
    """Raised when the workbook cannot be converted safely."""


@dataclass(frozen=True)
class GridProfile:
    sheet_name: str
    x_count: int
    y_count: int
    x_min_nm: float
    x_max_nm: float
    y_min_nm: float
    y_max_nm: float
    x_step_nm: float
    y_step_nm: float
    depth_min_m: float
    depth_max_m: float
    missing_depth_cells: int


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _column_index(letters: str) -> int:
    result = 0
    for char in letters:
        result = result * 26 + (ord(char) - ord("A") + 1)
    return result


def _parse_cell_ref(reference: str) -> tuple[int, int]:
    match = _CELL_REF.match(reference)
    if not match:
        raise AdapterError(f"Invalid cell reference: {reference!r}")
    return int(match.group(2)), _column_index(match.group(1))


def _load_shared_strings(archive: ZipFile) -> list[str]:
    try:
        raw = archive.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    root = ET.fromstring(raw)
    strings: list[str] = []
    for item in root.findall(f"{{{_MAIN_NS}}}si"):
        strings.append("".join(node.text or "" for node in item.iter(f"{{{_MAIN_NS}}}t")))
    return strings


def _sheet_target(archive: ZipFile, sheet_name: str) -> str:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    relation_id: str | None = None
    for sheet in workbook.findall(f".//{{{_MAIN_NS}}}sheet"):
        if sheet.attrib.get("name") == sheet_name:
            relation_id = sheet.attrib.get(f"{{{_REL_NS}}}id")
            break
    if not relation_id:
        available = [
            sheet.attrib.get("name", "")
            for sheet in workbook.findall(f".//{{{_MAIN_NS}}}sheet")
        ]
        raise AdapterError(f"Worksheet {sheet_name!r} not found; available={available}")

    relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    target: str | None = None
    for relation in relationships.findall(f"{{{_PKG_REL_NS}}}Relationship"):
        if relation.attrib.get("Id") == relation_id:
            target = relation.attrib.get("Target")
            break
    if not target:
        raise AdapterError(f"Worksheet relationship {relation_id!r} has no target")

    normalized = PurePosixPath("xl") / PurePosixPath(target)
    parts: list[str] = []
    for part in normalized.parts:
        if part == "..":
            if not parts:
                raise AdapterError("Unsafe worksheet relationship path")
            parts.pop()
        elif part not in ("", "."):
            parts.append(part)
    return "/".join(parts)


def _read_worksheet_cells(
    archive: ZipFile, sheet_path: str, shared_strings: Sequence[str]
) -> dict[tuple[int, int], Any]:
    cells: dict[tuple[int, int], Any] = {}
    with archive.open(sheet_path) as stream:
        for _, element in ET.iterparse(stream, events=("end",)):
            if element.tag != f"{{{_MAIN_NS}}}c":
                continue
            reference = element.attrib.get("r")
            if not reference:
                element.clear()
                continue
            row, column = _parse_cell_ref(reference)
            cell_type = element.attrib.get("t")
            value_node = element.find(f"{{{_MAIN_NS}}}v")
            inline_node = element.find(f"{{{_MAIN_NS}}}is")
            value: Any = None
            if cell_type == "inlineStr" and inline_node is not None:
                value = "".join(
                    node.text or "" for node in inline_node.iter(f"{{{_MAIN_NS}}}t")
                )
            elif value_node is not None and value_node.text is not None:
                raw = value_node.text
                if cell_type == "s":
                    index = int(raw)
                    try:
                        value = shared_strings[index]
                    except IndexError as exc:
                        raise AdapterError(
                            f"Shared-string index {index} in {reference} is out of range"
                        ) from exc
                elif cell_type in ("str", "e"):
                    value = raw
                elif cell_type == "b":
                    value = raw == "1"
                else:
                    try:
                        value = float(raw)
                    except ValueError:
                        value = raw
            cells[(row, column)] = value
            element.clear()
    return cells


def _as_float(value: Any, label: str) -> float:
    if isinstance(value, bool) or value is None:
        raise AdapterError(f"{label} is missing or non-numeric")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise AdapterError(f"{label} is non-numeric: {value!r}") from exc
    if not math.isfinite(result):
        raise AdapterError(f"{label} is not finite")
    return result


def _uniform_step(values: Sequence[float], label: str, tolerance: float = 1e-8) -> float:
    if len(values) < 2:
        raise AdapterError(f"{label} requires at least two values")
    deltas = [b - a for a, b in zip(values, values[1:])]
    if any(delta <= 0 for delta in deltas):
        raise AdapterError(f"{label} must be strictly increasing")
    step = sum(deltas) / len(deltas)
    if max(abs(delta - step) for delta in deltas) > tolerance:
        raise AdapterError(f"{label} is not uniformly spaced")
    return step


def _expect_contains(value: Any, tokens: Iterable[str], label: str) -> None:
    text = "" if value is None else str(value)
    if not all(token in text for token in tokens):
        raise AdapterError(f"Unexpected {label}: {text!r}")


def extract_grid(
    workbook_path: Path,
    sheet_name: str = "Sheet1",
    nautical_mile_to_m: float = 1852.0,
) -> tuple[dict[str, Any], GridProfile]:
    if nautical_mile_to_m <= 0:
        raise AdapterError("nautical_mile_to_m must be positive")
    try:
        with ZipFile(workbook_path) as archive:
            shared_strings = _load_shared_strings(archive)
            sheet_path = _sheet_target(archive, sheet_name)
            cells = _read_worksheet_cells(archive, sheet_path, shared_strings)
    except (OSError, KeyError, BadZipFile, ET.ParseError) as exc:
        raise AdapterError(f"Cannot read XLSX workbook: {exc}") from exc

    _expect_contains(cells.get((1, 1)), ["海水深度", "m"], "A1 depth heading")
    _expect_contains(cells.get((1, 3)), ["横向坐标", "NM"], "C1 x heading")
    _expect_contains(cells.get((3, 1)), ["纵向坐标", "NM"], "A3 y heading")

    x_values_nm: list[float] = []
    column = 3
    while cells.get((2, column)) is not None:
        x_values_nm.append(_as_float(cells[(2, column)], f"x coordinate at column {column}"))
        column += 1

    y_values_nm: list[float] = []
    row = 3
    while cells.get((row, 2)) is not None:
        y_values_nm.append(_as_float(cells[(row, 2)], f"y coordinate at row {row}"))
        row += 1

    if not x_values_nm or not y_values_nm:
        raise AdapterError("No coordinate axes were found")
    x_step_nm = _uniform_step(x_values_nm, "x coordinates")
    y_step_nm = _uniform_step(y_values_nm, "y coordinates")

    depths: list[list[float]] = []
    missing = 0
    for y_index, _ in enumerate(y_values_nm, start=3):
        depth_row: list[float] = []
        for x_index, _ in enumerate(x_values_nm, start=3):
            value = cells.get((y_index, x_index))
            if value is None:
                missing += 1
                depth_row.append(float("nan"))
            else:
                depth_row.append(_as_float(value, f"depth at row {y_index}, column {x_index}"))
        depths.append(depth_row)
    if missing:
        raise AdapterError(f"Depth matrix contains {missing} missing cells")

    flat_depths = [value for depth_row in depths for value in depth_row]
    if any(value <= 0 for value in flat_depths):
        raise AdapterError("Depth values must be positive-down and strictly positive")

    x_values_m = [value * nautical_mile_to_m for value in x_values_nm]
    y_values_m = [value * nautical_mile_to_m for value in y_values_nm]
    workbook_hash = _sha256(workbook_path)

    profile = GridProfile(
        sheet_name=sheet_name,
        x_count=len(x_values_nm),
        y_count=len(y_values_nm),
        x_min_nm=x_values_nm[0],
        x_max_nm=x_values_nm[-1],
        y_min_nm=y_values_nm[0],
        y_max_nm=y_values_nm[-1],
        x_step_nm=x_step_nm,
        y_step_nm=y_step_nm,
        depth_min_m=min(flat_depths),
        depth_max_m=max(flat_depths),
        missing_depth_cells=missing,
    )

    bundle: dict[str, Any] = {
        "schema_version": 1,
        "adapter": "cumcm_multibeam_xlsx_depth_grid",
        "independence_contract": {
            "terrain_fitting": False,
            "smoothing": False,
            "route_generation": False,
            "candidate_scoring": False,
        },
        "source": {
            "filename": workbook_path.name,
            "sha256": workbook_hash,
            "sheet_name": sheet_name,
            "coordinate_unit": "nautical_mile",
            "depth_unit": "m",
            "nautical_mile_to_m": nautical_mile_to_m,
        },
        "profile": {
            "x_count": profile.x_count,
            "y_count": profile.y_count,
            "x_min_nm": profile.x_min_nm,
            "x_max_nm": profile.x_max_nm,
            "y_min_nm": profile.y_min_nm,
            "y_max_nm": profile.y_max_nm,
            "x_step_nm": profile.x_step_nm,
            "y_step_nm": profile.y_step_nm,
            "depth_min_m": profile.depth_min_m,
            "depth_max_m": profile.depth_max_m,
            "missing_depth_cells": profile.missing_depth_cells,
        },
        "region": {
            "xmin": x_values_m[0],
            "xmax": x_values_m[-1],
            "ymin": y_values_m[0],
            "ymax": y_values_m[-1],
            "unit": "m",
        },
        "terrain": {
            "type": "grid",
            "x": x_values_m,
            "y": y_values_m,
            "depth": depths,
        },
    }
    return bundle, profile


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert the CUMCM multibeam depth workbook to normalized grid JSON."
    )
    parser.add_argument("--input", required=True, type=Path, help="Input .xlsx workbook")
    parser.add_argument("--output", required=True, type=Path, help="Output terrain JSON")
    parser.add_argument("--sheet", default="Sheet1", help="Worksheet name")
    parser.add_argument(
        "--nautical-mile-to-m", type=float, default=1852.0, help="Unit conversion"
    )
    args = parser.parse_args(argv)

    try:
        bundle, _ = extract_grid(
            args.input,
            sheet_name=args.sheet,
            nautical_mile_to_m=args.nautical_mile_to_m,
        )
    except (OSError, AdapterError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "ok",
                "output": str(args.output),
                "source_sha256": bundle["source"]["sha256"],
                "x_count": bundle["profile"]["x_count"],
                "y_count": bundle["profile"]["y_count"],
                "depth_min_m": bundle["profile"]["depth_min_m"],
                "depth_max_m": bundle["profile"]["depth_max_m"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
