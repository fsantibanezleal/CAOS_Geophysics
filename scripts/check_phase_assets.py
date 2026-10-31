"""Cheap stdlib guard for committed M13 browser bytes; not an accuracy test."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "data/derived/phase/browser-assets/stead"
BENCHMARK = ROOT / "data/derived/phase/stead-heldout-benchmark.json"
OVERLAP = ROOT / "data/derived/phase/stead-heldout-overlap.json"
SOURCE_RECEIPT = ROOT / "data/derived/phase/stead-waveform-source.json"
RIGHTS_REVIEW = ROOT / "docs/design/features/phase-picking/rights-review-2026-10-28.md"
HOST_PATH = re.compile(rb"[A-Za-z]:\\(?:[^\\\x00\r\n]{1,100}\\){2}")


def raw(name: str) -> bytes:
    if Path(name).name != name or name in {".", ".."}:
        raise ValueError("unsafe M13 asset name")
    return (ASSETS / name).read_bytes()


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def validate() -> None:
    manifest = json.loads(raw("manifest.json"))
    benchmark_bytes = raw("benchmark.json")
    benchmark = json.loads(benchmark_bytes)
    overlap = json.loads(OVERLAP.read_bytes())
    source_receipt = json.loads(SOURCE_RECEIPT.read_text(encoding="utf-8"))
    rights = manifest["source"]["redistribution"]
    source_rights = source_receipt["rights"]
    assert manifest["schema"] == "caos.phase-browser-assets.v1"
    assert manifest["source"]["license"] == "CC BY 4.0"
    assert manifest["source"]["license_url"] == (
        "https://github.com/smousavi05/STEAD/blob/e6f247cf174e4aaefe01a6fcc72a0e88296d42b4/LICENSE"
    )
    assert manifest["source"]["doi"] == "10.1109/ACCESS.2019.2947848"
    assert rights["decision"] == "approved-with-attribution"
    assert rights["license"] == "CC BY 4.0"
    assert rights["license_url"] == "https://creativecommons.org/licenses/by/4.0/"
    assert rights["review"] == "docs/design/features/phase-picking/rights-review-2026-10-28.md"
    assert rights["attribution_file"] == "ATTRIBUTION.md"
    assert source_rights["release_decision"] == "public-selected-derivatives-approved-with-CC-BY-4.0-attribution"
    assert source_rights["rights_review"] == rights["review"]
    assert source_rights["reviewed_upstream_license_url"] == manifest["source"]["license_url"]
    for key, manifest_key in (
        ("reviewed_upstream_license_commit", "upstream_license_commit"),
        ("reviewed_upstream_license_blob_sha1", "upstream_license_blob_sha1"),
        ("reviewed_upstream_license_sha256", "upstream_license_sha256"),
        ("reviewed_seisbench_commit", "seisbench_commit"),
        ("reviewed_seisbench_stead_blob_sha1", "seisbench_stead_blob_sha1"),
        ("reviewed_mirror_license_sha256", "mirror_license_sha256"),
    ):
        assert source_rights[key] == rights[manifest_key]
    attribution = raw("ATTRIBUTION.md").decode("utf-8")
    review = RIGHTS_REVIEW.read_text(encoding="utf-8")
    assert RIGHTS_REVIEW.is_file()
    for required in ("Mousavi", "Sheng", "Zhu", "Beroza", "CC BY 4.0", "changes", "not endorsed"):
        assert required.casefold() in attribution.casefold()
    assert "no-warranty" in attribution.casefold()
    assert "approved for public distribution" in review
    assert manifest["selection"]["selected_before_heldout_scoring"] is True
    assert (manifest["selection"]["selected"], manifest["selection"]["qc_valid"],
            manifest["selection"]["qc_rejected"]) == (24, 23, 1)
    assert manifest["input"]["shape"] == [1, 3, 6000]
    assert manifest["input"]["component_order"] == ["E", "N", "Z"]
    assert manifest["output"]["classes"] == ["N", "P", "S"]
    assert manifest["model"]["file"] == "model.onnx"
    model = raw("model.onnx")
    assert len(model) == manifest["model"]["bytes"] <= 10_000_000
    assert digest(model) == manifest["model"]["sha256"]
    assert HOST_PATH.search(model) is None, "ONNX contains an absolute host path"
    assert manifest["benchmark"]["file"] == "benchmark.json"
    assert digest(benchmark_bytes) == manifest["benchmark"]["sha256"]
    assert digest(BENCHMARK.read_bytes()) == digest(benchmark_bytes)
    assert benchmark["schema"] == "caos.stead-phase-heldout-benchmark.v1"
    assert benchmark["checkpoint_sha256"] == manifest["model"]["checkpoint_sha256"]
    assert benchmark["selected"] == manifest["selection"]["full_benchmark_selected"] == 6000
    assert benchmark["valid"] == manifest["benchmark"]["qc_valid"] == 5926
    assert overlap["checkpoint_sha256"] == benchmark["checkpoint_sha256"]
    assert overlap["array_sha256"]["test"] == benchmark["test_array_sha256"]

    records = manifest["records"]
    assert len(records) == 24 and len({row["trace_id"] for row in records}) == 24
    identity = "\n".join(sorted(row["trace_id"] for row in records)).encode()
    assert digest(identity) == manifest["selection"]["display_ids_sha256"]
    valid = [row for row in records if row["status"] == "qc-valid"]
    rejected = [row for row in records if row["status"] == "qc-rejected"]
    assert len(valid) == 23 and len(rejected) == 1
    assert not any(key.startswith("waveform_") for key in rejected[0])
    wave_files = set()
    for row in valid:
        name = row["waveform_file"]
        assert re.fullmatch(r"trace-\d\d\.f32", name)
        wave_files.add(name)
        payload = raw(name)
        assert len(payload) == row["waveform_bytes"] == 72_000
        assert digest(payload) == row["waveform_sha256"]
    assert wave_files == {path.name for path in ASSETS.glob("trace-*.f32")}
    assert (ASSETS / "ATTRIBUTION.md").is_file()
    print("PASS: M13 model, rights decision, attribution, 23 waveform assets, QC rejection, benchmark and hashes consistent")


if __name__ == "__main__":
    validate()
