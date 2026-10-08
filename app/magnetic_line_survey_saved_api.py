"""Executing saved-job/cancel/member leaf; full admission/export mount is separate.

No CLOSED start port, synthetic success or path-valued request is installed.
The parent must review the real admission/dispatch/export/accounting/recovery
chain before mounting this leaf as part of the complete owner workflow.
"""
from __future__ import annotations

import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.errors import ApiError
from app.magnetic_line_survey_lifecycle import attempt_root, cancel_owned, job_view, owned_job, storage_root, verified_member
from app.magnetic_line_survey_models import SurveyAttempt, SurveyMember
from app.magnetic_line_survey_wire import _reject_constant, _unique_object
from app.models import User
from app.processing_contract import sha256


async def _snapshot(member,maximum):
    if not 0<member.byte_count<=maximum:
        raise ApiError(409,'survey_member_invalid','Survey member exceeds its served envelope')
    def read():
        with member.path.open('rb') as stream:
            raw=stream.read(member.byte_count+1)
        if len(raw)!=member.byte_count or sha256(raw)!=member.sha256:
            raise ApiError(409,'survey_member_integrity_failed','Survey member differs from its receipt')
        return raw
    return await asyncio.to_thread(read)


def install_magnetic_line_survey_saved_routes(app,settings: Settings,current_user,get_session):
    router=APIRouter(prefix='/api/projects/{project_id}/magnetic-line-surveys/jobs',tags=['magnetic-line-surveys'])

    @router.get('/{job_id}')
    async def get_job(project_id: UUID,job_id: UUID,user: User=Depends(current_user),session: AsyncSession=Depends(get_session)):
        return JSONResponse(job_view(await owned_job(session,user,project_id,job_id)),headers={'Cache-Control':'no-store'})

    @router.post('/{job_id}/cancel')
    async def cancel(project_id: UUID,job_id: UUID,request: Request,user: User=Depends(current_user),session: AsyncSession=Depends(get_session)):
        await owned_job(session,user,project_id,job_id)
        async for chunk in request.stream():
            if chunk:
                raise ApiError(422,'request_invalid','Cancel does not accept a body',['body'])
        return JSONResponse(await cancel_owned(session,user,project_id,job_id),headers={'Cache-Control':'no-store'})

    @router.get('/{job_id}/members')
    async def registry(project_id: UUID,job_id: UUID,offset: int=Query(0,ge=0,le=1000000),
                       user: User=Depends(current_user),session: AsyncSession=Depends(get_session)):
        job=await owned_job(session,user,project_id,job_id)
        if job.state!='succeeded':
            raise ApiError(409,'result_not_ready','Full survey result is not available')
        query=select(SurveyMember).join(SurveyAttempt).where(SurveyAttempt.job_id==job.id,SurveyAttempt.state=='published')
        total=(await session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        if not 1<=total<=1000000 or offset>=total:
            raise ApiError(409,'survey_member_invalid','Survey member inventory is invalid')
        rows=(await session.execute(query.order_by(SurveyMember.relative_name).offset(offset).limit(512))).scalars().all()
        return JSONResponse(dict(schema='m03-owner-members/1',job_id=job.id,result_sha256=job.result_sha256,
            offset=offset,total=total,next_offset=offset+len(rows) if offset+len(rows)<total else None,
            entries=[dict(member_id=item.id,name=item.relative_name,bytes=item.byte_count,sha256=item.sha256,kind=item.kind) for item in rows]),
            headers={'Cache-Control':'no-store'})

    @router.get('/{job_id}/members/{member_id}')
    async def member(project_id: UUID,job_id: UUID,member_id: UUID,user: User=Depends(current_user),session: AsyncSession=Depends(get_session)):
        item=await verified_member(session,settings.data_dir,user,project_id,job_id,member_id)
        raw=await _snapshot(item,8388608)
        return Response(raw,media_type='application/octet-stream',headers={'Cache-Control':'no-store',
            'X-Content-SHA256':item.sha256,'X-Content-Type-Options':'nosniff'})

    @router.get('/{job_id}/result')
    async def result(project_id: UUID,job_id: UUID,user: User=Depends(current_user),session: AsyncSession=Depends(get_session)):
        job=await owned_job(session,user,project_id,job_id)
        if job.state!='succeeded':
            raise ApiError(409,'result_not_ready','Full survey result is not available')
        row=(await session.execute(select(SurveyMember,SurveyAttempt).join(SurveyAttempt).where(
            SurveyAttempt.job_id==job.id,SurveyAttempt.state=='published',SurveyMember.kind=='result',
        ))).one_or_none()
        if row is None:
            raise ApiError(409,'survey_result_invalid','Survey result inventory is invalid')
        stored,attempt=row
        path=attempt_root(settings.data_dir,job,attempt)/'result/result.json'
        if stored.relative_name!='result/result.json' or job.result_key!=path.relative_to(storage_root(settings.data_dir)).as_posix() or \
           job.result_sha256!=stored.sha256 or job.result_bytes!=stored.byte_count:
            raise ApiError(409,'survey_result_invalid','Survey result differs from its job receipt')
        item=await verified_member(session,settings.data_dir,user,project_id,job_id,UUID(stored.id))
        raw=await _snapshot(item,2097152)
        try:
            value=json.loads(raw,object_pairs_hook=_unique_object,parse_constant=_reject_constant)
        except (ValueError,RecursionError) as exc:
            raise ApiError(409,'survey_result_invalid','Survey result is invalid') from exc
        if type(value) is not dict or value.get('schema')!='magnetic-line-survey-result/2' or value.get('run_id')!=job.id:
            raise ApiError(409,'survey_result_invalid','Survey result identity differs from its job')
        # Return original verified UTF-8 bytes, not a reserialized identity.
        return Response(raw,media_type='application/json',headers={'Cache-Control':'no-store','X-Content-SHA256':stored.sha256})

    app.include_router(router)
