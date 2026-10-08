"""Actual retained ZIP/SQL excluded-reader controls; portable, not Linux proof."""
import asyncio
import copy
import hashlib

import pytest
from sqlalchemy import select

from app.errors import ApiError
from app.magnetic_custody import install_replay, zip_result_path
from app.magnetic_custody_owner import reconcile_attempts, SCHEMA
from app.magnetic_line_survey_models import SurveyDatasetAttempt
from app.processing_contract import canonical_bytes
from tests.api.test_magnetic_owned_custody import actual_generation as retained_generation, seeded


@pytest.fixture(scope="module")
def actual_generation():
    return retained_generation.__wrapped__()


def test_genuine_zip_startup_and_closed_mutations(tmp_path, actual_generation):
    async def gate():
        engine, sessions, settings, user, dataset, _, scratch = await seeded(tmp_path, actual_generation)
        binding = sessions.kw['info']['magnetic_custody_owner']
        physical = binding.physical
        try:
            async with sessions() as session:
                job = await install_replay(session, settings, user, dataset.id, actual_generation[0],
                    project_id=dataset.project_id, temp_root=scratch)
            async with sessions() as session, physical.leases.acquire(exclusive=True), physical.worker.acquire_processing():
                initial = await reconcile_attempts(session, binding, settings)
                assert initial == dict(schema="magnetic-owned-custody-reconciliation-1", attempts=1,
                    retained_bytes=0, unhandled_m03_attempt_ids=[])
                row = (await session.execute(select(SurveyDatasetAttempt))).scalar_one()
                from app.models import ProcessingJob
                persisted = await session.get(ProcessingJob, job.id)
                original_lifetime, original_request, original_input = copy.deepcopy(row.lifetime), copy.deepcopy(persisted.request_json), copy.deepcopy(row.input_json)
                archive = zip_result_path(settings, persisted.result_key)
                archive_raw = archive.read_bytes()

                for attack in ('integer_lifetime', 'unknown_input', 'request', 'preflight', 'generation', 'zip_corrupt', 'unknown_stage', 'debt'):
                    previous_preflight = copy.deepcopy(persisted.preflight)
                    previous_state = row.state
                    previous_request_sha = persisted.request_sha256
                    previous_result_sha, previous_result_bytes = persisted.result_sha256, persisted.result_bytes
                    if attack == 'integer_lifetime': row.lifetime = {**row.lifetime, 'work_completed':1}
                    if attack == 'unknown_input': row.input_json = {**row.input_json, 'schema':'unknown-owner-must-refuse'}
                    if attack == 'request':
                        persisted.request_json = {**persisted.request_json, 'unknown':True}
                        persisted.request_sha256 = hashlib.sha256(canonical_bytes(persisted.request_json)).hexdigest()
                    if attack == 'zip_corrupt':
                        archive.write_bytes(b'not a valid numeric ZIP')  # this test's owned result only
                        persisted.result_sha256 = hashlib.sha256(archive.read_bytes()).hexdigest()
                        persisted.result_bytes = archive.stat().st_size
                    if attack == 'preflight': persisted.preflight = {**persisted.preflight, 'unknown':True}
                    if attack == 'generation':
                        drifted_binding = {**persisted.preflight['magnetic_binding'], 'generation_sha256':'0'*64}
                        persisted.preflight = {**persisted.preflight, 'magnetic_binding':drifted_binding}
                        persisted.request_json = {**persisted.request_json,
                            'parameters':{**persisted.request_json['parameters'], 'generation_sha256':'0'*64}}
                        persisted.request_sha256 = hashlib.sha256(canonical_bytes(persisted.request_json)).hexdigest()
                    if attack == 'unknown_stage': (scratch/'unknown-keep').write_bytes(b'untouched')
                    if attack == 'debt': row.state = 'failed'
                    await session.flush()
                    with pytest.raises(ApiError):
                        await reconcile_attempts(session, binding, settings)
                    if attack == 'unknown_stage':
                        assert (scratch/'unknown-keep').read_bytes() == b'untouched'
                        (scratch/'unknown-keep').unlink()  # authored test bytes only
                    row.lifetime, row.input_json = copy.deepcopy(original_lifetime), copy.deepcopy(original_input)
                    row.state = previous_state
                    persisted.request_json, persisted.request_sha256 = copy.deepcopy(original_request), previous_request_sha
                    persisted.preflight = previous_preflight
                    if attack == 'zip_corrupt': archive.write_bytes(archive_raw)
                    persisted.result_sha256, persisted.result_bytes = previous_result_sha, previous_result_bytes
                    await session.flush()

                # Known M03 records are delegated, never claimed as M04 proof.
                row.input_json = {**row.input_json, 'schema':'m03-owner-dataset-request/1'}
                await session.flush()
                delegated = await reconcile_attempts(session, binding, settings)
                assert delegated['attempts'] == 0 and delegated['unhandled_m03_attempt_ids'] == [row.id]
                row.input_json = original_input
                await session.flush()
                assert row.input_json['schema'] == SCHEMA
        finally:
            await engine.dispose()
    asyncio.run(gate())


def test_nonexclusive_reader_refuses_before_census(tmp_path, actual_generation):
    async def gate():
        engine, sessions, settings, _, _, _, _ = await seeded(tmp_path, actual_generation)
        owner = sessions.kw['info']['magnetic_custody_owner']
        try:
            async with sessions() as session, owner.physical.worker.acquire_processing():
                with pytest.raises(AssertionError):
                    await reconcile_attempts(session, owner, settings)
        finally:
            await engine.dispose()
    asyncio.run(gate())
