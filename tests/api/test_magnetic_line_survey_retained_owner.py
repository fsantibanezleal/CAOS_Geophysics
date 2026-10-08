"""Explicit retained ORIGINAL S1 native prerequisite -> actual saved HTTP/audit.

No repeated fit, copied counter, mocked principal, fake provider or combined
production startup assertion. The supplied external test DB/root must retain
the actual previously completed original S1 attempt and its immutable members.
"""
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
from uuid import UUID,uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
import pytest

from app.auth import install_auth
from app.config import Settings
from app.database import make_engine
from app.errors import ApiError,api_error_handler
from app.magnetic_line_survey_lifecycle import METHOD,attempt_root,cancel_owned,_document,_publication_receipts
from app.magnetic_line_survey_models import SurveyAttempt
from app.magnetic_line_survey_saved_api import install_magnetic_line_survey_saved_routes
from app.magnetic_line_survey_storage import account_m03_custody_usage,reconcile_m03_project
from app.models import ProcessingJob,User
from app.magnetic_line_survey_wire import BoundSurveyFile
from app.processing_contract import sha256
from app.security import install_security


def test_retained_original_native_owner_http_and_exact_recovery(tmp_path):
    settings=Settings(data_dir=Path(os.environ['GEOPHYSICS_M03_RETAINED_OWNER_ROOT']),
        db_path=Path(os.environ['GEOPHYSICS_M03_RETAINED_OWNER_DB']),
        auth_secret='test-secret-with-at-least-32-characters-123456',public_origin='http://testserver',cookie_secure=False)
    assert settings.database_path.is_file() and settings.data_dir.is_dir()
    engine=make_engine(settings)
    sessions=async_sessionmaker(engine,expire_on_commit=False)
    async def audit():
        async with sessions() as session:
            job=(await session.execute(select(ProcessingJob).where(ProcessingJob.method_id==METHOD))).scalar_one()
            assert job.state=='succeeded' and not job.cancel_requested
            attempt=(await session.execute(select(SurveyAttempt).where(SurveyAttempt.job_id==job.id))).scalar_one()
            assert attempt.state=='published' and attempt.lifetime['verdict']=='component_pass'
            assert attempt.lifetime['total_processes']==1 and attempt.lifetime['active_processes']==0
            root=attempt_root(settings.data_dir,job,attempt)
            raw=(root/'result/result.json').read_bytes()
            assert sha256(raw)==job.result_sha256 and len(raw)==job.result_bytes
            result=json.loads(raw)
            assert result['inventory']['original_rows']==363 and result['fit']['fit_count']==25
            assert result['input']['original']['csv_sha256']=='ac28e5f7c8344b94ebe0c408484eede8ade5a4074c8ef44661bcfe774ff0bfae'
            assert result['verdict']['overall']=='fail' and result['evaluation']['verdict']['overall']=='fail'
            assert abs(result['evaluation']['rmse_nT']-18.799740861734186)<1e-6
            ready=_document(root,'result-ready.json',attempt.inventory)
            fitted=_document(root,'fit/physical-fit.json',attempt.inventory)
            fit_receipt=next(item for item in attempt.inventory if item['name']=='fit/physical-fit.json')
            actual=next(item for item in attempt.inventory if item['name']=='result/result.json')
            original=BoundSurveyFile(UUID(job.id),result['input']['original']['csv_sha256'],
                result['input']['original']['csv_bytes'],root/'unused-original-identity')
            # Actual retained completed S1 output, not a fabricated successful
            # v2 Result. This custody fence must preserve its scientific FAIL.
            _publication_receipts(result,ready,actual,original,fitted,fit_receipt)
            for mutation in ({'schema':'m03-resolution-fit-ready/1'}, {'rows':8201},
                             {'policy_epoch':'resolution_v2'}, {'scientific_verdict':'pass'},
                             {'result_sha256':'0'*64}, {'unexpected':True}):
                wrong=deepcopy(ready)
                wrong.update(mutation)
                with pytest.raises(ApiError) as error:
                    _publication_receipts(result,wrong,actual,original,fitted,fit_receipt)
                assert error.value.code=='survey_result_invalid'
            for key in ('fit','inventory','input','verdict'):
                wrong=deepcopy(result)
                wrong[key]=None
                with pytest.raises(ApiError):
                    _publication_receipts(wrong,ready,actual,original,fitted,fit_receipt)
            for mutation in ({'schema':'m03-global-physical-fit/2'}, {'evaluation_count':2},
                             {'rows':8201}, {'fit':None}, {'geometry_sha256':'0'*64}):
                wrong=deepcopy(fitted)
                wrong.update(mutation)
                with pytest.raises(ApiError):
                    _publication_receipts(result,ready,actual,original,wrong,fit_receipt)
            assert result['verdict']['overall']=='fail'
            user=await session.get(User,job.owner_id)
            actual=await reconcile_m03_project(session,settings,user,UUID(job.project_id))
            assert actual['retained_bytes']==attempt.retained_bytes==attempt.lifetime['scratch_bytes']
            assert await account_m03_custody_usage(session,user.id)==actual['retained_bytes']
            prepared=await reconcile_m03_project(session,settings,user,UUID(job.project_id),for_deletion=True)
            assert prepared['deletion_preparation'] and prepared['mutation']=='none'
            # An unexpected empty directory is retained outside custody after
            # demonstrating refusal, not silently allowlisted or erased.
            unknown=root/'unknown-empty-control'
            unknown.mkdir()
            try:
                try:
                    await reconcile_m03_project(session,settings,user,UUID(job.project_id))
                except ApiError as error:
                    assert error.code=='survey_recovery_required'
                else:
                    raise AssertionError('Unknown namespace must refuse')
            finally:
                unknown.rename(tmp_path/'unknown-empty-directory-evidence')
            await reconcile_m03_project(session,settings,user,UUID(job.project_id))
            return job.id,job.project_id,job.owner_id,user.email,raw
    job_id,project_id,owner_id,email,raw=asyncio.run(audit())

    # Separate real ORM session principal is a legal service input. This was
    # the previous detached-refresh failure; no principal is fabricated here.
    async def detached_cancel():
        async with sessions() as auth_session,sessions() as action_session:
            user=await auth_session.get(User,owner_id)
            view=await cancel_owned(action_session,user,UUID(project_id),UUID(job_id))
            assert view['state']=='succeeded' and not view['cancel_requested']
    asyncio.run(detached_cancel())

    app=FastAPI()
    app.state.sessions=sessions
    app.add_exception_handler(ApiError,api_error_handler)
    async def mail(_to,_subject,_body):
        raise AssertionError('Saved existing-owner test must not require mail')
    current_user,get_session=install_auth(app,settings,mail)
    install_security(app,settings)
    install_magnetic_line_survey_saved_routes(app,settings,current_user,get_session)
    with TestClient(app) as client:
        prefix=f'/api/projects/{project_id}/magnetic-line-surveys/jobs/{job_id}'
        assert client.get(prefix).status_code==401
        token=client.get('/api/auth/csrf').json()['csrf_token']
        headers={'Origin':'http://testserver','X-CSRF-Token':token}
        login=client.post('/api/auth/cookie/login',data={'username':email,'password':'correct horse battery staple'},headers=headers)
        assert login.status_code==204
        assert client.get(prefix).json()['state']=='succeeded'
        assert client.get(prefix+'/result').content==raw
        response=client.post(prefix+'/cancel',headers=headers)
        assert response.status_code==200 and response.json()['state']=='succeeded'
        assert client.post(prefix+'/cancel',content=b'{}',headers=headers).status_code==422
        assert client.post(prefix+'/cancel').status_code==403
        assert client.get(prefix.replace(project_id,str(uuid4()))).status_code==404
        page=client.get(prefix+'/members').json()
        assert page['schema']=='m03-owner-members/1' and page['next_offset'] is None
        result_member=next(item for item in page['entries'] if item['kind']=='result')
        served=client.get(prefix+'/members/'+result_member['member_id'])
        assert served.content==raw and served.headers['x-content-sha256']==sha256(raw)
        assert client.get(prefix+'/members/'+str(uuid4())).status_code==404
    asyncio.run(engine.dispose())


def test_current_publication_fence_on_consistent_retained_database_copy(tmp_path):
    """Real SQL/file publication fence, NOT a new native attempt or science run.

    SQLite backup preserves a consistent copied fixture. Reopening the terminal
    rows occurs ONLY in that explicitly labelled test DB; original DB, worker
    receipts and scientific bytes remain untouched. Native evidence still
    belongs to the original retained attempt, not this transaction exercise.
    """
    import sqlite3
    from sqlalchemy import delete
    from app.magnetic_line_survey_models import SurveyAdmission,SurveyMember
    from app.magnetic_line_survey_lifecycle import publish_drained_result

    source_db=Path(os.environ['GEOPHYSICS_M03_RETAINED_OWNER_DB'])
    copied_db=tmp_path/'consistent-terminal-fixture.sqlite3'
    with sqlite3.connect(source_db.as_uri()+'?mode=ro',uri=True) as source,sqlite3.connect(copied_db) as destination:
        source.backup(destination)
    settings=Settings(data_dir=Path(os.environ['GEOPHYSICS_M03_RETAINED_OWNER_ROOT']),db_path=copied_db,
        auth_secret='test-secret-with-at-least-32-characters-123456',public_origin='http://testserver',cookie_secure=False)
    engine=make_engine(settings)
    sessions=async_sessionmaker(engine,expire_on_commit=False)
    async def run():
        async with sessions() as session:
            job=(await session.execute(select(ProcessingJob).where(ProcessingJob.method_id==METHOD))).scalar_one()
            attempt=(await session.execute(select(SurveyAttempt).where(SurveyAttempt.job_id==job.id))).scalar_one()
            admission=await session.get(SurveyAdmission,job.id)
            assert job.state=='succeeded' and attempt.state=='published'
            identity,worker,authority=UUID(attempt.id),attempt.worker_id,admission.authority_sha256
            source_pins=deepcopy(attempt.lifetime['source_sha256'])
            expected=job.result_sha256,job.result_bytes
            inventory=deepcopy(attempt.inventory)
            job.state='running'
            job.finished_at=None
            attempt.state='drained'
            await session.execute(delete(SurveyMember).where(SurveyMember.attempt_id==attempt.id))
            await session.commit()
            # One unknown persisted inventory is NOT a license to publish the
            # matching Result only. Preserve all actual original files.
            attempt.inventory=[]
            await session.commit()
            with pytest.raises(ApiError) as refused:
                await publish_drained_result(session,settings,identity,worker,authority,source_pins)
            assert refused.value.code=='survey_inventory_mismatch'
            await session.rollback()
            attempt=await session.get(SurveyAttempt,str(identity))
            attempt.inventory=inventory
            await session.commit()
            view=await publish_drained_result(session,settings,identity,worker,authority,source_pins)
            assert view['state']=='succeeded'
            assert (view['result_sha256'],view['result_bytes'])==expected
            attempt=await session.get(SurveyAttempt,str(identity))
            assert attempt.state=='published' and attempt.inventory==inventory
            members=(await session.execute(select(SurveyMember).where(SurveyMember.attempt_id==str(identity)))).scalars().all()
            assert len(members)==216 and len({member.id for member in members})==216
            root=attempt_root(settings.data_dir,await session.get(ProcessingJob,view['job_id']),attempt)
            assert json.loads((root/'result/result.json').read_bytes())['verdict']['overall']=='fail'
        await engine.dispose()
    asyncio.run(run())
