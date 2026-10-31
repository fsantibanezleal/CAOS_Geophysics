"""Bounded optional Linux execution evidence, separate from scientific validity."""
from __future__ import annotations

import json
import math
import re

from app.profile_linux_exec import SOURCE_FILES
from app.processing_contract import canonical_bytes, sha256

KEYS = set("schema job_id request_sha256 dataset_sha256 raw_sha256 environment_sha256 unit terminal stop_reason failure launch_attempted extinction guardian_status guardian_scope invocation_sha256 source_hashes configuration_sha256 python_sha256 mounted_input_identities retained_stage_identity wall_seconds resources retained originals_reverified held_inputs_state cpu_accounting_admitted host_admission".split())
RESOURCE_KEYS = set("sampled_root_rss_peak_bytes rss_samples kernel_memcg_peak_bytes sampled_unit_rss_peak_bytes unit_rss_samples memcg_reads memory_events cgroup_events exact_group_removed hard_writable_scratch_bytes held_input_bytes".split())
INSTALLATION_KEYS = set("configuration_sha256 python_sha256 environment_sha256 invocation_sha256 source_hashes".split())


def require(value):
    if not value:
        raise ValueError("profile_execution_invalid")


def closed(value,keys):
    require(type(value) is dict and set(value) == keys)


def integer(value,low=0,high=2**63-1):
    require(type(value) is int and low <= value <= high)
    return value


def digest(value):
    require(type(value) is str and re.fullmatch("[a-f0-9]{64}",value))


def guardian_binding(receipt,job):
    guardian = receipt["guardian_scope"]
    closed(guardian,{"scope","group","memory_limit_bytes","tasks_max","wall_limit_seconds","identity_transport","manager_job"})
    scope = "geophysics-profile-guardian-"+job.id+".scope"
    require(guardian["scope"] == scope and guardian["group"] == "/system.slice/"+scope and
            type(guardian["memory_limit_bytes"]) is int and guardian["memory_limit_bytes"] == 128*1024**2 and
            type(guardian["tasks_max"]) is int and guardian["tasks_max"] == 16 and
            guardian["identity_transport"] == "PIDFDs/ah" and type(guardian["manager_job"]) is str and
            re.fullmatch(r"/org/freedesktop/systemd1/job/[0-9]{1,20}",guardian["manager_job"]))
    integer(guardian["wall_limit_seconds"],31,630)
    if getattr(job,"preflight",None):
        require(guardian["wall_limit_seconds"] == job.preflight["wall_limit_seconds"]+30)


def validate_installation(receipt,expected):
    closed(expected,INSTALLATION_KEYS)
    for key in INSTALLATION_KEYS-{"source_hashes"}:
        digest(expected[key])
        require(receipt[key] == expected[key])
    closed(expected["source_hashes"],set(SOURCE_FILES))
    for value in expected["source_hashes"].values():
        digest(value)
    require(receipt["source_hashes"] == expected["source_hashes"])


def validate_terminal(receipt,job,stage_identity,installation):
    """Extinction for a failed/cancelled job is not a successful science claim."""
    closed(receipt,KEYS)
    validate_installation(receipt,installation)
    require(len(canonical_bytes(receipt)) <= 65536 and receipt["schema"] == "geophysics.profile-linux-execution/v1" and
            receipt["job_id"] == job.id and receipt["request_sha256"] == job.request_sha256 and
            receipt["dataset_sha256"] == job.dataset_sha256 and receipt["raw_sha256"] == job.request_json["raw_sha256"] and
            receipt["unit"] == "geophysics-profile-"+job.id+".service" and receipt["extinction"] == "proved" and
            receipt["guardian_status"] == "complete" and receipt["retained_stage_identity"] == stage_identity and
            receipt["cpu_accounting_admitted"] is False and receipt["host_admission"] is False)
    closed(receipt["terminal"],{"MainPID","SubState","Result","ExecMainStatus","ControlGroup"})
    require(receipt["terminal"]["MainPID"] == "0" and receipt["terminal"]["SubState"] in ("dead","failed","exited") and
            receipt["terminal"]["ControlGroup"] in ("","/system.slice/"+receipt["unit"]))
    guardian_binding(receipt,job)
    closed(receipt["source_hashes"],set(SOURCE_FILES))
    for value in receipt["source_hashes"].values():
        digest(value)
    require(receipt["source_hashes"]["scripts/process_profile_job.py"] == job.request_json["profile_child_sha256"])
    for name,value in job.request_json["profile_code_hashes"].items():
        require(receipt["source_hashes"].get("data-pipeline/"+name) == value)
    resources = receipt["resources"]
    closed(resources,RESOURCE_KEYS)
    require(type(resources["exact_group_removed"]) is bool and (resources["exact_group_removed"] or
            type(resources["cgroup_events"]) is str and "populated 0" in resources["cgroup_events"].splitlines()))


def validate_execution(payload,job,stage_identity=None):
    """Check stored evidence on read/export; absent means no Linux claim."""
    if "linux_execution" not in payload:
        require("linux_installation" not in payload)
        return
    receipt = payload["linux_execution"]
    closed(receipt,KEYS)
    validate_installation(receipt,payload.get("linux_installation"))
    require(len(canonical_bytes(receipt)) <= 65536 and
            receipt["schema"] == "geophysics.profile-linux-execution/v1")
    for key,expected in (("job_id",job.id),("request_sha256",job.request_sha256),
                         ("dataset_sha256",job.dataset_sha256),("raw_sha256",job.request_json["raw_sha256"])):
        require(receipt[key] == expected)
    for key in ("request_sha256","dataset_sha256","raw_sha256","environment_sha256",
                "invocation_sha256","configuration_sha256","python_sha256"):
        digest(receipt[key])
    require(receipt["unit"] == "geophysics-profile-"+job.id+".service" and
            receipt["failure"] is None and receipt["stop_reason"] is None and
            receipt["launch_attempted"] is True and receipt["extinction"] == "proved" and
            receipt["guardian_status"] == "complete" and receipt["originals_reverified"] is True and
            receipt["held_inputs_state"] == "declared_copies_removed" and
            receipt["cpu_accounting_admitted"] is False and receipt["host_admission"] is False)
    terminal = receipt["terminal"]
    closed(terminal,{"MainPID","SubState","Result","ExecMainStatus","ControlGroup"})
    require(terminal["MainPID"] == "0" and terminal["ExecMainStatus"] == "0" and
            terminal["Result"] == "success" and terminal["SubState"] in ("dead","exited") and
            terminal["ControlGroup"] in ("","/system.slice/"+receipt["unit"]))
    limits = getattr(job,"preflight",None) or {"memory_limit_bytes":2*1024**3,
                                               "scratch_limit_bytes":64*1024**2,"wall_limit_seconds":600}
    guardian_binding(receipt,job)
    closed(receipt["source_hashes"],set(SOURCE_FILES))
    for value in receipt["source_hashes"].values():
        digest(value)
    require(receipt["source_hashes"]["scripts/process_profile_job.py"] == job.request_json["profile_child_sha256"])
    for name,value in job.request_json["profile_code_hashes"].items():
        require(receipt["source_hashes"].get("data-pipeline/"+name) == value)
    closed(receipt["retained_stage_identity"],{"device","inode"})
    for value in receipt["retained_stage_identity"].values():
        integer(value)
    if stage_identity is not None:
        require(receipt["retained_stage_identity"] == stage_identity)
    mounted = receipt["mounted_input_identities"]
    closed(mounted,{"original","dataset.json"})
    for name,record in mounted.items():
        closed(record,{"device","inode","bytes","sha256"})
        integer(record["device"])
        integer(record["inode"],1)
        integer(record["bytes"],1,1000000 if name == "original" else 2*1024**2)
        require(record["sha256"] == (receipt["raw_sha256"] if name == "original" else receipt["dataset_sha256"]))
    require(mounted["original"]["bytes"] == payload["raw_bytes"])
    require(type(receipt["wall_seconds"]) in (int,float) and math.isfinite(receipt["wall_seconds"]) and
            0 <= receipt["wall_seconds"] <= limits["wall_limit_seconds"]+40)
    resources = receipt["resources"]
    closed(resources,RESOURCE_KEYS)
    for key in ("sampled_root_rss_peak_bytes","sampled_unit_rss_peak_bytes","kernel_memcg_peak_bytes",
                "rss_samples","unit_rss_samples","memcg_reads"):
        integer(resources[key],1)
    require(resources["kernel_memcg_peak_bytes"] <= limits["memory_limit_bytes"] and
            resources["hard_writable_scratch_bytes"] <= limits["scratch_limit_bytes"] and
            resources["held_input_bytes"] == sum(record["bytes"] for record in mounted.values()))
    integer(resources["hard_writable_scratch_bytes"],4096,64*1024**2)
    require(type(resources["exact_group_removed"]) is bool)
    for name in ("memory_events","cgroup_events"):
        value = resources[name]
        require(value is None or type(value) is str and len(value) <= 4096)
    require(resources["exact_group_removed"] or type(resources["cgroup_events"]) is str and
            "populated 0" in resources["cgroup_events"].splitlines())
    retained = receipt["retained"]
    closed(retained,{"result.json","stderr.txt"})
    for name,record in retained.items():
        closed(record,{"bytes","sha256"})
        integer(record["bytes"],1 if name == "result.json" else 0,32*1024**2)
        digest(record["sha256"])
    producer = {key:value for key,value in payload.items() if key not in ("linux_execution","linux_installation")}
    original = canonical_bytes(producer)
    require(retained["result.json"] == {"bytes":len(original),"sha256":sha256(original)})


def attach_execution(producer_bytes,receipt,job,stage_identity,installation):
    require(type(producer_bytes) is bytes and 0 < len(producer_bytes) <= 8*1024**2)
    payload = json.loads(producer_bytes)
    require(type(payload) is dict and not {"linux_execution","linux_installation"}.intersection(payload) and canonical_bytes(payload) == producer_bytes)
    payload["linux_execution"] = receipt
    payload["linux_installation"] = json.loads(canonical_bytes(installation))
    validate_execution(payload,job,stage_identity)
    return payload
