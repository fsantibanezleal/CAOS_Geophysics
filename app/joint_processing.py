"""Owner-bound ordinary M11 uploads. No engine import or archive ingestion.

Parent installs this leaf with its existing auth/session/security dependencies.
Generic raw custody, downloads, exports, deletion and accounting stay canonical.
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import time
import uuid

from fastapi import APIRouter, Depends, Request
from pydantic import ValidationError
from sqlalchemy import delete, func, select, text
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app import joint_contract as native
from app.database import checked_storage_path
from app.errors import ApiError
from app.models import AccountUsage, RateWindow, RawAsset, SourceRecord, User, utcnow
from app.processing_storage import account_derived_usage
from app.projects import _owned_project
from app.schemas import SourceInput
from app.views import RawAssetView, asset_view


async def _member_rate(session, user):
    # Owner-bound and persistent. Generic upload20/hr is not changed.
    now = int(time.time()); bucket = now-now%3600; key = str(user.id)
    statement = insert(RateWindow).values(scope='joint_native_member', client_key=key, window_start=bucket, count=1)
    await session.execute(statement.on_conflict_do_update(
        index_elements=['scope','client_key','window_start'], set_={'count':RateWindow.count+1}))
    count = (await session.execute(select(RateWindow.count).where(
        RateWindow.scope=='joint_native_member', RateWindow.client_key==key, RateWindow.window_start==bucket))).scalar_one()
    if count==1:
        await session.execute(delete(RateWindow).where(
            RateWindow.scope=='joint_native_member',RateWindow.window_start<now-86400))
    await session.commit()
    if count > 80:
        raise ApiError(429, 'joint_member_rate_limited', 'Native member rate window exceeded')


def _staging(settings):
    try: native.external_root(settings.data_dir)
    except (ValueError,OSError) as exc:
        raise ApiError(409,'joint_external_root_invalid','Native storage must use an ordinary external root') from exc
    directory = settings.data_dir/'.staging'
    if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
        raise ApiError(409,'raw_state_unresolved','Native staging requires operator review')
    directory.mkdir(parents=True,exist_ok=True)
    return directory/str(uuid.uuid4())


def _envelope(path, meta, count):
    with path.open('rb') as stream: head = stream.read(4106)
    if head.startswith((b'PK\x03\x04',b'PK\x05\x06',b'\x1f\x8b',b'7z\xbc\xaf\x27\x1c',b'Rar!')) or head[257:262]==b'ustar':
        raise ApiError(415,'archive_forbidden','Archive uploads are not accepted')
    if meta['descriptor'] is not None:
        offset = native.native_header(head,meta['descriptor'],count)
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            stream.seek(offset)
            for chunk in iter(lambda:stream.read(1024*1024),b''): digest.update(chunk)
        if digest.hexdigest()!=meta['descriptor']['data_sha256']:
            raise ValueError('joint_member_data_digest')
    elif meta['name'] in ('request.json','sealed.json'):
        native.manifest(path.read_bytes(),meta['role'])
    elif meta['name'].endswith('.json'):
        # Correction semantics remain the original intake authority. This is
        # bounded structural transport, not scientific correction acceptance.
        if type(native.bounded_json(path.read_bytes())) is not dict:
            raise ValueError('joint_member_correction_object')


def install_joint_routes(app, settings, current_user, get_session):
    router = APIRouter(prefix='/api/projects',tags=['joint-native'])

    @router.post('/{project_id}/joint-members',status_code=201,response_model=RawAssetView)
    async def upload_member(project_id:str, request:Request, user:User=Depends(current_user),
            session:AsyncSession=Depends(get_session)):
        await _owned_project(session,project_id,user)
        try:
            header = request.headers.get('x-joint-member-metadata','').encode('utf-8')
            meta = native.member_metadata(header)
            source_input = SourceInput.model_validate(meta['source'])
        except (ValueError,UnicodeError,ValidationError) as exc:
            raise ApiError(422,'joint_member_metadata_invalid','Native member metadata is invalid') from exc
        if source_input.rights_decision=='forbidden':
            raise ApiError(422,'rights_forbidden','Forbidden sources cannot be stored')
        if request.headers.get('content-type','').split(';',1)[0].strip()!='application/octet-stream':
            raise ApiError(415,'mime_format_mismatch','Native members require ordinary binary transport')
        limit = min(settings.max_upload_bytes,native.MAX_BYTES,source_input.expected_bytes)
        length = request.headers.get('content-length')
        if length and (not length.isdigit() or int(length)!=source_input.expected_bytes or int(length)>limit):
            raise ApiError(413,'upload_too_large','Native member length exceeds its admitted bound')
        if source_input.expected_bytes>limit:
            raise ApiError(413,'upload_too_large','Native member length exceeds its admitted bound')
        await _member_rate(session,user)
        stage = _staging(settings); published = None; commit_attempted = committed = False
        digest = hashlib.sha256(); count = 0
        try:
            fd = os.open(stage,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'wb') as output:
                async for chunk in request.stream():
                    count += len(chunk)
                    if count>limit: raise ApiError(413,'upload_too_large','Native member exceeds its admitted bound')
                    digest.update(chunk)
                    await asyncio.to_thread(output.write,chunk)
                await asyncio.to_thread(output.flush)
                await asyncio.to_thread(os.fsync,output.fileno())
            if count!=source_input.expected_bytes or digest.hexdigest()!=source_input.expected_sha256:
                raise ApiError(422,'joint_member_digest_mismatch','Native member differs from its original receipt')
            try: await asyncio.to_thread(_envelope,stage,meta,count)
            except ValueError as exc:
                raise ApiError(422,'joint_member_native_invalid','Native member header, inventory or data digest is invalid') from exc
            await session.rollback(); await session.execute(text('BEGIN IMMEDIATE')); await session.refresh(user)
            await _owned_project(session,project_id,user)
            usage = (await session.execute(select(AccountUsage).where(AccountUsage.user_id==user.id))).scalar_one_or_none()
            current = usage.raw_bytes if usage else 0
            if current+await account_derived_usage(session,user.id)+count>settings.account_quota_bytes:
                raise ApiError(507,'account_quota_exceeded','Account private-byte quota exceeded')
            if usage: usage.raw_bytes += count
            else: session.add(AccountUsage(user_id=user.id,raw_bytes=count))
            version = (await session.execute(select(func.max(SourceRecord.version)).where(
                SourceRecord.owner_id==user.id,SourceRecord.project_id==project_id,
                SourceRecord.original_filename==meta['name']))).scalar_one() or 0
            now=utcnow(); asset_id=str(uuid.uuid4()); source_id=str(uuid.uuid4()); sha=digest.hexdigest()
            source=SourceRecord(id=source_id,project_id=project_id,owner_id=user.id,original_filename=meta['name'],
                version=version+1,provider=source_input.provider,exact_url=None,doi=source_input.doi,citation=source_input.citation,
                retrieved_at=now,rights_statement=source_input.rights_statement,rights_decision=source_input.rights_decision,
                private_storage_permission='attested',declared_format='joint_native',expected_bytes=count,sha256=sha,
                attribution=source_input.attribution)
            key=f'projects/{user.id}/{project_id}/{asset_id}'
            asset=RawAsset(id=asset_id,project_id=project_id,owner_id=user.id,source_id=source_id,filename=meta['name'],
                client_mime='application/octet-stream',detected_format='joint_native',byte_count=count,sha256=sha,storage_key=key,
                physical_metadata={'schema':'joint-native-member-1','role':meta['role'],'name':meta['name'],
                    'descriptor':meta['descriptor'],'scientific_values_decoded':False,'scientific_accepted':False},
                validation_status='raw_metadata_checked',created_at=now)
            session.add(source); await session.flush(); session.add(asset); await session.flush()
            target=checked_storage_path(settings,key); target.parent.mkdir(parents=True,exist_ok=True)
            # Exclusive hard link prevents accidental replacement, even if a
            # concurrent original appears after the preceding existence check.
            await asyncio.to_thread(os.link,stage,target); published=target
            stage.unlink(); commit_attempted=True; await session.commit(); committed=True
            return asset_view(asset,source)
        finally:
            if not committed:
                await session.rollback()
                if published is not None and not commit_attempted: published.unlink(missing_ok=True)
            stage.unlink(missing_ok=True)

    app.include_router(router)
