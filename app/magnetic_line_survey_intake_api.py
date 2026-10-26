"""Additive authenticated executing asset/source leaf; parent mounts explicitly.

The required account ledger is trusted backend assembly, NEVER a wire field or
fixed worker/host authority. Its absence/refusal prevents allocation, not a
fabricated no-op success. Dataset/admission/export leaves remain separate.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.errors import ApiError
from app.magnetic_line_survey_intake import AccountLedger, parse_asset_header, receive_asset, reserve_intake
from app.magnetic_line_survey_models import SurveyIntake
from app.models import RawAsset, SourceRecord, User
from app.projects import _owned_project


def install_magnetic_line_survey_intake_routes(app, settings: Settings, current_user, get_session,
                                              *, account_ledger: AccountLedger):
    router = APIRouter(prefix='/api/projects/{project_id}/magnetic-line-surveys', tags=['magnetic-line-surveys'])

    @router.post('/assets', status_code=201)
    async def upload(project_id: UUID, request: Request, user: User=Depends(current_user),
                     session: AsyncSession=Depends(get_session)):
        await _owned_project(session, str(project_id), user)
        header = parse_asset_header(request.headers.get('x-asset-metadata'))
        if request.headers.get('content-type', '').split(';', 1)[0].strip() != header.mime:
            raise ApiError(415, 'mime_format_mismatch', 'Content-Type and declared MIME must agree')
        length = request.headers.get('content-length')
        if length is not None and (not length.isdigit() or int(length) != header.source.expected_bytes):
            raise ApiError(413, 'upload_too_large', 'Content length differs from the reserved declaration')
        row = await reserve_intake(session, settings, user, project_id, header, account_ledger)
        receipt = await receive_asset(session, settings, UUID(row.id), request.stream())
        return JSONResponse(receipt, status_code=201, headers={'Cache-Control':'no-store'})

    @router.get('/sources')
    async def sources(project_id: UUID, offset: int=Query(0, ge=0, le=1000000),
                      user: User=Depends(current_user), session: AsyncSession=Depends(get_session)):
        await _owned_project(session, str(project_id), user)
        rows = (await session.execute(select(SurveyIntake, RawAsset, SourceRecord)
            .join(RawAsset, SurveyIntake.asset_id == RawAsset.id).join(SourceRecord, RawAsset.source_id == SourceRecord.id)
            .where(SurveyIntake.owner_id == user.id, SurveyIntake.project_id == str(project_id),
                RawAsset.owner_id == user.id, RawAsset.project_id == str(project_id),
                SourceRecord.owner_id == user.id, SourceRecord.project_id == str(project_id), SurveyIntake.state == 'published')
            .order_by(SurveyIntake.id).offset(offset).limit(513))).all()
        return JSONResponse(dict(schema='m03-owner-sources/1', offset=offset,
            next_offset=offset+512 if len(rows)>512 else None,
            entries=[dict(asset_id=asset.id, source_id=source.id, role=intake.role,
                bytes=asset.byte_count, sha256=asset.sha256, provider=source.provider, doi=source.doi,
                citation=source.citation, rights_statement=source.rights_statement,
                rights_decision=source.rights_decision, attribution=source.attribution,
                provider_verification='not_verified', field_eligibility='not_established')
                for intake, asset, source in rows[:512]]), headers={'Cache-Control':'no-store'})

    app.include_router(router)
