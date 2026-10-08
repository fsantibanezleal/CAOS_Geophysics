"""Exact M03 debt and read-only recovery/delete preparation, not shared hooks.

Parent accounting must exclude M03's generic fallback first. No missing receipt
is a zero-byte job, and no function here destroys evidence or asserts OS drain.
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import WorkerSettings
from app.errors import ApiError
from app.magnetic_line_survey_lifecycle import (
    METHOD, attempt_root, check_admission, collect_inventory, member_path,
    source_receipts, storage_root, validate_drain,
)
from app.magnetic_line_survey_models import SurveyAdmission, SurveyAttempt, SurveyExportRecord, SurveyMember
from app.magnetic_line_survey_wire import SurveyStart, bind_owned_survey_sources
from app.models import ProcessingJob, User
from app.projects import _owned_project


def _refuse():
    raise ApiError(409,'survey_recovery_required','Survey custody requires exact recovery')


def _retained(attempt:SurveyAttempt) -> int:
    if type(attempt.retained_bytes) is not int or attempt.retained_bytes<0:
        _refuse()
    if attempt.lifetime is None:
        if attempt.state not in ('claimed','running','publication_uncertain'):
            _refuse()
        return attempt.retained_bytes
    validate_drain(attempt.lifetime)
    if attempt.retained_bytes!=attempt.lifetime['scratch_bytes'] or attempt.state not in ('drained','publication_uncertain','published'):
        _refuse()
    return attempt.retained_bytes


async def account_m03_custody_usage(session:AsyncSession,owner_id:UUID) -> int:
    """M03 subtotal only; old attempts and uncertain reservation remain debt."""
    jobs=(await session.execute(select(ProcessingJob).where(ProcessingJob.owner_id==owner_id,
        ProcessingJob.method_id==METHOD))).scalars().all()
    total=0
    for job in jobs:
        admission=await session.get(SurveyAdmission,job.id)
        if admission is None:
            _refuse()
        check_admission(job,admission)
        attempts=(await session.execute(select(SurveyAttempt).where(SurveyAttempt.job_id==job.id))).scalars().all()
        if not attempts:
            if job.state=='queued':
                total+=admission.reservation_bytes
            elif job.state!='cancelled' or job.started_at is not None:
                _refuse()
        for attempt in attempts:
            retained=_retained(attempt)
            released=attempt.lifetime is not None and (attempt.state=='published' or
                attempt.state=='drained' and job.state in ('failed','cancelled'))
            total+=retained if released else max(admission.reservation_bytes,retained)
    return total


def exact_namespace(storage:Path,root:Path,expected:list[dict]) -> None:
    """Reject unknown EMPTY directories too, not just unknown regular files."""
    storage,root=storage_root(storage),storage_root(root)
    if not root.is_relative_to(storage):
        _refuse()
    files={member_path(root,item['name']) for item in expected}
    if len(files)!=len(expected):
        _refuse()
    directories=set()
    for file in files:
        for parent in file.parents:
            if parent==root:
                break
            if not parent.is_relative_to(root):
                _refuse()
            directories.add(parent)
    if not files:
        if root.exists():
            _refuse()
        return
    if not root.is_dir():
        _refuse()
    observed_files,observed_dirs=set(),set()
    def error(_exception):
        _refuse()
    for directory,folders,names in os.walk(root,followlinks=False,onerror=error):
        for name in folders+names:
            path=Path(directory)/name
            if path.is_symlink() or getattr(path,'is_junction',lambda:False)():
                _refuse()
            (observed_dirs if name in folders else observed_files).add(path)
    if observed_files!=files or observed_dirs!=directories:
        _refuse()
    if collect_inventory(storage,root)!=sorted(expected,key=lambda item:item['name']):
        _refuse()


async def reconcile_m03_project(session:AsyncSession,settings:WorkerSettings,user:User,
                                project_id:UUID,*,for_deletion:bool=False) -> dict:
    """Exact scoped evidence; no mutation, automatic retry or absent-counter pass."""
    await _owned_project(session,str(project_id),user)
    root=storage_root(settings.data_dir)/'m03'/str(user.id)/str(project_id)
    jobs=(await session.execute(select(ProcessingJob).where(ProcessingJob.owner_id==user.id,
        ProcessingJob.project_id==str(project_id),ProcessingJob.method_id==METHOD))).scalars().all()
    expected=[]
    for job in jobs:
        if for_deletion and job.state in ('queued','running'):
            raise ApiError(409,'project_jobs_active','Finish actual survey drain before project deletion')
        admission=await session.get(SurveyAdmission,job.id)
        if admission is None:
            _refuse()
        check_admission(job,admission)
        bound=await bind_owned_survey_sources(session,settings,project_id,user,SurveyStart.model_validate(admission.start_json))
        if source_receipts(bound)!=admission.source_receipts:
            _refuse()
        attempts=(await session.execute(select(SurveyAttempt).where(SurveyAttempt.job_id==job.id)
            .order_by(SurveyAttempt.ordinal))).scalars().all()
        if job.state=='running' or job.state=='succeeded' and not attempts:
            _refuse()
        published=0
        for attempt in attempts:
            if attempt.lifetime is None or attempt.state not in ('drained','published'):
                _refuse()
            count=_retained(attempt)
            attempt_directory=attempt_root(settings.data_dir,job,attempt)
            inventory=await asyncio.to_thread(collect_inventory,settings.data_dir,attempt_directory)
            if inventory!=attempt.inventory or sum(item['bytes'] for item in inventory)!=count:
                _refuse()
            members=(await session.execute(select(SurveyMember).where(SurveyMember.attempt_id==attempt.id))).scalars().all()
            exports=(await session.execute(select(SurveyExportRecord).where(SurveyExportRecord.attempt_id==attempt.id))).scalars().all()
            # Export registration/exhaustive accounting has its own next review
            # contract. Never exempt stored export rows pending that service.
            if exports:
                _refuse()
            if attempt.state=='published':
                published+=1
                if job.state!='succeeded' or attempt.lifetime['verdict']!='component_pass':
                    _refuse()
                actual={item['name']:item for item in inventory if item['name'].startswith('result/')}
                if len(members)!=len(actual) or len({item.relative_name for item in members})!=len(members):
                    _refuse()
                for member in members:
                    receipt=actual.get(member.relative_name)
                    if receipt is None or (member.byte_count,member.sha256)!=(receipt['bytes'],receipt['sha256']):
                        _refuse()
                results=[member for member in members if member.kind=='result']
                if len(results)!=1 or results[0].relative_name!='result/result.json' or \
                   job.result_key!=(attempt_directory/'result/result.json').relative_to(storage_root(settings.data_dir)).as_posix() or \
                   (job.result_bytes,job.result_sha256)!=(results[0].byte_count,results[0].sha256):
                    _refuse()
            elif members:
                _refuse()
            prefix=attempt_directory.relative_to(root).as_posix()
            expected.extend(dict(name=prefix+'/'+item['name'],bytes=item['bytes'],sha256=item['sha256']) for item in inventory)
        if (job.state=='succeeded')!=(published==1) or published>1:
            _refuse()
    await asyncio.to_thread(exact_namespace,settings.data_dir,root,expected)
    return dict(schema='m03-project-custody/1',owner_id=str(user.id),project_id=str(project_id),
        retained_bytes=sum(item['bytes'] for item in expected),inventory=sorted(expected,key=lambda item:item['name']),
        mutation='none',deletion_preparation=for_deletion)
