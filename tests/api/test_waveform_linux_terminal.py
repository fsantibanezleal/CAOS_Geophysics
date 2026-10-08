"""Authored historical terminal contracts, never native execution or queue proof."""
from copy import deepcopy
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.waveform_result import checked_resources
from app.errors import ApiError
from app.waveform_linux_execution import expected_job, validate_terminal
from waveform_m08_installation import SOURCE_FILES, canonical, sha


def native_fixture():
    path = Path(__file__).with_name("test_waveform_linux_resources.py")
    spec = importlib.util.spec_from_file_location("authored_native_contract", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    receipt = module.measured()
    return receipt, module.released(receipt)


def packet():
    installation = {key:"b"*64 for key in
                    ("configuration_sha256","python_sha256","environment_sha256","invocation_sha256")}
    installation["source_hashes"] = {name:"e"*64 for name in SOURCE_FILES}
    job = SimpleNamespace(**{name:str(uuid4()) for name in ("id","owner_id","project_id","dataset_id")},
        dataset_sha256="c"*64,request_sha256="d"*64,method_id="seismic.waveform-qc-classical/v1",
        request_json={"implementation_sha256":sha(canonical(installation["source_hashes"])),
                      "scientific_request_sha256":"f"*64,"waveform_sources":{}})
    native,release = native_fixture()
    from waveform_m08_guardian import guardian_names
    terminal = dict(schema="geophysics.waveform-linux-execution/v1",job=expected_job(job),sources={},
        installation=installation,stage=dict(device=0,inode=7),
        root_custody=dict(device=0,inode=8,plan_sha256="a"*64),
        outcome=dict(status="computed",reason="measured",run_id=native["run_id"],
                     receipt_sha256=sha(canonical(native)),release_sha256=sha(canonical(release)),runtime_authorized=False),
        lifecycle=dict(extinction_proved=True,science_quiescent_ns=native["stable_final_ns"],
            caller=dict(reason=None,started_ns=None),run_id=native["run_id"],admission_sha256=native["admission_sha256"],
            units=dict(zip(("service","accounting","guardian"),guardian_names(native["run_id"]),strict=True)),
            guardian={key:value for key,value in native["guardian"].items() if key != "status"},
            final_counters={**{key:native[key] for key in ("cpu_ns","user_cpu_ns","system_cpu_ns","peak_charge_bytes")},
                            "active_tasks":0}),native=dict(eligibility=native,release=release),
        calculation_sha256="1"*64,
        members=[dict(name=name,bytes=1,sha256="2"*64) for name in ("calculation.json","manifest.json","receipt.json")])
    payload = dict(scientific_status="computed",calculation_sha256=terminal["calculation_sha256"],members=deepcopy(terminal["members"]),
                   resources=checked_resources(native,release))
    return job,terminal,payload


def test_historical_complete_terminal_never_reads_current_installation(monkeypatch):
    import waveform_m08_installation as authority
    monkeypatch.setattr(authority,"read_installation",lambda **_:pytest.fail("historical config read"))
    job,terminal,payload = packet()
    assert validate_terminal(terminal,job,payload=payload) == terminal
    assert validate_terminal(terminal,job,terminal["stage"],terminal["installation"],payload=payload) == terminal


@pytest.mark.parametrize("mutate",[
    lambda r:r.update(extra=True),lambda r:r["job"].update(owner_id=str(uuid4())),
    lambda r:r["job"].update(request_sha256="0"*64),lambda r:r.update(sources={"foreign":True}),
    lambda r:r["installation"].update(configuration_sha256=None),
    lambda r:r["installation"]["source_hashes"].update({next(iter(SOURCE_FILES)):"0"*64}),
    lambda r:r["stage"].update(inode=True),lambda r:r["root_custody"].update(plan_sha256="bad"),
    lambda r:r["lifecycle"].update(extinction_proved=False),
    lambda r:r["lifecycle"]["final_counters"].update(active_tasks=1),
    lambda r:r["lifecycle"]["final_counters"].update(cpu_ns=0),
    lambda r:r["lifecycle"]["guardian"].update(scope_removed=False),
    lambda r:r["native"]["release"].update(all_native_owned_handles_closed=False),
    lambda r:r["native"]["eligibility"].update(memory_kind="rss"),
    lambda r:r["outcome"].update(runtime_authorized=True),
    lambda r:r["members"].append(deepcopy(r["members"][0])),
])
def test_changed_or_unproved_terminal_refuses(mutate):
    job,terminal,payload = packet()
    mutate(terminal)
    with pytest.raises((ValueError,ApiError)):
        validate_terminal(terminal,job,payload=payload)


def test_retained_prelaunch_installation_and_stage_are_independent():
    job,terminal,payload = packet()
    wrong = deepcopy(terminal["installation"])
    wrong["invocation_sha256"] = "0"*64
    with pytest.raises(ValueError):
        validate_terminal(terminal,job,installation=wrong,payload=payload)
    with pytest.raises(ValueError):
        validate_terminal(terminal,job,stage=dict(device=0,inode=9),payload=payload)


@pytest.mark.parametrize("reason",["cancelled","caller_lost"])
def test_proved_cancel_and_caller_loss_are_not_measured_success(reason):
    job,terminal,_ = packet()
    terminal.update(outcome=dict(status="cancelled",reason=reason,runtime_authorized=False),
                    native=None,calculation_sha256=None,members=[])
    life = terminal["lifecycle"]
    life["caller"] = dict(reason=reason,started_ns=life["science_quiescent_ns"]-1)
    life["cancel_to_quiescence_ns"] = 1
    assert validate_terminal(terminal,job) == terminal
    life["cancel_to_quiescence_ns"] += 1
    with pytest.raises(ValueError):
        validate_terminal(terminal,job)


def test_terminal_is_bounded_before_any_classification():
    job,terminal,_ = packet()
    terminal.update(outcome=dict(status="failed",reason="x"*65536,runtime_authorized=False),
                    native=None,calculation_sha256=None,members=[])
    with pytest.raises(ValueError):
        validate_terminal(terminal,job)


def test_quiescence_cannot_precede_native_final_seal():
    job,terminal,payload = packet()
    terminal["lifecycle"]["science_quiescent_ns"] = 1
    with pytest.raises(ValueError):
        validate_terminal(terminal,job,payload=payload)
