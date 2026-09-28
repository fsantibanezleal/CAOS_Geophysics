"""Screen the frozen M13 checkpoint on development data before opening test.

These metrics are not held-out evidence: the same development set selected the
epoch and P/S thresholds. The purpose is to detect gross clock-prior or
classical-baseline failure before the sealed test waveforms are extracted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data-pipeline"))

from evaluate_stead_phase import _summarize, _variant_batch  # noqa: E402
from extract_stead_phase import _members  # noqa: E402
from phase_model import PhaseUNet, pick_probabilities  # noqa: E402
from phase_picking import classical_stalta_picks  # noqa: E402
from stead_phase import file_sha256  # noqa: E402
from train_stead_phase import ExtractedPhaseDataset  # noqa: E402


def profile(extraction_dir: Path, manifest: Path, freeze_path: Path, report_path: Path,
            *, device_name: str = "cpu", batch_size: int = 16) -> dict:
    if device_name not in ("cpu", "cuda") or batch_size < 1:
        raise ValueError("unsupported development profile device or batch size")
    if device_name == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable")
    if (not report_path.resolve().is_relative_to((ROOT / "data/raw").resolve())
            or report_path.exists() or report_path.is_symlink()):
        raise ValueError("development profile must be a new private data/raw receipt")
    if (not freeze_path.resolve().is_relative_to((ROOT / "data/raw").resolve())
            or not freeze_path.is_file() or freeze_path.is_symlink()):
        raise ValueError("frozen checkpoint receipt must remain private")
    train = ExtractedPhaseDataset(extraction_dir, "train")
    dev = ExtractedPhaseDataset(extraction_dir, "dev")
    selected_train, _ = _members(manifest, "train")
    selected_dev, dev_hash = _members(manifest, "dev")
    if (train.index["waveform_source_sha256"] != dev.index["waveform_source_sha256"]
            or dev.index["selection_sha256"] != dev_hash
            or [row["member"] for row in dev.index["members"]]
            != [member.__dict__ for member in selected_dev]):
        raise ValueError("development arrays differ from the frozen selection")
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if (freeze.get("schema") != "caos.phase-freeze.v1"
            or freeze.get("frozen_before_test") is not True
            or freeze.get("waveform_source_sha256") != dev.index["waveform_source_sha256"]
            or freeze.get("dev_valid") != len(dev)
            or not isinstance(freeze.get("checkpoint_filename"), str)):
        raise ValueError("frozen checkpoint does not bind this development source")
    checkpoint_path = freeze_path.parent / freeze["checkpoint_filename"]
    if (checkpoint_path.name != freeze["checkpoint_filename"]
            or checkpoint_path.is_symlink()
            or file_sha256(checkpoint_path) != freeze.get("checkpoint_sha256")):
        raise ValueError("frozen checkpoint bytes differ")
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    model_code_sha256 = hashlib.sha256(
        Path(sys.modules[PhaseUNet.__module__].__file__).read_bytes()).hexdigest()
    if (checkpoint.get("schema") != "caos.phase-picking-checkpoint.v1"
            or checkpoint.get("dev_selection_sha256") != dev_hash
            or checkpoint.get("model_code_sha256") != model_code_sha256
            or freeze.get("model_code_sha256") != model_code_sha256):
        raise ValueError("checkpoint model or development split differs")
    model = PhaseUNet()
    model.load_state_dict(checkpoint["model"], strict=True)
    model.to(device_name).eval()
    train_p = [member.p_index for member in selected_train if member.p_index is not None]
    train_s = [member.s_index for member in selected_train if member.s_index is not None]
    position_prior = {"P": float(np.median(train_p)) * 0.01,
                      "S": float(np.median(train_s)) * 0.01}
    labels = {member.trace_id: {
        "P": member.p_index * 0.01 if member.p_index is not None else None,
        "S": member.s_index * 0.01 if member.s_index is not None else None,
    } for member in selected_dev}
    variants = ("nominal", "shift_plus_800")
    predictions = {variant: {method: {member.trace_id: {"P": None, "S": None}
                                     for member in selected_dev}
                             for method in ("M00", "M08", "M13")}
                   for variant in variants}
    eligible_shift = {member.trace_id for member in selected_dev
                      if member.category == "noise"
                      or (member.p_index is not None and member.p_index >= 200
                          and member.s_index is not None and member.s_index + 800 < 6000)}
    with torch.inference_mode():
        for start in range(0, len(dev.valid_indices), batch_size):
            indices = dev.valid_indices[start:start + batch_size]
            values = np.stack([dev.array[index] for index in indices])
            trace_ids = [selected_dev[index].trace_id for index in indices]
            for variant in variants:
                shifted = _variant_batch(values, trace_ids, variant)
                probabilities = model(torch.from_numpy(shifted).to(device_name)).softmax(dim=1).cpu().numpy()
                for offset, trace_id in enumerate(trace_ids):
                    predictions[variant]["M00"][trace_id] = position_prior
                    predictions[variant]["M08"][trace_id] = classical_stalta_picks(
                        shifted[offset].T, sample_interval_s=0.01,
                    )
                    predictions[variant]["M13"][trace_id] = pick_probabilities(
                        probabilities[offset], p_threshold=freeze["p_threshold"],
                        s_threshold=freeze["s_threshold"],
                    )
    noise_valid = sum(selected_dev[index].category == "noise" for index in dev.valid_indices)
    shifted_labels = {trace_id: {phase: value + 8 if value is not None else None
                                 for phase, value in labels[trace_id].items()}
                      for trace_id in eligible_shift}
    shifted_predictions = {method: {trace_id: picks[trace_id] for trace_id in eligible_shift}
                           for method, picks in predictions["shift_plus_800"].items()}
    report = {
        "schema": "caos.stead-phase-development-screen.v1",
        "status": "development-only-not-independent-heldout",
        "checkpoint_sha256": freeze["checkpoint_sha256"],
        "waveform_source_sha256": dev.index["waveform_source_sha256"],
        "dev_array_sha256": dev.index["array_sha256"],
        "dev_selection_sha256": dev_hash,
        "selected": len(selected_dev), "valid": len(dev),
        "qc_rejected": len(selected_dev) - len(dev),
        "noise_valid": noise_valid,
        "dev_selected_thresholds": {"P": freeze["p_threshold"], "S": freeze["s_threshold"]},
        "input_free_train_position_control_s": position_prior,
        "shift_plus_800_eligible": len(eligible_shift),
        "nominal": _summarize(labels, predictions["nominal"], noise_valid=noise_valid),
        "shift_plus_800": _summarize(shifted_labels, shifted_predictions,
                                     noise_valid=noise_valid),
        "test_waveforms_opened": False,
        "independent_accuracy_claim": False,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extraction-dir", type=Path,
                        default=ROOT / "data/raw/phase/extracted")
    parser.add_argument("--manifest", type=Path,
                        default=ROOT / "data/raw/phase/stead-selection.json")
    parser.add_argument("--frozen-receipt", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args()
    result = profile(args.extraction_dir, args.manifest, args.frozen_receipt,
                     args.report, device_name=args.device, batch_size=args.batch_size)
    print(json.dumps({"report": str(args.report), "status": result["status"],
                      "nominal": result["nominal"], "shift_plus_800": result["shift_plus_800"]},
                     indent=2))


if __name__ == "__main__":
    main()
