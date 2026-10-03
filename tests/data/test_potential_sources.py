"""Source intake cannot turn processed observations into fabricated raw truth."""

import csv
import hashlib
import io
import json
import os
import subprocess
import stat
import zipfile

import pytest

from potential_sources import HEADER, ROOT, extract_selected, profile_gravity, safe_target
from pathlib import PurePosixPath
from sources import SourceError, acquire_source, load_ledger


def source_archive(tmp_path, entries=None, **caps):
    payload = b"unmodified original fixture observations\n"
    entries = entries or [("data/ground.csv", payload)]
    raw = tmp_path / "original.zip"
    with zipfile.ZipFile(raw, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, value in entries:
            if isinstance(name, str):
                # ZipInfo normalizes backslashes on Windows at construction;
                # retain the hostile on-disk spelling for the negative control.
                original_name = name
                name = zipfile.ZipInfo(name)
                name.filename = name.orig_filename = original_name
                name.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(name, value)
    record = {
        "source_id": "fixture-source", "format": "research-zip", "expected_bytes": raw.stat().st_size,
        "sha256": hashlib.sha256(raw.read_bytes()).hexdigest(), "rights_decision": "mirror",
        "rights_statement": "Original test fixture", "citation": "Original fixture, not field measurements",
        "archive_contract": {"max_entries": 10, "max_expanded_bytes": 10000,
                             "max_member_bytes": 10000, "max_expansion_ratio": 1000,
                             "selected_members": {"data/ground.csv": {"bytes": len(payload),
                                                                     "sha256": hashlib.sha256(payload).hexdigest()}}, **caps},
    }
    return record, raw, payload


def test_pinned_source_identity_and_rights():
    ledger = load_ledger()
    original = ledger["bartlett-fgdc"]
    derivative = ledger["clear-lake-author-potentials-v2"]
    assert original["format"] == "fgdc-metadata-xml"
    assert original["expected_bytes"] == 37384
    assert original["sha256"] == "84d3d512f9deba53ae0251c74354c389b8723d056375390d2bfebd28c24b8295"
    assert "metadata only" in original["rights_statement"]
    assert derivative["expected_bytes"] == 121295137
    assert derivative["sha256"] == "337a2d9070493773af06aee11a19d591e6468ecf0f062dd75c194a04476c0cdf"
    assert "CC BY 4.0" in derivative["rights_statement"]
    assert "author" in derivative["citation"].lower()
    assert "16975696" in derivative["object_url"]
    assert set(derivative["archive_contract"]["selected_members"]) == {
        "data/ground_gravity_data.csv", "data/aeromagnetic_data.csv", "data/topography_data.csv", "README.pdf"}


def test_selected_members_immutable(tmp_path):
    record, raw, payload = source_archive(tmp_path)
    first = extract_selected(record, raw, root=tmp_path)
    target = tmp_path / first["members"][0]["path"]
    assert target.read_bytes() == payload
    assert first == extract_selected(record, raw, root=tmp_path)
    assert first["modified"] is False
    assert first["entry_count"] == 1
    target.write_bytes(b"changed protected content")
    with pytest.raises(SourceError, match="Existing selected bytes differ"):
        extract_selected(record, raw, root=tmp_path)
    assert target.read_bytes() == b"changed protected content"


@pytest.mark.parametrize("bad_name", ["../outside", "/outside", "C:/bad", "folder\\bad", "foo/../bar", "foo//bar",
                                      "folder/CON.csv", "folder/LPT1.txt", "folder/space /x.csv",
                                      "folder/dot./x.csv", "folder/control\x01.csv", "foo///", ".", "folder/CON .csv"])
def test_archive_path_negative_controls(tmp_path, bad_name):
    record, raw, payload = source_archive(tmp_path, [("data/ground.csv", b"x"), (bad_name, b"x")])
    with pytest.raises(SourceError, match="Unsafe"):
        extract_selected(record, raw, root=tmp_path)
    assert not (tmp_path / "data/downloads/extracted/fixture-source/data/ground.csv").exists()


def test_archive_negative_controls(tmp_path):
    for cap in ({"max_entries": 0}, {"max_expanded_bytes": 1}, {"max_member_bytes": 1}, {"max_expansion_ratio": .01}):
        record, raw, _ = source_archive(tmp_path, **cap)
        with pytest.raises(SourceError, match="limit"):
            extract_selected(record, raw, root=tmp_path)
    record, raw, _ = source_archive(tmp_path)
    record["archive_contract"]["selected_members"]["data/ground.csv"]["sha256"] = "0" * 64
    with pytest.raises(SourceError, match="byte/hash mismatch"):
        extract_selected(record, raw, root=tmp_path)
    assert not (tmp_path / "data/downloads/extracted/fixture-source/data/ground.csv").exists()
    record, raw, _ = source_archive(tmp_path)
    raw.write_bytes(b"tampered archive")
    with pytest.raises(SourceError, match="Archive byte/hash drift"):
        extract_selected(record, raw, root=tmp_path)
    symlink = zipfile.ZipInfo("link")
    symlink.create_system = 3
    symlink.external_attr = (stat.S_IFLNK | 0o777) << 16
    record, raw, _ = source_archive(tmp_path, [("data/ground.csv", b"x"), (symlink, b"../outside")])
    with pytest.raises(SourceError, match="symlink"):
        extract_selected(record, raw, root=tmp_path)
    with pytest.warns(UserWarning, match="Duplicate"):
        record, raw, _ = source_archive(tmp_path, [("data/ground.csv", b"x"), ("data/ground.csv", b"x")])
    with pytest.raises(SourceError, match="duplicate"):
        extract_selected(record, raw, root=tmp_path)


def test_profile_preserves_correction_and_missingness(tmp_path):
    path = tmp_path / "observations.csv"
    text = io.StringIO(newline="")
    writer = csv.writer(text)
    writer.writerow(HEADER)
    writer.writerow([0, "A", -123, 38, 500000, 4200000, 137, 980000, 23, 4, 2.75, 6.5, -1])
    writer.writerow([1, "A", -123, 38, 500000, 4200000, 137, 980000, "", 4, 2.75, 6.5, "NaN"])
    path.write_text(text.getvalue(), encoding="utf-8", newline="")
    source = {"source_id": "original-fixture", "rights_decision": "mirror", "rights_statement": "Original fixture", "citation": "Original fixture"}
    result = profile_gravity(path, source=source)
    assert result["row_count"] == 2
    assert result["channels_mgal"]["OG"] == [980000, 980000]
    assert result["channels_mgal"]["FAA"] == [23, None]
    assert result["channels_mgal"]["ISO"] == [-1, None]
    assert result["cba_minus_sba_minus_ttc_mgal"] == [-.25, -.25]
    assert result["duplicate_station_ids"] == ["A"]
    assert result["duplicate_author_xyz"] == [[500000, 4200000, 137]]
    assert len(result["flags"]) == 2 and result["excluded_rows"] == []
    assert result["uncertainty"]["kind"] == "unavailable"
    assert not result["modelling_eligible"] and not result["inversion_performed"]
    assert "tide/drift" in result["correction_state"]["OG"]
    assert not {"model", "truth", "predicted", "residual", "sigma"} & result.keys()
    assert json.loads(json.dumps(result, allow_nan=False)) == result
    path.write_text("station,value\nA,2\n", encoding="utf-8")
    with pytest.raises(SourceError, match="Unexpected"):
        profile_gravity(path, source=source)


def test_profile_guide_and_real_source():
    guide = (ROOT / "docs/guides/11_potential_source_intake.md").read_text(encoding="utf-8")
    for term in ("CC BY 4.0", "NAD27", "IGSN1971", "vertical datum", "modelling_eligible", "potential_sources.py"):
        assert term in guide
    for suffix in ("ps1", "sh"):
        script = (ROOT / f"scripts/intake-potential-sources.{suffix}").read_text(encoding="utf-8")
        assert "potential_sources.py" in script and "GEOPHYSICS_INTAKE_PYTHON" in script


def test_real_local_source_intake():
    if os.environ.get("GEOPHYSICS_REAL_POTENTIAL_SOURCE") != "1":
        pytest.skip("explicit local archive gate only; no download in tests or CI")
    source = load_ledger()["clear-lake-author-potentials-v2"]
    assert (ROOT / source["raw_path"]).is_file(), "Import the pinned ZIP with --file first; tests never fetch"
    record, raw, _ = acquire_source("clear-lake-author-potentials-v2")
    assert raw.stat().st_size == 121295137
    receipt = extract_selected(record, raw)
    assert receipt["entry_count"] == 40 and receipt["expanded_bytes"] == 299907397
    path = ROOT / next(item["path"] for item in receipt["members"] if item["name"] == "data/ground_gravity_data.csv")
    result = profile_gravity(path, source=record)
    assert result["row_count"] > 100
    assert not result["modelling_eligible"]
    assert result["row_count"] == 2929
    assert result["channel_bounds"]["FAA"]["missing_count"] == 70
    assert result["channel_bounds"]["SBA"]["missing_count"] == 70
    assert result["duplicate_station_ids"] == ["SROA55", "SROR4"]
    assert len(result["duplicate_author_xyz"]) == 1
    assert result["channels_mgal"]["OG"][0] == 979999.22
    assert not result["corrections_applied_by_intake"]


def test_all_selected_pins_before_any_publication(tmp_path):
    record, raw, payload = source_archive(tmp_path, [("data/ground.csv", b"unmodified original fixture observations\n"),
                                                   ("data/other.csv", b"other")])
    record["archive_contract"]["selected_members"]["data/other.csv"] = {"bytes": 5, "sha256": "0" * 64}
    with pytest.raises(SourceError, match="byte/hash mismatch"):
        extract_selected(record, raw, root=tmp_path)
    assert not list((tmp_path / "data/downloads/extracted").rglob("*.csv"))
    assert not list((tmp_path / "data/raw").rglob("*.json"))


@pytest.mark.parametrize("entries", [
    [("data", b"file"), ("data/ground.csv", b"x")],
    [("data/ground.csv", b"x"), ("DATA/ground.csv", b"x")],
    [("Data/other.csv", b"x"), ("data/ground.csv", b"x")],
])
def test_file_parent_and_case_aliases(tmp_path, entries):
    record, raw, _ = source_archive(tmp_path, entries)
    with pytest.raises(SourceError, match="Unsafe"):
        extract_selected(record, raw, root=tmp_path)


def test_existing_receipt_drift_before_publication(tmp_path):
    record, raw, _ = source_archive(tmp_path)
    receipt = tmp_path / "data/raw/acquisition/fixture-source-members.json"
    receipt.parent.mkdir(parents=True)
    receipt.write_bytes(b"protected receipt")
    with pytest.raises(SourceError, match="receipt drift"):
        extract_selected(record, raw, root=tmp_path)
    assert receipt.read_bytes() == b"protected receipt"
    assert not list((tmp_path / "data/downloads/extracted").rglob("*.csv"))


def test_unsupported_encrypted_and_special_entries(tmp_path):
    special = zipfile.ZipInfo("pipe")
    special.create_system = 3
    special.external_attr = (stat.S_IFIFO | 0o600) << 16
    record, raw, _ = source_archive(tmp_path, [("data/ground.csv", b"x"), (special, b"x")])
    with pytest.raises(SourceError, match="special"):
        extract_selected(record, raw, root=tmp_path)
    record, raw, _ = source_archive(tmp_path)
    with zipfile.ZipFile(raw, "w", compression=zipfile.ZIP_BZIP2) as archive:
        archive.writestr("data/ground.csv", b"unmodified original fixture observations\n")
    record.update(expected_bytes=raw.stat().st_size, sha256=hashlib.sha256(raw.read_bytes()).hexdigest())
    with pytest.raises(SourceError, match="unsupported"):
        extract_selected(record, raw, root=tmp_path)
    record, raw, _ = source_archive(tmp_path)
    value = bytearray(raw.read_bytes())
    central = value.index(b"PK\x01\x02")
    value[central + 8] |= 1
    raw.write_bytes(value)
    record.update(expected_bytes=len(value), sha256=hashlib.sha256(value).hexdigest())
    with pytest.raises(SourceError, match="Encrypted"):
        extract_selected(record, raw, root=tmp_path)


def test_unselected_arrays_and_code_not_opened(tmp_path, monkeypatch):
    record, raw, payload = source_archive(tmp_path, [("data/ground.csv", b"unmodified original fixture observations\n"),
                                                   ("results/model.npy", b"untrusted array"),
                                                   ("unsafe.py", b"raise RuntimeError('do not execute')")])
    original = zipfile.ZipFile.open
    opened = []
    def selected_only(archive, member, *args, **kwargs):
        opened.append(member.filename)
        assert member.filename == "data/ground.csv"
        return original(archive, member, *args, **kwargs)
    monkeypatch.setattr(zipfile.ZipFile, "open", selected_only)
    result = extract_selected(record, raw, root=tmp_path)
    assert opened == ["data/ground.csv"] and result["entry_count"] == 3
    assert not list((tmp_path / "data/downloads/extracted").rglob("*.npy"))
    assert not list((tmp_path / "data/downloads/extracted").rglob("*.py"))


def test_profile_physical_diagnostics_do_not_clip_or_fill(tmp_path):
    path = tmp_path / "observations.csv"
    text = io.StringIO(newline="")
    writer = csv.writer(text)
    writer.writerow(HEADER)
    writer.writerow(["original-index", " A ", 181, -91, -1, -2, "", 9.8, 23, 4, -2.75, 6.5, "Inf"])
    path.write_text(text.getvalue(), encoding="utf-8", newline="")
    source = {"source_id": "fixture", "rights_decision": "mirror", "rights_statement": "Original fixture", "citation": "Original fixture"}
    result = profile_gravity(path, source=source)
    assert result["original_row_indices"] == ["original-index"]
    assert result["station_ids"] == [" A "] and result["source_csv_line_ends"] == [2]
    assert result["author_xyz_m"] == [[-1, -2, None]]
    assert result["channels_mgal"]["OG"] == [9.8]
    assert result["channels_mgal"]["TTC"] == [-2.75]
    assert {item["reason"] for item in result["flags"]} == {"missing_or_nonfinite", "geographic_range",
           "declared_utm_range", "terrestrial_gravity_mgal_range", "negative_terrain_correction"}
    assert not result["corrections_applied_by_intake"] and not result["modelling_eligible"]
    pinned = load_ledger()["clear-lake-author-potentials-v2"]
    with pytest.raises(SourceError, match="byte/hash mismatch"):
        profile_gravity(path, source=pinned)


@pytest.mark.parametrize("data", [b"", b"station,value\nA,1\n", ",".join(HEADER).encode() + b"\n1,A,2\n",
                                 ",".join(HEADER).encode() + b"\n0,,1,1,1,1,1,1,1,1,1,1,1\n"])
def test_profile_rejects_ambiguous_or_incomplete_layout(tmp_path, data):
    path = tmp_path / "observations.csv"
    path.write_bytes(data)
    with pytest.raises(SourceError):
        profile_gravity(path, source={"source_id": "fixture"})


def test_storage_windows_junction_rejected(tmp_path):
    if os.name != "nt":
        pytest.skip("Windows junction control; symlink control covers other platforms")
    actual = tmp_path / "data/downloads/actual"
    actual.mkdir(parents=True)
    parent = tmp_path / "data/downloads/extracted"
    parent.mkdir(parents=True)
    junction = parent / "fixture-source"
    subprocess.run(["cmd", "/c", "mklink", "/J", str(junction), str(actual)], check=True, capture_output=True)
    with pytest.raises(SourceError, match="reparse|escapes"):
        safe_target(tmp_path, PurePosixPath("data/downloads/extracted/fixture-source/data/ground.csv"), "downloads")
    assert list(actual.iterdir()) == []


def test_storage_symlink_rejected(tmp_path):
    actual = tmp_path / "data/downloads/actual"
    actual.mkdir(parents=True)
    link = tmp_path / "data/downloads/extracted"
    try:
        link.symlink_to(actual, target_is_directory=True)
    except OSError as error:
        if os.name == "nt" and error.winerror == 1314:
            pytest.skip("Windows symlink privilege unavailable; junction control remains required")
        raise
    with pytest.raises(SourceError, match="Symlink|escapes"):
        safe_target(tmp_path, PurePosixPath("data/downloads/extracted/fixture-source/data/ground.csv"), "downloads")
    assert list(actual.iterdir()) == []


def test_corrupted_compression_rejected_before_publication(tmp_path):
    record, raw, _ = source_archive(tmp_path)
    value = bytearray(raw.read_bytes())
    with zipfile.ZipFile(raw) as archive:
        member = archive.getinfo("data/ground.csv")
        start = member.header_offset + 30 + len(member.filename.encode()) + len(member.extra)
    value[start] = 0xff  # invalid raw DEFLATE block; archive pin still matches this test input
    raw.write_bytes(value)
    record["sha256"] = hashlib.sha256(value).hexdigest()
    with pytest.raises(SourceError, match="Invalid ZIP"):
        extract_selected(record, raw, root=tmp_path)
    assert not list((tmp_path / "data/downloads/extracted").rglob("*.csv"))


def test_compact_inspection_evidence_not_solver_arrays():
    evidence = json.loads((ROOT / "docs/research/potential-source-intake-evidence-2026-10-03.json").read_text(encoding="utf-8"))
    assert evidence["schema"] == "geophysics.potential-source-intake-evidence/v1"
    assert evidence["profile"]["row_count"] == 2929
    assert evidence["archive"]["sha256"] == load_ledger()["clear-lake-author-potentials-v2"]["sha256"]
    assert evidence["metadata"]["sha256"] == load_ledger()["bartlett-fgdc"]["sha256"]
    assert evidence["profile"]["modelling_eligible"] is False
    assert not {"channels_mgal", "station_ids", "author_xyz_m", "predicted", "truth"} & evidence["profile"].keys()
    for item in evidence["receipt_files"]:
        assert len(item["sha256"]) == 64 and item["bytes"] > 0
