"""Fixed Linux profile launch construction. No native imports or host admission.

All paths and properties come from installation configuration or checked owned
database relations. A constructor result is not evidence of kernel enforcement.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import PurePosixPath
import re
from uuid import UUID

METHODS = {"ert.topographic-profile/v1":("ert.py","ert_profile","ert_ohm"),
           "traveltime.first-arrival-profile/v1":("traveltime.py","traveltime_profile","traveltime_sgt")}
SOURCE_FILES = ("app/profile_linux_exec.py", "scripts/profile_linux_supervisor.py", "scripts/profile_linux_child.py",
                "scripts/process_profile_job.py", "scripts/process_supplied_profile.py",
                "data-pipeline/ert.py", "data-pipeline/traveltime.py",
                "data-pipeline/profile_mesh.py", "data-pipeline/supplied_profiles.py",
                "data-pipeline/sources.py", "data/source-ledger.json")
CONFIG_KEYS = set("schema source_root data_root custody_root python python_sha256 environment_root environment_sha256 import_closure import_closure_sha256 systemd_library systemd_library_sha256 uid gid source_hashes".split())
JOB_KEYS = set("id owner_id project_id dataset_id dataset_sha256 method_id state cancel_requested request_json request_sha256 preflight".split())
DATA_KEYS = set("id owner_id project_id raw_asset_id raw_sha256 sha256 byte_count storage_key parser_version modality".split())
RAW_KEYS = set("id owner_id project_id source_id sha256 byte_count storage_key detected_format".split())
ORIGIN_KEYS = set("id owner_id project_id sha256 rights_decision private_storage_permission".split())
REQUEST_KEYS = set("schema job_id project_id dataset_id dataset_sha256 method_id parameters raw_asset_id raw_sha256 profile_child_sha256 profile_code_hashes".split())
LIMIT_KEYS = set("estimated_memory_bytes estimated_scratch_bytes memory_limit_bytes scratch_limit_bytes wall_limit_seconds".split())


class LaunchError(ValueError):
    """Closed refusal; no uploaded/private content in its message."""


def require(value, code="profile_launch_refused"):
    if not value:
        raise LaunchError(code)


def canonical(value):
    try:
        return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode("utf-8")
    except (TypeError,ValueError,UnicodeError,RecursionError):
        raise LaunchError("invalid_json") from None


def digest(raw):
    require(type(raw) is bytes, "invalid_bytes")
    return hashlib.sha256(raw).hexdigest()


def fields(value, expected):
    require(type(value) is dict and set(value) == expected, "closed_fields")


def uuid(value):
    require(type(value) is str, "invalid_uuid")
    try:
        require(str(UUID(value)) == value, "invalid_uuid")
    except ValueError:
        raise LaunchError("invalid_uuid") from None
    return value


def sha(value):
    require(type(value) is str and re.fullmatch("[a-f0-9]{64}",value), "invalid_digest")
    return value


def integer(value, minimum, maximum):
    require(type(value) is int and minimum <= value <= maximum, "invalid_integer")
    return value


def path(value):
    require(type(value) is str and len(value) <= 512 and
            re.fullmatch(r"/[A-Za-z0-9_./-]+",value), "invalid_config_path")
    p = PurePosixPath(value)
    require(str(p) == value and p.is_absolute() and len(p.parts) >= 3 and
            ".." not in p.parts and "." not in p.parts, "invalid_config_path")
    return p


def validate_configuration(config):
    fields(config, CONFIG_KEYS)
    require(config["schema"] == "geophysics.profile-linux-config/v3", "configuration_schema")
    source, data, python, environment = (path(config[key]) for key in ("source_root","data_root","python","environment_root"))
    require(source != data and not source.is_relative_to(data) and not data.is_relative_to(source), "configuration_overlap")
    require(python.is_relative_to(environment) and python != environment, "interpreter_boundary")
    require(environment != data and not environment.is_relative_to(data) and not data.is_relative_to(environment), "environment_boundary")
    closure = path(config["import_closure"])
    require(not closure.is_relative_to(data), "closure_boundary")
    custody = path(config["custody_root"])
    for boundary in (source,data,environment,closure.parent):
        require(not custody.is_relative_to(boundary) and not boundary.is_relative_to(custody), "custody_boundary")
    for temporary in ("/run","/tmp","/var/tmp","/dev/shm"):
        require(not custody.is_relative_to(PurePosixPath(temporary)), "custody_system_temp")
    library = path(config["systemd_library"])
    require(str(library).startswith("/usr/lib/") and library.name.startswith("libsystemd.so."), "manager_library_boundary")
    for key in ("uid","gid"):
        integer(config[key],1000,2147483647)
    for key in ("python_sha256","environment_sha256","import_closure_sha256","systemd_library_sha256"):
        sha(config[key])
    fields(config["source_hashes"], set(SOURCE_FILES))
    for value in config["source_hashes"].values():
        sha(value)
    return source, data, python


def construct_launch(config, job, dataset, raw, origin):
    """Pure complete relation barrier. Never calls SQL, sudo or systemd."""
    return _construct(config,job,dataset,raw,origin,recovery=False)


def construct_recorded_launch(config, job, dataset, raw, origin):
    """Terminal custody verification only; never relabel a terminal job running."""
    return _construct(config,job,dataset,raw,origin,recovery=True)


def _construct(config, job, dataset, raw, origin, *, recovery):
    try:
        source, data, python = validate_configuration(config)
        for value, keys in ((job,JOB_KEYS),(dataset,DATA_KEYS),(raw,RAW_KEYS),(origin,ORIGIN_KEYS)):
            fields(value,keys)
            for key in ("id","owner_id","project_id"):
                uuid(value[key])
            require((value["owner_id"],value["project_id"]) == (job["owner_id"],job["project_id"]), "foreign_relation")
        require(job["method_id"] in METHODS and type(job["cancel_requested"]) is bool, "job_state_or_method")
        if recovery:
            require(job["state"] in ("succeeded","failed","cancelled"), "recovery_job_state")
        else:
            require(job["state"] == "running" and job["cancel_requested"] is False, "job_state_or_method")
        request, limits = job["request_json"], job["preflight"]
        fields(request,REQUEST_KEYS)
        fields(limits,LIMIT_KEYS)
        require(request["schema"] == "geophysics.processing-request/v1" and
                type(request["parameters"]) is dict and not request["parameters"], "request_contract")
        require(digest(canonical(request)) == sha(job["request_sha256"]), "request_identity")
        engine, modality, original_format = METHODS[job["method_id"]]
        expected = {"job_id":job["id"],"project_id":job["project_id"],
                    "dataset_id":dataset["id"],"dataset_sha256":sha(dataset["sha256"]),
                    "raw_asset_id":raw["id"],"raw_sha256":sha(raw["sha256"]),"method_id":job["method_id"]}
        require(all(request[key] == value for key,value in expected.items()), "request_relation")
        require(job["dataset_id"] == dataset["id"] and job["dataset_sha256"] == dataset["sha256"] and
                dataset["raw_asset_id"] == raw["id"] and dataset["raw_sha256"] == raw["sha256"] and
                raw["source_id"] == origin["id"] and origin["sha256"] == raw["sha256"], "parent_relation")
        require(dataset["parser_version"] == "supplied-profile-original/v1" and
                dataset["modality"] == modality and raw["detected_format"] == original_format and
                origin["private_storage_permission"] == "attested" and
                origin["rights_decision"] in ("mirror","provider-link-only","derivative-only"), "source_eligibility")
        integer(raw["byte_count"],1,1000000)
        integer(dataset["byte_count"],1,2*1024**2)
        owner, project, identifier = job["owner_id"],job["project_id"],job["id"]
        require(raw["storage_key"] == f'projects/{owner}/{project}/{raw["id"]}' and
                dataset["storage_key"] == f'derived/{owner}/{project}/datasets/{dataset["id"]}.json', "storage_identity")
        hashes = config["source_hashes"]
        require(request["profile_child_sha256"] == hashes["scripts/process_profile_job.py"], "producer_changed")
        fields(request["profile_code_hashes"],{engine,"supplied_profiles.py","profile_mesh.py"})
        require(all(request["profile_code_hashes"][name] == hashes["data-pipeline/"+name]
                    for name in request["profile_code_hashes"]), "engine_changed")
        memory = integer(limits["memory_limit_bytes"],1,2*1024**3)
        scratch = integer(limits["scratch_limit_bytes"],4096,64*1024**2)
        wall = integer(limits["wall_limit_seconds"],1,600)
        integer(limits["estimated_memory_bytes"],1,2*1024**3)
        integer(limits["estimated_scratch_bytes"],1,64*1024**2)
        host_stage = str(data/".job-staging"/identifier)
        custody = path(config["custody_root"])/identifier
        stage = str(custody/"scratch")
        held = custody/"inputs"
        # The reviewed producer imports its sibling CLI module. -I would remove
        # that trusted script directory; -s excludes user-site without doing so.
        command = [str(python),"-s","-B",str(source/"scripts/process_profile_job.py"),
                   "--input",str(held/"dataset.json"),"--raw",str(held/"original"),
                   "--output",stage+"/result.json","--job-id",identifier,
                   "--dataset-sha256",dataset["sha256"],"--request-sha256",job["request_sha256"],
                   "--method-id",job["method_id"],"--parameters","{}"]
        uid,gid = str(config["uid"]),str(config["gid"])
        guardian_scope = "geophysics-profile-guardian-"+identifier+".scope"
        properties = ["Type=exec","User="+uid,"Group="+gid,"SupplementaryGroups=",
                      "BindsTo="+guardian_scope,"After="+guardian_scope,
                      "RemainAfterExit=yes","KillMode=control-group","KillSignal=SIGKILL","Restart=no",
                      "RuntimeMaxSec="+str(wall),"TimeoutStopSec=1s","CPUQuota=100%",
                      "MemoryMax="+str(memory),"MemorySwapMax=0","TasksMax=32","NoNewPrivileges=yes",
                      "CapabilityBoundingSet=","PrivateNetwork=yes","PrivateDevices=yes","PrivateTmp=yes",
                      "ProtectHome=yes","ProtectSystem=strict","ProtectControlGroups=yes","UMask=0077",
                      "StandardOutput=null","StandardError=null","WorkingDirectory="+stage,
                      "ReadOnlyPaths=-/tmp -/var/tmp -/dev/shm",
                      "BindReadOnlyPaths="+str(held),
                      f"TemporaryFileSystem={stage}:rw,size={scratch},mode=0700,uid={uid},gid={gid}"]
        environment = {"PATH":"/usr/bin:/bin","HOME":stage,"TMPDIR":stage,"TMP":stage,"TEMP":stage,
                       "PYTHONDONTWRITEBYTECODE":"1","PYTHONIOENCODING":"utf-8",
                       "MPLCONFIGDIR":stage+"/.matplotlib","APPDATA":stage+"/.pygimli-config",
                       "LOCALAPPDATA":stage+"/.pygimli-config","XDG_CONFIG_HOME":stage+"/.pygimli-config",
                       "NUMBER_OF_PROCESSORS":"1","GEOPHYSICS_LOCAL_DATA_ROOT":stage}
        for key in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS",
                    "BLIS_NUM_THREADS","VECLIB_MAXIMUM_THREADS"):
            environment[key] = "1"
        return {"unit":"geophysics-profile-"+identifier+".service","stage":stage,"host_stage":host_stage,
                "guardian_scope":guardian_scope,
                "custody":str(custody),"held":str(held),
                "command":command,"properties":properties,"environment":environment,
                "authority":"constructor_only_not_host_qualification"}
    except (KeyError,TypeError,ValueError) as error:
        if isinstance(error,LaunchError):
            raise
        raise LaunchError("invalid_launch_relation") from None


def installation_binding(config, job, dataset, raw, origin):
    """Independent prelaunch snapshot; its constructor is not a host proof."""
    launch = construct_launch(config,job,dataset,raw,origin)
    return dict(configuration_sha256=digest(canonical(config)),python_sha256=config["python_sha256"],
                environment_sha256=config["environment_sha256"],invocation_sha256=digest(canonical(launch)),
                source_hashes=json.loads(canonical(config["source_hashes"])))


def recorded_installation_binding(config, job, dataset, raw, origin):
    launch = construct_recorded_launch(config,job,dataset,raw,origin)
    return dict(configuration_sha256=digest(canonical(config)),python_sha256=config["python_sha256"],
                environment_sha256=config["environment_sha256"],invocation_sha256=digest(canonical(launch)),
                source_hashes=json.loads(canonical(config["source_hashes"])))


# Cleanup authority is deliberately separate from the scientific receipt DTO.
INSTALLATION_FIELDS = set("configuration_sha256 python_sha256 environment_sha256 invocation_sha256 source_hashes".split())
AUTHORITY_FIELDS = set("schema job_id relation installation stage_identity plan_sha256".split())
CUSTODY_FIELDS = set("schema job_id authority_sha256 directories members".split())
INCOMPLETE_FIELDS = set("schema job_id authority_sha256 custody_sha256 intent_sha256 installation retained_stage_identity terminal execution_receipt known_root_copies_removed".split())
CUSTODY_RELATION_FIELDS = set("owner_id project_id job_id dataset_id raw_asset_id source_id method_id dataset_sha256 raw_sha256 request_sha256".split())


def file_identity(value, *, member=False):
    fields(value, {"device", "inode", "bytes", "sha256"} if member else {"device", "inode"})
    integer(value["device"], 0, 2**64-1)
    integer(value["inode"], 1, 2**64-1)
    if member:
        integer(value["bytes"], 1, 2*1024**2)
        sha(value["sha256"])


def validate_installation(value):
    fields(value, INSTALLATION_FIELDS)
    fields(value["source_hashes"], set(SOURCE_FILES))
    for name in INSTALLATION_FIELDS - {"source_hashes"}:
        sha(value[name])
    for item in value["source_hashes"].values():
        sha(item)


def custody_relation(packet):
    job, dataset, raw = packet["job"], packet["dataset"], packet["raw"]
    return dict(owner_id=job["owner_id"], project_id=job["project_id"], job_id=job["id"],
                dataset_id=dataset["id"], raw_asset_id=raw["id"], source_id=packet["origin"]["id"],
                method_id=job["method_id"], dataset_sha256=dataset["sha256"],
                raw_sha256=raw["sha256"], request_sha256=job["request_sha256"])


def custody_authority(config,packet,stage_identity,*,recovery=False):
    constructor = construct_recorded_launch if recovery else construct_launch
    binder = recorded_installation_binding if recovery else installation_binding
    args = (config,packet["job"],packet["dataset"],packet["raw"],packet["origin"])
    launch = constructor(*args)
    plan = dict(schema="geophysics.profile-linux-custody-plan/v1",job_id=packet["job"]["id"],
                held_bytes=packet["raw"]["byte_count"]+packet["dataset"]["byte_count"],
                request_sha256=packet["job"]["request_sha256"],raw_sha256=packet["raw"]["sha256"],
                dataset_sha256=packet["dataset"]["sha256"],invocation_sha256=digest(canonical(launch)))
    result = dict(schema="geophysics.profile-custody-intent/v1",job_id=packet["job"]["id"],
                  relation=custody_relation(packet),installation=binder(*args),
                  stage_identity=stage_identity,plan_sha256=digest(canonical(plan)))
    validate_custody_authority(result)
    return result


def validate_custody_authority(value):
    fields(value, AUTHORITY_FIELDS)
    require(value["schema"] == "geophysics.profile-custody-intent/v1", "custody_authority_schema")
    uuid(value["job_id"])
    sha(value["plan_sha256"])
    file_identity(value["stage_identity"])
    validate_installation(value["installation"])
    fields(value["relation"], CUSTODY_RELATION_FIELDS)
    for key in ("owner_id", "project_id", "job_id", "dataset_id", "raw_asset_id", "source_id"):
        uuid(value["relation"][key])
    require(value["relation"]["job_id"] == value["job_id"] and value["relation"]["method_id"] in METHODS,
            "custody_relation")
    for key in ("dataset_sha256", "raw_sha256", "request_sha256"):
        sha(value["relation"][key])


def validate_custody_manifest(value, authority):
    validate_custody_authority(authority)
    fields(value, CUSTODY_FIELDS)
    require(value["schema"] == "geophysics.profile-custody/v1" and
            value["job_id"] == authority["job_id"] and
            value["authority_sha256"] == digest(canonical(authority)), "custody_manifest_identity")
    fields(value["directories"], {"custody", "inputs", "scratch"})
    fields(value["members"], {"original", "dataset.json", "launch.json"})
    for record in value["directories"].values():
        file_identity(record)
    for name, record in value["members"].items():
        file_identity(record, member=True)
        integer(record["bytes"], 1, {"original":1000000, "dataset.json":2*1024**2, "launch.json":65536}[name])
    require(value["members"]["original"]["sha256"] == authority["relation"]["raw_sha256"] and
            value["members"]["dataset.json"]["sha256"] == authority["relation"]["dataset_sha256"], "custody_member_hash")


def validate_incomplete_terminal(value, identifier):
    units = ("geophysics-profile-"+uuid(identifier)+".service", "geophysics-profile-guardian-"+identifier+".scope")
    fields(value, set(units))
    for unit in units:
        fields(value[unit], {"manager", "kernel"})
        state, kernel = value[unit]["manager"], value[unit]["kernel"]
        expected = {"MainPID", "ActiveState", "SubState", "ControlGroup"}
        require(type(state) is dict and (set(state) == expected or
                unit.endswith(".scope") and set(state) == expected - {"MainPID"}), "incomplete_manager_fields")
        require(state.get("MainPID", "0") == "0" and state["ActiveState"] in ("inactive", "failed") and
                state["SubState"] in ("dead", "failed", "exited") and
                state["ControlGroup"] in ("", "/system.slice/"+unit), "incomplete_live_unit")
        fields(kernel, {"path", "state"})
        require(kernel["path"] == "/sys/fs/cgroup/system.slice/"+unit and
                kernel["state"] in ("absent", "unpopulated_no_processes"), "incomplete_kernel")


def validate_incomplete_recovery(value):
    fields(value, INCOMPLETE_FIELDS)
    require(value["schema"] == "geophysics.profile-incomplete-recovery/v1" and
            value["execution_receipt"] == "absent" and value["known_root_copies_removed"] is True,
            "incomplete_recovery_schema")
    uuid(value["job_id"])
    for key in ("authority_sha256", "custody_sha256", "intent_sha256"):
        sha(value[key])
    validate_installation(value["installation"])
    file_identity(value["retained_stage_identity"])
    validate_incomplete_terminal(value["terminal"], value["job_id"])
