"""Durable two-phase owner dataset birth, without a mounted/shared default.

201 means actual descriptor publication, never a claimed UUID or geometry
receipt masquerading as scientific/field success. Interrupted bytes are debt.
"""
from __future__ import annotations

import asyncio
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import time
from uuid import UUID,uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.errors import ApiError
from app.magnetic_line_survey_dataset_accounting import (
    INSPECTION_BYTES,DatasetBaseLedger,DeviceReservationLedger,dataset_attempt_root,
    dataset_source_receipts,reserve_dataset_inspection,reserve_dataset_preparation,
)
from app.magnetic_line_survey_dataset_controller import WindowsPreparationController,PreparationAuthority
from app.magnetic_line_survey_lifecycle import collect_inventory,storage_root,validate_drain
from app.magnetic_line_survey_models import SurveyDatasetAttempt,SurveyIntake
from app.magnetic_line_survey_wire import (
    SurveyDatasetRequest,_hash,_reject_constant,_unique_object,_verify_bytes,bind_owned_dataset_inputs,
)
from app.models import ObservationDataset,User,utcnow
from app.processing_contract import canonical_bytes,dataset_key,checked_derived_path

PARSER='m03-original-geometry/1'


def _refuse(code='survey_dataset_integrity_failed'):
    raise ApiError(409,code,'Dataset preparation requires exact custody and recovery')


def _read(path:Path,*,canonical:bool=True)->dict:
    if path.is_symlink() or getattr(path,'is_junction',lambda:False)() or not path.is_file() or path.stat().st_size>2097152:_refuse()
    with path.open('rb') as stream:raw=stream.read(2097153)
    if len(raw)>2097152:_refuse()
    try:
        parsed=json.loads(raw.decode('utf-8'),object_pairs_hook=_unique_object,parse_constant=_reject_constant)
        if type(parsed) is not dict or canonical and canonical_bytes(parsed)!=raw:_refuse()
        return parsed
    except (ValueError,RecursionError):_refuse()


def _write(path:Path,body:bytes):
    with path.open('xb') as stream:
        stream.write(body);stream.flush();os.fsync(stream.fileno())


def _exclusive_move(source:Path,target:Path):
    """Windows MoveFile semantics; Linux renameat2 NOREPLACE, never overwrite."""
    if os.name=='nt':os.rename(source,target)
    elif sys_platform_linux():
        import ctypes
        native=ctypes.CDLL(None,use_errno=True)
        rename=getattr(native,'renameat2',None)
        if rename is None:_refuse('survey_exclusive_publication_unsupported')
        rename.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]
        rename.restype=ctypes.c_int
        if rename(-100,os.fsencode(source),-100,os.fsencode(target),1)!=0:
            raise OSError(ctypes.get_errno(),'Exclusive dataset publication refused')
    else:_refuse('survey_exclusive_publication_unsupported')
    if os.name!='nt':
        for parent in {source.parent,target.parent}:
            fd=os.open(parent,os.O_RDONLY|os.O_DIRECTORY)
            try:os.fsync(fd)
            finally:os.close(fd)


def sys_platform_linux():
    import sys
    return sys.platform=='linux'


def _limits(settings:Settings,scratch:int,lifetimes:list[dict],started:float,parent_started:float)->dict:
    cpu=600-sum(item['cpu_s'] for item in lifetimes)
    wall=min(600,settings.worker_wall_seconds)-(time.perf_counter()-started)
    parent=300-(time.process_time()-parent_started)
    if any(not math.isfinite(value) or value<2 for value in (cpu,wall,parent)):_refuse('survey_dataset_capacity_refused')
    if scratch>settings.worker_scratch_bytes:_refuse('survey_dataset_capacity_refused')
    return dict(memory_bytes=min(512*1024**2,settings.worker_memory_bytes),scratch_bytes=scratch,
        cpu_s=math.floor(cpu),wall_s=math.floor(wall),parent_cpu_s=math.floor(parent))


def _lifetime(lifetimes,inventory,started,parent_started,settings):
    for value in lifetimes:validate_drain(value)
    result=dict(schema='m03-owner-dataset-lifetime/1',phases=lifetimes,
        cpu_s=sum(item['cpu_s'] for item in lifetimes),wall_s=time.perf_counter()-started,
        parent_cpu_s=time.process_time()-parent_started,retained_bytes=sum(item['bytes'] for item in inventory),
        field_eligibility='not_established',host_admission='not_established')
    if result['cpu_s']>600 or result['wall_s']>min(600,settings.worker_wall_seconds) or result['parent_cpu_s']>300:
        _refuse('survey_dataset_capacity_refused')
    return result


async def _parents(session,settings,row):
    user=await session.get(User,row.owner_id)
    if user is None or not user.is_active or not user.is_verified:_refuse('survey_owner_inactive')
    bound=await bind_owned_dataset_inputs(session,settings,UUID(row.project_id),user,SurveyDatasetRequest.model_validate(row.input_json))
    if dataset_source_receipts(bound)!=row.source_receipts:_refuse()
    return bound


async def _record_failure(session,settings,attempt_id,root,target,lifetimes,error):
    # Missing/untrusted native drain does NOT release the committed reservation.
    await session.rollback();await session.execute(text('BEGIN IMMEDIATE'))
    row=await session.get(SurveyDatasetAttempt,str(attempt_id))
    if row is None or row.state=='published':return
    try:
        inventory=await asyncio.to_thread(collect_inventory,settings.data_dir,root) if root.exists() else []
        target_bytes=0
        if target is not None and target.exists():
            # Never trust just stat.size for an aliased/changed possible target.
            target_inventory=await asyncio.to_thread(collect_inventory,settings.data_dir,target.parent)
            target_item=next((item for item in target_inventory if item['name']==target.name),None)
            if target_item is None:_refuse()
            target_bytes=target_item['bytes']
        row.inventory=inventory;row.retained_bytes=sum(item['bytes'] for item in inventory)+target_bytes
    except (OSError,ValueError,ApiError):
        # Unknown byte state cannot be made zero, failed debt never released.
        row.retained_bytes=max(row.retained_bytes,row.reservation_bytes)
    row.state='publication_uncertain' if row.state=='publication_uncertain' or target is not None and target.exists() else 'failed'
    row.error_code=error.code if isinstance(error,ApiError) else 'survey_dataset_interrupted'
    row.lifetime=dict(schema='m03-owner-dataset-incomplete/1',phases=lifetimes,drain='unresolved')
    row.finished_at=utcnow();await session.commit()


async def create_owned_dataset(session:AsyncSession,settings:Settings,user:User,project_id:UUID,
                               request:SurveyDatasetRequest,*,controller:WindowsPreparationController,
                               base_ledger:DatasetBaseLedger,device_ledger:DeviceReservationLedger)->dict:
    """Two forward phases, genuine sources and immutable publication; no retries."""
    if not isinstance(controller,WindowsPreparationController):_refuse('survey_preparation_authority_missing')
    owner_id=user.id
    authority=await asyncio.to_thread(controller.snapshot,settings)
    row=await reserve_dataset_inspection(session,settings,user,project_id,request,authority.sha256,base_ledger,device_ledger)
    attempt_id=UUID(row.id);root=dataset_attempt_root(settings,row.id)
    target=None;lifetimes=[];started=time.perf_counter();parent_started=time.process_time()
    try:
        await session.rollback();await session.execute(text('BEGIN IMMEDIATE'))
        row=await session.get(SurveyDatasetAttempt,str(attempt_id))
        if row.state!='reserved' or row.authority_sha256!=authority.sha256 or root.exists():_refuse()
        bound=await _parents(session,settings,row)
        bundles=[];bundle_ids=[]
        for asset in bound.auxiliaries:
            intake=await session.get(SurveyIntake,str(asset.id))
            if intake.role=='typed_auxiliary_bundle':bundles.append(asset);bundle_ids.append(str(asset.id))
        if not bundles:_refuse('survey_bundle_missing')
        def entry(asset):return dict(path=str(asset.path),bytes=asset.byte_count,sha256=asset.sha256)
        plan=dict(schema='m03-owner-inspection-plan/1',original=entry(bound.original),metadata=entry(bound.metadata),
            request=entry(bound.request),bundles=[entry(asset) for asset in bundles])
        row.state='running';await session.commit()  # BEFORE even the initial mkdir.
        first=root/'inspection'
        # Commit above precedes both allocations. Create the attempt namespace
        # explicitly, then the phase exactly once: Path.mkdir(parents=True) on
        # the phase recursively re-enters that phase after a missing parent.
        await asyncio.to_thread(root.mkdir,parents=True,exist_ok=False)
        await asyncio.to_thread(first.mkdir,exist_ok=False)
        await asyncio.to_thread(_write,first/'plan.json',canonical_bytes(plan))
        lifetime=await _run_phase(controller,settings,authority,first,_limits(settings,INSPECTION_BYTES,lifetimes,started,parent_started),lifetimes)
        if lifetime['verdict']!='component_pass':_refuse('survey_dataset_preparation_failed')
        await _phase_inventory(settings,first,lifetime)
        inspection=await asyncio.to_thread(_read,first/'inspection.json')
        # Immutable uploaded JSON may be pretty-printed. Canonical receipts are
        # required only for our own producer, never by rewriting source bytes.
        metadata=await asyncio.to_thread(_read,bound.metadata.path,canonical=False)
        if inspection.get('original')!=metadata.get('original'):_refuse()
        if await asyncio.to_thread(controller.snapshot,settings)!=authority:_refuse('survey_authority_changed')
        proof=await reserve_dataset_preparation(session,settings,attempt_id,authority.sha256,inspection,bundle_ids,base_ledger,device_ledger)
        second=root/'preparation'
        limits=_limits(settings,proof['scratch_bound_bytes'],lifetimes,started,parent_started)
        inspection_bytes=(first/'inspection.json').stat().st_size
        next_plan={**plan,'schema':'m03-owner-preparation-plan/2','inspection':dict(path=str(first/'inspection.json'),
            bytes=inspection_bytes,sha256=sha256(canonical_bytes(inspection)).hexdigest())}
        await asyncio.to_thread(second.mkdir,exist_ok=False)
        await asyncio.to_thread(_write,second/'plan.json',canonical_bytes(next_plan))
        lifetime=await _run_phase(controller,settings,authority,second,limits,lifetimes)
        if lifetime['verdict']!='component_pass':_refuse('survey_dataset_preparation_failed')
        await _phase_inventory(settings,second,lifetime)
        prepared=await asyncio.to_thread(controller.verify_preparation,settings,authority,second)
        if prepared['capacity']!=proof or prepared['original']!=inspection['original'] or prepared['rows']!=inspection['rows'] or \
           prepared['metadata_sha256']!=bound.metadata.sha256 or prepared['request_sha256']!=bound.request.sha256 or \
           prepared['bundle_sha256']!=inspection['bundle_sha256']:_refuse()
        ids=[item for item in prepared['geometry']['arrays'] if item['role']=='row_id']
        if len(ids)!=1:_refuse()
        ordered_ids=_hash(ids[0]['ordered_ids_sha256'])
        dataset_id=str(uuid4())
        descriptor=dict(schema='m03-owner-dataset/1',dataset_id=dataset_id,owner_id=str(owner_id),project_id=str(project_id),
            original_asset_id=str(bound.original.id),original_sha256=bound.original.sha256,original_bytes=bound.original.byte_count,
            metadata_asset_id=str(bound.metadata.id),metadata_sha256=bound.metadata.sha256,
            auxiliary_asset_ids=[str(asset.id) for asset in bound.auxiliaries],auxiliary_sha256=[asset.sha256 for asset in bound.auxiliaries],
            geometry_sha256=prepared['geometry_sha256'],rows=prepared['rows'],ordered_row_ids_sha256=ordered_ids,parser_version=PARSER)
        body=canonical_bytes(descriptor)
        if len(body)>min(2097152,settings.max_dataset_bytes):_refuse('survey_dataset_capacity_refused')
        digest=sha256(body).hexdigest();pending=root/'descriptor.json'
        await asyncio.to_thread(_write,pending,body)
        inventory=await asyncio.to_thread(collect_inventory,settings.data_dir,root)
        aggregate=_lifetime(lifetimes,inventory,started,parent_started,settings)
        if aggregate['retained_bytes']>proof['dataset_reservation_bytes']:_refuse('survey_dataset_capacity_refused')
        await session.rollback();await session.execute(text('BEGIN IMMEDIATE'))
        row=await session.get(SurveyDatasetAttempt,str(attempt_id))
        if row.state!='running' or row.authority_sha256!=authority.sha256:_refuse()
        await _parents(session,settings,row)
        if await asyncio.to_thread(controller.snapshot,settings)!=authority:_refuse('survey_authority_changed')
        row.state='publication_uncertain';row.inventory=inventory;row.retained_bytes=aggregate['retained_bytes'];row.lifetime=aggregate
        await session.commit()  # Durable uncertainty BEFORE exclusive move.
        key=dataset_key(str(owner_id),str(project_id),dataset_id)
        checked_derived_path(settings,key)
        target=storage_root(settings.data_dir)/key
        for parent in (target,*target.parents):
            if parent.is_symlink() or getattr(parent,'is_junction',lambda:False)():_refuse()
            if parent==storage_root(settings.data_dir):break
        await asyncio.to_thread(target.parent.mkdir,parents=True,exist_ok=True)
        await asyncio.to_thread(_verify_bytes,storage_root(settings.data_dir),pending,digest,len(body),'survey_dataset_integrity_failed')
        await asyncio.to_thread(_exclusive_move,pending,target)
        await asyncio.to_thread(_verify_bytes,storage_root(settings.data_dir),target,digest,len(body),'survey_dataset_integrity_failed')
        await session.rollback();await session.execute(text('BEGIN IMMEDIATE'))
        row=await session.get(SurveyDatasetAttempt,str(attempt_id))
        if row.state!='publication_uncertain' or row.authority_sha256!=authority.sha256:_refuse()
        await _parents(session,settings,row)
        if await asyncio.to_thread(controller.snapshot,settings)!=authority:_refuse('survey_authority_changed')
        final_inventory=await asyncio.to_thread(collect_inventory,settings.data_dir,root)
        if final_inventory!=[item for item in inventory if item['name']!='descriptor.json']:_refuse()
        _lifetime(lifetimes,inventory,started,parent_started,settings)
        original=await session.get(SurveyIntake,str(bound.original.id))
        from app.models import SourceRecord
        source=await session.get(SourceRecord,str(bound.original.source_id))
        if original.state!='published' or source is None:_refuse()
        dataset=ObservationDataset(id=dataset_id,owner_id=owner_id,project_id=str(project_id),raw_asset_id=str(bound.original.id),
            version=source.version,parser_version=PARSER,modality='magnetic_line_survey',row_count=prepared['rows'],
            raw_sha256=bound.original.sha256,sha256=digest,byte_count=len(body),storage_key=key)
        session.add(dataset);await session.flush()
        # Existing derived ledger charges descriptor ONCE; raw_bytes is not increased.
        row.state='published';row.dataset_id=dataset_id;row.inventory=final_inventory
        row.retained_bytes=sum(item['bytes'] for item in final_inventory);row.finished_at=utcnow()
        await session.commit()
        return dict(schema='m03-owner-dataset-receipt/1',dataset_id=dataset_id,sha256=digest,bytes=len(body),rows=prepared['rows'],
            parser_version=PARSER,provider_verification='not_verified',field_eligibility='not_established')
    except BaseException as error:
        await _settle(asyncio.create_task(_record_failure(session,settings,attempt_id,root,target,lifetimes,error)))
        if isinstance(error,(ApiError,asyncio.CancelledError,KeyboardInterrupt,SystemExit)):raise
        raise ApiError(409,'survey_dataset_preparation_failed','Dataset preparation failed; retained custody requires recovery') from None


async def _phase_inventory(settings,root,lifetime):
    inventory=await asyncio.to_thread(collect_inventory,settings.data_dir,root)
    if sum(item['bytes'] for item in inventory)!=lifetime['scratch_bytes']:_refuse()


async def _settle(task):
    """Wait for an already bounded operation despite repeated caller cancel.

    Never infer child drain from coroutine cancellation. A cancelled operation
    itself remains cancelled, and an actual exception remains an exception.
    This helper neither restarts work nor fabricates a successful receipt.
    """
    while True:
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            if task.done():
                return task.result()


def _publish_cancel(root):
    marker=root/'cancel.request';pending=root/'cancel.request.pending'
    if not marker.exists():
        _write(pending,b'm03-owner-cancel/1\n')
        _exclusive_move(pending,marker)


async def _run_phase(controller,settings,authority:PreparationAuthority,root,limits,lifetimes):
    task=asyncio.create_task(asyncio.to_thread(controller.run,settings,authority,root,limits))
    try:
        receipt=await asyncio.shield(task)
        lifetimes.append(receipt)
        return receipt
    except asyncio.CancelledError as cancellation:
        # Wait for the ACTUAL bounded child drain before recording interrupted
        # custody. No cancelled coroutine is inferred to mean a stopped process.
        marker_error=None
        try:
            await _settle(asyncio.create_task(asyncio.to_thread(_publish_cancel,root)))
        except BaseException as error:
            marker_error=error
        # Even failed marker publication cannot bypass actual native settlement.
        # Additional cancellations cannot interrupt this bounded drain wait.
        receipt=await _settle(task)
        lifetimes.append(receipt)
        raise cancellation from marker_error
