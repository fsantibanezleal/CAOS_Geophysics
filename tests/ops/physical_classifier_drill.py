"""Actual Linux source-bound classifier, saved original science, no replay."""

import argparse
import asyncio
import json
import os
from pathlib import Path
import sqlite3

from app.physical_classifier import classify_snapshot
from app.physical_contract import byte_sha, canonical
from app.physical_leases import WriterLeases
from app.physical_participation import WorkerExclusion
from app.physical_posix import PrivateFiles
from app.physical_publication import publish_transform
from tests.api.test_physical_classifier import complete_fixture_root_custody


async def lane(root):
    record = json.loads((root / 'input.json').read_bytes())
    private = root / 'private'
    db = sqlite3.connect(root / 'fixture.sqlite', isolation_level=None, timeout=30)
    leases = None
    try:
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA synchronous=FULL')
        db.execute('PRAGMA trusted_schema=OFF')
        assert db.execute('SELECT sqlite_version(),sqlite_source_id()').fetchone() == (
            '3.51.3', '2026-03-13 10:38:09 737ae4a34738ffa0c3ff7f9bb18df914dd1cad163f28fd6b6e114a344fe6d618')
        # Explicit initialized fixture locks, not repair/replacement of live ones.
        for name, body in (('.physical-writers.lock', b'\0'), ('.processing-worker.lock', b'0')):
            with (private / name).open('xb') as stream:
                stream.write(body)
                stream.flush()
                os.fsync(stream.fileno())
            (private / name).chmod(0o600)
        with PrivateFiles(private) as files:
            global_lock = (private / '.physical-writers.lock').stat()
            worker_lock = (private / '.processing-worker.lock').stat()
            leases = WriterLeases(private, device=global_lock.st_dev, inode=global_lock.st_ino, uid=os.geteuid())
            worker = WorkerExclusion(leases, device=worker_lock.st_dev, inode=worker_lock.st_ino, uid=os.geteuid())
            async with leases.acquire(exclusive=True):
                async with worker.acquire():
                    # The old publication fixture's prior root stage is explicit
                    # fixture history, not an adoption of a real missing stage.
                    complete_fixture_root_custody(db, type('Root', (), {'root': private})())
                    metadata = {name: dict(cap=1, bytes=1, sha256=byte_sha(body), required=True)
                        for name, body in (('.physical-writers.lock', b'\0'), ('.processing-worker.lock', b'0'))}

                    def classify():
                        leases.require_held(exclusive=True)
                        worker.require_held()
                        changes = db.total_changes
                        db.execute('BEGIN IMMEDIATE')
                        try:
                            verdict = classify_snapshot(db, files,
                                approved_manifests=record['values']['approved_manifests'],
                                approved_installations={}, native_metadata=metadata)
                            assert db.in_transaction and changes == db.total_changes
                            return verdict
                        finally:
                            db.rollback()

                    prepared = classify()
                    assert prepared.classification == 'prepared_uncommitted', prepared.reason
                    child = publish_transform(db, files, **record['values'])
                    assert canonical(child) == canonical(record['child'])
                    committed = classify()
                    assert committed.classification == 'coherent_committed', committed.reason
                    # Exact known introduced fault only; leave it retained.
                    with (private / 'undeclared-control.bin').open('xb') as stream:
                        stream.write(b'known classifier negative, never adopt')
                    corrupt = classify()
                    assert corrupt.classification == 'inconsistent' and not corrupt.operations
                    assert (private / 'undeclared-control.bin').read_bytes() == b'known classifier negative, never adopt'
                    return dict(scientific_verdict=child['production']['scientific_verdict'],
                        stations=len(child['payload']['stations']['station_ids']),
                        candidates=len(child['payload']['selection']['candidates']),
                        height=child['payload']['selection']['height_m'],
                        prepared_inventory_sha256=prepared.inventory_sha256,
                        committed_inventory_sha256=committed.inventory_sha256,
                        complete_control_ancestry_custody=True, actual_exclusive_and_original_worker=True,
                        unknown_file_refused_and_preserved=True, classifier_sql_changes=0,
                        runtime_admission_inferred=False)
    finally:
        if leases is not None:
            leases.close()
        db.close()


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    root = Path(parser.parse_args().root)
    assert os.name == 'posix' and os.geteuid() == 61901 and root.is_absolute()
    os.umask(0o077)
    rows = [await lane(root / name) for name in ('passed', 'non_pass')]
    assert [r['scientific_verdict'] for r in rows] == ['passed', 'non_pass']
    assert rows[1]['height'] is None and all(r['stations'] == 196 and r['candidates'] == 9 for r in rows)
    print(json.dumps(dict(schema='geophysics.physical-native-classifier-drill/v1', uid=os.geteuid(),
        rows=rows, sqlite_version='3.51.3', scientific_execution_performed=False,
        deletion_extensions_qualified=False, production_activated=False), sort_keys=True))


if __name__ == '__main__':
    asyncio.run(main())
