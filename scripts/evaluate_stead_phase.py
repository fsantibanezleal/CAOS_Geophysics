"""Locked M08/M13 evaluation on the untouched real STEAD test split.

Refuses test waveforms without a private checkpoint freeze receipt. Thresholds
are fixed on development data. Public output is aggregate; trace-level picks
remain in ignored private storage.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data-pipeline"))

from extract_stead_phase import _frozen_model_receipt, _members  # noqa: E402
from phase_model import PhaseUNet, SAMPLES, pick_probabilities  # noqa: E402
from phase_picking import classical_stalta_picks, evaluate_matched_picks  # noqa: E402
from stead_phase import file_sha256  # noqa: E402


VARIANTS = ("nominal", "drop_E", "drop_N", "drop_Z", "noise_0p1", "shift_plus_800")


def _variant_batch(base: np.ndarray, trace_ids: list[str], variant: str) -> np.ndarray:
    if variant not in VARIANTS or base.ndim != 3 or base.shape[1:] != (3, SAMPLES):
        raise ValueError("unsupported waveform stress variant or shape")
    changed = np.array(base, copy=True)
    if variant.startswith("drop_"):
        changed[:, "ENZ".index(variant[-1]), :] = 0
    elif variant == "noise_0p1":
        for index, trace_id in enumerate(trace_ids):
            seed = int.from_bytes(hashlib.sha256(
                f"caos-m13-heldout-noise-v1|{trace_id}".encode()).digest()[:8], "big")
            changed[index] += np.random.default_rng(seed).normal(
                0, 0.1, changed[index].shape).astype(np.float32)
    elif variant == "shift_plus_800":
        changed[:, :, 800:] = base[:, :, :-800]
        for index, trace_id in enumerate(trace_ids):
            offset = int.from_bytes(hashlib.sha256(
                f"caos-m13-heldout-shift-v1|{trace_id}".encode()).digest()[:8], "big") % 200
            quiet_indices = (np.arange(800) + offset) % 200
            changed[index, :, :800] = np.take(base[index, :, :200], quiet_indices, axis=1)
    return changed


def _summarize(labels: dict, predictions: dict, *, noise_valid: int) -> dict:
    """Tolerance confusion, timing and valid-noise false-alarm denominator."""
    raw = evaluate_matched_picks(labels, predictions, tolerance_s=0.5)
    report = {}
    for method, phases in raw.items():
        report[method] = {}
        for phase, item in phases.items():
            other_phase = "S" if phase == "P" else "P"
            cross_phase = sum(
                label[other_phase] is not None
                and predictions[method][trace_id][phase] is not None
                and abs(predictions[method][trace_id][phase] - label[other_phase]) <= 0.5
                and (label[phase] is None
                     or abs(predictions[method][trace_id][phase] - label[phase]) > 0.5)
                for trace_id, label in labels.items()
            )
            tp = item["correct_within_tolerance"]
            fp = item["outside_tolerance"] + item["false_without_reference"]
            fn = item["missed"] + item["outside_tolerance"]
            picked = tp + fp
            reference = tp + fn
            signed = np.asarray(item["timing_signed_s"], dtype=np.float64)
            absolute = np.abs(signed)
            report[method][phase] = {
                "reference_count": item["total"],
                "correct_within_0p5s": tp,
                "missed": item["missed"],
                "outside_tolerance": item["outside_tolerance"],
                "false_without_reference": item["false_without_reference"],
                "near_opposite_phase_reference": cross_phase,
                "precision_at_0p5s": tp / picked if picked else None,
                "recall_at_0p5s": tp / reference if reference else None,
                "f1_at_0p5s": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
                "valid_noise_false_pick_rate": (
                    item["false_without_reference"] / noise_valid if noise_valid else None
                ),
                "picked_reference_count": len(signed),
                "timing_bias_median_s": float(np.median(signed)) if len(signed) else None,
                "timing_absolute_median_s": float(np.median(absolute)) if len(absolute) else None,
                "timing_absolute_p90_s": float(np.percentile(absolute, 90)) if len(absolute) else None,
            }
    return report


def _load_locked_test(extraction_dir: Path, manifest: Path, receipt_path: Path,
                      private_root: Path):
    """Validate receipts before mapping any held-out waveform bytes."""
    members, member_hash = _members(manifest, "test")
    index = json.loads((extraction_dir / "stead-test-index.json").read_text(encoding="utf-8"))
    if (index.get("schema") != "caos.stead-phase-local-array.v1"
            or index.get("partition") != "test"
            or index.get("selection_sha256") != member_hash
            or index.get("array_shape") != [len(members), 3, SAMPLES]
            or [row.get("member") for row in index.get("members", [])]
            != [member.__dict__ for member in members]):
        raise ValueError("test array index differs from the metadata-only selection")
    checkpoint_hash = _frozen_model_receipt(
        receipt_path, member_hash=member_hash,
        source_hash=index["waveform_source_sha256"], private_root=private_root,
    )
    if index.get("frozen_checkpoint_sha256") != checkpoint_hash:
        raise ValueError("test extraction was not bound to this exact frozen model")
    array_path = extraction_dir / "stead-test-normalized.npy"
    if file_sha256(array_path) != index.get("array_sha256"):
        raise ValueError("held-out array differs from its QC receipt")
    array = np.load(array_path, mmap_mode="r", allow_pickle=False)
    if array.shape != (len(members), 3, SAMPLES) or array.dtype != np.float32:
        raise ValueError("held-out waveform array shape or dtype differs")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    checkpoint = torch.load(
        receipt_path.parent / receipt["checkpoint_filename"],
        map_location="cpu", weights_only=True,
    )
    model_code_sha256 = hashlib.sha256(
        Path(sys.modules[PhaseUNet.__module__].__file__).read_bytes()).hexdigest()
    if (checkpoint.get("schema") != "caos.phase-picking-checkpoint.v1"
            or checkpoint.get("source_sha256") != index["waveform_source_sha256"]
            or checkpoint.get("chosen_epoch") != receipt["chosen_epoch"]
            or checkpoint.get("model_code_sha256") != model_code_sha256
            or receipt.get("model_code_sha256") != model_code_sha256
            or checkpoint.get("input", {}).get("shape") != [3, SAMPLES]):
        raise ValueError("frozen checkpoint content disagrees with source or receipt")
    return members, index, array, receipt, checkpoint, checkpoint_hash


def evaluate(
    extraction_dir: Path,
    manifest: Path,
    receipt_path: Path,
    report_path: Path,
    private_predictions_path: Path,
    *,
    batch_size: int = 16,
    device_name: str = "cuda",
    private_root: Path = ROOT / "data/raw",
) -> dict:
    if batch_size < 1 or device_name not in ("cuda", "cpu"):
        raise ValueError("invalid batch size or device")
    if device_name == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is unavailable")
    if not report_path.resolve().is_relative_to((ROOT / "data/derived/phase").resolve()):
        raise ValueError("public aggregate report must be under data/derived/phase")
    if not private_predictions_path.resolve().is_relative_to(private_root.resolve()):
        raise ValueError("trace-level picks must stay in ignored private raw storage")
    if report_path.exists() or private_predictions_path.exists():
        raise FileExistsError("held-out evidence already exists; never overwrite it")
    members, index, array, receipt, checkpoint, checkpoint_hash = _load_locked_test(
        extraction_dir, manifest, receipt_path, private_root,
    )
    train_members, _train_hash = _members(manifest, "train")
    train_p = [member.p_index for member in train_members if member.p_index is not None]
    train_s = [member.s_index for member in train_members if member.s_index is not None]
    if not train_p or not train_s:
        raise ValueError("position-only control requires the approved training labels")
    position_prior = {"P": float(np.median(train_p)) * 0.01,
                      "S": float(np.median(train_s)) * 0.01}
    model = PhaseUNet()
    model.load_state_dict(checkpoint["model"], strict=True)
    device = torch.device(device_name)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    model.to(device).eval()
    labels = {member.trace_id: {
        "P": member.p_index * 0.01 if member.p_index is not None else None,
        "S": member.s_index * 0.01 if member.s_index is not None else None,
    } for member in members}
    predictions = {variant: {method: {
        member.trace_id: {"P": None, "S": None} for member in members
    } for method in ("M00", "M08", "M13")} for variant in VARIANTS}
    valid_indices = [i for i, entry in enumerate(index["members"]) if entry.get("valid") is True]
    failures = Counter(entry.get("reason", "unreported") for entry in index["members"]
                       if entry.get("valid") is not True)
    if not valid_indices:
        raise ValueError("no QC-valid real held-out waveforms; no benchmark can be reported")
    private_rows = []
    with torch.inference_mode():
        for start in range(0, len(valid_indices), batch_size):
            indices = valid_indices[start:start + batch_size]
            trace_ids = [members[i].trace_id for i in indices]
            base = np.stack([array[i] for i in indices])
            if not np.all(np.isfinite(base)):
                raise ValueError("QC-valid held-out array contains nonfinite values")
            row_predictions = {trace_id: {} for trace_id in trace_ids}
            for variant in VARIANTS:
                values = _variant_batch(base, trace_ids, variant)
                probabilities = model(torch.from_numpy(values).to(device)).softmax(dim=1).cpu().numpy()
                for local_index, trace_id in enumerate(trace_ids):
                    learned = pick_probabilities(
                        probabilities[local_index],
                        p_threshold=receipt["p_threshold"],
                        s_threshold=receipt["s_threshold"],
                    )
                    classical = classical_stalta_picks(values[local_index].T, sample_interval_s=0.01)
                    predictions[variant]["M00"][trace_id] = position_prior
                    predictions[variant]["M13"][trace_id] = learned
                    predictions[variant]["M08"][trace_id] = classical
                    row_predictions[trace_id][variant] = {
                        "M00": position_prior, "M08": classical, "M13": learned,
                    }
            for trace_id in trace_ids:
                private_rows.append({"trace_id": trace_id, "labels": labels[trace_id],
                                     "variants": row_predictions[trace_id]})
            print(json.dumps({"evaluated": min(start + len(indices), len(valid_indices)),
                              "valid_total": len(valid_indices)}), flush=True)

    noise_valid = sum(members[i].category == "noise" for i in valid_indices)
    shift_eligible = {
        member.trace_id for member in members
        if member.category == "noise"
        or (member.p_index is not None and member.p_index >= 200
            and member.s_index is not None and member.s_index + 800 < SAMPLES)
    }
    metrics = {}
    for variant, methods in predictions.items():
        if variant == "shift_plus_800":
            variant_labels = {trace_id: {
                phase: value + 8.0 if value is not None else None
                for phase, value in labels[trace_id].items()
            } for trace_id in shift_eligible}
            variant_methods = {method: {trace_id: picks[trace_id] for trace_id in shift_eligible}
                               for method, picks in methods.items()}
        else:
            variant_labels, variant_methods = labels, methods
        metrics[variant] = _summarize(variant_labels, variant_methods, noise_valid=noise_valid)
    report = {
        "schema": "caos.stead-phase-heldout-benchmark.v1",
        "status": "computed-on-real-heldout-waveforms",
        "source": "STEAD SeisBench HDF5 mirror; unrestituted instrument counts, CC BY 4.0",
        "waveform_source_sha256": index["waveform_source_sha256"],
        "metadata_selection_sha256": index["selection_sha256"],
        "test_array_sha256": index["array_sha256"],
        "checkpoint_sha256": checkpoint_hash,
        "chosen_epoch": receipt["chosen_epoch"],
        "dev_selected_thresholds": {"P": receipt["p_threshold"], "S": receipt["s_threshold"]},
        "reference": "STEAD manual P/S picks, not geological truth",
        "tolerance_s": 0.5,
        "classical_parameters": {"STA_s": 0.12, "LTA_s": 1.2,
                                 "trigger_ratio": 2.5, "minimum_PS_s": 0.4},
        "position_only_negative_control": {
            "method": "M00", "train_median_P_s": position_prior["P"],
            "train_median_S_s": position_prior["S"],
            "rule": "predict these fixed times on every QC-valid trace, including noise; no waveform input",
        },
        "stress_protocol": {
            "nominal": "original trace-local normalized E/N/Z",
            "drop_E": "E component zero after normalization",
            "drop_N": "N component zero after normalization",
            "drop_Z": "Z component zero after normalization",
            "noise_0p1": "Gaussian sigma 0.1 per normalized sample, trace-ID hash seed",
            "shift_plus_800": "move input 800 samples later with pre-window noise padding from first 200 samples; labels shift by 8 s for eligible records",
        },
        "stress_population": {
            "shift_plus_800": {
                "selected_eligible": len(shift_eligible),
                "selected_excluded_p_before_200_or_s_after_5199": len(members) - len(shift_eligible),
                "eligibility_rule_predeclared": True,
            },
        },
        "selected": len(members), "valid": len(valid_indices),
        "qc_rejected": len(members) - len(valid_indices),
        "qc_rejection_reasons": dict(sorted(failures.items())),
        "noise_valid": noise_valid, "device": device_name,
        "software": {"torch": torch.__version__, "numpy": np.__version__},
        "metrics_include_qc_failures_as_unpicked": True,
        "metrics": metrics,
    }
    groups: dict[str, set[str]] = defaultdict(set)
    for member in members:
        groups[f"network:{member.station_id.split('.', 1)[0]}"].add(member.trace_id)
        groups[f"channel:{member.channel}"].add(member.trace_id)
    report["nominal_strata"] = {}
    valid_ids = {members[i].trace_id for i in valid_indices}
    for name, ids in sorted(groups.items()):
        subset_labels = {key: labels[key] for key in ids}
        subset_predictions = {method: {key: rows[key] for key in ids}
                              for method, rows in predictions["nominal"].items()}
        subset_noise_valid = sum(members[i].trace_id in ids and members[i].category == "noise"
                                 for i in valid_indices)
        report["nominal_strata"][name] = {
            "selected": len(ids), "valid": len(ids & valid_ids),
            "metrics": _summarize(subset_labels, subset_predictions, noise_valid=subset_noise_valid),
        }

    private_predictions_path.parent.mkdir(parents=True, exist_ok=True)
    private_ledger = {
        "schema": "caos.stead-phase-private-predictions.v1",
        "checkpoint_sha256": checkpoint_hash,
        "test_selection_sha256": index["selection_sha256"],
        "rows": private_rows,
        "qc_failures": [{"trace_id": members[i].trace_id, "reason": entry.get("reason")}
                        for i, entry in enumerate(index["members"]) if entry.get("valid") is not True],
    }
    private_predictions_path.write_text(json.dumps(private_ledger, sort_keys=True) + "\n", encoding="utf-8")
    report["private_predictions_sha256"] = file_sha256(private_predictions_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"report_path": str(report_path), "selected": len(members),
            "valid": len(valid_indices), "qc_rejected": report["qc_rejected"],
            "nominal": report["metrics"]["nominal"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extraction-dir", type=Path, default=ROOT / "data/raw/phase/extracted")
    parser.add_argument("--selection-manifest", type=Path,
                        default=ROOT / "data/raw/phase/stead-selection.json")
    parser.add_argument("--frozen-receipt", type=Path, default=ROOT / "data/raw/phase/models/phase-freeze.json")
    parser.add_argument("--report", type=Path,
                        default=ROOT / "data/derived/phase/stead-heldout-benchmark.json")
    parser.add_argument("--private-predictions", type=Path,
                        default=ROOT / "data/raw/phase/models/phase-heldout-predictions.json")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    args = parser.parse_args()
    print(json.dumps(evaluate(
        args.extraction_dir, args.selection_manifest, args.frozen_receipt,
        args.report, args.private_predictions, batch_size=args.batch_size,
        device_name=args.device,
    ), indent=2))


if __name__ == "__main__":
    main()
