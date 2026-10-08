"""Actual isolated post-M08 migrations, not production/WAL admission."""

import hashlib
import json
import shutil
import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config

from app.physical_successor import PREDECESSOR, REVISION, ddl_sha256
from tests.api.test_physical_persistence_schema import inventory, seed

ROOT = Path(__file__).resolve().parents[2]
WAVEFORM_SHA = "82c827b94940d803fae42eb7137fda63f2b4d816e11dddd481f79c5b3cb41ac3"
ROOTS = (
    ("gravity-station-csv/v1", "gravity_station", "geophysics.observation-dataset/v1"),
    ("edi-strict-envelope/v1", "edi_transfer_function", "geophysics.observation-dataset/v1"),
    ("supplied-profile-original/v1", "ert_profile", "geophysics.observation-dataset/v1"),
    ("supplied-profile-original/v1", "traveltime_profile", "geophysics.observation-dataset/v1"),
    ("m08/v1/" + "c" * 64, "waveform_counts_response", "geophysics.waveform-dataset/v1"),
)


@pytest.fixture
def successor(tmp_path, monkeypatch):
    versions = tmp_path / "versions"
    versions.mkdir()
    for source in sorted((ROOT / "app/migrations/versions").glob("*.py")):
        shutil.copyfile(source, versions / source.name)
    for name in ("0004_waveform_artifacts.py", "0005_physical_forest.py"):
        source = ROOT / "app/migrations/candidates" / name
        shutil.copyfile(source, versions / name)
    assert hashlib.sha256((versions / "0004_waveform_artifacts.py").read_bytes()).hexdigest() == WAVEFORM_SHA
    config = Config(str(ROOT / "app/alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "app/migrations/physical_successor"))
    config.set_main_option("version_locations", str(versions))
    config.attributes["m01_successor_candidate_only"] = True
    path = tmp_path / "successor.sqlite3"
    monkeypatch.setenv("GEOPHYSICS_DB_PATH", str(path))
    monkeypatch.setenv("GEOPHYSICS_CANDIDATE_ROOT", str(tmp_path))
    command.upgrade(config, PREDECESSOR)
    yield config, path
    assert not path.with_name(path.name + "-wal").exists()


def predecessor_snapshot(path):
    with sqlite3.connect(path) as db:
        return inventory(db), db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name").fetchall()


def assert_refused_unchanged(config, path, error):
    before = predecessor_snapshot(path)
    with pytest.raises((ValueError, sqlite3.IntegrityError), match=error):
        command.upgrade(config, REVISION)
    assert predecessor_snapshot(path) == before
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT version_num FROM alembic_version").fetchone() == (PREDECESSOR,)


def test_measured_predecessor_ddl_is_source_bound(successor):
    from app.physical_successor import PREDECESSOR_DDL
    _, path = successor
    with sqlite3.connect(path) as db:
        assert ddl_sha256(db) == PREDECESSOR_DDL


def test_successor_registration_binds_real_migration_source_and_measured_ddl(successor):
    config, path = successor
    record = json.loads((ROOT / "docs/design/features/m01-current-stage/successor-schema-registration.json").read_bytes())
    assert set(record) == {"schema", "revision", "down_revision", "ddl_sha256", "migration_sha256", "migration_git_blob"}
    assert record["schema"] == "geophysics.physical-schema-registration/v1"
    assert (record["revision"], record["down_revision"]) == (REVISION, PREDECESSOR)
    body = (ROOT / "app/migrations/candidates/0005_physical_forest.py").read_bytes()
    assert hashlib.sha256(body).hexdigest() == record["migration_sha256"]
    assert hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest() == record["migration_git_blob"]
    command.upgrade(config, REVISION)
    with sqlite3.connect(path) as db:
        assert ddl_sha256(db) == record["ddl_sha256"]


@pytest.mark.parametrize("parser,modality,payload", ROOTS)
def test_preserves_legacy_profiles_and_waveform_rows_native_types(successor, parser, modality, payload):
    config, path = successor
    with sqlite3.connect(path) as db:
        owner, project, raw, dataset, job = seed(db, parser=parser, modality=modality)
        if modality == "waveform_counts_response":
            source = db.execute("SELECT source_id FROM raw_assets WHERE id=?", (raw,)).fetchone()[0]
            db.execute("UPDATE processing_jobs SET method_id='seismic.waveform-qc-classical/v1'")
            db.execute("INSERT INTO waveform_dataset_sources VALUES (?,?,?,?,?,?,?)", (dataset, "counts", raw, source, "a"*64, 7, 1))
            db.execute("INSERT INTO waveform_result_artifacts VALUES (?,?,?,?,?)", (job, "receipt.json", "immutable-waveform-receipt", 19, "d"*64))
        elif modality in ("ert_profile", "traveltime_profile"):
            db.execute("UPDATE processing_jobs SET method_id=?", ("ert.topographic-profile/v1" if modality == "ert_profile" else "traveltime.first-arrival-profile/v1",))
            fmt = "ert_ohm" if modality == "ert_profile" else "traveltime_sgt"
            db.execute("UPDATE raw_assets SET detected_format=?", (fmt,))
            db.execute("UPDATE source_records SET declared_format=?", (fmt,))
        db.commit()
        before = inventory(db)
    command.upgrade(config, REVISION)
    with sqlite3.connect(path) as db:
        for table, (columns, rows) in before.items():
            projection = ",".join(f'"{c}",typeof("{c}")' for c in columns)
            assert list(db.execute(f'SELECT {projection} FROM "{table}" ORDER BY 1')) == rows
        assert db.execute("SELECT kind,root_dataset_id,parent_dataset_id,payload_schema FROM observation_datasets").fetchone() == ("root", dataset, None, payload)
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert db.execute("SELECT physical_fingerprint,physical_cpu_ms FROM processing_jobs").fetchone() == (None, None)
        assert db.execute("SELECT count(*) FROM physical_runtime_control").fetchone() == (0,)
        print("SUCCESSOR_DDL_SHA256=" + ddl_sha256(db))


@pytest.mark.parametrize("sql,error", [
    ("ALTER TABLE projects ADD COLUMN guessed TEXT", "unsupported_predecessor_ddl"),
    ("UPDATE processing_jobs SET state='running'", "active_predecessor_job"),
    ("UPDATE processing_jobs SET method_id='future/v1'", "unsupported_predecessor_job"),
    ("UPDATE raw_assets SET detected_format='future'", "unsupported_predecessor_format"),
    ("UPDATE observation_datasets SET parser_version='m08/v1/not-a-digest',modality='waveform_counts_response'", "unsupported_predecessor_dataset"),
    ("UPDATE observation_datasets SET parser_version='supplied-profile-original/v1',modality='gravity_station'", "unsupported_predecessor_dataset"),
])
def test_unknown_and_active_state_refuse_without_mutation(successor, sql, error):
    config, path = successor
    with sqlite3.connect(path) as db:
        seed(db)
        db.execute(sql)
        db.commit()
    assert_refused_unchanged(config, path, error)


@pytest.mark.parametrize("cut", ["indexes", "families", "dataset_copy", "dataset_rename", "job_columns", "tables", "checked"])
def test_every_migration_cut_rolls_back_schema_rows_and_revision(successor, cut):
    config, path = successor
    with sqlite3.connect(path) as db:
        seed(db)
    def fail(actual):
        if actual == cut:
            raise ValueError("injected_migration_cut")
    config.attributes["m01_successor_failure_cut"] = fail
    assert_refused_unchanged(config, path, "injected_migration_cut")
    config.attributes.pop("m01_successor_failure_cut")
    command.upgrade(config, REVISION)
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []


def test_foreign_owned_dataset_rolls_back_every_new_object(successor):
    config, path = successor
    with sqlite3.connect(path) as db:
        seed(db)
        other = str(uuid4())
        db.execute("INSERT INTO user VALUES (?,?,?,1,0,1)", (other, "foreign@example.org", "fixture"))
        db.execute("UPDATE observation_datasets SET owner_id=?", (other,))
        db.commit()
    assert_refused_unchanged(config, path, "successor_foreign_key_check_failed")


def test_predecessor_source_substitution_refuses_before_target_open(successor):
    config, path = successor
    migration = Path(config.get_main_option("version_locations")) / "0004_waveform_artifacts.py"
    migration.write_bytes(migration.read_bytes() + b"\n# substituted\n")
    assert_refused_unchanged(config, path, "predecessor_source_binding")


def test_successor_downgrade_cannot_erase_later_writes(successor):
    config, path = successor
    command.upgrade(config, REVISION)
    before = predecessor_snapshot(path)
    with pytest.raises(ValueError, match="successor_downgrade_forbidden"):
        command.downgrade(config, PREDECESSOR)
    assert predecessor_snapshot(path) == before


@pytest.mark.parametrize("name", ["0001_api_foundation.py", "0002_private_storage_permission.py", "0003_processing_jobs.py"])
def test_legacy_source_substitution_is_not_hidden_by_equal_ddl(successor, name):
    config, path = successor
    source = Path(config.get_main_option("version_locations")) / name
    source.write_bytes(source.read_bytes() + b"\n# substituted\n")
    assert_refused_unchanged(config, path, "predecessor_source_binding")


def test_wal_header_is_refused_before_native_target_open(successor, monkeypatch):
    import sqlalchemy
    config, path = successor
    body = path.read_bytes()
    path.write_bytes(body[:18] + b"\2\2" + body[20:])  # Offline bytes; no WAL experiment.
    def forbidden(*args, **kwargs):
        raise AssertionError("SQL target was opened before admission")
    monkeypatch.setattr(sqlalchemy, "create_engine", forbidden)
    with pytest.raises(ValueError, match="candidate_wal_target_refused_before_open"):
        command.upgrade(config, REVISION)
    assert path.read_bytes() == body[:18] + b"\2\2" + body[20:]
    path.write_bytes(body)


def test_explicit_external_root_is_required_before_target_open(successor, monkeypatch):
    config, path = successor
    monkeypatch.delenv("GEOPHYSICS_CANDIDATE_ROOT")
    assert_refused_unchanged(config, path, "explicit_external_candidate_root_required")


@pytest.mark.parametrize("event_name", ["before_cursor_execute", "after_cursor_execute"])
def test_actual_revision_update_failure_rolls_back_all_migration_ddl(successor, event_name):
    from sqlalchemy import event
    from sqlalchemy.engine import Engine
    config, path = successor
    with sqlite3.connect(path) as db:
        seed(db)
    def fail(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("UPDATE alembic_version"):
            raise ValueError("injected_actual_revision_update_cut")
    event.listen(Engine, event_name, fail)
    try:
        assert_refused_unchanged(config, path, "injected_actual_revision_update_cut")
    finally:
        event.remove(Engine, event_name, fail)
