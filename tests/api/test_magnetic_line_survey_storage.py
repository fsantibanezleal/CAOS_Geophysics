"""Deterministic accounting/namespace controls; SQL counters are UNIT fixtures."""
import asyncio
from copy import deepcopy
from uuid import UUID,uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker,create_async_engine

from app.errors import ApiError
from app.magnetic_line_survey_lifecycle import admitted_envelope,storage_root
from app.magnetic_line_survey_models import SurveyAttempt
from app.magnetic_line_survey_storage import account_m03_custody_usage,exact_namespace
from app.models import Base
from app.processing_contract import canonical_bytes,sha256
from tests.api.test_magnetic_line_survey_lifecycle import example_job
from tests.api.test_magnetic_line_survey_wire import registered  # noqa: F401


def counter_fixture(bytes=1000):
    # Not an actual native receipt/benchmark. Used only to test persisted debt
    # calculation and malformed-counter refusal independently of OS compute.
    return dict(schema='m03-local-lifetime/1',verdict='component_pass',exit_code=0,cpu_s=1,wall_s=1,
        peak_rss_bytes=100000,peak_committed_bytes=100000,parent_cpu_s=1,scratch_bytes=bytes,
        stop_wall_s=None,stop_cpu_s=None,active_processes=0,total_processes=1,
        source_sha256={'fixture.py':'b'*64},actual_executable_sha256='a'*64,admission='unit_fixture_not_native')


def test_every_attempt_debt_unknown_drain_and_no_generic_result_double_count(tmp_path):
    async def run():
        engine=create_async_engine('sqlite+aiosqlite:///'+(tmp_path/'debt.sqlite3').as_posix())
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        sessions=async_sessionmaker(engine,expire_on_commit=False)
        async with sessions() as session:
            job,admission=example_job()
            admission.reservation_bytes=2048
            job.request_json=admitted_envelope(job,admission)
            job.request_sha256=sha256(canonical_bytes(job.request_json))
            session.add_all([job,admission])
            await session.commit()
            assert await account_m03_custody_usage(session,job.owner_id)==2048
            job.state='cancelled'
            await session.commit()
            assert await account_m03_custody_usage(session,job.owner_id)==0
            attempt=SurveyAttempt(id=str(uuid4()),job_id=job.id,ordinal=1,state='claimed',worker_id='fixture',
                retained_bytes=4096,inventory=[])
            session.add(attempt)
            job.state='running'
            await session.commit()
            assert await account_m03_custody_usage(session,job.owner_id)==4096
            attempt.state='drained'
            attempt.lifetime=counter_fixture()
            attempt.retained_bytes=1000
            await session.commit()
            assert await account_m03_custody_usage(session,job.owner_id)==2048
            job.state='failed'
            await session.commit()
            assert await account_m03_custody_usage(session,job.owner_id)==1000
            attempt.state='published'
            job.state='succeeded'
            job.result_bytes=100
            await session.commit()
            assert await account_m03_custody_usage(session,job.owner_id)==1000
            old=SurveyAttempt(id=str(uuid4()),job_id=job.id,ordinal=2,state='publication_uncertain',worker_id='fixture',
                retained_bytes=3000,inventory=[])
            session.add(old)
            await session.commit()
            assert await account_m03_custody_usage(session,job.owner_id)==4000
            wrong=deepcopy(attempt.lifetime);wrong['active_processes']=1
            attempt.lifetime=wrong
            await session.commit()
            with pytest.raises(ApiError):
                await account_m03_custody_usage(session,job.owner_id)
            # Other owners never inherit this owner's debt.
            assert await account_m03_custody_usage(session,uuid4())==0
        await engine.dispose()
    asyncio.run(run())


def test_namespace_is_exhaustive_including_empty_directories_and_same_size_changes(tmp_path):
    root=storage_root(tmp_path/'owned-project')
    path=root/'job'/'attempts'/'attempt'/'result'/'chunk.bin'
    path.parent.mkdir(parents=True)
    path.write_bytes(b'exact retained')
    expected=[dict(name='job/attempts/attempt/result/chunk.bin',bytes=14,sha256=sha256(b'exact retained'))]
    exact_namespace(tmp_path,root,expected)
    unknown=root/'unknown-empty'
    unknown.mkdir()
    with pytest.raises(ApiError):
        exact_namespace(tmp_path,root,expected)
    # Preserve negative evidence, outside the scoped namespace.
    unknown.rename(tmp_path/'unknown-empty-directory-evidence')
    path.write_bytes(b'wrong retained')
    with pytest.raises(ApiError):
        exact_namespace(tmp_path,root,expected)
    with pytest.raises(ApiError):
        exact_namespace(tmp_path,root,[])
    exact_namespace(tmp_path,tmp_path/'never-allocated',[])


def test_reconciliation_scopes_project_before_storage(registered):  # noqa: F811
    from app.magnetic_line_survey_storage import reconcile_m03_project
    from app.models import User
    harness,account,_project,_assets,_body=registered
    async def run():
        async with harness.app.state.sessions() as session:
            user=await session.get(User,UUID(account['id']))
            with pytest.raises(ApiError) as error:
                await reconcile_m03_project(session,harness.settings,user,uuid4())
            assert error.value.status==404
    asyncio.run(run())
