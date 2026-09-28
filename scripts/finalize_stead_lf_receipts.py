"""One-time, lossless LF serialization of the already scored STEAD release.

The Windows scoring run wrote JSON with CRLF. Git normalizes tracked JSON to
LF, which would break byte hashes of the copied benchmark and manifest. This
guarded migration changes no picks, metrics, model bytes or waveform bytes. It
saves the original byte-for-byte receipts in ignored raw storage first.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/phase/models-amp2"
REPORT = ROOT / "data/derived/phase/stead-heldout-benchmark.json"
OVERLAP = ROOT / "data/derived/phase/stead-heldout-overlap.json"
ASSETS = ROOT / "data/derived/phase/browser-assets/stead"
PRIVATE_LEDGER = RAW / "phase-heldout-predictions.json"
BACKUP = RAW / "pre-lf-receipts"
OLD_REPORT_SHA256 = "1397cd17dd73480950a5c981f696634bfbfef34f974bc3fb09071ce9b7b6b8b1"
OLD_MANIFEST_SHA256 = "35fda3c20d40c0f6af2a7fa954c686ba75f6353b093531f25434e46fef8c948b"
OLD_OVERLAP_SHA256 = "4a3dbf26f559e3f8f7530a1b0757f5bfc9a62306b29c12c2db6876e95be0e0e4"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def lf(data: bytes) -> bytes:
    if b"\r\n" not in data or data.replace(b"\r\n", b"").find(b"\r") >= 0:
        raise ValueError("expected Windows CRLF-only JSON receipt")
    return data.replace(b"\r\n", b"\n")


def main() -> None:
    paths = {
        "private-ledger.json": PRIVATE_LEDGER,
        "heldout-report.json": REPORT,
        "overlap.json": OVERLAP,
        "asset-benchmark.json": ASSETS / "benchmark.json",
        "asset-manifest.json": ASSETS / "manifest.json",
    }
    if BACKUP.exists() or BACKUP.is_symlink():
        raise FileExistsError("pre-LF backup already exists; migration is one-time only")
    originals = {name: path.read_bytes() for name, path in paths.items()}
    if (sha(originals["heldout-report.json"]) != OLD_REPORT_SHA256
            or originals["heldout-report.json"] != originals["asset-benchmark.json"]
            or sha(originals["asset-manifest.json"]) != OLD_MANIFEST_SHA256
            or sha(originals["overlap.json"]) != OLD_OVERLAP_SHA256):
        raise ValueError("receipt bytes differ from the inspected pre-migration package")
    report = json.loads(originals["heldout-report.json"])
    manifest = json.loads(originals["asset-manifest.json"])
    overlap = json.loads(originals["overlap.json"])
    private = json.loads(originals["private-ledger.json"])
    if (sha(originals["private-ledger.json"]) != report["private_predictions_sha256"]
            or report["checkpoint_sha256"] != manifest["model"]["checkpoint_sha256"]
            or report["checkpoint_sha256"] != overlap["checkpoint_sha256"]
            or sha(originals["asset-benchmark.json"]) != manifest["benchmark"]["sha256"]
            or private["checkpoint_sha256"] != report["checkpoint_sha256"]
            or report["selected"] != 6000 or manifest["selection"]["selected"] != 24):
        raise ValueError("receipts do not bind the same scored model and cohort")
    revised = {}
    revised["private-ledger.json"] = lf(originals["private-ledger.json"])
    report["private_predictions_sha256"] = sha(revised["private-ledger.json"])
    revised["heldout-report.json"] = (
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    revised["asset-benchmark.json"] = revised["heldout-report.json"]
    revised["overlap.json"] = lf(originals["overlap.json"])
    manifest["benchmark"]["sha256"] = sha(revised["asset-benchmark.json"])
    revised["asset-manifest.json"] = (
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    if (json.loads(revised["private-ledger.json"]) != private
            or json.loads(revised["overlap.json"]) != overlap):
        raise ValueError("line-ending migration would alter ledger or overlap content")
    old_report_except_hash = dict(json.loads(originals["heldout-report.json"]))
    new_report_except_hash = dict(json.loads(revised["heldout-report.json"]))
    old_report_except_hash.pop("private_predictions_sha256")
    new_report_except_hash.pop("private_predictions_sha256")
    if old_report_except_hash != new_report_except_hash:
        raise ValueError("line-ending migration would alter benchmark metrics")
    old_manifest_except_hash = dict(json.loads(originals["asset-manifest.json"]))
    new_manifest_except_hash = dict(json.loads(revised["asset-manifest.json"]))
    old_manifest_except_hash["benchmark"].pop("sha256")
    new_manifest_except_hash["benchmark"].pop("sha256")
    if old_manifest_except_hash != new_manifest_except_hash:
        raise ValueError("line-ending migration would alter asset selection or model metadata")
    BACKUP.mkdir(parents=True, exist_ok=False)
    for name, original in originals.items():
        (BACKUP / name).write_bytes(original)
    for name, path in paths.items():
        path.write_bytes(revised[name])
    receipt = {
        "schema": "caos.phase-lf-migration.v1",
        "status": "serialization-only-no-metric-or-model-change",
        "files": {name: {"old_sha256": sha(originals[name]), "new_sha256": sha(revised[name])}
                  for name in paths},
        "private_backup": str(BACKUP),
    }
    (BACKUP / "migration.json").write_bytes(
        (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
