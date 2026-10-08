"""SQL reservation/cancellation cuts, not scientific publication or native proof."""

from concurrent.futures import ThreadPoolExecutor
import copy
import sqlite3
import threading
from uuid import uuid4

import pytest
from alembic import command

from app.physical_contract import canonical, byte_sha
from app.physical_forest import reserve_child_intent
from app.physical_persistence import M
from app.physical_successor import REVISION
from tests.api.test_physical_successor import successor as _successor_fixture
from tests.api.test_physical_persistence_schema import seed, insert

successor = _successor_fixture


def uid():
    return str(uuid4())


@pytest.fixture
def forest(successor):
    config, path = successor
    with sqlite3.connect(path) as db:
        owner, project, raw, root, job = seed(db)
    command.upgrade(config, REVISION)
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("DELETE FROM processing_jobs")
        db.execute("DELETE FROM observation_datasets")
        db.execute("DELETE FROM physical_dataset_families")
        insert(db, "physical_dataset_families", dict(root_dataset_id=root, raw_asset_id=raw, project_id=project,
               owner_id=owner, parser_version="gravity-stations-json/v1", state="published", next_ordinal=2,
               published_count=1, reserved_count=0, created_us=1))
        insert(db, "observation_datasets", dict(id=root, project_id=project, owner_id=owner, raw_asset_id=raw,
               version=1, parser_version="gravity-stations-json/v1", modality="gravity_physical_station", row_count=2,
               raw_sha256="a"*64, sha256="b"*64, byte_count=9, storage_key=f"derived/{owner}/{project}/datasets/{root}.json",
               created_at="2026-10-08 01:00:00", kind="root", root_dataset_id=root, parent_dataset_id=None,
               payload_schema="gravity-stations-1"))
        # SQL-only control fixture: these bytes do NOT represent an engine result.
        insert(db, "processing_jobs", dict(id=job, project_id=project, owner_id=owner, dataset_id=root,
               dataset_sha256="b"*64, method_id="gravity.station-corrections/v1", request_json='{"fixture":true}',
               request_sha256="c"*64, preflight='{"fixture":true}', state="running", cancel_requested=0,
               created_at="2026-10-08 01:00:00", physical_fingerprint="d"*64))
        stage = job
        insert(db, "physical_job_controls", dict(job_id=job, owner_id=owner, project_id=project, dataset_id=root,
               dataset_sha256="b"*64, root_dataset_id=root, raw_asset_id=raw, raw_sha256="a"*64, raw_bytes=7,
               method_id="gravity.station-corrections/v1", request_sha256="c"*64, request_bytes=b'{"fixture":true}',
               submitted_parameters_sha256="e"*64, scientific_request_sha256="f"*64, module_manifest_bytes=b'{}',
               module_manifest_sha256="e"*64, parent_production_bytes=None, stage_id=stage,
               permanent_reservation_bytes=80*M, admission_receipt_sha256="f"*64, created_us=1))
        child = uid()
        batch = uid()
        slots = [dict(ordinal=i, role=role, location="stage", artifact_id=artifact,
                      leaf=leaf, max_bytes=16*M if role == "dataset_copy" else 64*M,
                      actual_bytes=count, actual_sha256=h)
                 for i, (role, artifact, leaf, count, h) in enumerate((
                     ("dataset_copy", child, "dataset.json", 9, "e"*64),
                     ("result_copy", job, "result.json", 11, "f"*64),
                 ), 1)]
        inv = dict(schema="geophysics.physical-custody/v1", batch_id=batch, owner_id=owner, project_id=project,
                   origin_kind="job_stage", origin_id=stage, stage_id=stage, deletion_receipt_id=None,
                   raw_asset_id=raw, raw_sha256="a"*64, raw_bytes=7, parser_version="gravity-stations-json/v1",
                   method_id="gravity.station-corrections/v1", capacity_bytes=256*M,
                   initial_files=slots, removed_ordinals=[])
        body = canonical(inv)
        insert(db, "physical_custody_batches", dict(batch_id=batch, owner_id=owner, project_id=project,
               origin_kind="job_stage", origin_id=stage, stage_id=stage, deletion_receipt_id=None,
               raw_asset_id=raw, raw_sha256="a"*64, raw_bytes=7, parser_version="gravity-stations-json/v1",
               method_id="gravity.station-corrections/v1", state="sealed", capacity_bytes=256*M,
               charged_bytes=20, inventory_bytes=body, inventory_sha256=byte_sha(body), created_us=1,
               sealed_us=2, removed_us=None))
        for slot in slots:
            insert(db, "physical_custody_files", dict(slot, batch_id=batch, state="present"))
        db.commit()
    return path, dict(owner_id=owner, project_id=project, parent_dataset_id=root, parent_dataset_sha256="b"*64,
                     job_id=job, stage_id=stage, child_dataset_id=child, intent_id=uid(), created_us=2,
                     targets=[dict(kind=kind, artifact_id=identifier, storage_key=f"derived/{owner}/{project}/{lane}/{identifier}.json",
                                   bytes=count, sha256=h) for kind, identifier, lane, count, h in (
                                       ("dataset", child, "datasets", 9, "e"*64),
                                       ("result", job, "results", 11, "f"*64))])


def connect(path):
    db = sqlite3.connect(path, isolation_level=None, timeout=30)
    db.execute("PRAGMA foreign_keys=ON")
    return db


def test_atomic_reserved_ordinal_is_not_a_published_child(forest):
    path, values = forest
    with connect(path) as db:
        ordinal = reserve_child_intent(db, **values)
        assert ordinal == 2
        assert db.execute("SELECT next_ordinal,published_count,reserved_count FROM physical_dataset_families").fetchone() == (3, 1, 1)
        assert db.execute("SELECT count(*) FROM observation_datasets").fetchone() == (1,)
        assert db.execute("SELECT ordinal,phase FROM physical_publication_intents").fetchone() == (2, "prepared")
        assert db.execute("SELECT count(*) FROM physical_publication_targets").fetchone() == (2,)
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []


@pytest.mark.parametrize("change", [
    dict(owner_id=uid()), dict(project_id=uid()), dict(parent_dataset_id=uid()),
    dict(parent_dataset_sha256="e"*64), dict(job_id=uid()), dict(stage_id=uid()),
])
def test_foreign_or_stale_identity_never_advances_allocator(forest, change):
    path, values = forest
    with connect(path) as db:
        with pytest.raises(ValueError):
            reserve_child_intent(db, **dict(values, **change))
        assert db.execute("SELECT next_ordinal,reserved_count FROM physical_dataset_families").fetchone() == (2, 0)
        assert db.execute("SELECT count(*) FROM physical_publication_intents").fetchone() == (0,)


@pytest.mark.parametrize("sql", [
    "UPDATE processing_jobs SET cancel_requested=1",
    "UPDATE processing_jobs SET state='failed'",
    "UPDATE physical_dataset_families SET published_count=64",
    "UPDATE physical_dataset_families SET next_ordinal=9007199254740991",
    "UPDATE physical_job_controls SET permanent_reservation_bytes=0",
    "UPDATE physical_custody_batches SET charged_bytes=0",
    "DELETE FROM physical_custody_files",
])
def test_cancel_terminal_capacity_exhaustion_and_missing_reservation_refuse(forest, sql):
    path, values = forest
    with connect(path) as db:
        db.execute(sql)
        before = db.execute("SELECT next_ordinal,reserved_count FROM physical_dataset_families").fetchone()
        with pytest.raises(ValueError):
            reserve_child_intent(db, **values)
        assert db.execute("SELECT next_ordinal,reserved_count FROM physical_dataset_families").fetchone() == before


def test_failure_after_allocator_update_rolls_back_intent_and_capacity(forest):
    path, values = forest
    with connect(path) as db:
        def fail():
            raise RuntimeError("injected_after_allocator")
        with pytest.raises(RuntimeError):
            reserve_child_intent(db, **values, failure_cut=fail)
        assert db.execute("SELECT next_ordinal,reserved_count FROM physical_dataset_families").fetchone() == (2, 0)
        assert db.execute("SELECT count(*) FROM physical_publication_intents").fetchone() == (0,)


def test_second_competing_reservation_keeps_exact_first_intent(forest):
    path, values = forest
    first, second = connect(path), connect(path)
    try:
        assert reserve_child_intent(first, **values) == 2
        with pytest.raises((ValueError, sqlite3.IntegrityError)):
            reserve_child_intent(second, **dict(values, intent_id=uid()))
        assert second.execute("SELECT next_ordinal,reserved_count FROM physical_dataset_families").fetchone() == (3, 1)
        assert second.execute("SELECT intent_id FROM physical_publication_intents").fetchone() == (values["intent_id"],)
    finally:
        first.close()
        second.close()


def test_helper_refuses_nested_transaction_without_committing_callers_work(forest):
    path, values = forest
    with connect(path) as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("UPDATE projects SET name='Caller transaction'")
        with pytest.raises(ValueError, match="outside_transaction"):
            reserve_child_intent(db, **values)
        assert db.in_transaction
        db.rollback()
        assert db.execute("SELECT name FROM projects").fetchone() == ("Survey",)


def test_actual_simultaneous_connections_reserve_once(forest):
    path, values = forest
    barrier = threading.Barrier(2)
    def reserve():
        with connect(path) as db:
            barrier.wait(timeout=10)
            try:
                return reserve_child_intent(db, **dict(values, intent_id=uid()))
            except sqlite3.IntegrityError:
                return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: reserve(), range(2)))
    assert outcomes.count(2) == 1 and outcomes.count(None) == 1
    with connect(path) as db:
        assert db.execute("SELECT next_ordinal,reserved_count FROM physical_dataset_families").fetchone() == (3, 1)
        assert db.execute("SELECT count(*) FROM physical_publication_targets").fetchone() == (2,)


def test_existing_committed_ordinal_gap_is_not_reused(forest):
    path, values = forest
    with connect(path) as db:
        db.execute("UPDATE physical_dataset_families SET next_ordinal=4")
        assert reserve_child_intent(db, **values) == 4
        assert db.execute("SELECT next_ordinal FROM physical_dataset_families").fetchone() == (5,)


@pytest.mark.parametrize("mutate", [
    lambda x: x.pop(),
    lambda x: x[0].update(bytes=10),
    lambda x: x[0].update(sha256="a"*64),
    lambda x: x[0].update(storage_key="../dataset.json"),
    lambda x: x[1].update(kind="dataset"),
])
def test_partial_or_rehashed_target_metadata_never_consumes_an_ordinal(forest, mutate):
    path, values = forest
    values = copy.deepcopy(values)
    mutate(values["targets"])
    with connect(path) as db:
        with pytest.raises(ValueError):
            reserve_child_intent(db, **values)
        assert db.execute("SELECT next_ordinal,reserved_count FROM physical_dataset_families").fetchone() == (2, 0)


def test_control_and_rehashed_stage_cannot_substitute_the_original_raw(forest):
    path, values = forest
    with connect(path) as db:
        db.execute("UPDATE physical_job_controls SET raw_sha256=?", ("e"*64,))
        with pytest.raises(ValueError, match="forest_raw_identity"):
            reserve_child_intent(db, **values)
        assert db.execute("SELECT next_ordinal FROM physical_dataset_families").fetchone() == (2,)
