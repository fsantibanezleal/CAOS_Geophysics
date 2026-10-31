"""Geometry-only export closure, not future inverse-bundle durability."""

import json
import pytest
from magnetic_survey_support import encode, request
from magnetic_survey_json import InputError, parse_request
from magnetic_survey import plan_geometry
from magnetic_survey_bundle import export_geometry, import_geometry, write_geometry, read_geometry


def test_geometry_roundtrip_and_write_failure(tmp_path, monkeypatch):
    raw = encode(request())
    handle = parse_request(raw)
    blob = export_geometry(handle)
    assert import_geometry(blob) == plan_geometry(handle)
    target = tmp_path/"geometry.json"
    write_geometry(target, handle)
    assert read_geometry(target) == plan_geometry(handle)
    previous = target.read_bytes()
    with pytest.raises(FileExistsError):
        write_geometry(target, handle)
    assert target.read_bytes() == previous
    import magnetic_survey_bundle as module
    def disk_full(*args):
        raise OSError("injected fsync failure")
    monkeypatch.setattr(module.os, "fsync", disk_full)
    failed = tmp_path/"failed.json"
    with pytest.raises(OSError):
        write_geometry(failed, handle)
    assert not failed.exists()
    assert target.read_bytes() == previous


@pytest.mark.parametrize("attack", ["extra", "hash", "plan", "request", "oversized", "truncated"])
def test_export_closure_rejects_tampering(attack):
    blob = export_geometry(parse_request(encode(request())))
    obj = json.loads(blob)
    if attack == "extra":
        obj["owner_path"] = "../../private"
    elif attack == "hash":
        obj["generation_sha256"] = "a"*64
    elif attack == "plan":
        obj["plan"]["claims"]["full_method_accepted"] = True
    elif attack == "request":
        obj["request"] += " "
    elif attack == "oversized":
        blob = b" "*16777217
    else:
        blob = blob[:-1]
    if attack not in {"oversized", "truncated"}:
        blob = json.dumps(obj).encode()
    with pytest.raises(InputError):
        import_geometry(blob)


@pytest.mark.parametrize("attack", ["extra", "claims", "unit", "partition", "bytes"])
def test_rehashed_hostile_export_cannot_upgrade_plan(attack):
    from magnetic_survey_support import digest
    doc = json.loads(export_geometry(parse_request(encode(request()))))
    if attack == "extra":
        doc["plan"]["engine_accepted"] = True
    elif attack == "claims":
        doc["plan"]["claims"]["field_source_verified"] = True
    elif attack == "unit":
        doc["plan"]["inventory"]["receivers_m"]["dtype"] = "float32"
    elif attack == "partition":
        doc["plan"]["partition"]["outer_rows"]["data"] = [0]
    else:
        doc["request_bytes"] = float(doc["request_bytes"])
    doc.pop("generation_sha256")
    doc["generation_sha256"] = digest(doc)
    with pytest.raises(InputError):
        import_geometry(json.dumps(doc).encode())
