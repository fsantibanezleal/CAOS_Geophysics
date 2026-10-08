"""Atomic inspection/next-phase claims and exact unreleased dataset debt.

No fixture authority, native success, descriptor publication or activation is
inferred here. Parent supplies the complete independent base/device ledgers.
"""
from __future__ import annotations

import asyncio
import csv
from pathlib import Path
import shutil
import struct
from typing import Protocol
from uuid import UUID,uuid4

from sqlalchemy import select,text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.errors import ApiError
from app.magnetic_line_survey_intake import account_intake_usage
from app.magnetic_line_survey_lifecycle import storage_root
from app.magnetic_line_survey_models import SurveyDatasetAttempt
from app.magnetic_line_survey_wire import (
    OwnedDatasetInputs,SurveyDatasetRequest,_hash,bind_owned_dataset_inputs,
)
from app.models import User,ObservationDataset

INSPECTION_BYTES=16*1024**2
DESCRIPTOR_BYTES=2*1024**2
CSV_COLUMNS=('row_id','line_id','line_kind','sensor_id','ordinal','utc','easting_m','northing_m',
    'upward_m','terrain_upward_m','clearance_m','magnetic_nT','uncertainty_nT','heading_deg')


class DatasetBaseLedger(Protocol):
    async def __call__(self,session:AsyncSession,owner_id:UUID)->int:
        """Actual raw/derived/ALL other job/export debt, excluding intake/dataset attempts."""


class DeviceReservationLedger(Protocol):
    async def __call__(self,session:AsyncSession)->int:
        """ALL other active device reservations, excluding dataset attempts."""


def _refuse(code='survey_dataset_integrity_failed'):
    raise ApiError(409,code,'Dataset custody requires exact recovery')


def dataset_attempt_root(settings:Settings,key:str)->Path:
    if str(UUID(key))!=key:_refuse()
    root=storage_root(settings.data_dir)/'.m03-datasets'/key
    for parent in (root,root.parent):
        if parent.is_symlink() or getattr(parent,'is_junction',lambda:False)():_refuse()
    return root


def dataset_source_receipts(bound:OwnedDatasetInputs)->dict:
    def item(asset):return dict(id=str(asset.id),sha256=asset.sha256,bytes=asset.byte_count,
        source_id=str(asset.source_id),rights_decision=asset.rights_decision,private_storage_permission=asset.private_storage_permission)
    return dict(original=item(bound.original),metadata=item(bound.metadata),request=item(bound.request),
        auxiliaries=[item(asset) for asset in bound.auxiliaries])


async def account_dataset_usage(session:AsyncSession,owner_id:UUID)->int:
    debt=0
    rows=(await session.execute(select(SurveyDatasetAttempt).where(SurveyDatasetAttempt.owner_id==owner_id))).scalars()
    for row in rows:
        if type(row.reservation_bytes) is not int or not 0<row.reservation_bytes<=32*1024**3 or \
           type(row.retained_bytes) is not int or row.retained_bytes<0:_refuse()
        if row.state=='published':
            if row.dataset_id is None:_refuse()
            # Descriptor is charged by the existing ObservationDataset-derived
            # ledger exactly once; retained preparation workspace remains debt.
            debt+=row.retained_bytes
        elif row.state in ('reserved','running','drained','failed','publication_uncertain'):
            debt+=max(row.reservation_bytes,row.retained_bytes)
        else:_refuse()
    return debt


def exact_next_phase(rows:int,auxiliary_bytes:int,members:int)->dict:
    # Independent integer proof, not an echoed native JSON reservation.
    for value,low,high in ((rows,1,8000000),(auxiliary_bytes,56,4294967296),(members,1,1000000)):
        if type(value) is not int or not low<=value<=high:_refuse('survey_dataset_capacity_invalid')
    if 12+44*members>auxiliary_bytes:_refuse('survey_dataset_capacity_invalid')
    index=4096*(16+(2048*members+4095)//4096)
    geometry=65536*rows+67108864
    phase=auxiliary_bytes+2*index+geometry+67108864
    reserve=INSPECTION_BYTES+phase+DESCRIPTOR_BYTES
    if index>2147483648 or reserve>32*1024**3:_refuse('survey_dataset_capacity_refused')
    return dict(schema='m03-owner-preparation-capacity/2',original_rows=rows,auxiliary_bytes=auxiliary_bytes,
        physical_members=members,index_and_journal_bytes=2*index,geometry_workspace_bytes=geometry,
        scratch_bound_bytes=phase,memory_bound_bytes=512*1024**2,dataset_reservation_bytes=reserve,
        logical_member_limit=192,physical_member_limit=1000000,value_access='not_opened',full_job_admission='not_established')


def inspect_dimensions(bound:OwnedDatasetInputs,bundle_ids:list[str])->tuple[int,int,int,list[int]]:
    """Independently count every original row/envelope; no float response decode."""
    rows=0
    with bound.original.path.open('r',encoding='utf-8-sig',errors='strict',newline='') as stream:
        reader=csv.reader(stream,strict=True);header=next(reader,None)
        if header!=list(CSV_COLUMNS):_refuse('survey_dataset_capacity_invalid')
        for row in reader:
            if len(row)!=len(CSV_COLUMNS):_refuse('survey_dataset_capacity_invalid')
            rows+=1
            if rows>8000000:_refuse('survey_dataset_capacity_refused')
    auxiliary=0;counts=[]
    for key in bundle_ids:
        matches=[asset for asset in bound.auxiliaries if str(asset.id)==key]
        if len(matches)!=1:_refuse('survey_bundle_missing')
        asset=matches[0]
        with asset.path.open('rb') as stream:
            if stream.read(8)!=b'M03AUX1\n':_refuse('survey_bundle_invalid')
            raw=stream.read(4)
            if len(raw)!=4:_refuse('survey_bundle_invalid')
            count=struct.unpack('<I',raw)[0]
        counts.append(count);auxiliary+=asset.byte_count
    return rows,auxiliary,sum(counts),counts


async def _quota(session,settings,owner_id,reservation,base_ledger,device_ledger,*,replace_id=None):
    if not callable(base_ledger) or not callable(device_ledger):_refuse('survey_account_authority_missing')
    base=await base_ledger(session,owner_id);device=await device_ledger(session)
    if type(base) is not int or base<0 or type(device) is not int or device<0:_refuse('survey_account_authority_invalid')
    debt=await account_dataset_usage(session,owner_id)
    active=(await session.execute(select(SurveyDatasetAttempt).where(SurveyDatasetAttempt.state.in_(['reserved','running'])))).scalars().all()
    if replace_id is not None:
        prior=await session.get(SurveyDatasetAttempt,replace_id)
        debt-=max(prior.reservation_bytes,prior.retained_bytes)
    if base+await account_intake_usage(session,owner_id)+debt+reservation>settings.account_quota_bytes:
        raise ApiError(507,'account_quota_exceeded','Account private-byte quota exceeded')
    outstanding=sum(row.reservation_bytes for row in active if row.id!=replace_id)
    if len(active)-(1 if replace_id is not None else 0)>=settings.max_queued_jobs or \
       outstanding+reservation>settings.worker_scratch_bytes:
        raise ApiError(507,'survey_dataset_capacity_refused','Dataset active scratch reservation exceeds configured bounds')
    # Free device space is physical; existing retained bytes have already reduced
    # it. Add only independently reported outstanding reservations, not a second
    # subtraction of existing raw/derived files.
    if shutil.disk_usage(settings.data_dir).free<device+outstanding+reservation+67108864:
        raise ApiError(507,'survey_disk_reservation_refused','External device cannot reserve dataset preparation')


async def reserve_dataset_inspection(session:AsyncSession,settings:Settings,user:User,project_id:UUID,
                                     request:SurveyDatasetRequest,authority_sha256:str,
                                     base_ledger:DatasetBaseLedger,device_ledger:DeviceReservationLedger)->SurveyDatasetAttempt:
    owner_id=user.id;storage_root(settings.data_dir);_hash(authority_sha256)
    await session.rollback();await session.execute(text('BEGIN IMMEDIATE'))
    user=await session.get(User,owner_id)
    if user is None or not user.is_active or not user.is_verified:_refuse('survey_owner_inactive')
    bound=await bind_owned_dataset_inputs(session,settings,project_id,user,request)
    existing=(await session.execute(select(ObservationDataset.id).where(
        ObservationDataset.raw_asset_id==str(bound.original.id),
        ObservationDataset.parser_version=='m03-original-geometry/1'))).scalar_one_or_none()
    if existing is not None:_refuse('survey_dataset_already_published')
    await _quota(session,settings,owner_id,INSPECTION_BYTES,base_ledger,device_ledger)
    row=SurveyDatasetAttempt(id=str(uuid4()),owner_id=owner_id,project_id=str(project_id),
        input_json=request.model_dump(mode='json',by_alias=True),source_receipts=dataset_source_receipts(bound),
        authority_sha256=authority_sha256,reservation_bytes=INSPECTION_BYTES,state='reserved',retained_bytes=0,inventory=[])
    session.add(row);await session.commit()
    return row


async def reserve_dataset_preparation(session:AsyncSession,settings:Settings,attempt_id:UUID,
                                      authority_sha256:str,inspection:dict,bundle_ids:list[str],
                                      base_ledger:DatasetBaseLedger,device_ledger:DeviceReservationLedger)->dict:
    """Caller passes an actual verified fixed-worker snapshot, never HTTP JSON.

    Commit the independently recomputed next-phase debt BEFORE its allocation.
    A refusal retains the original committed inspection claim and all bytes.
    """
    await session.rollback();await session.execute(text('BEGIN IMMEDIATE'))
    row=await session.get(SurveyDatasetAttempt,str(attempt_id))
    if row is None or row.state!='running' or row.reservation_bytes!=INSPECTION_BYTES or \
       row.authority_sha256!=_hash(authority_sha256):_refuse()
    user=await session.get(User,row.owner_id)
    if user is None or not user.is_active or not user.is_verified:_refuse('survey_owner_inactive')
    request=SurveyDatasetRequest.model_validate(row.input_json)
    bound=await bind_owned_dataset_inputs(session,settings,UUID(row.project_id),user,request)
    if dataset_source_receipts(bound)!=row.source_receipts:_refuse()
    from app.magnetic_line_survey_models import SurveyIntake
    actual_bundles=[]
    for asset in bound.auxiliaries:
        intake=await session.get(SurveyIntake,str(asset.id))
        if intake.role=='typed_auxiliary_bundle':actual_bundles.append(str(asset.id))
    if bundle_ids!=actual_bundles or not actual_bundles:_refuse('survey_bundle_missing')
    rows,auxiliary,members,counts=await asyncio.to_thread(inspect_dimensions,bound,bundle_ids)
    proof=exact_next_phase(rows,auxiliary,members)
    if type(inspection) is not dict:_refuse('survey_dataset_capacity_invalid')
    expected=dict(schema='m03-owner-inspection-receipt/1',original=inspection.get('original'),rows=rows,
        metadata_sha256=bound.metadata.sha256,request_sha256=bound.request.sha256,
        bundle_sha256=[next(asset.sha256 for asset in bound.auxiliaries if str(asset.id)==key) for key in bundle_ids],
        bundle_members=counts,auxiliary_bytes=auxiliary,next_phase=proof,value_access='not_opened')
    if type(inspection) is not dict or inspection!=expected or type(inspection['original']) is not dict or \
       inspection['original'].get('csv_sha256')!=bound.original.sha256 or inspection['original'].get('csv_bytes')!=bound.original.byte_count:
        _refuse('survey_dataset_capacity_invalid')
    await _quota(session,settings,row.owner_id,proof['dataset_reservation_bytes'],base_ledger,device_ledger,replace_id=row.id)
    row.reservation_bytes=proof['dataset_reservation_bytes']
    await session.commit()
    return proof
