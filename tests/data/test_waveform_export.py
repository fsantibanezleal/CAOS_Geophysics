"""Ordinary strict export/reopen controls on temp fixtures only."""

import hashlib
import importlib
import json
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "data-pipeline"))
sys.path.insert(0, str(ROOT / "tests/data"))
from test_waveform_input import source, inventory, request
from waveform_processing import process_waveform_record
from waveform_evaluation import seal_result, evaluate_waveform_candidates
from waveform_input import WaveformInputError


def exporter():
    return importlib.import_module("waveform_m08_export")


def result():
    return process_waveform_record(source(), inventory(), request())


def test_plan_is_precouned_exact_names_and_chunked_without_array_copy():
    module = exporter()
    out = result()
    sealed = seal_result(out)
    plan = module.plan_export(out, sealed)
    assert plan.total_bytes <= 33554432
    assert plan.calculation_sha256 == sealed.calculation_sha256
    assert "calculation.json" in plan.names and "receipt.json" in plan.names
    assert not any("/" in name or ".." in name for name in plan.names)
    for member in plan.members:
        chunks = list(module.member_chunks(member))
        assert all(0 < len(chunk) <= 65536 for chunk in chunks)
        assert sum(map(len, chunks)) == member.bytes
        assert hashlib.sha256(b"".join(chunks)).hexdigest() == member.sha256
        if member.name.endswith(".bin"):
            assert type(member.data) is memoryview and member.data.readonly


@pytest.mark.parametrize("change", ["wrong_seal", "nonfinite", "unknown_array", "qc_physics"])
def test_invalid_result_or_seal_never_gets_an_export_plan(change):
    module = exporter()
    out = result()
    sealed = seal_result(out)
    if change == "wrong_seal":
        sealed = type(sealed)(sealed.metadata_bytes, "0" * 64)
    elif change == "nonfinite":
        data = out.arrays[(0, "physical_native")]
        data.setflags(write=True)
        data[0] = np.nan
        data.setflags(write=False)
    elif change == "unknown_array":
        out.arrays[(0, "unknown")] = out.arrays[(0, "counts")]
    else:
        out.metadata["status"] = "qc_only"
        out.metadata["candidates"] = None
    with pytest.raises(WaveformInputError):
        module.plan_export(out, sealed)


def test_evaluation_bound_and_unknown_metadata_fail_before_plan():
    module = exporter()
    out = result()
    sealed = seal_result(out)
    for raw in (b"x" * 2097153, b'{"schema":"unknown"}', b'{"x":NaN}', b'{"x":1,"x":2}'):
        with pytest.raises(WaveformInputError):
            module.plan_export(out, sealed, evaluation=raw)


def test_actual_separate_evaluation_can_be_exported_with_exact_seal(tmp_path):
    module = exporter()
    files = importlib.import_module("waveform_m08_files")
    out = result()
    sealed = seal_result(out)
    reference = {
        "schema": "caos.waveform-analyst-references.v1",
        "event_id": "1",
        "source": {
            "raw_sha256": "0" * 64,
            "citation": "authored empty-reference control",
            "rights": "private-use-attested",
        },
        "selection_sealed_before_scoring": True,
        "references": [],
    }
    evaluated = evaluate_waveform_candidates(sealed, json.dumps(reference).encode())
    assert evaluated["status"] == "not_evaluable"
    raw = json.dumps(evaluated).encode()
    plan = module.plan_export(out, sealed, evaluation=raw)
    with files.create_output(tmp_path / "new", trusted_parent=tmp_path) as directory:
        module.write_export(plan, directory)
        assert module.verify_export(directory) == sealed
    evaluated["unknown"] = 1
    with pytest.raises(WaveformInputError):
        module.plan_export(out, sealed, evaluation=json.dumps(evaluated).encode())


def test_plan_hash_detects_mutation_during_streaming():
    module = exporter()
    out = result()
    plan = module.plan_export(out, seal_result(out))
    member = next(m for m in plan.members if m.name == "c00-counts.bin")
    out.arrays[(0, "counts")].setflags(write=True)
    out.arrays[(0, "counts")][0] += 1
    out.arrays[(0, "counts")].setflags(write=False)
    with pytest.raises(WaveformInputError):
        list(module.member_chunks(member))


def test_ordinary_export_roundtrip_is_not_native_resource_acceptance(tmp_path):
    module = exporter()
    files = importlib.import_module("waveform_m08_files")
    out = result()
    plan = module.plan_export(out, seal_result(out))
    with files.create_output(tmp_path / "new", trusted_parent=tmp_path) as directory:
        receipt = module.write_export(plan, directory)
        reopened = module.verify_export(directory)
        assert reopened.calculation_sha256 == plan.calculation_sha256
        assert receipt["manifest_sha256"] == hashlib.sha256((tmp_path / "new/manifest.json").read_bytes()).hexdigest()
        assert json.loads((tmp_path / "new/receipt.json").read_bytes())["runtime_authorized"] is False
    assert not (tmp_path / "new/manifest.pending").exists()


@pytest.mark.parametrize("channels", [1, 3])
def test_real_multichannel_and_qc_count_only_export(tmp_path, channels):
    module, files = exporter(), importlib.import_module("waveform_m08_files")
    raw, xml, req = source(), inventory(), request()
    if channels == 3:
        start, stop = xml.index(b'<Channel code="BHZ"'), xml.index(b"</Channel>") + len(b"</Channel>")
        channel = xml[start:stop]
        names = ("BHZ", "BHN", "BHE")
        xml = xml[:start] + b"".join(channel.replace(b'code="BHZ"', f'code="{n}"'.encode()) for n in names) + xml[stop:]
        inputs = []
        for name in names:
            part = bytearray(raw)
            for offset in range(0, len(part), 4096):
                part[offset + 15 : offset + 18] = name.encode()
            inputs.append(bytes(part))
        raw = b"".join(inputs)
        req["channels"] = [{**req["channels"][0], "channel": n} for n in names]
        req["adc_rails"] = [None] * 3
    computed = process_waveform_record(raw, xml, req)
    assert computed.metadata["status"] == "computed"
    assert len(computed.metadata["channels"]) == channels
    with files.create_output(tmp_path / "computed", trusted_parent=tmp_path) as owned:
        module.write_export(module.plan_export(computed, seal_result(computed)), owned)
    with files.open_output(tmp_path / "computed") as readonly:
        assert module.verify_export(readonly) == seal_result(computed)
    qc = process_waveform_record(source([1] * 4000), inventory(), request())
    assert qc.metadata["status"] == "qc_only"
    assert set(qc.arrays) == {(0, "counts")}
    with files.create_output(tmp_path / "qc", trusted_parent=tmp_path) as owned:
        module.write_export(module.plan_export(qc, seal_result(qc)), owned)
        assert module.verify_export(owned) == seal_result(qc)


@pytest.mark.parametrize("change", ["hash", "extra", "missing", "unknown_schema", "unknown_name", "nonfinite"])
def test_reopen_detects_invalid_or_unknown_export_members(tmp_path, change):
    module = exporter()
    files = importlib.import_module("waveform_m08_files")
    out = result()
    with files.create_output(tmp_path / "new", trusted_parent=tmp_path) as directory:
        module.write_export(module.plan_export(out, seal_result(out)), directory)
        if change == "extra":
            (tmp_path / "new/extra").write_bytes(b"x")
        elif change == "missing":
            (tmp_path / "new/c00-counts.bin").unlink()
        elif change in ("unknown_schema", "unknown_name"):
            path = tmp_path / "new/manifest.json"
            manifest = json.loads(path.read_bytes())
            if change == "unknown_schema":
                manifest["schema"] = "unknown"
            else:
                manifest["files"][0]["name"] = "../escape"
            path.write_text(json.dumps(manifest), encoding="utf-8")
        elif change == "nonfinite":
            # Correct byte hash alone must not authenticate a NaN scientific product.
            path = tmp_path / "new/c00-physical_native.bin"
            data = bytearray(path.read_bytes())
            import struct

            data[:8] = struct.pack("<d", float("nan"))
            path.write_bytes(data)
        else:
            path = tmp_path / "new/c00-counts.bin"
            data = bytearray(path.read_bytes())
            data[0] ^= 1
            path.write_bytes(data)
        with pytest.raises(WaveformInputError):
            module.verify_export(directory)


def test_inclusive_export_cap_and_boolean_size_rejected_before_member_open():
    module = exporter()
    manifest = {
        "schema": module.SCHEMA,
        "status": "qc_only",
        "calculation_sha256": "0" * 64,
        "files": [
            {"name": "calculation.json", "bytes": 1, "sha256": "0" * 64},
            {"name": "receipt.json", "bytes": module.TOTAL_CAP, "sha256": "0" * 64},
        ],
    }
    # Includes the manifest itself; neither data buffers nor directory are needed.
    with pytest.raises(WaveformInputError):
        module._manifest(json.dumps(manifest).encode())
    manifest["files"][1]["bytes"] = True
    with pytest.raises(WaveformInputError):
        module._manifest(json.dumps(manifest).encode())


def test_reopen_rejects_nan_even_with_consistent_byte_and_calculation_hashes(tmp_path):
    module, files = exporter(), importlib.import_module("waveform_m08_files")
    out = result()
    with files.create_output(tmp_path / "new", trusted_parent=tmp_path) as directory:
        module.write_export(module.plan_export(out, seal_result(out)), directory)
        path = tmp_path / "new/c00-physical_native.bin"
        import struct

        raw = struct.pack("<d", float("nan")) + path.read_bytes()[8:]
        path.write_bytes(raw)
        digest = hashlib.sha256(raw).hexdigest()
        meta = json.loads((tmp_path / "new/calculation.json").read_bytes())
        next(d for d in meta["array_descriptors"] if d["name"] == "physical_native")["sha256"] = digest
        calculation = module._canonical(meta, module.JSON_CAP)
        identity = hashlib.sha256(calculation).hexdigest()
        (tmp_path / "new/calculation.json").write_bytes(calculation)
        receipt = json.loads((tmp_path / "new/receipt.json").read_bytes())
        receipt["calculation_sha256"] = identity
        (tmp_path / "new/receipt.json").write_bytes(module._canonical(receipt, 65536))
        manifest = json.loads((tmp_path / "new/manifest.json").read_bytes())
        manifest["calculation_sha256"] = identity
        for item in manifest["files"]:
            contents = (tmp_path / "new" / item["name"]).read_bytes()
            item.update(bytes=len(contents), sha256=hashlib.sha256(contents).hexdigest())
        (tmp_path / "new/manifest.json").write_bytes(module._canonical(manifest, module.JSON_CAP))
        with pytest.raises(WaveformInputError):
            module.verify_export(directory)


def test_independent_read_only_reopen_cannot_write_existing_user_directory(tmp_path):
    module, files = exporter(), importlib.import_module("waveform_m08_files")
    out = result()
    plan = module.plan_export(out, seal_result(out))
    with files.create_output(tmp_path / "new", trusted_parent=tmp_path) as directory:
        module.write_export(plan, directory)
    before = {p.name: p.read_bytes() for p in (tmp_path / "new").iterdir()}
    with files.open_output(tmp_path / "new") as reopened:
        assert module.verify_export(reopened) == seal_result(out)
        with pytest.raises(WaveformInputError):
            reopened.create_regular("evaluation.json")
        with pytest.raises(WaveformInputError):
            reopened.publish_pending()
        with pytest.raises(WaveformInputError):
            module.write_export(plan, reopened)
    assert {p.name: p.read_bytes() for p in (tmp_path / "new").iterdir()} == before
