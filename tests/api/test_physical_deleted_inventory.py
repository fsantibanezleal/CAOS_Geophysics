"""Current source-positive deletion data; old frozen decoder stays unchanged."""

from copy import deepcopy

import pytest

from app.physical_deleted_inventory import project_inventory, validate_current_inventory
from app.physical_deleted_inventory import observe_receipt, validate_current_tombstone, save_current_tombstone
from app.physical_contract import byte_sha
from app.physical_roots import prepare_root, publish_root
from tests.api.test_physical_forest import connect
from tests.api.test_physical_roots import root_case as root_case, install_fixture, publish_values
from tests.api.test_physical_successor import successor as successor
from tests.api.test_physical_wire import survey as survey


POLICY = 'e'*64  # Explicit supplied fixture policy, not operator approval.


def case(root_case):
    path, files, values, body, _ = root_case
    with connect(path) as db:
        prepare_root(db, files, **values)
        install_fixture(files, values, body)
        publish_root(db, files, **publish_values(values))
        db.execute('BEGIN IMMEDIATE')
        inventory = project_inventory(db, owner_id=values['owner_id'], project_id=values['project_id'],
            source_policy_sha256=POLICY, profile_records=[])
        raw = db.execute('SELECT id,sha256,byte_count FROM raw_assets').fetchall()
        derived = db.execute('SELECT id,sha256,byte_count FROM observation_datasets').fetchall()
        receipt = dict(owner_id=values['owner_id'], project_id=values['project_id'],
            asset_manifest=[dict(asset_id=i,sha256=h,byte_count=n) for i,h,n in raw],
            derived_manifest=[dict(kind='dataset',id=i,sha256=h,byte_count=n) for i,h,n in derived])
        db.rollback()
    return inventory, receipt


def test_whole_current_inventory_projects_original_receipt_without_physics_replay(root_case):
    inventory, receipt = case(root_case)
    assert validate_current_inventory(inventory, receipt, expected_source_policy_sha256=POLICY,
                                      approved_installations={}) is None
    assert inventory['schema'] == 'geophysics.physical-deleted-inventory/v1'
    assert len(inventory['raw_assets']) == len(inventory['datasets']) == len(inventory['custody']) == 1


@pytest.mark.parametrize('damage', ['policy','raw','dataset','source','custody','future','receipt','duplicate'])
def test_deleted_projection_unknown_or_missing_never_grants_custody(root_case, damage):
    inventory, receipt = case(root_case)
    before = deepcopy(inventory)
    if damage == 'policy': inventory['source_policy_sha256'] = 'a'*64
    elif damage == 'raw': inventory['raw_assets'][0]['sha256'] = 'a'*64
    elif damage == 'dataset': inventory['datasets'][0]['root_dataset_id'] = inventory['raw_assets'][0]['asset_id']
    elif damage == 'source': inventory['raw_assets'][0]['source_id'] = False
    elif damage == 'custody': inventory['custody'][0]['initial_inventory_sha256'] = False
    elif damage == 'future': inventory['extra'] = 'do not skip unknown'
    elif damage == 'duplicate': inventory['datasets'].append(deepcopy(inventory['datasets'][0]))
    else: receipt['derived_manifest'][0]['sha256'] = byte_sha(b'changed')
    with pytest.raises(ValueError):
        validate_current_inventory(inventory, receipt, expected_source_policy_sha256=POLICY,
                                   approved_installations={})
    assert before['schema'] == inventory['schema']


def deleted_case(root_case):
    import json
    from uuid import uuid4
    inventory, receipt = case(root_case)
    path = root_case[0]
    receipt_id = str(uuid4())
    with connect(path) as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('DELETE FROM observation_datasets')
        db.execute('DELETE FROM physical_dataset_families')
        db.execute('DELETE FROM raw_assets')
        db.execute('DELETE FROM source_records')
        db.execute('DELETE FROM projects')
        db.execute('UPDATE account_usage SET raw_bytes=0')
        native = [json.dumps([r['sha256'] for r in receipt['asset_manifest']],ensure_ascii=False),
                  json.dumps(receipt['asset_manifest'],ensure_ascii=False,indent=1),
                  json.dumps(receipt['derived_manifest'],ensure_ascii=False,indent=2)]
        db.execute('''INSERT INTO deletion_receipts(id,owner_id,project_id,deleted_at,
            backup_purge_status,asset_hashes,asset_manifest,derived_manifest) VALUES(?,?,?,?,?,?,?,?)''',
            (receipt_id,receipt['owner_id'],receipt['project_id'],'2026-10-08 13:00:00','not_attempted',*native))
        body=save_current_tombstone(db,receipt_id=receipt_id,inventory=inventory,
            expected_source_policy_sha256=POLICY,approved_installations={})
        assert db.in_transaction
        observed=observe_receipt(db,receipt_id)
        assert [observed[k]['utf8'] for k in ('asset_hashes','asset_manifest','derived_manifest')]==native
        db.commit()
    return path,receipt_id,body


def test_native_receipt_serialization_and_extension_co_commit_are_preserved(root_case):
    import json
    path,receipt_id,body=deleted_case(root_case)
    receipt=validate_current_tombstone(json.loads(body),expected_source_policy_sha256=POLICY,approved_installations={})
    assert receipt['id']==receipt_id
    with connect(path) as db:
        assert db.execute('SELECT count(*) FROM projects').fetchone()==(0,)
        assert db.execute('SELECT tombstone_bytes,tombstone_sha256 FROM physical_deletion_extensions').fetchone()==(body,byte_sha(body))
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]


@pytest.mark.parametrize('damage',['native-json','descriptor','revision','owner','inventory','future'])
def test_current_extension_never_recanonicalizes_or_adopts_foreign_receipt(root_case,damage):
    import json
    _,_,body=deleted_case(root_case)
    value=json.loads(body)
    if damage=='native-json': value['legacy_receipt']['asset_manifest']['utf8']+=' '
    elif damage=='descriptor': value['legacy_receipt']['asset_manifest']['sha256']='a'*64
    elif damage=='revision': value['origin_revision']='0004_physical_persistence'
    elif damage=='owner': value['owner_id']=value['project_id']
    elif damage=='inventory': value['physical_inventory']['source_policy_sha256']='a'*64
    else: value['future']='never skip'
    with pytest.raises(ValueError):
        validate_current_tombstone(value,expected_source_policy_sha256=POLICY,approved_installations={})


def append_root(inventory, receipt, *, identifier, raw_id, source_id, raw_sha, dataset_sha,
                parser, modality, schema, count=20):
    inventory['raw_assets'].append(dict(asset_id=raw_id,source_id=source_id,sha256=raw_sha,bytes=count))
    inventory['datasets'].append(dict(dataset_id=identifier,raw_asset_id=raw_id,root_dataset_id=identifier,
        parent_dataset_id=None,version=1,parser_version=parser,kind='root',modality=modality,payload_schema=schema,
        sha256=dataset_sha,bytes=100))
    receipt['asset_manifest'].append(dict(asset_id=raw_id,sha256=raw_sha,byte_count=count))
    receipt['derived_manifest'].append(dict(kind='dataset',id=identifier,sha256=dataset_sha,byte_count=100))
    inventory['raw_assets'].sort(key=lambda row:row['asset_id'])
    inventory['datasets'].sort(key=lambda row:row['dataset_id'])


@pytest.mark.parametrize('damage',[None,'pair','source','future-parser','unknown-artifact'])
def test_current_m08_pair_is_positive_registry_not_a_future_fallback(root_case,damage):
    from uuid import uuid4
    inventory, receipt=case(root_case)
    dataset, mseed, xml, ms_source, xml_source=[str(uuid4()) for _ in range(5)]
    append_root(inventory,receipt,identifier=dataset,raw_id=mseed,source_id=ms_source,raw_sha='a'*64,dataset_sha='b'*64,
        parser='m08/v1/'+'c'*64,modality='waveform_counts_response',schema='geophysics.waveform-dataset/v1')
    inventory['raw_assets'].append(dict(asset_id=xml,source_id=xml_source,sha256='d'*64,bytes=30))
    inventory['raw_assets'].sort(key=lambda row:row['asset_id'])
    receipt['asset_manifest'].append(dict(asset_id=xml,sha256='d'*64,byte_count=30))
    inventory['waveform_sources']=[dict(dataset_id=dataset,role=role,asset_id=asset,source_id=source,
        raw_sha256=h,raw_bytes=n,source_version=1) for role,asset,source,h,n in
        [('miniseed',mseed,ms_source,'a'*64,20),('stationxml',xml,xml_source,'d'*64,30)]]
    if damage=='pair': inventory['waveform_sources'].pop()
    elif damage=='source': inventory['waveform_sources'][1]['source_id']=ms_source
    elif damage=='future-parser':
        next(r for r in inventory['datasets'] if r['dataset_id']==dataset)['parser_version']='m09/v1/'+'c'*64
    elif damage=='unknown-artifact':
        inventory['waveform_artifacts']=[dict(job_id=str(uuid4()),name='unknown.bin',sha256='a'*64,bytes=20)]
    if damage is None:
        validate_current_inventory(inventory,receipt,expected_source_policy_sha256=POLICY,approved_installations={})
    else:
        with pytest.raises(ValueError):
            validate_current_inventory(inventory,receipt,expected_source_policy_sha256=POLICY,approved_installations={})


@pytest.mark.parametrize('damage',[None,'nested-owner','raw-source','state','missing-receipt','unknown-entry'])
def test_nested_eleven_archive_binds_full_deleted_job_dataset_raw_relation(root_case,tmp_path,damage):
    from tests.api.test_profile_archive_custody import archive_fixture
    from app.profile_archive_custody import retained_inventory
    inventory, receipt=case(root_case)
    _,relation,_,installation,_=archive_fixture(tmp_path/'seed')
    relation.update(owner_id=receipt['owner_id'],project_id=receipt['project_id'])
    files,relation,_,installation,_=archive_fixture(tmp_path/'owned',declared_relation=relation,declared_installation=installation)
    approved={relation['id']:installation}
    records=retained_inventory(files,[relation],[],approved_installations=approved)
    append_root(inventory,receipt,identifier=relation['dataset_id'],raw_id=relation['raw_asset_id'],
        source_id=relation['source_id'],raw_sha=relation['raw_sha256'],dataset_sha=relation['dataset_sha256'],
        parser='supplied-profile-original/v1',modality='ert_profile',schema='geophysics.observation-dataset/v1')
    inventory['jobs'].append(dict(job_id=relation['id'],dataset_id=relation['dataset_id'],dataset_sha256=relation['dataset_sha256'],
        method_id=relation['method_id'],state=relation['state'],request_sha256=relation['request_sha256'],
        result_sha256=None,result_bytes=None,physical_fingerprint=None,physical_control_sha256=None,scientific_verdict=None))
    inventory['profile_archives']=records
    receipt['derived_manifest']+=deepcopy(records)
    if damage=='nested-owner': inventory['profile_archives'][0]['manifest']['ownership']['owner_id']=relation['project_id']
    elif damage=='raw-source': next(r for r in inventory['raw_assets'] if r['asset_id']==relation['raw_asset_id'])['source_id']=relation['project_id']
    elif damage=='state': inventory['jobs'][0]['state']='failed'
    elif damage=='missing-receipt': receipt['derived_manifest'].pop()
    elif damage=='unknown-entry': receipt['derived_manifest'].append({'schema':'future-custody','bytes':1})
    if damage is None:
        validate_current_inventory(inventory,receipt,expected_source_policy_sha256=POLICY,approved_installations=approved)
    else:
        with pytest.raises(ValueError):
            validate_current_inventory(inventory,receipt,expected_source_policy_sha256=POLICY,approved_installations=approved)
