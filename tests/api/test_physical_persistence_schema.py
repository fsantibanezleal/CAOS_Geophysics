"""Isolated rollback-journal candidate; never the default migration registry."""

from __future__ import annotations

import hashlib
import shutil
import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

from app.physical_persistence import TABLES


ROOT = Path(__file__).resolve().parents[2]
OLD = "0003_processing_jobs"
NEW = "0004_physical_persistence"


@pytest.fixture
def candidate(tmp_path, monkeypatch):
    versions = tmp_path / "candidate-registry"
    versions.mkdir()
    originals = {}
    for path in sorted((ROOT / "app/migrations/versions").glob("*.py")):
        originals[path] = path.read_bytes()
        shutil.copyfile(path, versions / path.name)
    migration = ROOT / "app/migrations/candidates/0004_physical_persistence.py"
    shutil.copyfile(migration, versions / migration.name)
    config = Config(str(ROOT / "app/alembic.ini"))
    config.set_main_option("version_locations", str(versions))
    config.attributes["physical_candidate_only"] = True
    database = tmp_path / "private-candidate.sqlite3"
    monkeypatch.setenv("GEOPHYSICS_DB_PATH", str(database))
    command.upgrade(config, OLD)
    with sqlite3.connect(database) as db:
        assert db.execute("PRAGMA journal_mode").fetchone() == ("delete",)
    yield config, database, tmp_path
    assert all(path.read_bytes() == body for path, body in originals.items())
    assert not database.with_name(database.name + "-wal").exists()


def seed(db, *, parser="gravity-station-csv/v1", modality="gravity_station"):
    owner, project, source, raw, dataset, job = [str(uuid4()) for _ in range(6)]
    time = "2026-09-27 12:00:00.123456"
    native = ' {"epsilon":1.0,"label":"Señal", "nested":null} '
    db.execute("INSERT INTO user VALUES (?,?,?,1,0,1)", (owner, owner + "@example.org", "fixture-hash"))
    db.execute("INSERT INTO projects VALUES (?,?,?,?,?,?)", (project, owner, "Survey", "", time, time))
    db.execute(
        "INSERT INTO source_records(id,project_id,owner_id,original_filename,version,provider,retrieved_at,"
        "rights_statement,rights_decision,declared_format,sha256,attribution) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (source, project, owner, "legacy.csv", 1, "fixture", time, "original", "mirror", "gravity_csv", "a"*64, "fixture"),
    )
    db.execute(
        "INSERT INTO raw_assets VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (raw, project, owner, source, "legacy.csv", "text/csv", "gravity_csv", 7, "a"*64,
         f"projects/{owner}/{project}/{raw}", native, "valid", time),
    )
    db.execute("INSERT INTO observation_datasets VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (
        dataset, project, owner, raw, 1, parser, modality, 2, "a"*64, "b"*64, 9,
        f"derived/{owner}/{project}/datasets/{dataset}.json", time,
    ))
    db.execute(
        "INSERT INTO processing_jobs(id,project_id,owner_id,dataset_id,dataset_sha256,method_id,request_json,"
        "request_sha256,preflight,state,cancel_requested,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (job, project, owner, dataset, "b"*64, "gravity.station-outlier-flags/v1", native, "c"*64, native, "failed", 0, time),
    )
    db.execute("INSERT INTO account_usage VALUES (?,?)", (owner, 7))
    db.execute("INSERT INTO deletion_receipts VALUES (?,?,?,?,?,?,?,?)", (
        str(uuid4()), str(uuid4()), owner, time, ' ["' + "d"*64 + '"] ', "external_pending", None, None,
    ))
    db.commit()
    return owner, project, raw, dataset, job


def inventory(db):
    tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name<>'alembic_version'")]
    result = {}
    for table in tables:
        cols = [r[1] for r in db.execute(f'PRAGMA table_info("{table}")')]
        projection = ",".join(f'"{c}",typeof("{c}")' for c in cols)
        result[table] = (cols, list(db.execute(f'SELECT {projection} FROM "{table}" ORDER BY 1')))
    return result


def upgraded(candidate, *, parser="gravity-station-csv/v1", modality="gravity_station"):
    config, path, _ = candidate
    with sqlite3.connect(path) as db:
        ids = seed(db, parser=parser, modality=modality)
    command.upgrade(config, NEW)
    db = sqlite3.connect(path)
    db.execute("PRAGMA foreign_keys=ON")
    assert db.execute("PRAGMA journal_mode").fetchone() == ("delete",)
    return db, ids


def test_default_registry_and_metadata_remain_0003():
    assert ScriptDirectory.from_config(Config(str(ROOT / "app/alembic.ini"))).get_current_head() == OLD
    from app.database import MIGRATION_HEAD
    from app.models import Base
    assert MIGRATION_HEAD == OLD
    assert not any(name.startswith("physical_") for name in Base.metadata.tables)
    assert not (ROOT / "app/migrations/versions/0004_physical_persistence.py").exists()


@pytest.mark.parametrize("parser,modality", [
    ("gravity-station-csv/v1", "gravity_station"), ("edi-strict-envelope/v1", "edi_transfer_function"),
])
def test_preserves_all_original_values_types_native_json_times_and_file_bytes(candidate, parser, modality):
    config, path, scratch = candidate
    body = b"immutable original\x00\xff\n"
    artifact = scratch / "unchanged-original.bin"
    artifact.write_bytes(body)
    with sqlite3.connect(path) as db:
        ids = seed(db, parser=parser, modality=modality)
        before = inventory(db)
    command.upgrade(config, NEW)
    with sqlite3.connect(path) as db:
        for table, (cols, rows) in before.items():
            projection = ",".join(f'"{c}",typeof("{c}")' for c in cols)
            assert list(db.execute(f'SELECT {projection} FROM "{table}" ORDER BY 1')) == rows
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert db.execute("SELECT kind,root_dataset_id,parent_dataset_id,payload_schema FROM observation_datasets").fetchone() == (
            "root", ids[3], None, "geophysics.observation-dataset/v1",
        )
        assert db.execute("SELECT state,next_ordinal,published_count,reserved_count FROM physical_dataset_families").fetchone() == ("published", 2, 1, 0)
        for table in TABLES:
            if table != "physical_dataset_families":
                assert db.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone() == (0,)
        assert db.execute("SELECT physical_fingerprint,physical_cpu_ms FROM processing_jobs").fetchone() == (None, None)
    assert artifact.read_bytes() == body


def test_unknown_parser_refuses_without_partial_candidate_publication(candidate):
    config, path, _ = candidate
    with sqlite3.connect(path) as db:
        seed(db, parser="future-parser/v99")
        before = inventory(db)
    with pytest.raises(ValueError, match="unsupported_legacy_dataset"):
        command.upgrade(config, NEW)
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT version_num FROM alembic_version").fetchone() == (OLD,)
        assert inventory(db) == before


def test_active_legacy_job_refuses_candidate_before_ddl(candidate):
    config, path, _ = candidate
    with sqlite3.connect(path) as db:
        seed(db)
        db.execute("UPDATE processing_jobs SET state='running'")
        db.commit()
    with pytest.raises(ValueError, match="active_legacy_job"):
        command.upgrade(config, NEW)


@pytest.mark.parametrize("sql", [
    "ALTER TABLE projects ADD COLUMN unreviewed TEXT",
    "UPDATE processing_jobs SET method_id='future/v1'",
    "UPDATE processing_jobs SET state='future'",
    "UPDATE raw_assets SET detected_format='future'",
])
def test_unknown_legacy_schema_method_state_or_format_is_not_adopted(candidate, sql):
    config, path, _ = candidate
    with sqlite3.connect(path) as db:
        seed(db)
        db.execute(sql)
        db.commit()
        before = inventory(db)
    with pytest.raises(ValueError, match="unsupported_legacy"):
        command.upgrade(config, NEW)
    with sqlite3.connect(path) as db:
        assert inventory(db) == before
        assert db.execute("SELECT version_num FROM alembic_version").fetchone() == (OLD,)


def test_fk_failure_during_candidate_ddl_rolls_back_all_new_tables_columns_and_original_bytes(candidate):
    config, path, _ = candidate
    other = str(uuid4())
    with sqlite3.connect(path) as db:
        seed(db)
        db.execute("INSERT INTO user VALUES (?,?,?,1,0,1)", (other, "other@example.org", "fixture"))
        # Valid under old individual FKs, inconsistent under exact owned raw binding.
        db.execute("UPDATE observation_datasets SET owner_id=?", (other,))
        db.commit()
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        before = inventory(db)
        ddl_before = db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name").fetchall()
    with pytest.raises(ValueError, match="candidate_foreign_key_check_failed"):
        command.upgrade(config, NEW)
    with sqlite3.connect(path) as db:
        assert inventory(db) == before
        assert db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name").fetchall() == ddl_before
        assert db.execute("SELECT version_num FROM alembic_version").fetchone() == (OLD,)


def test_exact_named_constraints_composite_foreign_keys_and_no_debt_cascade(candidate):
    db, _ = upgraded(candidate)
    try:
        sql = dict(db.execute("SELECT name,sql FROM sqlite_master WHERE sql IS NOT NULL"))
        assert set(TABLES) <= set(sql)
        for table, spec in TABLES.items():
            assert [r[1] for r in db.execute(f'PRAGMA table_info("{table}")')] == [c.name for c in spec.columns]
            for name, _ in spec.checks:
                assert name in sql[table]
            for fk in db.execute(f'PRAGMA foreign_key_list("{table}")'):
                assert fk[5:7] == ("RESTRICT", "RESTRICT")
        assert "WHERE kind='root'" in sql["uq_dataset_root_parser"]
        assert "'queued','running','succeeded'" in sql["uq_jobs_physical_reuse"]
        assert {r[2] for r in db.execute("PRAGMA foreign_key_list(physical_custody_batches)")} == {"user"}
        assert {r[2] for r in db.execute("PRAGMA foreign_key_list(physical_deletion_extensions)")} == {"deletion_receipts"}
        assert len(db.execute("PRAGMA foreign_key_list(physical_job_controls)").fetchall()) == 13
    finally:
        db.close()


def test_derived_uses_same_parser_and_parent_binding_not_suffix(candidate):
    db, (owner, project, raw, root, _) = upgraded(candidate)
    try:
        child = str(uuid4())
        values = (child, project, owner, raw, 2, "gravity-station-csv/v1", "gravity_station", 2, "a"*64, "e"*64, 9,
                  f"derived/{owner}/{project}/datasets/{child}.json", "2026-10-03 01:00:00", "derived", root, root, "gravity-station-adapter-result-1")
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("INSERT INTO observation_datasets VALUES (" + ",".join("?"*17) + ")", values)
        assert db.execute("SELECT COUNT(*) FROM observation_datasets").fetchone() == (1,)
    finally:
        db.close()


@pytest.mark.parametrize("field,value", [("next_ordinal", 1), ("published_count", 65), ("reserved_count", -1), ("owner_id", str(uuid4()))])
def test_family_domain_capacity_and_foreign_owner_refuse(candidate, field, value):
    db, _ = upgraded(candidate)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(f'UPDATE physical_dataset_families SET "{field}"=?', (value,))
    finally:
        db.close()


def test_runtime_control_null_triplet_and_no_automatic_readiness(candidate):
    db, _ = upgraded(candidate)
    try:
        assert db.execute("SELECT COUNT(*) FROM physical_runtime_control").fetchone() == (0,)
        params = (1, str(uuid4()), str(uuid4()), 1, "closed", None, None, None)
        db.execute("INSERT INTO physical_runtime_control(singleton,deployment_id,storage_generation,lease_generation,inventory_state,source_policy_sha256,last_clean_inventory_sha256,audited_us) VALUES (?,?,?,?,?,?,?,?)", params)
        for change in ("inventory_state='clean'", "source_policy_sha256='" + "a"*64 + "'", "singleton=2"):
            with pytest.raises(sqlite3.IntegrityError):
                db.execute("UPDATE physical_runtime_control SET " + change)
    finally:
        db.close()


def test_candidate_digest_measured_with_original_ops_sqlite_master_domain(candidate):
    db, _ = upgraded(candidate)
    try:
        import json
        rows = db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type,name").fetchall()
        digest = hashlib.sha256(json.dumps(rows, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
        assert len(digest) == 64 and digest != "0"*64
        assert digest == "7496e07c6d4454a556e3b094b16ad458e06aa4cf57727e434dd7fb002fb59d86"
        print("CANDIDATE_DDL_SHA256=" + digest)
        print("CANDIDATE_DDL_OBJECTS=" + str(len(rows)))
    finally:
        db.close()


def batch(owner, project, raw, *, origin="root_stage", method=None):
    return dict(batch_id=str(uuid4()), owner_id=owner, project_id=project, origin_kind=origin,
                origin_id=str(uuid4()), stage_id=str(uuid4()), deletion_receipt_id=None, raw_asset_id=raw,
                raw_sha256="a"*64, raw_bytes=7, parser_version="gravity-stations-json/v1", method_id=method,
                state="reserved", capacity_bytes=32*1048576, charged_bytes=32*1048576, inventory_bytes=None,
                inventory_sha256=None, created_us=1, sealed_us=None, removed_us=None)


def insert(db, table, row):
    db.execute(f"INSERT INTO {table} ({','.join(row)}) VALUES ({','.join('?' for _ in row)})", tuple(row.values()))


@pytest.mark.parametrize("change", [
    {"capacity_bytes": 1}, {"charged_bytes": 0}, {"parser_version": None}, {"raw_sha256": None},
    {"origin_kind": "job_stage", "method_id": None}, {"method_id": "future/v1"},
    {"state": "removed"}, {"inventory_bytes": b"{}"}, {"sealed_us": 1}, {"stage_id": None},
])
def test_custody_origin_nulls_charges_states_and_capacities_refuse(candidate, change):
    db, (owner, project, raw, _, _) = upgraded(candidate)
    try:
        row = batch(owner, project, raw)
        row.update(change)
        with pytest.raises(sqlite3.IntegrityError):
            insert(db, "physical_custody_batches", row)
    finally:
        db.close()


def test_cleanup_debt_outlives_project_and_intent_but_blocks_owner_delete(candidate):
    db, (owner, project, raw, _, _) = upgraded(candidate)
    try:
        row = batch(owner, project, raw)
        insert(db, "physical_custody_batches", row)
        for table in ("processing_jobs", "observation_datasets", "physical_dataset_families", "raw_assets", "source_records", "projects"):
            db.execute(f"DELETE FROM {table}")
        assert db.execute("SELECT charged_bytes FROM physical_custody_batches").fetchone() == (32*1048576,)
        db.execute("DELETE FROM deletion_receipts")
        db.execute("DELETE FROM account_usage")
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("DELETE FROM user")
    finally:
        db.close()


@pytest.mark.parametrize("change", [{"actual_bytes": None}, {"actual_sha256": None}, {"actual_bytes": 11}, {"artifact_id": str(uuid4())}, {"state": "future"}])
def test_custody_file_measurements_roles_and_caps_refuse(candidate, change):
    db, (owner, project, raw, _, _) = upgraded(candidate)
    try:
        b = batch(owner, project, raw)
        insert(db, "physical_custody_batches", b)
        row = dict(batch_id=b["batch_id"], ordinal=1, role="stdout_log", location="stage", artifact_id=None,
                   leaf="stdout.txt", max_bytes=10, actual_bytes=0, actual_sha256=hashlib.sha256(b"").hexdigest(), state="present")
        row.update(change)
        with pytest.raises(sqlite3.IntegrityError):
            insert(db, "physical_custody_files", row)
    finally:
        db.close()


def test_partial_job_fingerprint_unique_excludes_failed_not_success(candidate):
    db, (_, _, _, _, job) = upgraded(candidate)
    try:
        db.execute("UPDATE processing_jobs SET method_id='gravity.station-corrections/v1',physical_fingerprint=?", ("a"*64,))
        row = dict(zip([r[1] for r in db.execute("PRAGMA table_info(processing_jobs)")], db.execute("SELECT * FROM processing_jobs").fetchone()))
        row.update(id=str(uuid4()), state="queued")
        insert(db, "processing_jobs", row)  # The earlier failed fingerprint permits a real new job ID.
        row.update(id=str(uuid4()), state="succeeded")
        with pytest.raises(sqlite3.IntegrityError):
            insert(db, "processing_jobs", row)
        db.execute("UPDATE processing_jobs SET state='cancelled' WHERE id<>?", (job,))
        insert(db, "processing_jobs", row)
        row.update(id=str(uuid4()))
        with pytest.raises(sqlite3.IntegrityError):
            insert(db, "processing_jobs", row)
    finally:
        db.close()


def test_real_candidate_downgrade_refuses(candidate):
    db, _ = upgraded(candidate)
    db.close()
    config, _, _ = candidate
    with pytest.raises(ValueError, match="candidate_downgrade_forbidden"):
        command.downgrade(config, OLD)


def test_pending_root_intent_can_reserve_an_absent_output_but_not_a_second_raw_parser(candidate):
    db, (owner, project, raw, _, _) = upgraded(candidate)
    try:
        root = str(uuid4())
        family = dict(root_dataset_id=root, raw_asset_id=raw, project_id=project, owner_id=owner,
                      parser_version="gravity-stations-json/v1", state="pending", next_ordinal=2,
                      published_count=0, reserved_count=1, created_us=1)
        insert(db, "physical_dataset_families", family)
        intent = dict(intent_id=str(uuid4()), kind="root", owner_id=owner, project_id=project, raw_asset_id=raw,
                      root_dataset_id=root, parser_version=family["parser_version"], child_dataset_id=root,
                      ordinal=1, job_id=None, parent_dataset_id=None, parent_dataset_sha256=None,
                      request_sha256=None, stage_id=root, permanent_reservation_bytes=16*1048576,
                      phase="prepared", created_us=1)
        insert(db, "physical_publication_intents", intent)
        assert db.execute("SELECT count(*) FROM observation_datasets WHERE id=?", (root,)).fetchone() == (0,)
        family["root_dataset_id"] = str(uuid4())
        with pytest.raises(sqlite3.IntegrityError):
            insert(db, "physical_dataset_families", family)
        intent.update(intent_id=str(uuid4()), child_dataset_id=str(uuid4()))
        with pytest.raises(sqlite3.IntegrityError):
            insert(db, "physical_publication_intents", intent)
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        db.close()


def test_child_parent_family_and_owned_raw_composite_fk_reject_rehashed_foreign_root(candidate):
    db, (owner, project, raw, root, _) = upgraded(candidate)
    try:
        # SQL-only structural fixture; never a published scientific artifact.
        db.execute("DELETE FROM processing_jobs")
        db.execute("DELETE FROM observation_datasets")
        db.execute("DELETE FROM physical_dataset_families")
        insert(db, "physical_dataset_families", dict(root_dataset_id=root, raw_asset_id=raw, project_id=project,
               owner_id=owner, parser_version="gravity-stations-json/v1", state="published", next_ordinal=3,
               published_count=2, reserved_count=0, created_us=1))
        common = dict(project_id=project, owner_id=owner, raw_asset_id=raw, parser_version="gravity-stations-json/v1",
                      modality="gravity_physical_station", row_count=2, raw_sha256="a"*64, sha256="b"*64,
                      byte_count=9, created_at="2026-10-03 01:00:00", root_dataset_id=root)
        insert(db, "observation_datasets", dict(common, id=root, version=1, kind="root", parent_dataset_id=None,
               payload_schema="gravity-stations-1", storage_key=f"derived/{owner}/{project}/datasets/{root}.json"))
        child = str(uuid4())
        row = dict(common, id=child, version=2, kind="derived", parent_dataset_id=root,
                   payload_schema="gravity-station-adapter-result-1", sha256="e"*64,
                   storage_key=f"derived/{owner}/{project}/datasets/{child}.json")
        for change in ({"owner_id": str(uuid4())}, {"parent_dataset_id": str(uuid4())},
                       {"root_dataset_id": str(uuid4())}, {"raw_asset_id": str(uuid4())}):
            with pytest.raises(sqlite3.IntegrityError):
                insert(db, "observation_datasets", dict(row, **change))
        insert(db, "observation_datasets", row)
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        db.close()
