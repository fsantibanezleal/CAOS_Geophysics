"""Fresh complete deleted-project classification, no HTTP/delete replacement."""

from copy import deepcopy
import json
from uuid import uuid4

import pytest

from app.physical_classifier import classify_snapshot
from app.physical_contract import M, byte_sha, canonical
from app.physical_deleted_inventory import save_current_tombstone
from tests.api.test_physical_classifier import CensusFiles
from tests.api.test_physical_deleted_inventory import POLICY, case
from tests.api.test_physical_forest import connect
from tests.ops.physical_sql_fixture import insert
from tests.api.test_physical_roots import root_case as root_case
from tests.api.test_physical_successor import successor as successor
from tests.api.test_physical_wire import survey as survey


def retired(root_case, *, extra_waveform=False):
    """Declared SQL/file cut fixture, NOT the production original DELETE."""
    inventory, receipt = case(root_case)
    path, files, values, body, original = root_case
    owner, project = values['owner_id'], values['project_id']
    rid, batch_id = str(uuid4()), str(uuid4())
    extras = []
    if extra_waveform:
        # Explicit compact-deleted structural control, NOT a numerical M08 job,
        # pre-delete producer proof or retrofit of a real project's receipts.
        from tests.api.test_physical_deleted_inventory import append_root
        dataset, mseed, xml, ms_source, xml_source, job = [str(uuid4()) for _ in range(6)]
        raw_body, xml_body, data_body, result_body, member_body = (
            b'compact declared mseed', b'compact declared xml', b'compact declared waveform dataset',
            b'compact declared waveform result', b'compact declared waveform member')
        append_root(inventory,receipt,identifier=dataset,raw_id=mseed,source_id=ms_source,
            raw_sha=byte_sha(raw_body),dataset_sha=byte_sha(data_body),count=len(raw_body),
            parser='m08/v1/'+'c'*64,modality='waveform_counts_response',schema='geophysics.waveform-dataset/v1')
        next(r for r in inventory['datasets'] if r['dataset_id']==dataset)['bytes']=len(data_body)
        next(r for r in receipt['derived_manifest'] if r.get('id')==dataset)['byte_count']=len(data_body)
        inventory['raw_assets'].append(dict(asset_id=xml,source_id=xml_source,sha256=byte_sha(xml_body),bytes=len(xml_body)))
        inventory['raw_assets'].sort(key=lambda r:r['asset_id'])
        receipt['asset_manifest'].append(dict(asset_id=xml,sha256=byte_sha(xml_body),byte_count=len(xml_body)))
        inventory['waveform_sources']=[dict(dataset_id=dataset,role=role,asset_id=asset,source_id=source,
            raw_sha256=byte_sha(payload),raw_bytes=len(payload),source_version=1)
            for role,asset,source,payload in [('miniseed',mseed,ms_source,raw_body),('stationxml',xml,xml_source,xml_body)]]
        inventory['jobs'].append(dict(job_id=job,dataset_id=dataset,dataset_sha256=byte_sha(data_body),
            method_id='seismic.waveform-qc-classical/v1',state='succeeded',request_sha256='a'*64,
            result_sha256=byte_sha(result_body),result_bytes=len(result_body),physical_fingerprint=None,
            physical_control_sha256=None,scientific_verdict=None))
        receipt['derived_manifest'].append(dict(kind='result',id=job,sha256=byte_sha(result_body),byte_count=len(result_body)))
        # Equal bytes/hashes for two members must still be two charged copies.
        for name in ('calculation.json','evaluation.json'):
            inventory['waveform_artifacts'].append(dict(job_id=job,name=name,sha256=byte_sha(member_body),bytes=len(member_body)))
            receipt['derived_manifest'].append(dict(kind='waveform_artifact',id=job,name=name,
                relative_path=f'waveforms/{job}/{name}',sha256=byte_sha(member_body),byte_count=len(member_body)))
        extras = [('raw_delete','deleting_raw',mseed,mseed,1024*M,raw_body),
                  ('raw_delete','deleting_raw',xml,xml,1024*M,xml_body),
                  ('dataset_copy','deleting_derived',dataset,f'datasets/{dataset}.json',64*M,data_body),
                  ('result_copy','deleting_derived',job,f'results/{job}.json',64*M,result_body)] + [
                  ('result_copy','deleting_derived',job,f'waveforms/{job}/{name}',52690944,member_body)
                  for name in ('calculation.json','evaluation.json')]
        for _,location,_,leaf,_,payload in extras:
            lane='projects' if location=='deleting_raw' else 'derived'
            target=files.root / f'{lane}/{owner}/{project}/{leaf}'
            target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(payload)
    deleting = files.root / '.deleting'
    deleting.mkdir()
    (files.root / f'projects/{owner}/{project}').rename(deleting / f'{owner}--{project}')
    (files.root / f'derived/{owner}/{project}').rename(deleting / f'{owner}--{project}--derived')
    # The closed census does not adopt unrecorded leftover empty parents.
    for lane in ('projects','derived'):
        (files.root / lane / owner).rmdir()
        (files.root / lane).rmdir()
    slots = [dict(ordinal=i,role=role,location=location,artifact_id=identifier,leaf=leaf,
                  max_bytes=cap,actual_bytes=len(payload),actual_sha256=byte_sha(payload))
        for i,(role,location,identifier,leaf,cap,payload) in enumerate([
            ('raw_delete','deleting_raw',values['raw_asset_id'],values['raw_asset_id'],1024*M,original),
            ('dataset_copy','deleting_derived',values['root_dataset_id'],f"datasets/{values['root_dataset_id']}.json",64*M,body),*extras],1)]
    inv = dict(schema='geophysics.physical-custody/v2' if extra_waveform else 'geophysics.physical-custody/v1',batch_id=batch_id,owner_id=owner,project_id=project,
        origin_kind='project_deletion',origin_id=project,stage_id=None,deletion_receipt_id=rid,
        raw_asset_id=None,raw_sha256=None,raw_bytes=None,parser_version=None,method_id=None,
        capacity_bytes=sum(s['actual_bytes'] for s in slots),initial_files=slots,removed_ordinals=[])
    from app.physical_current_custody import validate_current_custody
    charge = validate_current_custody(inv)
    inventory['custody'].append(dict(batch_id=batch_id,origin_kind='project_deletion',origin_id=project,
                                     initial_inventory_sha256=charge['initial_inventory_sha256']))
    inventory['custody'].sort(key=lambda row:row['batch_id'])
    with connect(path) as db:
        db.execute('BEGIN IMMEDIATE')
        insert(db,'physical_custody_batches',dict({k:v for k,v in inv.items() if k not in ('schema','initial_files','removed_ordinals')},
            state='cleanup_pending',charged_bytes=charge['retained_bytes'],inventory_bytes=canonical(inv),
            inventory_sha256=byte_sha(canonical(inv)),created_us=3,sealed_us=4,removed_us=None))
        for slot in slots: insert(db,'physical_custody_files',dict(slot,batch_id=batch_id,state='present'))
        db.execute('DELETE FROM observation_datasets')
        db.execute('DELETE FROM physical_dataset_families')
        db.execute('DELETE FROM raw_assets')
        db.execute('DELETE FROM source_records')
        db.execute('DELETE FROM projects')
        db.execute('UPDATE account_usage SET raw_bytes=0')
        insert(db,'deletion_receipts',dict(id=rid,owner_id=owner,project_id=project,deleted_at='2026-10-08 13:00:00',
            backup_purge_status='not_attempted',asset_hashes=json.dumps([r['sha256'] for r in receipt['asset_manifest']]),
            asset_manifest=json.dumps(receipt['asset_manifest'],indent=1),derived_manifest=json.dumps(receipt['derived_manifest'],indent=2)))
        save_current_tombstone(db,receipt_id=rid,inventory=inventory,expected_source_policy_sha256=POLICY,approved_installations={})
        db.commit()
    return path,files,values,rid,batch_id,inv


def classified(path,files,policy=POLICY):
    with connect(path) as db:
        db.execute('BEGIN IMMEDIATE')
        before=db.total_changes
        result=classify_snapshot(db,CensusFiles(files),approved_manifests={},approved_installations={},
                                native_metadata={},expected_source_policy_sha256=policy)
        assert db.total_changes==before and db.in_transaction
        db.rollback()
    return result


def test_complete_deleted_project_preserves_literal_stage_and_original_deletion_debt(root_case):
    path,files,values,rid,batch_id,inv=retired(root_case)
    result=classified(path,files)
    assert result.classification=='coherent_committed',result.reason
    assert result.operations[rid]=='retain_deleted_projection'
    assert result.operations[batch_id]=='retain_debt'
    charges=result.account_charges[values['owner_id']]
    assert charges['raw']==charges['datasets']==charges['results']==0
    assert charges['custody']==2*sum(s['actual_bytes'] for s in inv['initial_files'])
    assert result.runtime is False


@pytest.mark.parametrize('damage',['policy','native-receipt','missing-debt','extra-debt','hash','missing-file','alternate-directory','reappeared','live-project'])
def test_deleted_classifier_never_adopts_or_drops_retained_partitions(root_case,damage):
    path,files,values,rid,batch_id,inv=retired(root_case)
    if damage=='policy': policy='a'*64
    else: policy=POLICY
    if damage=='missing-file':
        (files.root / f".deleting/{values['owner_id']}--{values['project_id']}/{values['raw_asset_id']}").unlink()
    elif damage=='alternate-directory':
        alternate=files.root/'.deleting-derived'; alternate.mkdir()
        (files.root / f".deleting/{values['owner_id']}--{values['project_id']}--derived").rename(
            alternate / f"{values['owner_id']}--{values['project_id']}")
    with connect(path) as db:
        if damage=='native-receipt': db.execute("UPDATE deletion_receipts SET asset_manifest=asset_manifest||' '")
        elif damage=='missing-debt':
            db.execute('DELETE FROM physical_custody_files WHERE batch_id=?',(batch_id,))
            db.execute('DELETE FROM physical_custody_batches WHERE batch_id=?',(batch_id,))
        elif damage=='extra-debt':
            row=deepcopy(inv); row['batch_id']=str(uuid4()); row['origin_id']=str(uuid4())
            insert(db,'physical_custody_batches',dict({k:v for k,v in row.items() if k not in ('schema','initial_files','removed_ordinals')},
                state='cleanup_pending',charged_bytes=sum(s['actual_bytes'] for s in row['initial_files']),inventory_bytes=canonical(row),
                inventory_sha256=byte_sha(canonical(row)),created_us=3,sealed_us=4,removed_us=None))
        elif damage=='hash': db.execute("UPDATE physical_deletion_extensions SET tombstone_sha256=?",('a'*64,))
        elif damage=='live-project':
            insert(db,'projects',dict(id=values['project_id'],owner_id=values['owner_id'],name='Never resurrect',description='',
                created_at='2026-10-08 13:00:00',updated_at='2026-10-08 13:00:00'))
        elif damage=='reappeared':
            row=deepcopy(inv); row['removed_ordinals']=[1]
            db.execute('UPDATE physical_custody_batches SET inventory_bytes=?,inventory_sha256=?,charged_bytes=? WHERE batch_id=?',
                (canonical(row),byte_sha(canonical(row)),row['initial_files'][1]['actual_bytes'],batch_id))
            db.execute("UPDATE physical_custody_files SET state='removed' WHERE batch_id=? AND ordinal=1",(batch_id,))
        db.commit()
    result=classified(path,files,policy)
    assert result.classification=='inconsistent' and not result.operations and not result.account_charges
    assert result.inventory_sha256 is None


def test_no_independent_policy_never_uses_embedded_policy_as_authority(root_case):
    path,files,_,_,_,_=retired(root_case)
    result=classified(path,files,None)
    assert result.classification=='inconsistent' and not result.operations


def test_recorded_removed_ordinal_preserves_initial_inventory_and_other_literal_copies(root_case):
    path,files,values,_,batch_id,inv=retired(root_case)
    (files.root / f".deleting/{values['owner_id']}--{values['project_id']}/{values['raw_asset_id']}").unlink()
    # Explicit fixture of already acknowledged removal. No production durability
    # is inferred from Python unlink or absent names in this portable test.
    row=deepcopy(inv); row['removed_ordinals']=[1]
    with connect(path) as db:
        db.execute('UPDATE physical_custody_batches SET inventory_bytes=?,inventory_sha256=?,charged_bytes=? WHERE batch_id=?',
            (canonical(row),byte_sha(canonical(row)),row['initial_files'][1]['actual_bytes'],batch_id))
        db.execute("UPDATE physical_custody_files SET state='removed' WHERE batch_id=? AND ordinal=1",(batch_id,))
        db.commit()
    result=classified(path,files)
    assert result.classification=='coherent_committed',result.reason
    assert result.account_charges[values['owner_id']]['custody']==(
        sum(s['actual_bytes'] for s in inv['initial_files'])+inv['initial_files'][1]['actual_bytes'])


@pytest.mark.parametrize('damage',[None,'missing','wrong-name','missing-row','wrong-owner','v1','initial-inventory'])
def test_m08_named_member_trash_binds_complete_deleted_projection_without_dedup(root_case,damage):
    path,files,values,_,batch_id,inv=retired(root_case,extra_waveform=True)
    if damage=='missing':
        (files.root / f".deleting/{values['owner_id']}--{values['project_id']}--derived/{inv['initial_files'][-1]['leaf']}").unlink()
    with connect(path) as db:
        if damage in ('wrong-name','v1','initial-inventory'):
            row=deepcopy(inv)
            if damage=='wrong-name': row['initial_files'][-1]['leaf']=row['initial_files'][-1]['leaf'].replace('evaluation.json','manifest.json')
            elif damage=='v1': row['schema']='geophysics.physical-custody/v1'
            else: row['initial_files'][-1]['actual_sha256']='f'*64
            db.execute('UPDATE physical_custody_batches SET inventory_bytes=?,inventory_sha256=? WHERE batch_id=?',
                       (canonical(row),byte_sha(canonical(row)),batch_id))
        elif damage=='missing-row':
            db.execute('DELETE FROM physical_custody_files WHERE batch_id=? AND ordinal=?',(batch_id,inv['initial_files'][-1]['ordinal']))
        elif damage=='wrong-owner':
            db.execute('UPDATE physical_custody_batches SET project_id=? WHERE batch_id=?',(str(uuid4()),batch_id))
        db.commit()
    result=classified(path,files)
    if damage is None:
        assert result.classification=='coherent_committed',result.reason
        assert result.account_charges[values['owner_id']]['custody']==sum(s['actual_bytes'] for s in inv['initial_files'])+len(root_case[3])+len(root_case[4])
    else:
        assert result.classification=='inconsistent' and not result.operations and result.inventory_sha256 is None
