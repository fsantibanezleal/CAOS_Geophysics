"""Authored execution-binding controls, not Linux or scientific qualification."""
from copy import deepcopy
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.profile_execution import attach_execution, validate_execution, validate_terminal
from app.profile_linux_exec import SOURCE_FILES
from app.processing_contract import canonical_bytes, sha256


def execution_fixture():
    identifier = str(uuid4())
    job = SimpleNamespace(id=identifier, dataset_sha256="a"*64, request_sha256="b"*64,
        request_json={"raw_sha256":"c"*64,"profile_child_sha256":"d"*64,
                      "profile_code_hashes":{name:"d"*64 for name in ("ert.py","supplied_profiles.py","profile_mesh.py")}},
        preflight={"memory_limit_bytes":2*1024**3,"scratch_limit_bytes":64*1024**2,"wall_limit_seconds":600})
    producer = dict(job_id=identifier,dataset_sha256=job.dataset_sha256,request_sha256=job.request_sha256,
                    raw_sha256=job.request_json["raw_sha256"],raw_bytes=3,profile={"placeholder_for_contract_control":True})
    stage = dict(device=1,inode=2)
    scope = "geophysics-profile-guardian-"+identifier+".scope"
    receipt = dict(schema="geophysics.profile-linux-execution/v1",job_id=identifier,
        request_sha256=job.request_sha256,dataset_sha256=job.dataset_sha256,raw_sha256=job.request_json["raw_sha256"],
        environment_sha256="e"*64,unit="geophysics-profile-"+identifier+".service",
        terminal=dict(MainPID="0",SubState="dead",Result="success",ExecMainStatus="0",ControlGroup=""),
        stop_reason=None,failure=None,launch_attempted=True,extinction="proved",guardian_status="complete",
        guardian_scope=dict(scope=scope,group="/system.slice/"+scope,memory_limit_bytes=128*1024**2,
            tasks_max=16,wall_limit_seconds=630,identity_transport="PIDFDs/ah",manager_job="/org/freedesktop/systemd1/job/123"),
        invocation_sha256="f"*64,source_hashes={name:"d"*64 for name in SOURCE_FILES},
        configuration_sha256="1"*64,python_sha256="2"*64,
        mounted_input_identities={"original":dict(device=1,inode=3,bytes=3,sha256="c"*64),
                                 "dataset.json":dict(device=1,inode=4,bytes=100,sha256="a"*64)},
        retained_stage_identity=stage,wall_seconds=10.,resources=dict(sampled_root_rss_peak_bytes=1000,
            rss_samples=20,kernel_memcg_peak_bytes=900, sampled_unit_rss_peak_bytes=1100,unit_rss_samples=20,
            memcg_reads=20,memory_events="oom 0\noom_kill 0\n",cgroup_events="populated 0\n",exact_group_removed=True,
            hard_writable_scratch_bytes=64*1024**2,held_input_bytes=103),
        retained={"result.json":dict(bytes=len(canonical_bytes(producer)),sha256=sha256(canonical_bytes(producer))),
                  "stderr.txt":dict(bytes=0,sha256=sha256(b""))},originals_reverified=True,
        held_inputs_state="declared_copies_removed",cpu_accounting_admitted=False,host_admission=False)
    return producer,receipt,job,stage


def test_execution_is_durable_outer_metadata_without_changing_scientific_producer():
    producer,receipt,job,stage = execution_fixture()
    encoded = attach_execution(canonical_bytes(producer),receipt,job,stage)
    assert encoded["profile"] == producer["profile"] and encoded["linux_execution"] == receipt
    validate_execution(encoded,job)
    assert "linux_execution" not in producer


@pytest.mark.parametrize("change",[
    lambda r:r.update(job_id=str(uuid4())),lambda r:r.update(request_sha256="3"*64),
    lambda r:r.update(dataset_sha256="3"*64),lambda r:r.update(raw_sha256="3"*64),
    lambda r:r.update(extinction="unproved_retained_debt"),lambda r:r.update(guardian_status="failed_retained_debt"),
    lambda r:r.update(failure="ValueError"),lambda r:r.update(stop_reason="owner_cancel"),
    lambda r:r.update(launch_attempted=False),lambda r:r.update(originals_reverified=False),
    lambda r:r.update(held_inputs_state="retained_unverified"),lambda r:r.update(cpu_accounting_admitted=True),
    lambda r:r.update(host_admission=True),lambda r:r["terminal"].update(MainPID="123"),
    lambda r:r["terminal"].update(ExecMainStatus="2"),lambda r:r["terminal"].update(Result="oom-kill"),
    lambda r:r["retained"]["result.json"].update(sha256="3"*64),
    lambda r:r["source_hashes"].update({"data-pipeline/ert.py":"3"*64}),
    lambda r:r["mounted_input_identities"]["original"].update(sha256="3"*64),
    lambda r:r["mounted_input_identities"]["dataset.json"].update(bytes=-1),
    lambda r:r["resources"].update(kernel_memcg_peak_bytes=3*1024**3),
    lambda r:r["resources"].update(unit_rss_samples=0),lambda r:r.update(wall_seconds=float("nan")),
    lambda r:r.update(extra="unknown"),lambda r:r["guardian_scope"].update(identity_transport="PIDs/au"),
])
def test_altered_or_unproved_execution_cannot_be_published(change):
    producer,receipt,job,stage = execution_fixture()
    change(receipt)
    with pytest.raises(ValueError):
        attach_execution(canonical_bytes(producer),receipt,job,stage)


def test_stage_replacement_and_changed_producer_bytes_refuse_publication():
    producer,receipt,job,stage = execution_fixture()
    with pytest.raises(ValueError):
        attach_execution(canonical_bytes(producer),receipt,job,dict(device=1,inode=5))
    producer["profile"] = {"changed":True}
    with pytest.raises(ValueError):
        attach_execution(canonical_bytes(producer),receipt,job,stage)


def test_stored_receipt_reconstructs_exact_producer_digest_on_every_read():
    producer,receipt,job,stage = execution_fixture()
    encoded = attach_execution(canonical_bytes(producer),receipt,job,stage)
    encoded["profile"] = {"changed_after_publication":True}
    with pytest.raises(ValueError):
        validate_execution(encoded,job)


def test_original_windows_payload_does_not_acquire_linux_claims():
    producer,_,job,_ = execution_fixture()
    validate_execution(deepcopy(producer),job)


def test_cancelled_execution_proves_extinction_without_claiming_scientific_success():
    producer,receipt,job,stage = execution_fixture()
    receipt.update(stop_reason="owner_cancel",originals_reverified=False,held_inputs_state="retained_unverified")
    receipt["terminal"].update(Result="signal",ExecMainStatus="9")
    validate_terminal(receipt,job,stage)
    with pytest.raises(ValueError):
        attach_execution(canonical_bytes(producer),receipt,job,stage)


@pytest.mark.parametrize("change",[
    lambda r:r.update(extinction="unproved_retained_debt"),
    lambda r:r.update(guardian_status="failed_retained_debt"),
    lambda r:r["terminal"].update(MainPID="12"),
    lambda r:r["resources"].update(exact_group_removed=False,cgroup_events="populated 1\n"),
    lambda r:r.update(request_sha256="3"*64),
    lambda r:r["terminal"].update(SubState="running"),
    lambda r:r["guardian_scope"].update(identity_transport="PIDs/au"),
    lambda r:r["guardian_scope"].update(scope="unrelated.scope"),
])
def test_cancel_request_is_not_extinction_proof(change):
    _,receipt,job,stage = execution_fixture()
    change(receipt)
    with pytest.raises(ValueError):
        validate_terminal(receipt,job,stage)


def test_linux_environment_cannot_enable_legacy_soft_supervision(monkeypatch):
    from app import config
    monkeypatch.setattr(config.sys,"platform","linux")
    monkeypatch.setenv("GEOPHYSICS_PROFILE_ONLINE_ENABLED","1")
    monkeypatch.delenv("GEOPHYSICS_PROFILE_LINUX_SUPERVISOR",raising=False)
    with pytest.raises(ValueError,match="GEOPHYSICS_PROFILE_LINUX_SUPERVISOR"):
        config.configured_profile_supervisor()
    monkeypatch.setenv("GEOPHYSICS_PROFILE_ONLINE_ENABLED","0")
    assert config.configured_profile_supervisor() is None


def test_windows_environment_retains_its_explicit_separate_lane(monkeypatch):
    from app import config
    monkeypatch.setattr(config.sys,"platform","win32")
    monkeypatch.setenv("GEOPHYSICS_PROFILE_ONLINE_ENABLED","1")
    monkeypatch.delenv("GEOPHYSICS_PROFILE_LINUX_SUPERVISOR",raising=False)
    assert config.configured_profile_supervisor() is None
