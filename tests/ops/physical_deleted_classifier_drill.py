"""Bounded native deleted snapshot and known durable cleanup, not HTTP DELETE."""

import argparse
import asyncio
import json
import os
from pathlib import Path
import sqlite3

from app.physical_classifier import classify_snapshot
from app.physical_contract import byte_sha
from app.physical_debt import cleanup_custody_file
from app.physical_leases import WriterLeases
from app.physical_participation import WorkerExclusion
from app.physical_posix import PrivateFiles


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--policy', required=True)
    args = parser.parse_args()
    root = Path(args.root)
    assert os.name == 'posix' and os.geteuid() == 61901 and root.is_absolute()
    os.umask(0o077)
    private = root / 'private'
    db = sqlite3.connect(root / 'fixture.sqlite', isolation_level=None, timeout=30)
    leases = None
    try:
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA synchronous=FULL')
        db.execute('PRAGMA trusted_schema=OFF')
        assert db.execute('SELECT sqlite_version(),sqlite_source_id()').fetchone() == (
            '3.51.3', '2026-03-13 10:38:09 737ae4a34738ffa0c3ff7f9bb18df914dd1cad163f28fd6b6e114a344fe6d618')
        owner, batch, expected_charge = db.execute("SELECT owner_id,batch_id,charged_bytes FROM physical_custody_batches WHERE origin_kind='project_deletion'").fetchone()
        assert db.execute('SELECT count(*) FROM projects').fetchone() == (0,)
        metadata = {}
        for name, body in (('.physical-writers.lock', b'\0'), ('.processing-worker.lock', b'0')):
            with (private / name).open('xb') as stream:
                stream.write(body); stream.flush(); os.fsync(stream.fileno())
            (private / name).chmod(0o600)
            metadata[name] = dict(cap=1, bytes=1, sha256=byte_sha(body), required=True)
        with PrivateFiles(private) as files:
            lock = (private / '.physical-writers.lock').stat()
            old = (private / '.processing-worker.lock').stat()
            leases = WriterLeases(private, device=lock.st_dev, inode=lock.st_ino, uid=os.geteuid())
            worker = WorkerExclusion(leases, device=old.st_dev, inode=old.st_ino, uid=os.geteuid())
            async with leases.acquire(exclusive=True):
                async with worker.acquire():
                    def classify():
                        leases.require_held(exclusive=True); worker.require_held()
                        before = db.total_changes
                        db.execute('BEGIN IMMEDIATE')
                        try:
                            result = classify_snapshot(db, files, approved_manifests={}, approved_installations={},
                                native_metadata=metadata, expected_source_policy_sha256=args.policy)
                            assert db.in_transaction and before == db.total_changes
                            return result
                        finally:
                            db.rollback()
                    before = classify()
                    assert before.classification == 'coherent_committed', before.reason
                    assert before.account_charges[owner]['raw'] == 0 and before.account_charges[owner]['custody'] == 2*expected_charge
                    old_tombstone = db.execute('SELECT tombstone_bytes,tombstone_sha256 FROM physical_deletion_extensions').fetchone()
                    size = db.execute('SELECT actual_bytes FROM physical_custody_files WHERE batch_id=? AND ordinal=1', (batch,)).fetchone()[0]
                    cleanup_custody_file(db, files, owner_id=owner, batch_id=batch, ordinal=1, removed_us=5)
                    after = classify()
                    assert after.classification == 'coherent_committed', after.reason
                    assert after.account_charges[owner]['custody'] == 2*expected_charge-size
                    assert db.execute('SELECT tombstone_bytes,tombstone_sha256 FROM physical_deletion_extensions').fetchone() == old_tombstone
                    # Exact known introduced negative retained, not auto-repaired.
                    with (private / 'unknown-deleted-control.bin').open('xb') as stream:
                        stream.write(b'known negative never adopt')
                    bad = classify()
                    assert bad.classification == 'inconsistent' and not bad.operations and bad.inventory_sha256 is None
                    assert (private / 'unknown-deleted-control.bin').read_bytes() == b'known negative never adopt'
                    assert db.execute('PRAGMA foreign_key_check').fetchall() == []
                    assert db.execute('PRAGMA integrity_check').fetchone() == ('ok',)
                    print(json.dumps(dict(schema='geophysics.physical-native-deleted-classifier-drill/v1', uid=os.geteuid(),
                        before_inventory_sha256=before.inventory_sha256, after_inventory_sha256=after.inventory_sha256,
                        actual_exclusive_and_original_worker=True, known_unlink_directory_fsync_and_sql_ack=True,
                        original_tombstone_unchanged=True, removed_bytes=size, before_custody_charge=2*expected_charge,
                        after_custody_charge=2*expected_charge-size, classifier_sql_changes=0,
                        unknown_refused_and_preserved=True, actual_http_delete_performed=False,
                        runtime_admission_inferred=False, production_activated=False), sort_keys=True))
    finally:
        if leases is not None: leases.close()
        db.close()


if __name__ == '__main__':
    asyncio.run(main())
