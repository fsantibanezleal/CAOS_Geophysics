"""Small, source-bound checks of the public real-waveform M13 asset release."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct


ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "data/derived/phase/browser-assets/stead"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_model_and_benchmark_are_bound_to_public_manifest() -> None:
    manifest = json.loads((ASSETS / "manifest.json").read_text(encoding="utf-8"))
    benchmark = json.loads((ASSETS / "benchmark.json").read_text(encoding="utf-8"))
    overlap = json.loads((ROOT / "data/derived/phase/stead-heldout-overlap.json").read_text(
        encoding="utf-8",
    ))
    assert manifest["schema"] == "caos.phase-browser-assets.v1"
    assert manifest["source"]["license"] == "CC BY 4.0"
    assert manifest["source"]["doi"] == "10.1109/ACCESS.2019.2947848"
    assert "modification" in manifest["source"]
    assert _sha256(ASSETS / manifest["model"]["file"]) == manifest["model"]["sha256"]
    assert _sha256(ASSETS / manifest["benchmark"]["file"]) == manifest["benchmark"]["sha256"]
    assert benchmark["schema"] == "caos.stead-phase-heldout-benchmark.v1"
    assert benchmark["checkpoint_sha256"] == manifest["model"]["checkpoint_sha256"]
    assert benchmark["metadata_selection_sha256"] == manifest["selection"]["test_selection_sha256"]
    assert benchmark["selected"] == manifest["selection"]["full_benchmark_selected"] == 6000
    assert benchmark["valid"] == manifest["benchmark"]["qc_valid"] == 5926
    assert overlap["checkpoint_sha256"] == benchmark["checkpoint_sha256"]
    assert overlap["array_sha256"]["test"] == benchmark["test_array_sha256"]
    assert overlap["status"] == "no-exact-cross-partition-overlap"


def test_predeclared_display_population_preserves_qc_failure() -> None:
    manifest = json.loads((ASSETS / "manifest.json").read_text(encoding="utf-8"))
    records = manifest["records"]
    assert len(records) == manifest["selection"]["selected"] == 24
    assert len({row["trace_id"] for row in records}) == 24
    digest = hashlib.sha256("\n".join(sorted(row["trace_id"] for row in records)).encode()).hexdigest()
    assert digest == manifest["selection"]["display_ids_sha256"]
    valid = [row for row in records if row["status"] == "qc-valid"]
    rejected = [row for row in records if row["status"] == "qc-rejected"]
    assert len(valid) == manifest["selection"]["qc_valid"] == 23
    assert len(rejected) == manifest["selection"]["qc_rejected"] == 1
    assert "flat component" in rejected[0]["qc_reason"]
    assert "waveform_file" not in rejected[0]
    assert manifest["input"]["shape"] == [1, 3, 6000]
    assert manifest["input"]["component_order"] == ["E", "N", "Z"]
    assert manifest["input"]["sample_rate_hz"] == 100
    assert manifest["output"]["classes"] == ["N", "P", "S"]
    for record in records:
        if record["category"] == "noise":
            assert record["analyst_p_s"] is None and record["analyst_s_s"] is None
        else:
            assert 0 <= record["analyst_p_s"] < record["analyst_s_s"] < 60


def test_binary_waveforms_are_finite_normalized_enz() -> None:
    manifest = json.loads((ASSETS / "manifest.json").read_text(encoding="utf-8"))
    for record in manifest["records"]:
        if record["status"] != "qc-valid":
            continue
        path = ASSETS / record["waveform_file"]
        data = path.read_bytes()
        assert len(data) == record["waveform_bytes"] == 3 * 6000 * 4
        assert hashlib.sha256(data).hexdigest() == record["waveform_sha256"]
        # A few representative positions check the declared little-endian
        # layout without requiring NumPy in the frontend test environment.
        for sample in (0, 2999, 5999, 6000, 11999, 12000, 17999):
            value = struct.unpack_from("<f", data, sample * 4)[0]
            assert -1.000001 <= value <= 1.000001
        assert record["normalization"]["component_order"] == ["E", "N", "Z"]
        assert len(record["normalization"]["peak_centered_counts"]) == 3
        assert all(peak > 0 for peak in record["normalization"]["peak_centered_counts"])
