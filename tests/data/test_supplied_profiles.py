"""Closed supplied-profile admission and immutable portable results."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

import supplied_profiles as workflow


def original(tmp_path):
    path = tmp_path / "own.ohm"
    text = "\n".join(["# Wenner array with 2m", "8# Number of sensors", "#x z",
                      *(f"{2*i} 0" for i in range(8)), "5# Number of data", "#a b m n R",
                      *(f"{i+1} {i+4} {i+2} {i+3} {-1 if i == 0 else 1}" for i in range(5))])
    path.write_text(text + "\n", encoding="utf-8")
    raw = path.read_bytes()
    meta = {"schema": "geophysics.supplied-profile/v1",
            "method": "ert.topographic-profile/v1",
            "source": {"source_id": "own-field-01", "kind": "user_upload",
                       "citation": "Own acquisition; unverified declaration",
                       "rights": {"holder": "Local operator", "processing_allowed": True,
                                  "redistribution_allowed": False},
                       "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)},
            "frame": {"horizontal_reference": "Local profile baseline",
                      "vertical_datum": "Local benchmark", "coordinate_unit": "m",
                      "vertical_positive": "up", "profile_axes": ["distance", "elevation"]},
            "weights": {"policy": "provider-example-conditional/v1"}}
    return path, meta


def test_closed_metadata(tmp_path):
    _, meta = original(tmp_path)
    assert workflow.parse_metadata(json.dumps(meta).encode()) == meta
    for extra in ({**meta, "extra": 1}, {**meta, "schema": "other"}):
        with pytest.raises(workflow.ProfileError):
            workflow.parse_metadata(json.dumps(extra).encode())
    for suffix in (', "schema": "duplicate"}', ', "extra": NaN}'):
        with pytest.raises(workflow.ProfileError):
            workflow.parse_metadata((json.dumps(meta)[:-1] + suffix).encode())


@pytest.mark.parametrize("section,key,value", [
    ("source", "bytes", True), ("source", "sha256", "A"*64),
    ("source", "kind", "provider"), ("source", "source_id", ""),
    ("frame", "coordinate_unit", "ft"), ("frame", "vertical_positive", "down"),
    ("frame", "profile_axes", ["northing", "easting"]),
    ("weights", "policy", "measured-covariance"),
])
def test_metadata_mutations(tmp_path, section, key, value):
    _, meta = original(tmp_path)
    meta[section][key] = value
    with pytest.raises(workflow.ProfileError):
        workflow.parse_metadata(json.dumps(meta).encode())


def test_rights_exact_and_bounded(tmp_path):
    _, meta = original(tmp_path)
    for key, value in (("processing_allowed", False), ("processing_allowed", 1),
                       ("redistribution_allowed", 0), ("holder", "é"*257)):
        bad = deepcopy(meta)
        bad["source"]["rights"][key] = value
        with pytest.raises(workflow.ProfileError):
            workflow.parse_metadata(json.dumps(bad).encode())
    with pytest.raises(workflow.ProfileError):
        workflow.parse_metadata(b" " * (workflow.MAX_METADATA_BYTES + 1))


def test_source_binding_and_no_engine_on_rejection(tmp_path, monkeypatch):
    import ert
    path, meta = original(tmp_path)
    monkeypatch.setattr(ert, "run", lambda *a, **k: pytest.fail("rejected original executed"))
    bad = deepcopy(meta)
    bad["source"]["sha256"] = "0" * 64
    with pytest.raises(workflow.ProfileError):
        workflow.process_profile(path, bad)
    bad = deepcopy(meta)
    bad["source"]["bytes"] += 1
    with pytest.raises(workflow.ProfileError):
        workflow.process_profile(path, bad)
    with pytest.raises(workflow.ProfileError):
        workflow.process_profile(tmp_path, meta)


def test_actual_ineligible_run_preserved_and_exported(tmp_path):
    path, meta = original(tmp_path)
    result = workflow.process_profile(path, meta)
    assert result["engine_report"]["inverse_status"] == "ineligible"
    assert result["engine_report"]["source_id"] == "own-field-01"
    assert result["engine_report"]["truth"] is None
    assert result["engine_report"]["rights_decision"] == "supplied-declaration-not-verified"
    assert result["original"] == {"sha256": meta["source"]["sha256"], "bytes": meta["source"]["bytes"]}
    assert len(result["geometry"]["sensor_xz_m"]) == 8
    assert result["geometry"]["row_ids_zero_based"] == list(range(5))
    assert result["scope"]["residual_convention"] == "predicted-minus-observed"
    assert result["scope"]["uploaded"] is False
    out = tmp_path / "new-result"
    workflow.export_result(result, out)
    assert {p.name for p in out.iterdir()} == {"result.json", "manifest.json"}
    assert workflow.import_result(out) == result
    assert not (out / path.name).exists()
    with pytest.raises(workflow.ProfileError):
        workflow.export_result(result, out)


def test_export_and_import_tamper(tmp_path):
    path, meta = original(tmp_path)
    result = workflow.process_profile(path, meta)
    bad = deepcopy(result)
    bad["metadata"]["source"]["source_id"] = "false-provider"
    with pytest.raises(workflow.ProfileError):
        workflow.export_result(bad, tmp_path / "bad")
    out = tmp_path / "good"
    workflow.export_result(result, out)
    member = out / "result.json"
    member.write_bytes(member.read_bytes() + b" ")
    with pytest.raises(workflow.ProfileError):
        workflow.import_result(out)


def test_drift_during_engine_prevents_result(tmp_path, monkeypatch):
    import ert
    path, meta = original(tmp_path)
    actual = ert.run

    def changed(*args, **kwargs):
        report = actual(*args, **kwargs)
        path.write_bytes(path.read_bytes() + b"\n")
        return report

    monkeypatch.setattr(ert, "run", changed)
    with pytest.raises(workflow.ProfileError, match="original changed during calculation"):
        workflow.process_profile(path, meta)


def test_symlink_is_not_original(tmp_path):
    path, meta = original(tmp_path)
    linked = tmp_path / "link.ohm"
    try:
        linked.symlink_to(path)
    except OSError:
        pytest.skip("OS does not permit symlink fixture")
    with pytest.raises(workflow.ProfileError):
        workflow.process_profile(linked, meta)


def test_traveltime_ineligible_geometry_retained(tmp_path):
    _, meta = original(tmp_path)
    path = tmp_path / "own.sgt"
    path.write_text("4 # shot/geophone points\n#x y\n0 0\n1 0\n2 0\n3 0\n"
                    "4 # measurements\n#s g t\n1 2 0.001\n1 3 0.002\n"
                    "2 3 0.001\n2 4 0.002\n", encoding="utf-8")
    raw = path.read_bytes()
    meta["method"] = "traveltime.first-arrival-profile/v1"
    meta["source"].update(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
    result = workflow.process_profile(path, meta)
    assert result["engine_report"]["inverse_status"] == "ineligible"
    assert len(result["geometry"]["shot_geophone_zero_based"]) == 4
    assert result["engine_report"]["unit_basis"].startswith("explicit supplied metadata")
    workflow.export_result(result, tmp_path / "own-tt-result")
    assert workflow.import_result(tmp_path / "own-tt-result") == result


def test_cli_failure_artifact_and_safe_output(tmp_path):
    path, meta = original(tmp_path)
    metadata_path = tmp_path / "metadata.json"
    metadata_path.write_text(json.dumps(meta), encoding="utf-8")
    cli = Path(__file__).resolve().parents[2] / "scripts/process_supplied_profile.py"
    out = tmp_path / "cli-result"
    completed = subprocess.run([sys.executable, "-B", str(cli), "--input", str(path),
                                "--metadata", str(metadata_path), "--output", str(out)],
                               capture_output=True, text=True, timeout=30)
    assert completed.returncode == 3
    receipt = json.loads(completed.stdout)
    assert receipt["status"] == "ineligible" and receipt["published"] is True
    assert str(tmp_path) not in completed.stdout
    assert workflow.import_result(out)["engine_report"]["inverse_status"] == "ineligible"
