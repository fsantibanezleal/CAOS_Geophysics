"""Audit all current-source CPU2 certificate-bearing calibration archives."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "research"))
sys.path.insert(0, str(ROOT / "data-pipeline"))

import audit_cpu2_terminal_certificate as audit_one
import gravity_irls_pool as pool
import gravity_workflow_io as transport
import gravity_l2 as l2


def audit_matrix(archive_root: Path) -> dict:
    archive_root = audit_one._external(archive_root, "archive root")
    paths = sorted(archive_root.glob("corrected-family*-condition*-*.gza"))
    expected = {f"family{family}-condition{condition}" for family in range(6) for condition in range(4)}
    observed = set()
    audited = []
    for path in paths:
        name_parts = path.name.split("-")
        identity = "-".join(name_parts[1:3])
        if identity in observed:
            raise ValueError(f"duplicate family/condition archive: {identity}")
        observed.add(identity)
        archive = transport.read_archive(path.parent, path.name)
        fits = archive["result"].get("fits")
        if type(fits) not in (tuple, list):
            raise ValueError(f"{path.name}: missing exact calibration fit book")
        cert_count = 0
        for fit in fits[:24]:
            decoded = pool.decode(fit)
            cert_count += decoded.get("terminal", {}).get("fixed_point_certificate") is not None
        if cert_count:
            report = audit_one.audit(path)
            if len(report["records"]) != cert_count:
                raise ValueError(f"{path.name}: audit count differs from archive certificate count")
            audited.append({"archive": path.name, "archive_sha256": report["archive_sha256"],
                "request_sha256": report["request_sha256"], "result_sha256": report["result_sha256"],
                "certificate_count": cert_count, "records": report["records"]})
    if observed != expected:
        raise ValueError(f"matrix archive inventory mismatch: missing={sorted(expected-observed)}, extra={sorted(observed-expected)}")
    records = [record for item in audited for record in item["records"]]
    if not records:
        raise ValueError("matrix contains no CPU2 terminal certificates")
    kkt = [record["projected_kkt_inf"] for record in records]
    receipt = {"schema": "gravity-cpu2-terminal-certificate-matrix-audit-1",
        "research_only": True, "acceptance": False, "archive_count": len(paths),
        "audited_archive_count": len(audited), "certificate_count": len(records),
        "archive_root": str(archive_root), "auditor_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "single_archive_auditor_sha256": hashlib.sha256(Path(audit_one.__file__).read_bytes()).hexdigest(),
        "matrix": audited,
        "summary": {"kkt_inf_min": min(kkt), "kkt_inf_max": max(kkt),
            "minimum_smallness_curvature": min(r["smallness_curvature_min"] for r in records),
            "minimum_strict_convexity_bound": min(r["strict_convexity_lower_bound"] for r in records)}}
    receipt["receipt_sha256"] = l2.survey._digest(receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = audit_one._external(args.output, "receipt")
    if output.exists():
        raise FileExistsError(output)
    report = audit_matrix(args.archive_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, sort_keys=True, allow_nan=False, indent=2)
        stream.write("\n")
    print(json.dumps({"status": "research_only", "archives": report["archive_count"],
        "audited_archives": report["audited_archive_count"], "certificates": report["certificate_count"],
        "receipt_sha256": report["receipt_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
