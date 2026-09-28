"""Freeze private PyTorch/native-ONNX outputs for real held-out browser parity.

The input is the exact public M13 model and 23 preselected QC-valid binary
traces. Probability arrays stay in ignored storage, not the web application.
This does not execute a browser or establish browser parity by itself.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time

import numpy as np
import onnxruntime as ort
import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data-pipeline"))

from phase_model import PhaseUNet, SAMPLES, pick_probabilities  # noqa: E402
from stead_phase import file_sha256  # noqa: E402


def prepare(assets_dir: Path, frozen_receipt_path: Path, output_dir: Path) -> dict:
    if (not output_dir.resolve().is_relative_to((ROOT / "data/raw").resolve())
            or output_dir.exists() or output_dir.is_symlink()):
        raise ValueError("private browser oracle requires a new ignored output directory")
    assets = json.loads((assets_dir / "manifest.json").read_text(encoding="utf-8"))
    frozen = json.loads(frozen_receipt_path.read_text(encoding="utf-8"))
    if (assets.get("schema") != "caos.phase-browser-assets.v1"
            or assets.get("selection", {}).get("selected_before_heldout_scoring") is not True
            or assets.get("browser_parity_verified") is not False
            or frozen.get("schema") != "caos.phase-freeze.v1"
            or assets.get("model", {}).get("checkpoint_sha256") != frozen.get("checkpoint_sha256")
            or assets.get("selection", {}).get("test_selection_sha256")
            != frozen.get("test_selection_sha256")
            or assets.get("input", {}).get("shape") != [1, 3, SAMPLES]
            or assets.get("output", {}).get("shape") != [1, 3, SAMPLES]
            or assets.get("input", {}).get("file_dtype") != "float32-little-endian"):
        raise ValueError("public assets are not bound to the frozen held-out model/split")
    model_path = assets_dir / assets["model"]["file"]
    if file_sha256(model_path) != assets["model"]["sha256"]:
        raise ValueError("public ONNX model differs from its manifest")
    checkpoint_path = frozen_receipt_path.parent / frozen["checkpoint_filename"]
    if file_sha256(checkpoint_path) != frozen["checkpoint_sha256"]:
        raise ValueError("checkpoint differs from the pre-test freeze")
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    model_code_sha256 = hashlib.sha256(
        Path(sys.modules[PhaseUNet.__module__].__file__).read_bytes(),
    ).hexdigest()
    if (checkpoint.get("model_code_sha256") != model_code_sha256
            or frozen.get("model_code_sha256") != model_code_sha256
            or checkpoint.get("source_sha256") != frozen.get("waveform_source_sha256")):
        raise ValueError("frozen model code or waveform source differs")
    model = PhaseUNet()
    model.load_state_dict(checkpoint["model"], strict=True)
    model.eval()
    session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
    if ([item.name for item in session.get_inputs()] != ["waveform"]
            or [item.name for item in session.get_outputs()] != ["probabilities"]):
        raise ValueError("public ONNX input/output names differ")
    thresholds = assets["model"]["thresholds"]
    records = assets.get("records", [])
    if len(records) != assets["selection"]["selected"]:
        raise ValueError("public record count differs from selection")
    source_valid = [row for row in records if row.get("status") == "qc-valid"]
    source_rejected = [row for row in records if row.get("status") == "qc-rejected"]
    if (len(source_valid) != assets["selection"]["qc_valid"]
            or len(source_rejected) != assets["selection"]["qc_rejected"]
            or any(row.get("waveform_file") for row in source_rejected)):
        raise ValueError("QC-valid and QC-rejected display records differ")
    private_root = ROOT / "data/raw"
    private_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".phase-browser-oracle-", dir=private_root) as temp:
        stage = Path(temp)
        results = []
        maximum_abs = 0.0
        maximum_peak_samples = 0
        native_latency_ms = []
        for row in source_valid:
            path = assets_dir / row["waveform_file"]
            if path.stat().st_size != 3 * SAMPLES * 4 or file_sha256(path) != row["waveform_sha256"]:
                raise ValueError(f"public trace differs: {row['trace_id']}")
            values = np.fromfile(path, dtype="<f4").reshape(1, 3, SAMPLES)
            if not np.all(np.isfinite(values)):
                raise ValueError(f"public trace contains nonfinite samples: {row['trace_id']}")
            with torch.inference_mode():
                torch_prob = model(torch.from_numpy(values)).softmax(dim=1).numpy()[0]
            started = time.perf_counter()
            native_prob = session.run(["probabilities"], {"waveform": values})[0][0]
            native_latency_ms.append((time.perf_counter() - started) * 1000)
            error = float(np.max(np.abs(torch_prob - native_prob)))
            if not np.all(np.isfinite(native_prob)) or error > 0.001:
                raise ValueError(f"native ONNX held-out probability parity failed: {row['trace_id']}")
            torch_picks = pick_probabilities(
                torch_prob, p_threshold=thresholds["P"], s_threshold=thresholds["S"],
            )
            native_picks = pick_probabilities(
                native_prob, p_threshold=thresholds["P"], s_threshold=thresholds["S"],
            )
            for phase in ("P", "S"):
                first, second = torch_picks[phase], native_picks[phase]
                if (first is None) != (second is None):
                    raise ValueError(f"native ONNX changed held-out {phase} abstention")
                if first is not None:
                    maximum_peak_samples = max(maximum_peak_samples, round(abs(first - second) * 100))
            maximum_abs = max(maximum_abs, error)
            filename = row["waveform_file"].replace(".f32", "-torch-probabilities.f32")
            (stage / filename).write_bytes(np.asarray(torch_prob, dtype="<f4").tobytes(order="C"))
            results.append({
                "trace_id": row["trace_id"],
                "waveform_file": row["waveform_file"],
                "waveform_sha256": row["waveform_sha256"],
                "expected_probabilities_file": filename,
                "expected_probabilities_sha256": file_sha256(stage / filename),
                "torch_picks_s": torch_picks,
                "native_picks_s": native_picks,
                "native_max_abs_probability_error": error,
            })
        if maximum_peak_samples > 1:
            raise ValueError("native ONNX held-out peak parity failed")
        receipt = {
            "schema": "caos.phase-browser-private-oracle.v1",
            "status": "native-heldout-parity-only; browser-not-yet-tested",
            "asset_manifest_sha256": file_sha256(assets_dir / "manifest.json"),
            "onnx_sha256": assets["model"]["sha256"],
            "checkpoint_sha256": frozen["checkpoint_sha256"],
            "heldout_selected": assets["selection"]["selected"],
            "heldout_qc_valid": len(source_valid),
            "heldout_qc_rejected": len(source_rejected),
            "native_max_abs_probability_error": maximum_abs,
            "native_max_peak_time_error_samples": maximum_peak_samples,
            "native_cpu_latency_median_ms": float(np.median(native_latency_ms)),
            "native_cpu_latency_p90_ms": float(np.percentile(native_latency_ms, 90)),
            "records": results,
        }
        (stage / "receipt.json").write_bytes(
            (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        )
        stage.rename(output_dir)
    return {key: receipt[key] for key in (
        "status", "asset_manifest_sha256", "onnx_sha256", "heldout_selected",
        "heldout_qc_valid", "heldout_qc_rejected", "native_max_abs_probability_error",
        "native_max_peak_time_error_samples",
    )}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", type=Path,
                        default=ROOT / "data/derived/phase/browser-assets/stead")
    parser.add_argument("--frozen-receipt", type=Path,
                        default=ROOT / "data/raw/phase/models-amp2/phase-freeze.json")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "data/raw/phase/models-amp2/browser-parity")
    args = parser.parse_args()
    print(json.dumps(prepare(args.assets, args.frozen_receipt, args.output), indent=2))


if __name__ == "__main__":
    main()
