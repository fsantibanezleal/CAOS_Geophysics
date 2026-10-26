"""Actual original S1 native output through durable publication and saved HTTP.

Direct SQL setup exercises the publication boundary, NOT production magnetic
upload/normalization/admission. No acquired field or Linux/VPS claim follows.
The original predictive FAIL must survive publication and byte serving.
"""
import asyncio
from dataclasses import replace
import os
from pathlib import Path
import sys
import tempfile
from uuid import UUID, uuid4

from sqlalchemy import select

from app.config import WorkerSettings
from app.magnetic_line_survey_lifecycle import (
    METHOD, admitted_envelope, attempt_root, claim_attempt, collect_inventory,
    publish_drained_result, record_terminal_attempt, source_receipts,
)
from app.magnetic_line_survey_models import SurveyAdmission, SurveyAttempt, SurveyExportRecord, SurveyMember
from app.magnetic_line_survey_saved_api import install_magnetic_line_survey_saved_routes
from app.magnetic_line_survey_wire import SurveyStart, bind_owned_survey_sources
from app.models import AccountUsage, ObservationDataset, ProcessingJob, RawAsset, SourceRecord, User
from app.processing_contract import canonical_bytes, dataset_key, sha256

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'data-pipeline'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'data'))
import magnetic_line_contract as base
import magnetic_line_survey_runtime as runtime
from test_magnetic_line_survey_diagnostic import plan


def test_real_original_s1_native_attempt_publication_and_saved_routes(harness,tmp_path):
    # Win32 CreateProcess current-directory length is separate from ordinary
    # extended-length file custody. Use a genuine compact external storage
    # configuration, not a junction/copy of the attempt or shortened UUIDs.
    # Retain it for exact evidence; the DB remains at its original external path.
    compact_parent=Path(tmp_path.anchor)/'_Temp'/'m03-owned-publication'
    compact_parent.mkdir(parents=True,exist_ok=True)
    compact=Path(tempfile.mkdtemp(prefix='o-',dir=compact_parent))
    harness.settings=replace(harness.settings,data_dir=compact)
    account=harness.account()
    project=harness.project('Original authored S1 publication control')
    prepared=tmp_path/'original-control'
    prepared.mkdir()
    original=base.strict_json(plan(prepared).read_bytes())
    job_id=uuid4()
    bodies=[Path(original['csv_path']).read_bytes(),base.canonical_bytes(original['metadata']),base.canonical_bytes(original['request'])]
    owner=UUID(account['id'])
    settings=WorkerSettings(harness.settings.data_dir,harness.settings.db_path)
    # Fixed local test configuration identity, not a client flag or Linux profile.
    authority_sha=sha256(canonical_bytes(dict(schema='m03-native-publication-test-authority/1',
        executable=str(Path(sys.base_prefix)/'python.exe'),packages=os.environ['GEOPHYSICS_EXISTING_PACKAGE_ROOT'])))
    refs=[]

    async def setup():
        async with harness.app.state.sessions.kw['bind'].begin() as connection:
            for table in (SurveyAdmission.__table__,SurveyAttempt.__table__,SurveyMember.__table__,SurveyExportRecord.__table__):
                await connection.run_sync(table.create,checkfirst=True)
        async with harness.app.state.sessions() as session:
            for role,body in zip(('original','metadata','request'),bodies,strict=True):
                asset_id,source_id=str(uuid4()),str(uuid4())
                key=f'projects/{owner}/{project["id"]}/{asset_id}'
                target=settings.data_dir/key
                target.parent.mkdir(parents=True,exist_ok=True)
                with target.open('xb') as stream:
                    stream.write(body)
                    stream.flush()
                    os.fsync(stream.fileno())
                filename=f'authored-s1-{role}'+('.csv' if role=='original' else '.json')
                source=SourceRecord(id=source_id,project_id=project['id'],owner_id=owner,original_filename=filename,
                    version=1,provider='Frozen authored original S1 regression, not provider field',
                    rights_statement='Authored regression retained for private scientific validation; no field authenticity claim.',
                    rights_decision='mirror',private_storage_permission='attested',declared_format='magnetic_csv' if role=='original' else 'm03_'+role,
                    expected_bytes=len(body),sha256=sha256(body),attribution='Existing unchanged authored S1')
                session.add(source)
                await session.flush()
                session.add(RawAsset(id=asset_id,project_id=project['id'],owner_id=owner,source_id=source_id,filename=filename,
                    client_mime='text/csv' if role=='original' else 'application/json',detected_format=source.declared_format,
                    byte_count=len(body),sha256=sha256(body),storage_key=key,physical_metadata={'source_kind':'original_synthetic_acquisition'}))
                refs.append((asset_id,sha256(body)))
            await session.flush()
            dataset_id=str(uuid4())
            # This is an explicit custody-boundary descriptor, not a newly
            # approved production normalizer or invented field acquisition.
            descriptor=canonical_bytes(dict(schema='m03-test-original-parent-descriptor/1',original_asset_id=refs[0][0],
                original_sha256=refs[0][1],metadata_sha256=refs[1][1],rows=363,source_kind='original_synthetic_acquisition'))
            key=dataset_key(str(owner),project['id'],dataset_id)
            target=settings.data_dir/key
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(descriptor)
            dataset=ObservationDataset(id=dataset_id,project_id=project['id'],owner_id=owner,raw_asset_id=refs[0][0],version=1,
                parser_version='m03-test-parent-custody/1',modality='magnetic_line_survey',row_count=363,
                raw_sha256=refs[0][1],sha256=sha256(descriptor),byte_count=len(descriptor),storage_key=key)
            session.add(dataset)
            usage=await session.get(AccountUsage,owner)
            if usage is None:
                session.add(AccountUsage(user_id=owner,raw_bytes=sum(map(len,bodies))))
            else:
                usage.raw_bytes+=sum(map(len,bodies))
            await session.commit()
            start=SurveyStart.model_validate(dict(schema='m03-owner-start/1',dataset_id=dataset_id,
                dataset_sha256=dataset.sha256,original_asset_id=refs[0][0],original_sha256=refs[0][1],metadata_asset_id=refs[1][0],
                metadata_sha256=refs[1][1],request_asset_id=refs[2][0],request_sha256=refs[2][1],auxiliary_asset_ids=[],auxiliary_sha256=[]))
            user=await session.get(User,owner)
            bound=await bind_owned_survey_sources(session,settings,UUID(project['id']),user,start)
            job=ProcessingJob(id=str(job_id),project_id=project['id'],owner_id=owner,dataset_id=dataset_id,dataset_sha256=dataset.sha256,
                method_id=METHOD,state='queued',cancel_requested=False,request_json={},request_sha256='0'*64,preflight={})
            admission=SurveyAdmission(job_id=job.id,start_json=start.model_dump(mode='json',by_alias=True),
                source_receipts=source_receipts(bound),authority_sha256=authority_sha,reservation_bytes=32*1024**3)
            job.request_json=admitted_envelope(job,admission)
            job.request_sha256=sha256(canonical_bytes(job.request_json))
            session.add(job)
            await session.flush()
            session.add(admission)
            await session.commit()
            attempt=await claim_attempt(session,settings,job_id,'native-original-s1',authority_sha)
            assert attempt is not None
            current=await session.get(ProcessingJob,str(job_id))
            root=attempt_root(settings.data_dir,current,attempt)
            root.mkdir(parents=True)
            return UUID(attempt.id),root,bound

    attempt_id,root,bound=asyncio.run(setup())
    original.pop('mode')
    original.update(schema='m03-full-result-plan/1',csv_path=str(bound.original.path),navigation_root=None,
        auxiliary_roots={},reference_definitions={},run_id=str(job_id))
    request_path=root/'plan.json'
    request_path.write_bytes(base.canonical_bytes(original))
    lifetime=runtime.run_worker(Path(sys.base_prefix)/'python.exe',Path(os.environ['GEOPHYSICS_EXISTING_PACKAGE_ROOT']),root,request_path)
    assert lifetime['verdict']=='component_pass',(lifetime,(root/'stdout.log').read_text(),(root/'stderr.log').read_text())
    assert lifetime['total_processes']==1 and lifetime['active_processes']==0
    result=base.strict_json((root/'result/result.json').read_bytes())
    assert result['fit']['fit_count']==25 and result['inventory']['original_rows']==363
    assert result['verdict']['overall']=='fail' and result['evaluation']['verdict']['overall']=='fail'
    assert abs(result['evaluation']['rmse_nT']-18.799740861734186)<1e-6
    inventory=collect_inventory(settings.data_dir,root)
    assert sum(item['bytes'] for item in inventory)==lifetime['scratch_bytes']

    async def publish():
        async with harness.app.state.sessions() as session:
            await record_terminal_attempt(session,attempt_id,'native-original-s1',lifetime,inventory)
            view=await publish_drained_result(session,settings,attempt_id,'native-original-s1',authority_sha,lifetime['source_sha256'])
            assert view['state']=='succeeded' and view['error_code'] is None
            row=(await session.execute(select(SurveyMember).where(SurveyMember.attempt_id==str(attempt_id),SurveyMember.kind=='result'))).scalar_one()
            return row.id,row.sha256,row.byte_count
    result_member_id,result_sha,result_bytes=asyncio.run(publish())

    # Use actual existing authentication/session dependencies and security,
    # not a mocked current_user or parallel login router.
    current_user=next(route for route in harness.app.routes if getattr(route,'path',None)=='/api/auth/me').dependant.dependencies[0].call
    async def get_session():
        async with harness.app.state.sessions() as session:
            yield session
    install_magnetic_line_survey_saved_routes(harness.app,harness.settings,current_user,get_session)
    prefix=f'/api/projects/{project["id"]}/magnetic-line-surveys/jobs/{job_id}'
    saved=harness.request('GET',prefix)
    assert saved.status_code==200 and saved.json()['state']=='succeeded'
    response=harness.request('GET',prefix+'/result')
    assert response.status_code==200 and response.content==(root/'result/result.json').read_bytes()
    assert response.json()['verdict']['overall']=='fail' and response.headers['x-content-sha256']==result_sha
    registry=harness.request('GET',prefix+'/members')
    assert registry.status_code==200 and registry.json()['next_offset'] is None
    member=harness.request('GET',prefix+'/members/'+result_member_id)
    assert member.status_code==200 and len(member.content)==result_bytes and sha256(member.content)==result_sha
    assert member.headers['content-type']=='application/octet-stream'
    assert harness.request('GET',prefix+'/members/'+str(uuid4())).status_code==404
    assert harness.request('POST',prefix+'/cancel',content=b'{}').status_code==422
    assert harness.request('POST',prefix+'/cancel').json()['state']=='succeeded'
    assert harness.request('GET',prefix.replace(project['id'],str(uuid4()))).status_code==404
    # Same-size changed bytes are rejected, not silently served from the registry.
    saved_bytes=(root/'result/result.json').read_bytes()
    (root/'result/result.json').write_bytes(b'X'+saved_bytes[1:])
    assert harness.request('GET',prefix+'/members/'+result_member_id).status_code==409
    (root/'result/result.json').write_bytes(saved_bytes)
