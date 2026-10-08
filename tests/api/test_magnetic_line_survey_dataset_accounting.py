"""Genuine cookie intake and SQL quota negatives; no native execution grant."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import select

from app.errors import ApiError
from app.magnetic_line_survey_dataset_accounting import (
    INSPECTION_BYTES,account_dataset_usage,dataset_attempt_root,exact_next_phase,reserve_dataset_inspection,
    reserve_dataset_preparation,CSV_COLUMNS,
)
from app.magnetic_line_survey_models import SurveyDatasetAttempt
from app.magnetic_line_survey_wire import parse_survey_dataset
from app.models import AccountUsage,ObservationDataset,ProcessingJob,User
from tests.api.test_magnetic_line_survey_intake import install,upload,header


def inputs(harness,project):
    assets=[]
    for role,body in [('original_csv',b'non-scientific original quota control'),('metadata_json',b'{}'),('request_json',b'{}')]:
        response=upload(harness,project,body,header(body,role));assert response.status_code==201,response.text
        assets.append(response.json())
    from app.processing_contract import canonical_bytes
    return parse_survey_dataset(canonical_bytes(dict(schema='m03-owner-dataset-request/1',
        original_asset_id=assets[0]['asset_id'],original_sha256=assets[0]['sha256'],
        metadata_asset_id=assets[1]['asset_id'],metadata_sha256=assets[1]['sha256'],
        request_asset_id=assets[2]['asset_id'],request_sha256=assets[2]['sha256'],auxiliary_asset_ids=[],auxiliary_sha256=[])))


async def table(harness):
    async with harness.app.state.sessions() as session:
        connection=await session.connection()
        await connection.run_sync(lambda conn:SurveyDatasetAttempt.__table__.create(conn))
        await session.commit()


async def control_ledger(session,owner):
    # Complete for this isolated control: no jobs, no exports, no other methods.
    assert not (await session.execute(select(ProcessingJob.id))).first()
    assert not (await session.execute(select(ObservationDataset.id))).first()
    usage=await session.get(AccountUsage,owner)
    return usage.raw_bytes if usage else 0


async def no_other_device_work(session):
    assert not (await session.execute(select(ProcessingJob.id))).first()
    return 0


def test_real_default_claim_is_visible_before_any_namespace(make_harness):
    harness=make_harness();install(harness);owner=UUID(harness.account()['id']);project=UUID(harness.project()['id'])
    request=inputs(harness,str(project));asyncio.run(table(harness))
    async def run():
        async with harness.app.state.sessions() as session:
            user=await session.get(User,owner)
            row=await reserve_dataset_inspection(session,harness.settings,user,project,request,'b'*64,control_ledger,no_other_device_work)
            assert row.state=='reserved' and row.reservation_bytes==INSPECTION_BYTES
            assert not dataset_attempt_root(harness.settings,row.id).exists()
            async with harness.app.state.sessions() as other:
                observed=await other.get(SurveyDatasetAttempt,row.id)
                assert observed.state=='reserved' and await account_dataset_usage(other,owner)==INSPECTION_BYTES
            # Explicit test-only SHA is a SQL claim control, not installed authority.
    asyncio.run(run())


def test_actual_one_byte_deficit_refuses_before_claim_or_allocation(make_harness):
    harness=make_harness();install(harness);owner=UUID(harness.account()['id']);project=UUID(harness.project()['id'])
    request=inputs(harness,str(project));asyncio.run(table(harness))
    async def run():
        async with harness.app.state.sessions() as session:
            raw=await control_ledger(session,owner)
            settings=replace(harness.settings,max_upload_bytes=1024**2,account_quota_bytes=raw+INSPECTION_BYTES-1)
            user=await session.get(User,owner)
            with pytest.raises(ApiError) as error:
                await reserve_dataset_inspection(session,settings,user,project,request,'b'*64,control_ledger,no_other_device_work)
            assert error.value.code=='account_quota_exceeded'
            await session.rollback()
            assert not (await session.execute(select(SurveyDatasetAttempt.id))).first()
            assert not (Path(settings.data_dir)/'.m03-datasets').exists()
    asyncio.run(run())


@pytest.mark.parametrize('bad',['missing','boolean','negative'])
def test_unknown_complete_ledger_cannot_allocate(make_harness,bad):
    harness=make_harness();install(harness);owner=UUID(harness.account()['id']);project=UUID(harness.project()['id'])
    request=inputs(harness,str(project));asyncio.run(table(harness))
    async def wrong(session,owner):return True if bad=='boolean' else -1
    async def run():
        async with harness.app.state.sessions() as session:
            user=await session.get(User,owner)
            with pytest.raises(ApiError):
                await reserve_dataset_inspection(session,harness.settings,user,project,request,'b'*64,
                    None if bad=='missing' else wrong,no_other_device_work)
            await session.rollback()
            assert not (await session.execute(select(SurveyDatasetAttempt.id))).first()
            assert not (Path(harness.settings.data_dir)/'.m03-datasets').exists()
    asyncio.run(run())


def test_independent_actual_phase_equation_and_strict_types():
    proof=exact_next_phase(363,79507,69)
    assert proof['scratch_bound_bytes']==158504595
    assert proof['dataset_reservation_bytes']==177378963<1024**3
    for shape in [(True,79507,69),(363,True,69),(363,79507,True),(8000000,79507,69),(363,55,1)]:
        with pytest.raises(ApiError):exact_next_phase(*shape)


def test_closed_dataset_request_no_path_coercion_duplicate_or_mutable_bypass():
    from app.processing_contract import canonical_bytes
    request=dict(schema='m03-owner-dataset-request/1',original_asset_id=str(UUID(int=1)),original_sha256='a'*64,
        metadata_asset_id=str(UUID(int=2)),metadata_sha256='b'*64,request_asset_id=str(UUID(int=3)),request_sha256='c'*64,
        auxiliary_asset_ids=[str(UUID(int=4))],auxiliary_sha256=['d'*64])
    assert parse_survey_dataset(canonical_bytes(request)).model_dump(mode='json',by_alias=True)==request
    cases=[{**request,'path':'hidden'},{**request,'original_sha256':'A'*64},{**request,'auxiliary_sha256':[]},
        {**request,'request_asset_id':request['original_asset_id']},{**request,'original_asset_id':1}]
    for case in cases:
        with pytest.raises(ApiError):parse_survey_dataset(canonical_bytes(case))
    raw=json.dumps(request).encode()
    with pytest.raises(ApiError):parse_survey_dataset(raw[:-1]+b',"schema":"m03-owner-dataset-request/1"}')


@pytest.mark.parametrize('failure',['foreign_project','wrong_hash','wrong_role','changed_bytes'])
def test_genuine_intake_adverse_parent_binding_before_claim(make_harness,failure):
    from app.models import RawAsset
    harness=make_harness();install(harness);owner=UUID(harness.account()['id']);project=UUID(harness.project()['id'])
    request=inputs(harness,str(project));asyncio.run(table(harness))
    refused_project=project
    if failure=='foreign_project':
        # A genuinely registered second verified owner/project, not a missing
        # UUID whose404 could conceal a cross-owner binding regression.
        foreign=UUID(harness.account('foreign-dataset-owner@example.org')['id'])
        assert foreign!=owner
        refused_project=UUID(harness.project('Actual foreign owner project')['id'])
    async def run():
        async with harness.app.state.sessions() as session:
            user=await session.get(User,owner)
            changes={}
            if failure=='wrong_hash':changes['original_sha256']='0'*64
            if failure=='wrong_role':
                changes={'original_asset_id':request.metadata_asset_id,'original_sha256':request.metadata_sha256,
                    'metadata_asset_id':request.original_asset_id,'metadata_sha256':request.original_sha256}
            if failure=='changed_bytes':
                asset=await session.get(RawAsset,str(request.original_asset_id))
                # Same-size actual mutation preserves historical registered SHA.
                path=harness.settings.data_dir/asset.storage_key;before=path.read_bytes()
                path.write_bytes(bytes([before[0]^1])+before[1:])
            changed=type(request).model_validate({**request.model_dump(by_alias=True),**changes})
            with pytest.raises(ApiError):
                await reserve_dataset_inspection(session,harness.settings,user,refused_project,
                    changed,'b'*64,control_ledger,no_other_device_work)
            await session.rollback()
            assert not (await session.execute(select(SurveyDatasetAttempt.id))).first()
            assert not (harness.settings.data_dir/'.m03-datasets').exists()
    asyncio.run(run())


def test_actual_second_phase_one_byte_deficit_preserves_initial_claim(make_harness):
    from tests.api.test_magnetic_line_survey_intake import bundle
    from app.processing_contract import canonical_bytes
    harness=make_harness();install(harness);owner=UUID(harness.account()['id']);project=UUID(harness.project()['id'])
    original=(','.join(CSV_COLUMNS)+'\n'+','.join(['R0','L0','flight','S0','0','2001-01-01T00:00:00Z',*['1']*8])+'\n').encode()
    bodies=[('original_csv',original),('metadata_json',b'{}'),('request_json',b'{}'),('typed_auxiliary_bundle',bundle([('array-a.json',b'{}')]))]
    receipts=[]
    for role,body in bodies:
        result=upload(harness,str(project),body,header(body,role));assert result.status_code==201,result.text
        receipts.append(result.json())
    request=parse_survey_dataset(canonical_bytes(dict(schema='m03-owner-dataset-request/1',
        original_asset_id=receipts[0]['asset_id'],original_sha256=receipts[0]['sha256'],metadata_asset_id=receipts[1]['asset_id'],
        metadata_sha256=receipts[1]['sha256'],request_asset_id=receipts[2]['asset_id'],request_sha256=receipts[2]['sha256'],
        auxiliary_asset_ids=[receipts[3]['asset_id']],auxiliary_sha256=[receipts[3]['sha256']])))
    asyncio.run(table(harness))
    async def run():
        async with harness.app.state.sessions() as session:
            user=await session.get(User,owner)
            row=await reserve_dataset_inspection(session,harness.settings,user,project,request,'b'*64,control_ledger,no_other_device_work)
            key=row.id;row.state='running';await session.commit()
            # Actual SQL capacity-control receipt, NOT a native success or scientific grant.
            proof=exact_next_phase(1,len(bodies[3][1]),1)
            inspection=dict(schema='m03-owner-inspection-receipt/1',original=dict(csv_bytes=len(original),csv_sha256=sha256(original).hexdigest()),
                rows=1,metadata_sha256=receipts[1]['sha256'],request_sha256=receipts[2]['sha256'],bundle_sha256=[receipts[3]['sha256']],
                bundle_members=[1],auxiliary_bytes=len(bodies[3][1]),next_phase=proof,value_access='not_opened')
            quota=sum(item['bytes'] for item in receipts)+proof['dataset_reservation_bytes']-1
            settings=replace(harness.settings,max_upload_bytes=1024**2,account_quota_bytes=quota)
            with pytest.raises(ApiError) as error:
                await reserve_dataset_preparation(session,settings,UUID(key),'b'*64,deepcopy(inspection),
                    [receipts[3]['asset_id']],control_ledger,no_other_device_work)
            assert error.value.code=='account_quota_exceeded'
            await session.rollback()
            async with harness.app.state.sessions() as second:
                observed=await second.get(SurveyDatasetAttempt,key)
                assert observed.state=='running' and observed.reservation_bytes==INSPECTION_BYTES
            assert not dataset_attempt_root(settings,key).exists()
    asyncio.run(run())
