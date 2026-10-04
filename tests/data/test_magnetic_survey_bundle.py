"""Geometry-only export closure, not future inverse-bundle durability."""

import json
import pytest
from magnetic_survey_support import encode, request
from magnetic_survey_json import InputError, parse_request
from magnetic_survey import plan_geometry
from magnetic_survey_bundle import export_geometry, import_geometry, write_geometry, read_geometry


def test_roundtrip_and_interrupted_generation(tmp_path, monkeypatch):
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
