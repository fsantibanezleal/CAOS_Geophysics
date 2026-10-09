"""Exact SQL byte charges, no filesystem-block or media-erasure claims."""

import pytest

from app.physical_accounting import account_private_charge
from app.physical_debt import retire_failed_job
from app.physical_forest import reserve_child_intent
from app.physical_persistence import M
from tests.api.test_physical_debt import terminal
from tests.api.test_physical_forest import connect, forest as forest, successor as successor


def test_sql_utf8_and_every_preserved_blob_copy_are_charged(forest):
    path, values = forest
    with connect(path) as db:
        db.execute("UPDATE processing_jobs SET request_json=?", (' {"label":"Se\u00f1al", "n":1.0} ',))
        db.execute("BEGIN IMMEDIATE")
        charge = account_private_charge(db, values["owner_id"])
        actual = db.execute("SELECT length(request_bytes)+length(module_manifest_bytes)+length(CAST(request_json AS BLOB))+length(CAST(preflight AS BLOB)) FROM physical_job_controls JOIN processing_jobs ON job_id=id").fetchone()[0]
        assert charge["controls"] == actual
        assert charge["raw"] == 7 and charge["datasets"] == 9 and charge["custody"] == 20
        assert charge["permanent"] == 80*M and charge["legacy_active"] == 0
        assert charge["total"] == 7+9+20+80*M+actual
        db.rollback()


def test_terminal_transfers_only_unconsumed_capacity_to_literal_installed_debt(forest):
    path, values = forest
    with connect(path) as db:
        reserve_child_intent(db, **values)
        db.execute("BEGIN IMMEDIATE")
        before = account_private_charge(db, values["owner_id"])
        db.rollback()
        retire_failed_job(db, **terminal(values, values["targets"]))
        db.execute("BEGIN IMMEDIATE")
        after = account_private_charge(db, values["owner_id"])
        assert after["custody"] == 40  # Stage20 plus distinct installed20.
        assert after["controls"] == before["controls"] and after["permanent"] == 0
        assert before["total"]-after["total"] == 80*M-20
        db.rollback()


def test_no_active_unknown_method_fallback(forest):
    path, values = forest
    with connect(path) as db:
        # Remove the control first so the old generic job columns can hold an
        # unregistered legacy label. This is an explicit inconsistent fixture.
        db.execute("DELETE FROM physical_job_controls")
        db.execute("UPDATE processing_jobs SET method_id='gravity.future-method/v99', physical_fingerprint=NULL")
        db.execute("BEGIN IMMEDIATE")
        with pytest.raises(ValueError, match="unknown_active_method"):
            account_private_charge(db, values["owner_id"])
        db.rollback()


def test_raw_usage_is_not_total_and_corrupt_usage_refuses(forest):
    path, values = forest
    with connect(path) as db:
        db.execute("UPDATE account_usage SET raw_bytes=8")
        db.execute("BEGIN IMMEDIATE")
        with pytest.raises(ValueError, match="raw_accounting"):
            account_private_charge(db, values["owner_id"])
        db.rollback()


def test_no_implicit_inconsistent_snapshot(forest):
    path, values = forest
    with connect(path) as db:
        with pytest.raises(ValueError, match="consistent_transaction"):
            account_private_charge(db, values["owner_id"])
