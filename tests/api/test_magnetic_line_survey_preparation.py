"""Actual intake UUIDs and committed preparation fence, NOT scientific admission.

Dataset/job assembly below is an explicit test-only SQL fixture: parent owns
the real fixed authority/dataset publication seam and combined queue assembly.
"""
import asyncio
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from app.config import WorkerSettings
from app.errors import ApiError
from app.magnetic_line_survey_lifecycle import (
    METHOD, admitted_envelope, attempt_root, claim_attempt, source_receipts,
)
from app.magnetic_line_survey_models import SurveyAdmission, SurveyAttempt
from app.magnetic_line_survey_preparation import prepare_intake_plan
from app.magnetic_line_survey_wire import SurveyStart, bind_owned_survey_sources
from app.models import ObservationDataset, ProcessingJob, RawAsset, User
from app.processing_contract import canonical_bytes, dataset_key, sha256
from tests.api.test_magnetic_line_survey_intake import header, install, upload, bundle


def test_claim_and_registered_roles_precede_plan_allocation(make_harness, monkeypatch):
    harness = make_harness(); install(harness)
    account = harness.account(); project = harness.project()['id']; owner = UUID(account['id'])
    uploaded = []
    # Real cookie/CSRF/upload custody. Bytes are non-scientific strict-role
    # boundary controls, not a fabricated field or numerical workflow.
    for role, body in [('original_csv', b'opaque original control'), ('metadata_json', b'{}'),
            ('request_json', b'{}'), ('typed_auxiliary_bundle', bundle([('unknown', b'abc')]))]:
        response = upload(harness, project, body, header(body, role))
        assert response.status_code == 201, response.text
        uploaded.append(response.json())
    settings = WorkerSettings(harness.settings.data_dir, harness.settings.db_path)
    authority = 'b'*64  # Explicit test assembly pin, never a host grant.
    async def setup():
        async with harness.app.state.sessions.kw['bind'].begin() as connection:
            for table in (SurveyAdmission.__table__, SurveyAttempt.__table__):
                await connection.run_sync(table.create, checkfirst=True)
        async with harness.app.state.sessions() as session:
            dataset_id, job_id = str(uuid4()), str(uuid4())
            descriptor = canonical_bytes(dict(schema='m03-test-preparation-parent/1', original=uploaded[0]['sha256']))
            key = dataset_key(str(owner), project, dataset_id)
            target = settings.data_dir/key; target.parent.mkdir(parents=True); target.write_bytes(descriptor)
            dataset = ObservationDataset(id=dataset_id, project_id=project, owner_id=owner,
                raw_asset_id=uploaded[0]['asset_id'], version=1, parser_version='m03-test-preparation-parent/1',
                modality='magnetic_line_survey', row_count=1, raw_sha256=uploaded[0]['sha256'],
                sha256=sha256(descriptor), byte_count=len(descriptor), storage_key=key)
            session.add(dataset); await session.commit()
            start = SurveyStart.model_validate(dict(schema='m03-owner-start/1', dataset_id=dataset_id,
                dataset_sha256=dataset.sha256, original_asset_id=uploaded[0]['asset_id'], original_sha256=uploaded[0]['sha256'],
                metadata_asset_id=uploaded[1]['asset_id'], metadata_sha256=uploaded[1]['sha256'],
                request_asset_id=uploaded[2]['asset_id'], request_sha256=uploaded[2]['sha256'],
                auxiliary_asset_ids=[uploaded[3]['asset_id']], auxiliary_sha256=[uploaded[3]['sha256']]))
            user = await session.get(User, owner)
            bound = await bind_owned_survey_sources(session, settings, UUID(project), user, start)
            job = ProcessingJob(id=job_id, project_id=project, owner_id=owner, dataset_id=dataset_id,
                dataset_sha256=dataset.sha256, method_id=METHOD, state='queued', cancel_requested=False,
                request_json={}, request_sha256='0'*64, preflight={})
            admission = SurveyAdmission(job_id=job_id, start_json=start.model_dump(mode='json', by_alias=True),
                source_receipts=source_receipts(bound), authority_sha256=authority, reservation_bytes=32*1024**3)
            job.request_json = admitted_envelope(job, admission); job.request_sha256 = sha256(canonical_bytes(job.request_json))
            session.add(job); await session.flush(); session.add(admission); await session.commit()
            attempt = await claim_attempt(session, settings, UUID(job_id), 'owned-preparation', authority)
            job = await session.get(ProcessingJob, job_id)
            return UUID(attempt.id), job_id, attempt_root(settings.data_dir, job, attempt)
    attempt_id, job_id, root = asyncio.run(setup())
    assert not root.exists()

    async def refusals():
        async with harness.app.state.sessions() as session:
            for worker, pin in [('other-worker', authority), ('owned-preparation', 'c'*64)]:
                with pytest.raises(ApiError): await prepare_intake_plan(session, settings, attempt_id, worker, pin)
                await session.rollback(); assert not root.exists()
            raw = await session.get(RawAsset, uploaded[1]['asset_id'])
            original = raw.detected_format; raw.detected_format = 'magnetic_csv'; await session.commit()
            with pytest.raises(ApiError) as failure:
                await prepare_intake_plan(session, settings, attempt_id, 'owned-preparation', authority)
            assert failure.value.code == 'survey_source_role_invalid'
            await session.rollback(); raw = await session.get(RawAsset, uploaded[1]['asset_id'])
            raw.detected_format = original; await session.commit()
            job = await session.get(ProcessingJob, job_id); job.cancel_requested = True; await session.commit()
            with pytest.raises(ApiError): await prepare_intake_plan(session, settings, attempt_id, 'owned-preparation', authority)
            await session.rollback(); job = await session.get(ProcessingJob, job_id)
            job.cancel_requested = False; await session.commit()
    asyncio.run(refusals())

    original_mkdir = Path.mkdir
    def observed_mkdir(path, *args, **kwargs):
        if path == root:
            async def another_transaction():
                async with harness.app.state.sessions() as second:
                    row = await second.get(SurveyAttempt, str(attempt_id))
                    assert row.state == 'running' and row.lifetime is None
                    assert not root.exists()
            asyncio.run(another_transaction())
        return original_mkdir(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'mkdir', observed_mkdir)
    async def prepare():
        async with harness.app.state.sessions() as session:
            path = await prepare_intake_plan(session, settings, attempt_id, 'owned-preparation', authority)
            assert path == root/'preparation-plan.json' and path.exists()
            import json
            plan = json.loads(path.read_bytes())
            assert set(plan) == {'schema', 'original', 'metadata', 'request', 'bundles'}
            assert plan['original']['sha256'] == uploaded[0]['sha256']
            assert plan['bundles'][0]['sha256'] == uploaded[3]['sha256']
            with pytest.raises(ApiError): await prepare_intake_plan(session, settings, attempt_id, 'owned-preparation', authority)
            await session.rollback()
            assert (await session.get(ProcessingJob, job_id)).state == 'running'
            assert (await session.get(SurveyAttempt, str(attempt_id))).lifetime is None
            # Plan/claim is real, but no native or Result status is fabricated.
    asyncio.run(prepare())
