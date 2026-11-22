"""Real successor transaction cuts; fixtures are not numerical/native proofs."""

import copy
from uuid import uuid4

import pytest

from app.physical_debt import retire_failed_job
from app.physical_forest import reserve_child_intent
from tests.api.test_physical_forest import connect, forest as forest, successor as successor


def terminal(values, installed):
    return dict(owner_id=values["owner_id"], project_id=values["project_id"], job_id=values["job_id"],
                state="failed", error_code="physical_publication_abandoned",
                metrics=dict(wall_ms=11, cpu_ms=7, peak_rss_bytes=100, scratch_bytes=20),
                finished_at="2026-10-08 01:01:00", finished_us=3,
                installed_targets=installed, abandon_batch_id=str(uuid4()))


@pytest.mark.parametrize("installed_count", [0, 1, 2])
def test_failed_preparation_retains_every_literal_copy_and_never_adopts(forest, installed_count):
    path, values = forest
    with connect(path) as db:
        reserve_child_intent(db, **values)
        retire_failed_job(db, **terminal(values, values["targets"][:installed_count]))
        assert db.execute("SELECT state,physical_cpu_ms,result_key,result_sha256 FROM processing_jobs").fetchone() == ("failed", 7, None, None)
        assert db.execute("SELECT count(*) FROM observation_datasets").fetchone() == (1,)
        assert db.execute("SELECT count(*) FROM physical_dataset_productions").fetchone() == (0,)
        assert db.execute("SELECT count(*) FROM physical_publication_intents").fetchone() == (0,)
        assert db.execute("SELECT count(*) FROM physical_publication_targets").fetchone() == (0,)
        assert db.execute("SELECT next_ordinal,published_count,reserved_count FROM physical_dataset_families").fetchone() == (3, 1, 0)
        assert db.execute("SELECT permanent_reservation_bytes FROM physical_job_controls").fetchone() == (0,)
        charge = 20 + sum(v["bytes"] for v in values["targets"][:installed_count])
        assert db.execute("SELECT sum(charged_bytes) FROM physical_custody_batches").fetchone() == (charge,)
        assert set(row[0] for row in db.execute("SELECT state FROM physical_custody_batches")) == {"cleanup_pending"}
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []


@pytest.mark.parametrize("cut", ["debt", "terminal"])
def test_terminal_uncertainty_rolls_back_all_sql_but_does_not_release_liability(forest, cut):
    path, values = forest
    with connect(path) as db:
        reserve_child_intent(db, **values)
        def fail(point):
            if point == cut:
                raise RuntimeError("injected_terminal_uncertainty")
        with pytest.raises(RuntimeError):
            retire_failed_job(db, **terminal(values, values["targets"]), failure_cut=fail)
        assert db.execute("SELECT state FROM processing_jobs").fetchone() == ("running",)
        assert db.execute("SELECT next_ordinal,reserved_count FROM physical_dataset_families").fetchone() == (3, 1)
        assert db.execute("SELECT count(*) FROM physical_publication_targets").fetchone() == (2,)
        assert db.execute("SELECT state,charged_bytes FROM physical_custody_batches").fetchone() == ("sealed", 20)


def test_cancel_without_intent_retains_stage_before_retiring_reservation(forest):
    path, values = forest
    with connect(path) as db:
        db.execute("UPDATE processing_jobs SET cancel_requested=1")
        request = terminal(values, [])
        request.update(state="cancelled", error_code="physical_cancelled")
        retire_failed_job(db, **request)
        assert db.execute("SELECT state,result_key FROM processing_jobs").fetchone() == ("cancelled", None)
        assert db.execute("SELECT next_ordinal,reserved_count FROM physical_dataset_families").fetchone() == (2, 0)
        assert db.execute("SELECT state,charged_bytes FROM physical_custody_batches").fetchone() == ("cleanup_pending", 20)


@pytest.mark.parametrize("mutation", [
    lambda v: v[0].update(bytes=10),
    lambda v: v[0].update(sha256="a"*64),
    lambda v: v[0].update(storage_key="foreign/result.json"),
    lambda v: v.append(v[0]),
])
def test_foreign_unknown_or_duplicate_installed_target_keeps_prepared_state(forest, mutation):
    path, values = forest
    installed = copy.deepcopy(values["targets"][:1])
    mutation(installed)
    with connect(path) as db:
        reserve_child_intent(db, **values)
        with pytest.raises(ValueError):
            retire_failed_job(db, **terminal(values, installed))
        assert db.execute("SELECT state FROM processing_jobs").fetchone() == ("running",)
        assert db.execute("SELECT reserved_count FROM physical_dataset_families").fetchone() == (1,)


@pytest.mark.parametrize("sql", [
    "UPDATE physical_custody_batches SET state='quarantined'",
    "UPDATE physical_custody_batches SET charged_bytes=0",
    "DELETE FROM physical_custody_files",
])
def test_unknown_stage_is_not_convenient_failure_with_released_quota(forest, sql):
    path, values = forest
    with connect(path) as db:
        db.execute(sql)
        with pytest.raises(ValueError):
            retire_failed_job(db, **terminal(values, []))
        assert db.execute("SELECT state FROM processing_jobs").fetchone() == ("running",)
        assert db.execute("SELECT permanent_reservation_bytes FROM physical_job_controls").fetchone()[0] > 0


def test_nested_terminal_transaction_preserves_callers_work(forest):
    path, values = forest
    with connect(path) as db:
        db.execute("BEGIN IMMEDIATE")
        with pytest.raises(ValueError, match="outside_transaction"):
            retire_failed_job(db, **terminal(values, []))
        assert db.in_transaction
        db.rollback()
