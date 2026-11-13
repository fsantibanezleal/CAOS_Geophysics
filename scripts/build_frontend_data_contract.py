"""Generate the shared-template declared-file index for the canonical v2 catalogue."""
from __future__ import annotations

import json
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "data" / "derived"
V2 = DERIVED / "v2"
MANIFESTS = DERIVED / "manifests"
SUPPLEMENTAL = [
    "v2/catalog.json",
    "v2/fwi-replay.json",
    "v2/migration.json",
    "v2/models/autoencoder.json",
    "v2/models/cnn.json",
    "v2/models/training.json",
]


def main() -> int:
    catalog = json.loads((V2 / "catalog.json").read_text(encoding="utf-8"))
    if catalog.get("schema") != "inverse-earth.catalog/v2" or catalog.get("complete") is not True:
        raise SystemExit("v2 catalog must be complete and use inverse-earth.catalog/v2")
    readiness = json.loads((DERIVED / "readiness.json").read_text(encoding="utf-8"))
    catalog_bytes = (V2 / "catalog.json").read_bytes()
    if (readiness.get("schema") != "inverse-earth.readiness/v1"
            or readiness.get("catalog", {}).get("sha256") != hashlib.sha256(catalog_bytes).hexdigest()
            or readiness.get("catalog", {}).get("version") != catalog.get("version")
            or readiness.get("counts", {}).get("cases") != len(catalog.get("cases", []))
            or readiness.get("counts", {}).get("variants") != sum(len(c.get("variants", [])) for c in catalog.get("cases", []))):
        raise SystemExit("existing readiness receipt does not bind the current catalog; reconcile it in the data pipeline")
    cases = catalog.get("cases")
    if not isinstance(cases, list) or len(cases) != 20:
        raise SystemExit("v2 catalog must contain the 20 reviewed geological cases")
    variant_count = sum(len(c.get("variants", [])) for c in cases)
    method_count = sum(len(v.get("methods", {})) for c in cases for v in c.get("variants", []))
    declared_bytes = sum(v.get("bytes", 0) for c in cases for v in c.get("variants", []))
    if (readiness.get("counts", {}).get("variants") != variant_count
            or readiness.get("counts", {}).get("method_results") != method_count
            or readiness.get("artifacts", {}).get("present") != variant_count
            or readiness.get("artifacts", {}).get("declared_bytes") != declared_bytes
            or readiness.get("artifacts", {}).get("missing") != []
            or readiness.get("state") != "available"):
        raise SystemExit("readiness counts and bytes do not match the canonical catalog")

    MANIFESTS.mkdir(parents=True, exist_ok=True)
    index_cases: list[dict[str, str]] = []
    seen: set[str] = set()
    for case in cases:
        case_id = case.get("id")
        if not isinstance(case_id, str) or not re.fullmatch(r"[A-Z0-9_-]+", case_id) or case_id in seen:
            raise SystemExit(f"invalid or duplicate v2 case id: {case_id!r}")
        seen.add(case_id)
        variants = case.get("variants")
        if not isinstance(variants, list) or len(variants) != 6:
            raise SystemExit(f"{case_id}: expected six declared condition artifacts")
        artifacts: list[dict[str, object]] = []
        for variant in variants:
            rel = variant.get("path")
            if not isinstance(rel, str) or not re.fullmatch(rf"{re.escape(case_id)}/[A-Za-z0-9_-]+\.json", rel):
                raise SystemExit(f"{case_id}: unsafe artifact path {rel!r}")
            path = V2 / rel
            size = variant.get("bytes")
            digest = variant.get("sha256")
            if not path.is_file() or path.stat().st_size != size or not re.fullmatch(r"[0-9a-f]{64}", str(digest)):
                raise SystemExit(f"{case_id}/{rel}: missing artifact or invalid byte/hash declaration")
            artifacts.append({"path": f"v2/{rel}", "bytes": size, "sha256": digest})
        manifest_path = f"manifests/v2-{case_id.lower()}.json"
        manifest = {"schema": "caos.declared-artifacts/v1", "case_id": case_id, "artifacts": artifacts}
        (DERIVED / manifest_path).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        index_cases.append({"case_id": case_id, "manifest_path": manifest_path})

    for rel in SUPPLEMENTAL:
        if not (DERIVED / rel).is_file():
            raise SystemExit(f"declared supplemental artifact is missing: {rel}")
    index = {"schema": "caos.declared-artifacts-index/v1", "files": SUPPLEMENTAL, "cases": index_cases}
    (MANIFESTS / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"[data-contract] {len(cases)} cases, {variant_count} artifacts, {method_count} method results, {len(SUPPLEMENTAL)} supplemental files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
