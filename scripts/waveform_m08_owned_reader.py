"""Bounded owned waveform relations. SQLite/originals open only as the app UID."""
from __future__ import annotations

import base64
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import re
import select
import sqlite3
import stat
import time
from uuid import UUID

from waveform_m08_installation import (
    canonical, decode, digest, directory_fd, fields, file_identity,
    regular_at, require, sha, uuid, validate_configuration, validate_recorded_binding,
)

METHOD = "seismic.waveform-qc-classical/v1"
MAX_PACKET = 28*1024**2
JOB_KEYS = set("id owner_id project_id dataset_id dataset_sha256 method_id request_json request_sha256 preflight state cancel_requested".split())
DATA_KEYS = set("id owner_id project_id raw_asset_id version parser_version modality row_count raw_sha256 sha256 byte_count storage_key".split())
RAW_KEYS = set("id owner_id project_id source_id detected_format byte_count sha256 storage_key physical_metadata".split())
SOURCE_KEYS = set("id owner_id project_id version sha256 rights_decision private_storage_permission".split())
DEPENDENCY_KEYS = set("dataset_id role asset_id source_id raw_sha256 raw_bytes source_version".split())
REQUEST_KEYS = set("schema job_id project_id dataset_id dataset_sha256 method_id parameters waveform_sources scientific_request scientific_request_sha256 implementation_sha256".split())
INDEX_KEYS = set("schema dataset_id version owner_id project_id raw_asset_id parent_raw_sha256 parser_version modality dimensions sources request scientific_request_sha256 qc_verdict".split())
LIMIT_KEYS = set("estimated_memory_bytes memory_limit_bytes scratch_limit_bytes wall_limit_seconds estimated_scratch_bytes memory_kind cpu_budget_ns cpu_stop_ns".split())
SOURCE_BINDING_KEYS = set("asset_id source_id source_version raw_sha256 raw_bytes rights_decision private_storage_permission".split())
ROLE_CAPS = {"miniseed":16777216,"stationxml":2097152}


def product_bytes(value):
    # Existing protected-job/dataset canonical domain is UTF-8, not native ASCII.
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode("utf-8")


def structural_input():
    name = Path(__file__).resolve().parents[1]/"data-pipeline/waveform_input.py"
    spec = importlib.util.spec_from_file_location("_m08_owned_structural_input",name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def integer(value, minimum, maximum):
    require(type(value) is int and minimum <= value <= maximum,"waveform_owned_relation_invalid")


def checked_relations(config, identifier, record, payload):
    """No SQL/OS launch. Every accepted path is regenerated from owned UUIDs."""
    validate_configuration(config)
    uuid(identifier)
    fields(record,{"job","project","dataset","dependencies","assets","sources"})
    job,dataset = record["job"],record["dataset"]
    fields(job,JOB_KEYS)
    fields(dataset,DATA_KEYS)
    fields(record["project"],{"id","owner_id"})
    for value in (job,dataset,record["project"]):
        uuid(value["id"])
        uuid(value["owner_id"])
    require(job["id"] == identifier and job["state"] == "running" and job["cancel_requested"] is False)
    require(job["method_id"] == METHOD and dataset["id"] == job["dataset_id"])
    require(record["project"] == {"id":job["project_id"],"owner_id":job["owner_id"]})
    require((dataset["project_id"],dataset["owner_id"]) == (job["project_id"],job["owner_id"]))
    uuid(job["project_id"])
    uuid(dataset["raw_asset_id"])
    for name in ("request_sha256","dataset_sha256"):
        digest(job[name])
    for name in ("sha256","raw_sha256"):
        digest(dataset[name])
    integer(dataset["byte_count"],1,2097152)
    require(dataset["sha256"] == job["dataset_sha256"] and type(dataset["version"]) is int and dataset["version"] == 1)
    require(dataset["storage_key"] == f"derived/{job['owner_id']}/{job['project_id']}/datasets/{dataset['id']}.json")
    require(dataset["modality"] == "waveform_counts_response")
    request = job["request_json"]
    fields(request,REQUEST_KEYS)
    require(len(product_bytes(request)) <= 65536 and sha(product_bytes(request)) == job["request_sha256"])
    require(request["schema"] == "geophysics.processing-request/v1")
    for request_key,job_key in (("job_id","id"),("project_id","project_id"),("dataset_id","dataset_id"),
                                ("dataset_sha256","dataset_sha256"),("method_id","method_id")):
        require(request[request_key] == job[job_key])
    require(request["implementation_sha256"] == sha(canonical(config["source_hashes"])))
    fields(payload,INDEX_KEYS)
    require(sha(product_bytes(payload)) == dataset["sha256"] and len(product_bytes(payload)) == dataset["byte_count"])
    for name in ("dataset_id","version","owner_id","project_id","raw_asset_id","parser_version","modality"):
        require(payload[name] == (dataset["id"] if name == "dataset_id" else dataset[name]))
    require(payload["schema"] == "geophysics.waveform-dataset/v1" and payload["parent_raw_sha256"] == dataset["raw_sha256"])
    require(payload["qc_verdict"] == "structural_index_not_physical_qc")
    input_module = structural_input()
    validated = input_module.validate_request(payload["request"])
    science_sha = input_module.scientific_identity(validated)
    require(validated["source"]["rights"] in ("private-use-attested","reviewed-public-scsn"))
    require(payload["request"] == request["scientific_request"] and
            payload["scientific_request_sha256"] == science_sha == request["scientific_request_sha256"])
    require(dataset["parser_version"] == "m08/v1/"+science_sha)
    require(request["parameters"] == {"scientific_request_sha256":science_sha})
    fields(payload["dimensions"],{"channel","sample","record"})
    dimensions = payload["dimensions"]
    integer(dimensions["channel"],1,3)
    integer(dimensions["sample"],1,180000)
    integer(dimensions["record"],1,4096)
    require(dimensions["channel"] == len(validated["channels"]) and dimensions["sample"] == dataset["row_count"])
    limits = job["preflight"]
    fields(limits,LIMIT_KEYS)
    for name,cap in (("estimated_memory_bytes",1073741824),("estimated_scratch_bytes",52690944)):
        integer(limits[name],1,cap)
    require({name:limits[name] for name in LIMIT_KEYS-{"estimated_memory_bytes","estimated_scratch_bytes"}} ==
            dict(memory_limit_bytes=1073741824,scratch_limit_bytes=52690944,wall_limit_seconds=120,
                 memory_kind="platform_committed_or_cgroup_charge_not_rss",cpu_budget_ns=60000000000,cpu_stop_ns=57000000000))
    # bool and float equivalents are not resource limits.
    for name in LIMIT_KEYS-{"memory_kind"}:
        require(type(limits[name]) is int)
    fields(payload["sources"],ROLE_CAPS)
    require(payload["sources"] == request["waveform_sources"])
    for name in ("assets","sources"):
        fields(record[name],ROLE_CAPS)
    require(type(record["dependencies"]) is list and len(record["dependencies"]) == 2)
    dependencies = {}
    for dependency in record["dependencies"]:
        fields(dependency,DEPENDENCY_KEYS)
        require(dependency["role"] in ROLE_CAPS and dependency["role"] not in dependencies)
        dependencies[dependency["role"]] = dependency
    keys = {}
    for role,cap in ROLE_CAPS.items():
        binding,asset,source,dependency = (payload["sources"][role],record["assets"][role],
                                         record["sources"][role],dependencies[role])
        fields(binding,SOURCE_BINDING_KEYS)
        fields(asset,RAW_KEYS)
        fields(source,SOURCE_KEYS)
        for value in (asset,source):
            for name in ("id","owner_id","project_id"):
                uuid(value[name])
            require((value["owner_id"],value["project_id"]) == (job["owner_id"],job["project_id"]))
            digest(value["sha256"])
        integer(source["version"],1,2147483647)
        integer(asset["byte_count"],1,cap)
        require(source["private_storage_permission"] == "attested" and
                source["rights_decision"] in ("mirror","provider-link-only","derivative-only"))
        expected = dict(asset_id=asset["id"],source_id=source["id"],source_version=source["version"],
                        raw_sha256=asset["sha256"],raw_bytes=asset["byte_count"],
                        rights_decision=source["rights_decision"],private_storage_permission="attested")
        require(binding == expected and source["sha256"] == asset["sha256"] and asset["source_id"] == source["id"])
        require(dependency == dict(dataset_id=dataset["id"],role=role,**{key:expected[key] for key in
                                ("asset_id","source_id","source_version","raw_sha256","raw_bytes")}))
        require(asset["detected_format"] == role)
        key = f"projects/{job['owner_id']}/{job['project_id']}/{asset['id']}"
        require(asset["storage_key"] == key)
        keys[role] = key
    mseed = record["assets"]["miniseed"]
    require(mseed["id"] == dataset["raw_asset_id"] and mseed["sha256"] == dataset["raw_sha256"])
    require(type(mseed["physical_metadata"]) is dict and
            mseed["physical_metadata"].get("geometry",{}).get("stationxml_asset_id") == record["assets"]["stationxml"]["id"])
    require(validated["source"]["declared_sha256"] in (None,mseed["sha256"]))
    return keys


def read_key(root, key, cap):
    # Called after regenerated-key validation, with every parent held no-follow.
    parts = key.split("/")
    require(all(name and name not in (".","..") for name in parts))
    parent = directory_fd(Path(root).joinpath(*parts[:-1]))
    try:
        return regular_at(parent,parts[-1],cap)
    finally:
        os.close(parent)


def checked_terminal_relations(config, identifier, record, payload, plan, receipt):
    """Pure historical relation barrier, NOT native proof or cleanup authority.

    Only the operator's later root-owned plan/receipt path may call this. Normal
    query/dispatch never selects it. Full terminal/namespace/archive validation
    remains a distinct requirement before any retained copy can be retired.
    """
    validate_configuration(config)
    uuid(identifier)
    fields(record,{"job","project","dataset","dependencies","assets","sources"})
    fields(record["job"],JOB_KEYS)
    job = record["job"]
    require(job["id"] == identifier and job["state"] in ("failed","cancelled","succeeded") and
            type(job["cancel_requested"]) is bool)
    fields(plan,{"schema","job_id","request_sha256","input_bytes","stage","installation","record_sha256"})
    require(plan["schema"] == "geophysics.waveform-custody-plan/v1" and plan["job_id"] == identifier and
            plan["request_sha256"] == job["request_sha256"])
    validate_recorded_binding(plan["installation"])
    digest(plan["record_sha256"])
    fields(receipt,set("schema job sources installation stage root_custody outcome lifecycle native calculation_sha256 members".split()))
    require(len(canonical(receipt)) <= 65536 and receipt["schema"] == "geophysics.waveform-linux-execution/v1")
    expected = {**{key:job[key] for key in ("id","owner_id","project_id","dataset_id","dataset_sha256","request_sha256","method_id")},
                **{key:job["request_json"][key] for key in ("implementation_sha256","scientific_request_sha256")}}
    require(receipt["job"] == expected and receipt["sources"] == job["request_json"]["waveform_sources"] and
            receipt["installation"] == plan["installation"] and receipt["stage"] == plan["stage"])
    fields(plan["stage"],{"device","inode"})
    integer(plan["stage"]["device"],0,2**64-1)
    integer(plan["stage"]["inode"],1,2**64-1)
    fields(receipt["root_custody"],{"device","inode","plan_sha256"})
    integer(receipt["root_custody"]["device"],0,2**64-1)
    integer(receipt["root_custody"]["inode"],1,2**64-1)
    require(receipt["root_custody"]["plan_sha256"] == sha(canonical(plan)) and
            type(receipt["lifecycle"]) is dict and receipt["lifecycle"].get("extinction_proved") is True)
    normalized = deepcopy(record)
    normalized["job"].update(state="running",cancel_requested=False)
    require(sha(product_bytes(normalized)) == plan["record_sha256"])
    historical = {**config,"source_hashes":dict(plan["installation"]["source_hashes"])}
    keys = checked_relations(historical,identifier,normalized,payload)
    expected_bytes = sum(binding["raw_bytes"] for binding in job["request_json"]["waveform_sources"].values())
    expected_bytes += len(canonical(job["request_json"]["scientific_request"]))
    require(type(plan["input_bytes"]) is int and plan["input_bytes"] == expected_bytes)
    return keys


def query(config, identifier):
    """One bounded read transaction as the configured app identity, never root."""
    require(os.geteuid() == os.getuid() == config["uid"] and os.getegid() == os.getgid() == config["gid"])
    require(not os.getgroups())
    database = Path(config["data_root"])/"api.sqlite3"
    parent = directory_fd(database.parent)
    fd = os.open(database.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK,dir_fd=parent)
    try:
        identity = file_identity(os.fstat(fd))
        require(stat.S_ISREG(identity[2]) and identity[3] == 1 and 0 < identity[6] <= 256*1024**2)
        connection = sqlite3.connect("file:"+str(database)+"?mode=ro",uri=True,timeout=.2)
        connection.row_factory = sqlite3.Row
        deadline = time.monotonic()+3
        connection.set_progress_handler(lambda:int(time.monotonic()>deadline),1000)
        try:
            connection.execute("PRAGMA query_only=ON")
            connection.execute("BEGIN")
            require(file_identity(os.stat(database.name,dir_fd=parent,follow_symlinks=False)) == identity)
            def row(table, keys, identifier):
                result = connection.execute("SELECT "+",".join(sorted(keys))+" FROM "+table+" WHERE id=?",(identifier,)).fetchone()
                require(result is not None)
                value = dict(result)
                for name in ("owner_id",):
                    require(type(value[name]) is str and re.fullmatch("[a-f0-9]{32}|[a-f0-9-]{36}",value[name]))
                    value[name] = str(UUID(value[name]))
                for name in ("request_json","preflight","physical_metadata"):
                    if name in value:
                        require(type(value[name]) is str)
                        value[name] = decode(value[name].encode("utf-8"),65536)
                return value
            job = row("processing_jobs",JOB_KEYS,identifier)
            require(type(job["cancel_requested"]) is int and job["cancel_requested"] in (0,1))
            job["cancel_requested"] = bool(job["cancel_requested"])
            dataset = row("observation_datasets",DATA_KEYS,job["dataset_id"])
            project = row("projects",{"id","owner_id"},job["project_id"])
            dependencies = [dict(item) for item in connection.execute("SELECT "+",".join(sorted(DEPENDENCY_KEYS))+
                " FROM waveform_dataset_sources WHERE dataset_id=? LIMIT 3",(dataset["id"],))]
            require(len(dependencies) == 2 and {item["role"] for item in dependencies} == set(ROLE_CAPS))
            assets,sources = {},{}
            for item in dependencies:
                asset = row("raw_assets",RAW_KEYS,item["asset_id"])
                assets[item["role"]] = asset
                sources[item["role"]] = row("source_records",SOURCE_KEYS,asset["source_id"])
            record = dict(job=job,project=project,dataset=dataset,dependencies=dependencies,assets=assets,sources=sources)
            # Generate the index path before consulting any SQL-supplied path.
            for name in ("owner_id","project_id","dataset_id"):
                uuid(job[name])
            key = f"derived/{job['owner_id']}/{job['project_id']}/datasets/{job['dataset_id']}.json"
            index = read_key(config["data_root"],key,2097152)
            payload = decode(index,2097152)
            require(index == product_bytes(payload))
            keys = checked_relations(config,identifier,record,payload)
            bodies = {role:read_key(config["data_root"],key,ROLE_CAPS[role]) for role,key in keys.items()}
            for role,body in bodies.items():
                binding = payload["sources"][role]
                require(sha(body) == binding["raw_sha256"] and len(body) == binding["raw_bytes"])
            require(file_identity(os.stat(database.name,dir_fd=parent,follow_symlinks=False)) == identity)
            bodies["dataset.json"] = index
            return dict(record=record,bodies={name:base64.b64encode(body).decode("ascii") for name,body in bodies.items()},
                        reader=dict(uid=os.getuid(),gid=os.getgid(),groups=os.getgroups()))
        finally:
            connection.close()
    finally:
        os.close(fd)
        os.close(parent)


def nonroot_query(config, identifier):
    """Anonymous bounded packet; only the owned unreaped fork may be signalled."""
    import resource
    validate_configuration(config)
    uuid(identifier)
    require(os.geteuid() == 0)
    reader,writer = os.pipe2(os.O_CLOEXEC)
    try:
        pid = os.fork()
    except BaseException:
        os.close(reader)
        os.close(writer)
        raise
    if pid == 0:
        try:
            for name in os.listdir("/proc/self/fd"):
                fd = int(name)
                if fd != writer:
                    try:
                        os.close(fd)
                    except OSError:
                        pass
            os.setgroups([])
            os.setgid(config["gid"])
            os.setuid(config["uid"])
            os.environ.clear()
            resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2))
            resource.setrlimit(resource.RLIMIT_CPU,(5,5))
            packet = canonical(query(config,identifier))
            require(len(packet) <= MAX_PACKET)
            with os.fdopen(writer,"wb") as stream:
                stream.write(packet)
            os._exit(0)
        except BaseException:
            os._exit(2)
    os.close(writer)
    reaped = False
    chunks = bytearray()
    deadline = time.monotonic()+8
    try:
        while True:
            require(time.monotonic() < deadline,"waveform_owned_reader_timeout")
            ready,_,_ = select.select([reader],[],[],min(.1,max(0,deadline-time.monotonic())))
            if not ready:
                continue
            part = os.read(reader,65536)
            if not part:
                break
            require(len(chunks)+len(part) <= MAX_PACKET)
            chunks.extend(part)
        _,status = os.waitpid(pid,0)
        reaped = True
        require(os.waitstatus_to_exitcode(status) == 0,"waveform_owned_reader_refused")
        packet = decode(bytes(chunks),MAX_PACKET)
        fields(packet,{"record","bodies","reader"})
        require(packet["reader"] == dict(uid=config["uid"],gid=config["gid"],groups=[]))
        fields(packet["bodies"],{"miniseed","stationxml","dataset.json"})
        decoded = {}
        for name,cap in {**ROLE_CAPS,"dataset.json":2097152}.items():
            body = packet["bodies"][name]
            require(type(body) is str and len(body) <= ((cap+2)//3)*4)
            decoded[name] = base64.b64decode(body,validate=True)
            require(0 < len(decoded[name]) <= cap)
        payload = decode(decoded["dataset.json"],2097152)
        require(decoded["dataset.json"] == product_bytes(payload))
        checked_relations(config,identifier,packet["record"],payload)
        for role in ROLE_CAPS:
            binding = payload["sources"][role]
            require(sha(decoded[role]) == binding["raw_sha256"] and len(decoded[role]) == binding["raw_bytes"])
        return packet
    except BaseException:
        if not reaped:
            try:
                os.kill(pid,9)
            except ProcessLookupError:
                pass
            os.waitpid(pid,0)
        raise
    finally:
        os.close(reader)
