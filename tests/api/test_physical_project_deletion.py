"""Original native TX hooks and exact precommit partitions, not HTTP acceptance."""

from copy import deepcopy
import json
from uuid import uuid4

import pytest
from alembic import command

from app.physical_classifier import classify_snapshot
from app.physical_contract import byte_sha, canonical
from app.physical_project_deletion import (
    prepare_project_deletion,retire_project_forest_relations,
    retire_project_forest_families,transfer_project_deletion,
)
from tests.api.test_physical_classifier import CensusFiles
from tests.api.test_physical_deleted_inventory import POLICY,case
from tests.api.test_physical_forest import connect
from tests.api.test_physical_roots import root_case as root_case
from tests.api.test_physical_successor import successor as successor
from tests.api.test_physical_wire import survey as survey
from tests.ops.physical_union_fixture import capsule


def classified(db,files):
    before=db.total_changes
    result=classify_snapshot(db,CensusFiles(files),approved_manifests={},approved_installations={},
                            native_metadata={},expected_source_policy_sha256=POLICY)
    assert db.total_changes==before and db.in_transaction
    return result


def test_classifier_initializes_relocation_before_any_declared_native_metadata(root_case):
    case(root_case)
    files=root_case[1]
    name='.physical-writers.lock'
    (files.root/name).write_bytes(b'\0')
    rule={name:dict(cap=1,bytes=1,sha256=byte_sha(b'\0'),required=True)}
    with connect(root_case[0]) as db:
        db.execute('BEGIN IMMEDIATE')
        result=classify_snapshot(db,CensusFiles(files),approved_manifests={},approved_installations={},
            native_metadata=rule,expected_source_policy_sha256=POLICY)
        assert result.classification=='coherent_committed',result.reason
        assert result.runtime is False
        db.rollback()


def prepared(root_case, revision=None, monkeypatch=None):
    case(root_case)
    path,files,values,*_=root_case
    if revision is not None and revision != '0005_physical_forest':
        config, _ = capsule(path.parent/'allocated-union')
        monkeypatch.setenv('GEOPHYSICS_DB_PATH', str(path))
        monkeypatch.setenv('GEOPHYSICS_CANDIDATE_ROOT', str(path.parent))
        command.upgrade(config, revision)
    with connect(path) as db:
        db.execute('BEGIN IMMEDIATE')
        original=classified(db,files)
        assert original.classification=='coherent_committed',original.reason
        plan=prepare_project_deletion(db,files=CensusFiles(files),owner_id=values['owner_id'],project_id=values['project_id'],
            batch_id=str(uuid4()),receipt_id=str(uuid4()),created_us=7,expected_source_policy_sha256=POLICY,
            approved_manifests={},approved_installations={},native_metadata={},profile_records=[])
        assert db.in_transaction
        assert db.execute('SELECT count(*) FROM deletion_receipts').fetchone()==(0,)
        db.commit()
    return plan,dict(original.account_charges[values['owner_id']])


def move(root_case,raw,derived):
    _,files,values,*_=root_case
    if raw or derived: (files.root/'.deleting').mkdir(exist_ok=True)
    for lane,enabled,suffix in [('projects',raw,''),('derived',derived,'--derived')]:
        if enabled:
            (files.root/f"{lane}/{values['owner_id']}/{values['project_id']}").rename(
                files.root/f".deleting/{values['owner_id']}--{values['project_id']}{suffix}")


@pytest.mark.parametrize('raw,derived',[(False,False),(True,False),(False,True),(True,True)])
def test_durable_precommit_original_or_moved_partition_is_abandon_only_and_charged_once(root_case,raw,derived):
    plan,charge=prepared(root_case)
    move(root_case,raw,derived)
    with connect(root_case[0]) as db:
        db.execute('BEGIN IMMEDIATE')
        result=classified(db,root_case[1])
        assert result.classification=='prepared_uncommitted',result.reason
        assert result.operations[plan['custody']['batch_id']]=='abandon_only'
        assert dict(result.account_charges[root_case[2]['owner_id']])==charge
        assert db.execute('SELECT charged_bytes FROM physical_custody_batches WHERE batch_id=?',
                          (plan['custody']['batch_id'],)).fetchone()==(0,)
        assert db.execute('SELECT count(*) FROM projects').fetchone()==(1,)
        assert result.runtime is False
        db.rollback()


@pytest.mark.parametrize('damage',['duplicate','missing','file','slot','charge','receipt','foreign-owner','omitted','extra'])
def test_precommit_unknown_partition_never_authorizes_restoration_or_uncharge(root_case,damage):
    plan,_=prepared(root_case)
    move(root_case,True,True)
    values=root_case[2]; files=root_case[1]
    target=files.root/f".deleting/{values['owner_id']}--{values['project_id']}/{values['raw_asset_id']}"
    if damage=='duplicate':
        duplicate=files.root/f"projects/{values['owner_id']}/{values['project_id']}/{values['raw_asset_id']}"
        duplicate.parent.mkdir(); duplicate.write_bytes(target.read_bytes())
    elif damage=='missing': target.unlink()
    elif damage=='file': target.write_bytes(b'unknown changed bytes')
    elif damage=='extra': (target.parent/'unknown').write_bytes(b'never sweep')
    with connect(root_case[0]) as db:
        if damage=='charge': db.execute('UPDATE physical_custody_batches SET charged_bytes=1 WHERE batch_id=?',(plan['custody']['batch_id'],))
        elif damage=='receipt':
            db.execute('INSERT INTO deletion_receipts(id,owner_id,project_id,deleted_at,asset_hashes,asset_manifest,derived_manifest,backup_purge_status) VALUES(?,?,?,?,?,?,?,?)',
                (plan['custody']['deletion_receipt_id'],values['owner_id'],values['project_id'],'2026-10-08 13:00:00','[]','[]','[]','not_attempted'))
        elif damage in ('slot','foreign-owner','omitted'):
            inv=deepcopy(plan['custody'])
            if damage=='slot': inv['initial_files'][0]['leaf']=str(uuid4())
            elif damage=='foreign-owner': inv['owner_id']=str(uuid4())
            else:
                inv['initial_files'].pop(); inv['capacity_bytes']=max(1,sum(s['actual_bytes'] for s in inv['initial_files']))
            db.execute('UPDATE physical_custody_batches SET inventory_bytes=?,inventory_sha256=? WHERE batch_id=?',
                       (canonical(inv),byte_sha(canonical(inv)),plan['custody']['batch_id']))
        db.commit(); db.execute('BEGIN IMMEDIATE')
        result=classified(db,files)
        assert result.classification=='inconsistent' and not result.operations and not result.account_charges
        assert db.execute('SELECT count(*) FROM projects').fetchone()==(1,)
        db.rollback()


@pytest.mark.parametrize('commit',[False,True])
@pytest.mark.parametrize('revision', ['0005_physical_forest', '0006_joint_artifacts', '0007_magnetic_line_artifacts'])
def test_existing_native_receipt_row_removal_and_retained_debt_share_one_caller_commit(root_case,commit,revision,monkeypatch):
    plan,charge=prepared(root_case,revision,monkeypatch)
    move(root_case,True,True)
    values=root_case[2]; inventory=plan['inventory']; custody=plan['custody']
    raw=[dict(asset_id=r['asset_id'],sha256=r['sha256'],byte_count=r['bytes']) for r in inventory['raw_assets']]
    derived=[dict(kind='dataset',id=r['dataset_id'],sha256=r['sha256'],byte_count=r['bytes']) for r in inventory['datasets']]
    serialized=[json.dumps([r['sha256'] for r in raw]),json.dumps(raw,indent=1),json.dumps(derived,indent=2)]
    with connect(root_case[0]) as db:
        db.execute('BEGIN IMMEDIATE')
        retire_project_forest_relations(db,owner_id=values['owner_id'],project_id=values['project_id'])
        db.execute('DELETE FROM processing_jobs WHERE project_id=?',(values['project_id'],))
        db.execute('DELETE FROM observation_datasets WHERE project_id=?',(values['project_id'],))
        retire_project_forest_families(db,owner_id=values['owner_id'],project_id=values['project_id'])
        for table in ('raw_assets','source_records','projects'):
            key='id' if table=='projects' else 'project_id'
            db.execute(f'DELETE FROM {table} WHERE {key}=?',(values['project_id'],))
        db.execute('UPDATE account_usage SET raw_bytes=0 WHERE user_id=?',(values['owner_id'],))
        db.execute('INSERT INTO deletion_receipts(id,owner_id,project_id,deleted_at,asset_hashes,asset_manifest,derived_manifest,backup_purge_status) VALUES(?,?,?,?,?,?,?,?)',
            (custody['deletion_receipt_id'],values['owner_id'],values['project_id'],'2026-10-08 13:00:00',*serialized,'not_attempted'))
        body=transfer_project_deletion(db,inventory=inventory,custody=custody,expected_source_policy_sha256=POLICY,approved_installations={})
        assert json.loads(body)['origin_revision'] == revision
        assert [json.loads(body)['legacy_receipt'][k]['utf8'] for k in ('asset_hashes','asset_manifest','derived_manifest')]==serialized
        assert db.in_transaction and not db.execute('PRAGMA foreign_key_check').fetchall()
        if commit: db.commit()
        else: db.rollback()
        db.execute('BEGIN IMMEDIATE')
        result=classified(db,root_case[1])
        assert result.classification==('coherent_committed' if commit else 'prepared_uncommitted'),result.reason
        if commit:
            actual=result.account_charges[values['owner_id']]
            assert actual['raw']==actual['datasets']==actual['results']==0
            assert actual['custody']==charge['custody']+sum(s['actual_bytes'] for s in custody['initial_files'])
            assert actual['total']==charge['total']
        else: assert dict(result.account_charges[values['owner_id']])==charge
        db.rollback()
