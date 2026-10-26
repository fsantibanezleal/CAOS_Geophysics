"""Durable leaf transitions, not magnetic intake or integrated execution proof."""
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.errors import ApiError
from app.magnetic_line_survey_lifecycle import METHOD, admitted_envelope, check_admission, job_view, member_path, validate_drain
from app.magnetic_line_survey_models import SurveyAdmission, SurveyAttempt
from app.models import Base, ProcessingJob
from app.processing_contract import canonical_bytes, sha256
from tests.api.test_magnetic_line_survey_wire import registered  # noqa: F401


def example_job():
    # Explicit SQL/DTO fixture only, never an admitted scientific acquisition.
    refs={key:str(uuid4()) for key in ('dataset_id','original_asset_id','metadata_asset_id','request_asset_id')}
    start=dict(schema='m03-owner-start/1',**refs,auxiliary_asset_ids=[],auxiliary_sha256=[],
        **{key:'a'*64 for key in ('dataset_sha256','original_sha256','metadata_sha256','request_sha256')})
    job=ProcessingJob(id=str(uuid4()),project_id=str(uuid4()),owner_id=uuid4(),dataset_id=start['dataset_id'],
        dataset_sha256=start['dataset_sha256'],method_id=METHOD,state='queued',cancel_requested=False,
        created_at=datetime.now(timezone.utc),request_json={},request_sha256='0'*64,preflight={})
    admission=SurveyAdmission(job_id=job.id,start_json=start,source_receipts={},authority_sha256='b'*64,reservation_bytes=1024)
    job.request_json=admitted_envelope(job,admission)
    job.request_sha256=sha256(canonical_bytes(job.request_json))
    return job,admission


def test_closed_job_projection_and_distinct_admitted_hash_domain():
    job,admission=example_job()
    check_admission(job,admission)
    result=job_view(job)
    assert set(result)==set('schema job_id project_id dataset_id method state cancel_requested request_sha256 result_sha256 result_bytes error_code created_at started_at finished_at'.split())
    assert result['schema']=='m03-owner-job/1'
    assert result['request_sha256']!=admission.start_json['request_sha256']
    assert 'request_json' not in result and 'preflight' not in result and 'error_message' not in result
    assert result['created_at'].endswith('Z')
    for key in ('authority_sha256','reservation_bytes','source_receipts'):
        wrong=deepcopy(admission)
        setattr(wrong,key,{'changed':True} if key=='source_receipts' else 2048 if key=='reservation_bytes' else 'c'*64)
        with pytest.raises(ApiError):
            check_admission(job,wrong)
    job.method_id='gravity.station-outlier-flags/v1'
    with pytest.raises(ApiError):
        job_view(job)


@pytest.mark.parametrize('name',['../raw.csv','/original.csv','nested/../raw','nested//raw','./raw','C:/secret','a\\b','', 'https://provider/object'])
def test_member_registry_never_interprets_http_paths(name):
    with pytest.raises(ValueError):
        member_path(Path('E:/external/m03'),name)


def test_owned_records_have_fk_unique_state_and_byte_constraints(tmp_path):
    # Schema materialization is isolated test-only, NOT migration-head admission.
    async def run():
        engine=create_async_engine('sqlite+aiosqlite:///'+(tmp_path/'leaf.sqlite').as_posix())
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        sessions=async_sessionmaker(engine,expire_on_commit=False)
        job,admission=example_job()
        async with sessions() as session:
            session.add(job)
            session.add(admission)
            await session.commit()
            original=await session.get(SurveyAdmission,job.id)
            assert original.start_json==admission.start_json
            session.add(SurveyAttempt(id=str(uuid4()),job_id=job.id,ordinal=1,state='claimed',worker_id='fixed-owner',retained_bytes=0,inventory=[]))
            await session.commit()
            rows=(await session.execute(select(SurveyAttempt))).scalars().all()
            assert len(rows)==1 and rows[0].lifetime is None
            session.add(SurveyAttempt(id=str(uuid4()),job_id=job.id,ordinal=1,state='claimed',worker_id='fixed-owner',retained_bytes=0,inventory=[]))
            with pytest.raises(Exception) as failure:
                await session.commit()
            assert 'UNIQUE constraint failed' in str(failure.value)
            await session.rollback()
        await engine.dispose()
    asyncio.run(run())


def test_actual_retained_native_receipt_required_not_boolean():
    for receipt in (True,None,{},dict(schema='m03-local-lifetime/1',verdict='component_pass')):
        with pytest.raises(ApiError):
            validate_drain(receipt)


def test_corrupt_admission_and_native_hashes_are_closed_recovery_errors():
    from tests.api.test_magnetic_line_survey_storage import counter_fixture
    job,admission=example_job()
    for mutation in ({'authority_sha256':'NOT-A-HASH'}, {'start_json':{}}, {'start_json':None}):
        wrong=deepcopy(admission)
        for key,value in mutation.items():
            setattr(wrong,key,value)
        with pytest.raises(ApiError) as error:
            check_admission(job,wrong)
        assert error.value.code=='survey_admission_invalid'
    for mutation in ({'actual_executable_sha256':False}, {'source_sha256':{}},
                     {'source_sha256':{'source.py':'NOT-A-HASH'}}):
        receipt=counter_fixture()
        receipt.update(mutation)
        with pytest.raises(ApiError) as error:
            validate_drain(receipt)
        assert error.value.code=='survey_drain_unverified'


def test_real_sql_queued_cancel_and_foreign_project_method_refusal(registered):  # noqa: F811
    from app.magnetic_line_survey_lifecycle import cancel_owned, owned_job
    from app.models import User
    harness,account,project,_assets,body=registered
    async def run():
        async with harness.app.state.sessions() as session:
            job,_=example_job()
            job.owner_id=UUID(account['id'])
            job.project_id=project['id']
            job.dataset_id=body['dataset_id']
            job.dataset_sha256=body['dataset_sha256']
            session.add(job)
            await session.commit()
            job_id=UUID(job.id)
            user=await session.get(User,UUID(account['id']))
            cancelled=await cancel_owned(session,user,UUID(project['id']),job_id)
            assert cancelled['state']=='cancelled' and cancelled['cancel_requested']
            assert cancelled['started_at'] is None and cancelled['result_sha256'] is None
            assert (await session.get(ProcessingJob,str(job_id))).error_code=='user_cancelled'
            with pytest.raises(ApiError) as missing:
                await owned_job(session,user,uuid4(),job_id)
            assert missing.value.status==404
            await session.rollback()
            original=await session.get(ProcessingJob,str(job_id))
            await session.refresh(user)
            original.method_id='gravity.station-outlier-flags/v1'
            await session.commit()
            with pytest.raises(ApiError) as method:
                await owned_job(session,user,UUID(project['id']),job_id)
            assert method.value.status==404
    asyncio.run(run())


def test_exact_external_inventory_detects_bytes_and_aliases(tmp_path):
    import os
    from app.magnetic_line_survey_lifecycle import collect_inventory
    root=tmp_path/'attempt'
    root.mkdir()
    (root/'result').mkdir()
    (root/'result'/'chunk.bin').write_bytes(b'original actual bytes')
    (root/'stderr.log').write_bytes(b'')
    records=collect_inventory(tmp_path,root)
    assert sum(item['bytes'] for item in records)==21
    assert records[0]['sha256']==sha256(b'original actual bytes')
    os.link(root/'result'/'chunk.bin',root/'alias.bin')
    with pytest.raises(ApiError):
        collect_inventory(tmp_path,root)


def test_inventory_requires_actual_accessible_root_and_rejects_empty_alias(tmp_path):
    import os
    from app.magnetic_line_survey_lifecycle import collect_inventory
    with pytest.raises(ApiError) as missing:
        collect_inventory(tmp_path,tmp_path/'missing')
    assert missing.value.code=='survey_storage_invalid'
    root=tmp_path/'allocated'
    root.mkdir()
    (root/'empty.log').write_bytes(b'')
    assert collect_inventory(tmp_path,root)==[dict(name='empty.log',bytes=0,sha256=sha256(b''))]
    os.link(root/'empty.log',root/'empty-alias.log')
    with pytest.raises(ApiError) as aliased:
        collect_inventory(tmp_path,root)
    assert aliased.value.code=='survey_inventory_mismatch'


def test_publication_document_reads_only_exact_inventory_snapshot(tmp_path):
    from app.magnetic_line_survey_lifecycle import _document,collect_inventory
    root=tmp_path/'attempt'
    root.mkdir()
    path=root/'ready.json'
    path.write_bytes(b'{"status":"kept"}')
    inventory=collect_inventory(tmp_path,root)
    assert _document(root,'ready.json',inventory)=={'status':'kept'}
    path.write_bytes(b'{"status":"fake"}')
    assert path.stat().st_size==inventory[0]['bytes']
    with pytest.raises(ApiError) as changed:
        _document(root,'ready.json',inventory)
    assert changed.value.code=='survey_result_invalid'
    with pytest.raises(ApiError):
        _document(root,'ready.json',[])


def test_long_device_custody_preserves_relative_identity_and_byte_checks(tmp_path):
    from app.magnetic_line_survey_lifecycle import attempt_root, collect_inventory, storage_root, write_cancel_marker
    job,_=example_job()
    attempt=SurveyAttempt(id=str(uuid4()),job_id=job.id,ordinal=1,state='claimed',worker_id='long-path',
        retained_bytes=0,inventory=[])
    storage=tmp_path/('long-external-root-'+'x'*80)
    storage_root(storage).mkdir(parents=True)
    root=attempt_root(storage,job,attempt)
    root.mkdir(parents=True)
    member=root/'result'/'array-native-physical-original-00000000.bin'
    member.parent.mkdir()
    member.write_bytes(b'unchanged byte custody')
    write_cancel_marker(storage,job,attempt)
    records=collect_inventory(storage,root)
    assert [item['name'] for item in records]==['cancel.request','result/array-native-physical-original-00000000.bin']
    assert records[1]['sha256']==sha256(b'unchanged byte custody')
    key=(root/'result/result.json').relative_to(storage_root(storage)).as_posix()
    assert key==f'm03/{job.owner_id}/{job.project_id}/{job.id}/attempts/{attempt.id}/result/result.json'
    assert len(key)==179
