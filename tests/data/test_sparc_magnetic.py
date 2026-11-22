from __future__ import annotations

import csv
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data-pipeline"))
from sparc_magnetic import SPARCError, preprocess  # noqa: E402


def _record(flight: int, line: int, x: float | None, y: float | None, order: int,
            *, magml: float | None, date: str = "2003/01/04") -> str:
    values = [str(line), str(flight), "*", "*", "*", "*", "*", date, "*",
              "*", "*", "*", "*", "*", "*", "*", "*", "*", "*", "*", "*"]
    if x is None or y is None:
        return " ".join(values)
    values[2:7] = [f"{-65 + x / 100000:.6f}", f"{-71 + y / 100000:.6f}",
                   f"{x:.3f}", f"{y:.3f}", "2799.0"]
    values[8] = f"16:24:{order:02d}.00"
    values[9:21] = ["45130.0", "*", "*", "45180.0", "-50.0", "*", "-50.0", "*", "*",
                    f"{-50.0 + order * .1:.1f}", f"{-50.0 + order * .1:.1f}",
                    "*" if magml is None else f"{magml:.1f}"]
    return " ".join(values)


def _fixture(path: Path) -> None:
    rows = ["/ fixture in BAS 21-column XYZ layout"]
    for flight in range(1, 7):
        line = flight * 10
        rows.append(f"Line {line}")
        rows.append(_record(flight, line, None, None, 0, magml=None))
        for i in range(3):
            rows.append(_record(flight, line, 1000.0 * i, 5000.0 * flight,
                                i + 1, magml=-20.0 + i))
        if flight == 1:
            partial = _record(1, 10, 1000.0, 5000.0, 2, magml=-19.0).split()
            partial[4] = partial[5] = "*"
            rows.append(" ".join(partial))
    for flight in range(7, 10):
        line = flight * 10
        rows.append(f"Tie {line}")
        rows.append(_record(flight, line, None, None, 0, magml=None))
        for i in range(3):
            rows.append(_record(flight, line, 5000.0 * flight, 1000.0 * i,
                                i + 1, magml=None))
    path.write_text("\n".join(rows) + "\n", encoding="ascii")


def test_pinned_source_preprocessor_preserves_inventory_and_separates_channel_inputs(tmp_path):
    raw = tmp_path / "SPARC_Mag.XYZ"
    _fixture(raw)
    output = tmp_path / "processed"

    manifest = preprocess(raw, output, verify_pin=False)

    assert manifest["schema"] == "bas-sparc-magnetic-preprocess/v1"
    assert manifest["counts"]["numeric_records"] == 37
    assert manifest["counts"]["line_headers"] == 9
    assert manifest["counts"]["coordinate_complete"] == 27
    assert manifest["counts"]["coordinate_incomplete"] == 1
    assert manifest["counts"]["MagML_tie_rows"] == 0
    assert manifest["geometry_classification"]["flight_line_count"] == 6
    assert manifest["geometry_classification"]["tie_line_count"] == 3
    assert manifest["counts"]["magl_processing_rows"] == 27
    assert manifest["counts"]["magml_processing_rows"] == 18
    assert manifest["counts"]["magl_common_profile_rows"] == 18
    with (output / "inventory.csv").open(encoding="utf-8", newline="") as stream:
        inventory = list(csv.DictReader(stream))
    assert len(inventory) == 37
    assert inventory[0]["record_kind"] == "line_header"
    assert inventory[1]["raw_record"].startswith("10 1 ")
    assert sum(row["record_kind"] == "incomplete_observation" for row in inventory) == 1
    with (output / "magml-flight-profiles.csv").open(encoding="utf-8", newline="") as stream:
        processed = list(csv.DictReader(stream))
    assert all(row["line_role"] == "flight" for row in processed)
    assert all(row["source_marker_type"] == "Line" for row in processed)
    assert all(row["source_record_index"] for row in processed)
    with (output / "magl-common-profile-rows.csv").open(encoding="utf-8", newline="") as stream:
        paired = list(csv.DictReader(stream))
    assert len(paired) == len(processed)
    assert [row["source_record_index"] for row in paired] == [row["source_record_index"] for row in processed]
    assert all(row["comparison_MagML_nT"] for row in paired)
    assert json.loads((output / "manifest.json").read_text(encoding="utf-8")) == manifest


def test_default_mode_rejects_unpinned_source_without_creating_output(tmp_path):
    raw = tmp_path / "SPARC_Mag.XYZ"
    _fixture(raw)
    output = tmp_path / "processed"
    with pytest.raises(SPARCError, match="pinned BAS SPARC object"):
        preprocess(raw, output)
    assert not output.exists()


def test_parser_rejects_wrong_column_count_before_installing_partial_outputs(tmp_path):
    raw = tmp_path / "bad.XYZ"
    raw.write_text("12 5 -69 -71\n", encoding="ascii")
    output = tmp_path / "processed"
    with pytest.raises(SPARCError, match="expected 21 fields"):
        preprocess(raw, output, verify_pin=False)
    assert not output.exists()


def test_outputs_are_never_overwritten(tmp_path):
    raw = tmp_path / "SPARC_Mag.XYZ"
    _fixture(raw)
    output = tmp_path / "processed"
    output.mkdir()
    (output / "sentinel").write_text("keep", encoding="utf-8")
    with pytest.raises(SPARCError, match="refusing to replace"):
        preprocess(raw, output, verify_pin=False)
    assert (output / "sentinel").read_text(encoding="utf-8") == "keep"
