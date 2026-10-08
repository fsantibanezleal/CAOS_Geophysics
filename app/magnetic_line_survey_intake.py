"""Executing rights-bearing asset intake, isolated from shared route assembly.

The shared account ledger is a REQUIRED trusted dependency, not HTTP authority.
It must include all existing raw/derived/job debt and EXCLUDE this intake subtotal.
No generic gravity fallback, source verification claim or processing grant.
"""
from __future__ import annotations

import asyncio
import hashlib
import os
from pathlib import Path
import re
import shutil
import struct
from typing import Literal, Protocol
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.database import checked_storage_path
from app.errors import ApiError
from app.magnetic_line_survey_lifecycle import collect_inventory, storage_root
from app.magnetic_line_survey_models import SurveyIntake
from app.magnetic_line_survey_wire import Hash, _parse
from app.models import AccountUsage, RawAsset, SourceRecord, User, utcnow
from app.processing_contract import canonical_bytes
from app.projects import _owned_project

ROLES = ('original_csv', 'metadata_json', 'request_json', 'typed_auxiliary_bundle', 'navigation_original',
    'base_original', 'calibration_original', 'reference_original', 'offset_original')
LIMITS = {role: 2097152 if role in ('metadata_json', 'request_json') else 4294967296 for role in ROLES}
MIMES = {role: 'application/json' if role in ('metadata_json', 'request_json') else
    'application/octet-stream' if role == 'typed_auxiliary_bundle' else 'text/csv' for role in ROLES}


class IntakeSource(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, frozen=True)
    provider: str = Field(min_length=1, max_length=200)
    doi: str | None = Field(max_length=200)
    citation: str | None = Field(max_length=2000)
    rights_statement: str = Field(min_length=10, max_length=4000)
    rights_decision: Literal['mirror', 'provider-link-only', 'derivative-only', 'forbidden']
    private_storage_permission: Literal[True]
    attribution: str = Field(min_length=1, max_length=2000)
    expected_bytes: int = Field(gt=0, le=4294967296)
    expected_sha256: Hash

    @field_validator('private_storage_permission', mode='before')
    @classmethod
    def actual_boolean(cls, value):
        if value is not True: raise ValueError('Explicit true private storage attestation required')
        return value

    @field_validator('provider', 'rights_statement', 'attribution')
    @classmethod
    def visible(cls, value):
        if not value.strip(): raise ValueError('Visible source declaration required')
        return value


class SurveyAssetHeader(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, frozen=True)
    schema_version: Literal['m03-owner-asset/1'] = Field(alias='schema')
    role: Literal['original_csv', 'metadata_json', 'request_json', 'typed_auxiliary_bundle', 'navigation_original',
        'base_original', 'calibration_original', 'reference_original', 'offset_original']
    filename: str = Field(min_length=1, max_length=255)
    mime: str
    source: IntakeSource

    @field_validator('filename')
    @classmethod
    def basename(cls, value):
        if value in ('.', '..') or any(c in value for c in '/\\:') or any(ord(c) < 32 for c in value):
            raise ValueError('Plain filename required')
        return value

    @model_validator(mode='after')
    def exact_role_envelope(self):
        if self.mime != MIMES[self.role] or self.source.expected_bytes > LIMITS[self.role]:
            raise ValueError('Role/MIME/size envelope mismatch')
        return self


def parse_asset_header(raw: str | None) -> SurveyAssetHeader:
    if type(raw) is not str:
        raise ApiError(422, 'request_invalid', 'Survey asset header is required', ['header'])
    try: encoded = raw.encode('utf-8', errors='strict')
    except UnicodeError as exc:
        raise ApiError(422, 'request_invalid', 'Survey asset header is invalid', ['header']) from exc
    return _parse(encoded, SurveyAssetHeader)


class AccountLedger(Protocol):
    async def __call__(self, session: AsyncSession, owner_id: UUID) -> int:
        """Actual raw + derived + all non-intake reservations in THIS transaction."""


def _refuse(code='survey_intake_integrity_failed'):
    raise ApiError(409, code, 'Survey intake custody requires exact recovery')


def intake_root(settings: Settings, intake_id: str) -> Path:
    if str(UUID(intake_id)) != intake_id: _refuse()
    root = storage_root(settings.data_dir)/'.m03-intake'/intake_id
    for parent in (root, root.parent):
        if parent.is_symlink() or getattr(parent, 'is_junction', lambda: False)(): _refuse()
    return root


async def account_intake_usage(session: AsyncSession, owner_id: UUID) -> int:
    rows = (await session.execute(select(SurveyIntake).where(SurveyIntake.owner_id == owner_id))).scalars().all()
    debt = 0
    for row in rows:
        if type(row.reservation_bytes) is not int or row.reservation_bytes <= 0 or \
           type(row.retained_bytes) is not int or row.retained_bytes < 0: _refuse()
        if row.state == 'published':
            if row.asset_id != row.id or row.retained_bytes != 0 or row.inventory: _refuse()
        elif row.state in ('reserved', 'receiving', 'failed', 'publication_uncertain'):
            debt += max(row.reservation_bytes, row.retained_bytes)
        else: _refuse()
    return debt


def _exact(stream, count):
    data = stream.read(count)
    if len(data) != count: _refuse('survey_bundle_invalid')
    return data


def inspect_bundle(path: Path, expected_bytes: int) -> dict:
    """Stream the bounded M03AUX1 envelope; no extraction or extension grant."""
    if not 12 <= expected_bytes <= 4294967296: _refuse('survey_bundle_invalid')
    total, previous, ledger = 12, '', hashlib.sha256()
    with path.open('rb') as stream:
        if _exact(stream, 8) != b'M03AUX1\n': _refuse('survey_bundle_invalid')
        count = struct.unpack('<I', _exact(stream, 4))[0]
        if not 1 <= count <= 1000000 or 12+44*count > expected_bytes: _refuse('survey_bundle_invalid')
        for _ in range(count):
            length = struct.unpack('<H', _exact(stream, 2))[0]
            if not 1 <= length <= 64: _refuse('survey_bundle_invalid')
            try: name = _exact(stream, length).decode('ascii')
            except UnicodeError: _refuse('survey_bundle_invalid')
            size = struct.unpack('<Q', _exact(stream, 8))[0]
            expected = _exact(stream, 32).hex()
            total += 42+length+size
            if re.fullmatch(r'[A-Za-z0-9_.-]{1,64}', name) is None or name in ('.', '..') or \
               name <= previous or not 0 < size <= 8388608 or total > expected_bytes:
                _refuse('survey_bundle_invalid')
            offset, digest = stream.tell(), hashlib.sha256()
            remaining = size
            while remaining:
                chunk = _exact(stream, min(remaining, 1048576))
                remaining -= len(chunk); digest.update(chunk)
            if digest.hexdigest() != expected: _refuse('survey_bundle_invalid')
            ledger.update(canonical_bytes(dict(name=name, bytes=size, sha256=expected, offset=offset)))
            previous = name
        if total != expected_bytes or stream.read(1): _refuse('survey_bundle_invalid')
    return dict(schema='m03-owner-bundle-envelope/1', members=count, bytes=total,
        inventory_sha256=ledger.hexdigest(), semantic_closure='not_verified')


async def reserve_intake(session: AsyncSession, settings: Settings, user: User, project_id: UUID,
                         header: SurveyAssetHeader, ledger: AccountLedger) -> SurveyIntake:
    # Call ONLY after auth/CSRF/owned-project and header/MIME checks, BEFORE body.
    owner_id = user.id
    if header.source.rights_decision != 'mirror':
        raise ApiError(422, 'rights_forbidden', 'Original storage requires mirror rights', ['source.rights_decision'])
    if header.source.expected_bytes > settings.max_upload_bytes:
        raise ApiError(413, 'upload_too_large', 'Survey asset exceeds configured upload limit')
    storage_root(settings.data_dir)
    await session.rollback()
    await session.execute(text('BEGIN IMMEDIATE'))
    user = await session.get(User, owner_id)
    if user is None or not user.is_active or not user.is_verified: _refuse('survey_owner_inactive')
    await _owned_project(session, str(project_id), user)
    if ledger is None: _refuse('survey_account_authority_missing')
    prior = await ledger(session, owner_id)
    if type(prior) is not int or prior < 0: _refuse('survey_account_authority_invalid')
    debt = await account_intake_usage(session, owner_id)
    encoded = header.model_dump(mode='json', by_alias=True)
    reserve = header.source.expected_bytes+len(canonical_bytes(encoded))+4096
    if prior+debt+reserve > settings.account_quota_bytes:
        raise ApiError(507, 'account_quota_exceeded', 'Account private-byte quota exceeded')
    if shutil.disk_usage(settings.data_dir).free < reserve+67108864:
        raise ApiError(507, 'survey_disk_reservation_refused', 'External device cannot reserve the survey upload')
    row = SurveyIntake(id=str(uuid4()), owner_id=owner_id, project_id=str(project_id), role=header.role,
        header_json=encoded, state='reserved', reservation_bytes=reserve, retained_bytes=0, inventory=[])
    session.add(row)
    await session.commit()  # Actual durable claim BEFORE mkdir/open/body read.
    return row


async def receive_asset(session: AsyncSession, settings: Settings, intake_id: UUID, chunks) -> dict:
    await session.rollback()
    await session.execute(text('BEGIN IMMEDIATE'))
    row = await session.get(SurveyIntake, str(intake_id))
    if row is None or row.state != 'reserved': _refuse()
    header = SurveyAssetHeader.model_validate(row.header_json)
    row.state = 'receiving'
    await session.commit()
    root = intake_root(settings, row.id)
    path, target = root/'upload.part', None
    try:
        root.mkdir(parents=True, exist_ok=False)
        digest, count = hashlib.sha256(), 0
        with path.open('xb') as stream:
            async for chunk in chunks:
                if type(chunk) is not bytes: _refuse()
                count += len(chunk)
                if count > header.source.expected_bytes:
                    raise ApiError(413, 'upload_too_large', 'Survey upload exceeds its reserved byte count')
                digest.update(chunk)
                await asyncio.to_thread(stream.write, chunk)
            await asyncio.to_thread(stream.flush)
            await asyncio.to_thread(os.fsync, stream.fileno())
        if count != header.source.expected_bytes or digest.hexdigest() != header.source.expected_sha256:
            raise ApiError(422, 'survey_source_mismatch', 'Survey upload differs from its exact source declaration')
        if header.role == 'typed_auxiliary_bundle':
            await asyncio.to_thread(inspect_bundle, path, count)
        owner_id, project_id = row.owner_id, row.project_id
        await session.rollback()
        await session.execute(text('BEGIN IMMEDIATE'))
        row = await session.get(SurveyIntake, str(intake_id))
        user = await session.get(User, owner_id)
        if row is None or row.state != 'receiving' or user is None or not user.is_active or not user.is_verified: _refuse()
        await _owned_project(session, project_id, user)
        if row.header_json != header.model_dump(mode='json', by_alias=True): _refuse()
        row.state = 'publication_uncertain'
        row.retained_bytes = count
        row.inventory = await asyncio.to_thread(collect_inventory, settings.data_dir, root)
        await session.commit()  # Uncertainty/debt persists BEFORE moving bytes.
        key = f'projects/{owner_id}/{project_id}/{row.id}'
        target = checked_storage_path(settings, key)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists(): _refuse()
        # Revalidate immutable source just before move, not merely its early hash.
        from app.magnetic_line_survey_wire import _verify_bytes
        await asyncio.to_thread(_verify_bytes, storage_root(settings.data_dir), path,
            digest.hexdigest(), count, 'survey_source_mismatch')
        await asyncio.to_thread(os.rename, path, target)
        await asyncio.to_thread(_verify_bytes, storage_root(settings.data_dir),
            storage_root(settings.data_dir)/key, digest.hexdigest(), count, 'survey_source_mismatch')
        await session.rollback()
        await session.execute(text('BEGIN IMMEDIATE'))
        row = await session.get(SurveyIntake, str(intake_id))
        if row is None or row.state != 'publication_uncertain': _refuse()
        user = await session.get(User, owner_id)
        if user is None or not user.is_active or not user.is_verified: _refuse('survey_owner_inactive')
        await _owned_project(session, project_id, user)
        source_id = str(uuid4())
        version = (await session.execute(select(func.max(SourceRecord.version)).where(
            SourceRecord.owner_id == owner_id, SourceRecord.project_id == project_id,
            SourceRecord.original_filename == header.filename))).scalar_one() or 0
        declared = 'm03_'+header.role
        source = SourceRecord(id=source_id, owner_id=owner_id, project_id=project_id,
            original_filename=header.filename, version=version+1, provider=header.source.provider,
            exact_url=None, doi=header.source.doi, citation=header.source.citation,
            rights_statement=header.source.rights_statement, rights_decision=header.source.rights_decision,
            private_storage_permission='attested', declared_format=declared, expected_bytes=count,
            sha256=digest.hexdigest(), attribution=header.source.attribution, retrieved_at=utcnow())
        session.add(source); await session.flush()
        asset = RawAsset(id=row.id, owner_id=owner_id, project_id=project_id, source_id=source_id,
            filename=header.filename, client_mime=header.mime, detected_format=declared, byte_count=count,
            sha256=digest.hexdigest(), storage_key=key, physical_metadata=dict(schema='m03-owner-asset/1', role=header.role),
            validation_status='m03_bytes_custodied', created_at=utcnow())
        session.add(asset); await session.flush()
        usage = await session.get(AccountUsage, owner_id)
        if usage is None: session.add(AccountUsage(user_id=owner_id, raw_bytes=count))
        else: usage.raw_bytes += count
        row.asset_id, row.state, row.retained_bytes, row.inventory = row.id, 'published', 0, []
        await session.commit()
        return dict(schema='m03-owner-asset-receipt/1', asset_id=row.id, source_id=source_id, role=header.role,
            bytes=count, sha256=digest.hexdigest(), provider_verification='not_verified', field_eligibility='not_established')
    except BaseException as error:
        await session.rollback()
        await session.execute(text('BEGIN IMMEDIATE'))
        row = await session.get(SurveyIntake, str(intake_id))
        if row is not None and row.state != 'published':
            row.state = 'publication_uncertain' if target is not None and target.exists() else 'failed'
            row.error_code = error.code if isinstance(error, ApiError) else 'survey_intake_interrupted'
            inventory = await asyncio.to_thread(collect_inventory, settings.data_dir, root) if root.exists() else []
            row.inventory = inventory
            row.retained_bytes = sum(item['bytes'] for item in inventory)+(target.stat().st_size if target is not None and target.exists() else 0)
            await session.commit()
        raise
