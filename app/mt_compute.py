"""Private child process: strict original-byte EDI QC and bounded layered TRF."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
import sys
import threading
from pathlib import Path

from app.mt_contract import EDI_SOURCE_LIMIT, M05_ID, M06_ID, M05Parameters, M06Parameters
from app.processing_contract import canonical_bytes, sha256


PIPELINE = Path(__file__).resolve().parents[1] / "data-pipeline"


def verified_source_snapshot(raw_path: Path, stage: Path, *, raw_sha256: str, raw_bytes: int) -> Path:
    """Copy only the verified original bytes for every subsequent scientific read."""
    if not 128 <= raw_bytes <= EDI_SOURCE_LIMIT or raw_path.is_symlink():
        raise ValueError("Original EDI exceeds the admitted source boundary")
    with raw_path.open("rb") as original:
        encoded = original.read(raw_bytes + 1)
    if len(encoded) != raw_bytes or sha256(encoded) != raw_sha256:
        raise ValueError("Admitted original EDI bytes differ from receipt")
    snapshot = stage / "source.edi"
    with snapshot.open("xb") as output:
        output.write(encoded)
        output.flush()
        os.fsync(output.fileno())
    return snapshot


def _edi_modules():
    if str(PIPELINE) not in sys.path:
        sys.path.insert(0, str(PIPELINE))
    from edi import EDIError, invert_edi, screen_edi
    return EDIError, invert_edi, screen_edi


def _read_options(dataset: dict) -> dict:
    physical = dataset["physical_metadata"]
    geometry = physical["geometry"]
    return {
        "units": "mt" if physical["measurement_unit"] == "mV/km/nT" else "ohm",
        "sign_convention": geometry["sign_convention"],
        "variance_convention": geometry["variance_convention"],
        "rotation": "geographic" if physical["component_frame"] == "geographic ENU" else "preserve",
        "rotation_reference": (geometry["rotation_reference"]
                               if geometry["rotation_reference"] == "geographic-north" else None),
    }


def _checked_screen(raw_path: Path, dataset: dict, screen_edi) -> dict:
    screen = screen_edi(raw_path, **_read_options(dataset))
    physical = dataset["physical_metadata"]
    geometry = physical["geometry"]
    provenance = screen["provenance"]
    if (provenance["source_sha256"] != dataset["parent_raw_sha256"]
            or provenance["source_bytes"] != dataset["parent_raw_bytes"]
            or screen["id"] != geometry["station_id"]
            or len(screen["frequencies_hz"]) != geometry["frequency_count"]
            or provenance["original_units"] != ("mt" if physical["measurement_unit"] == "mV/km/nT" else "ohm")
            or provenance["original_sign_convention"] != geometry["sign_convention"]
            or provenance["variance_convention"] != geometry["variance_convention"]
            or provenance["tipper_present"] != (set(geometry["tensor_components"]) ==
                                                 {"Zxx", "Zxy", "Zyx", "Zyy", "Tx", "Ty"})
            or any(abs((angle - geometry["rotation_degrees"] + 180) % 360 - 180) > 1e-7
                   for angle in provenance["original_rotation_deg"])):
        raise ValueError("Declared EDI station, tensor, units, sign, variance or rotation disagrees with original")
    return screen


def _fit_summary(run: dict) -> dict:
    method = run["methods"]["mt-lm"]
    return {
        "model_ohm_m": method["model"],
        "training_objective": method["metrics"]["objective"],
        "training_component_wrms": method["metrics"]["active_component_wrms"],
        "heldout_component_wrms": method["metrics"]["withheld_component_wrms"],
        "solver_success": method["solver"]["success"],
        "stop_reason": method["solver"]["stop_reason"],
    }


def _inverse(raw_path: Path, screen: dict, parameters: M06Parameters, invert_edi, options: dict) -> dict:
    frequencies = screen["frequencies_hz"]
    if not screen["one_d_inversion_eligible"] or not 12 <= len(frequencies) <= 64:
        raise ValueError("Full original tensor is ineligible for bounded 1D inversion")
    active = [index % 5 != 4 for index in range(len(frequencies))]
    h = parameters.thickness_m
    beta = parameters.beta
    initial = parameters.initial_ohm_m
    n = len(initial)
    starts = [initial, [30.0] * n, [1000.0] * n]
    trials = []
    for start in starts:
        run = invert_edi(raw_path, h, initial=start, beta=beta, active=active,
                         bootstrap_samples=0, seed=parameters.seed, **options)
        trials.append({"initial_ohm_m": start, **_fit_summary(run)})
    eligible_trials = [trial for trial in trials if trial["solver_success"]]
    if not eligible_trials:
        raise ValueError("All bounded TRF starts failed")
    winner = min(eligible_trials, key=lambda trial: trial["training_objective"])
    chosen = invert_edi(raw_path, h, initial=winner["initial_ohm_m"], beta=beta,
                        active=active, bootstrap_samples=parameters.bootstrap_samples,
                        seed=parameters.seed, **options)
    primary = chosen["methods"]["mt-lm"]
    baseline = (invert_edi(raw_path, [], initial=[100.0], beta=beta, active=active,
                           bootstrap_samples=0, seed=parameters.seed, **options)
                if h else chosen)
    alternate_beta = 0.01 if beta == 0 else (beta * 10 if beta <= .1 else beta / 10)
    beta_run = invert_edi(raw_path, h, initial=winner["initial_ohm_m"], beta=alternate_beta,
                          active=active, bootstrap_samples=0, seed=parameters.seed, **options)
    thickness_runs = []
    for multiplier in (.8, 1.2) if h else ():
        alternative = [value * multiplier for value in h]
        run = invert_edi(raw_path, alternative, initial=winner["initial_ohm_m"], beta=beta,
                         active=active, bootstrap_samples=0, seed=parameters.seed, **options)
        thickness_runs.append({"thickness_m": alternative, **_fit_summary(run)})
    chosen["evaluation_protocol"] = {
        "frequency_partition": "sorted frequencies, every fifth index withheld before any fit",
        "training_mask": active,
        "selection": "minimum training objective among successful starts; holdout not used for selection",
        "starts": trials,
        "halfspace_baseline": _fit_summary(baseline),
        "beta_sensitivity": {"beta": alternate_beta, **_fit_summary(beta_run)},
        "thickness_sensitivity": thickness_runs,
        "selected_start_ohm_m": winner["initial_ohm_m"],
        "uncertainty_limit": "Pointwise conditional parametric bootstrap only; fixed thickness, independent marginal errors, beta, bounds and source frame. No field geological truth or posterior coverage.",
    }
    if not primary["solver"]["success"] or primary["uncertainty"]["status"] != "computed":
        raise ValueError("Selected TRF or conditional interval did not complete")
    if chosen["truth"] is not None or chosen["clean"] is not None:
        raise ValueError("Supplied EDI must not acquire invented target truth")
    return chosen


def compute_mt(dataset: dict, raw_path: Path, *, dataset_sha: str, job_id: str,
               request_sha: str, method_id: str, parameters: dict,
               qc_screen_sha256: str = "") -> dict:
    _, invert_edi, screen_edi = _edi_modules()
    if dataset.get("modality") != "edi_transfer_function":
        raise ValueError("MT worker needs an admitted EDI dataset")
    screen = _checked_screen(raw_path, dataset, screen_edi)
    inverse = None
    if method_id == M05_ID:
        M05Parameters.model_validate(parameters)
        if qc_screen_sha256:
            raise ValueError("M05 cannot cite an inverse-admission receipt")
    elif method_id == M06_ID:
        parsed = M06Parameters.model_validate(parameters)
        if not qc_screen_sha256 or sha256(canonical_bytes(screen)) != qc_screen_sha256:
            raise ValueError("M05 QC screen differs from this exact original")
        inverse = _inverse(raw_path, screen, parsed, invert_edi, _read_options(dataset))
    else:
        raise ValueError("Unsupported MT method")
    environment = {
        "python": platform.python_version(),
        "packages": {package: importlib.metadata.version(package) for package in (
            "numpy", "scipy", "mt-metadata", "pandas", "matplotlib", "xarray")},
    }
    return {
        "schema": "geophysics.processing-result/v1", "job_id": job_id,
        "dataset_id": dataset["dataset_id"], "dataset_sha256": dataset_sha,
        "method_id": method_id, "request_sha256": request_sha,
        "parameters": parameters, "raw_asset_id": dataset["raw_asset_id"],
        "raw_sha256": dataset["parent_raw_sha256"], "raw_bytes": dataset["parent_raw_bytes"],
        "engine_sha256": sha256(Path(__file__).read_bytes()),
        "parser_sha256": sha256((PIPELINE / "edi.py").read_bytes()),
        "forward_sha256": sha256((PIPELINE / "electromagnetics.py").read_bytes()),
        "environment": environment, "environment_sha256": sha256(canonical_bytes(environment)),
        "axis_order": ["frequency"], "dimensions": {"frequency": len(screen["frequencies_hz"])},
        "frequency_hz": screen["frequencies_hz"], "physical_metadata": dataset["physical_metadata"],
        "source": dataset["source"], "screen": screen, "inverse": inverse,
        "qc_screen_sha256": qc_screen_sha256 if inverse is not None else None,
        "truth": None,
        "interpretation_limit": "A passing tensor screen is necessary but cannot establish 1D geology; fixed-thickness estimates are conditional.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("input", "raw", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    for name in ("job-id", "dataset-sha256", "request-sha256", "raw-sha256", "method-id", "parameters"):
        parser.add_argument(f"--{name}", required=True)
    parser.add_argument("--raw-bytes", type=int, required=True)
    parser.add_argument("--qc-screen-sha256", default="")
    parser.add_argument("--memory-limit", type=int, required=True)
    parser.add_argument("--scratch-limit", type=int, required=True)
    args = parser.parse_args()
    try:
        if min(args.memory_limit, args.scratch_limit) <= 0:
            raise ValueError("Invalid child resource ceiling")
        if os.name == "posix":
            import resource
            resource.setrlimit(resource.RLIMIT_AS, (args.memory_limit, args.memory_limit))
            resource.setrlimit(resource.RLIMIT_FSIZE, (args.scratch_limit, args.scratch_limit))

        def parent_watch() -> None:
            if not os.read(0, 1):
                os._exit(99)

        _edi_modules()
        from mt_metadata.transfer_functions.io.edi import EDI  # noqa: F401
        threading.Thread(target=parent_watch, daemon=True).start()
        dataset_bytes = args.input.read_bytes()
        if len(dataset_bytes) > 8 * 1024 * 1024 or sha256(dataset_bytes) != args.dataset_sha256:
            raise ValueError("Admitted dataset or original EDI bytes differ from receipt")
        dataset = json.loads(dataset_bytes)
        if canonical_bytes(dataset) != dataset_bytes or dataset["parent_raw_sha256"] != args.raw_sha256:
            raise ValueError("Noncanonical or unrelated EDI dataset")
        snapshot = verified_source_snapshot(args.raw, args.output.parent,
                                            raw_sha256=args.raw_sha256, raw_bytes=args.raw_bytes)
        parameters = json.loads(args.parameters)
        result = compute_mt(dataset, snapshot, dataset_sha=args.dataset_sha256, job_id=args.job_id,
                            request_sha=args.request_sha256, method_id=args.method_id,
                            parameters=parameters, qc_screen_sha256=args.qc_screen_sha256)
        encoded = canonical_bytes(result)
        if len(encoded) > 8 * 1024 * 1024 or len(encoded) > args.scratch_limit:
            raise ValueError("MT result exceeds scratch cap")
        with args.output.open("xb") as output:
            output.write(encoded)
            output.flush()
            os.fsync(output.fileno())
    except Exception as exc:
        print(f"mt_processing_failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
