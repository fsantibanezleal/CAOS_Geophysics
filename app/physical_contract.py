"""Bounded data-only physical recovery contracts. No runtime admission or I/O."""

from __future__ import annotations

import base64
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from uuid import UUID

M = 1048576
J = 9007199254740991
LEGACY_REVISION = "0003_processing_jobs"
PHYSICAL_REVISION = "0004_physical_persistence"
LEGACY_DDL = "33a96998cd77c595a0d983461f84e1367a813e460b9c13222d07490fd9b86709"
CORRECTION = "gravity.station-corrections/v1"
TRANSFORM = "gravity.equivalent-source-transform/v1"
METHODS = ("gravity.station-outlier-flags/v1", "mt.edi-full-tensor-qc/v1", "mt.edi-fixed-thickness-trf/v1", CORRECTION, TRANSFORM)


class ContractError(ValueError):
    """A closed structural refusal, with no source/private text in its message."""


def require(condition, code="contract_refused"):
    if not condition:
        raise ContractError(code)


def fields(value, names):
    require(type(value) is dict and set(value) == set(names.split()), "fields")


def integer(value, low=0, high=J):
    require(type(value) is int and low <= value <= high, "integer")
    return value


def text(value, cap=8192):
    require(type(value) is str, "text")
    try:
        body = value.encode("utf-8", "strict")
    except UnicodeError as error:
        raise ContractError("encoding") from error
    require(0 < len(body) <= cap and "\0" not in value, "text")
    return value


def uuid(value):
    text(value, 36)
    try:
        require(str(UUID(value)) == value, "uuid")
    except ValueError as error:
        raise ContractError("uuid") from error
    return value


def sha(value):
    require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value), "sha256")
    return value


def instant(value, legacy=False):
    text(value, 40 if legacy else 27)
    if not legacy:
        require(re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z", value), "utc")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None and legacy:
            parsed = parsed.replace(tzinfo=timezone.utc)
        require(parsed.utcoffset() is not None and parsed.utcoffset().total_seconds() == 0, "utc")
        return parsed
    except ValueError as error:
        raise ContractError("utc") from error


def canonical(value, *, scientific=False):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=scientific,
                          allow_nan=False).encode("utf-8", "strict")
    except (ValueError, TypeError, UnicodeError, RecursionError) as error:
        raise ContractError("canonical") from error


def digest(value, *, scientific=False):
    return hashlib.sha256(canonical(value, scientific=scientific)).hexdigest()


def byte_sha(body):
    return hashlib.sha256(body).hexdigest()


class _Reader:
    """Token-aware parser: counts/bounds BEFORE allocating each token/container."""

    def __init__(self, source, depth, nodes):
        self.source, self.pos, self.depth, self.nodes = source, 0, depth, nodes

    def space(self):
        while self.pos < len(self.source) and self.source[self.pos] in " \t\r\n":
            self.pos += 1

    def take(self, char):
        self.space()
        require(self.pos < len(self.source) and self.source[self.pos] == char, "json")
        self.pos += 1

    def string(self, cap):
        self.take('"')
        start, escaped = self.pos - 1, False
        while self.pos < len(self.source):
            c = self.source[self.pos]
            self.pos += 1
            require(self.pos - start <= cap * 6 + 2, "string_limit")
            if c == '"' and not escaped:
                try:
                    result = json.loads(self.source[start:self.pos])
                    require(len(result.encode("utf-8", "strict")) <= cap, "string_limit")
                    return result
                except (ValueError, UnicodeError) as error:
                    raise ContractError("string") from error
            escaped = not escaped if c == "\\" else False
        raise ContractError("partial_json")

    def value(self, depth=1, key=None, *, build=True):
        self.space()
        self.nodes -= 1
        require(self.nodes >= 0 and depth <= self.depth, "structure_limit")
        require(self.pos < len(self.source), "partial_json")
        c = self.source[self.pos]
        if c == '"':
            return self.string(4 * ((4*M + 2)//3) if key == "base64" else 8192)
        if c == "{":
            self.pos += 1
            obj = {}
            self.space()
            if self.pos < len(self.source) and self.source[self.pos] == "}":
                self.pos += 1
                return obj
            while True:
                self.nodes -= 1
                require(self.nodes >= 0, "structure_limit")
                name = self.string(128)
                require(name not in obj, "duplicate_key")
                self.take(":")
                item = self.value(depth+1, name, build=build)
                # Scan pass retains only key uniqueness and the root schema;
                # no nested tree or vector is kept before per-schema admission.
                obj[name] = item if build or (depth == 1 and name == "schema") else None
                self.space()
                if self.pos < len(self.source) and self.source[self.pos] == "}":
                    self.pos += 1
                    return obj
                self.take(",")
        if c == "[":
            self.pos += 1
            result = []
            self.space()
            if self.pos < len(self.source) and self.source[self.pos] == "]":
                self.pos += 1
                return result
            while True:
                item = self.value(depth+1, build=build)
                if build:
                    result.append(item)
                self.space()
                if self.pos < len(self.source) and self.source[self.pos] == "]":
                    self.pos += 1
                    return result
                self.take(",")
        for literal, value in (("null", None), ("true", True), ("false", False)):
            if self.source.startswith(literal, self.pos):
                self.pos += len(literal)
                return value
        start = self.pos
        while self.pos < len(self.source) and self.source[self.pos] not in " \t\r\n,]}":
            self.pos += 1
            require(self.pos-start <= 128, "number_limit")
        token = self.source[start:self.pos]
        require(re.fullmatch(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?", token), "number")
        if "." not in token and "e" not in token.lower():
            value = int(token)
            require(abs(value) <= J, "integer_limit")
            return value
        value = float(token)
        require(math.isfinite(value), "nonfinite")
        return value


def decode_source(chunks, *, max_bytes, depth=32, nodes=2250000):
    integer(max_bytes, 1, 64*M)
    body = bytearray()
    for chunk in chunks:
        require(type(chunk) is bytes, "source_bytes")
        require(len(body) + len(chunk) <= max_bytes, "source_limit")
        body.extend(chunk)
    try:
        source = body.decode("utf-8", "strict")
    except UnicodeError as error:
        raise ContractError("encoding") from error
    require(not source.startswith("\ufeff"), "bom")
    reader = _Reader(source, depth, nodes)
    result = reader.value()
    reader.space()
    require(reader.pos == len(source), "trailing_json")
    return result  # Only returned after EOF, including trailing source chunks.


def descriptor(body):
    return {"bytes": len(body), "sha256": byte_sha(body), "base64": base64.b64encode(body).decode("ascii")}


def descriptor_bytes(value, cap):
    fields(value, "bytes sha256 base64")
    integer(value["bytes"], 1, cap)
    sha(value["sha256"])
    require(type(value["base64"]) is str and len(value["base64"]) <= 4*((cap+2)//3), "base64_limit")
    try:
        body = base64.b64decode(value["base64"], validate=True)
    except (ValueError, UnicodeError) as error:
        raise ContractError("base64") from error
    require(base64.b64encode(body).decode("ascii") == value["base64"], "base64")
    require(len(body) == value["bytes"] and byte_sha(body) == value["sha256"], "byte_identity")
    return body


def legacy_receipt(value):
    # Reuse the frozen positive v1 validator; no v1 file/DB/native entry point.
    from scripts.ops_recovery import RecoveryError, validate_tombstone
    try:
        validate_tombstone(value)
    except (RecoveryError, ValueError, TypeError, KeyError) as error:
        raise ContractError("legacy_receipt") from error
    for name in ("asset_hashes", "asset_manifest", "derived_manifest"):
        require(len(value[name]) <= 4096, "legacy_receipt_count")
    return value


def evidence(value):
    fields(value, "schema origin_kind origin_cipher_sha256 record canonical_record_sha256 sqlite_json")
    require(value["schema"] == "geophysics.deletion-receipt-evidence/v1", "schema")
    body = descriptor_bytes(value["record"], 4*M)
    parsed = legacy_receipt(decode_source([body], max_bytes=4*M, depth=12, nodes=150000))
    require(digest(parsed) == sha(value["canonical_record_sha256"]), "receipt_digest")
    if value["origin_kind"] == "v1_authority":
        sha(value["origin_cipher_sha256"])
        require(value["sqlite_json"] is None, "wire_native_invention")
    else:
        require(value["origin_kind"] == "sqlite_record" and value["origin_cipher_sha256"] is None, "receipt_origin")
        require(body == canonical(parsed), "sql_projection")
        fields(value["sqlite_json"], "asset_hashes asset_manifest derived_manifest")
        for name, desc in value["sqlite_json"].items():
            native = decode_source([descriptor_bytes(desc, M)], max_bytes=M, depth=12, nodes=150000)
            require(canonical(native) == canonical(parsed[name]), "native_json_disagreement")
    require(len(canonical(value)) <= 12*M, "receipt_limit")
    return parsed


def wrap_legacy_receipt(body, *, origin_cipher_sha256=None, sqlite_json=None):
    parsed = legacy_receipt(decode_source([body], max_bytes=4*M, depth=12, nodes=150000))
    result = dict(schema="geophysics.deletion-receipt-evidence/v1",
                  origin_kind="v1_authority" if sqlite_json is None else "sqlite_record",
                  origin_cipher_sha256=origin_cipher_sha256, record=descriptor(body),
                  canonical_record_sha256=digest(parsed),
                  sqlite_json=None if sqlite_json is None else {k: descriptor(v) for k, v in sqlite_json.items()})
    evidence(result)
    return result


CUSTODY_HEADER = "schema batch_id owner_id project_id origin_kind origin_id stage_id deletion_receipt_id raw_asset_id raw_sha256 raw_bytes parser_version method_id capacity_bytes"
CUSTODY_FILE = "ordinal role location artifact_id leaf max_bytes actual_bytes actual_sha256"


def custody_file(item, header, *, measured=True):
    fields(item, CUSTODY_FILE)
    integer(item["ordinal"], 1, 4096)
    integer(item["max_bytes"], 1, 1024*M)
    text(item["leaf"], 180)
    role, location = item["role"], item["location"]
    method = header["method_id"]
    names = {"input_spool": ("input.json", 16*M), "request_spool": ("request.json", 34*M),
             "scientific_output": ("scientific.json", 64*M if method == TRANSFORM else 16*M),
             "stdout_log": ("stdout.txt", 65536 if method else M),
             "stderr_log": ("stderr.txt", 65536 if method else M), "completion": ("complete.json", 4096)}
    caps = {"raw_delete": 1024*M, "dataset_copy": 64*M if method == TRANSFORM else 16*M, "result_copy": 64*M}
    if role in caps:
        uuid(item["artifact_id"])
    else:
        require(item["artifact_id"] is None, "custody_artifact")
    if location == "stage":
        require(header["origin_kind"] in ("root_stage", "job_stage"), "custody_location")
        if role in ("dataset_copy", "result_copy"):
            require(item["leaf"] == ("dataset.json" if role == "dataset_copy" else "result.json"), "custody_leaf")
            cap = caps[role]
        else:
            require(role in names, "custody_role_or_cache_closed")
            leaf, cap = names[role]
            require(item["leaf"] == leaf, "custody_leaf")
        if header["origin_kind"] == "root_stage":
            require(role in ("input_spool", "dataset_copy", "stdout_log", "stderr_log"), "root_stage_role")
    elif location == "pending_target":
        require(header["origin_kind"] == "publication_abandon" and role in ("dataset_copy", "result_copy"), "custody_location")
        lane = "datasets" if role == "dataset_copy" else "results"
        require(item["leaf"] == f"derived/{header['owner_id']}/{header['project_id']}/{lane}/{item['artifact_id']}.json", "custody_leaf")
        cap = caps[role]
    elif location == "deleting_raw":
        require(header["origin_kind"] == "project_deletion" and role == "raw_delete" and item["leaf"] == item["artifact_id"], "custody_location")
        cap = caps[role]
    elif location == "deleting_derived":
        require(header["origin_kind"] == "project_deletion" and role in ("dataset_copy", "result_copy"), "custody_location")
        lane = "datasets" if role == "dataset_copy" else "results"
        require(item["leaf"] == f"{lane}/{item['artifact_id']}.json", "custody_leaf")
        # Deletion may include terminal transforms. Full row audit applies the
        # admitted legacy/per-schema cap; this header covers multiple families.
        cap = 64*M
    else:
        raise ContractError("custody_location")
    require(item["max_bytes"] <= cap, "custody_file_cap")
    if measured:
        integer(item["actual_bytes"], 0, item["max_bytes"])
        sha(item["actual_sha256"])
    else:
        require(item["actual_bytes"] is None and item["actual_sha256"] is None, "custody_unmeasured")
    require(len(canonical(item)) <= 1024, "custody_file_limit")


def custody_header(value):
    require(value["schema"] == "geophysics.physical-custody/v1", "schema")
    for key in ("batch_id", "owner_id", "project_id", "origin_id"):
        uuid(value[key])
    origin, method = value["origin_kind"], value["method_id"]
    require(origin in ("root_stage", "job_stage", "publication_abandon", "project_deletion"), "custody_origin")
    require(method in (None, CORRECTION, TRANSFORM), "custody_method")
    if origin in ("root_stage", "job_stage"):
        require(uuid(value["stage_id"]) == value["origin_id"] and value["deletion_receipt_id"] is None, "custody_stage")
    elif origin == "publication_abandon":
        require(value["stage_id"] is None and value["deletion_receipt_id"] is None, "custody_abandon")
    else:
        require(value["stage_id"] is None and method is None, "custody_deletion")
        uuid(value["deletion_receipt_id"])
    if origin == "project_deletion":
        require(all(value[k] is None for k in ("raw_asset_id", "raw_sha256", "raw_bytes", "parser_version")), "custody_raw")
    else:
        uuid(value["raw_asset_id"])
        sha(value["raw_sha256"])
        integer(value["raw_bytes"], 1, 16*M)
        require(value["parser_version"] == "gravity-stations-json/v1", "custody_parser")
    integer(value["capacity_bytes"], 1, 1024*M*4096)
    if origin == "root_stage":
        require(method is None and value["capacity_bytes"] == 32*M, "custody_capacity")
    elif origin == "job_stage":
        require(method is not None and value["capacity_bytes"] == (512*M if method == TRANSFORM else 256*M), "custody_capacity")
    elif origin == "publication_abandon":
        require(value["capacity_bytes"] == (16*M if method is None else 128*M if method == TRANSFORM else 80*M), "custody_capacity")


def validate_custody(value):
    """Validate complete measured wire inventory, without asserting removals.

    Retained charge is literal SUM, not SHA deduplication. A runtime must separately
    prove each recorded removed ordinal's durable native removal/absence.
    """
    fields(value, CUSTODY_HEADER + " initial_files removed_ordinals")
    custody_header(value)
    entries = value["initial_files"]
    require(type(entries) is list and len(entries) <= (4096 if value["origin_kind"] == "project_deletion" else 64), "custody_count")
    ordinals, slots = [], set()
    for item in entries:
        custody_file(item, value)
        ordinals.append(item["ordinal"])
        slot = (item["location"], item["leaf"])
        require(slot not in slots, "custody_duplicate_slot")
        slots.add(slot)
    require(ordinals == sorted(set(ordinals)), "custody_ordinals")
    removed = value["removed_ordinals"]
    require(type(removed) is list and all(type(n) is int for n in removed) and removed == sorted(set(removed)) and set(removed) <= set(ordinals), "custody_removed_subset")
    initial_bytes = sum(item["actual_bytes"] for item in entries)
    require(initial_bytes <= value["capacity_bytes"], "custody_capacity")
    if value["origin_kind"] == "project_deletion":
        require(value["capacity_bytes"] == max(1, initial_bytes), "deletion_capacity")
    require(len(canonical(value)) <= 4*M, "custody_inventory_limit")
    return dict(retained_bytes=sum(item["actual_bytes"] for item in entries if item["ordinal"] not in removed),
                initial_inventory_sha256=digest(dict(value, removed_ordinals=[])), current_inventory_sha256=digest(value))


def _list(value, cap, key):
    require(type(value) is list and len(value) <= cap, "list_limit")
    identities = [item[key] for item in value if type(item) is dict and key in item]
    require(len(identities) == len(value) and identities == sorted(set(identities)), "list_identity")


def validate_tombstone(value):
    fields(value, "schema id project_id owner_id deleted_at origin_revision legacy_receipt physical_inventory")
    require(value["schema"] == "geophysics.physical-deletion/v2", "schema")
    receipt = evidence(value["legacy_receipt"])
    for name in ("id", "project_id", "owner_id", "deleted_at"):
        require(value[name] == receipt[name], "tombstone_identity")
    require(value["origin_revision"] in (LEGACY_REVISION, PHYSICAL_REVISION), "revision")
    if value["origin_revision"] == LEGACY_REVISION:
        require(value["physical_inventory"] is None, "legacy_inventory_invention")
    else:
        validate_deleted_inventory(value["physical_inventory"], receipt)


def validate_registration(value, *, embedded=False):
    fields(value, "schema snapshot_id sha256 created_at expires_at policy_id snapshot_schema database_revision source_policy_sha256 legacy_registration")
    require(value["schema"] == "geophysics.snapshot-registration/v2", "schema")
    uuid(value["snapshot_id"])
    if value["sha256"] is None:
        require(embedded, "registration_cipher")
    else:
        sha(value["sha256"])
        require(value["sha256"] != "0"*64, "registration_cipher")
    require(instant(value["expires_at"]) > instant(value["created_at"]), "expiry")
    require(type(value["policy_id"]) is str and re.fullmatch(r"[a-z0-9-]{1,64}", value["policy_id"]), "policy")
    if (value["snapshot_schema"], value["database_revision"]) == ("geophysics.restricted-snapshot/v1", LEGACY_REVISION):
        require(value["source_policy_sha256"] is None, "legacy_source_invention")
        old = decode_source([descriptor_bytes(value["legacy_registration"], 65536)], max_bytes=65536)
        fields(old, "snapshot_id sha256 created_at expires_at policy_id")
        for name in old:
            require(old[name] == value[name], "legacy_registration_identity")
    else:
        require((value["snapshot_schema"], value["database_revision"]) == ("geophysics.restricted-snapshot/v2", PHYSICAL_REVISION), "revision")
        sha(value["source_policy_sha256"])
        require(value["legacy_registration"] is None, "registration_origin")
    require(len(canonical(value)) <= 65536, "registration_limit")


def validate_authority(value, *, schema_registry=None):
    fields(value, "schema deployment_id fixture_only sequence predecessor_sha256 observed_at validation_policy_sha256 database_schemas legacy_predecessor tombstones snapshots")
    require(value["schema"] == "geophysics.recovery-authority/v2", "schema")
    uuid(value["deployment_id"])
    require(type(value["fixture_only"]) is bool, "boolean")
    integer(value["sequence"], 1)
    if value["sequence"] == 1:
        require(value["predecessor_sha256"] is None and value["legacy_predecessor"] is None, "predecessor")
    else:
        sha(value["predecessor_sha256"])
    instant(value["observed_at"])
    sha(value["validation_policy_sha256"])
    if value["legacy_predecessor"] is not None:
        fields(value["legacy_predecessor"], "schema sha256 sequence")
        require(value["legacy_predecessor"]["schema"] == "geophysics.recovery-authority/v1", "schema")
        require(sha(value["legacy_predecessor"]["sha256"]) == value["predecessor_sha256"], "predecessor")
        require(integer(value["legacy_predecessor"]["sequence"], 1)+1 == value["sequence"], "sequence")
    registry = {LEGACY_REVISION: LEGACY_DDL} if schema_registry is None else schema_registry
    _list(value["database_schemas"], 2, "revision")
    require(value["database_schemas"], "schema_registry")
    for item in value["database_schemas"]:
        fields(item, "revision ddl_sha256")
        require(item["revision"] in (LEGACY_REVISION, PHYSICAL_REVISION) and registry.get(item["revision"]) == sha(item["ddl_sha256"]), "schema_registry")
    _list(value["tombstones"], 4096, "project_id")
    require(len({item["id"] for item in value["tombstones"]}) == len(value["tombstones"]), "receipt_identity")
    for item in value["tombstones"]:
        require(item.get("schema") == "geophysics.physical-deletion/v2", "schema")
        validate_tombstone(item)
    _list(value["snapshots"], 4096, "snapshot_id")
    require(len({item["sha256"] for item in value["snapshots"]}) == len(value["snapshots"]), "cipher_identity")
    for item in value["snapshots"]:
        validate_registration(item)


def validate_deleted_inventory(value, receipt):
    # Full compact deletion inventory: does not claim to re-run lost physics.
    fields(value, "raw_assets datasets edges productions jobs custody source_policy_sha256")
    sha(value["source_policy_sha256"])
    from app.physical_persistence import DATASET_REGISTRY
    raw, datasets, jobs = {}, {}, {}
    definitions = {
        "raw_assets": ("asset_id", "asset_id source_id sha256 bytes"),
        "datasets": ("dataset_id", "dataset_id raw_asset_id root_dataset_id parent_dataset_id version parser_version kind modality payload_schema sha256 bytes"),
        "edges": ("child_dataset_id", "parent_dataset_id child_dataset_id role parent_dataset_sha256"),
        "productions": ("child_dataset_id", "child_dataset_id job_id input_dataset_id input_dataset_sha256 method_id request_sha256 result_sha256 result_bytes submitted_parameters_sha256 scientific_request_sha256 scientific_result_sha256 adapter_result_sha256 module_manifest_sha256 scientific_verdict"),
        "jobs": ("job_id", "job_id dataset_id dataset_sha256 method_id state request_sha256 result_sha256 result_bytes physical_fingerprint physical_control_sha256 scientific_verdict"),
        "custody": ("batch_id", "batch_id origin_kind origin_id initial_inventory_sha256"),
    }
    for name, (key, keys) in definitions.items():
        _list(value[name], 4096, key)
        for item in value[name]:
            fields(item, keys)
            for field, data in item.items():
                if field.endswith("_id") and field != "method_id" and data is not None:
                    uuid(data)
                elif field.endswith("sha256") and data is not None:
                    sha(data)
            if name == "raw_assets":
                integer(item["bytes"], 1, 1024*M)
                raw[item[key]] = item
            elif name == "datasets":
                integer(item["version"], 1)
                require((item["kind"], item["parser_version"], item["modality"], item["payload_schema"]) in DATASET_REGISTRY, "dataset_discriminator")
                integer(item["bytes"], 1, 64*M if item["payload_schema"] == "gravity-transform-result-1" else 16*M)
                datasets[item[key]] = item
            elif name == "jobs":
                require(item["method_id"] in METHODS and item["state"] in ("succeeded", "failed", "cancelled"), "job_discriminator")
                success, physical = item["state"] == "succeeded", item["method_id"] in (CORRECTION, TRANSFORM)
                require((item["result_sha256"] is not None) == success and (item["result_bytes"] is not None) == success, "job_result")
                if success:
                    integer(item["result_bytes"], 1, 64*M)
                require((item["physical_fingerprint"] is not None) == physical and (item["physical_control_sha256"] is not None) == physical, "job_control")
                if physical:
                    sha(item["physical_fingerprint"])
                require(item["scientific_verdict"] in (("passed", "non_pass") if physical and success else (None,)), "job_verdict")
                jobs[item[key]] = item
            elif name == "custody":
                require(item["origin_kind"] in ("root_stage", "job_stage", "publication_abandon", "project_deletion"), "custody_origin")
    require(sum(len(value[n]) for n in definitions) <= 20000 and len(canonical(value)) <= 4*M, "inventory_limit")
    edges = {e["child_dataset_id"]: e for e in value["edges"]}
    productions = {p["child_dataset_id"]: p for p in value["productions"]}
    for identifier, row in datasets.items():
        require(row["raw_asset_id"] in raw, "raw_binding")
        if row["kind"] == "root":
            require(row["version"] == 1 and row["root_dataset_id"] == identifier and row["parent_dataset_id"] is None and identifier not in edges and identifier not in productions, "root_binding")
        else:
            parent = datasets.get(row["parent_dataset_id"])
            require(parent is not None and parent["version"] < row["version"] and parent["raw_asset_id"] == row["raw_asset_id"] and parent["root_dataset_id"] == row["root_dataset_id"], "parent_binding")
            edge, production = edges.get(identifier), productions.get(identifier)
            require(edge is not None and production is not None and edge["role"] == "scientific_input" and edge["parent_dataset_id"] == row["parent_dataset_id"] and edge["parent_dataset_sha256"] == parent["sha256"], "edge_binding")
            job = jobs.get(production["job_id"])
            require(job is not None and job["state"] == "succeeded" and production["input_dataset_id"] == parent["dataset_id"] and production["input_dataset_sha256"] == parent["sha256"], "producer_binding")
            for field in ("method_id", "request_sha256", "result_sha256", "result_bytes", "scientific_verdict"):
                require(production[field] == job[field], "producer_binding")
            require(job["dataset_id"] == parent["dataset_id"] and job["dataset_sha256"] == parent["sha256"], "producer_binding")
            require(production["method_id"] in (CORRECTION, TRANSFORM), "producer_method")
            if production["method_id"] == CORRECTION:
                require(production["scientific_verdict"] == "passed" and production["adapter_result_sha256"] == production["scientific_result_sha256"], "adapter_binding")
            else:
                require(production["adapter_result_sha256"] is None and row["payload_schema"] == "gravity-transform-result-1" and parent["payload_schema"] == "gravity-station-adapter-result-1", "transform_binding")
    require(set(edges) == set(productions) == {k for k,v in datasets.items() if v["kind"] == "derived"}, "graph_completeness")
    for job in jobs.values():
        require(job["dataset_id"] in datasets and datasets[job["dataset_id"]]["sha256"] == job["dataset_sha256"], "job_input")
    projected_raw = sorted((x["asset_id"], x["sha256"], x["bytes"]) for x in raw.values())
    projected_derived = sorted([("dataset", x["dataset_id"], x["sha256"], x["bytes"]) for x in datasets.values()] + [("result", x["job_id"], x["result_sha256"], x["result_bytes"]) for x in jobs.values() if x["state"] == "succeeded"])
    require(len(projected_raw)+len(projected_derived) <= 4096, "deletion_file_limit")
    require(projected_raw == sorted((x["asset_id"], x["sha256"], x["byte_count"]) for x in receipt["asset_manifest"]), "legacy_projection")
    require(projected_derived == sorted((x["kind"], x["id"], x["sha256"], x["byte_count"]) for x in receipt["derived_manifest"]), "legacy_projection")


def parse_record(chunks, *, schema_registry=None):
    body = bytearray()
    for chunk in chunks:
        require(type(chunk) is bytes and len(body)+len(chunk) <= 16*M, "source_limit")
        body.extend(chunk)
    try:
        source = body.decode("utf-8", "strict")
    except UnicodeError as error:
        raise ContractError("encoding") from error
    require(not source.startswith("\ufeff"), "bom")
    scan = _Reader(source, 16, 250000)
    header = scan.value(build=False)
    scan.space()
    require(scan.pos == len(source), "trailing_json")
    require(type(header) is dict and type(header.get("schema")) is str, "schema")
    schema = header["schema"]
    limits = {"geophysics.deletion-receipt-evidence/v1": (12*M,12,150000),
              "geophysics.snapshot-registration/v2": (65536,8,1000),
              "geophysics.physical-custody/v1": (4*M,8,100000),
              "geophysics.physical-deletion/v2": (16*M,16,200000),
              "geophysics.recovery-authority/v2": (16*M,16,250000)}
    require(schema in limits, "unknown_schema")
    cap, depth, nodes = limits[schema]
    require(len(body) <= cap, "source_limit")
    value = decode_source([bytes(body)], max_bytes=cap, depth=depth, nodes=nodes)
    if schema == "geophysics.deletion-receipt-evidence/v1":
        evidence(value)
    elif schema == "geophysics.physical-deletion/v2":
        validate_tombstone(value)
    elif schema == "geophysics.recovery-authority/v2":
        validate_authority(value, schema_registry=schema_registry)
    elif schema == "geophysics.snapshot-registration/v2":
        validate_registration(value)
    elif schema == "geophysics.physical-custody/v1":
        validate_custody(value)
    else:
        raise ContractError("unknown_schema")
    return value
