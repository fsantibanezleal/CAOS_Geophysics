"""Actual private POSIX correction terminal commit, no live queue activation."""

import argparse
import json
import os
from pathlib import Path
import sqlite3

from app.physical_contract import canonical
from app.physical_posix import PrivateFiles
from app.physical_publication import audit_correction_ancestry, publish_correction


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',required=True)
    root=Path(parser.parse_args().root)
    assert root.is_absolute() and os.name=='posix' and os.geteuid()==61901
    record=json.loads((root/'input.json').read_bytes())
    db=sqlite3.connect(root/'fixture.sqlite',isolation_level=None,timeout=30)
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('PRAGMA synchronous=FULL')
    db.execute('PRAGMA trusted_schema=OFF')
    db.execute('PRAGMA busy_timeout=30000')
    assert db.execute('SELECT sqlite_version(),sqlite_source_id()').fetchone()==(
        '3.51.3','2026-03-13 10:38:09 737ae4a34738ffa0c3ff7f9bb18df914dd1cad163f28fd6b6e114a344fe6d618')
    assert db.execute('PRAGMA journal_mode').fetchone()==('delete',)
    before=list(db.execute('SELECT state,request_json,result_key,physical_cpu_ms FROM processing_jobs'))
    with PrivateFiles(root) as files:
        for cut in ('child','production','terminal','retired'):
            def fail(point):
                if point==cut:
                    raise RuntimeError('actual_native_derived_cut')
            try:
                publish_correction(db,files,**record['values'],failure_cut=fail)
            except RuntimeError as error:
                assert str(error)=='actual_native_derived_cut'
            else:
                raise AssertionError('native failure not injected')
            assert list(db.execute('SELECT state,request_json,result_key,physical_cpu_ms FROM processing_jobs'))==before
            assert db.execute('SELECT count(*) FROM observation_datasets').fetchone()==(1,)
            assert db.execute('SELECT count(*) FROM physical_publication_targets').fetchone()==(2,)
            assert db.execute('SELECT permanent_reservation_bytes FROM physical_job_controls').fetchone()==(80*1048576,)
        actual=publish_correction(db,files,**record['values'])
        assert canonical(actual)==canonical(record['snapshot'])
        cursor=db.execute("SELECT * FROM observation_datasets WHERE kind='derived'")
        row=dict(zip((c[0] for c in cursor.description),cursor.fetchone()))
        body,snapshot=audit_correction_ancestry(db,files,row,approved_manifests=record['values']['approved_manifests'])
        assert canonical(snapshot)==canonical(actual) and len(body)==actual['output_dataset_bytes']
        assert db.execute('SELECT state FROM processing_jobs').fetchone()==('succeeded',)
        assert db.execute('SELECT published_count,reserved_count,next_ordinal FROM physical_dataset_families').fetchone()==(2,0,3)
        assert db.execute('SELECT state FROM physical_custody_batches').fetchone()==('cleanup_pending',)
        assert db.execute('SELECT count(*) FROM physical_publication_intents').fetchone()==(0,)
        assert db.execute('PRAGMA integrity_check').fetchall()==[('ok',)]
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]
    db.close()
    print(json.dumps(dict(schema='geophysics.physical-native-derived-drill/v1',uid=os.geteuid(),sqlite_version='3.51.3',
                          all_four_terminal_cuts_rollback=True,actual_dual_file_saved_science_binding=True,
                          complete_original_and_producing_edge_verified=True,all_terminal_rows_debt_retirement_atomic=True,
                          no_numerical_replay_in_parent=True,fixture_telemetry_only=True,production_activated=False),sort_keys=True))


if __name__=='__main__':
    main()
