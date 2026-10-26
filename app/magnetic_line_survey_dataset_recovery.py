"""Exact read-only dataset-attempt recovery and parent deletion barrier.

No absence is inferred to be drain, no unknown target is adopted or removed.
Published descriptors are charged by the existing derived ledger exactly once.
"""
from __future__ import annotations

import asyncio
import math
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.errors import ApiError
from app.magnetic_line_survey_dataset import PARSER,_parents,_read
from app.magnetic_line_survey_dataset_accounting import account_dataset_usage,dataset_attempt_root
from app.magnetic_line_survey_lifecycle import storage_root,validate_drain
from app.magnetic_line_survey_models import SurveyDatasetAttempt
from app.magnetic_line_survey_storage import exact_namespace
from app.magnetic_line_survey_wire import _verify_bytes
from app.models import ObservationDataset,User
from app.processing_contract import dataset_key
from app.projects import _owned_project


def _refuse():
    raise ApiError(409,'survey_dataset_recovery_required','Dataset custody requires explicit exact recovery')


async def reconcile_owned_datasets(session:AsyncSession,settings:Settings,user:User,project_id:UUID)->dict:
    """Read-only barrier for parent startup/delete; not a destructive hook."""
    await _owned_project(session,str(project_id),user)
    rows=(await session.execute(select(SurveyDatasetAttempt).where(
        SurveyDatasetAttempt.owner_id==user.id,SurveyDatasetAttempt.project_id==str(project_id)))).scalars().all()
    datasets=(await session.execute(select(ObservationDataset).where(ObservationDataset.owner_id==user.id,
        ObservationDataset.project_id==str(project_id),ObservationDataset.parser_version==PARSER))).scalars().all()
    linked={}
    for row in rows:
        if row.state!='published' or row.dataset_id is None or row.dataset_id in linked:_refuse()
        bound=await _parents(session,settings,row)
        root=dataset_attempt_root(settings,row.id)
        await asyncio.to_thread(exact_namespace,settings.data_dir,root,row.inventory)
        if sum(item['bytes'] for item in row.inventory)!=row.retained_bytes:_refuse()
        lifetime=row.lifetime
        if type(lifetime) is not dict or set(lifetime)!=set('schema phases cpu_s wall_s parent_cpu_s retained_bytes field_eligibility host_admission'.split()) or \
           lifetime['schema']!='m03-owner-dataset-lifetime/1' or type(lifetime['phases']) is not list or len(lifetime['phases'])!=2 or \
           lifetime['field_eligibility']!='not_established' or lifetime['host_admission']!='not_established':_refuse()
        for phase in lifetime['phases']:
            validate_drain(phase)
            if phase['verdict']!='component_pass':_refuse()
            for name,limit in [('peak_rss_bytes',min(512*1024**2,settings.worker_memory_bytes)),
                               ('peak_committed_bytes',min(512*1024**2,settings.worker_memory_bytes)),
                               ('cpu_s',600),('wall_s',min(600,settings.worker_wall_seconds)),
                               ('parent_cpu_s',300)]:
                if phase[name]>limit:_refuse()
        for name,limit in [('cpu_s',600),('wall_s',min(600,settings.worker_wall_seconds)),('parent_cpu_s',300)]:
            value=lifetime[name]
            if type(value) not in (int,float) or not math.isfinite(value) or not 0<value<=limit:_refuse()
        phases=lifetime['phases']
        if lifetime['cpu_s']!=sum(phase['cpu_s'] for phase in phases) or \
           phases[0]['actual_executable_sha256']!=phases[1]['actual_executable_sha256'] or \
           phases[0]['source_sha256']!=phases[1]['source_sha256']:_refuse()
        dataset=next((item for item in datasets if item.id==row.dataset_id),None)
        if dataset is None or dataset.raw_asset_id!=str(bound.original.id) or dataset.raw_sha256!=bound.original.sha256 or \
           dataset.modality!='magnetic_line_survey' or dataset.storage_key!=dataset_key(str(user.id),str(project_id),dataset.id) or \
           lifetime['retained_bytes']!=row.retained_bytes+dataset.byte_count:_refuse()
        path=storage_root(settings.data_dir)/dataset.storage_key
        await asyncio.to_thread(_verify_bytes,storage_root(settings.data_dir),path,dataset.sha256,dataset.byte_count,'survey_dataset_integrity_failed')
        descriptor=await asyncio.to_thread(_read,path)
        if set(descriptor)!=set('schema dataset_id owner_id project_id original_asset_id original_sha256 original_bytes metadata_asset_id metadata_sha256 auxiliary_asset_ids auxiliary_sha256 geometry_sha256 rows ordered_row_ids_sha256 parser_version'.split()) or \
           descriptor['schema']!='m03-owner-dataset/1' or descriptor['dataset_id']!=dataset.id or \
           descriptor['owner_id']!=str(user.id) or descriptor['project_id']!=str(project_id) or descriptor['parser_version']!=PARSER or \
           descriptor['original_asset_id']!=str(bound.original.id) or descriptor['original_sha256']!=bound.original.sha256 or \
           descriptor['original_bytes']!=bound.original.byte_count or descriptor['metadata_asset_id']!=str(bound.metadata.id) or \
           descriptor['metadata_sha256']!=bound.metadata.sha256 or descriptor['rows']!=dataset.row_count or \
           descriptor['auxiliary_asset_ids']!=[str(item.id) for item in bound.auxiliaries] or \
           descriptor['auxiliary_sha256']!=[item.sha256 for item in bound.auxiliaries]:_refuse()
        # Recheck the original prepared geometry receipt, not just descriptor SHA.
        prepared=await asyncio.to_thread(_read,root/'preparation/preparation.json')
        ids=[item for item in prepared['geometry']['arrays'] if item['role']=='row_id']
        if len(ids)!=1 or descriptor['ordered_row_ids_sha256']!=ids[0]['ordered_ids_sha256'] or \
           descriptor['geometry_sha256']!=prepared['geometry_sha256'] or prepared['rows']!=dataset.row_count:_refuse()
        linked[dataset.id]=row.id
    if set(linked)!={item.id for item in datasets}:_refuse()
    # The top-level namespace is device-wide and may contain other owners. Parent
    # must reconcile every attempt before deleting it, never rmtree it per project.
    return dict(schema='m03-owner-dataset-reconciliation/1',project_id=str(project_id),
        published=len(linked),retained_bytes=sum(row.retained_bytes for row in rows),
        owner_dataset_debt=await account_dataset_usage(session,user.id),state='exact',
        field_eligibility='not_established',destructive_action='not_performed')


async def reconcile_dataset_device_namespace(session:AsyncSession,settings:Settings)->dict:
    """Unknown empty directories and unknown owners are NOT exempt from custody."""
    directory=storage_root(settings.data_dir)/'.m03-datasets'
    rows=(await session.execute(select(SurveyDatasetAttempt))).scalars().all()
    expected={row.id for row in rows}
    if not directory.exists():
        if expected:_refuse()
        return dict(schema='m03-dataset-device-reconciliation/1',attempts=0,state='exact')
    if directory.is_symlink() or getattr(directory,'is_junction',lambda:False)():_refuse()
    actual={item.name for item in directory.iterdir()}
    if actual!=expected:_refuse()
    for row in rows:
        if row.state!='published':_refuse()
        await asyncio.to_thread(exact_namespace,settings.data_dir,dataset_attempt_root(settings,row.id),row.inventory)
    return dict(schema='m03-dataset-device-reconciliation/1',attempts=len(rows),state='exact')
