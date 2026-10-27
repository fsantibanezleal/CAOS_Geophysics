"""Recompute descriptive M08/M13 results on the 23 public browser traces.

The 24-record display subset was selected before scoring and is not an
independent accuracy sample. Its STEAD picks are analyst references, not
geological truth. The locked 6,000-record benchmark remains the only accuracy
claim. Outputs are written only beneath CAOS_TEMP_ROOT.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

import numpy as np
import onnxruntime as ort

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data-pipeline"))

from phase_model import pick_probabilities  # noqa: E402
from phase_picking import classical_stalta_picks, evaluate_matched_picks  # noqa: E402

SAMPLES = 6000
RATE_HZ = 100
THRESHOLD = 0.8
TOLERANCE_S = 0.5


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _asset_child(root: Path, relative: object, *, description: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ValueError(f"unsafe {description} asset path")
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root.resolve()) or not candidate.is_file():
        raise ValueError(f"missing or escaping {description} asset")
    return candidate


def _metric_row(item: dict, *, noise_count: int) -> dict:
    tp = int(item["correct_within_tolerance"])
    missed = int(item["missed"])
    outside = int(item["outside_tolerance"])
    false = int(item["false_without_reference"])
    fp = outside + false
    fn = missed + outside
    f1_denominator = 2 * tp + fp + fn
    signed = np.asarray(item["timing_signed_s"], dtype=np.float64)
    absolute = np.abs(signed)
    return {
        "reference_count": int(item["total"]),
        "correct_within_0p5s": tp,
        "missed": missed,
        "outside_tolerance": outside,
        "false_without_reference": false,
        "precision_at_0p5s": tp / (tp + fp) if tp + fp else None,
        "recall_at_0p5s": tp / (tp + fn) if tp + fn else None,
        "f1_at_0p5s": 2 * tp / f1_denominator if f1_denominator else None,
        "valid_noise_false_pick_rate": false / noise_count if noise_count else None,
        "picked_reference_count": int(len(signed)),
        "timing_bias_median_s": float(np.median(signed)) if len(signed) else None,
        "timing_absolute_median_s": float(np.median(absolute)) if len(absolute) else None,
        "timing_absolute_p90_s": float(np.percentile(absolute, 90)) if len(absolute) else None,
    }


def process(assets_dir: Path, output_path: Path) -> dict:
    assets_dir = Path(assets_dir).resolve()
    output_path = Path(output_path).resolve()
    temp_setting = os.environ.get("CAOS_TEMP_ROOT", "")
    if not temp_setting.strip():
        raise ValueError("CAOS_TEMP_ROOT must identify the configured temporary directory")
    temp_root = Path(temp_setting).resolve()
    if not output_path.is_relative_to(temp_root):
        raise ValueError("M13 subset output must be beneath CAOS_TEMP_ROOT")
    manifest_path = assets_dir / "manifest.json"
    benchmark_path = assets_dir / "benchmark.json"
    manifest_bytes = manifest_path.read_bytes()
    benchmark_bytes = benchmark_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    benchmark = json.loads(benchmark_bytes)
    if (manifest.get("schema") != "caos.phase-browser-assets.v1"
            or manifest.get("browser_parity_verified") is not False
            or manifest.get("selection", {}).get("selected_before_heldout_scoring") is not True
            or manifest.get("selection", {}).get("selected") != 24
            or manifest.get("selection", {}).get("qc_valid") != 23
            or manifest.get("selection", {}).get("qc_rejected") != 1
            or manifest.get("input", {}).get("sample_rate_hz") != RATE_HZ
            or manifest.get("input", {}).get("samples") != SAMPLES
            or manifest.get("input", {}).get("component_order") != ["E", "N", "Z"]
            or manifest.get("output", {}).get("classes") != ["N", "P", "S"]
            or manifest.get("benchmark", {}).get("selected") != 6000
            or manifest.get("benchmark", {}).get("tolerance_s") != TOLERANCE_S
            or benchmark.get("schema") != "caos.stead-phase-heldout-benchmark.v1"
            or benchmark.get("checkpoint_sha256") != manifest["model"]["checkpoint_sha256"]
            or benchmark.get("selected") != 6000
            or benchmark.get("metrics_include_qc_failures_as_unpicked") is not True):
        raise ValueError("M13 assets or benchmark differ from the frozen browser contract")
    model_path = _asset_child(assets_dir, manifest["model"]["file"], description="model")
    if (model_path.stat().st_size != manifest["model"]["bytes"]
            or sha256(model_path) != manifest["model"]["sha256"]):
        raise ValueError("M13 ONNX model hash or byte count differs from its manifest")

    records = manifest["records"]
    if not isinstance(records, list) or any(not isinstance(row, dict) for row in records):
        raise ValueError("M13 trace manifest must contain record objects")
    trace_ids = [row.get("trace_id") for row in records]
    if any(not isinstance(trace_id, str) or not trace_id for trace_id in trace_ids) or len(set(trace_ids)) != len(trace_ids):
        raise ValueError("M13 trace identifiers must be nonempty and unique")
    valid = [row for row in records if row.get("status") == "qc-valid"]
    rejected = [row for row in records if row.get("status") == "qc-rejected"]
    if (len(records) != 24 or len(valid) != 23 or len(rejected) != 1
            or rejected[0].get("waveform_file") is not None
            or rejected[0].get("waveform_sha256") is not None):
        raise ValueError("QC rejection must remain excluded without acquiring waveform bytes")

    session_options = ort.SessionOptions()
    session_options.intra_op_num_threads = 1
    session_options.inter_op_num_threads = 1
    session = ort.InferenceSession(
        str(model_path),
        providers=["CPUExecutionProvider"],
        sess_options=session_options,
    )
    if ([item.name for item in session.get_inputs()] != ["waveform"]
            or [item.name for item in session.get_outputs()] != ["probabilities"]):
        raise ValueError("M13 ONNX input/output names differ from the browser contract")

    labels: dict[str, dict[str, float | None]] = {}
    predictions: dict[str, dict[str, dict[str, float | None]]] = {"M08": {}, "M13": {}}
    rows = []
    example = None
    source = manifest.get("source", {})
    if ("CC BY 4.0" not in source.get("license", "")
            or not source.get("doi") or not source.get("citation")):
        raise ValueError("STEAD attribution and license metadata are required")

    for row in valid:
        waveform_path = _asset_child(assets_dir, row.get("waveform_file"), description=f"waveform {row['trace_id']}")
        raw = waveform_path.read_bytes()
        if len(raw) != 3 * SAMPLES * 4 or hashlib.sha256(raw).hexdigest() != row["waveform_sha256"]:
            raise ValueError(f"STEAD waveform bytes differ from the manifest: {row['trace_id']}")
        waveform = np.frombuffer(raw, dtype="<f4").reshape(1, 3, SAMPLES)
        if not np.all(np.isfinite(waveform)):
            raise ValueError(f"nonfinite normalized samples: {row['trace_id']}")
        probabilities = np.asarray(
            session.run(["probabilities"], {"waveform": waveform})[0], dtype=np.float32,
        )
        if (probabilities.shape != (1, 3, SAMPLES)
                or not np.all(np.isfinite(probabilities))
                or np.any(probabilities < 0) or np.any(probabilities > 1)
                or not np.allclose(probabilities.sum(axis=1), 1, atol=1e-3)):
            raise ValueError(f"invalid N/P/S probability output: {row['trace_id']}")
        probabilities = probabilities[0]
        picks = pick_probabilities(
            probabilities, p_threshold=THRESHOLD, s_threshold=THRESHOLD,
            minimum_ps_s=0.4,
        )
        analyst = {phase: row[f"analyst_{phase.lower()}_s"] for phase in ("P", "S")}
        if row.get("reference_is_ground_truth") is not False:
            raise ValueError("STEAD analyst picks must not be labelled geological truth")
        labels[row["trace_id"]] = analyst
        predictions["M13"][row["trace_id"]] = picks
        predictions["M08"][row["trace_id"]] = classical_stalta_picks(
            np.asarray(waveform[0].T, dtype=np.float64), sample_interval_s=1 / RATE_HZ,
        )
        rows.append({
            "trace_id": row["trace_id"], "network": row["network"],
            "station_id": row["station_id"], "category": row["category"],
            "analyst_p_s": analyst["P"], "analyst_s_s": analyst["S"],
            "m08_p_s": predictions["M08"][row["trace_id"]]["P"],
            "m08_s_s": predictions["M08"][row["trace_id"]]["S"],
            "m13_p_s": picks["P"], "m13_s_s": picks["S"],
            "m13_p_peak": float(probabilities[1].max()),
            "m13_s_peak": float(probabilities[2].max()),
        })
        if example is None and analyst["P"] is not None and analyst["S"] is not None and picks["P"] is not None:
            example = {
                "trace_id": row["trace_id"], "waveform_enz": waveform[0].T.astype(float).tolist(),
                "probabilities_nps": probabilities.T.astype(float).tolist(),
                "analyst_p_s": analyst["P"], "analyst_s_s": analyst["S"],
                "m13_p_s": picks["P"], "m13_s_s": picks["S"],
                "m08_p_s": predictions["M08"][row["trace_id"]]["P"],
                "m08_s_s": predictions["M08"][row["trace_id"]]["S"],
            }

    raw_metrics = evaluate_matched_picks(labels, predictions, tolerance_s=TOLERANCE_S)
    noise_count = sum(row["category"] == "noise" for row in valid)
    selected_metrics = {
        method: {phase: _metric_row(raw_metrics[method][phase], noise_count=noise_count)
                 for phase in ("P", "S")}
        for method in ("M08", "M13")
    }
    locked = benchmark["metrics"]["nominal"]
    locked_metrics = {
        method: {phase: locked[method][phase] for phase in ("P", "S")}
        for method in ("M08", "M13")
    }
    result = {
        "schema": "caos.m13-browser-display-subset-analysis.v1",
        "status": "recomputed-23-trace-descriptive-subset; not full benchmark or browser parity",
        "selection_before_heldout_scoring": True,
        "selected_count": 24, "qc_valid_count": len(valid), "qc_rejected_count": len(rejected),
        "noise_valid_count": noise_count,
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "benchmark_sha256": hashlib.sha256(benchmark_bytes).hexdigest(),
        "model_sha256": manifest["model"]["sha256"],
        "checkpoint_sha256": manifest["model"]["checkpoint_sha256"],
        "thresholds": {"P": THRESHOLD, "S": THRESHOLD, "minimum_PS_s": 0.4},
        "analyst_reference_is_ground_truth": False,
        "display_subset_metrics": selected_metrics,
        "locked_6000_test_metrics": locked_metrics,
        "traces": rows,
        "example": example,
        "limitations": [
            "The 23 valid display traces were selected before scoring but are not a representative accuracy sample.",
            "STEAD manual analyst picks are reference times, not geological ground truth.",
            "The selected-subset M08/M13 comparison is descriptive; only the frozen 6,000-trace test table supports the reported aggregate evaluation.",
            "ONNX Runtime CPU inference here does not establish browser WASM parity; the manifest keeps browser_parity_verified=false.",
            "M13 scores are uncalibrated; threshold abstentions are not calibrated uncertainty estimates.",
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, allow_nan=False, separators=(",", ":")), encoding="utf-8")
    return {key: result[key] for key in (
        "status", "selected_count", "qc_valid_count", "qc_rejected_count", "noise_valid_count",
        "manifest_sha256", "model_sha256", "display_subset_metrics",
    )}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", type=Path, default=ROOT / "data/derived/phase/browser-assets/stead")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(process(args.assets, args.output), indent=2))


if __name__ == "__main__":
    main()
