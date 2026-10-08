"""Actual native dataset birth via real cookie intake, NOT production authority.

One existing authored363-row geometry control, not a provider/8201 field run,
not a new scientific fit/holdout experiment. Must run in the shared dispatcher.
"""
import asyncio
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from uuid import UUID

import pytest
from sqlalchemy import select

from app.magnetic_line_survey_dataset_api import install_magnetic_line_survey_dataset_routes
from app.magnetic_line_survey_dataset_controller import WindowsPreparationController,METHOD
from app.magnetic_line_survey_models import SurveyDatasetAttempt
from app.models import AccountUsage,ObservationDataset,ProcessingJob
from tests.api.test_magnetic_line_survey_intake import install,upload,header


def test_missing_real_installation_refuses_not_noop():
    from app.errors import ApiError
    with pytest.raises(ApiError):WindowsPreparationController(Path(sys.executable),Path.cwd(),installation=None)


def register_control_only_dataset_route(harness):
    """Genuine native controller, but explicit isolated TEST installation seam."""
    class TestInstallationOnly:
        def __init__(self):self.expected=None
        def verify(self,settings,**actual):
            assert actual['method']==METHOD and settings==harness.settings
            snapshot={**actual,'executable':str(actual['executable']),'package_root':str(actual['package_root'])}
            if self.expected is None:self.expected=snapshot
            assert snapshot==self.expected
            return sha256(json.dumps(snapshot,sort_keys=True).encode()).hexdigest()
    controller=WindowsPreparationController(Path(sys.base_prefix)/'python.exe',
        Path(os.environ['GEOPHYSICS_EXISTING_PACKAGE_ROOT']),installation=TestInstallationOnly())
    async def base_ledger(session,owner_id):
        assert not (await session.execute(select(ProcessingJob.id))).first()
        raw=await session.get(AccountUsage,owner_id)
        datasets=(await session.execute(select(ObservationDataset).where(ObservationDataset.owner_id==owner_id))).scalars().all()
        return (raw.raw_bytes if raw else 0)+sum(item.byte_count for item in datasets)
    async def device_ledger(session):
        assert not (await session.execute(select(ProcessingJob.id))).first()
        return 0
    def routes(items):
        for item in items:
            if hasattr(item,'original_router'):yield from routes(item.original_router.routes)
            else:yield item
    route=next(item for item in routes(harness.app.routes) if getattr(item,'path',None)=='/api/projects/{project_id}/assets' and 'POST' in item.methods)
    deps={dep.name:dep.call for dep in route.dependant.dependencies}
    install_magnetic_line_survey_dataset_routes(harness.app,harness.settings,deps['user'],deps['session'],
        controller=controller,base_ledger=base_ledger,device_ledger=device_ledger)


@pytest.mark.skipif(sys.platform!='win32',reason='Actual Windows Job required')
def test_real_intake_native_descriptor_publication(make_harness,tmp_path,monkeypatch):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'data'))
    from test_magnetic_line_survey_bundle import fixture
    plan=fixture(tmp_path/'authored-original')
    harness=make_harness();install(harness)
    owner=UUID(harness.account()['id']);project=harness.project()['id']
    async def create_table():
        async with harness.app.state.sessions() as session:
            connection=await session.connection()
            await connection.run_sync(lambda conn:SurveyDatasetAttempt.__table__.create(conn))
            await session.commit()
    asyncio.run(create_table())
    receipts=[]
    for role,entry in [('original_csv',plan['original']),('metadata_json',plan['metadata']),('request_json',plan['request']),
                       *[('typed_auxiliary_bundle',item) for item in plan['bundles']]]:
        body=Path(entry['path']).read_bytes()
        if role=='metadata_json':
            # Legitimate noncanonical original-sidecar bytes stay unmodified.
            # Dataset identity uses the specified canonical semantic domain,
            # while RawAsset/SourceRecord receipts bind these exact bytes.
            body=json.dumps(json.loads(body),indent=2).encode('utf-8')
        response=upload(harness,project,body,header(body,role));assert response.status_code==201,response.text
        receipts.append(response.json())
    body=dict(schema='m03-owner-dataset-request/1',original_asset_id=receipts[0]['asset_id'],original_sha256=receipts[0]['sha256'],
        metadata_asset_id=receipts[1]['asset_id'],metadata_sha256=receipts[1]['sha256'],request_asset_id=receipts[2]['asset_id'],
        request_sha256=receipts[2]['sha256'],auxiliary_asset_ids=[item['asset_id'] for item in receipts[3:]],
        auxiliary_sha256=[item['sha256'] for item in receipts[3:]])
    register_control_only_dataset_route(harness)
    # Observe committed state from a genuinely independent SQL transaction at
    # initial and second-phase mkdir, not a mocked native success receipt.
    real_mkdir=Path.mkdir;observed=[]
    def mkdir(path,*args,**kwargs):
        if path.name in ('inspection','preparation') and path.parent.parent.name=='.m03-datasets':
            async def check():
                async with harness.app.state.sessions() as second:
                    attempt=await second.get(SurveyDatasetAttempt,path.parent.name)
                    assert attempt.state=='running' and not path.exists()
                    if path.name=='inspection':assert attempt.reservation_bytes==16*1024**2
                    else:assert 16*1024**2<attempt.reservation_bytes<1024**3
            asyncio.run(check());observed.append(path.name)
        return real_mkdir(path,*args,**kwargs)
    monkeypatch.setattr(Path,'mkdir',mkdir)
    response=harness.request('POST',f'/api/projects/{project}/magnetic-line-surveys/datasets',json=body)
    assert response.status_code==201,response.text
    receipt=response.json();assert set(receipt)=={'schema','dataset_id','sha256','bytes','rows','parser_version','provider_verification','field_eligibility'}
    assert receipt['rows']==363 and receipt['provider_verification']=='not_verified' and receipt['field_eligibility']=='not_established'
    assert observed==['inspection','preparation']
    async def verify():
        async with harness.app.state.sessions() as session:
            dataset=await session.get(ObservationDataset,receipt['dataset_id'])
            attempt=(await session.execute(select(SurveyDatasetAttempt))).scalar_one()
            assert attempt.state=='published' and attempt.dataset_id==dataset.id and dataset.owner_id==owner
            assert dataset.raw_asset_id==receipts[0]['asset_id'] and dataset.row_count==363
            data=(harness.settings.data_dir/dataset.storage_key).read_bytes()
            assert len(data)==receipt['bytes']==dataset.byte_count and sha256(data).hexdigest()==receipt['sha256']==dataset.sha256
            descriptor=json.loads(data);assert len(descriptor)==15 and descriptor['rows']==363
            assert not (harness.settings.data_dir/'.m03-datasets'/attempt.id/'descriptor.json').exists()
            assert len(attempt.lifetime['phases'])==2
            assert all(item['active_processes']==0 and item['total_processes']==1 for item in attempt.lifetime['phases'])
            assert attempt.lifetime['cpu_s']<=600 and attempt.lifetime['wall_s']<=600
            assert attempt.retained_bytes==sum(item['bytes'] for item in attempt.inventory)
            usage=await session.get(AccountUsage,owner)
            assert usage.raw_bytes==sum(item['bytes'] for item in receipts)  # Descriptor not charged twice.
            from app.magnetic_line_survey_dataset_recovery import reconcile_owned_datasets,reconcile_dataset_device_namespace
            from app.models import User
            user=await session.get(User,owner)
            reconciliation=await reconcile_owned_datasets(session,harness.settings,user,UUID(project))
            assert reconciliation['published']==1 and reconciliation['state']=='exact'
            assert (await reconcile_dataset_device_namespace(session,harness.settings))['state']=='exact'
            # Actual published lifetime mutations must not bypass the stricter
            # preparation envelope by borrowing full science's4GiB/6h caps.
            from copy import deepcopy
            from app.errors import ApiError
            baseline=deepcopy(attempt.lifetime)
            for fault in ('cpu','wall','boolean','rss','source','executable'):
                changed=deepcopy(baseline)
                if fault=='cpu':changed['cpu_s']=601
                elif fault=='wall':changed['wall_s']=601
                elif fault=='boolean':changed['parent_cpu_s']=True
                elif fault=='rss':changed['phases'][0]['peak_rss_bytes']=512*1024**2+1
                elif fault=='source':changed['phases'][1]['source_sha256']={}
                else:changed['phases'][1]['actual_executable_sha256']='0'*64
                attempt.lifetime=changed;await session.flush()
                with pytest.raises(ApiError):await reconcile_owned_datasets(session,harness.settings,user,UUID(project))
                attempt.lifetime=deepcopy(baseline);await session.flush()
            # Unknown EMPTY namespaces are retained evidence, not exempt files.
            unexpected=harness.settings.data_dir/'.m03-datasets'/'unknown-empty';unexpected.mkdir()
            with pytest.raises(ApiError):await reconcile_dataset_device_namespace(session,harness.settings)
            assert unexpected.exists()
    asyncio.run(verify())
    duplicate=harness.request('POST',f'/api/projects/{project}/magnetic-line-surveys/datasets',json=body)
    assert duplicate.status_code==409 and duplicate.json()['code']=='survey_dataset_already_published'


@pytest.mark.skipif(sys.platform!='win32',reason='Actual Windows Job required')
def test_real_intake_native_first_failure_blocks_all_dependents(make_harness,tmp_path):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'data'))
    from test_magnetic_line_survey_bundle import fixture
    plan=fixture(tmp_path/'authored-original')
    harness=make_harness();install(harness);owner=UUID(harness.account()['id']);project=harness.project()['id']
    from tests.api.test_magnetic_line_survey_dataset_accounting import table
    asyncio.run(table(harness));receipts=[]
    for role,entry in [('original_csv',plan['original']),('metadata_json',plan['metadata']),('request_json',plan['request']),
                       *[('typed_auxiliary_bundle',item) for item in plan['bundles']]]:
        # Genuine uploaded bytes and hashes; malformed request fails native
        # closed-document parsing. No synthetic failed counter/status supplied.
        body=b'{}' if role=='request_json' else Path(entry['path']).read_bytes()
        response=upload(harness,project,body,header(body,role));assert response.status_code==201,response.text
        receipts.append(response.json())
    body=dict(schema='m03-owner-dataset-request/1',original_asset_id=receipts[0]['asset_id'],original_sha256=receipts[0]['sha256'],
        metadata_asset_id=receipts[1]['asset_id'],metadata_sha256=receipts[1]['sha256'],request_asset_id=receipts[2]['asset_id'],
        request_sha256=receipts[2]['sha256'],auxiliary_asset_ids=[v['asset_id'] for v in receipts[3:]],auxiliary_sha256=[v['sha256'] for v in receipts[3:]])
    register_control_only_dataset_route(harness)
    response=harness.request('POST',f'/api/projects/{project}/magnetic-line-surveys/datasets',json=body)
    assert response.status_code==409 and response.json()['code']=='survey_dataset_preparation_failed'
    async def verify():
        async with harness.app.state.sessions() as session:
            row=(await session.execute(select(SurveyDatasetAttempt))).scalar_one()
            assert row.state=='failed' and row.dataset_id is None and row.reservation_bytes==16*1024**2
            assert len(row.lifetime['phases'])==1
            native=row.lifetime['phases'][0]
            assert native['verdict']=='resource_refused' and native['exit_code']==2 and native['active_processes']==0 and native['total_processes']==1
            from app.magnetic_line_survey_dataset_accounting import account_dataset_usage,dataset_attempt_root
            from app.magnetic_line_survey_lifecycle import collect_inventory
            root=dataset_attempt_root(harness.settings,row.id)
            assert not (root/'preparation').exists() and not (root/'descriptor.json').exists()
            assert row.inventory==collect_inventory(harness.settings.data_dir,root)
            assert row.retained_bytes==sum(v['bytes'] for v in row.inventory)>0
            assert await account_dataset_usage(session,owner)==16*1024**2
            assert not (await session.execute(select(ObservationDataset.id))).first()
    asyncio.run(verify())
