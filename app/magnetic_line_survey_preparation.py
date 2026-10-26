"""Claimed owner intake preparation assembly, not queue/host activation.

Parent invokes the fixed native controller and records the actual drained
inventory. This function cannot publish a Result or accept HTTP authority.
"""
from __future__ import annotations

import asyncio
import os
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import WorkerSettings
from app.errors import ApiError
from app.magnetic_line_survey_intake import SurveyAssetHeader
from app.magnetic_line_survey_lifecycle import (
    attempt_root, check_admission, source_receipts, storage_root,
)
from app.magnetic_line_survey_models import SurveyAdmission, SurveyAttempt, SurveyIntake
from app.magnetic_line_survey_wire import SurveyStart, _hash, bind_owned_survey_sources
from app.models import ProcessingJob, RawAsset, SourceRecord, User
from app.processing_contract import canonical_bytes


def _refuse(code='survey_preparation_refused'):
    raise ApiError(409, code, 'Survey preparation requires exact admitted custody')


async def prepare_intake_plan(session: AsyncSession, settings: WorkerSettings,
                              attempt_id: UUID, worker_id: str, authority_sha256: str):
    """Rebind committed real parents, fence once, THEN allocate immutable plan.

    Returning a plan does not grant native execution: parent must consume its
    actual fixed configuration authority and enforce the whole attempt envelope.
    Interrupted plan allocation stays running debt, never an automatic retry.
    """
    storage_root(settings.data_dir)
    await session.rollback()
    await session.execute(text('BEGIN IMMEDIATE'))
    attempt = await session.get(SurveyAttempt, str(attempt_id))
    if attempt is None or attempt.state != 'claimed' or attempt.worker_id != worker_id: _refuse()
    job = await session.get(ProcessingJob, attempt.job_id)
    admission = await session.get(SurveyAdmission, attempt.job_id)
    if job is None or admission is None or job.state != 'running' or job.cancel_requested or job.worker_id != worker_id: _refuse()
    check_admission(job, admission)
    if _hash(authority_sha256) != admission.authority_sha256: _refuse('survey_authority_changed')
    # Complete attempt reservation, not an 8 MiB or phase-only fallback.
    if admission.reservation_bytes != 32*1024**3: _refuse('survey_reservation_invalid')
    user = await session.get(User, job.owner_id)
    if user is None or not user.is_active or not user.is_verified: _refuse('survey_owner_inactive')
    bound = await bind_owned_survey_sources(session, settings, UUID(job.project_id), user,
        SurveyStart.model_validate(admission.start_json))
    if source_receipts(bound) != admission.source_receipts: _refuse()
    bundles = []
    for item, required in [(bound.original, 'original_csv'), (bound.metadata, 'metadata_json'),
                           (bound.request, 'request_json'), *((item, None) for item in bound.auxiliaries)]:
        raw = await session.get(RawAsset, str(item.id))
        intake = await session.get(SurveyIntake, str(item.id))
        if raw is None or intake is None or intake.state != 'published' or intake.asset_id != raw.id or \
           intake.owner_id != user.id or intake.project_id != job.project_id or \
           raw.validation_status != 'm03_bytes_custodied' or raw.detected_format != 'm03_'+intake.role or \
           raw.physical_metadata != dict(schema='m03-owner-asset/1', role=intake.role) or \
           (required is not None and intake.role != required): _refuse('survey_source_role_invalid')
        try: header = SurveyAssetHeader.model_validate(intake.header_json)
        except ValueError: _refuse('survey_source_role_invalid')
        source = await session.get(SourceRecord, str(item.source_id))
        if source is None or source.declared_format != raw.detected_format or header.role != intake.role or \
           header.source.expected_bytes != raw.byte_count or header.source.expected_sha256 != raw.sha256 or \
           header.filename != raw.filename or header.mime != raw.client_mime or \
           intake.retained_bytes != 0 or intake.inventory or source.rights_decision != 'mirror' or \
           source.private_storage_permission != 'attested': _refuse('survey_source_role_invalid')
        if any(getattr(source, key) != getattr(header.source, key) for key in
               ('provider', 'doi', 'citation', 'rights_statement', 'rights_decision', 'attribution')):
            _refuse('survey_source_role_invalid')
        if intake.role == 'typed_auxiliary_bundle': bundles.append(item)
        elif required is None and intake.role not in ('navigation_original', 'base_original',
                'calibration_original', 'reference_original', 'offset_original'): _refuse('survey_source_role_invalid')
    if not bundles: _refuse('survey_bundle_missing')
    def entry(item): return dict(path=str(item.path), bytes=item.byte_count, sha256=item.sha256)
    plan = dict(schema='m03-owner-preparation-plan/1', original=entry(bound.original),
        metadata=entry(bound.metadata), request=entry(bound.request), bundles=[entry(item) for item in bundles])
    root = attempt_root(settings.data_dir, job, attempt)
    if root.exists(): _refuse('survey_attempt_requires_recovery')
    attempt.state = 'running'
    await session.commit()  # Another transaction can observe this before mkdir.
    def write():
        root.mkdir(parents=True, exist_ok=False)
        path = root/'preparation-plan.json'
        with path.open('xb') as stream:
            stream.write(canonical_bytes(plan)); stream.flush(); os.fsync(stream.fileno())
        return path
    return await asyncio.to_thread(write)
