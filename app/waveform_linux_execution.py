"""Closed historical Linux waveform terminal binding; no process launch or config read."""
from __future__ import annotations

import os
import re

from waveform_m08_installation import (
    canonical, digest, fields, require, sha, uuid,
    validate_installation_binding, validate_recorded_binding,
)

EXECUTION_KEYS = set("schema job sources installation stage root_custody outcome lifecycle native calculation_sha256 members".split())
JOB_KEYS = set("id owner_id project_id dataset_id dataset_sha256 request_sha256 method_id implementation_sha256 scientific_request_sha256".split())


def expected_job(job):
    return {"id":job.id,"owner_id":str(job.owner_id),"project_id":job.project_id,
            "dataset_id":job.dataset_id,"dataset_sha256":job.dataset_sha256,"request_sha256":job.request_sha256,
            "method_id":job.method_id,**{name:job.request_json[name] for name in
                ("implementation_sha256","scientific_request_sha256")}}


def identity(fd):
    value = os.fstat(fd)
    return dict(device=value.st_dev,inode=value.st_ino)


def directory_identity(value):
    fields(value,{"device","inode"})
    require(type(value["device"]) is int and 0 <= value["device"] < 2**64 and
            type(value["inode"]) is int and 0 < value["inode"] < 2**64)


def validate_terminal(receipt, job, stage=None, installation=None, *, payload=None):
    """Same closed binding on success/cancel/history; no read of today's config."""
    from waveform_m08_windows import ControlError, precount
    try:
        precount(receipt,65536,max_nodes=4096,max_depth=24)
        require(len(canonical(receipt)) <= 65536)
    except ControlError:
        raise ValueError("waveform_terminal_invalid") from None
    fields(receipt,EXECUTION_KEYS)
    require(receipt["schema"] == "geophysics.waveform-linux-execution/v1")
    fields(receipt["job"],JOB_KEYS)
    require(receipt["job"] == expected_job(job) and receipt["sources"] == job.request_json["waveform_sources"])
    for name in ("id","owner_id","project_id","dataset_id"):
        uuid(receipt["job"][name])
    for name in JOB_KEYS-{"id","owner_id","project_id","dataset_id","method_id"}:
        digest(receipt["job"][name])
    require(receipt["job"]["method_id"] == "seismic.waveform-qc-classical/v1")
    validate_recorded_binding(receipt["installation"])
    if installation is not None:
        validate_installation_binding(receipt["installation"],checked=installation)
    require(sha(canonical(receipt["installation"]["source_hashes"])) == receipt["job"]["implementation_sha256"])
    directory_identity(receipt["stage"])
    if stage is not None:
        require(receipt["stage"] == stage)
    custody = receipt["root_custody"]
    fields(custody,{"device","inode","plan_sha256"})
    directory_identity({key:custody[key] for key in ("device","inode")})
    digest(custody["plan_sha256"])
    life = receipt["lifecycle"]
    require(type(life) is dict and life.get("extinction_proved") is True)
    base = {"extinction_proved","science_quiescent_ns","caller","final_counters","guardian"}
    running = {"run_id","admission_sha256","units"}
    require(set(life) in (base,base|running,base|running|{"cancel_to_quiescence_ns"},base|{"cancel_to_quiescence_ns"}))
    require(type(life["science_quiescent_ns"]) is int and 0 < life["science_quiescent_ns"] < 2**64)
    caller = life["caller"]
    fields(caller,{"reason","started_ns"})
    require(caller["reason"] in (None,"cancelled","caller_lost"))
    if caller["reason"] is None:
        require(caller["started_ns"] is None and "cancel_to_quiescence_ns" not in life)
    else:
        require(type(caller["started_ns"]) is int and 0 < caller["started_ns"] <= life["science_quiescent_ns"])
        elapsed = life["science_quiescent_ns"]-caller["started_ns"]
        require(type(life["cancel_to_quiescence_ns"]) is int and elapsed == life["cancel_to_quiescence_ns"] <= 2000000000)
    if "run_id" in life:
        from waveform_m08_guardian import guardian_names
        require(type(life["run_id"]) is str and re.fullmatch("[a-f0-9]{32}",life["run_id"]))
        require(life["units"] == dict(zip(("service","accounting","guardian"),guardian_names(life["run_id"]),strict=True)))
        digest(life["admission_sha256"])
    guardian = life["guardian"]
    if guardian is not None:
        require("run_id" in life)
        fields(guardian,set("scope group identity_transport memory_limit_bytes tasks_max wall_limit_seconds manager_job scope_removed".split()))
        require(guardian["scope"] == life["units"]["guardian"] and guardian["group"] == "/system.slice/"+guardian["scope"])
        require(guardian["identity_transport"] == "PIDFDs/ah" and guardian["scope_removed"] is True)
        for key,expected in (("memory_limit_bytes",128*1024**2),("tasks_max",16),("wall_limit_seconds",150)):
            require(type(guardian[key]) is int and guardian[key] == expected)
        require(type(guardian["manager_job"]) is str and re.fullmatch(r"/org/freedesktop/systemd1/job/[0-9]{1,20}",guardian["manager_job"]))
    counters = life["final_counters"]
    if counters is not None:
        fields(counters,{"cpu_ns","user_cpu_ns","system_cpu_ns","active_tasks","peak_charge_bytes"})
        require(all(type(value) is int and 0 <= value < 2**63 for value in counters.values()))
        require(counters["active_tasks"] == 0 and counters["user_cpu_ns"] <= counters["cpu_ns"] and
                counters["system_cpu_ns"] <= counters["cpu_ns"])
    outcome = receipt["outcome"]
    require(type(outcome) is dict and outcome.get("runtime_authorized") is False)
    if outcome.get("reason") == "measured":
        fields(outcome,{"status","reason","run_id","receipt_sha256","release_sha256","runtime_authorized"})
        require(outcome["status"] in ("computed","qc_only") and caller["reason"] is None and
                outcome["run_id"] == life["run_id"] and counters is not None and guardian is not None)
        native = receipt["native"]
        fields(native,{"eligibility","release"})
        from app.waveform_result import checked_resources
        checked_resources(native["eligibility"],native["release"])
        require(life["science_quiescent_ns"] >= native["eligibility"]["stable_final_ns"])
        require(outcome["receipt_sha256"] == sha(canonical(native["eligibility"])) and
                outcome["release_sha256"] == sha(canonical(native["release"])))
        require(native["eligibility"]["admission_sha256"] == life["admission_sha256"] and
                {name:native["eligibility"][name] for name in ("cpu_ns","user_cpu_ns","system_cpu_ns","peak_charge_bytes")} ==
                {name:counters[name] for name in ("cpu_ns","user_cpu_ns","system_cpu_ns","peak_charge_bytes")})
        require({**guardian,"status":"complete"} == native["eligibility"]["guardian"])
        digest(receipt["calculation_sha256"])
        members = receipt["members"]
        require(type(members) is list and 3 <= len(members) <= 55)
        from app.waveform_contract import MEMBER
        names,total = [],0
        for member in members:
            fields(member,{"name","bytes","sha256"})
            require(type(member["name"]) is str and MEMBER.fullmatch(member["name"]))
            require(type(member["bytes"]) is int and 0 < member["bytes"] <= 33554432)
            digest(member["sha256"])
            names.append(member["name"])
            total += member["bytes"]
        require(names == sorted(set(names)) and total <= 33554432 and
                {"calculation.json","manifest.json","receipt.json"} <= set(names))
        if payload is not None:
            require(payload["scientific_status"] == outcome["status"])
            require(payload["calculation_sha256"] == receipt["calculation_sha256"] and payload["members"] == members)
            require(payload["resources"] == checked_resources(native["eligibility"],native["release"]))
    else:
        fields(outcome,{"status","reason","runtime_authorized"})
        require(receipt["native"] is None and receipt["calculation_sha256"] is None and receipt["members"] == [])
        require(outcome["status"] in ("failed","cancelled","timed_out","resource_exceeded","rejected","engine_unavailable"))
        require(payload is None)
    return receipt
