"""Export the frozen M12 physics-v2 checkpoint to the browser ONNX runtime.

This converts an existing checkpoint. It never trains, selects weights, or
changes the scientific comparator result. A receipt is written beside the
model only after full cohort parity with the source PyTorch model is checked.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data-pipeline"))

import velocity_physics_refinement as refinement  # noqa: E402
import velocity_validation as operators  # noqa: E402


MODEL_DIR = ROOT / "models/experimental/m12-physics-cuda-20261004"
CHECKPOINT = MODEL_DIR / "m12-physics.npz"
TRAINING_RECEIPT = MODEL_DIR / "receipt.json"
DEFAULT_OUTPUT = MODEL_DIR / "m12-physics.onnx"
OUTPUT_RECEIPT = MODEL_DIR / "m12-physics-browser-receipt.json"
SCHEMA = "geophysics.m12-browser-model/v1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export(output: Path) -> dict:
    import onnx
    import onnxruntime as ort
    import torch

    training = json.loads(TRAINING_RECEIPT.read_text(encoding="utf-8"))
    if (training.get("schema") != "geophysics.m12-physics/v2"
            or training.get("status") == "fixture-only"
            or training.get("epochs") != 40
            or sha256(CHECKPOINT) != training.get("checkpoint_sha256")
            or training.get("code_sha256") != refinement.LEGACY_V2_TRAINING_SOURCE_SHA256
            or sha256(ROOT / "data-pipeline/velocity_validation.py") != training.get("operator_code_sha256")):
        raise ValueError("The frozen M12 checkpoint or its source receipt is not the reviewed physics-v2 experiment")
    receipt_path = OUTPUT_RECEIPT if output == DEFAULT_OUTPUT.resolve() else output.with_name(
        f"{output.stem}-browser-receipt.json")
    if output.exists() or receipt_path.exists():
        raise FileExistsError("Refuse to overwrite an existing browser model or receipt")

    torch.set_num_threads(4)
    torch.manual_seed(0)
    model = refinement.load_checkpoint(CHECKPOINT, training["checkpoint_sha256"], device="cpu")
    output.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        model,
        torch.zeros((1, 2, 16, 16), dtype=torch.float32),
        output,
        input_names=["features"],
        output_names=["velocity_m_s"],
        opset_version=18,
        dynamic_axes={"features": {0: "batch"}, "velocity_m_s": {0: "batch"}},
        dynamo=False,
    )
    graph = onnx.load(output)
    onnx.checker.check_model(graph, full_check=True)
    session = ort.InferenceSession(str(output), providers=["CPUExecutionProvider"])
    if ([i.name for i in session.get_inputs()] != ["features"]
            or [o.name for o in session.get_outputs()] != ["velocity_m_s"]
            or session.get_inputs()[0].shape != ["batch", 2, 16, 16]
            or session.get_outputs()[0].shape != ["batch", 16, 16]):
        raise ValueError("Exported ONNX input/output contract differs from the browser adapter")

    cohorts = {}
    maximum_error = 0.0
    ops = operators.operators()
    for name in ("validation", "id_test", "family_only", "acquisition_only", "joint_ood"):
        cohort = refinement.make_cohort(name, ops)
        features = np.asarray(cohort["features"], dtype=np.float32)
        with torch.inference_mode():
            expected = model(torch.from_numpy(features)).cpu().numpy()
        actual = session.run(["velocity_m_s"], {"features": features})[0]
        if actual.shape != expected.shape or not np.isfinite(actual).all():
            raise ValueError(f"Invalid ONNX output for cohort {name}")
        error = np.abs(actual - expected)
        maximum_error = max(maximum_error, float(error.max()))
        cohorts[name] = {
            "records": len(features),
            "max_absolute_error_m_s": float(error.max()),
            "rmse_of_export_difference_m_s": float(np.sqrt(np.mean(error ** 2))),
            "input_manifest_sha256": cohort["manifest_sha256"],
        }
    record = {
        "schema": SCHEMA,
        "status": "parity-verified",
        "model": {"file": output.name, "bytes": output.stat().st_size, "sha256": sha256(output)},
        "checkpoint": {"file": CHECKPOINT.relative_to(ROOT).as_posix(), "sha256": training["checkpoint_sha256"]},
        "training": {
            "receipt_sha256": sha256(TRAINING_RECEIPT),
            "source_sha256": training["code_sha256"],
            "operator_source_sha256": training["operator_code_sha256"],
            "status": training["status"],
            "protocol": "m12-physics/v2",
            "scientific_verdict": "failed-held-out-comparator",
            "selection": "frozen-checkpoint; no retraining or reselection during export",
        },
        "runtime": {
            "exporter": "PyTorch TorchScript ONNX exporter",
            "pytorch": torch.__version__,
            "onnx": onnx.__version__,
            "onnxruntime": ort.__version__,
            "opset": 18,
            "input": {"name": "features", "dtype": "float32", "shape": ["batch", 2, 16, 16]},
            "output": {"name": "velocity_m_s", "dtype": "float32", "shape": ["batch", 16, 16]},
            "browser_execution_provider": "wasm",
            "device_used_for_parity": "CPUExecutionProvider",
            "python": platform.python_version(),
        },
        "parity": {
            "records": sum(item["records"] for item in cohorts.values()),
            "cohorts": cohorts,
            "max_absolute_error_m_s": maximum_error,
            "acceptance_tolerance_m_s": 0.002,
            "passed": maximum_error <= 0.002,
            "training_and_test_inputs": "reconstructed from frozen disjoint manifests; metrics were not used for selection",
        },
        "limitations": [
            "Synthetic training only; no field accuracy or generalization claim.",
            "The original held-out joint comparator failed; the CNN is exposed only as an exploratory alternative.",
            "Fixed local 800 m by 800 m domain and 16 by 16 grid; straight-ray input features.",
            "Unsupported cells remain prior-dominated network output and are marked by a separate support mask.",
            "ONNX parity certifies format conversion only, not physical correctness or scientific acceptance.",
        ],
    }
    if not record["parity"]["passed"]:
        raise ValueError("ONNX conversion parity exceeds the 0.002 m/s cap")
    receipt_path.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = export(args.output.resolve())
    print(json.dumps({"status": result["status"], "records": result["parity"]["records"],
                      "max_absolute_error_m_s": result["parity"]["max_absolute_error_m_s"],
                      "model": result["model"]}, indent=2))


if __name__ == "__main__":
    main()
