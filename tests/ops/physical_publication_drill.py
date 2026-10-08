"""Actual isolated POSIX root publication/cleanup cuts, no live activation."""

import argparse
import os
from pathlib import Path
import sqlite3

from app.physical_contract import byte_sha, canonical, decode_source
from app.physical_debt import cleanup_custody_file
from app.physical_forest import SUCCESSOR_DDL
from app.physical_posix import PrivateFiles
from app.physical_roots import prepare_root, publish_root
from app.physical_successor import ddl_sha256


def connect(path):
    db = sqlite3.connect(path.as_uri()+"?mode=rw&cache=private", uri=True,
                         autocommit=sqlite3.LEGACY_TRANSACTION_CONTROL, isolation_level=None, timeout=30)
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA synchronous=FULL")
    db.execute("PRAGMA trusted_schema=OFF")
    db.execute("PRAGMA busy_timeout=30000")
    return db


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    arguments = parser.parse_args()
    root = Path(arguments.root)
    assert root.is_absolute() and os.name == "posix" and os.geteuid() == 61901
    with sqlite3.connect(":memory:") as memory:
        assert memory.execute("SELECT sqlite_version(),sqlite_source_id()").fetchone() == (
            "3.51.3", "2026-03-13 10:38:09 737ae4a34738ffa0c3ff7f9bb18df914dd1cad163f28fd6b6e114a344fe6d618")
    record = decode_source([(root/"input.json").read_bytes()], max_bytes=65536, depth=8, nodes=2000)
    values = record["values"]
    with PrivateFiles(root) as files, connect(root/"fixture.sqlite") as db:
        assert ddl_sha256(db) == SUCCESSOR_DDL
        body = files.read(f".job-staging/{values['root_dataset_id']}/dataset.json", cap=16*1048576,
                          expected_bytes=record["dataset_bytes"], expected_sha256=record["dataset_sha256"])
        prepare_root(db, files, **values)
        target = f"derived/{values['owner_id']}/{values['project_id']}/datasets/{values['root_dataset_id']}.json"
        files.install(f".job-staging/{values['root_dataset_id']}/dataset.json", target, cap=16*1048576,
                      expected_bytes=len(body), expected_sha256=byte_sha(body))
        def uncertain(point):
            if point == "published":
                raise RuntimeError("actual_native_published_cut")
        publication = dict(owner_id=values["owner_id"], project_id=values["project_id"],
                           intent_id=values["intent_id"], created_at="2026-10-08 01:01:00")
        try:
            publish_root(db, files, **publication, failure_cut=uncertain)
        except RuntimeError:
            pass
        assert not db.execute("SELECT 1 FROM observation_datasets").fetchone()
        assert db.execute("SELECT count(*) FROM physical_publication_intents").fetchone() == (1,)
        assert files.read(target, cap=16*1048576, expected_bytes=len(body), expected_sha256=byte_sha(body)) == body
        publish_root(db, files, **publication)
        assert db.execute("SELECT kind,sha256,byte_count FROM observation_datasets").fetchone() == ("root",byte_sha(body),len(body))
        assert not db.execute("SELECT 1 FROM physical_dataset_productions").fetchone()
        batch, inv_body = db.execute("SELECT batch_id,inventory_bytes FROM physical_custody_batches").fetchone()
        inventory = decode_source([inv_body], max_bytes=4*1048576, depth=8, nodes=100000)
        first = inventory["initial_files"][0]
        cleanup_custody_file(db, files, owner_id=values["owner_id"], batch_id=batch,
                            ordinal=first["ordinal"], removed_us=4)
        remaining = sum(s["actual_bytes"] for s in inventory["initial_files"][1:])
        assert db.execute("SELECT state,charged_bytes FROM physical_custody_batches").fetchone() == ("cleanup_pending",remaining)
        second = inventory["initial_files"][1]
        def unlink_uncertain(point):
            if point == "before_sql_acknowledgement":
                raise RuntimeError("actual_native_uncertain_charge_ack")
        try:
            cleanup_custody_file(db, files, owner_id=values["owner_id"], batch_id=batch,
                                ordinal=second["ordinal"], removed_us=5, failure_cut=unlink_uncertain)
        except RuntimeError:
            pass
        assert db.execute("SELECT state,charged_bytes FROM physical_custody_batches").fetchone() == ("cleanup_pending",remaining)
        # Exact directory absence does not authorize another SQL acknowledgement.
        try:
            cleanup_custody_file(db, files, owner_id=values["owner_id"], batch_id=batch,
                                ordinal=second["ordinal"], removed_us=6)
        except (OSError, ValueError):
            pass
        else:
            raise AssertionError("uncertain absence released charge")
        assert db.execute("SELECT state,charged_bytes FROM physical_custody_batches").fetchone() == ("cleanup_pending",remaining)
        raw = db.execute("SELECT storage_key,sha256,byte_count FROM raw_assets").fetchone()
        original = files.read(raw[0], cap=16*1048576, expected_bytes=raw[2], expected_sha256=raw[1])
        assert byte_sha(original) == raw[1]
        assert db.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        result = dict(schema="geophysics.physical-native-publication-drill/v1", uid=os.geteuid(),
                      actual_source_bound_root=True, intent_and_single_target_committed=True,
                      actual_independent_destination_copy=True, uncertain_publication_not_adopted=True,
                      root_commit_stage_debt_atomic=True, actual_durable_partial_cleanup_ack=True,
                      uncertain_sql_ack_retains_charge=True, absence_not_charge_relief=True,
                      original_bytes_retained=True, dataset_sha256=byte_sha(body),
                      retained_stage_debt_bytes=remaining, sqlite_integrity=True,
                      fixture_only=True, production_activated=False, power_loss_tested=False)
        print(canonical(result).decode())


if __name__ == "__main__":
    main()
