"""Actual private POSIX saved pass/non-pass publication using qualified SQLite."""

import argparse
import json
import os
from pathlib import Path
import sqlite3

from app.physical_contract import canonical
from app.physical_posix import PrivateFiles
from app.physical_publication import audit_transform_producer, publish_transform


def inventory(db):
    result={}
    for name, in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
        assert name.replace('_','').isalnum()
        result[name]=list(db.execute('SELECT * FROM '+name+' ORDER BY rowid'))
    return result


def run(root):
    record=json.loads((root/'input.json').read_bytes())
    db=sqlite3.connect(root/'fixture.sqlite',isolation_level=None,timeout=30)
    try:
        db.execute('PRAGMA foreign_keys=ON'); db.execute('PRAGMA synchronous=FULL')
        db.execute('PRAGMA trusted_schema=OFF'); db.execute('PRAGMA busy_timeout=30000')
        assert db.execute('SELECT sqlite_version(),sqlite_source_id()').fetchone()==(
            '3.51.3','2026-03-13 10:38:09 737ae4a34738ffa0c3ff7f9bb18df914dd1cad163f28fd6b6e114a344fe6d618')
        assert db.execute('PRAGMA journal_mode').fetchone()==('delete',)
        before=inventory(db)
        # Complete fixture ordinary bytes excluding SQLite's mutable bookkeeping.
        retained={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file() and p.name!='fixture.sqlite'}
        with PrivateFiles(root) as files:
            for cut in ('child','production','terminal','retired'):
                def fail(point):
                    if point==cut:
                        raise RuntimeError('actual_native_transform_cut')
                try:
                    publish_transform(db,files,**record['values'],failure_cut=fail)
                except RuntimeError as error:
                    assert str(error)=='actual_native_transform_cut'
                else:
                    raise AssertionError('native cut not executed')
                assert inventory(db)==before
                assert retained=={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file() and p.name!='fixture.sqlite'}
                assert db.execute('SELECT count(*) FROM physical_publication_targets').fetchone()==(2,)
            child=publish_transform(db,files,**record['values'])
            assert canonical(child)==canonical(record['child'])
            cursor=db.execute('SELECT * FROM observation_datasets WHERE id=?',(child['dataset_id'],))
            row=dict(zip((c[0] for c in cursor.description),cursor.fetchone()))
            assert canonical(audit_transform_producer(db,files,row,approved_manifests=record['values']['approved_manifests']))==canonical(child)
            assert retained=={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file() and p.name!='fixture.sqlite'}
            assert db.execute('SELECT published_count,reserved_count,next_ordinal FROM physical_dataset_families').fetchone()==(3,0,4)
            assert db.execute('SELECT count(*) FROM physical_publication_intents').fetchone()==(0,)
            assert db.execute("SELECT count(*) FROM physical_custody_batches WHERE state='cleanup_pending'").fetchone()==(2,)
            assert db.execute('PRAGMA integrity_check').fetchall()==[('ok',)]
            assert db.execute('PRAGMA foreign_key_check').fetchall()==[]
            return dict(scientific_verdict=child['production']['scientific_verdict'],stations=len(child['payload']['stations']['station_ids']),
                candidates=len(child['payload']['selection']['candidates']),height=child['payload']['selection']['height_m'],
                all_four_cuts_rollback=True,retained_bytes_unchanged=True,full_correction_ancestry_verified=True)
    finally:
        db.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--root',required=True)
    root=Path(parser.parse_args().root)
    assert root.is_absolute() and os.name=='posix' and os.geteuid()==61901
    rows=[run(root/lane) for lane in ('passed','non_pass')]
    assert [r['scientific_verdict'] for r in rows]==['passed','non_pass']
    assert rows[1]['height'] is None and all(r['stations']==196 and r['candidates']==9 for r in rows)
    print(json.dumps(dict(schema='geophysics.physical-native-transform-drill/v1',uid=os.geteuid(),sqlite_version='3.51.3',
        rows=rows,no_numerical_replay_in_parent=True,fixture_telemetry_only=True,production_activated=False),sort_keys=True))
