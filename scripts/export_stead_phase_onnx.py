"""Export the frozen M13 checkpoint to private ONNX and verify native parity.

This command uses development waveforms only. It does not open the held-out
test array, publish a model or assert browser parity. A later browser gate
must use this exact model hash on rights-cleared held-out real traces.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time

import numpy as np
import onnx
import onnxruntime as ort
import torch
from torch import nn


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data-pipeline"))

from phase_model import PhaseUNet, SAMPLES, pick_probabilities  # noqa: E402
from stead_phase import file_sha256  # noqa: E402
from train_stead_phase import ExtractedPhaseDataset  # noqa: E402


class PhaseProbabilities(nn.Module):
    """One-trace, fixed-window N/P/S probabilities for the browser runtime."""

    def __init__(self, model: PhaseUNet):
        super().__init__()
        self.model = model

    def forward(self, waveform: torch.Tensor) -> torch.Tensor:
        return self.model(waveform).softmax(dim=1)


def _parity(model: PhaseProbabilities, session: ort.InferenceSession,
            dataset: ExtractedPhaseDataset, *, p_threshold: float,
            s_threshold: float, sample_count: int) -> dict:
    if sample_count < 1 or len(dataset) < sample_count:
        raise ValueError("not enough QC-valid development traces for ONNX parity")
    ordered = sorted(range(len(dataset)), key=lambda i: hashlib.sha256(
        f"caos-phase-onnx-dev-v1|{dataset.index['members'][dataset.valid_indices[i]]['member']['trace_id']}"
        .encode()).digest())[:sample_count]
    selected_ids = []
    absolute_max = 0.0
    peak_sample_max = 0
    latencies_ms = []
    for index in ordered:
        values, _p, _s, trace_id = dataset[index]
        selected_ids.append(trace_id)
        waveform = values.unsqueeze(0).numpy()
        with torch.inference_mode():
            canonical = model(values.unsqueeze(0)).detach().numpy()[0]
        started = time.perf_counter()
        exported = session.run(["probabilities"], {"waveform": waveform})[0]
        latencies_ms.append((time.perf_counter() - started) * 1000)
        if exported.shape != (1, 3, SAMPLES):
            raise ValueError("ONNX output has the wrong N/P/S sample shape")
        exported = exported[0]
        if not np.all(np.isfinite(exported)) or not np.allclose(exported.sum(axis=0), 1, atol=1e-4):
            raise ValueError("ONNX probabilities are nonfinite or not normalized")
        absolute_max = max(absolute_max, float(np.max(np.abs(canonical - exported))))
        first = pick_probabilities(canonical, p_threshold=p_threshold, s_threshold=s_threshold)
        second = pick_probabilities(exported, p_threshold=p_threshold, s_threshold=s_threshold)
        for phase in ("P", "S"):
            if (first[phase] is None) != (second[phase] is None):
                raise ValueError("ONNX changed a dev-set phase abstention")
            if first[phase] is not None:
                peak_sample_max = max(peak_sample_max, round(abs(first[phase] - second[phase]) / 0.01))
    if absolute_max > 0.001 or peak_sample_max > 1:
        raise ValueError("native ONNX probability/peak parity failed")
    return {
        "dev_trace_count": len(ordered),
        "dev_trace_ids_sha256": hashlib.sha256("\n".join(sorted(selected_ids)).encode()).hexdigest(),
        "max_probability_absolute_error": absolute_max,
        "max_peak_time_error_samples": peak_sample_max,
        "native_cpu_latency_median_ms": float(np.median(latencies_ms)),
        "native_cpu_latency_p90_ms": float(np.percentile(latencies_ms, 90)),
    }


def export(
    extraction_dir: Path,
    freeze_receipt: Path,
    output_dir: Path,
    *,
    sample_count: int = 16,
    private_root: Path = ROOT / "data/raw",
) -> dict:
    output_dir = output_dir.resolve()
    if not output_dir.is_relative_to(private_root.resolve()):
        raise ValueError("unvalidated ONNX export must remain in ignored private raw storage")
    target = output_dir / "phase-model.onnx"
    receipt_path = output_dir / "phase-onnx-dev-parity.json"
    if target.exists() or receipt_path.exists():
        raise FileExistsError("ONNX export or parity receipt already exists; do not overwrite")
    if (not freeze_receipt.resolve().is_relative_to(private_root.resolve())
            or not freeze_receipt.is_file() or freeze_receipt.is_symlink()):
        raise ValueError("private checkpoint freeze receipt is missing")
    freeze = json.loads(freeze_receipt.read_text(encoding="utf-8"))
    filename = freeze.get("checkpoint_filename")
    if (freeze.get("schema") != "caos.phase-freeze.v1"
            or freeze.get("frozen_before_test") is not True
            or not isinstance(filename, str) or filename != Path(filename).name
            or not filename.endswith(".pt")):
        raise ValueError("checkpoint freeze receipt is invalid")
    checkpoint_path = freeze_receipt.parent / filename
    if file_sha256(checkpoint_path) != freeze.get("checkpoint_sha256"):
        raise ValueError("frozen checkpoint hash differs")
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    model_code_sha256 = hashlib.sha256(
        Path(sys.modules[PhaseUNet.__module__].__file__).read_bytes()).hexdigest()
    if (checkpoint.get("schema") != "caos.phase-picking-checkpoint.v1"
            or checkpoint.get("source_sha256") != freeze.get("waveform_source_sha256")
            or checkpoint.get("chosen_epoch") != freeze.get("chosen_epoch")
            or checkpoint.get("model_code_sha256") != model_code_sha256
            or freeze.get("model_code_sha256") != model_code_sha256
            or checkpoint.get("input", {}).get("shape") != [3, SAMPLES]):
        raise ValueError("checkpoint content differs from the freeze receipt")
    dataset = ExtractedPhaseDataset(extraction_dir, "dev")
    if (dataset.index.get("selection_sha256") != checkpoint.get("dev_selection_sha256")
            or dataset.index.get("waveform_source_sha256") != freeze.get("waveform_source_sha256")):
        raise ValueError("development array is not the checkpoint's source/split")
    model = PhaseUNet()
    model.load_state_dict(checkpoint["model"], strict=True)
    wrapper = PhaseProbabilities(model.eval()).eval()
    output_dir.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".phase-export-", suffix=".onnx", dir=output_dir)
    os.close(fd)
    stage = Path(temp_name)
    stage_receipt: Path | None = None
    try:
        sample = torch.zeros((1, 3, SAMPLES), dtype=torch.float32)
        torch.onnx.export(
            wrapper, (sample,), stage,
            input_names=["waveform"], output_names=["probabilities"],
            opset_version=18, dynamo=True, external_data=False,
            optimize=True,
        )
        onnx.checker.check_model(str(stage))
        session = ort.InferenceSession(str(stage), providers=["CPUExecutionProvider"])
        parity = _parity(
            wrapper, session, dataset,
            p_threshold=freeze["p_threshold"], s_threshold=freeze["s_threshold"],
            sample_count=sample_count,
        )
        receipt = {
            "schema": "caos.phase-onnx-dev-parity.v1",
            "status": "native-onnx-dev-parity-only",
            "checkpoint_sha256": freeze["checkpoint_sha256"],
            "waveform_source_sha256": freeze["waveform_source_sha256"],
            "dev_array_sha256": dataset.index["array_sha256"],
            "onnx_sha256": file_sha256(stage),
            "onnx_bytes": stage.stat().st_size,
            "opset": 18,
            "input": {"name": "waveform", "shape": [1, 3, SAMPLES], "component_order": "ENZ"},
            "output": {"name": "probabilities", "shape": [1, 3, SAMPLES], "classes": ["N", "P", "S"]},
            "thresholds": {"P": freeze["p_threshold"], "S": freeze["s_threshold"]},
            "parity": parity,
            "software": {"torch": torch.__version__, "onnx": onnx.__version__,
                         "onnxruntime": ort.__version__},
            "heldout_test_opened": False,
            "browser_parity_claim": False,
        }
        fd, receipt_name = tempfile.mkstemp(prefix=".phase-onnx-receipt-", suffix=".json", dir=output_dir)
        os.close(fd)
        stage_receipt = Path(receipt_name)
        stage_receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        os.link(stage, target)
        os.link(stage_receipt, receipt_path)
        return receipt
    finally:
        stage.unlink(missing_ok=True)
        if stage_receipt is not None:
            stage_receipt.unlink(missing_ok=True)


def main() -> None:
    # PyTorch's exporter prints Unicode status glyphs even with verbose=False.
    # A legacy Windows console may use cp1252; escape unsupported glyphs in
    # progress text instead of aborting a mathematically valid export.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extraction-dir", type=Path, default=ROOT / "data/raw/phase/extracted")
    parser.add_argument("--frozen-receipt", type=Path, default=ROOT / "data/raw/phase/models/phase-freeze.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/raw/phase/models")
    parser.add_argument("--sample-count", type=int, default=16)
    args = parser.parse_args()
    result = export(args.extraction_dir, args.frozen_receipt, args.output_dir,
                    sample_count=args.sample_count)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
