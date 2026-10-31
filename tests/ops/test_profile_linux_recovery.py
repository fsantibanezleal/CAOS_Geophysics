"""Authored terminal recovery controls. No installed-host qualification."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from app import profile_linux_exec as constructor
from test_profile_linux_launch import fixture, supervisor_module


@pytest.mark.parametrize("state",["failed","cancelled","succeeded"])
def test_recorded_terminal_envelope_is_identical_without_relabelling_job(state):
    values = fixture()
    original = constructor.construct_launch(*values)
    values[1].update(state=state,cancel_requested=True)
    before = deepcopy(values)
    assert constructor.construct_recorded_launch(*values) == original
    assert values == before
    with pytest.raises(constructor.LaunchError):
        constructor.construct_launch(*values)


@pytest.mark.parametrize("state",["queued","running","unknown"])
def test_recovery_does_not_accept_pending_or_running_rows(state):
    values = fixture()
    values[1]["state"] = state
    with pytest.raises(constructor.LaunchError):
        constructor.construct_recorded_launch(*values)


@pytest.mark.parametrize("active",[True,False])
def test_recovery_queries_both_exact_groups_without_stopping_them(monkeypatch,active):
    module = supervisor_module()
    identifier = fixture()[1]["id"]
    calls = []
    def run(command,**kwargs):
        calls.append(command)
        return SimpleNamespace(stdout=(b"MainPID=123\nActiveState=active\nSubState=running\nControlGroup=\n" if active else
            b"MainPID=0\nActiveState=inactive\nSubState=dead\nControlGroup=\n"))
    monkeypatch.setattr(module.subprocess,"run",run)
    monkeypatch.setattr(module.Path,"exists",lambda self:False)
    if active:
        with pytest.raises(ValueError,match="recovery_active_unit"):
            module.recovery_extinction(identifier)
    else:
        result = module.recovery_extinction(identifier)
        assert set(result) == {"geophysics-profile-"+identifier+".service","geophysics-profile-guardian-"+identifier+".scope"}
        assert len(calls) == 2
    assert all(command[:2] == ["/usr/bin/systemctl","show"] for command in calls)


def records():
    config,job,data,raw,origin = fixture()
    job["state"] = "failed"
    packet = dict(job=job,dataset=data,raw=raw,origin=origin,bodies={})
    expected = constructor.recorded_installation_binding(config,job,data,raw,origin)
    launch = constructor.construct_recorded_launch(config,job,data,raw,origin)
    plan = dict(schema="geophysics.profile-linux-custody-plan/v1",job_id=job["id"],
        held_bytes=data["byte_count"]+raw["byte_count"],request_sha256=job["request_sha256"],
        dataset_sha256=data["sha256"],raw_sha256=raw["sha256"],invocation_sha256=expected["invocation_sha256"])
    receipt = dict(schema="geophysics.profile-linux-execution/v1",job_id=job["id"],unit=launch["unit"],
        request_sha256=job["request_sha256"],dataset_sha256=data["sha256"],raw_sha256=raw["sha256"],**expected)
    return config,packet,plan,receipt


def test_recovery_requires_owned_plan_and_receipt_from_exact_installation():
    module = supervisor_module()
    config,packet,plan,receipt = records()
    launch,expected = module.validate_recovery_records(config,constructor,packet,plan,receipt)
    assert expected["invocation_sha256"] == plan["invocation_sha256"]
    assert launch["custody"].startswith(config["custody_root"]+"/")


@pytest.mark.parametrize("change",[
    lambda c,p,l,r:l.update(held_bytes=1),
    lambda c,p,l,r:l.update(extra="unknown"),
    lambda c,p,l,r:r.update(configuration_sha256="9"*64),
    lambda c,p,l,r:r.update(invocation_sha256="9"*64),
    lambda c,p,l,r:r.update(job_id=fixture()[1]["id"]),
    lambda c,p,l,r:r.update(unit="unrelated.service"),
    lambda c,p,l,r:r["source_hashes"].update({"scripts/profile_linux_child.py":"9"*64}),
    lambda c,p,l,r:p["job"].update(state="running"),
])
def test_changed_recovery_relations_refuse_before_deleting_any_bytes(change):
    values = records()
    change(*values)
    with pytest.raises(ValueError):
        supervisor_module().validate_recovery_records(values[0],constructor,*values[1:])
