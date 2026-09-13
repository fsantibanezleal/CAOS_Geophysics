"""Named staged release pipeline for Inverse Earth Studio."""
from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path
from functools import lru_cache

from geophysicslab import __version__
from geophysicslab.cases import get_case, list_cases
from geophysicslab.core.manifest import build_index
from geophysicslab.core.solver_checks import run_solver_certificates
from geophysicslab.io.formats import write_json
from geophysicslab.stages import dataset, evaluate, export, features, infer, ingest, preprocess, train, validate

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "data" / "derived"
MANIFESTS = DERIVED / "manifests"
STAGES = ("ingest", "preprocess", "dataset", "features", "train", "infer", "evaluate", "export", "validate")


@lru_cache(maxsize=1)
def engine_inventory() -> dict:
    inventory = {"python": platform.python_version(), "numpy": "installed", "torch": False, "cuda": False, "simpeg": False, "choclo": False, "deepwave": False, "devito": False}
    try:
        import torch

        inventory["torch"] = True
        inventory["cuda"] = bool(torch.cuda.is_available())
        if inventory["cuda"]:
            inventory["cuda_device"] = torch.cuda.get_device_name(0)
    except ImportError:
        pass
    for module, key in (("simpeg", "simpeg"), ("choclo", "choclo"), ("deepwave", "deepwave"), ("devito", "devito")):
        try:
            __import__(module)
            inventory[key] = True
        except ImportError:
            pass
    if inventory["simpeg"] and inventory["choclo"]:
        inventory["certificates"] = run_solver_certificates()
    return inventory


def _observation_rows(result: dict) -> list[dict]:
    rows: list[dict] = []
    for index, value in enumerate(result["gravity"]["gravity_mgal"]):
        rows.append({"station_id": f"gravity-{index:03d}", "x_m": float(result["gravity"]["x_m"][index]), "y_m": 0.0, "frequency_hz": 1.0, "value": float(value), "unit": "gravity_mgal"})
    for index, value in enumerate(result["magnetics"]["magnetic_nT"]):
        rows.append({"station_id": f"magnetic-{index:03d}", "x_m": float(result["magnetics"]["x_m"][index]), "y_m": 0.0, "frequency_hz": 1.0, "value": float(value), "unit": "magnetic_nT"})
    for index, value in enumerate(result["mt"]["apparent_resistivity_ohm_m"]):
        rows.append({"station_id": f"mt-{index:03d}", "x_m": float(index), "y_m": 0.0, "frequency_hz": float(result["mt"]["frequency_hz"][index]), "value": float(value), "unit": "ohm_m"})
    for index, value in enumerate(result["fwi"]["observed"]):
        rows.append({"station_id": f"fwi-{index:03d}", "x_m": float(index), "y_m": 0.0, "frequency_hz": 18.0, "value": float(value), "unit": "trace_amplitude"})
    return rows


def _run_stage_contracts(case, result: dict, seed: int, derived: Path, split: dict) -> dict:
    ingested = ingest.run(_observation_rows(result))
    preprocessed = preprocess.run([row["value"] for row in ingested["accepted"]], case.noise)
    feature_table = features.run(result["model"])
    summary = {
        "ingest": {"n_rows": ingested["n_rows"], "accepted": len(ingested["accepted"]), "rejected": len(ingested["rejected"]), "flagged": len(ingested["flagged"])},
        "preprocess": {"n_values": len(preprocessed["values"]), "mean": preprocessed["mean"], "scale": preprocessed["scale"], "noise": preprocessed["noise"]},
        "dataset": {"split_policy": split["split_policy"], "train_groups": len(split["train"]), "validation_groups": len(split["validation"]), "test_groups": len(split["test"])},
        "features": feature_table,
    }
    write_json(derived / "stages" / f"{case.id}.json", {"schema": "inverse-earth.stages/v1", "case_id": case.id, "seed": seed, "stages": summary})
    return summary


def precompute(case_id: str, seed: int = 42, output_root: str | Path | None = None, split: dict | None = None, trained: dict | None = None) -> dict:
    derived = Path(output_root).resolve() if output_root else DERIVED
    manifests = derived / "manifests"
    case = get_case(case_id)
    split = split or dataset.run([candidate.id for candidate in list_cases()])
    result = infer.run(case, seed)
    metrics = evaluate.run(result, case)
    metrics["held_out"] = case.id in split["test"]
    trained = trained or train.run(seed, tuple(split["train"]), tuple(split["validation"]), tuple(split["test"]))
    metrics.update({"learned_surrogate_weight_norm": round(sum(value * value for value in trained["weights"]) ** 0.5, 8), "training_split": "grouped-case-70-15-15", "learned_backend": trained["learned"]["backend"], "cnn_loss": trained["learned"]["cnn_loss"], "autoencoder_loss": trained["learned"]["autoencoder_loss"]})
    engines = engine_inventory()
    stages = _run_stage_contracts(case, result, seed, derived, split)
    stages["train"] = {"model": trained["model"], "backend": trained["learned"]["backend"], "device": trained["learned"]["device"], "train_samples": trained["learned"]["train_samples"], "test_samples": trained["learned"]["test_samples"], "test_cnn_mse": trained["learned"]["test_cnn_mse"], "test_autoencoder_mse": trained["learned"]["test_autoencoder_mse"], "validation_cnn_mse": trained["learned"]["validation_cnn_mse"], "validation_autoencoder_mse": trained["learned"]["validation_autoencoder_mse"]}
    stages["infer"] = {"methods": [case.method, "gravity forward", "magnetic forward", "layered MT", "acoustic FWI", "cross-gradient diagnostics"]}
    stages["evaluate"] = {"metric_keys": sorted(metrics)}
    stages["export"] = {"artifact": f"{case.id}/result.json"}
    stages["validate"] = {"contract": "manifest bytes, schema, and artifact presence", "release_validator": "validate.run"}
    return export.run(case=case, seed=seed, result=result, metrics=metrics, engines=engines, derived_dir=derived, manifests_dir=manifests, stages=stages)


def run_all(seed: int = 42, output_root: str | Path | None = None) -> list[dict]:
    derived = Path(output_root).resolve() if output_root else DERIVED
    entries = []
    all_cases = list_cases()
    split = dataset.run([case.id for case in all_cases])
    trained = train.run(seed, tuple(split["train"]), tuple(split["validation"]), tuple(split["test"]))
    write_json(derived / "training.json", {"schema": "inverse-earth.training/v1", "seed": seed, "split": split, "model": trained})
    for case in all_cases:
        precompute(case.id, seed=seed, output_root=derived, split=split, trained=trained)
        entries.append({"case_id": case.id, "category": case.category, "method": case.method, "manifest_path": f"manifests/{case.id}.json"})
    write_json(derived / "manifests" / "index.json", build_index(entries))
    write_json(derived / "release.json", {"schema": "inverse-earth.release/v1", "version": __version__, "seed": seed, "stages": STAGES, "stage_contract": "ingest -> preprocess -> dataset -> features -> train -> infer -> evaluate -> export -> validate", "training_manifest": "training.json", "engines": engine_inventory(), "case_count": len(entries)})
    verdict = validate.run(derived, derived / "manifests", [entry["case_id"] for entry in entries])
    if not verdict["ok"]:
        raise RuntimeError(json.dumps(verdict))
    return entries


def main() -> None:
    parser = argparse.ArgumentParser(prog="geophysicslab.pipeline")
    parser.add_argument("case", nargs="?", default="all")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.case == "all":
        entries = run_all(args.seed, args.output)
        print(f"baked {len(entries)} geophysics cases")
    else:
        manifest = precompute(args.case, args.seed, args.output)
        print(f"baked {args.case}: {manifest['artifact']['bytes']} bytes, lane={manifest['lane']}")


if __name__ == "__main__":
    main()
