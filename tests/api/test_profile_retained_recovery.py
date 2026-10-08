"""Portable retained-evidence controls, not privileged Linux qualification."""
from copy import deepcopy
import asyncio
from types import SimpleNamespace

import pytest

from app import profile_linux_recovery as recovery
from app.errors import ApiError
from app.processing_contract import canonical_bytes, sha256
from test_profile_execution_receipt import execution_fixture
from uuid import uuid4


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


def ownership_fixture():
    owner,project,job,dataset,asset,source = (str(uuid4()) for _ in range(6))
    return dict(owner_id=owner,project_id=project,job_id=job,dataset_id=dataset,raw_asset_id=asset,
        source_id=source,method_id="ert.topographic-profile/v1",terminal_state="cancelled",
        dataset_sha256="d"*64,raw_sha256="e"*64,request_sha256="f"*64)


def manifest_fixture():
    owner = ownership_fixture()
    return dict(schema="geophysics.profile-retained-stage/v2",job_id=owner["job_id"],
        request_sha256=owner["request_sha256"],ownership=owner,installation={},stage_identity={},
        members={},recovery={},uncommitted_duplicate=None)


def test_manifest_carries_explicit_surviving_relation_not_directory_inference():
    manifest = manifest_fixture()
    recovery.validate_manifest_ownership(manifest,deepcopy(manifest["ownership"]))


@pytest.mark.parametrize("field",sorted(recovery.OWNERSHIP_KEYS))
def test_each_archive_identity_is_frozen_to_live_owned_relation(field):
    manifest = manifest_fixture()
    expected = deepcopy(manifest["ownership"])
    manifest["ownership"][field] = str(uuid4()) if field.endswith("_id") and field != "method_id" else (
        "succeeded" if field == "terminal_state" else "traveltime.first-arrival-profile/v1" if field == "method_id" else "a"*64)
    with pytest.raises((ValueError,ApiError)):
        recovery.validate_manifest_ownership(manifest,expected)


@pytest.mark.parametrize("change",[
    lambda m:m.update(schema="geophysics.profile-retained-stage/v1"),
    lambda m:m["ownership"].update(extra="unknown"),lambda m:m["ownership"].pop("owner_id"),
    lambda m:m["ownership"].update(owner_id="not-a-uuid"),
    lambda m:m["ownership"].update(raw_sha256="not-a-digest"),
    lambda m:m["ownership"].update(terminal_state="running"),
    lambda m:m["ownership"].update(method_id="gravity.survey/v1"),
    lambda m:m.update(job_id=str(uuid4())),lambda m:m.update(request_sha256="a"*64),
])
def test_unknown_legacy_incomplete_or_contradictory_ownership_refuses(change):
    manifest = manifest_fixture()
    change(manifest)
    with pytest.raises((ValueError,ApiError)):
        recovery.validate_manifest_ownership(manifest)
