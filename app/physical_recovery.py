"""Pure candidate recovery decisions. Never opens a target or changes state."""

from __future__ import annotations

import copy
import math
import re
from dataclasses import dataclass
from types import MappingProxyType

from app.physical_contract import (
    ContractError, M, canonical, digest, evidence, fields, integer, instant,
    parse_record, require, sha, text, uuid, byte_sha, decode_source, custody_header, custody_file,
)


@dataclass(frozen=True)
class Outcome:
    classification: str
    disposition: str
    reason: str
    runtime: bool = False
    fixture_only: bool = True
    account_charges: object = None
    inventory_sha256: str | None = None


def _body(descriptor, bodies, cap):
    fields(descriptor, "type bytes sha256")
    integer(descriptor["bytes"], 0, cap)
    h = sha(descriptor["sha256"])
    require(h in bodies and type(bodies[h]) is bytes, "body_missing")
    body = bodies[h]
    require(len(body) == descriptor["bytes"] and byte_sha(body) == h, "body_identity")
    return body


def _domain(value, column):
    if value is None:
        require(column.nullable, "sql_null")
        return
    d = column.domain
    if d in ("U", "O"):
        uuid(value)
    elif d == "H":
        sha(value)
    elif d[0] == "I":
        integer(value, d[1], d[2])
    elif d[0] == "E":
        require(value in d[1:], "sql_enum")
    elif d[0] == "T":
        text(value, d[1])
    elif d[0] == "B":
        require(type(value) is bytes and 1 <= len(value) <= d[1], "sql_blob")


def _read_rows(inventory, bodies):
    """All columns/types/keys/FKs, before any operation-specific disposition.

    Metadata inspection is read-only; no Engine/Session/SQL/native call. Exact
    conditional scientific/cut predicates are checked separately, never eval SQL.
    """
    from app.models import Base
    from app.physical_persistence import TABLES, DATASET_COLUMNS, column
    from sqlalchemy import Boolean, DateTime, Integer, JSON, String, UniqueConstraint
    extra_jobs = (column("physical_cpu_ms", ("I", 0, 9007199254740991), True), column("physical_fingerprint", "H", True))
    expected = set(Base.metadata.tables) | set(TABLES) | {"alembic_version"}
    rows = inventory["rows"]
    require(type(rows) is dict and set(rows) == expected, "table_set")
    require(sum(len(v) for v in rows.values() if type(v) is list) <= 100000, "row_limit")
    result, keys, constraints, foreign = {}, {}, {}, []
    for name in sorted(expected):
        require(type(rows[name]) is list, "row_list")
        if name == "alembic_version":
            columns, pk, unique = {"version_num": None}, ("version_num",), []
        elif name in TABLES:
            table = TABLES[name]
            columns = {c.name: c for c in table.columns}
            pk, unique = table.primary_key, [cols for _, cols in table.uniques]
            foreign += [(name, cols, target, refs) for _, cols, target, refs in table.foreign_keys]
            # Only these declared nullable-key partials are active here. The
            # job fingerprint's state predicate is checked with the job contract.
            unique += [cols for _, cols, is_unique, where in table.indexes if is_unique and where in ("job_id IS NOT NULL", "stage_id IS NOT NULL")]
        else:
            table = Base.metadata.tables[name]
            columns = dict(table.columns.items())
            if name == "observation_datasets":
                columns.update({c.name: c for c in DATASET_COLUMNS})
            if name == "processing_jobs":
                columns.update({c.name: c for c in extra_jobs})
            pk = tuple(c.name for c in table.primary_key.columns)
            unique = [tuple(c.name for c in u.columns) for u in table.constraints if isinstance(u, UniqueConstraint)]
            if name == "observation_datasets":
                unique.remove(("raw_asset_id", "parser_version"))
                unique += [("root_dataset_id", "version")]
            foreign += [(name, tuple(c.name for c in f.columns), f.referred_table.name, tuple(e.column.name for e in f.elements)) for f in table.foreign_key_constraints]
        result[name] = []
        for encoded in rows[name]:
            require(type(encoded) is dict and set(encoded) == set(columns), "column_set")
            decoded = {}
            for key, c in columns.items():
                item = encoded[key]
                require(type(item) is dict and item.get("type") in ("integer", "real", "text", "null", "blob", "json_text"), "sql_type")
                kind = item["type"]
                if kind in ("blob", "json_text"):
                    cap = c.domain[1] if hasattr(c, "domain") and c.domain[0] == "B" else (35*M if name == "processing_jobs" and key == "request_json" else M)
                    value = _body(item, bodies, cap)
                    if kind == "json_text":
                        decode_source([value], max_bytes=cap, depth=32, nodes=2250000)
                    require((hasattr(c, "domain") and c.domain[0] == "B" and kind == "blob") or (c is not None and not hasattr(c, "domain") and isinstance(c.type, JSON) and kind == "json_text"), "sql_type")
                else:
                    fields(item, "type value")
                    value = item["value"]
                    require((kind == "null" and value is None) or (kind == "integer" and type(value) is int and -(2**63) <= value < 2**63) or (kind == "real" and type(value) is float and math.isfinite(value)) or (kind == "text" and type(value) is str), "sql_scalar")
                    if kind == "text":
                        require(len(value.encode("utf-8", "strict")) <= 8192 and "\0" not in value, "sql_text")
                if hasattr(c, "domain"):
                    _domain(value, c)
                elif c is None:
                    require(kind == "text" and value == inventory["database_revision"], "revision")
                elif value is None:
                    require(c.nullable, "sql_null")
                elif isinstance(c.type, JSON):
                    require(kind == "json_text", "sql_json_text")
                elif isinstance(c.type, (Integer, Boolean)):
                    require(kind == "integer", "sql_integer")
                    if isinstance(c.type, Boolean):
                        require(value in (0, 1), "sql_boolean")
                elif isinstance(c.type, DateTime):
                    require(kind == "text", "sql_time")
                    instant(value, legacy=True)
                else:
                    require(kind == "text", "sql_text")
                    if isinstance(c.type, String) and c.type.length:
                        require(len(value.encode("utf-8")) <= c.type.length, "sql_string")
                    if str(c.type).startswith("CHAR(36)"):
                        uuid(value)
                if value is not None and not hasattr(c, "domain") and name != "alembic_version":
                    if (key == "id" and name != "rate_windows") or key in ("owner_id", "project_id", "source_id", "raw_asset_id", "dataset_id", "user_id"):
                        uuid(value)
                decoded[key] = value
            result[name].append(decoded)
        tuples = [tuple(row[c] for c in pk) for row in result[name]]
        require(all(all(x is not None for x in k) for k in tuples) and tuples == sorted(tuples) and len(set(tuples)) == len(tuples), "primary_keys")
        keys[name], constraints[name] = pk, unique
    require(len(result["alembic_version"]) == 1, "revision_rows")
    for name, unique in constraints.items():
        for cols in unique:
            values = [tuple(row[c] for c in cols) for row in result[name] if all(row[c] is not None for c in cols)]
            require(len(set(values)) == len(values), "unique")
    for name, cols, target, refs in foreign:
        targets = {tuple(row[c] for c in refs) for row in result[target]}
        require(all(any(row[c] is None for c in cols) or tuple(row[c] for c in cols) in targets for row in result[name]), "foreign_key")
    return result


def _root_reservations(inventory, bodies, rows):
    """Exact pre-parse root-stage cut; never adopts or parses a scientific root."""
    allowed = {"alembic_version", "user", "access_tokens", "projects", "source_records", "raw_assets", "account_usage", "rate_windows", "physical_custody_batches", "physical_custody_files"}
    require(all(not values for name, values in rows.items() if name not in allowed), "cut_not_yet_supported")
    projects = {r["id"]: r for r in rows["projects"]}
    sources = {r["id"]: r for r in rows["source_records"]}
    raw = {r["id"]: r for r in rows["raw_assets"]}
    charges = {r["id"]: 0 for r in rows["user"]}
    expected_files = {}
    def file(key, owner, project, origin, role, count=None, h=None, cap=1024*M, required=True):
        require(key not in expected_files, "file_overlap")
        expected_files[key] = (owner, project, origin, role, count, h, cap, required)
    raw_sum = dict(charges)
    for r in rows["source_records"]:
        require(projects[r["project_id"]]["owner_id"] == r["owner_id"], "source_owner")
        require(r["declared_format"] == "gravity_stations_json" and r["private_storage_permission"] == "attested" and r["rights_decision"] == "mirror", "source_contract")
        uuid(r["id"])
        integer(r["version"], 1)
        sha(r["sha256"])
        if r["expected_bytes"] is not None:
            integer(r["expected_bytes"], 1, 16*M)
    for r in raw.values():
        s = sources[r["source_id"]]
        require((s["owner_id"], s["project_id"], s["sha256"]) == (r["owner_id"], r["project_id"], r["sha256"]), "raw_source")
        require(s["expected_bytes"] in (None, r["byte_count"]), "raw_source_bytes")
        require(r["detected_format"] == "gravity_stations_json" and r["validation_status"] == "raw_metadata_checked", "raw_discriminator")
        integer(r["byte_count"], 1, 16*M)
        uuid(r["id"])
        sha(r["sha256"])
        key = f'projects/{r["owner_id"]}/{r["project_id"]}/{r["id"]}'
        require(r["storage_key"] == key, "raw_key")
        file(key, r["owner_id"], r["project_id"], r["id"], "raw", r["byte_count"], r["sha256"], 16*M)
        charges[r["owner_id"]] += r["byte_count"]
        raw_sum[r["owner_id"]] += r["byte_count"]
    usage = {r["user_id"]: r["raw_bytes"] for r in rows["account_usage"]}
    require(all(usage.get(owner, 0) == count for owner, count in raw_sum.items()), "raw_accounting")
    batches = {r["batch_id"]: r for r in rows["physical_custody_batches"]}
    slots = {key: [] for key in batches}
    for slot in rows["physical_custody_files"]:
        slots[slot["batch_id"]].append(slot)
    for batch in batches.values():
        require(batch["origin_kind"] == "root_stage" and batch["state"] in ("reserved", "active"), "root_cut")
        require(batch["project_id"] in projects and projects[batch["project_id"]]["owner_id"] == batch["owner_id"], "batch_owner")
        r = raw.get(batch["raw_asset_id"])
        require(r is not None and (r["owner_id"], r["project_id"], r["sha256"], r["byte_count"]) == (batch["owner_id"], batch["project_id"], batch["raw_sha256"], batch["raw_bytes"]), "batch_raw")
        for key in ("inventory_bytes", "inventory_sha256", "sealed_us", "removed_us"):
            require(batch[key] is None, "unsealed_stage")
        require(batch["charged_bytes"] == batch["capacity_bytes"] == 32*M, "reservation_charge")
        header = {key: batch[key] for key in ("batch_id", "owner_id", "project_id", "origin_kind", "origin_id", "stage_id", "deletion_receipt_id", "raw_asset_id", "raw_sha256", "raw_bytes", "parser_version", "method_id", "capacity_bytes")}
        header["schema"] = "geophysics.physical-custody/v1"
        custody_header(header)
        require(1 <= len(slots[batch["batch_id"]]) <= 64, "root_slot_count")
        roles = set()
        for slot in slots[batch["batch_id"]]:
            require(slot["state"] == "reserved", "unsealed_file")
            entry = {k: v for k,v in slot.items() if k not in ("batch_id", "state")}
            custody_file(entry, header, measured=False)
            require(slot["role"] not in roles, "root_slot_role")
            roles.add(slot["role"])
            is_input = slot["role"] == "input_spool"
            file(f'.job-staging/{batch["stage_id"]}/{slot["leaf"]}', batch["owner_id"], batch["project_id"], batch["batch_id"], slot["role"], r["byte_count"] if is_input else None, r["sha256"] if is_input else None, slot["max_bytes"], False)
        require("input_spool" in roles, "input_slot")
        charges[batch["owner_id"]] += batch["charged_bytes"]
    files = inventory["files"]
    require(type(files) is dict and len(files) <= 100000 and "@database" in files and ".physical-writers.lock" in files, "file_inventory")
    actual_total, stage_totals = 0, {batch: 0 for batch in batches}
    for key, d in files.items():
        fields(d, "bytes sha256 role owner_id project_id origin_id")
        if key in ("@database", "@wal", "@shm"):
            require(d == dict(bytes=None, sha256=None, role="native_metadata", owner_id=None, project_id=None, origin_id=None), "native_metadata")
            continue  # Supplied fixture marker, NOT native identity/durability proof.
        if key == ".physical-writers.lock":
            require(d == dict(bytes=1, sha256=byte_sha(b"\0"), role="writer_lock", owner_id=None, project_id=None, origin_id=None), "writer_lock")
            _body(dict(type="blob", bytes=1, sha256=d["sha256"]), bodies, 1)
            continue
        require(key in expected_files, "undeclared_file")
        owner, project, origin, role, count, h, cap, _ = expected_files[key]
        require((d["owner_id"], d["project_id"], d["origin_id"], d["role"]) == (owner, project, origin, role), "file_owner")
        integer(d["bytes"], 0, cap)
        if count is not None:
            require((d["bytes"], d["sha256"]) == (count, h), "file_binding")
        _body(dict(type="blob", bytes=d["bytes"], sha256=d["sha256"]), bodies, cap)
        actual_total += d["bytes"]
        require(actual_total <= 4096*M, "audit_bytes")
        if origin in batches:
            stage_totals[origin] += d["bytes"]
    require(all(not info[-1] or key in files for key, info in expected_files.items()), "committed_file_missing")
    require(all(stage_totals[key] <= b["capacity_bytes"] for key,b in batches.items()), "stage_capacity")
    require(all(charge <= 1024*M for charge in charges.values()), "account_quota")
    require(bool(batches), "root_reservation_required")
    return MappingProxyType(charges)


def classify_fixture(inventory, bodies, *, schema_registry=None, source_policy_sha256=None):
    """Complete EOF/body barrier for supplied pure-data root reservation fixtures.

    No native/maintenance proof is inferred. Other cuts remain closed until their
    entire positive predicates and negative fixtures are implemented/reviewed.
    """
    try:
        fields(inventory, "schema database_revision ddl_sha256 source_policy_sha256 storage_generation lease_generation rows files")
        require(inventory["schema"] == "geophysics.physical-inventory/v1" and inventory["database_revision"] == "0004_physical_persistence", "inventory_schema")
        require(type(schema_registry) is dict and schema_registry.get(inventory["database_revision"]) == sha(inventory["ddl_sha256"]), "unregistered_schema")
        require(source_policy_sha256 is not None and sha(source_policy_sha256) == inventory["source_policy_sha256"], "unregistered_source")
        uuid(inventory["storage_generation"])
        integer(inventory["lease_generation"], 1)
        # Whole-object structural ceilings apply even when callers supply dicts.
        encoded = canonical(inventory)
        decode_source([encoded], max_bytes=16*M, depth=16, nodes=500000)
        require(type(bodies) is dict, "body_map")
        rows = _read_rows(inventory, bodies)
        charges = _root_reservations(inventory, bodies, rows)
        projection = copy.deepcopy(inventory)
        for key in ("@database", "@wal", "@shm"):
            projection["files"].pop(key, None)
        for row in projection["rows"]["physical_runtime_control"]:
            for key in ("last_clean_inventory_sha256", "audited_us"):
                row[key] = dict(type="null", value=None)
        return Outcome("prepared_uncommitted", "retain_reservation", "complete_root_stage_reservation", account_charges=charges, inventory_sha256=digest(projection))
    except (ContractError, UnicodeError, TypeError, KeyError, ValueError) as error:
        reason = str(error) if isinstance(error, ContractError) else "inventory_refused"
        return Outcome("inconsistent", "preserve_inconsistent", reason)


def classify_fixture_source(chunks, bodies, *, schema_registry=None, source_policy_sha256=None):
    """One result only AFTER complete bounded source EOF; never a yield/callback.

    Descriptors must still pass the complete body/row audit. Source parsing alone
    grants no disposition, native proof, physical API or publication authority.
    """
    try:
        value = decode_source(chunks, max_bytes=16*M, depth=16, nodes=500000)
    except ContractError as error:
        return Outcome("inconsistent", "preserve_inconsistent", str(error))
    return classify_fixture(value, bodies, schema_registry=schema_registry, source_policy_sha256=source_policy_sha256)


def merge_authorities(before, after, *, predecessor_cipher_sha256, current_cipher_sha256, latest, schema_registry=None, now=None):
    """Verify a complete supplied fixture link and explicit latest descriptor.

    No returned object is an external checkpoint ACK or runtime activation.
    """
    before = parse_record([canonical(before)], schema_registry=schema_registry)
    after = parse_record([canonical(after)], schema_registry=schema_registry)
    require(before["fixture_only"] is True and after["fixture_only"] is True, "fixture_only")
    fields(latest, "deployment_id authority_sha256 sequence observed_at validation_policy_sha256")
    uuid(latest["deployment_id"])
    integer(latest["sequence"], 1)
    sha(latest["authority_sha256"])
    require(after["sequence"] == before["sequence"]+1 and after["predecessor_sha256"] == sha(predecessor_cipher_sha256), "authority_predecessor")
    require(after["legacy_predecessor"] is None, "authority_predecessor")
    for field in ("deployment_id", "validation_policy_sha256"):
        require(before[field] == after[field] == latest[field], "authority_identity")
    # Cipher identities are supplied independently; plaintext serialization is
    # NOT the ciphertext hash. This pure comparison cannot authenticate age.
    require(latest["sequence"] == after["sequence"] and latest["observed_at"] == after["observed_at"] and latest["authority_sha256"] == sha(current_cipher_sha256), "latest_watermark")
    require(instant(after["observed_at"]) >= instant(before["observed_at"]), "authority_time")
    if now is not None:
        require(instant(after["observed_at"]) <= instant(now), "authority_future")
    else:
        # The descriptor comparison is a fixture link check, NOT freshness proof.
        require(after["fixture_only"] is True, "trusted_current_time_required")
    for name, key in (("tombstones", "project_id"), ("snapshots", "snapshot_id")):
        current = {item[key]: item for item in after[name]}
        for item in before[name]:
            require(item[key] in current and canonical(current[item[key]]) == canonical(item), "authority_history_rewrite")
    require(before["database_schemas"] == after["database_schemas"], "authority_schema_change_requires_review")
    return copy.deepcopy(after)


def bridge_legacy_fixture(snapshot, authority):
    """Compare a supplied *fixture* legacy file index against typed tombstones.

    Does not validate a DB/archive or emit a restore receipt. The full v1 source
    validator remains mandatory before any separately authorized live adapter.
    It returns removal identities only, without mutating input or serializing
    existing SQL receipt text.
    """
    fields(snapshot, "projects files receipts")
    for name in snapshot:
        require(type(snapshot[name]) is dict and len(snapshot[name]) <= 100000, "fixture_index")
    for project, owner in snapshot["projects"].items():
        uuid(project)
        uuid(owner)
    for identifier, item in snapshot["files"].items():
        uuid(identifier)
        fields(item, "owner_id project_id sha256 bytes")
        uuid(item["owner_id"])
        uuid(item["project_id"])
        sha(item["sha256"])
        integer(item["bytes"], 0, 1024*M)
        require(snapshot["projects"].get(item["project_id"]) == item["owner_id"], "fixture_owner")
    authority = parse_record([canonical(authority)])
    require(authority["fixture_only"] is True, "fixture_only")
    removed, insertable = [], []
    for tombstone in authority["tombstones"]:
        project, owner = tombstone["project_id"], tombstone["owner_id"]
        if project in snapshot["projects"]:
            require(snapshot["projects"][project] == owner, "deletion_owner")
            removed.append(project)
        old = evidence(tombstone["legacy_receipt"])
        for name, key in (("asset_manifest", "asset_id"), ("derived_manifest", "id")):
            for item in old[name]:
                if item[key] not in snapshot["files"]:
                    continue  # Later legitimate nodes need not exist in old snapshot.
                present = snapshot["files"][item[key]]
                require((present["owner_id"], present["project_id"], present["sha256"], present["bytes"]) ==
                        (owner, project, item["sha256"], item["byte_count"]), "overlapping_identity")
        if project in snapshot["receipts"]:
            observed = evidence(snapshot["receipts"][project])
            require(canonical(observed) == canonical(old), "receipt_conflict")
        else:
            insertable.append(copy.deepcopy(tombstone["legacy_receipt"]))
    return dict(fixture_only=True, runtime=False, removed_projects=tuple(sorted(removed)),
                missing_receipt_evidence=tuple(insertable))


def verify_patch_descriptor(value, *, supported):
    """Only data comparison with an explicit independently reviewed fixture set.

    Production registry stays empty. No version/source_id is probed here and
    no SQL target is opened. A successful comparison is not native proof.
    """
    fields(value, "schema sqlite_version sqlite_source_id platform python python_implementation linkage binaries patch_provenance validation_policy_sha256 reviewed_evidence_sha256")
    require(value["schema"] == "geophysics.sqlite-wal-patch-build/v1", "schema")
    text(value["sqlite_version"], 40)
    text(value["sqlite_source_id"], 120)
    require(value["platform"] in ("linux-local", "windows-local"), "platform")
    require(type(value["python"]) is str and re.fullmatch(r"3\.12\.\d+(?:[a-z0-9.+-]*)?", value["python"]) and len(value["python"]) <= 40 and value["python_implementation"] == "CPython", "python")
    require(value["linkage"] in ("static", "dynamic"), "linkage")
    require(type(value["binaries"]) is list and 1 <= len(value["binaries"]) <= 8, "binaries")
    roles, identities = set(), set()
    for item in value["binaries"]:
        fields(item, "role artifact_id bytes sha256")
        require(item["role"] in ("interpreter", "python_extension", "sqlite_library"), "binary_role")
        text(item["artifact_id"], 180)
        require(not any(c in item["artifact_id"] for c in ("/", "\\", ":")), "artifact_not_path")
        integer(item["bytes"], 1, 1024*M)
        sha(item["sha256"])
        identity = (item["role"], item["artifact_id"])
        require(identity not in identities, "binary_duplicate")
        identities.add(identity)
        roles.add(item["role"])
    require("interpreter" in roles and (value["linkage"] != "dynamic" or "sqlite_library" in roles), "binary_missing")
    p = value["patch_provenance"]
    fields(p, "kind upstream_reference reference_receipt_sha256 patch_evidence_sha256 distribution_id distribution_version")
    text(p["upstream_reference"])
    require(p["upstream_reference"].startswith("https://"), "upstream_reference")
    sha(p["reference_receipt_sha256"])
    sha(p["patch_evidence_sha256"])
    if p["kind"] == "distribution_backport":
        text(p["distribution_id"], 180)
        text(p["distribution_version"], 180)
    else:
        require(p["distribution_id"] is None and p["distribution_version"] is None, "distribution")
        if p["kind"] == "upstream_documented_backport":
            require(value["sqlite_version"] in ("3.44.6", "3.50.7"), "backport_tuple")
        else:
            require(p["kind"] == "upstream_release" and re.fullmatch(r"\d+\.\d+\.\d+", value["sqlite_version"]), "patch_kind")
            require(tuple(map(int, value["sqlite_version"].split("."))) >= (3, 51, 3), "affected_build")
    sha(value["validation_policy_sha256"])
    sha(value["reviewed_evidence_sha256"])
    require(len(canonical(value)) <= 65536, "patch_limit")
    require(any(canonical(value) == canonical(reviewed) for reviewed in supported), "unregistered_patch_tuple")
    return dict(fixture_only=True, runtime=False, build_descriptor_sha256=digest(value))
