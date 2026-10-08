"""Atomic SQL forest preparation; no installed files or scientific success.

This candidate-only ledger co-commits the ordinal, intent and BOTH targets.
It does not admit a child to computation or publish one; callers still need
complete source/producer/scientific/native verification for those transitions.
"""

import sqlite3

from app.physical_contract import byte_sha, fields, integer, parse_record, require, sha, uuid, validate_custody
from app.physical_persistence import CORRECTION, TRANSFORM, J, M
from app.physical_successor import REVISION, ddl_sha256

SUCCESSOR_DDL = "b35d30cbbc77e7c26ad4d4c0efa7d2365cdd582e7e22979ca1ae0461ef1dacb4"


def _row(connection, sql, parameters):
    cursor = connection.execute(sql, parameters)
    row = cursor.fetchone()
    require(row is not None, "forest_identity_not_found")
    require(cursor.fetchone() is None, "forest_identity_duplicate")
    return dict(zip((c[0] for c in cursor.description), row))


def _parent_chain(connection, parent, owner, project):
    seen = set()
    current = parent
    depth = 0
    while True:
        require(current["id"] not in seen, "forest_cycle")
        seen.add(current["id"])
        require((current["owner_id"], current["project_id"], current["root_dataset_id"], current["raw_asset_id"], current["parser_version"]) ==
                (owner, project, parent["root_dataset_id"], parent["raw_asset_id"], "gravity-stations-json/v1"), "forest_parent_identity")
        if current["kind"] == "root":
            require(current["id"] == parent["root_dataset_id"] and current["version"] == 1
                    and current["parent_dataset_id"] is None and current["payload_schema"] == "gravity-stations-1", "forest_root")
            break
        require(current["kind"] == "derived" and current["payload_schema"] == "gravity-station-adapter-result-1", "forest_terminal_parent")
        ancestor = _row(connection, "SELECT * FROM observation_datasets WHERE id=?", (current["parent_dataset_id"],))
        edge = _row(connection, "SELECT * FROM physical_dataset_edges WHERE child_dataset_id=?", (current["id"],))
        production = _row(connection, "SELECT * FROM physical_dataset_productions WHERE child_dataset_id=?", (current["id"],))
        require(ancestor["version"] < current["version"] and edge["parent_dataset_id"] == ancestor["id"]
                and edge["parent_dataset_sha256"] == ancestor["sha256"]
                and production["parent_dataset_id"] == ancestor["id"]
                and production["parent_dataset_sha256"] == ancestor["sha256"]
                and production["method_id"] == CORRECTION and production["scientific_verdict"] == "passed", "forest_parent_relation")
        depth += 1
        require(depth < 4, "forest_depth_limit")  # New child adds one edge.
        current = ancestor


def _targets(connection, control, values, child, job, owner, project):
    require(type(values) is list and len(values) == 2, "forest_dual_targets_required")
    kinds = set()
    batch = _row(connection, "SELECT * FROM physical_custody_batches WHERE stage_id=?", (control["stage_id"],))
    require(batch["state"] == "sealed" and batch["origin_kind"] == "job_stage"
            and (batch["owner_id"], batch["project_id"], batch["raw_asset_id"], batch["raw_sha256"], batch["raw_bytes"], batch["method_id"]) ==
            (owner, project, control["raw_asset_id"], control["raw_sha256"], control["raw_bytes"], control["method_id"]), "forest_stage_binding")
    body = batch["inventory_bytes"]
    require(type(body) is bytes and byte_sha(body) == batch["inventory_sha256"], "forest_stage_inventory")
    inventory = parse_record([body])
    require(all(inventory[key] == batch[key] for key in inventory if key not in
                ("schema", "initial_files", "removed_ordinals")), "forest_stage_inventory")
    require(inventory["batch_id"] == batch["batch_id"] and inventory["stage_id"] == control["stage_id"]
            and inventory["owner_id"] == owner and inventory["project_id"] == project
            and inventory["raw_asset_id"] == control["raw_asset_id"] and inventory["raw_sha256"] == control["raw_sha256"]
            and inventory["raw_bytes"] == control["raw_bytes"] and inventory["method_id"] == control["method_id"]
            and not inventory["removed_ordinals"], "forest_stage_inventory")
    require(validate_custody(inventory)["retained_bytes"] == batch["charged_bytes"], "forest_stage_charge")
    rows = connection.execute("SELECT * FROM physical_custody_files WHERE batch_id=? ORDER BY ordinal", (batch["batch_id"],))
    columns = [c[0] for c in rows.description]
    entries = []
    for raw in rows:
        entry = dict(zip(columns, raw))
        require(entry.pop("state") == "present", "forest_stage_slots")
        entry.pop("batch_id")
        entries.append(entry)
    require(entries == inventory["initial_files"], "forest_stage_slots")
    stage_files = {entry["role"]: entry for entry in entries if entry["role"] in ("dataset_copy", "result_copy")}
    require(set(stage_files) == {"dataset_copy", "result_copy"}, "forest_stage_slots")
    total = 0
    for target in values:
        fields(target, "kind artifact_id storage_key bytes sha256")
        kind = target["kind"]
        require(kind in ("dataset", "result") and kind not in kinds, "forest_target_kind")
        kinds.add(kind)
        identifier, lane = (child, "datasets") if kind == "dataset" else (job, "results")
        require(target["artifact_id"] == identifier and target["storage_key"] == f"derived/{owner}/{project}/{lane}/{identifier}.json", "forest_target_identity")
        integer(target["bytes"], 1, 64*M if kind == "result" or control["method_id"] == TRANSFORM else 16*M)
        sha(target["sha256"])
        entry = stage_files[kind + "_copy"]
        require((entry["artifact_id"], entry["actual_bytes"], entry["actual_sha256"]) ==
                (identifier, target["bytes"], target["sha256"]), "forest_target_stage")
        total += target["bytes"]
    require(total <= control["permanent_reservation_bytes"], "forest_target_capacity")


def reserve_child_intent(connection, *, owner_id, project_id, parent_dataset_id,
                         parent_dataset_sha256, job_id, stage_id, child_dataset_id,
                         intent_id, created_us, targets, failure_cut=None):
    """Allocate one monotonic ordinal and durable preparation, never publish.

    Own transaction only, rollback-journal candidate only. No file/CPU/native
    proof is manufactured by SQL metadata or this return value.
    """
    if not isinstance(connection, sqlite3.Connection) or connection.in_transaction:
        raise ValueError("forest_requires_outside_transaction")
    for value in (owner_id, project_id, parent_dataset_id, job_id, stage_id, child_dataset_id, intent_id):
        uuid(value)
    sha(parent_dataset_sha256)
    integer(created_us)
    require(connection.execute("PRAGMA foreign_keys").fetchone() == (1,), "forest_foreign_keys_required")
    require(connection.execute("PRAGMA journal_mode").fetchone()[0] in ("delete", "memory"), "forest_native_wal_not_admitted")
    connection.execute("BEGIN IMMEDIATE")
    try:
        require(connection.execute("SELECT version_num FROM alembic_version").fetchone() == (REVISION,)
                and ddl_sha256(connection) == SUCCESSOR_DDL, "forest_schema_binding")
        parent = _row(connection, "SELECT * FROM observation_datasets WHERE id=? AND owner_id=? AND project_id=?", (parent_dataset_id, owner_id, project_id))
        require(parent["sha256"] == parent_dataset_sha256, "forest_stale_parent")
        _parent_chain(connection, parent, owner_id, project_id)
        job = _row(connection, "SELECT * FROM processing_jobs WHERE id=? AND owner_id=? AND project_id=?", (job_id, owner_id, project_id))
        require(job["state"] == "running" and job["cancel_requested"] == 0 and job["physical_fingerprint"] is not None
                and (job["dataset_id"], job["dataset_sha256"]) == (parent_dataset_id, parent_dataset_sha256), "forest_job_not_publishable")
        control = _row(connection, "SELECT * FROM physical_job_controls WHERE job_id=?", (job_id,))
        require((control["owner_id"], control["project_id"], control["dataset_id"], control["dataset_sha256"], control["root_dataset_id"], control["raw_asset_id"], control["stage_id"], control["request_sha256"], control["method_id"]) ==
                (owner_id, project_id, parent_dataset_id, parent_dataset_sha256, parent["root_dataset_id"], parent["raw_asset_id"], stage_id, job["request_sha256"], job["method_id"]), "forest_control_identity")
        raw = _row(connection, "SELECT * FROM raw_assets WHERE id=? AND owner_id=? AND project_id=?", (parent["raw_asset_id"], owner_id, project_id))
        require((control["raw_sha256"], control["raw_bytes"]) == (raw["sha256"], raw["byte_count"])
                and parent["raw_sha256"] == raw["sha256"], "forest_raw_identity")
        require(control["method_id"] in (CORRECTION, TRANSFORM) and control["permanent_reservation_bytes"] == (80*M if control["method_id"] == CORRECTION else 128*M), "forest_permanent_reservation")
        if control["method_id"] == TRANSFORM:
            require(parent["payload_schema"] == "gravity-station-adapter-result-1", "forest_transform_parent")
        _targets(connection, control, targets, child_dataset_id, job_id, owner_id, project_id)
        family = _row(connection, "SELECT * FROM physical_dataset_families WHERE root_dataset_id=?", (parent["root_dataset_id"],))
        require(family["state"] == "published" and family["published_count"] + family["reserved_count"] < 64
                and family["next_ordinal"] < J and parent["version"] < family["next_ordinal"], "forest_capacity_or_ordinal")
        require(family["published_count"] == connection.execute("SELECT count(*) FROM observation_datasets WHERE root_dataset_id=?", (parent["root_dataset_id"],)).fetchone()[0]
                and family["reserved_count"] == connection.execute("SELECT count(*) FROM physical_publication_intents WHERE root_dataset_id=?", (parent["root_dataset_id"],)).fetchone()[0], "forest_allocator_counts")
        ordinal = family["next_ordinal"]
        connection.execute("UPDATE physical_dataset_families SET next_ordinal=next_ordinal+1,reserved_count=reserved_count+1 WHERE root_dataset_id=?", (parent["root_dataset_id"],))
        if failure_cut is not None:
            failure_cut()
        columns = "intent_id kind owner_id project_id raw_asset_id root_dataset_id child_dataset_id stage_id parser_version ordinal job_id parent_dataset_id parent_dataset_sha256 request_sha256 permanent_reservation_bytes phase created_us".split()
        values = (intent_id, "job", owner_id, project_id, parent["raw_asset_id"], parent["root_dataset_id"], child_dataset_id,
                  stage_id, parent["parser_version"], ordinal, job_id, parent_dataset_id, parent_dataset_sha256,
                  job["request_sha256"], 0, "prepared", created_us)
        connection.execute(f"INSERT INTO physical_publication_intents ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})", values)
        for target in targets:
            connection.execute("INSERT INTO physical_publication_targets(intent_id,kind,artifact_id,storage_key,bytes,sha256) VALUES (?,?,?,?,?,?)",
                               (intent_id, target["kind"], target["artifact_id"], target["storage_key"], target["bytes"], target["sha256"]))
        connection.commit()
        return ordinal
    except BaseException:
        connection.rollback()
        raise
