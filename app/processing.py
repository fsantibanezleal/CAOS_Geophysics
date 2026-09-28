"""Authenticated typed datasets, eligibility, bounded processing jobs and results."""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.bundle import build_bundle
from app.config import Settings
from app.errors import ApiError
from app.models import AccountUsage, ObservationDataset, ProcessingJob, User, utcnow
from app.processing_contract import (
    METHOD_ID, METHOD_MEMORY_BYTES, METHOD_SCRATCH_BYTES, METHOD_WALL_SECONDS,
    PARSER_VERSION, canonical_bytes, checked_derived_path, dataset_key,
    parse_gravity_dataset, result_key, sha256, validate_dataset_identity,
    validate_result_identity, verified_json,
)
from app.processing_storage import account_derived_usage
from app.projects import _owned_asset, _owned_project, _verified_file
from app.views import stored_utc


class DatasetCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    asset_id: uuid.UUID


class JobParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    threshold: float = Field(ge=1, le=10, allow_inf_nan=False)


class JobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset_id: uuid.UUID
    method_id: str = Field(min_length=1, max_length=80)
    parameters: JobParameters


def _date(value: datetime | None) -> str | None:
    return stored_utc(value).isoformat().replace("+00:00", "Z") if value else None


def _dataset_view(item: ObservationDataset) -> dict:
    return {
        "dataset_id": item.id, "project_id": item.project_id, "raw_asset_id": item.raw_asset_id,
        "version": item.version, "schema": "geophysics.observation-dataset/v1",
        "modality": item.modality, "row_count": item.row_count, "parser_version": item.parser_version,
        "raw_sha256": item.raw_sha256, "sha256": item.sha256, "created_at": _date(item.created_at),
        "qc_verdict": "parsed_for_flag_qc_only",
    }


def _job_view(item: ProcessingJob) -> dict:
    return {
        "job_id": item.id, "project_id": item.project_id, "dataset_id": item.dataset_id,
        "dataset_sha256": item.dataset_sha256, "method_id": item.method_id,
        "request": item.request_json, "request_sha256": item.request_sha256,
        "preflight": item.preflight, "state": item.state, "cancel_requested": item.cancel_requested,
        "created_at": _date(item.created_at), "started_at": _date(item.started_at),
        "finished_at": _date(item.finished_at), "wall_ms": item.wall_ms,
        "peak_rss_bytes": item.peak_rss_bytes, "scratch_bytes": item.scratch_bytes,
        "result_sha256": item.result_sha256,
        "error": {"code": item.error_code, "message": item.error_message} if item.error_code else None,
        "result_url": f"/api/projects/{item.project_id}/jobs/{item.id}/result" if item.state == "succeeded" else None,
    }


async def _owned_dataset(session: AsyncSession, project_id: str, dataset_id: str, user: User) -> ObservationDataset:
    await _owned_project(session, project_id, user)
    row = (await session.execute(select(ObservationDataset).where(
        ObservationDataset.id == dataset_id, ObservationDataset.project_id == project_id,
        ObservationDataset.owner_id == user.id,
    ))).scalar_one_or_none()
    if row is None:
        raise ApiError(404, "not_found", "Dataset not found")
    return row


async def _owned_job(session: AsyncSession, project_id: str, job_id: str, user: User) -> ProcessingJob:
    await _owned_project(session, project_id, user)
    row = (await session.execute(select(ProcessingJob).where(
        ProcessingJob.id == job_id, ProcessingJob.project_id == project_id,
        ProcessingJob.owner_id == user.id,
    ))).scalar_one_or_none()
    if row is None:
        raise ApiError(404, "not_found", "Processing job not found")
    return row


def _dataset_payload(settings: Settings, dataset: ObservationDataset) -> dict:
    expected_key = dataset_key(str(dataset.owner_id), dataset.project_id, dataset.id)
    if dataset.storage_key != expected_key:
        raise ApiError(409, "derived_integrity_failed", "Dataset storage identity differs from its receipt")
    payload = verified_json(settings, expected_key, dataset.sha256, dataset.byte_count)
    validate_dataset_identity(payload, dataset)
    return payload


def _result_payload(settings: Settings, job: ProcessingJob) -> dict:
    if job.state != "succeeded" or not job.result_key or not job.result_sha256 or job.result_bytes is None:
        raise ApiError(409, "result_not_ready", "Processing result is not available")
    expected_key = result_key(str(job.owner_id), job.project_id, job.id)
    if job.result_key != expected_key:
        raise ApiError(409, "derived_integrity_failed", "Result storage identity differs from its receipt")
    payload = verified_json(settings, expected_key, job.result_sha256, job.result_bytes)
    validate_result_identity(payload, job)
    return payload


def install_processing_routes(app, settings: Settings, current_user, get_session) -> None:
    router = APIRouter(prefix="/api/projects/{project_id}", tags=["processing"])

    @router.post("/datasets", status_code=201)
    async def create_dataset(
        project_id: str, request: DatasetCreate,
        user: User = Depends(current_user), session: AsyncSession = Depends(get_session),
    ):
        await _owned_project(session, project_id, user)
        await session.rollback()
        await session.execute(text("BEGIN IMMEDIATE"))
        await session.refresh(user)
        asset, source = await _owned_asset(session, project_id, str(request.asset_id), user)
        if asset.byte_count > settings.max_dataset_bytes:
            raise ApiError(413, "dataset_too_large", "Gravity dataset exceeds the processing byte cap")
        existing = (await session.execute(select(ObservationDataset).where(
            ObservationDataset.raw_asset_id == asset.id, ObservationDataset.parser_version == PARSER_VERSION,
        ))).scalar_one_or_none()
        if existing is not None:
            raise ApiError(409, "dataset_exists", "This raw asset already has an immutable processed dataset")
        raw_path = await asyncio.to_thread(_verified_file, settings, asset)
        raw = await asyncio.to_thread(raw_path.read_bytes)
        dataset_id = str(uuid.uuid4())
        payload = parse_gravity_dataset(
            raw, dataset_id=dataset_id, owner_id=str(user.id), project_id=project_id,
            asset=asset, source=source, settings=settings,
        )
        encoded = canonical_bytes(payload)
        raw_usage = (await session.execute(select(AccountUsage.raw_bytes).where(
            AccountUsage.user_id == user.id,
        ))).scalar_one_or_none() or 0
        if raw_usage + await account_derived_usage(session, user.id) + len(encoded) > settings.account_quota_bytes:
            raise ApiError(507, "account_quota_exceeded", "Account private-byte quota exceeded")
        key = dataset_key(str(user.id), project_id, dataset_id)
        target = checked_derived_path(settings, key)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() or target.is_symlink():
            raise ApiError(409, "derived_state_unresolved", "Dataset storage target already exists")
        created = False
        commit_attempted = False
        try:
            with target.open("xb") as output:
                output.write(encoded)
                output.flush()
                os.fsync(output.fileno())
            created = True
            item = ObservationDataset(
                id=dataset_id, project_id=project_id, owner_id=user.id, raw_asset_id=asset.id,
                version=1, parser_version=PARSER_VERSION, modality="gravity_station",
                row_count=len(payload["station_ids"]), raw_sha256=asset.sha256,
                sha256=sha256(encoded), byte_count=len(encoded), storage_key=key, created_at=utcnow(),
            )
            session.add(item)
            commit_attempted = True
            await session.commit()
            return _dataset_view(item)
        except Exception:
            await session.rollback()
            if created and not commit_attempted:
                target.unlink(missing_ok=True)
            raise

    @router.get("/datasets")
    async def list_datasets(
        project_id: str, user: User = Depends(current_user), session: AsyncSession = Depends(get_session),
    ):
        await _owned_project(session, project_id, user)
        rows = (await session.execute(select(ObservationDataset).where(
            ObservationDataset.project_id == project_id, ObservationDataset.owner_id == user.id,
        ).order_by(ObservationDataset.created_at))).scalars().all()
        return {"datasets": [_dataset_view(row) for row in rows]}

    @router.get("/datasets/{dataset_id}")
    async def get_dataset(
        project_id: str, dataset_id: str, user: User = Depends(current_user),
        session: AsyncSession = Depends(get_session),
    ):
        dataset = await _owned_dataset(session, project_id, dataset_id, user)
        return JSONResponse(_dataset_payload(settings, dataset), headers={"Cache-Control": "no-store"})

    @router.get("/datasets/{dataset_id}/methods")
    async def methods(
        project_id: str, dataset_id: str, user: User = Depends(current_user),
        session: AsyncSession = Depends(get_session),
    ):
        dataset = await _owned_dataset(session, project_id, dataset_id, user)
        _dataset_payload(settings, dataset)
        return {
            "dataset_id": dataset.id,
            "methods": [{"method_id": METHOD_ID, "eligible": True, "lane": "online_processing",
                         "scope": "flag-only QC; no correction or inversion"}],
            "unavailable": [{"method_id": f"M{number:02d}", "eligible": False, "lane": "not_activated",
                             "reason": "No validated online adapter and host benchmark for this complete method"}
                            for number in range(1, 14)],
        }

    @router.post("/jobs", status_code=202)
    async def submit_job(
        project_id: str, request: JobCreate,
        user: User = Depends(current_user), session: AsyncSession = Depends(get_session),
    ):
        await _owned_project(session, project_id, user)
        await session.rollback()
        await session.execute(text("BEGIN IMMEDIATE"))
        await session.refresh(user)
        dataset = await _owned_dataset(session, project_id, str(request.dataset_id), user)
        _dataset_payload(settings, dataset)
        if dataset.modality != "gravity_station" or request.method_id != METHOD_ID:
            raise ApiError(422, "method_ineligible", "Method is not eligible for this dataset")
        active = (await session.execute(select(func.count()).select_from(ProcessingJob).where(
            ProcessingJob.owner_id == user.id, ProcessingJob.state.in_(["queued", "running"]),
        ))).scalar_one()
        if active:
            raise ApiError(409, "active_job_limit", "Only one active processing job per account is allowed")
        queued = (await session.execute(select(func.count()).select_from(ProcessingJob).where(
            ProcessingJob.state == "queued",
        ))).scalar_one()
        if queued >= settings.max_queued_jobs:
            raise ApiError(429, "job_queue_full", "Processing queue is full")
        estimated_memory = 64 * 1024 * 1024 + 20 * dataset.byte_count
        memory = min(settings.worker_memory_bytes, METHOD_MEMORY_BYTES)
        scratch = min(settings.worker_scratch_bytes, METHOD_SCRATCH_BYTES)
        wall = min(settings.worker_wall_seconds, METHOD_WALL_SECONDS)
        if estimated_memory > memory or 4 * dataset.byte_count > scratch:
            raise ApiError(413, "job_resource_ineligible", "Dataset exceeds this method's resource limits")
        raw_usage = (await session.execute(select(AccountUsage.raw_bytes).where(
            AccountUsage.user_id == user.id,
        ))).scalar_one_or_none() or 0
        if raw_usage + await account_derived_usage(session, user.id) + METHOD_SCRATCH_BYTES > settings.account_quota_bytes:
            raise ApiError(507, "account_quota_exceeded", "Account private-byte quota exceeded")
        job_id = str(uuid.uuid4())
        parameters = request.parameters.model_dump(mode="json")
        immutable = {
            "schema": "geophysics.processing-request/v1", "job_id": job_id,
            "project_id": project_id, "dataset_id": dataset.id, "dataset_sha256": dataset.sha256,
            "method_id": METHOD_ID, "parameters": parameters,
        }
        item = ProcessingJob(
            id=job_id, project_id=project_id, owner_id=user.id,
            dataset_id=dataset.id, dataset_sha256=dataset.sha256, method_id=METHOD_ID,
            request_json=immutable, request_sha256=sha256(canonical_bytes(immutable)),
            preflight={"estimated_memory_bytes": estimated_memory, "memory_limit_bytes": memory,
                       "scratch_limit_bytes": scratch, "wall_limit_seconds": wall},
            state="queued", cancel_requested=False, created_at=utcnow(),
        )
        session.add(item)
        await session.commit()
        return _job_view(item)

    @router.get("/jobs")
    async def list_jobs(
        project_id: str, user: User = Depends(current_user), session: AsyncSession = Depends(get_session),
    ):
        await _owned_project(session, project_id, user)
        rows = (await session.execute(select(ProcessingJob).where(
            ProcessingJob.project_id == project_id, ProcessingJob.owner_id == user.id,
        ).order_by(ProcessingJob.created_at))).scalars().all()
        return {"jobs": [_job_view(row) for row in rows]}

    @router.get("/jobs/{job_id}")
    async def get_job(
        project_id: str, job_id: str, user: User = Depends(current_user),
        session: AsyncSession = Depends(get_session),
    ):
        return _job_view(await _owned_job(session, project_id, job_id, user))

    @router.post("/jobs/{job_id}/cancel")
    async def cancel_job(
        project_id: str, job_id: str, user: User = Depends(current_user),
        session: AsyncSession = Depends(get_session),
    ):
        await _owned_project(session, project_id, user)
        await session.rollback()
        await session.execute(text("BEGIN IMMEDIATE"))
        await session.refresh(user)
        item = await _owned_job(session, project_id, job_id, user)
        if item.state == "queued":
            item.state = "cancelled"
            item.cancel_requested = True
            item.error_code = "user_cancelled"
            item.error_message = "Owner cancelled before execution"
            item.finished_at = utcnow()
        elif item.state == "running":
            item.cancel_requested = True
        else:
            raise ApiError(409, "job_terminal", "A terminal job cannot be cancelled")
        await session.commit()
        return _job_view(item)

    @router.get("/jobs/{job_id}/result")
    async def get_result(
        project_id: str, job_id: str, user: User = Depends(current_user),
        session: AsyncSession = Depends(get_session),
    ):
        job = await _owned_job(session, project_id, job_id, user)
        return JSONResponse(_result_payload(settings, job), headers={"Cache-Control": "no-store"})

    @router.get("/jobs/{job_id}/export")
    async def export_result(
        project_id: str, job_id: str, user: User = Depends(current_user),
        session: AsyncSession = Depends(get_session),
    ):
        job = await _owned_job(session, project_id, job_id, user)
        dataset = await _owned_dataset(session, project_id, job.dataset_id, user)
        data = _dataset_payload(settings, dataset)
        result = _result_payload(settings, job)
        try:
            bundle = build_bundle(data, result, dataset.sha256, job.result_sha256)
        except ValueError as exc:
            raise ApiError(409, "derived_integrity_failed", "Processing bundle contract is invalid") from exc
        response = StreamingResponse(iter([bundle]), media_type="application/zip")
        response.headers["Content-Disposition"] = f'attachment; filename="processing-{job.id}.zip"'
        response.headers["Cache-Control"] = "no-store"
        return response

    app.include_router(router)
