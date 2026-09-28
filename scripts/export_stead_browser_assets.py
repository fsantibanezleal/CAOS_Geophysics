"""Publish the frozen M13 ONNX model and preselected, QC-audited STEAD traces.

This is an asset preparation step, not a benchmark or browser-parity claim. It
requires the sealed held-out report and will not replace a prior public asset
directory. The 24 metadata-selected records stay fixed even when QC rejects a
waveform; only valid rows receive a binary trace.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data-pipeline"))

from evaluate_stead_phase import _load_locked_test  # noqa: E402
from extract_stead_phase import _members  # noqa: E402
from stead_phase import file_sha256  # noqa: E402


SOURCE = {
    "dataset": "STEAD",
    "authors": "Mousavi, Sheng, Zhu and Beroza (2019)",
    "citation": "Stanford Earthquake Dataset (STEAD): A Global Data Set of Seismic Signals for AI",
    "doi": "10.1109/ACCESS.2019.2947848",
    "original_url": "https://github.com/smousavi05/STEAD",
    "mirror_url": "https://seisbench.gfz-potsdam.de/mirror/datasets/stead/",
    "license": "CC BY 4.0",
    "license_url": "https://github.com/smousavi05/STEAD/blob/master/LICENSE",
    "modification": (
        "Metadata-only event/station-disjoint selection; source ZNE counts reordered ENZ; "
        "QC rejects flat or exactly duplicated components; valid traces mean-removed and "
        "divided by per-component peak centred count for model inference. These are "
        "dimensionless normalized instrument counts, not ground velocity or acceleration."
    ),
}


def _load_selection(private_path: Path, public_path: Path, test_selection_hash: str) -> tuple[list[dict], str]:
    if not private_path.is_file() or not public_path.is_file():
        raise ValueError("predeclared private/public browser selections are missing")
    private = json.loads(private_path.read_text(encoding="utf-8"))
    public = json.loads(public_path.read_text(encoding="utf-8"))
    if (private.get("schema") != "caos.stead-browser-members.v1"
            or public.get("schema") != "caos.stead-browser-selection-profile.v1"
            or private.get("test_selection_sha256") != test_selection_hash
            or public.get("test_selection_sha256") != test_selection_hash
            or private.get("waveform_values_used_to_select") is not False
            or private.get("model_predictions_used_to_select") is not False
            or public.get("test_performance_known_when_selected") is not False):
        raise ValueError("browser selection was not fixed before held-out scoring")
    selected = private.get("members", [])
    identifiers = sorted(row["trace_id"] for row in selected)
    digest = hashlib.sha256("\n".join(identifiers).encode()).hexdigest()
    if (len(selected) != 24 or len(set(identifiers)) != 24
            or digest != private.get("display_ids_sha256")
            or digest != public.get("display_ids_sha256")):
        raise ValueError("browser selection has changed or duplicated a trace")
    return selected, digest


def export(
    manifest_path: Path,
    selection_path: Path,
    selection_profile_path: Path,
    extraction_dir: Path,
    frozen_receipt_path: Path,
    onnx_path: Path,
    native_parity_path: Path,
    heldout_report_path: Path,
    output_dir: Path,
) -> dict:
    destination_root = (ROOT / "data/derived/phase/browser-assets").resolve()
    if (output_dir.resolve() != (destination_root / "stead").resolve()
            or output_dir.exists() or output_dir.is_symlink()):
        raise ValueError("public STEAD asset destination must be a new canonical directory")
    members, test_selection_hash = _members(manifest_path, "test")
    selected, selected_hash = _load_selection(
        selection_path, selection_profile_path, test_selection_hash,
    )
    by_id = {member.trace_id: index for index, member in enumerate(members)}
    if any(row.get("trace_id") not in by_id or row != members[by_id[row["trace_id"]]].__dict__
           for row in selected):
        raise ValueError("browser selection differs from the locked test inventory")
    loaded, index, values, frozen, _checkpoint, checkpoint_hash = _load_locked_test(
        extraction_dir, manifest_path, frozen_receipt_path, ROOT / "data/raw",
    )
    if loaded != members:
        raise ValueError("held-out extraction differs from test selection")
    report = json.loads(heldout_report_path.read_text(encoding="utf-8"))
    native = json.loads(native_parity_path.read_text(encoding="utf-8"))
    model_hash = file_sha256(onnx_path)
    if (report.get("schema") != "caos.stead-phase-heldout-benchmark.v1"
            or report.get("status") != "computed-on-real-heldout-waveforms"
            or report.get("checkpoint_sha256") != checkpoint_hash
            or report.get("metadata_selection_sha256") != test_selection_hash
            or report.get("test_array_sha256") != index["array_sha256"]
            or report.get("selected") != len(members)
            or native.get("schema") != "caos.phase-onnx-dev-parity.v1"
            or native.get("checkpoint_sha256") != checkpoint_hash
            or native.get("onnx_sha256") != model_hash
            or native.get("parity", {}).get("max_probability_absolute_error", 1) > 0.001
            or native.get("parity", {}).get("max_peak_time_error_samples", 2) > 1
            or report.get("dev_selected_thresholds") != native.get("thresholds")
            or report.get("dev_selected_thresholds") != {
                "P": frozen["p_threshold"], "S": frozen["s_threshold"],
            }):
        raise ValueError("held-out benchmark, ONNX export and checkpoint do not match")
    destination_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".stead-assets-", dir=destination_root) as temporary:
        staged = Path(temporary)
        shutil.copyfile(onnx_path, staged / "model.onnx")
        shutil.copyfile(heldout_report_path, staged / "benchmark.json")
        records = []
        valid_count = 0
        for ordinal, row in enumerate(selected):
            member = members[by_id[row["trace_id"]]]
            entry = index["members"][by_id[member.trace_id]]
            record = {
                "trace_id": member.trace_id,
                "station_id": member.station_id,
                "network": member.station_id.split(".", 1)[0],
                "channel": member.channel,
                "category": member.category,
                "analyst_p_s": member.p_index * 0.01 if member.p_index is not None else None,
                "analyst_s_s": member.s_index * 0.01 if member.s_index is not None else None,
                "reference_is_ground_truth": False,
            }
            if entry.get("valid") is True:
                waveform = np.asarray(values[by_id[member.trace_id]], dtype="<f4")
                if (waveform.shape != (3, 6000) or not np.all(np.isfinite(waveform))
                        or np.max(np.abs(waveform)) > 1.000001):
                    raise ValueError(f"invalid extracted normalized waveform: {member.trace_id}")
                filename = f"trace-{ordinal:02d}.f32"
                (staged / filename).write_bytes(waveform.tobytes(order="C"))
                record.update({
                    "status": "qc-valid",
                    "waveform_file": filename,
                    "waveform_sha256": file_sha256(staged / filename),
                    "waveform_bytes": (staged / filename).stat().st_size,
                    "normalization": entry["scales"],
                })
                valid_count += 1
            else:
                record.update({"status": "qc-rejected", "qc_reason": entry.get("reason")})
            records.append(record)
        manifest = {
            "schema": "caos.phase-browser-assets.v1",
            "status": "assets-exported-browser-parity-not-yet-verified",
            "source": SOURCE,
            "selection": {
                "selected_before_heldout_scoring": True,
                "selected": len(records),
                "qc_valid": valid_count,
                "qc_rejected": len(records) - valid_count,
                "display_ids_sha256": selected_hash,
                "test_selection_sha256": test_selection_hash,
                "full_benchmark_selected": len(members),
            },
            "input": {
                "sample_rate_hz": 100,
                "samples": 6000,
                "duration_s": 60,
                "component_order": ["E", "N", "Z"],
                "shape": [1, 3, 6000],
                "file_dtype": "float32-little-endian",
                "file_layout": "component-major; 6000 consecutive samples per component",
                "unit": "dimensionless normalized instrument counts",
                "original_unit": "unrestituted instrument counts",
                "normalization": "per-component float64 mean cast to float32; subtract in float32; divide by float32 peak absolute centred count",
            },
            "output": {"shape": [1, 3, 6000], "classes": ["N", "P", "S"]},
            "model": {
                "file": "model.onnx", "sha256": model_hash,
                "bytes": (staged / "model.onnx").stat().st_size,
                "checkpoint_sha256": checkpoint_hash,
                "thresholds": native["thresholds"],
                "peak_rule": "global class argmax above threshold; S abstains when S-P < 0.4 s",
                "native_dev_max_abs_probability_error": native["parity"]["max_probability_absolute_error"],
                "native_dev_max_peak_error_samples": native["parity"]["max_peak_time_error_samples"],
                "probabilities_calibrated": False,
            },
            "benchmark": {
                "file": "benchmark.json", "sha256": file_sha256(staged / "benchmark.json"),
                "selected": report["selected"], "qc_valid": report["valid"],
                "reference": report["reference"], "tolerance_s": report["tolerance_s"],
            },
            "records": records,
            "browser_parity_verified": False,
        }
        (staged / "manifest.json").write_bytes(
            (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        )
        staged.rename(output_dir)
    return {"output": str(output_dir), "selected": len(records),
            "qc_valid": valid_count, "qc_rejected": len(records) - valid_count,
            "model_sha256": model_hash, "manifest_sha256": file_sha256(output_dir / "manifest.json")}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/raw/phase/stead-selection.json")
    parser.add_argument("--selection", type=Path,
                        default=ROOT / "data/raw/phase/stead-browser-selection.json")
    parser.add_argument("--selection-profile", type=Path,
                        default=ROOT / "data/derived/phase/stead-browser-selection-profile.json")
    parser.add_argument("--extraction-dir", type=Path, default=ROOT / "data/raw/phase/extracted")
    parser.add_argument("--frozen-receipt", type=Path,
                        default=ROOT / "data/raw/phase/models-amp2/phase-freeze.json")
    parser.add_argument("--onnx", type=Path,
                        default=ROOT / "data/raw/phase/models-amp2/phase-model.onnx")
    parser.add_argument("--native-parity", type=Path,
                        default=ROOT / "data/raw/phase/models-amp2/phase-onnx-dev-parity.json")
    parser.add_argument("--heldout-report", type=Path,
                        default=ROOT / "data/derived/phase/stead-heldout-benchmark.json")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "data/derived/phase/browser-assets/stead")
    args = parser.parse_args()
    print(json.dumps(export(
        args.manifest, args.selection, args.selection_profile, args.extraction_dir,
        args.frozen_receipt, args.onnx, args.native_parity, args.heldout_report,
        args.output,
    ), indent=2))


if __name__ == "__main__":
    main()
