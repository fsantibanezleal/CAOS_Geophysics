"""Read-only authentic M11 transport custody, not API/scientific execution.

The saved job is FAILED/custody_fixture_no_execution. Its genuine native
member bytes are not a newly accepted fit. Never modify this retained fixture.
"""

from contextlib import closing
from copy import deepcopy
from pathlib import Path
import sqlite3

import pytest

from app.physical_contract import byte_sha
from app.physical_joint_custody import accounting, audit_snapshot, dataset_inventory, result_inventory, scan_stream

ROOT = Path('E:/_Temp/m11cu5/test_actual_full_native_public0/case-0/private')
DATABASE_SHA = '30cf3f3e06649c98a2ce4810186e413582a428cf45e334a079f9e92621ece21b'


class RetainedFiles:
    """Portable immutable test bytes; no POSIX lease/durability grant."""
    def read(self, key, *, cap, expected_bytes, expected_sha256):
        path = ROOT/key
        assert path.stat().st_size <= cap
        body = path.read_bytes()
        assert len(body) == expected_bytes and byte_sha(body) == expected_sha256
        return body

    def scan_joint_member(self, key, **values):
        with (ROOT/key).open('rb') as stream:
            return scan_stream(stream, **values)


@pytest.fixture(scope='module')
def retained_rows():
    path = ROOT/'api.sqlite3'
    assert byte_sha(path.read_bytes()) == DATABASE_SHA
    assert not path.with_name('api.sqlite3-wal').exists()
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro&immutable=1', uri=True)) as connection:
        assert connection.execute('SELECT version_num FROM alembic_version').fetchall() == [('0006_joint_artifacts',)]
        rows = {}
        for table in ('source_records','raw_assets','observation_datasets','processing_jobs','joint_dataset_sources','joint_result_artifacts'):
            cursor = connection.execute('SELECT * FROM '+table)
            columns = [r[0] for r in cursor.description]
            rows[table] = [dict(zip(columns,r)) for r in cursor]
        assert len(rows['joint_dataset_sources']) == 36
        assert len(rows['joint_result_artifacts']) == 1097
        yield rows
    assert byte_sha(path.read_bytes()) == DATABASE_SHA


def test_original_structural_members_and_plan_bindings_without_any_fit(retained_rows):
    dataset = retained_rows['observation_datasets'][0]
    payload = dataset_inventory(retained_rows, RetainedFiles(), dataset)
    assert payload['scientific_accepted'] is False and payload['scientific_values_decoded'] is False
    assert sum(len(v) for v in payload['members'].values()) == 36


def test_original_failed_archival_index_and_every_native_copy_are_charged_once(retained_rows):
    job = retained_rows['processing_jobs'][0]
    assert job['state'] == 'failed' and job['error_code'] == 'custody_fixture_no_execution'
    payload, declared = result_inventory(retained_rows, RetainedFiles(), job)
    assert len(declared) == 1097 and payload['scientific_acceptance'] is False
    for key, rule in declared:
        RetainedFiles().scan_joint_member(key, byte_count=rule['bytes'], sha256=rule['sha256'], descriptor=None)
    assert sum(r['bytes'] for _,r in declared) == payload['native_bytes'] == 903644
    with closing(sqlite3.connect((ROOT/'api.sqlite3').as_uri()+'?mode=ro&immutable=1', uri=True)) as connection:
        connection.execute('BEGIN')
        charge = accounting(connection, job['owner_id'])
        assert charge == dict(joint_members=903644,joint_terminal_indices=151987,joint_active=0)
        assert sum(charge.values()) == 1055631
        assert connection.total_changes == 0 and connection.in_transaction


def test_complete_joint_declarations_have_no_hash_deduplication(retained_rows):
    snapshot = audit_snapshot(retained_rows, RetainedFiles())
    assert len(snapshot['files']) == 1099  # 1097 members + saved dataset + failed index.
    assert snapshot['index_ids'] == frozenset(r['id'] for r in retained_rows['processing_jobs'])


@pytest.mark.parametrize('damage', ['duplicate','foreign_owner','foreign_project','foreign_dataset','request','path','count','hash','orphan'])
def test_native_retained_row_substitution_is_not_a_positive_custody_reader(retained_rows, damage):
    rows = deepcopy(retained_rows)
    row = rows['joint_result_artifacts'][0]
    if damage == 'duplicate': rows['joint_result_artifacts'].append(dict(row))
    if damage == 'foreign_owner': row['owner_id'] = 'ffffffff-ffff-4fff-8fff-ffffffffffff'
    if damage == 'foreign_project': row['project_id'] = 'ffffffff-ffff-4fff-8fff-ffffffffffff'
    if damage == 'foreign_dataset': row['dataset_id'] = 'ffffffff-ffff-4fff-8fff-ffffffffffff'
    if damage == 'request': row['request_sha256'] = '0'*64
    if damage == 'path': row['storage_key'] = '../never-adopt.npy'
    if damage == 'count': row['byte_count'] += 1
    if damage == 'hash': row['sha256'] = '0'*64
    if damage == 'orphan': row['job_id'] = 'ffffffff-ffff-4fff-8fff-ffffffffffff'
    with pytest.raises(ValueError):
        audit_snapshot(rows, RetainedFiles())
