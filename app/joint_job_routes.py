"""Candidate-only owner-scoped M11 job admission and result delivery.

The caller must mount this router only with the explicit physical runtime and
the isolated 0006 candidate schema. The general processing API is untouched.
"""
from __future__ import annotations

import hashlib
import os
import re
import stat
import tempfile
import zipfile
from datetime import timezone
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.background import BackgroundTask

from app import physical_joint_native_contract as native
from app.errors import ApiError
from app.joint_routes import _physical, _registered_0006, _require_quota
from app.models import ObservationDataset, ProcessingJob, User, utcnow
from app.physical_async_sql import run_native_transaction
from app.physical_contract import byte_sha, canonical
from app.projects import _owned_project

METHOD = native.METHOD_ID
ACTIVE_PER_OWNER = 1
MAX_QUEUE = 8
RESULT_SCHEMA = "geophysics.joint-result-custody/v1"
HISTORY_SCHEMA = "geophysics.joint-custody-history/v1"
MEMBER_NAME = re.compile(r"(?:workflow\.json|failure\.json|api-failure\.json|(?:calibration|frozen|models|result|instrument|aborted)/[a-z][a-z0-9_]{0,120}\.(?:json|npy))\Z")


class JointJobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset_id: UUID
    operation: Literal["solve"] = "solve"


def _json_bytes(value: dict) -> bytes:
    return canonical(value)


def _job_view(job: ProcessingJob) -> dict:
    def stamp(value):
        if value is None:
            return None
        value = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
        return value.isoformat().replace("+00:00", "Z")
    return {
        "job_id": job.id, "owner_id": str(job.owner_id), "project_id": job.project_id,
        "dataset_id": job.dataset_id,
        "dataset_sha256": job.dataset_sha256, "method_id": job.method_id,
        "request_sha256": job.request_sha256, "state": job.state,
        "cancel_requested": bool(job.cancel_requested), "created_at": stamp(job.created_at),
        "started_at": stamp(job.started_at), "finished_at": stamp(job.finished_at),
        "wall_ms": job.wall_ms, "peak_rss_bytes": job.peak_rss_bytes,
        "scratch_bytes": job.scratch_bytes, "result_sha256": job.result_sha256,
        "result_bytes": job.result_bytes, "error_code": job.error_code,
        "index_available": job.result_key is not None,
        "result_url": f"/api/projects/{job.project_id}/joint-results/{job.id}" if job.result_key else None,
        "scientific_acceptance": False,
    }


async def _load_owned_job(session: AsyncSession, project_id: str, job_id: str, owner_id):
    job = (await session.execute(select(ProcessingJob).where(
        ProcessingJob.id == job_id, ProcessingJob.project_id == project_id,
        ProcessingJob.owner_id == owner_id, ProcessingJob.method_id == METHOD,
    ))).scalar_one_or_none()
    if job is None:
        raise ApiError(404, "not_found", "Joint processing job not found")
    return job


async def _proof(session, physical, owner_id, quota):
    try:
        proof = await run_native_transaction(session, "classify_snapshot", files=physical.leases.files,
                                             **physical.participant.arguments())
    except (ValueError, OSError) as error:
        raise ApiError(409, "joint_custody_unresolved", "M11 custody cannot be proven from this snapshot") from error
    if proof.classification not in ("coherent_committed", "prepared_uncommitted"):
        raise ApiError(409, "joint_custody_unresolved", "M11 custody cannot be proven from this snapshot")
    if str(owner_id) not in proof.account_charges:
        raise ApiError(409, "joint_custody_unresolved", "M11 custody cannot be proven from this snapshot")
    _require_quota(proof, owner_id, quota)
    return proof


def _result_index(files, job):
    if job.result_key is None or job.result_bytes is None or job.result_sha256 is None:
        raise ApiError(409, "result_not_ready", "Joint processing has no published terminal result")
    expected_key = f"derived/{job.owner_id}/{job.project_id}/results/{job.id}.json"
    if job.result_key != expected_key:
        raise ApiError(409, "joint_result_integrity", "Joint result receipt identity is inconsistent")
    body = files.read(expected_key, cap=native.MAX_JSON, expected_bytes=job.result_bytes,
                      expected_sha256=job.result_sha256)
    payload = native.bounded_json(body)
    if (type(payload) is not dict or payload.get("schema") != RESULT_SCHEMA
            or payload.get("job_id") != job.id or payload.get("state") != job.state
            or payload.get("scientific_acceptance") is not False
            or payload.get("authenticity_verified") is not False
            or payload.get("public_activation") is not False):
        raise ApiError(409, "joint_result_integrity", "Joint result claims do not match its job")
    return payload


def _read_verified_member(files, key: str, cap: int, expected_bytes: int, expected_sha256: str):
    """Open and hash an admitted file through the private root dirfd in chunks."""
    parent, name = files._parent(key)
    descriptor = None
    try:
        descriptor = files._open(parent, name)
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size != expected_bytes or info.st_size > cap:
            raise ValueError("joint_export_file_identity")
        chunks = []
        digest = hashlib.sha256()
        count = 0
        while True:
            block = os.read(descriptor, min(65536, cap + 1 - count))
            if not block:
                break
            count += len(block)
            if count > cap:
                raise ValueError("joint_export_member_cap")
            digest.update(block)
            chunks.append(block)
        after = os.fstat(descriptor)
        if ((info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
                != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
                or count != expected_bytes or digest.hexdigest() != expected_sha256):
            raise ValueError("joint_export_digest")
        return b"".join(chunks)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(parent)


def install_joint_job_routes(app, settings, current_user, get_session) -> None:
    router = APIRouter(prefix="/api/projects", tags=["joint-processing"])

    @router.post("/{project_id}/joint-jobs", status_code=202)
    async def admit(project_id: str, body: JointJobCreate, request: Request,
                    user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
        physical = _physical(request, session)
        owner_id = user.id
        await _owned_project(session, project_id, user)
        await session.rollback()
        await session.execute(text("BEGIN IMMEDIATE"))
        await _registered_0006(session)
        await session.refresh(user)
        await _owned_project(session, project_id, user)
        dataset = (await session.execute(select(ObservationDataset).where(
            ObservationDataset.id == str(body.dataset_id), ObservationDataset.project_id == project_id,
            ObservationDataset.owner_id == owner_id, ObservationDataset.parser_version == native.PARSER,
            ObservationDataset.modality == native.MODALITY,
        ))).scalar_one_or_none()
        if dataset is None:
            raise ApiError(404, "not_found", "Joint native dataset not found")

        active = (await session.execute(select(func.count()).select_from(ProcessingJob).where(
            ProcessingJob.method_id == METHOD, ProcessingJob.state.in_(("queued", "running")),
        ))).scalar_one()
        owner_active = (await session.execute(select(func.count()).select_from(ProcessingJob).where(
            ProcessingJob.owner_id == owner_id, ProcessingJob.method_id == METHOD,
            ProcessingJob.state.in_(("queued", "running")),
        ))).scalar_one()
        if active >= min(MAX_QUEUE, settings.max_queued_jobs) or owner_active >= ACTIVE_PER_OWNER:
            raise ApiError(429, "joint_queue_full", "The bounded M11 queue has no available reservation")

        job_id = str(uuid4())
        request_value = {"schema": "geophysics.joint-job-request/v1", "operation": "solve",
                         "dataset_id": dataset.id, "dataset_sha256": dataset.sha256,
                         "workflow": "joint-survey-workflow-1"}
        request_bytes = _json_bytes(request_value)
        preflight = {"schema": "geophysics.joint-job-preflight/v1", "reserved_bytes": native.MAX_BYTES,
                     "memory_limit_bytes": 2 * 1024**3, "scratch_limit_bytes": 256 * 1024**2,
                     "wall_limit_seconds": 1800, "execution": "pinned-linux-cp312"}
        created = utcnow().astimezone(timezone.utc).replace(tzinfo=None).isoformat(sep=" ")
        await session.execute(text(
            "INSERT INTO processing_jobs "
            "(id,project_id,owner_id,dataset_id,dataset_sha256,method_id,request_json,request_sha256,preflight,state,cancel_requested,created_at) "
            "VALUES (:id,:project,:owner,:dataset,:dataset_sha,:method,:request,:request_sha,:preflight,'queued',0,:created)"),
            {"id": job_id, "project": project_id, "owner": str(owner_id), "dataset": dataset.id,
             "dataset_sha": dataset.sha256, "method": METHOD, "request": request_bytes.decode("utf-8"),
             "request_sha": byte_sha(request_bytes), "preflight": _json_bytes(preflight).decode("utf-8"),
             "created": created})
        job = (await session.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))).scalar_one()
        await _proof(session, physical, owner_id, settings.account_quota_bytes)
        physical.leases.require_held()
        await session.commit()
        return _job_view(job)

    @router.get("/{project_id}/joint-jobs/{job_id}")
    async def get_job(project_id: str, job_id: str, request: Request,
                     user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
        physical = _physical(request, session)
        owner_id = user.id
        await _owned_project(session, project_id, user)
        await session.rollback()
        await session.execute(text("BEGIN"))
        await _registered_0006(session)
        job = await _load_owned_job(session, project_id, job_id, owner_id)
        await _proof(session, physical, owner_id, settings.account_quota_bytes)
        return JSONResponse(_job_view(job), headers={"Cache-Control": "no-store"})

    @router.post("/{project_id}/joint-jobs/{job_id}/cancel")
    async def cancel(project_id: str, job_id: str, request: Request,
                     user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
        physical = _physical(request, session)
        owner_id = user.id
        await _owned_project(session, project_id, user)
        await session.rollback()
        await session.execute(text("BEGIN IMMEDIATE"))
        await _registered_0006(session)
        await session.refresh(user)
        job = await _load_owned_job(session, project_id, job_id, owner_id)
        if job.state == "queued":
            # Keep the reservation until the M11 worker observes and publishes
            # the cancellation receipt; terminal state and custody stay atomic.
            job.cancel_requested = True
        elif job.state == "running":
            job.cancel_requested = True
        await session.flush()
        await _proof(session, physical, owner_id, settings.account_quota_bytes)
        physical.leases.require_held()
        await session.commit()
        return _job_view(job)

    @router.get("/{project_id}/joint-results/{job_id}")
    async def result(project_id: str, job_id: str, request: Request,
                    user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
        physical = _physical(request, session)
        owner_id = user.id
        await _owned_project(session, project_id, user)
        await session.rollback()
        await session.execute(text("BEGIN"))
        await _registered_0006(session)
        job = await _load_owned_job(session, project_id, job_id, owner_id)
        await _proof(session, physical, owner_id, settings.account_quota_bytes)
        payload = _result_index(physical.leases.files, job)
        return JSONResponse(payload, headers={"Cache-Control": "no-store"})

    @router.get("/{project_id}/joint-results")
    async def history(project_id: str, request: Request,
                      user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
        physical = _physical(request, session)
        owner_id = user.id
        await _owned_project(session, project_id, user)
        await session.rollback()
        await session.execute(text("BEGIN"))
        await _registered_0006(session)
        await _proof(session, physical, owner_id, settings.account_quota_bytes)
        jobs = (await session.execute(select(ProcessingJob).where(
            ProcessingJob.project_id == project_id, ProcessingJob.owner_id == owner_id,
            ProcessingJob.method_id == METHOD,
        ).order_by(ProcessingJob.created_at.desc(), ProcessingJob.id).limit(200))).scalars().all()
        payload = {"schema": HISTORY_SCHEMA, "owner_id": str(owner_id),
                   "project_id": project_id, "jobs": [
                       {key: _job_view(job)[key] for key in (
                           "job_id", "owner_id", "project_id", "dataset_id", "dataset_sha256",
                           "method_id", "request_sha256", "state", "cancel_requested", "error_code",
                           "index_available", "result_sha256", "result_bytes",
                       )} for job in jobs]}
        return JSONResponse(payload, headers={"Cache-Control": "no-store"})

    @router.get("/{project_id}/joint-results/{job_id}/export")
    async def export(project_id: str, job_id: str, request: Request,
                     user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
        physical = _physical(request, session)
        owner_id = user.id
        await _owned_project(session, project_id, user)
        await session.rollback()
        await session.execute(text("BEGIN"))
        await _registered_0006(session)
        job = await _load_owned_job(session, project_id, job_id, owner_id)
        await _proof(session, physical, owner_id, settings.account_quota_bytes)
        index = _result_index(physical.leases.files, job)
        members = (await session.execute(text(
            "SELECT name,storage_key,byte_count,sha256 FROM joint_result_artifacts "
            "WHERE job_id=:job ORDER BY name"), {"job": job.id})).mappings().all()
        stream = tempfile.SpooledTemporaryFile(max_size=8 * 1024**2, mode="w+b")
        total = 0
        try:
            with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED) as archive:
                archive.writestr("private-custody-index.json", _json_bytes(index))
                for member in members:
                    if MEMBER_NAME.fullmatch(member["name"]) is None:
                        raise ApiError(409, "joint_result_integrity", "Stored result member name is invalid")
                    total += member["byte_count"]
                    if total > native.MAX_BYTES:
                        raise ApiError(409, "joint_result_integrity", "Stored result exceeds the M11 export bound")
                    archive.writestr(member["name"], _read_verified_member(physical.leases.files,
                        member["storage_key"], native.MAX_BYTES, member["byte_count"], member["sha256"]))
            stream.seek(0)
        except BaseException:
            stream.close()
            raise

        def chunks():
            try:
                while block := stream.read(65536):
                    yield block
            finally:
                stream.close()

        return StreamingResponse(chunks(), media_type="application/zip", headers={
            "Content-Disposition": f'attachment; filename="m11-{job.id}.zip"',
            "Cache-Control": "no-store",
        }, background=BackgroundTask(stream.close))

    app.include_router(router)
