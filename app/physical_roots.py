"""Intent-backed immutable physical root publication, with retained stage debt.

The root is structurally admitted only; no HTTP/publication numerical solver.
The SQL lane stays isolated until the independently reviewed native runtime is
wired by integration. Files are read/installed under the caller's writer lease.
"""

from app.physical_contract import byte_sha, canonical, integer, parse_record, require, uuid, validate_custody
from app.physical_debt import begin_ledger
from app.physical_forest import _row
from app.physical_persistence import M
from app.physical_wire import SOURCE_KEYS, parse_root, root_envelope, scientific_digest


def _stage(connection, files, owner, project, raw, root):
    batch = _row(connection, "SELECT * FROM physical_custody_batches WHERE stage_id=? AND owner_id=? AND project_id=?", (root, owner, project))
    require(batch["origin_kind"] == "root_stage" and batch["state"] == "sealed"
            and batch["origin_id"] == root and batch["method_id"] is None, "physical_root_stage")
    body = batch["inventory_bytes"]
    require(type(body) is bytes and byte_sha(body) == batch["inventory_sha256"], "physical_root_inventory")
    inv = parse_record([body])
    require(not inv["removed_ordinals"] and all(inv[k] == batch[k] for k in inv
            if k not in ("schema", "initial_files", "removed_ordinals")), "physical_root_inventory")
    require(validate_custody(inv)["retained_bytes"] == batch["charged_bytes"], "physical_root_stage_charge")
    require((batch["raw_asset_id"], batch["raw_sha256"], batch["raw_bytes"], batch["parser_version"]) ==
            (raw["id"], raw["sha256"], raw["byte_count"], "gravity-stations-json/v1"), "physical_root_raw_binding")
    cursor = connection.execute("SELECT * FROM physical_custody_files WHERE batch_id=? ORDER BY ordinal", (batch["batch_id"],))
    names = [c[0] for c in cursor.description]
    slots, roles = [], {}
    for values in cursor:
        slot = dict(zip(names, values))
        require(slot.pop("state") == "present", "physical_root_slot_state")
        slot.pop("batch_id")
        require(slot["role"] not in roles, "physical_root_duplicate_role")
        roles[slot["role"]] = slot
        slots.append(slot)
    require(slots == inv["initial_files"] and {"input_spool", "dataset_copy"} <= set(roles), "physical_root_slots")
    files.verify_directory(f".job-staging/{root}", expected_files=[slot["leaf"] for slot in slots])
    for slot in slots:
        files.read(f".job-staging/{root}/{slot['leaf']}", cap=slot["max_bytes"],
                   expected_bytes=slot["actual_bytes"], expected_sha256=slot["actual_sha256"])
    require(roles["dataset_copy"]["artifact_id"] == root, "physical_root_copy_id")
    require((roles["input_spool"]["actual_bytes"], roles["input_spool"]["actual_sha256"]) ==
            (raw["byte_count"], raw["sha256"]), "physical_root_original_bytes")
    return batch, roles


def _verified(connection, files, owner, project, raw_id, root):
    raw = _row(connection, "SELECT * FROM raw_assets WHERE id=? AND owner_id=? AND project_id=?", (raw_id, owner, project))
    source = _row(connection, "SELECT * FROM source_records WHERE id=? AND owner_id=? AND project_id=?", (raw["source_id"], owner, project))
    require(_row(connection, "SELECT owner_id FROM projects WHERE id=?", (project,))["owner_id"] == owner, "physical_root_owner")
    require(raw["detected_format"] == source["declared_format"] == "gravity_stations_json"
            and raw["validation_status"] == "raw_metadata_checked"
            and source["private_storage_permission"] == "attested" and source["rights_decision"] == "mirror"
            and source["sha256"] == raw["sha256"] and source["expected_bytes"] in (None, raw["byte_count"]), "physical_root_source")
    integer(raw["byte_count"], 1, 16*M)
    key = f"projects/{owner}/{project}/{raw_id}"
    require(raw["storage_key"] == key, "physical_root_raw_key")
    original = files.read(key, cap=16*M, expected_bytes=raw["byte_count"], expected_sha256=raw["sha256"])
    scientific = parse_root([original])
    batch, roles = _stage(connection, files, owner, project, raw, root)
    slot = roles["dataset_copy"]
    body = files.read(f".job-staging/{root}/dataset.json", cap=16*M,
                      expected_bytes=slot["actual_bytes"], expected_sha256=slot["actual_sha256"])
    envelope = root_envelope([body])
    require(canonical(envelope) == body, "physical_root_envelope_canonical")
    require((envelope["dataset_id"], envelope["owner_id"], envelope["project_id"], envelope["raw_asset_id"],
             envelope["raw_sha256"], envelope["raw_bytes"]) ==
            (root, owner, project, raw_id, raw["sha256"], raw["byte_count"]), "physical_root_envelope_binding")
    require(scientific_digest(envelope["payload"]) == scientific_digest(scientific)
            and canonical(envelope["payload"], scientific=True) == canonical(scientific, scientific=True), "physical_root_payload_changed")
    require(envelope["source"] == {key: source[key] for key in SOURCE_KEYS.split()}, "physical_root_source_changed")
    return raw, batch, body, envelope


def prepare_root(connection, files, *, owner_id, project_id, raw_asset_id, root_dataset_id, intent_id, created_us, failure_cut=None):
    for value in (owner_id, project_id, raw_asset_id, root_dataset_id, intent_id):
        uuid(value)
    integer(created_us)
    begin_ledger(connection)
    try:
        _, _, body, _ = _verified(connection, files, owner_id, project_id, raw_asset_id, root_dataset_id)
        from app.physical_accounting import account_private_charge
        require(account_private_charge(connection, owner_id)["total"] + 16*M <= 1024*M, "physical_account_quota")
        require(not connection.execute("SELECT 1 FROM physical_dataset_families WHERE raw_asset_id=? AND parser_version='gravity-stations-json/v1'", (raw_asset_id,)).fetchone(),
                "physical_root_already_reserved")
        connection.execute("INSERT INTO physical_dataset_families(root_dataset_id,owner_id,project_id,raw_asset_id,parser_version,state,next_ordinal,published_count,reserved_count,created_us) VALUES(?,?,?,?,'gravity-stations-json/v1','pending',2,0,1,?)",
                           (root_dataset_id, owner_id, project_id, raw_asset_id, created_us))
        connection.execute("INSERT INTO physical_publication_intents(intent_id,kind,owner_id,project_id,raw_asset_id,root_dataset_id,child_dataset_id,stage_id,parser_version,ordinal,job_id,parent_dataset_id,parent_dataset_sha256,request_sha256,permanent_reservation_bytes,phase,created_us) VALUES(?,'root',?,?,?,?,?,?,'gravity-stations-json/v1',1,NULL,NULL,NULL,NULL,?,'prepared',?)",
                           (intent_id, owner_id, project_id, raw_asset_id, root_dataset_id, root_dataset_id, root_dataset_id, 16*M, created_us))
        connection.execute("INSERT INTO physical_publication_targets(intent_id,kind,artifact_id,storage_key,bytes,sha256) VALUES(?,'dataset',?,?,?,?)",
                           (intent_id, root_dataset_id, f"derived/{owner_id}/{project_id}/datasets/{root_dataset_id}.json", len(body), byte_sha(body)))
        if failure_cut:
            failure_cut("prepared")
        connection.commit()
    except BaseException:
        connection.rollback()
        raise


def publish_root(connection, files, *, owner_id, project_id, intent_id, created_at, failure_cut=None):
    from app.physical_contract import instant
    for value in (owner_id, project_id, intent_id):
        uuid(value)
    instant(created_at, legacy=True)
    begin_ledger(connection)
    try:
        intent = _row(connection, "SELECT * FROM physical_publication_intents WHERE intent_id=? AND owner_id=? AND project_id=?", (intent_id, owner_id, project_id))
        require(intent["kind"] == "root" and intent["phase"] == "prepared" and intent["ordinal"] == 1,
                "physical_root_intent")
        root = intent["root_dataset_id"]
        require(intent["child_dataset_id"] == intent["stage_id"] == root
                and intent["permanent_reservation_bytes"] == 16*M, "physical_root_intent_binding")
        raw, batch, body, envelope = _verified(connection, files, owner_id, project_id, intent["raw_asset_id"], root)
        target = _row(connection, "SELECT * FROM physical_publication_targets WHERE intent_id=?", (intent_id,))
        require((target["kind"], target["artifact_id"], target["storage_key"], target["bytes"], target["sha256"]) ==
                ("dataset", root, f"derived/{owner_id}/{project_id}/datasets/{root}.json", len(body), byte_sha(body)), "physical_root_target")
        require(files.read(target["storage_key"], cap=16*M, expected_bytes=len(body), expected_sha256=byte_sha(body)) == body,
                "physical_root_installed_copy")
        family = _row(connection, "SELECT * FROM physical_dataset_families WHERE root_dataset_id=?", (root,))
        require((family["owner_id"], family["project_id"], family["raw_asset_id"], family["parser_version"],
                 family["state"], family["next_ordinal"], family["published_count"], family["reserved_count"]) ==
                (owner_id, project_id, raw["id"], "gravity-stations-json/v1", "pending", 2, 0, 1), "physical_root_family")
        # All original legacy columns remain literal, no row/data defaults.
        connection.execute("INSERT INTO observation_datasets(id,project_id,owner_id,raw_asset_id,version,parser_version,modality,row_count,raw_sha256,sha256,byte_count,storage_key,created_at,kind,root_dataset_id,parent_dataset_id,payload_schema) VALUES(?,?,?,?,1,'gravity-stations-json/v1','gravity_physical_station',?,?,?,?,?,?,'root',?,NULL,'gravity-stations-1')",
                           (root, project_id, owner_id, raw["id"], len(envelope["payload"]["stations"]), raw["sha256"], byte_sha(body), len(body), target["storage_key"], created_at, root))
        connection.execute("UPDATE physical_custody_batches SET state='cleanup_pending' WHERE batch_id=?", (batch["batch_id"],))
        connection.execute("UPDATE physical_dataset_families SET state='published',published_count=1,reserved_count=0 WHERE root_dataset_id=?", (root,))
        if failure_cut:
            failure_cut("published")
        connection.execute("DELETE FROM physical_publication_targets WHERE intent_id=?", (intent_id,))
        connection.execute("DELETE FROM physical_publication_intents WHERE intent_id=?", (intent_id,))
        require(not connection.execute("PRAGMA foreign_key_check").fetchall(), "physical_root_foreign_keys")
        connection.commit()
        return root
    except BaseException:
        connection.rollback()
        raise
