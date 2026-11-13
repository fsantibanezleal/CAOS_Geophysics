"""Bind a passing real-trace CPU/WASM parity report to the public M13 assets.

The report is accepted only for the exact pre-finalization manifest and the
current verifier sources. It proves runtime parity, not picking accuracy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "data/derived/phase/browser-assets/stead"
PARITY_SCRIPT = ROOT / "frontend/scripts/verify-phase-browser-population.mjs"
ENTRYPOINT = ROOT / "frontend/scripts/verify-phase-browser-parity.mjs"
RECEIPT_NAME = "browser-parity.json"
EXPORT_STATUS = "assets-exported-browser-parity-not-yet-verified"
FINAL_STATUS = "browser-runtime-parity-verified; accuracy-unproven; release-unaccepted"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_write(path: Path, content: bytes) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def validate_report(manifest: dict, manifest_bytes: bytes, report_bytes: bytes) -> dict:
    report = json.loads(report_bytes)
    population = report.get("population", {})
    parity = report.get("parity", {})
    if (report.get("schema") != "caos.m13-browser-population-parity.v1"
            or report.get("status") != "pass"
            or report.get("assetDelivery") != "vite-publicDir"
            or report.get("manifestSha256") != sha256(manifest_bytes)
            or report.get("modelSha256") != manifest.get("model", {}).get("sha256")
            or report.get("verifierScriptSha256") != sha256(PARITY_SCRIPT.read_bytes())
            or report.get("gateEntrypointSha256") != sha256(ENTRYPOINT.read_bytes())
            or report.get("maxProbabilityAbsoluteError", 1) > 0.001
            or report.get("maxPeakDifferenceSamples", 99) > 1
            or not parity.get("sameFrozenOnnx")
            or parity.get("probabilityAbsoluteTolerance") != 0.001
            or parity.get("peakToleranceSamples") != 1
            or parity.get("pickToleranceSamples") != 1
            or population.get("selected") != 24
            or population.get("qcValidBrowserInferences") != 23
            or population.get("qcRejectedExcluded") != 1
            or population.get("selectionBeforeHeldoutScoring") is not True
            or population.get("allCpuReferenceHashesVerified") is not True
            or population.get("accuracyClaim") is not False
            or len(report.get("traces", [])) != 23):
        raise ValueError("browser parity report does not satisfy the source-bound 24/23/1 runtime gate")
    if (report.get("cpuReferenceManifestHashMatched") is False
            and report.get("cpuReferencePopulationIdentity") != "per-trace-model-and-waveform-hashes"):
        raise ValueError("a changed reference manifest requires verified per-trace model and waveform hashes")
    return report


def _export_manifest_bytes(manifest: dict) -> bytes:
    """Recreate the exact pre-finalization export bound by the parity receipt."""
    exported = {key: value for key, value in manifest.items()
                if key not in {"browser_parity_receipt", "export_status"}}
    exported["status"] = manifest.get("export_status", manifest.get("status"))
    exported["browser_parity_verified"] = False
    return (json.dumps(exported, indent=2, sort_keys=True) + "\n").encode("utf-8")


def refresh_finalized_status() -> dict:
    """Repair a legacy finalized manifest whose status still says unverified.

    The retained report must still validate against the reconstructed exact
    export and all hashes recorded in the manifest. No result or model bytes
    are replaced.
    """
    manifest_path = ASSETS / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    receipt_path = ASSETS / RECEIPT_NAME
    if manifest.get("browser_parity_verified") is not True or not receipt_path.is_file():
        raise ValueError("a finalized manifest and its retained parity receipt are required")
    report_bytes = receipt_path.read_bytes()
    exported_bytes = _export_manifest_bytes(manifest)
    exported = json.loads(exported_bytes)
    report = validate_report(exported, exported_bytes, report_bytes)
    metadata = manifest.get("browser_parity_receipt")
    if (not isinstance(metadata, dict)
            or metadata.get("file") != RECEIPT_NAME
            or metadata.get("sha256") != sha256(report_bytes)
            or metadata.get("schema") != report.get("schema")
            or metadata.get("max_probability_absolute_error") != report.get("maxProbabilityAbsoluteError")
            or metadata.get("max_peak_difference_samples") != report.get("maxPeakDifferenceSamples")
            or metadata.get("accuracy_claim") is not False):
        raise ValueError("finalized manifest receipt metadata does not match its retained report")
    if manifest.get("export_status") is None:
        if manifest.get("status") != EXPORT_STATUS:
            raise ValueError("legacy status is not the known pre-finalization export status")
        manifest["export_status"] = manifest["status"]
    elif manifest.get("export_status") != EXPORT_STATUS:
        raise ValueError("recorded export status is not the known pre-finalization state")
    manifest["status"] = FINAL_STATUS
    manifest["browser_parity_receipt"]["release_accepted"] = False
    atomic_write(manifest_path, (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    return {"status": manifest["status"], "export_status": manifest["export_status"],
            "release_accepted": False, "manifest_sha256": sha256(manifest_path.read_bytes()),
            "parity_receipt_sha256": sha256(report_bytes)}


def finalize(report_path: Path) -> dict:
    manifest_path = ASSETS / "manifest.json"
    original_bytes = manifest_path.read_bytes()
    manifest = json.loads(original_bytes)
    if manifest.get("browser_parity_verified") is not False or "browser_parity_receipt" in manifest:
        raise ValueError("browser parity is already finalized; refusing to replace the receipt")
    if manifest.get("status") != EXPORT_STATUS or "export_status" in manifest:
        raise ValueError("source manifest does not have the expected unverified export state")
    report_bytes = report_path.read_bytes()
    report = validate_report(manifest, original_bytes, report_bytes)
    receipt_path = ASSETS / RECEIPT_NAME
    if receipt_path.exists():
        raise ValueError(f"refusing to overwrite existing parity receipt: {receipt_path}")

    manifest["browser_parity_verified"] = True
    manifest["export_status"] = manifest["status"]
    manifest["status"] = FINAL_STATUS
    manifest["browser_parity_receipt"] = {
        "file": RECEIPT_NAME,
        "sha256": sha256(report_bytes),
        "schema": report["schema"],
        "measured_at": report["measuredAt"],
        "max_probability_absolute_error": report["maxProbabilityAbsoluteError"],
        "max_peak_difference_samples": report["maxPeakDifferenceSamples"],
        "mean_browser_inference_ms": report["meanBrowserInferenceMs"],
        "accuracy_claim": False,
        "release_accepted": False,
    }
    atomic_write(receipt_path, report_bytes)
    try:
        atomic_write(manifest_path, (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    except BaseException:
        receipt_path.unlink(missing_ok=True)
        raise
    return {"receipt": receipt_path.as_posix(), "receipt_sha256": sha256(report_bytes),
            "manifest_sha256": sha256(manifest_path.read_bytes()),
            "max_probability_absolute_error": report["maxProbabilityAbsoluteError"],
            "max_peak_difference_samples": report["maxPeakDifferenceSamples"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, nargs="?",
                        help="passing report from verify-phase-browser-population.mjs")
    parser.add_argument("--refresh-finalized-status", action="store_true",
                        help="reconcile status on an already finalized manifest after verifying its retained receipt")
    args = parser.parse_args()
    try:
        if args.refresh_finalized_status:
            if args.report is not None:
                parser.error("--refresh-finalized-status does not take a report path")
            result = refresh_finalized_status()
        else:
            if args.report is None:
                parser.error("a passing report path is required unless --refresh-finalized-status is used")
            result = finalize(args.report.resolve(strict=True))
        print(json.dumps(result, indent=2))
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        print(f"finalize_stead_browser_parity: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
