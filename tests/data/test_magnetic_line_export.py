"""Exact local Result and immutable rights/custody; not field acceptance."""
from copy import deepcopy
from hashlib import sha256
import importlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from test_magnetic_lines import modules


def processor():
    modules()
    return importlib.import_module("magnetic_lines")


def test_array_identity_units_and_null_are_not_zero():
    c, _ = modules()
    p = processor()
    d = p.array_descriptor([0., None], ["a", "b"], [[], ["missing_value"]], [2], "nT")
    assert d["values"] == [0., None]
    assert d["values_sha256"] == c.digest([0., None])
    assert d["ordered_ids_sha256"] == c.digest(["a", "b"])
    for change in ({"values": [0., 0.]}, {"masks": [[], []]}, {"shape": [3]}, {"extra": 1}):
        bad = deepcopy(d)
        bad.update(change)
        with pytest.raises(c.MagneticContractError):
            p.validate_array_descriptor(bad, ["a", "b"])
    for values in ([True, 0.], [float("nan"), 0.], [None, 0.]):
        with pytest.raises(c.MagneticContractError):
            p.array_descriptor(values, ["a", "b"], [[], []], [2], "nT")


def test_result_parser_preallocation_and_closed_root():
    c, _ = modules()
    p = processor()
    for raw in (b'{"schema":NaN}', b'{"x":1,"x":2}', b"["*17+b"0"+b"]"*17, b"{} trailing", b"{}", b'{"x":1e9999}'):
        with pytest.raises(c.MagneticContractError):
            p.parse_result(raw)
    with pytest.raises(c.MagneticContractError) as caught:
        p.parse_result(b" "*(8*1024**2+1))
    assert caught.value.error["code"] == "resource_refused"


@pytest.fixture(scope="module")
def actual_result():
    c, g = modules()
    p = processor()
    raw, meta, req = g.instrument_input(raw_mirroring="allowed")
    originals = (raw, c.canonical_bytes(meta), c.canonical_bytes(req))
    result = p.run_result(*originals, run_id="test-S3")
    return originals, result


def test_exact_result_source_bindings_and_objectives(actual_result):
    c, _ = modules()
    p = processor()
    originals, result = actual_result
    p.validate_result(result)
    assert len(result) == 19
    assert result["input"]["csv_sha256"] == sha256(originals[0]).hexdigest()
    assert result["request"]["bytes_sha256"] == sha256(originals[2]).hexdigest()
    assert result["fit"]["production_fit_count"] == 25
    assert all(f["objective"] is not None for a in result["fit"]["candidates"] for f in a["folds"])
    assert result["evaluation"]["field_acceptance"] == "unresolved"
    assert result["evaluation"]["synthetic_acceptance"] == "unresolved"
    assert result["verdict"]["overall"] == "unresolved"
    assert result["environment"]["source_revision"] != "0"*64
    assert result["fit"]["residuals"]["shape"] == [363]
    assert sum(v is not None for v in result["fit"]["residuals"]["values"]) == 33
    assert len(result["geometry"]["line_statistics"]) == 11
    assert p.parse_result(c.canonical_bytes(result)) == result
    for location, key in (("environment", "extra"), ("input", "extra"), ("fit", "extra")):
        bad = deepcopy(result)
        bad[location][key] = True
        with pytest.raises(c.MagneticContractError):
            p.validate_result(bad)
    bad = deepcopy(result)
    bad["fit"]["source_coefficients"]["unit"] = "nT"
    with pytest.raises(c.MagneticContractError):
        p.validate_result(bad)
    bad = deepcopy(result)
    bad["evaluation"]["outer"]["rmse_nT"] = 0.
    with pytest.raises(c.MagneticContractError):
        p.validate_result(bad)


def test_missing_typed_reference_not_guessed():
    c, g = modules()
    p = processor()
    raw, meta, req = g.control_input("S1")
    with pytest.raises(c.MagneticContractError) as caught:
        p.run_result(raw, c.canonical_bytes(meta), c.canonical_bytes(req), run_id="missing-reference")
    assert caught.value.error["field"] == "result.typed_reference_required"


def test_rehashed_stale_processing_identity_is_not_original_authority(actual_result):
    c, _ = modules()
    p = processor()
    originals, result = actual_result
    for field in ("python_revision", "source_revision", "loaded_modules"):
        bad = deepcopy(result)
        if field=="loaded_modules":
            bad["environment"][field][0]["sha256"] = "0"*64
            bad["environment"]["source_revision"] = c.digest(bad["environment"][field][:3])
        else:
            bad["environment"][field] = "3.12.0" if field=="python_revision" else "0"*64
        bad["environment"]["environment_receipt_sha256"] = c.digest({k:v for k,v in bad["environment"].items() if k!="environment_receipt_sha256"})
        with pytest.raises(c.MagneticContractError):
            p._binding_check(bad, originals)
    changed = (originals[0], originals[1], originals[2]+b" ")
    with pytest.raises(c.MagneticContractError):
        p._binding_check(result, changed)


def test_embedded_auxiliary_raw_denial_is_not_hidden(actual_result, tmp_path):
    c, g = modules()
    p = processor()
    raw, meta, req = g.instrument_input()
    # The real producer will refuse publication, not discard or relabel raw
    # records embedded in its exact canonical request/processor history.
    with pytest.raises(c.MagneticContractError) as caught:
        p.export_run(raw,c.canonical_bytes(meta),c.canonical_bytes(req),tmp_path/"denied")
    assert caught.value.error["code"]=="rights_denied"
    assert not (tmp_path/"denied").exists()


def test_actual_allowlisted_export_replay_and_tamper_before_solver(tmp_path, monkeypatch):
    c, g = modules()
    p = processor()
    raw, meta, req = g.instrument_input(raw_mirroring="allowed")
    req["export_policy"]["raw_requested"] = "include"
    original = (raw,c.canonical_bytes(meta),c.canonical_bytes(req))
    first = tmp_path/"original"
    receipt = p.export_run(*original,first)
    assert receipt["replay_verdict"]=="eligible"
    second = tmp_path/"replayed"
    actual = p.replay_run(first,second)
    assert actual==receipt
    assert {f.name:f.read_bytes() for f in first.iterdir()}=={f.name:f.read_bytes() for f in second.iterdir()}
    # A rehashed original cannot substitute for the pinned dataset/request.
    broken = json.loads((first/"custody.json").read_bytes())
    request = (first/"request.json").read_bytes()+b" "
    (first/"request.json").write_bytes(request)
    for m in broken["members"]:
        if m["relative_path"]=="request.json":
            m.update(sha256=sha256(request).hexdigest(),bytes=len(request))
    (first/"custody.json").write_bytes(c.canonical_bytes(broken))
    monkeypatch.setattr(p,"fit_grid",lambda *a,**k: pytest.fail("Custody refusal must precede solver"))
    with pytest.raises(c.MagneticContractError):
        p.replay_run(first,tmp_path/"bad")
    assert not (tmp_path/"bad").exists()


def test_rights_and_member_custody(actual_result, tmp_path):
    c, _ = modules()
    p = processor()
    originals, result = actual_result
    target = tmp_path / "new"
    receipt = p.export_run(*originals, target, result=result)
    assert receipt["replay_verdict"] == "ineligible"
    assert not (target / "original.csv").exists()
    assert (target / "result.json").read_bytes() == c.canonical_bytes(p.parse_result((target / "result.json").read_bytes()))
    before = {f.name: f.read_bytes() for f in target.iterdir()}
    with pytest.raises(c.MagneticContractError) as caught:
        p.export_run(*originals, target, result=result)
    assert caught.value.error["code"] == "overwrite_refused"
    assert before == {f.name: f.read_bytes() for f in target.iterdir()}
    with pytest.raises(c.MagneticContractError):
        p.replay_run(target, tmp_path / "replayed")
    assert not (tmp_path / "replayed").exists()
    receipt["members"][0]["relative_path"] = "../other"
    (target / "custody.json").write_bytes(c.canonical_bytes(receipt))
    with pytest.raises(c.MagneticContractError):
        p.verify_bundle(target)


def test_paired_scripts_replay_and_no_overwrite(tmp_path):
    p = processor()
    root = Path(p.__file__).resolve().parents[1]
    for name in ("magnetic-lines.ps1", "magnetic-lines.sh"):
        text = (root / "scripts" / name).read_text(encoding="utf-8")
        assert "magnetic_lines.py" in text
        assert "pip install" not in text and "curl" not in text
    completed = subprocess.run([sys.executable, str(root / "data-pipeline" / "magnetic_lines.py"), "run",
        "--csv", str(tmp_path / "absent"), "--metadata", str(tmp_path / "absent"), "--request", str(tmp_path / "absent"),
        "--output-directory", str(tmp_path / "must-not-exist")], capture_output=True, timeout=10)
    assert completed.returncode != 0
    error = json.loads(completed.stdout)
    assert error["code"] == "custody_mismatch"
    assert "Traceback" not in completed.stderr.decode()
    assert str(tmp_path) not in completed.stdout.decode()
    assert not (tmp_path / "must-not-exist").exists()


def resource_controller():
    import importlib.util
    root = Path(processor().__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("m03_resource_review", root / "scripts/check_magnetic_artifacts.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_whole_contract_export_probe_requires_actual_job_before_control_values(tmp_path, monkeypatch):
    m = resource_controller()
    c, _ = modules()
    monkeypatch.setattr(m, "_generator", lambda: pytest.fail("Control values cannot precede real containment"))
    destination = tmp_path/"absent-contract-root"
    with pytest.raises(c.MagneticContractError) as caught:
        m.run_contract_probe(destination, None)
    assert caught.value.error["code"] == "resource_refused"
    assert not destination.exists()


def test_prevalue_study_manifest_separates_ordinary_and_local_source_caps():
    m = resource_controller()
    packet = m.geometry_packet()
    assert packet["magnetic_values_generated"] is False
    assert [s["request"]["equivalent_sources"]["source_geometry"]["max_sources"] for s in packet["studies"]] == [256,320]
    assert [s["preallocation"]["source_limit"] for s in packet["studies"]] == [256,320]
    assert [s["preallocation"]["source_counts"] for s in packet["studies"]] == [[227,137,156,194],[287,168,193,243]]
    assert [s["preallocation"]["peak_dense_bytes_bound"] for s in packet["studies"]] == [15939552,21691872]


@pytest.mark.parametrize("role,declared", (("original.csv",16777217),("sidecar.json",2097153),
    ("request.json",2097153),("environment.json",2097153),("result.json",8388609),("replay.txt",8193),
    ("combined",2097154),("wrong-kind",0),("duplicate",0)))
def test_export_declared_role_bounds_before_any_member_read(tmp_path, monkeypatch, role, declared):
    c, _ = modules()
    p = processor()
    kinds = dict(zip(("original.csv","sidecar.json","request.json","environment.json","replay.txt","result.json"),
        ("original","metadata","request","receipt","replay_recipe","result_array")))
    receipt = dict(schema="magnetic-local-custody/1",input_sha256="0"*64,request_sha256="0"*64,
        environment_sha256="0"*64,result_sha256="0"*64,publication="local_only",replay_verdict="eligible",
        members=[dict(relative_path=name,kind=kind,included=True,permission="allowed",reason=None,
            sha256="0"*64,bytes=declared if name==role else 1) for name,kind in kinds.items()])
    if role == "combined":
        for member in receipt["members"]:
            if member["relative_path"] in ("sidecar.json","request.json"):
                member["bytes"] = declared//2
    elif role == "wrong-kind":
        receipt["members"][-1]["kind"] = "original"
    elif role == "duplicate":
        receipt["members"].append(deepcopy(receipt["members"][0]))
    reads = []
    def bounded(path, limit):
        reads.append(Path(path).name)
        if Path(path).name == "custody.json":
            return c.canonical_bytes(receipt)
        pytest.fail("All declared member limits must be checked before the first body allocation")
    monkeypatch.setattr(c,"read_bounded",bounded)
    with pytest.raises(c.MagneticContractError) as caught:
        p.verify_bundle(tmp_path)
    assert caught.value.error["code"] == ("custody_mismatch" if role in ("wrong-kind","duplicate") else "resource_refused")
    assert reads == ["custody.json"]


@pytest.mark.parametrize("failed", ("accounting", "limits", "memory", "exit", "still_active"))
def test_terminal_resource_counters_fail_closed(failed):
    from types import SimpleNamespace
    m = resource_controller()
    c, _ = modules()
    def query(job, kind, pointer, size, returned):
        if kind == 1:
            pointer._obj.user = 10000000
        else:
            pointer._obj.peak_job_memory = 4096
        return int(failed != ("accounting" if kind == 1 else "limits"))
    def memory(handle, pointer, size):
        pointer._obj.peak_working = 2048
        return int(failed != "memory")
    def exit_code(handle, pointer):
        pointer._obj.value = 259 if failed == "still_active" else 0
        return int(failed != "exit")
    api = SimpleNamespace(QueryInformationJobObject=query, GetExitCodeProcess=exit_code)
    psapi = SimpleNamespace(GetProcessMemoryInfo=memory)
    with pytest.raises(c.MagneticContractError) as caught:
        m.terminal_counters(api, psapi, 1, 2)
    assert caught.value.error["code"] == "resource_refused"


@pytest.mark.parametrize("change", ({"controller_cpu_s": 10.00001}, {"peak_owned_scratch_bytes": 67108865},
    {"peak_tree_rss_bytes": 536870913}, {"peak_job_commit_bytes": 536870913}, {"child_tree_cpu_s": 60.00001},
    {"wall_s": 120.00001}, {"measurement_complete": False}, {"exit_code": 1},
    {"mode": "cancel", "terminal": "cancelled", "exit_code": 2, "post_stop_cpu_s": None, "post_stop_wall_s": 0.01},
    {"mode": "cancel", "terminal": "cancelled", "exit_code": 2, "post_stop_cpu_s": 0., "post_stop_wall_s": 10.00001}))
def test_resource_verdict_has_independent_measured_limits(change):
    m = resource_controller()
    record = dict(mode="probe", terminal="completed", exit_code=0, measurement_complete=True,
        child_tree_cpu_s=60., controller_cpu_s=10., wall_s=120., peak_owned_scratch_bytes=67108864,
        peak_tree_rss_bytes=536870912, peak_job_commit_bytes=536870912, post_stop_cpu_s=None, post_stop_wall_s=None)
    assert m.resource_eligible(record)
    record.update(change)
    assert not m.resource_eligible(record)
