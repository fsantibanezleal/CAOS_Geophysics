"""Explicit current M08 trash member grammar; never rewrite historical v1."""

from copy import deepcopy
from uuid import uuid4

import pytest

from app.physical_contract import M, canonical, parse_record
from app.physical_current_custody import parse_current_custody, validate_current_custody


def inventory():
    job = str(uuid4())
    slot = dict(ordinal=1,role='result_copy',location='deleting_derived',artifact_id=job,
        leaf=f'waveforms/{job}/calculation.json',max_bytes=52690944,actual_bytes=20,actual_sha256='a'*64)
    project = str(uuid4())
    return dict(schema='geophysics.physical-custody/v2',batch_id=str(uuid4()),owner_id=str(uuid4()),
        project_id=project,origin_kind='project_deletion',origin_id=project,stage_id=None,
        deletion_receipt_id=str(uuid4()),raw_asset_id=None,raw_sha256=None,raw_bytes=None,
        parser_version=None,method_id=None,capacity_bytes=20,initial_files=[slot],removed_ordinals=[])


def test_current_m08_slot_is_explicit_without_mutating_frozen_v1_decoder():
    value = inventory()
    measured = validate_current_custody(value)
    assert measured['retained_bytes'] == 20
    assert parse_current_custody([canonical(value)]) == value
    with pytest.raises(ValueError): parse_record([canonical(value)])
    old = dict(value,schema='geophysics.physical-custody/v1')
    with pytest.raises(ValueError): parse_current_custody([canonical(old)])
    assert measured['initial_inventory_sha256'] == validate_current_custody(dict(value,removed_ordinals=[1]))['initial_inventory_sha256']


@pytest.mark.parametrize('damage',['schema','origin','owner','path','job','traversal','name','role','location','cap','unknown','duplicate','boolean','removed','capacity'])
def test_unknown_current_custody_does_not_acquire_positive_dispatch(damage):
    value = inventory()
    slot = value['initial_files'][0]
    if damage=='schema': value['schema']='geophysics.physical-custody/v3'
    elif damage=='origin': value['origin_kind']='root_stage'
    elif damage=='owner': value['owner_id']=False
    elif damage=='path': slot['leaf']='arbitrary/unowned.bin'
    elif damage=='job': slot['artifact_id']=str(uuid4())
    elif damage=='traversal': slot['leaf']=f"waveforms/{slot['artifact_id']}/../calculation.json"
    elif damage=='name': slot['leaf']=f"waveforms/{slot['artifact_id']}/future.bin"
    elif damage=='role': slot['role']='cache'; slot['artifact_id']=None
    elif damage=='location': slot['location']='stage'
    elif damage=='cap': slot['max_bytes']=1024*M
    elif damage=='unknown': slot['future']=0
    elif damage=='duplicate':
        value['initial_files'].append(deepcopy(slot)); value['initial_files'][1]['ordinal']=2; value['capacity_bytes']=40
    elif damage=='boolean': slot['ordinal']=True
    elif damage=='removed': value['removed_ordinals']=[2]
    else: value['capacity_bytes']=21
    with pytest.raises(ValueError): parse_current_custody([canonical(value)])


def test_duplicate_or_trailing_json_and_nonfinite_never_get_recanonicalized():
    body = canonical(inventory())
    for damaged in (body+b' {}',body[:-1]+b',"capacity_bytes":20}',body.replace(b'"actual_bytes":20',b'"actual_bytes":NaN')):
        with pytest.raises(ValueError): parse_current_custody([damaged])


def test_ordinary_v1_and_ordinary_slots_in_v2_preserve_original_rules():
    value = inventory()
    value['initial_files'][0]['leaf']=f"results/{value['initial_files'][0]['artifact_id']}.json"
    old=dict(value,schema='geophysics.physical-custody/v1')
    assert parse_current_custody([canonical(old)]) == parse_record([canonical(old)])
    assert validate_current_custody(value)['retained_bytes']==20


def joint_inventory():
    value = inventory()
    job = str(uuid4())
    value['schema']='geophysics.physical-custody/v3'
    value['initial_files'].append(dict(ordinal=2,role='result_copy',location='deleting_derived',
        artifact_id=job,leaf=f'joint/{job}/calibration/field.npy',max_bytes=256*M,
        actual_bytes=17,actual_sha256='b'*64))
    value['capacity_bytes']=37
    return value


def test_joint_schema_requires_a_real_closed_member_without_promoting_old_slots():
    value = joint_inventory()
    measured = validate_current_custody(value)
    assert measured['retained_bytes']==37
    assert parse_current_custody([canonical(value)])==value
    assert validate_current_custody(dict(value,removed_ordinals=[2]))['retained_bytes']==20
    for old in ('geophysics.physical-custody/v1','geophysics.physical-custody/v2'):
        with pytest.raises(ValueError): parse_current_custody([canonical(dict(value,schema=old))])
    without_joint=dict(value,initial_files=value['initial_files'][:1],capacity_bytes=20)
    with pytest.raises(ValueError,match='current_custody_joint_dispatch_required'):
        parse_current_custody([canonical(without_joint)])


@pytest.mark.parametrize('damage',['empty','uuid','method','name','path','role','location','zero','cap','hash','extra'])
def test_registered_joint_custody_does_not_accept_unknown_or_unbound_members(damage):
    value = joint_inventory()
    member=value['initial_files'][1]
    if damage=='empty': value.update(initial_files=[],capacity_bytes=1)
    elif damage=='uuid': member['artifact_id']=str(uuid4())
    elif damage=='method': member['leaf']=member['leaf'].replace('joint/','m03/',1)
    elif damage=='name': member['leaf']=member['leaf'].replace('field.npy','field.zip')
    elif damage=='path': member['leaf']=member['leaf'].replace('calibration/','calibration/../')
    elif damage=='role': member['role']='cache'
    elif damage=='location': member['location']='stage'
    elif damage=='zero': member['actual_bytes']=0;value['capacity_bytes']=20
    elif damage=='cap': member['max_bytes']=256*M+1
    elif damage=='hash': member['actual_sha256']='bad'
    else: member['source_id']=str(uuid4())
    with pytest.raises(ValueError): parse_current_custody([canonical(value)])
