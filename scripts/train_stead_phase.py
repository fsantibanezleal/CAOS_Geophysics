"""Train an original PhaseNet-family picker on verified real STEAD partitions.

The ignored train/dev arrays must have been extracted from a fully hashed
waveform source. Test waveforms are neither read nor opened by this script.
This command requires CUDA; it never runs in CI or during a web build.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import random
import sys
import tempfile

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data-pipeline"))

from phase_model import (  # noqa: E402
    PhaseUNet, SAMPLES, gaussian_targets,
    weighted_soft_cross_entropy,
)
from stead_phase import file_sha256  # noqa: E402


class ExtractedPhaseDataset(Dataset):
    """Valid rows only; QC failures remain in the private index and denominator."""

    def __init__(self, root: Path, partition: str, *, verify_hash: bool = True):
        if partition not in ("train", "dev"):
            raise ValueError("training may open train and dev only; test remains frozen")
        self.partition = partition
        self.array_path = root / f"stead-{partition}-normalized.npy"
        index_path = root / f"stead-{partition}-index.json"
        self.index = json.loads(index_path.read_text(encoding="utf-8"))
        if (self.index.get("schema") != "caos.stead-phase-local-array.v1"
                or self.index.get("partition") != partition
                or self.index.get("array_shape", [None])[1:] != [3, SAMPLES]
                or not isinstance(self.index.get("members"), list)):
            raise ValueError("private extracted array index is incompatible with M13")
        if verify_hash and file_sha256(self.array_path) != self.index["array_sha256"]:
            raise ValueError("private extracted array differs from its QC hash")
        self.array = np.load(self.array_path, mmap_mode="r")
        if self.array.shape != tuple(self.index["array_shape"]) or self.array.dtype != np.float32:
            raise ValueError("private extracted array shape or dtype drifted")
        if len(self.index["members"]) != len(self.array):
            raise ValueError("QC index and extracted rows differ")
        self.valid_indices = [index for index, row in enumerate(self.index["members"]) if row["valid"] is True]
        if not self.valid_indices:
            raise ValueError("no QC-valid real traces in partition")

    def __len__(self) -> int:
        return len(self.valid_indices)

    def __getitem__(self, index: int):
        source_index = self.valid_indices[index]
        record = self.index["members"][source_index]["member"]
        values = np.array(self.array[source_index], copy=True)
        if not np.all(np.isfinite(values)):
            raise ValueError("nonfinite extracted waveform")
        p_index = record["p_index"] if record["p_index"] is not None else -1
        s_index = record["s_index"] if record["s_index"] is not None else -1
        return torch.from_numpy(values), int(p_index), int(s_index), record["trace_id"]


def _augment_shift(values: torch.Tensor, p: torch.Tensor, s: torch.Tensor,
                   generator: torch.Generator) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Train-only broad translation, padding solely from pre-event quiet samples.

    STEAD puts essentially every P in samples 400..1000. A narrow jitter would
    let the network memorize clock position. Use analyst labels only to keep
    both phases within [100, 5900]; they are never passed to inference.
    """
    output = values.clone()
    p = p.clone()
    s = s.clone()
    for index in range(len(values)):
        if p[index] >= 0:
            minimum = 100 - int(p[index])
            maximum = SAMPLES - 101 - int(s[index])
            if minimum > maximum:
                raise ValueError("training phases leave no valid translated window")
        else:
            minimum, maximum = -2000, 2000
        shift = int(torch.randint(minimum, maximum + 1, (1,), generator=generator))
        quiet_length = max(32, min(200, int(p[index]) // 2 if p[index] >= 0 else 200))
        phase_offset = int(torch.randint(0, quiet_length, (1,), generator=generator))
        if shift > 0:
            output[index, :, shift:] = values[index, :, :-shift]
            quiet_indices = (torch.arange(shift) + phase_offset) % quiet_length
            output[index, :, :shift] = values[index, :, quiet_indices]
        elif shift < 0:
            amount = -shift
            output[index, :, :-amount] = values[index, :, amount:]
            quiet_indices = (torch.arange(amount) + phase_offset) % quiet_length
            output[index, :, -amount:] = values[index, :, quiet_indices]
        if p[index] >= 0:
            p[index] += shift
            s[index] += shift
    return output, p, s


def _dev_summary(model: PhaseUNet, loader: DataLoader, device: torch.device):
    model.eval()
    loss_sum = 0.0
    sample_count = 0
    rows: list[dict] = []
    with torch.no_grad():
        for values, p, s, trace_ids in loader:
            logits = model(values.to(device, non_blocking=True))
            target = gaussian_targets(p.to(device), s.to(device))
            loss_sum += float(weighted_soft_cross_entropy(logits, target)) * len(values)
            sample_count += len(values)
            probability = logits.softmax(dim=1).cpu().numpy()
            for index, trace_id in enumerate(trace_ids):
                rows.append({"id": trace_id, "p": int(p[index]), "s": int(s[index]),
                             "p_max": float(probability[index, 1].max()),
                             "p_argmax": int(probability[index, 1].argmax()),
                             "s_max": float(probability[index, 2].max()),
                             "s_argmax": int(probability[index, 2].argmax())})
    if sample_count == 0:
        raise ValueError("development loader contains no QC-valid traces")
    return loss_sum / sample_count, rows


def _score_rows(rows: list[dict], p_threshold: float, s_threshold: float) -> dict:
    counts = {"P": {"tp": 0, "fp": 0, "fn": 0}, "S": {"tp": 0, "fp": 0, "fn": 0}}
    for row in rows:
        p_pick = row["p_argmax"] if row["p_max"] >= p_threshold else None
        s_pick = row["s_argmax"] if row["s_max"] >= s_threshold else None
        if p_pick is not None and s_pick is not None and s_pick - p_pick < 40:
            s_pick = None
        for phase, pick in (("P", p_pick), ("S", s_pick)):
            truth = row[phase.lower()]
            item = counts[phase]
            if truth < 0:
                item["fp"] += int(pick is not None)
            elif pick is None:
                item["fn"] += 1
            elif abs(pick - truth) <= 50:  # 0.5 s at 100 Hz; fixed before test
                item["tp"] += 1
            else:
                item["fp"] += 1
                item["fn"] += 1
    f1 = {}
    for phase, item in counts.items():
        denominator = 2 * item["tp"] + item["fp"] + item["fn"]
        f1[phase] = (2 * item["tp"] / denominator) if denominator else 0.0
    return {"macro_f1": (f1["P"] + f1["S"]) / 2, "phase_f1": f1, "counts": counts}


def select_dev_thresholds(rows: list[dict]) -> dict:
    if not rows:
        raise ValueError("development set has no real traces")
    best: dict | None = None
    for p_step in range(1, 10):
        for s_step in range(1, 10):
            p_threshold, s_threshold = p_step / 10, s_step / 10
            score = _score_rows(rows, p_threshold, s_threshold)
            candidate = {"p_threshold": p_threshold, "s_threshold": s_threshold, **score}
            # Conservative tie break: higher thresholds mean fewer noise false picks.
            if best is None or (candidate["macro_f1"], p_threshold + s_threshold) > (
                best["macro_f1"], best["p_threshold"] + best["s_threshold"]
            ):
                best = candidate
    assert best is not None
    return best


def _selection_hashes(path: Path, train: ExtractedPhaseDataset, dev: ExtractedPhaseDataset) -> str:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema") != "caos.stead-phase-members.v1":
        raise ValueError("selection manifest schema differs")
    selected = document["report"]["selected"]
    if (selected["train"]["ids_sha256"] != train.index["selection_sha256"]
            or selected["dev"]["ids_sha256"] != dev.index["selection_sha256"]
            or train.index["waveform_source_sha256"] != dev.index["waveform_source_sha256"]):
        raise ValueError("train/dev arrays do not bind the same approved source and split")
    return selected["test"]["ids_sha256"]


def _save_resume_state(path: Path, state: dict) -> None:
    """Replace only this script's private per-epoch continuation checkpoint."""
    fd, name = tempfile.mkstemp(prefix=".phase-train-", suffix=".pt", dir=path.parent)
    os.close(fd)
    staged = Path(name)
    try:
        torch.save(state, staged)
        os.replace(staged, path)
    finally:
        staged.unlink(missing_ok=True)


def train(
    extraction_dir: Path,
    selection_manifest: Path,
    output_dir: Path,
    *,
    epochs: int = 12,
    batch_size: int = 16,
    seed: int = 41027,
    resume: bool = False,
) -> dict:
    if not torch.cuda.is_available():
        raise RuntimeError("real STEAD model training requires the local CUDA GPU")
    if epochs < 2 or batch_size < 1:
        raise ValueError("training requires at least two epochs and positive batch size")
    output_dir = output_dir.resolve()
    if not output_dir.is_relative_to((ROOT / "data/raw").resolve()):
        raise ValueError("checkpoints and training ledger must stay in ignored data/raw/")
    checkpoint_path = output_dir / "phase-model.pt"
    receipt_path = output_dir / "phase-freeze.json"
    resume_path = output_dir / "phase-resume-state.pt"
    if checkpoint_path.exists() or receipt_path.exists():
        raise FileExistsError("training output exists; never overwrite a frozen model")
    if resume_path.is_symlink():
        raise ValueError("private training continuation state cannot be a symlink")
    if resume and not resume_path.is_file():
        raise FileNotFoundError("resume requested but no private per-epoch state exists")
    if not resume and resume_path.exists():
        raise FileExistsError("per-epoch state exists; use --resume after verifying it")
    train_set = ExtractedPhaseDataset(extraction_dir, "train")
    dev_set = ExtractedPhaseDataset(extraction_dir, "dev")
    test_selection_hash = _selection_hashes(selection_manifest, train_set, dev_set)
    torch.manual_seed(seed)
    np.random.seed(seed)
    random.seed(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    device = torch.device("cuda")
    generator = torch.Generator().manual_seed(seed)
    train_loader = DataLoader(train_set, batch_size=batch_size, shuffle=True,
                              generator=generator, num_workers=0, pin_memory=True)
    dev_loader = DataLoader(dev_set, batch_size=batch_size, shuffle=False,
                            num_workers=0, pin_memory=True)
    model = PhaseUNet().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-4, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    scaler = torch.amp.GradScaler("cuda")
    code_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    model_code_sha256 = hashlib.sha256(
        Path(sys.modules[PhaseUNet.__module__].__file__).read_bytes()).hexdigest()
    config = {"epochs": epochs, "batch_size": batch_size, "seed": seed,
              "source_sha256": train_set.index["waveform_source_sha256"],
              "train_selection_sha256": train_set.index["selection_sha256"],
              "dev_selection_sha256": dev_set.index["selection_sha256"],
              "test_selection_sha256": test_selection_hash,
              "code_sha256": code_sha256, "model_code_sha256": model_code_sha256,
              "torch": str(torch.__version__)}
    best_loss = float("inf")
    best_state = None
    chosen_epoch = 0
    history: list[dict] = []
    start_epoch = 1
    output_dir.mkdir(parents=True, exist_ok=True)
    if resume:
        state = torch.load(resume_path, map_location="cpu", weights_only=True)
        if state.get("schema") != "caos.phase-train-resume.v1" or state.get("config") != config:
            raise ValueError("private training state differs from code, source, split or hyperparameters")
        model.load_state_dict(state["model"], strict=True)
        optimizer.load_state_dict(state["optimizer"])
        scheduler.load_state_dict(state["scheduler"])
        scaler.load_state_dict(state["scaler"])
        best_loss = state["best_loss"]
        best_state = state["best_state"]
        chosen_epoch = state["chosen_epoch"]
        history = state["history"]
        start_epoch = state["epoch"] + 1
        if start_epoch < 2 or start_epoch > epochs + 1 or len(history) != start_epoch - 1:
            raise ValueError("private training state has an invalid epoch history")
        generator.set_state(state["loader_rng"])
        torch.set_rng_state(state["torch_cpu_rng"])
        torch.cuda.set_rng_state_all(state["torch_cuda_rng"])
        random.setstate(state["python_rng"])
    for epoch in range(start_epoch, epochs + 1):
        model.train()
        epoch_losses = []
        for values, p, s, _trace_ids in train_loader:
            values, p, s = _augment_shift(values, p, s, generator)
            values = values.to(device, non_blocking=True)
            p = p.to(device)
            s = s.to(device)
            target = gaussian_targets(p, s)
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast("cuda", dtype=torch.float16):
                logits = model(values)
                loss = weighted_soft_cross_entropy(logits, target)
            if not torch.isfinite(loss):
                raise FloatingPointError("nonfinite M13 training loss")
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0, error_if_nonfinite=True)
            scaler.step(optimizer)
            scaler.update()
            epoch_losses.append(float(loss.detach()))
        scheduler.step()
        dev_loss, _ = _dev_summary(model, dev_loader, device)
        row = {"epoch": epoch, "train_loss": float(np.mean(epoch_losses)),
               "dev_loss": dev_loss, "learning_rate": scheduler.get_last_lr()[0]}
        history.append(row)
        print(json.dumps(row), flush=True)
        if dev_loss < best_loss:
            best_loss = dev_loss
            chosen_epoch = epoch
            best_state = deepcopy({key: value.detach().cpu() for key, value in model.state_dict().items()})
        _save_resume_state(resume_path, {
            "schema": "caos.phase-train-resume.v1",
            "config": config,
            "epoch": epoch,
            "model": model.state_dict(),
            "optimizer": optimizer.state_dict(),
            "scheduler": scheduler.state_dict(),
            "scaler": scaler.state_dict(),
            "best_loss": best_loss,
            "best_state": best_state,
            "chosen_epoch": chosen_epoch,
            "history": history,
            "loader_rng": generator.get_state(),
            "torch_cpu_rng": torch.get_rng_state(),
            "torch_cuda_rng": torch.cuda.get_rng_state_all(),
            "python_rng": random.getstate(),
        })
    if best_state is None:
        raise RuntimeError("no finite development-selected checkpoint")
    model.load_state_dict(best_state)
    dev_loss, dev_rows = _dev_summary(model, dev_loader, device)
    thresholds = select_dev_thresholds(dev_rows)
    checkpoint = {
        "schema": "caos.phase-picking-checkpoint.v1",
        "model": best_state,
        "architecture": "original-1d-residual-unet-16-32-64-128-192",
        "input": {"shape": [3, SAMPLES], "component_order": "ENZ",
                  "sampling_rate_hz": 100, "source_unit": "unrestituted counts",
                  "normalization": "trace-local demean and per-component centred peak"},
        "output": {"classes": ["N", "P", "S"], "kind": "logits"},
        "chosen_epoch": chosen_epoch,
        "seed": seed,
        "source_sha256": train_set.index["waveform_source_sha256"],
        "train_selection_sha256": train_set.index["selection_sha256"],
        "dev_selection_sha256": dev_set.index["selection_sha256"],
        "training_code_sha256": code_sha256,
        "model_code_sha256": model_code_sha256,
    }
    torch.save(checkpoint, checkpoint_path)
    checkpoint_sha = file_sha256(checkpoint_path)
    receipt = {
        "schema": "caos.phase-freeze.v1", "frozen_before_test": True,
        "checkpoint_filename": checkpoint_path.name,
        "checkpoint_sha256": checkpoint_sha,
        "waveform_source_sha256": train_set.index["waveform_source_sha256"],
        "test_selection_sha256": test_selection_hash,
        "chosen_epoch": chosen_epoch,
        "p_threshold": thresholds["p_threshold"],
        "s_threshold": thresholds["s_threshold"],
        "dev_macro_f1_at_0p5s": thresholds["macro_f1"],
        "dev_phase_counts": thresholds["counts"],
        "dev_loss": dev_loss,
        "train_valid": len(train_set), "dev_valid": len(dev_set),
        "train_qc_rejected": len(train_set.index["members"]) - len(train_set),
        "dev_qc_rejected": len(dev_set.index["members"]) - len(dev_set),
        "epochs_requested": epochs,
        "training_code_sha256": code_sha256,
        "model_code_sha256": model_code_sha256,
        "history": history,
        "software": {"torch": torch.__version__, "cuda": torch.version.cuda,
                     "numpy": np.__version__},
        "test_waveforms_opened": False,
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return {key: receipt[key] for key in ("checkpoint_sha256", "chosen_epoch", "p_threshold",
                                         "s_threshold", "dev_macro_f1_at_0p5s", "train_valid", "dev_valid")}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extraction-dir", type=Path,
                        default=ROOT / "data/raw/phase/extracted")
    parser.add_argument("--selection-manifest", type=Path,
                        default=ROOT / "data/raw/phase/stead-selection.json")
    parser.add_argument("--output-dir", type=Path,
                        default=ROOT / "data/raw/phase/models")
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--seed", type=int, default=41027)
    parser.add_argument("--resume", action="store_true",
                        help="Continue only an exact code/source/split/config private epoch state")
    args = parser.parse_args()
    print(json.dumps(train(args.extraction_dir, args.selection_manifest, args.output_dir,
                           epochs=args.epochs, batch_size=args.batch_size, seed=args.seed,
                           resume=args.resume), indent=2))


if __name__ == "__main__":
    main()
