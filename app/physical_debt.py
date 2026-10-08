"""Transactional custody retirement for the post-waveform physical ledger.

This module is the SQL part of publication, not a native admission receipt.
Its caller must hold the writer lease, drain the child and measure the complete
stage and installed targets before entering it. Uncertain inventory is retained.
No failed or cancelled operation is allowed to acquire a scientific child.
"""

import sqlite3

from app.physical_contract import (
    byte_sha, canonical, fields, integer, parse_record, require, uuid,
    validate_custody,
)
from app.physical_forest import SUCCESSOR_DDL, _row, _targets
from app.physical_persistence import CORRECTION, TRANSFORM, M
from app.physical_successor import REVISION, ddl_sha256
from app.physical_current_custody import parse_current_custody, validate_current_custody


METRICS = "wall_ms cpu_ms peak_rss_bytes scratch_bytes"
ERRORS = {
    "physical_cancelled": "Physical processing was cancelled",
    "physical_child_interrupted": "Physical child did not complete",
    "physical_wall_limit": "Physical child exceeded its wall limit",
    "physical_cpu_limit": "Physical child exceeded its CPU limit",
    "physical_memory_limit": "Physical child exceeded its memory limit",
    "physical_scratch_limit": "Physical child exceeded its scratch limit",
    "physical_execution_failed": "Physical child failed",
    "physical_publication_abandoned": "Uncommitted physical publication was abandoned",
}


def begin_ledger(connection):
    """Own an explicit transaction; never commit another caller's transaction."""
    require(isinstance(connection, sqlite3.Connection) and not connection.in_transaction,
            "physical_requires_outside_transaction")
    require(connection.execute("PRAGMA foreign_keys").fetchone() == (1,), "physical_foreign_keys")
    require(connection.execute("PRAGMA journal_mode").fetchone()[0] in ("delete", "memory"),
            "physical_native_wal_not_admitted")
    connection.execute("BEGIN IMMEDIATE")
    try:
        require(connection.execute("SELECT version_num FROM alembic_version").fetchone() == (REVISION,)
                and ddl_sha256(connection) == SUCCESSOR_DDL, "physical_schema_binding")
    except BaseException:
        connection.rollback()
        raise


def sealed_stage(connection, control):
    """Check every immutable inventory header, slot, hash and literal charge."""
    batch = _row(connection, "SELECT * FROM physical_custody_batches WHERE stage_id=?", (control["stage_id"],))
    require(batch["origin_kind"] == "job_stage" and batch["state"] == "sealed", "physical_stage_unsealed")
    body = batch["inventory_bytes"]
    require(type(body) is bytes and byte_sha(body) == batch["inventory_sha256"], "physical_inventory_hash")
    inventory = parse_record([body])
    measured = validate_custody(inventory)
    require(not inventory["removed_ordinals"], "physical_stage_removed")
    require(all(inventory[key] == batch[key] for key in inventory
                if key not in ("schema", "initial_files", "removed_ordinals")), "physical_inventory_header")
    require((batch["owner_id"], batch["project_id"], batch["raw_asset_id"], batch["raw_sha256"],
             batch["raw_bytes"], batch["method_id"], batch["stage_id"]) ==
            tuple(control[key] for key in ("owner_id", "project_id", "raw_asset_id", "raw_sha256",
                                          "raw_bytes", "method_id", "stage_id")), "physical_stage_control")
    require(control["stage_id"] == control["job_id"], "physical_stage_job_identity")
    require(measured["retained_bytes"] == batch["charged_bytes"], "physical_stage_charge")
    cursor = connection.execute("SELECT * FROM physical_custody_files WHERE batch_id=? ORDER BY ordinal", (batch["batch_id"],))
    names = [c[0] for c in cursor.description]
    slots = []
    for values in cursor:
        slot = dict(zip(names, values))
        require(slot.pop("state") == "present", "physical_stage_slot_state")
        slot.pop("batch_id")
        slots.append(slot)
    require(slots == inventory["initial_files"], "physical_stage_slots")
    return batch, inventory


def _installed(connection, intent, values):
    require(type(values) is list and len(values) <= 2, "physical_installed_set")
    cursor = connection.execute("SELECT kind,artifact_id,storage_key,bytes,sha256 FROM physical_publication_targets WHERE intent_id=? ORDER BY kind", (intent["intent_id"],))
    targets = {row[0]: dict(zip((c[0] for c in cursor.description), row)) for row in cursor}
    require(set(targets) == {"dataset", "result"}, "physical_dual_targets")
    seen = set()
    for value in values:
        fields(value, "kind artifact_id storage_key bytes sha256")
        require(value["kind"] in targets and value["kind"] not in seen
                and value == targets[value["kind"]], "physical_installed_identity")
        seen.add(value["kind"])
    require((targets["dataset"]["artifact_id"], targets["result"]["artifact_id"]) ==
            (intent["child_dataset_id"], intent["job_id"]), "physical_target_artifact")
    return targets


def _abandon_targets(connection, control, intent, installed, batch_id, now_us):
    targets = _installed(connection, intent, installed)
    _targets(connection, control, list(targets.values()), intent["child_dataset_id"], intent["job_id"],
             control["owner_id"], control["project_id"])
    if not installed:
        return
    uuid(batch_id)
    files = [dict(ordinal=i, role=value["kind"] + "_copy", location="pending_target",
                  artifact_id=value["artifact_id"], leaf=value["storage_key"],
                  max_bytes=64*M if value["kind"] == "result" or control["method_id"] == TRANSFORM else 16*M,
                  actual_bytes=value["bytes"], actual_sha256=value["sha256"])
             for i, value in enumerate(sorted(installed, key=lambda v: v["kind"]), 1)]
    inventory = dict(schema="geophysics.physical-custody/v1", batch_id=batch_id,
                     owner_id=control["owner_id"], project_id=control["project_id"],
                     origin_kind="publication_abandon", origin_id=intent["intent_id"],
                     stage_id=None, deletion_receipt_id=None, raw_asset_id=control["raw_asset_id"],
                     raw_sha256=control["raw_sha256"], raw_bytes=control["raw_bytes"],
                     parser_version="gravity-stations-json/v1", method_id=control["method_id"],
                     capacity_bytes=80*M if control["method_id"] == CORRECTION else 128*M,
                     initial_files=files, removed_ordinals=[])
    charge = validate_custody(inventory)["retained_bytes"]
    body = canonical(inventory)
    header = {k: v for k, v in inventory.items() if k not in ("schema", "initial_files", "removed_ordinals")}
    header.update(state="cleanup_pending", charged_bytes=charge, inventory_bytes=body,
                  inventory_sha256=byte_sha(body), created_us=now_us, sealed_us=now_us, removed_us=None)
    names = list(header)
    connection.execute(f"INSERT INTO physical_custody_batches({','.join(names)}) VALUES ({','.join('?' for _ in names)})", tuple(header.values()))
    for slot in files:
        slot = dict(slot, batch_id=batch_id, state="present")
        connection.execute(f"INSERT INTO physical_custody_files({','.join(slot)}) VALUES ({','.join('?' for _ in slot)})", tuple(slot.values()))


def retire_failed_job(connection, *, owner_id, project_id, job_id, state, error_code,
                      metrics, finished_at, finished_us, installed_targets,
                      abandon_batch_id=None, failure_cut=None):
    """Co-commit nonsuccess, retained copies and reservation/intent retirement.

    ``installed_targets`` is the complete measured installed subset, not an
    adoption request. Full native inventory must precede this SQL operation.
    Exceptions leave all SQL reservations in place; no file is removed here.
    """
    for value in (owner_id, project_id, job_id):
        uuid(value)
    require(state in ("failed", "cancelled") and error_code in ERRORS, "physical_terminal_error")
    require((state == "cancelled") == (error_code == "physical_cancelled"), "physical_terminal_error")
    fields(metrics, METRICS)
    for value in metrics.values():
        integer(value)
    integer(finished_us)
    from app.physical_contract import instant
    instant(finished_at, legacy=True)
    begin_ledger(connection)
    try:
        job = _row(connection, "SELECT * FROM processing_jobs WHERE id=? AND owner_id=? AND project_id=?", (job_id, owner_id, project_id))
        require(job["state"] == "running" and job["result_sha256"] is None and job["result_key"] is None
                and job["result_bytes"] is None,
                "physical_job_terminal_conflict")
        control = _row(connection, "SELECT * FROM physical_job_controls WHERE job_id=?", (job_id,))
        require((control["owner_id"], control["project_id"], control["dataset_id"], control["dataset_sha256"],
                 control["method_id"], control["request_sha256"]) ==
                (owner_id, project_id, job["dataset_id"], job["dataset_sha256"], job["method_id"], job["request_sha256"]),
                "physical_control_binding")
        require(control["permanent_reservation_bytes"] == (80*M if control["method_id"] == CORRECTION else 128*M),
                "physical_permanent_reservation")
        require(not connection.execute("SELECT 1 FROM physical_dataset_productions WHERE job_id=?", (job_id,)).fetchone(),
                "physical_terminal_has_production")
        batch, _ = sealed_stage(connection, control)
        intent_cursor = connection.execute("SELECT intent_id FROM physical_publication_intents WHERE job_id=?", (job_id,))
        intent_rows = intent_cursor.fetchall()
        require(len(intent_rows) <= 1, "physical_intent_count")
        if intent_rows:
            intent = _row(connection, "SELECT * FROM physical_publication_intents WHERE intent_id=?", intent_rows[0])
            require((intent["owner_id"], intent["project_id"], intent["stage_id"], intent["parent_dataset_id"],
                     intent["parent_dataset_sha256"], intent["request_sha256"], intent["root_dataset_id"]) ==
                    (owner_id, project_id, control["stage_id"], job["dataset_id"], job["dataset_sha256"],
                     job["request_sha256"], control["root_dataset_id"]), "physical_intent_binding")
            require(not connection.execute("SELECT 1 FROM observation_datasets WHERE id=?", (intent["child_dataset_id"],)).fetchone(),
                    "physical_terminal_has_child")
            _abandon_targets(connection, control, intent, installed_targets, abandon_batch_id, finished_us)
        else:
            require(installed_targets == [], "physical_installed_without_intent")
        connection.execute("UPDATE physical_custody_batches SET state='cleanup_pending' WHERE batch_id=?", (batch["batch_id"],))
        if failure_cut:
            failure_cut("debt")
        connection.execute("UPDATE processing_jobs SET state=?,finished_at=?,wall_ms=?,physical_cpu_ms=?,peak_rss_bytes=?,scratch_bytes=?,error_code=?,error_message=? WHERE id=?",
                           (state, finished_at, metrics["wall_ms"], metrics["cpu_ms"], metrics["peak_rss_bytes"], metrics["scratch_bytes"],
                            error_code, ERRORS[error_code], job_id))
        connection.execute("UPDATE physical_job_controls SET permanent_reservation_bytes=0 WHERE job_id=?", (job_id,))
        if intent_rows:
            family = _row(connection, "SELECT * FROM physical_dataset_families WHERE root_dataset_id=?", (control["root_dataset_id"],))
            require(family["reserved_count"] >= 1 and family["reserved_count"] ==
                    connection.execute("SELECT count(*) FROM physical_publication_intents WHERE root_dataset_id=?", (control["root_dataset_id"],)).fetchone()[0]
                    and family["published_count"] == connection.execute("SELECT count(*) FROM observation_datasets WHERE root_dataset_id=?", (control["root_dataset_id"],)).fetchone()[0],
                    "physical_reserved_count")
            connection.execute("DELETE FROM physical_publication_targets WHERE intent_id=?", (intent["intent_id"],))
            connection.execute("DELETE FROM physical_publication_intents WHERE intent_id=?", (intent["intent_id"],))
            connection.execute("UPDATE physical_dataset_families SET reserved_count=reserved_count-1 WHERE root_dataset_id=?", (control["root_dataset_id"],))
        if failure_cut:
            failure_cut("terminal")
        require(not connection.execute("PRAGMA foreign_key_check").fetchall(), "physical_foreign_key_check")
        connection.commit()
    except BaseException:
        connection.rollback()
        raise


def cleanup_custody_file(connection, files, *, owner_id, batch_id, ordinal, removed_us, failure_cut=None):
    """Acknowledge only a verified unlink AND successful directory sync.

    Native uncertainty or a failed SQL commit leaves conservative charge. A
    later absent pathname is not sufficient to retry/acknowledge this operation.
    Cleanup requires the caller's full fresh audit and exclusive writer lease.
    """
    from app.physical_posix import PrivateFiles
    require(isinstance(files, PrivateFiles), "physical_native_files_required")
    uuid(owner_id)
    uuid(batch_id)
    integer(ordinal, 1, 4096)
    integer(removed_us)
    begin_ledger(connection)
    try:
        batch = _row(connection, "SELECT * FROM physical_custody_batches WHERE batch_id=? AND owner_id=?", (batch_id, owner_id))
        require(batch["state"] == "cleanup_pending", "physical_cleanup_state")
        body = batch["inventory_bytes"]
        require(type(body) is bytes and byte_sha(body) == batch["inventory_sha256"], "physical_inventory_hash")
        inventory = parse_current_custody([body])
        measured = validate_current_custody(inventory)
        require(all(inventory[key] == batch[key] for key in inventory
                    if key not in ("schema", "initial_files", "removed_ordinals")), "physical_inventory_header")
        require(measured["retained_bytes"] == batch["charged_bytes"], "physical_cleanup_charge")
        cursor = connection.execute("SELECT * FROM physical_custody_files WHERE batch_id=? ORDER BY ordinal", (batch_id,))
        names = [c[0] for c in cursor.description]
        slots, removed = [], []
        for values in cursor:
            slot = dict(zip(names, values))
            state = slot.pop("state")
            require(state in ("present", "removed"), "physical_cleanup_slot_state")
            if state == "removed":
                removed.append(slot["ordinal"])
            slot.pop("batch_id")
            slots.append(slot)
        require(slots == inventory["initial_files"] and removed == inventory["removed_ordinals"], "physical_cleanup_slots")
        selected = [slot for slot in slots if slot["ordinal"] == ordinal]
        require(len(selected) == 1 and ordinal not in removed, "physical_cleanup_ordinal")
        slot = selected[0]
        location = slot["location"]
        if location == "stage":
            key = f".job-staging/{batch['stage_id']}/{slot['leaf']}"
            directory = f".job-staging/{batch['stage_id']}"
            files.verify_directory(directory, expected_files=[s["leaf"] for s in slots if s["ordinal"] not in removed])
        elif location == "pending_target":
            key = slot["leaf"]
        elif location == "deleting_raw":
            key = f".deleting/{owner_id}--{batch['project_id']}/{slot['leaf']}"
        else:
            require(location == "deleting_derived", "physical_cleanup_location")
            key = f".deleting/{owner_id}--{batch['project_id']}--derived/{slot['leaf']}"
        files.remove(key, cap=slot["max_bytes"], expected_bytes=slot["actual_bytes"],
                     expected_sha256=slot["actual_sha256"], failure_cut=failure_cut)
        if location == "stage":
            files.verify_directory(directory, expected_files=[s["leaf"] for s in slots
                                                              if s["ordinal"] not in [*removed, ordinal]])
        if failure_cut:
            failure_cut("before_sql_acknowledgement")
        inventory["removed_ordinals"] = sorted([*removed, ordinal])
        charge = validate_current_custody(inventory)["retained_bytes"]
        body = canonical(inventory)
        complete = len(inventory["removed_ordinals"]) == len(slots)
        connection.execute("UPDATE physical_custody_files SET state='removed' WHERE batch_id=? AND ordinal=?", (batch_id, ordinal))
        connection.execute("UPDATE physical_custody_batches SET inventory_bytes=?,inventory_sha256=?,charged_bytes=?,state=?,removed_us=? WHERE batch_id=?",
                           (body, byte_sha(body), charge, "removed" if complete else "cleanup_pending", removed_us if complete else None, batch_id))
        if failure_cut:
            failure_cut("sql_acknowledgement")
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
