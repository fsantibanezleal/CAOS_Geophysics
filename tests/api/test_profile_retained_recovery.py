"""Portable retained-evidence controls, not privileged Linux qualification."""
from copy import deepcopy
import asyncio
from types import SimpleNamespace

import pytest

from app import profile_linux_recovery as recovery
from app.errors import ApiError
from app.processing_contract import canonical_bytes, sha256
from test_profile_execution_receipt import execution_fixture


def fixture():
    producer,receipt,job,stage = execution_fixture()
    states = {unit:dict(MainPID="0",ActiveState="inactive",SubState="dead",ControlGroup="") for unit in (
        "geophysics-profile-"+job.id+".service","geophysics-profile-guardian-"+job.id+".scope")}
    record = dict(schema="geophysics.profile-linux-recovery/v1",job_id=job.id,
        receipt_sha256=sha256(canonical_bytes(receipt)),intent_sha256="8"*64,installation=deepcopy(job.installation),
        retained_stage_identity=stage,terminal=states,known_root_copies_removed=True)
    return producer,receipt,job,stage,record


def test_root_recovery_proves_only_terminal_custody_not_scientific_success():
    _,receipt,job,stage,record = fixture()
    receipt.update(failure="ValueError",extinction="unproved_retained_debt",guardian_status="failed_retained_debt")
    record["receipt_sha256"] = sha256(canonical_bytes(receipt))
    recovery.validate_recovery(record,receipt,job,job.installation,stage)


@pytest.mark.parametrize("change",[
    lambda r:r.update(known_root_copies_removed=False),lambda r:r.update(job_id="9"*36),
    lambda r:r.update(receipt_sha256="9"*64),lambda r:r.update(intent_sha256="not a digest"),
    lambda r:r.update(extra="unknown"),lambda r:r["installation"].update(invocation_sha256="9"*64),
    lambda r:r["retained_stage_identity"].update(inode=99),
    lambda r:next(iter(r["terminal"].values())).update(ActiveState="active"),
    lambda r:next(iter(r["terminal"].values())).update(MainPID="123"),
    lambda r:next(iter(r["terminal"].values())).update(ControlGroup="/system.slice/unrelated.service"),
    lambda r:next(iter(r["terminal"].values())).update(SubState="running"),
])
def test_incomplete_unrelated_or_changed_recovery_refuses_archive(change):
    _,receipt,job,stage,record = fixture()
    change(record)
    with pytest.raises((ValueError,ApiError)):
        recovery.validate_recovery(record,receipt,job,job.installation,stage)


def test_stage_archives_only_root_declared_members(monkeypatch):
    producer,receipt,_,_,_ = fixture()
    bodies = {"linux-execution.json":canonical_bytes(receipt),"result.json":canonical_bytes(producer),"linux-stderr.txt":b""}
    monkeypatch.setattr(recovery.os,"listdir",lambda fd:list(bodies))
    monkeypatch.setattr(recovery,"regular_at",lambda fd,name,cap:bodies[name])
    inventory = recovery.stage_inventory(1,receipt)
    assert inventory["result.json"] == receipt["retained"]["result.json"]
    bodies["unknown-private-file"] = b"do not remove"
    with pytest.raises((ValueError,ApiError)):
        recovery.stage_inventory(1,receipt)


def test_changed_stage_bytes_do_not_become_archived_as_verified(monkeypatch):
    producer,receipt,_,_,_ = fixture()
    producer["profile"] = {"changed":True}
    bodies = {"linux-execution.json":canonical_bytes(receipt),"result.json":canonical_bytes(producer),"linux-stderr.txt":b""}
    monkeypatch.setattr(recovery.os,"listdir",lambda fd:list(bodies))
    monkeypatch.setattr(recovery,"regular_at",lambda fd,name,cap:bodies[name])
    with pytest.raises((ValueError,ApiError)):
        recovery.stage_inventory(1,receipt)


def test_recovery_resolves_real_terminal_owned_sql_relations_before_privileged_command(make_harness,monkeypatch):
    from test_profile_jobs import owned_dataset, profile_harness
    harness = profile_harness(make_harness)
    project,_,dataset,metadata = owned_dataset(harness)
    path = f"/api/projects/{project['id']}/jobs"
    response = harness.request("POST",path,json=dict(dataset_id=dataset["dataset_id"],method_id=metadata["method"],parameters={}))
    assert response.status_code == 202
    identifier = response.json()["job_id"]
    assert harness.request("POST",path+"/"+identifier+"/cancel").json()["state"] == "cancelled"
    class StopBeforePrivilege(RuntimeError):
        pass
    def checked_command(settings,job,**kwargs):
        assert settings == harness.settings and job.id == identifier and job.state == "cancelled"
        assert job.dataset_id == dataset["dataset_id"] and job.project_id == project["id"]
        assert kwargs == {"with_configuration":True}
        raise StopBeforePrivilege()
    monkeypatch.setattr(recovery,"os",SimpleNamespace(name="posix",geteuid=lambda:61901))
    monkeypatch.setattr(recovery,"installed_command",checked_command)
    with pytest.raises(StopBeforePrivilege):
        asyncio.run(recovery.recover_job(harness.settings,identifier))
    assert not (harness.settings.data_dir/".profile-retained").exists()
    assert harness.client.get(path+"/"+identifier).json()["state"] == "cancelled"
