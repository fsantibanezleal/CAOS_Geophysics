"""Authored historical relation controls, not native recovery or cleanup proof."""
from copy import deepcopy
from uuid import uuid4

import pytest

from tests.data.test_waveform_owned_reader import module, records
from waveform_m08_installation import installation_binding


def packet(state="failed", cancelled=False):
    value = module()
    config, record, payload = records(value)
    job = record["job"]
    installation = installation_binding(config,job["id"])
    plan = dict(schema="geophysics.waveform-custody-plan/v1",job_id=job["id"],
        request_sha256=job["request_sha256"],
        input_bytes=sum(item["raw_bytes"] for item in job["request_json"]["waveform_sources"].values())+
            len(value.canonical(job["request_json"]["scientific_request"])),stage=dict(device=0,inode=7),
        installation=installation,record_sha256=value.sha(value.product_bytes(record)))
    receipt = dict(schema="geophysics.waveform-linux-execution/v1",job={
        **{key:job[key] for key in ("id","owner_id","project_id","dataset_id","dataset_sha256","request_sha256","method_id")},
        **{key:job["request_json"][key] for key in ("implementation_sha256","scientific_request_sha256")}},
        sources=deepcopy(job["request_json"]["waveform_sources"]),installation=deepcopy(installation),
        stage=deepcopy(plan["stage"]),root_custody=dict(device=0,inode=8,plan_sha256=value.sha(value.canonical(plan))),
        outcome=dict(status="failed",reason="scientific_rejected",runtime_authorized=False),
        lifecycle=dict(extinction_proved=True),native=None,calculation_sha256=None,members=[])
    job.update(state=state,cancel_requested=cancelled)
    return value,config,record,payload,plan,receipt


@pytest.mark.parametrize("state",["failed","cancelled","succeeded"])
@pytest.mark.parametrize("cancelled",[False,True])
def test_only_historical_terminal_mode_normalizes_the_two_mutable_fields(state,cancelled):
    value,config,record,payload,plan,receipt = packet(state,cancelled)
    before = deepcopy((config,record,payload,plan,receipt))
    keys = value.checked_terminal_relations(config,record["job"]["id"],record,payload,plan,receipt)
    assert keys == {role:asset["storage_key"] for role,asset in record["assets"].items()}
    assert (config,record,payload,plan,receipt) == before
    with pytest.raises(ValueError):
        value.checked_relations(config,record["job"]["id"],record,payload)


def test_recorded_source_identity_is_not_replaced_by_current_installation():
    value,config,record,payload,plan,receipt = packet()
    config["source_hashes"] = {key:"f"*64 for key in config["source_hashes"]}
    assert value.checked_terminal_relations(config,record["job"]["id"],record,payload,plan,receipt)
    assert receipt["installation"]["source_hashes"] != config["source_hashes"]
    # Current running dispatch still refuses that old admitted source.
    live = deepcopy(record)
    live["job"].update(state="running",cancel_requested=False)
    with pytest.raises(ValueError):
        value.checked_relations(config,record["job"]["id"],live,payload)


@pytest.mark.parametrize("mutate",[
    lambda r,p,t:r["job"].update(state="running"),
    lambda r,p,t:r["job"].update(state="queued"),
    lambda r,p,t:r["job"].update(cancel_requested=1),
    lambda r,p,t:r["job"].update(owner_id=str(uuid4())),
    lambda r,p,t:r["project"].update(owner_id=str(uuid4())),
    lambda r,p,t:r["sources"]["stationxml"].update(version=2),
    lambda r,p,t:r["job"]["preflight"].update(cpu_stop_ns=57000000001),
    lambda r,p,t:p.update(record_sha256="a"*64),
    lambda r,p,t:p.update(extra=True),
    lambda r,p,t:t["job"].update(dataset_id=str(uuid4())),
    lambda r,p,t:t["stage"].update(inode=True),
    lambda r,p,t:t["root_custody"].update(plan_sha256="a"*64),
    lambda r,p,t:t["installation"].update(invocation_sha256="a"*64),
    lambda r,p,t:t["sources"]["miniseed"].update(raw_sha256="a"*64),
    lambda r,p,t:t["lifecycle"].update(extinction_proved=False),
    lambda r,p,t:t.update(extra=True),
])
def test_changed_terminal_plan_relation_or_unknown_field_refuses(mutate):
    value,config,record,payload,plan,receipt = packet()
    mutate(record,plan,receipt)
    with pytest.raises(ValueError):
        value.checked_terminal_relations(config,record["job"]["id"],record,payload,plan,receipt)


def test_valid_running_dispatch_stays_distinct_and_no_io_is_performed(monkeypatch):
    value,config,record,payload,plan,receipt = packet()
    monkeypatch.setattr(value.os,"open",lambda *a,**k:pytest.fail("Pure barrier opened a path"))
    assert value.checked_terminal_relations(config,record["job"]["id"],record,payload,plan,receipt)
    record["job"].update(state="running",cancel_requested=False)
    assert value.checked_relations(config,record["job"]["id"],record,payload)
