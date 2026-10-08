"""Explicit retained ORIGINAL S1 native prerequisite -> actual saved HTTP/audit.

No repeated fit, copied counter, mocked principal, fake provider or combined
production startup assertion. The supplied external test DB/root must retain
the actual previously completed original S1 attempt and its immutable members.
"""
import asyncio
import json
import os
from pathlib import Path
from uuid import UUID,uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.auth import install_auth
from app.config import Settings
from app.database import make_engine
from app.errors import ApiError,api_error_handler
from app.magnetic_line_survey_lifecycle import METHOD,attempt_root,cancel_owned
from app.magnetic_line_survey_models import SurveyAttempt
from app.magnetic_line_survey_saved_api import install_magnetic_line_survey_saved_routes
from app.magnetic_line_survey_storage import account_m03_custody_usage,reconcile_m03_project
from app.models import ProcessingJob,User
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
