from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "skills" / "math_modeling" / "evaluators" / "xlsx_depth_grid.py"
spec = importlib.util.spec_from_file_location("xlsx_depth_grid", MODULE_PATH)
assert spec and spec.loader
adapter = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = adapter
spec.loader.exec_module(adapter)


def _cell(reference: str, value, inline: bool = False) -> str:
    if inline:
        return f'<c r="{reference}" t="inlineStr"><is><t>{value}</t></is></c>'
    return f'<c r="{reference}"><v>{value}</v></c>'


def write_fixture(path: Path, missing_depth: bool = False) -> None:
    rows = [
        '<row r="1">'
        + _cell("A1", "海水深度/m", True)
        + _cell("C1", "横向坐标/NM（由西向东）", True)
        + "</row>",
        '<row r="2">' + _cell("C2", 0) + _cell("D2", 0.02) + _cell("E2", 0.04) + "</row>",
        '<row r="3">'
        + _cell("A3", "纵向坐标/NM（由南向北）", True)
        + _cell("B3", 0)
        + _cell("C3", 10)
        + _cell("D3", 11)
        + ("" if missing_depth else _cell("E3", 12))
        + "</row>",
        '<row r="4">'
        + _cell("B4", 0.02)
        + _cell("C4", 20)
        + _cell("D4", 21)
        + _cell("E4", 22)
        + "</row>",
    ]
    worksheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetData>' + "".join(rows) + "</sheetData></worksheet>"
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    relationships = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/></Relationships>'
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '</Types>'
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/></Relationships>'
    )
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", relationships)
        archive.writestr("xl/worksheets/sheet1.xml", worksheet)


class XlsxDepthGridAdapterTests(unittest.TestCase):
    def test_extracts_and_converts_regular_grid(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixture.xlsx"
            write_fixture(path)
            bundle, profile = adapter.extract_grid(path)
            self.assertEqual(profile.x_count, 3)
            self.assertEqual(profile.y_count, 2)
            self.assertAlmostEqual(bundle["terrain"]["x"][-1], 0.04 * 1852)
            self.assertAlmostEqual(bundle["terrain"]["y"][-1], 0.02 * 1852)
            self.assertEqual(bundle["terrain"]["depth"], [[10.0, 11.0, 12.0], [20.0, 21.0, 22.0]])
            self.assertFalse(bundle["independence_contract"]["terrain_fitting"])

    def test_missing_depth_cell_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixture.xlsx"
            write_fixture(path, missing_depth=True)
            with self.assertRaises(adapter.AdapterError):
                adapter.extract_grid(path)

    def test_cli_writes_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "fixture.xlsx"
            output = root / "terrain.json"
            write_fixture(source)
            self.assertEqual(
                adapter.main(["--input", str(source), "--output", str(output)]), 0
            )
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(data["profile"]["missing_depth_cells"], 0)
            self.assertEqual(data["region"]["unit"], "m")


if __name__ == "__main__":
    unittest.main()
