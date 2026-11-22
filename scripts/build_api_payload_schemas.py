"""Refresh API payload schemas from the actual runtime request models.

Run with the API environment, for example:
    .venv-api/Scripts/python.exe scripts/build_api_payload_schemas.py

The document also contains modality result records that are deliberately
hand-authored. This exporter replaces only the two request roots and their
Pydantic definitions, then synchronizes the processing-method identity enum
and the locked schema digest.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.processing import DatasetCreate, JobCreate  # noqa: E402
from app.gravity_l2_contract import METHOD_ID as GRAVITY_L2_ID  # noqa: E402
from app.magnetic_contract import METHOD_ID as MAGNETIC_ID  # noqa: E402
from app.mt_contract import M05_ID, M06_ID  # noqa: E402
from app.profile_contract import PROFILE_METHODS  # noqa: E402
from app.processing_contract import METHOD_ID as GRAVITY_FLAGS_ID  # noqa: E402


SCHEMA_PATH = ROOT / "docs/contracts/schemas/api-payloads.schema.json"
LOCK_PATH = ROOT / "docs/contracts/versions.lock.json"


def schema_for(model) -> dict:
    return model.model_json_schema(ref_template="#/$defs/{model}")


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    document = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    definitions = document["$defs"]
    for model in (DatasetCreate, JobCreate):
        exported = schema_for(model)
        definitions.update(exported.pop("$defs", {}))
        definitions[model.__name__] = exported

    method_ids = [GRAVITY_FLAGS_ID, GRAVITY_L2_ID, MAGNETIC_ID, M05_ID, M06_ID, *PROFILE_METHODS]
    definitions["ScientificProcessingResult"]["properties"]["method_id"] = {"enum": method_ids}
    write_json(SCHEMA_PATH, document)

    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    lock["api-payloads"]["version"] = "1.3.0"
    normalized_schema = SCHEMA_PATH.read_bytes().replace(b"\r\n", b"\n")
    lock["api-payloads"]["sha256"] = hashlib.sha256(normalized_schema).hexdigest()
    write_json(LOCK_PATH, lock)
    print(f"updated {SCHEMA_PATH.relative_to(ROOT)}: {len(definitions)} definitions")
    print(f"api-payloads 1.3.0 sha256={lock['api-payloads']['sha256']}")


if __name__ == "__main__":
    main()
