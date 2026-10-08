"""Durable transitions and exact owner member custody, not shared queue assembly.

The fixed executing adapter supplies actual terminal lifetime and exhaustive
inventory. No caller flag, synthetic counter or successful partial Result can
stand in for that native receipt. This leaf does not allocate a migration head.
"""
from __future__ import annotations

import asyncio
from datetime import timezone
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
from uuid import UUID, uuid4

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import ApiError
from app.config import WorkerSettings
from app.magnetic_line_survey_models import SurveyAdmission, SurveyAttempt, SurveyMember
from app.magnetic_line_survey_wire import BoundSurveyFile, OwnedSurveySources, SurveyStart, _hash, _verify_bytes, bind_owned_survey_sources
from app.magnetic_line_survey_wire import _unique_object, _reject_constant, _stamp
from app.models import ProcessingJob, User, utcnow
from app.processing import _owned_job
from app.processing_contract import canonical_bytes, sha256


METHOD = 'magnetic_line_survey_v1'
STATES = {'queued','running','succeeded','failed','cancelled'}
CANCEL_BYTES = b'm03-owner-cancel/1\n'


def job_view(job: ProcessingJob) -> dict:
    if job.method_id != METHOD or job.state not in STATES:
        raise ApiError(409,'survey_state_invalid','Survey lifecycle state is invalid')
    def stamp(value):
        if value is None:
            return None
        # SQLite DateTime reads naive UTC, never interpret local device time.
        if value.tzinfo is None:
            value=value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat().replace('+00:00','Z')
    return dict(schema='m03-owner-job/1',job_id=job.id,project_id=job.project_id,
        dataset_id=job.dataset_id,method=METHOD,state=job.state,cancel_requested=job.cancel_requested,
        request_sha256=job.request_sha256,result_sha256=job.result_sha256,result_bytes=job.result_bytes,
        error_code=job.error_code,created_at=stamp(job.created_at),started_at=stamp(job.started_at),finished_at=stamp(job.finished_at))


async def owned_job(session: AsyncSession, user: User, project_id: UUID, job_id: UUID) -> ProcessingJob:
    job=await _owned_job(session,str(project_id),str(job_id),user)
    if job.method_id != METHOD:
        raise ApiError(404,'not_found','Survey job not found')
    return job


def admitted_envelope(job: ProcessingJob, admission: SurveyAdmission) -> dict:
    try:
        start=SurveyStart.model_validate(admission.start_json).model_dump(mode='json',by_alias=True)
        _hash(admission.authority_sha256)
    except ValueError as exc:
        raise ApiError(409,'survey_admission_invalid','Survey admission differs from its receipt') from exc
    if type(admission.reservation_bytes) is not int or not 0<admission.reservation_bytes<=32*1024**3 or \
       start['dataset_id']!=job.dataset_id or start['dataset_sha256']!=job.dataset_sha256 or admission.job_id!=job.id:
        raise ApiError(409,'survey_admission_invalid','Survey admission differs from its receipt')
    return dict(schema='m03-admitted-request/1',job_id=job.id,owner_id=str(job.owner_id),project_id=job.project_id,
        dataset_id=job.dataset_id,dataset_sha256=job.dataset_sha256,start=start,
        source_receipts=admission.source_receipts,authority_sha256=admission.authority_sha256,
        reservation_bytes=admission.reservation_bytes)


def check_admission(job: ProcessingJob, admission: SurveyAdmission) -> None:
    if job.method_id!=METHOD or job.request_json!=admitted_envelope(job,admission) or \
       job.request_sha256!=sha256(canonical_bytes(job.request_json)):
        raise ApiError(409,'survey_admission_invalid','Survey admission differs from its receipt')


def source_receipts(bound: OwnedSurveySources) -> dict:
    def receipt(item):
        result=dict(id=str(item.id),sha256=item.sha256,bytes=item.byte_count)
        if hasattr(item,'source_id'):
            result.update(source_id=str(item.source_id),rights_decision=item.rights_decision,
                private_storage_permission=item.private_storage_permission)
        return result
    return dict(dataset=receipt(bound.dataset),original=receipt(bound.original),metadata=receipt(bound.metadata),
        request=receipt(bound.request),auxiliaries=[receipt(item) for item in bound.auxiliaries])


async def claim_attempt(session: AsyncSession, settings: WorkerSettings, job_id: UUID,
                        worker_id: str, authority_sha256: str) -> SurveyAttempt | None:
    if type(worker_id) is not str or re.fullmatch(r'[A-Za-z0-9_.-]{1,100}',worker_id) is None:
        raise ValueError('Invalid fixed worker identity')
    await session.rollback()
    await session.execute(text('BEGIN IMMEDIATE'))
    job=await session.get(ProcessingJob,str(job_id))
    if job is None or job.method_id!=METHOD or job.state!='queued' or job.cancel_requested:
        await session.rollback()
        return None
    admission=await session.get(SurveyAdmission,job.id)
    if admission is None:
        raise ApiError(409,'survey_admission_invalid','Survey admission is missing')
    check_admission(job,admission)
    if _hash(authority_sha256)!=admission.authority_sha256:
        raise ApiError(409,'survey_authority_changed','Fixed execution authority differs from admission')
    user=await session.get(User,job.owner_id)
    if user is None or not user.is_active or not user.is_verified:
        raise ApiError(409,'survey_owner_inactive','Survey owner is no longer eligible')
    bound=await bind_owned_survey_sources(session,settings,UUID(job.project_id),user,
        SurveyStart.model_validate(admission.start_json))
    if source_receipts(bound)!=admission.source_receipts:
        raise ApiError(409,'survey_admission_invalid','Survey source parents differ from admission')
    ordinal=(await session.execute(select(func.max(SurveyAttempt.ordinal)).where(SurveyAttempt.job_id==job.id))).scalar_one() or 0
    attempt=SurveyAttempt(id=str(uuid4()),job_id=job.id,ordinal=ordinal+1,state='claimed',worker_id=worker_id,
        started_at=utcnow(),retained_bytes=0,inventory=[])
    session.add(attempt)
    job.state='running'
    job.worker_id=worker_id
    job.started_at=attempt.started_at
    await session.commit()
    return attempt


async def cancel_owned(session: AsyncSession, user: User, project_id: UUID, job_id: UUID) -> dict:
    user_id=user.id
    await owned_job(session,user,project_id,job_id)
    await session.rollback()
    await session.execute(text('BEGIN IMMEDIATE'))
    # Authentication may legitimately use another dependency-owned session.
    # Load the existing principal in THIS transaction, never merge a detached
    # auth object or refresh an instance belonging to a different Session.
    user=await session.get(User,user_id)
    if user is None or not user.is_active or not user.is_verified:
        raise ApiError(404,'not_found','Survey job not found')
    job=await owned_job(session,user,project_id,job_id)
    if job.state in ('queued','running'):
        job.cancel_requested=True
        if job.state=='queued':
            job.state='cancelled'
            job.error_code='user_cancelled'
            job.finished_at=utcnow()
    await session.commit()
    return job_view(job)


def storage_root(storage: Path) -> Path:
    """One internal disk-root spelling, with Windows long-path support."""
    if not storage.is_absolute():
        raise ValueError('External absolute storage is required')
    raw=os.path.abspath(storage)
    if os.name=='nt':
        if raw.startswith('\\\\?\\'):
            raw=raw[4:]
        # This leaf requires local device custody, not UNC/remote mounts.
        if re.match(r'^[A-Za-z]:\\',raw) is None:
            raise ValueError('External device storage is required')
        raw='\\\\?\\'+raw
    root=Path(raw)
    for parent in (root,*root.parents):
        if parent.is_symlink() or getattr(parent,'is_junction',lambda:False)() or (parent/'.git').exists():
            raise ValueError('Unsafe owned storage root')
    for key in ('TEMP','TMP','TMPDIR'):
        value=os.environ.get(key)
        if value:
            temp=os.path.abspath(value)
            if os.name=='nt' and not temp.startswith('\\\\?\\'):
                temp='\\\\?\\'+temp
            if root.is_relative_to(Path(temp)):
                raise ValueError('Device external storage is required')
    return root


def attempt_root(storage: Path, job: ProcessingJob, attempt: SurveyAttempt) -> Path:
    if not storage.is_absolute() or attempt.job_id!=job.id:
        raise ValueError('Invalid owned storage identity')
    identities=[str(job.owner_id),job.project_id,job.id,attempt.id]
    for identity in identities:
        if str(UUID(identity))!=identity:
            raise ValueError('Invalid owned storage identity')
    storage=storage_root(storage)
    root=storage/'m03'/identities[0]/identities[1]/identities[2]/'attempts'/identities[3]
    for parent in (root,*root.parents):
        if parent.is_symlink() or getattr(parent,'is_junction',lambda:False)() or (parent/'.git').exists():
            raise ValueError('Unsafe owned storage root')
        if parent==storage:
            break
    return root


def member_path(root: Path, name: str) -> Path:
    if type(name) is not str or len(name)>240 or '\\' in name or ':' in name:
        raise ValueError('Invalid member identity')
    parts=PurePosixPath(name).parts
    if not parts or name!='/'.join(parts) or any(part in ('.','..') for part in parts) or name.startswith('/'):
        raise ValueError('Invalid member identity')
    path=root.joinpath(*parts)
    if not path.is_relative_to(root):
        raise ValueError('Invalid member identity')
    return path


def write_cancel_marker(storage: Path, job: ProcessingJob, attempt: SurveyAttempt) -> None:
    root=attempt_root(storage,job,attempt)
    if not root.is_dir():
        raise ApiError(409,'survey_attempt_missing','Survey attempt requires recovery')
    marker=root/'cancel.request'
    if marker.exists():
        _verify_bytes(storage_root(storage),marker,sha256(CANCEL_BYTES),len(CANCEL_BYTES),'survey_cancel_integrity_failed')
        return
    pending=root/'cancel.request.pending'
    try:
        with pending.open('xb') as stream:
            stream.write(CANCEL_BYTES)
            stream.flush()
            os.fsync(stream.fileno())
        os.rename(pending,marker)
    except FileExistsError:
        _verify_bytes(storage_root(storage),marker,sha256(CANCEL_BYTES),len(CANCEL_BYTES),'survey_cancel_integrity_failed')


def validate_drain(receipt: dict) -> None:
    # Actual controller receipts contain source/executable pins and all counters.
    required={'schema','verdict','exit_code','cpu_s','peak_rss_bytes','peak_committed_bytes','active_processes',
        'total_processes','wall_s','scratch_bytes','parent_cpu_s','stop_wall_s','stop_cpu_s','source_sha256','actual_executable_sha256','admission'}
    if type(receipt) is not dict or not required<=set(receipt) or receipt['schema']!='m03-local-lifetime/1' or \
       receipt['verdict'] not in ('component_pass','cancelled','resource_refused') or \
       type(receipt['active_processes']) is not int or receipt['active_processes']!=0 or \
       type(receipt['total_processes']) is not int or receipt['total_processes']!=1 or \
       type(receipt['exit_code']) is not int or not 0<=receipt['exit_code']<=2**32-1:
        raise ApiError(409,'survey_drain_unverified','Actual complete attempt drain is required')
    for key,limit in [('cpu_s',21600),('wall_s',43200),('parent_cpu_s',300),
        ('peak_rss_bytes',4*1024**3),('peak_committed_bytes',4*1024**3),('scratch_bytes',32*1024**3)]:
        value=receipt[key]
        if type(value) not in (int,float) or not math.isfinite(value) or value<0 or \
           receipt['verdict']=='component_pass' and not 0<value<=limit:
            raise ApiError(409,'survey_drain_unverified','Actual complete attempt drain is required')
    if receipt['verdict']=='component_pass' and (receipt['exit_code']!=0 or receipt['stop_cpu_s'] is not None or receipt['stop_wall_s'] is not None):
        raise ApiError(409,'survey_drain_unverified','Native completion differs from its receipt')
    if receipt['verdict']=='cancelled':
        for key in ('stop_cpu_s','stop_wall_s'):
            value=receipt[key]
            if type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<=10:
                raise ApiError(409,'survey_drain_unverified','Actual bounded cancellation drain is required')
    try:
        _hash(receipt['actual_executable_sha256'])
        if type(receipt['source_sha256']) is not dict or not receipt['source_sha256']:
            raise ValueError('Missing source pins')
        for value in receipt['source_sha256'].values():
            _hash(value)
    except ValueError as exc:
        raise ApiError(409,'survey_drain_unverified','Actual native source pins are required') from exc


async def record_terminal_attempt(session: AsyncSession, attempt_id: UUID, worker_id: str,
                                  lifetime: dict, inventory: list) -> dict:
    """Persist actual failed/cancelled drain; success still needs publication."""
    validate_drain(lifetime)
    await session.rollback()
    await session.execute(text('BEGIN IMMEDIATE'))
    attempt=await session.get(SurveyAttempt,str(attempt_id))
    job=await session.get(ProcessingJob,attempt.job_id) if attempt else None
    if job is None or job.method_id!=METHOD or job.state!='running' or job.worker_id!=worker_id or \
       attempt.worker_id!=worker_id or attempt.state not in ('claimed','running'):
        raise ApiError(409,'survey_attempt_stale','Survey attempt no longer owns publication')
    # Inventory is fixed worker evidence, never a request body. Exact byte
    # verification belongs to storage reconciliation before reservation release.
    if type(inventory) is not list or len(inventory)>1000000:
        raise ValueError('Invalid finite attempt inventory')
    names=set()
    count=0
    for item in inventory:
        if type(item) is not dict or set(item)!={'name','bytes','sha256'}:
            raise ValueError('Invalid finite attempt inventory')
        member_path(Path('/'),item['name'])
        _hash(item['sha256'])
        if item['name'] in names or type(item['bytes']) is not int or item['bytes']<0:
            raise ValueError('Invalid finite attempt inventory')
        names.add(item['name'])
        count+=item['bytes']
    if count!=lifetime['scratch_bytes']:
        raise ApiError(409,'survey_inventory_mismatch','Actual retained attempt bytes differ')
    attempt.state='drained'
    attempt.lifetime=lifetime
    attempt.inventory=inventory
    attempt.retained_bytes=count
    attempt.finished_at=utcnow()
    job.wall_ms=round(lifetime['wall_s']*1000)
    job.peak_rss_bytes=lifetime['peak_rss_bytes']
    job.scratch_bytes=count
    if lifetime['verdict']!='component_pass':
        job.state='cancelled' if lifetime['verdict']=='cancelled' else 'failed'
        job.error_code='user_cancelled' if job.state=='cancelled' else 'survey_execution_refused'
        job.finished_at=attempt.finished_at
    await session.commit()
    return job_view(job)


async def verified_member(session: AsyncSession, storage: Path, user: User,
                          project_id: UUID, job_id: UUID, member_id: UUID) -> BoundSurveyFile:
    job=await owned_job(session,user,project_id,job_id)
    item=(await session.execute(select(SurveyMember,SurveyAttempt).join(SurveyAttempt).where(
        SurveyMember.id==str(member_id),SurveyAttempt.job_id==job.id,SurveyAttempt.state=='published',
    ))).one_or_none()
    if job.state!='succeeded' or item is None:
        raise ApiError(404,'not_found','Survey member not found')
    member,attempt=item
    try:
        path=member_path(attempt_root(storage,job,attempt),member.relative_name)
        await asyncio.to_thread(_verify_bytes,storage_root(storage),path,member.sha256,member.byte_count,'survey_member_integrity_failed')
    except (OSError,ValueError) as exc:
        raise ApiError(409,'survey_storage_invalid','Survey storage requires recovery') from exc
    return BoundSurveyFile(UUID(member.id),member.sha256,member.byte_count,path)


def collect_inventory(storage: Path, root: Path) -> list:
    """Exact ordinary single-link files; no unknown subtree exemption."""
    storage=storage_root(storage)
    root=storage_root(root)
    if not root.is_relative_to(storage):
        raise ValueError('Invalid owned storage boundary')
    if not root.is_dir():
        raise ApiError(409,'survey_storage_invalid','Survey storage requires recovery')
    inventory=[]
    retained=0
    def walk_error(_exception):
        raise ApiError(409,'survey_storage_invalid','Survey storage requires recovery')
    for directory,folders,files in os.walk(root,followlinks=False,onerror=walk_error):
        for name in folders:
            path=Path(directory)/name
            if path.is_symlink() or getattr(path,'is_junction',lambda:False)():
                raise ApiError(409,'survey_storage_invalid','Survey storage requires recovery')
        for name in sorted(files):
            path=Path(directory)/name
            relative=path.relative_to(root).as_posix()
            member_path(root,relative)
            digest=hashlib.sha256()
            try:
                _ordinary_member_parents(root,path)
                before=_stamp(path.lstat())
                size=before[2]
                # Refuse BEFORE hashing an over-envelope file, including a
                # sparse file. Empty logs receive the same alias/race checks.
                if len(inventory)>=1000000 or retained+size>32*1024**3:
                    raise ValueError('Inventory exceeds envelope')
                count=0
                with path.open('rb') as stream:
                    opened=_stamp(os.fstat(stream.fileno()))
                    if opened[:4]+opened[5:]!=before[:4]+before[5:]:
                        raise ValueError('Storage changed before read')
                    while data:=stream.read(min(1024*1024,size-count+1)):
                        count+=len(data)
                        if count>size:
                            raise ValueError('Storage grew during read')
                        digest.update(data)
                    if _stamp(os.fstat(stream.fileno()))!=opened:
                        raise ValueError('Storage changed during read')
                if count!=size or _stamp(path.lstat())!=before:
                    raise ValueError('Storage changed during read')
                _ordinary_member_parents(root,path)
            except (OSError,ValueError) as exc:
                raise ApiError(409,'survey_inventory_mismatch','Survey storage requires recovery') from exc
            inventory.append(dict(name=relative,bytes=size,sha256=digest.hexdigest()))
            retained+=size
            if len(inventory)>1000000 or retained>32*1024**3:
                raise ApiError(409,'survey_inventory_mismatch','Survey retained inventory exceeds its envelope')
    return sorted(inventory,key=lambda item:item['name'])


def _ordinary_member_parents(root: Path, path: Path) -> None:
    if not path.is_relative_to(root):
        raise ValueError('Invalid member boundary')
    for parent in path.parents:
        if parent.is_symlink() or getattr(parent,'is_junction',lambda:False)() or (parent/'.git').exists():
            raise ValueError('Unsafe member ancestor')
        if parent==root:
            return
    raise ValueError('Missing member boundary')


def _document(root: Path, name: str, inventory: list) -> dict:
    """Parse the exact bounded inventory snapshot, not a pathname reopened blind."""
    path=member_path(root,name)
    matches=[item for item in inventory if item['name']==name]
    if len(matches)!=1 or not 0<matches[0]['bytes']<=2097152:
        raise ApiError(409,'survey_result_invalid','Survey result receipt is invalid')
    try:
        receipt=matches[0]
        _ordinary_member_parents(root,path)
        before=_stamp(path.lstat())
        with path.open('rb') as stream:
            opened=_stamp(os.fstat(stream.fileno()))
            if opened[:4]+opened[5:]!=before[:4]+before[5:] or before[2]!=receipt['bytes']:
                raise ValueError('Storage changed before read')
            raw=stream.read(receipt['bytes']+1)
            if _stamp(os.fstat(stream.fileno()))!=opened:
                raise ValueError('Storage changed during read')
        if len(raw)!=receipt['bytes'] or sha256(raw)!=receipt['sha256'] or _stamp(path.lstat())!=before:
            raise ValueError('Document differs from inventory')
        _ordinary_member_parents(root,path)
        result=json.loads(raw.decode('utf-8',errors='strict'),object_pairs_hook=_unique_object,parse_constant=_reject_constant)
        if type(result) is not dict:
            raise ValueError('Invalid object')
        return result
    except (OSError,ValueError,RecursionError) as exc:
        raise ApiError(409,'survey_result_invalid','Survey result receipt is invalid') from exc


def _publication_receipts(result: dict, ready: dict, actual: dict, original: BoundSurveyFile,
                          fitted: dict, fit_receipt: dict) -> None:
    """Bind readiness to completed epoch/rows/parents without relabeling science.

    This is a custody fence after the fixed native semantic verifier, NOT a
    replacement for whole Result/DAG/model verification or a new fit policy.
    """
    try:
        epoch=result['policy_epoch']
        resolution=epoch=='resolution_v2'
        if epoch not in ('resolution_v2','fixed_basis_v1') or \
           type(result['fit']['fit_count']) is not int or result['fit']['fit_count']!=(97 if resolution else 25) or \
           type(result['inventory']['original_rows']) is not int or not 0<result['inventory']['original_rows']<=8000000 or \
           result['input']['original']['csv_sha256']!=original.sha256 or \
           result['input']['original']['csv_bytes']!=original.byte_count:
            raise ValueError('Result completion differs from original')
        if fitted['schema']!=('m03-global-physical-fit/2' if resolution else 'm03-global-physical-fit/1') or \
           fitted['original']!=result['input']['original'] or fitted['rows']!=result['inventory']['original_rows'] or \
           type(fitted['rows']) is not int or type(fitted['evaluation_count']) is not int or \
           fitted['evaluation_count']!=1 or fitted['fit']!=result['fit'] or \
           fitted['geometry_sha256']!=sha256(canonical_bytes(result['geometry'])):
            raise ValueError('Physical fit differs from completed Result')
        common=dict(result_sha256=actual['sha256'],rows=result['inventory']['original_rows'],policy_epoch=epoch)
        if resolution:
            expected=dict(schema='m03-resolution-fit-ready/1',**common,original=result['input']['original'],
                fit_count=97,evaluation_count=1,outer_status='opened_authored_diagnostic',field_acceptance='unresolved',
                full_result='assembled',host_admission='not_established')
            # This is the exact full physical-fit document hash, NOT a hash of
            # Result.fit (a distinct subobject/domain).
            expected['fit_sha256']=_hash(fit_receipt['sha256'])
        else:
            expected=dict(schema='m03-full-result-ready/1',**common,scientific_verdict=result['verdict']['overall'])
        if ready!=expected or type(ready['rows']) is not int or \
           resolution and (type(ready['fit_count']) is not int or type(ready['evaluation_count']) is not int):
            raise ValueError('Readiness differs from completed Result')
    except (KeyError,TypeError,ValueError) as exc:
        raise ApiError(409,'survey_result_invalid','Survey result differs from its original parents') from exc


async def publish_drained_result(session: AsyncSession, settings: WorkerSettings, attempt_id: UUID,
                                 worker_id: str, authority_sha256: str, source_sha256: dict) -> dict:
    """Fence actual full native output; no HTTP-supplied result or counter body.

    Both fixed authority inputs come from parent-owned runtime configuration.
    Publication uncertainty retains the committed drained attempt and its files.
    The shared dispatcher must rebind that authority before actual execution.
    """
    await session.rollback()
    await session.execute(text('BEGIN IMMEDIATE'))
    attempt=await session.get(SurveyAttempt,str(attempt_id))
    job=await session.get(ProcessingJob,attempt.job_id) if attempt else None
    if job is None or job.method_id!=METHOD or job.state!='running' or job.worker_id!=worker_id or \
       attempt.worker_id!=worker_id or attempt.state!='drained':
        raise ApiError(409,'survey_attempt_stale','Survey attempt no longer owns publication')
    if job.cancel_requested:
        # Native work has already drained; preserve successful numerical bytes
        # but do not publish a cancellation-raced execution as succeeded.
        job.state='cancelled'
        job.error_code='user_cancelled'
        job.finished_at=utcnow()
        await session.commit()
        return job_view(job)
    admission=await session.get(SurveyAdmission,job.id)
    if admission is None:
        raise ApiError(409,'survey_admission_invalid','Survey admission is missing')
    check_admission(job,admission)
    validate_drain(attempt.lifetime)
    if attempt.lifetime['verdict']!='component_pass' or admission.authority_sha256!=_hash(authority_sha256) or \
       attempt.lifetime['source_sha256']!=source_sha256:
        raise ApiError(409,'survey_authority_changed','Fixed native receipt differs from admission')
    user=await session.get(User,job.owner_id)
    if user is None or not user.is_active or not user.is_verified:
        raise ApiError(409,'survey_owner_inactive','Survey owner is no longer eligible')
    bound=await bind_owned_survey_sources(session,settings,UUID(job.project_id),user,SurveyStart.model_validate(admission.start_json))
    if source_receipts(bound)!=admission.source_receipts:
        raise ApiError(409,'survey_admission_invalid','Survey source parents differ from admission')
    root=attempt_root(settings.data_dir,job,attempt)
    inventory=await asyncio.to_thread(collect_inventory,settings.data_dir,root)
    if inventory!=attempt.inventory or sum(item['bytes'] for item in inventory)!=attempt.retained_bytes:
        raise ApiError(409,'survey_inventory_mismatch','Actual retained attempt bytes differ')
    result=_document(root,'result/result.json',inventory)
    if result.get('schema')!='magnetic-line-survey-result/2' or result.get('run_id')!=job.id:
        raise ApiError(409,'survey_result_invalid','Survey result identity differs from its job')
    # The fixed full native producer independently validates all result/DAG/
    # selected-model/grid semantics before writing readiness. This publication
    # fence is additional DB/file custody, not a substitute numerical verifier.
    resolution=result.get('policy_epoch')=='resolution_v2'
    ready=_document(root,'resolution-fit-ready.json' if resolution else 'result-ready.json',inventory)
    actual=next((item for item in inventory if item['name']=='result/result.json'),None)
    if actual is None:
        raise ApiError(409,'survey_result_invalid','Survey result differs from its original parents')
    fitted=_document(root,'fit/physical-fit.json',inventory)
    fit_receipt=next(item for item in inventory if item['name']=='fit/physical-fit.json')
    _publication_receipts(result,ready,actual,bound.original,fitted,fit_receipt)
    for role,parent in [('metadata',bound.metadata),('request',bound.request)]:
        await asyncio.to_thread(_verify_bytes,storage_root(settings.data_dir),root/'result'/(role+'.json'),
            parent.sha256,parent.byte_count,'survey_result_invalid')
    members=[]
    for item in inventory:
        if item['name'].startswith('result/'):
            if item['bytes']<=0:
                raise ApiError(409,'survey_result_invalid','Empty scientific member is invalid')
            leaf=PurePosixPath(item['name']).name
            kind='result' if item['name']=='result/result.json' else 'manifest' if leaf.endswith('.json') else \
                'page' if leaf.endswith('.jsonl') else 'chunk' if leaf.endswith('.bin') else 'receipt'
            member=SurveyMember(id=str(uuid4()),attempt_id=attempt.id,relative_name=item['name'],
                byte_count=item['bytes'],sha256=item['sha256'],kind=kind)
            session.add(member)
            members.append(member)
    if not members:
        raise ApiError(409,'survey_result_invalid','Full scientific member inventory is missing')
    job.result_key=(root/'result/result.json').relative_to(storage_root(settings.data_dir)).as_posix()
    job.result_sha256=actual['sha256']
    job.result_bytes=actual['bytes']
    job.state='succeeded'
    job.finished_at=utcnow()
    attempt.state='published'
    try:
        await session.commit()
    except Exception:
        # Do not delete any files or infer rollback outcome. The separately
        # committed drained attempt/inventory retains quota and recovery debt.
        await session.rollback()
        raise
    return job_view(job)
