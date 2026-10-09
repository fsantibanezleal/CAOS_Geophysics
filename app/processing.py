"""Authenticated typed datasets, eligibility, bounded processing jobs and results."""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.bundle import build_bundle
from app.config import Settings
from app.errors import ApiError
from app.models import AccountUsage, ObservationDataset, ProcessingJob, User, utcnow
from app.mt_contract import (
    EDI_PARSER_VERSION, EDI_SOURCE_LIMIT, M05_ID, M06_ID, M05_MEMORY_BYTES,
    M06_MEMORY_BYTES, M05_SCRATCH_BYTES, M06_SCRATCH_BYTES,
    M05_WALL_SECONDS, M06_WALL_SECONDS, M05Parameters, M06Parameters,
    parse_edi_envelope,
)
from app.processing_contract import (
    METHOD_ID, METHOD_MEMORY_BYTES, METHOD_SCRATCH_BYTES, METHOD_WALL_SECONDS,
    PARSER_VERSION, canonical_bytes, checked_derived_path, dataset_key,
    parse_gravity_dataset, result_key, sha256, validate_dataset_identity,
    validate_result_identity, verified_json,
)
from app.processing_storage import account_derived_usage
from app.profile_contract import (
    PARSER_VERSION as PROFILE_PARSER_VERSION, PROFILE_FORMATS, PROFILE_METHODS,
    PROFILE_SOURCE_LIMIT, PROFILE_MEMORY_BYTES, PROFILE_SCRATCH_BYTES, PROFILE_WALL_SECONDS,
    ProfileParameters, parse_profile_envelope, profile_child_hash, profile_code_hashes,
)
from app.projects import _owned_asset, _owned_project, _verified_file
from app.views import stored_utc
from app.waveform_contract import (
    METHOD_ID as WAVEFORM_ID, MODALITY as WAVEFORM_MODALITY,
    WaveformParameters, SCRATCH as WAVEFORM_SCRATCH, MEMORY as WAVEFORM_MEMORY,
    WALL as WAVEFORM_WALL, context_available,
)


class DatasetCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    asset_id: uuid.UUID
    waveform_request: dict | None = None
    profile_metadata: dict | None = None


class JobParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    threshold: float = Field(ge=1, le=10, allow_inf_nan=False)


class JobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset_id: uuid.UUID
    method_id: str = Field(min_length=1, max_length=80)
    parameters: JobParameters | M05Parameters | M06Parameters | ProfileParameters | WaveformParameters


def _date(value: datetime | None) -> str | None:
    return stored_utc(value).isoformat().replace("+00:00", "Z") if value else None


def _dataset_view(item: ObservationDataset) -> dict:
    return {
        "dataset_id": item.id, "project_id": item.project_id, "raw_asset_id": item.raw_asset_id,
        "version": item.version, "schema": "geophysics.observation-dataset/v1",
        "modality": item.modality, "row_count": item.row_count, "parser_version": item.parser_version,
        "raw_sha256": item.raw_sha256, "sha256": item.sha256, "created_at": _date(item.created_at),
        "qc_verdict": "structural_only_not_scientifically_admitted" if item.parser_version == 'gravity-stations-json/v1'
                      else "structural_index_not_physical_qc" if item.modality == WAVEFORM_MODALITY
                      else "awaiting_full_tensor_qc" if item.modality == "edi_transfer_function"
                      else "parsed_not_numerically_inverted" if item.modality in {"ert_profile", "traveltime_profile"}
                      else "parsed_for_flag_qc_only",
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


async def _eligible_mt_qc(session: AsyncSession, settings: Settings, dataset: ObservationDataset,
                          qc_job_id: str | None = None) -> tuple[ProcessingJob, dict] | None:
    query = select(ProcessingJob).where(
        ProcessingJob.owner_id == dataset.owner_id, ProcessingJob.project_id == dataset.project_id,
        ProcessingJob.dataset_id == dataset.id, ProcessingJob.dataset_sha256 == dataset.sha256,
        ProcessingJob.method_id == M05_ID, ProcessingJob.state == "succeeded",
    )
    if qc_job_id is not None:
        query = query.where(ProcessingJob.id == qc_job_id)
    rows = (await session.execute(query.order_by(ProcessingJob.created_at.desc()))).scalars().all()
    for job in rows:
        result = _result_payload(settings, job)
        if (result.get("raw_sha256") == dataset.raw_sha256
                and result["screen"].get("one_d_inversion_eligible") is True):
            return job, result
    return None


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
        if asset.detected_format == 'gravity_stations_json':
            from app.physical_assembly import PhysicalAssembly
            from app.physical_root_route import create_physical_root
            physical = getattr(app.state, 'physical_assembly', None)
            if not isinstance(physical, PhysicalAssembly):
                raise ApiError(409, 'physical_admission_closed', 'Physical dataset assembly is not installed')
            if request.waveform_request is not None or request.profile_metadata is not None:
                raise ApiError(422, 'method_ineligible', 'Physical originals do not accept waveform or profile metadata')
            return _dataset_view(await create_physical_root(settings, session, physical,
                owner_id=str(user.id), project_id=project_id, raw_asset_id=asset.id))
        if asset.detected_format == "miniseed":
            from app.waveform_processing import create_waveform_dataset
            return _dataset_view(await create_waveform_dataset(settings, session, user, project_id,
                asset, source, request.waveform_request))
        if request.waveform_request is not None:
            raise ApiError(422, "method_ineligible", "Waveform request is only valid for MiniSEED")
        is_edi = asset.detected_format == "edi"
        is_profile = asset.detected_format in PROFILE_FORMATS
        if asset.byte_count > (PROFILE_SOURCE_LIMIT if is_profile else EDI_SOURCE_LIMIT if is_edi else settings.max_dataset_bytes):
            raise ApiError(413, "dataset_too_large", "EDI exceeds the processing byte cap" if is_edi
                           else "Gravity dataset exceeds the processing byte cap")
        parser_version = PROFILE_PARSER_VERSION if is_profile else EDI_PARSER_VERSION if is_edi else PARSER_VERSION
        existing = (await session.execute(select(ObservationDataset).where(
            ObservationDataset.raw_asset_id == asset.id, ObservationDataset.parser_version == parser_version,
        ))).scalar_one_or_none()
        if existing is not None:
            raise ApiError(409, "dataset_exists", "This raw asset already has an immutable processed dataset")
        raw_path = await asyncio.to_thread(_verified_file, settings, asset)
        raw = await asyncio.to_thread(raw_path.read_bytes)
        dataset_id = str(uuid.uuid4())
        if is_profile:
            payload = parse_profile_envelope(raw, metadata=request.profile_metadata,
                dataset_id=dataset_id, owner_id=str(user.id), project_id=project_id, asset=asset, source=source)
            if payload["dimensions"]["measurement"] > settings.max_dataset_rows:
                raise ApiError(413, "dataset_too_large", "Profile row count exceeds the admitted online envelope")
        elif is_edi:
            payload = parse_edi_envelope(raw, dataset_id=dataset_id, owner_id=str(user.id),
                                         project_id=project_id, asset=asset, source=source)
        else:
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
                version=1, parser_version=parser_version,
                modality=payload["modality"],
                row_count=payload["dimensions"]["measurement"] if is_profile else payload["dimensions"]["frequency"] if is_edi else len(payload["station_ids"]),
                raw_sha256=asset.sha256,
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
        if dataset.parser_version == 'gravity-stations-json/v1':
            from app.physical_read import owned_dataset_payload
            value = await owned_dataset_payload(session, getattr(app.state, 'physical_assembly', None), dataset)
            return JSONResponse(value, headers={'Cache-Control': 'no-store'})
        return JSONResponse(_dataset_payload(settings, dataset), headers={"Cache-Control": "no-store"})

    @router.get("/datasets/{dataset_id}/methods")
    async def methods(
        project_id: str, dataset_id: str, user: User = Depends(current_user),
        session: AsyncSession = Depends(get_session),
    ):
        dataset = await _owned_dataset(session, project_id, dataset_id, user)
        if dataset.parser_version == 'gravity-stations-json/v1':
            from app.physical_read import owned_dataset_payload
            from app.physical_persistence import CORRECTION, TRANSFORM
            await owned_dataset_payload(session, getattr(app.state, 'physical_assembly', None), dataset)
            # No flag-QC fallback or source-hash-only claim of child admission.
            # The concrete native dispatcher must supply its fixed reviewed
            # runtime before these two actual scientific methods can be queued.
            return {'dataset_id': dataset.id, 'methods': [], 'unavailable': [
                dict(method_id=method, eligible=False, lane='native_context_pending',
                    reason='Physical scientific worker runtime is not yet installed')
                for method in (CORRECTION, TRANSFORM)]}
        data = _dataset_payload(settings, dataset)
        if dataset.modality in {"ert_profile", "traveltime_profile"}:
            method = data["method_id"]
            if not settings.profile_online_enabled:
                return {"dataset_id": dataset.id, "methods": [], "unavailable": [{
                    "method_id": method, "eligible": False, "lane": "pending_host_admission",
                    "reason": "Use the complete local profile pipeline and result importer; actual host admission is not yet recorded"}]}
            return {"dataset_id": dataset.id, "methods": [{"method_id": method, "eligible": True,
                    "lane": "online_processing", "scope": "Original profile inverse with independent physical and holdout gates"}],
                    "unavailable": []}
        if dataset.modality == WAVEFORM_MODALITY:
            available = context_available(settings)
            method = {"method_id": WAVEFORM_ID, "eligible": available,
                "lane": "online_processing" if available else "native_context_pending",
                **({"scope": "Conditional native response/QC/filter/PSD and unlabelled onset candidates"}
                   if available else {"reason": "Selected native context must be validated by the worker before execution"})}
            return {"dataset_id": dataset.id, "methods": [method] if available else [],
                    "unavailable": [] if available else [method]}
        if dataset.modality == "edi_transfer_function":
            if not settings.mt_online_enabled:
                return {"dataset_id": dataset.id, "methods": [], "unavailable": [
                    {"method_id": method, "eligible": False, "lane": "pending_host_admission",
                     "reason": "Actual ML VPS numerical and resource admission is not recorded"}
                    for method in (M05_ID, M06_ID)]}
            qualified = await _eligible_mt_qc(session, settings, dataset)
            return {
                "dataset_id": dataset.id,
                "methods": [{"method_id": M05_ID, "eligible": True, "lane": "online_processing",
                             "scope": "Full original EDI tensor QC; no inverse"}]
                + ([{"method_id": M06_ID, "eligible": True, "lane": "online_processing",
                     "qc_job_id": qualified[0].id, "scope": "conditional fixed-thickness 1D TRF"}]
                   if qualified and 12 <= dataset.row_count <= 64 else []),
                "unavailable": [] if qualified and 12 <= dataset.row_count <= 64 else [{
                    "method_id": M06_ID, "eligible": False, "lane": "ineligible",
                    "reason": "A passing M05 full-tensor screen and 12..64 frequencies are required"}],
            }
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
        payload = _dataset_payload(settings, dataset)
        mt = dataset.modality == "edi_transfer_function"
        profile = dataset.modality in {"ert_profile", "traveltime_profile"}
        waveform = dataset.modality == WAVEFORM_MODALITY
        if profile:
            if not settings.profile_online_enabled:
                raise ApiError(409, "host_admission_pending", "Profile online jobs require actual ML VPS admission")
            if request.method_id != payload["method_id"] or request.method_id not in PROFILE_METHODS:
                raise ApiError(422, "method_ineligible", "Method does not match this original profile")
            parameters_dict = request.parameters.model_dump(mode="json")
            try:
                ProfileParameters.model_validate(parameters_dict)
            except ValueError:
                raise ApiError(422, "method_ineligible", "Profile solver settings must match the validated frozen contract")
            asset, _source = await _owned_asset(session, project_id, dataset.raw_asset_id, user)
            await asyncio.to_thread(_verified_file, settings, asset)
            method_memory, method_scratch, method_wall = PROFILE_MEMORY_BYTES, PROFILE_SCRATCH_BYTES, PROFILE_WALL_SECONDS
            estimated_memory = 256 * 1024 * 1024 + 64 * dataset.byte_count
            estimated_scratch = PROFILE_SOURCE_LIMIT + 8 * dataset.byte_count
            qc_screen_sha = None
        elif waveform:
            if not context_available(settings):
                raise ApiError(409, "waveform_context_unavailable", "Waveform execution requires its selected native context")
            if request.method_id != WAVEFORM_ID or not isinstance(request.parameters, WaveformParameters):
                raise ApiError(422,"method_ineligible","Method or parameters are not eligible for waveform data")
            if request.parameters.scientific_request_sha256 != payload["scientific_request_sha256"]:
                raise ApiError(409,"request_changed","Waveform request differs from the immutable dataset")
            from app.waveform_processing import validate_source_rows
            await validate_source_rows(session,settings,dataset,payload)
            method_memory,method_scratch,method_wall=WAVEFORM_MEMORY,WAVEFORM_SCRATCH,WAVEFORM_WALL
            estimated_memory,estimated_scratch=method_memory,method_scratch
            qc_screen_sha=None
        elif mt:
            if not settings.mt_online_enabled:
                raise ApiError(409, "host_admission_pending", "MT online jobs require an actual ML VPS admission receipt")
            asset, _source = await _owned_asset(session, project_id, dataset.raw_asset_id, user)
            await asyncio.to_thread(_verified_file, settings, asset)
            if request.method_id == M05_ID and isinstance(request.parameters, M05Parameters):
                method_memory, method_scratch, method_wall = M05_MEMORY_BYTES, M05_SCRATCH_BYTES, M05_WALL_SECONDS
                estimated_memory = 256 * 1024 * 1024 + 64 * payload["parent_raw_bytes"]
                estimated_scratch = payload["parent_raw_bytes"] + 2 * 1024 * 1024
                qc_screen_sha = None
            elif request.method_id == M06_ID and isinstance(request.parameters, M06Parameters):
                if not 12 <= dataset.row_count <= 64:
                    raise ApiError(422, "method_ineligible", "M06 needs 12..64 original frequencies")
                eligible = await _eligible_mt_qc(session, settings, dataset, str(request.parameters.qc_job_id))
                if eligible is None:
                    raise ApiError(422, "method_ineligible", "A passing M05 screen for this exact dataset is required")
                method_memory, method_scratch, method_wall = M06_MEMORY_BYTES, M06_SCRATCH_BYTES, M06_WALL_SECONDS
                estimated_memory = 384 * 1024 * 1024 + 2 * 1024 * 1024 * request.parameters.bootstrap_samples
                estimated_scratch = (payload["parent_raw_bytes"] + 8 * 1024 * 1024
                                     + 128 * 1024 * request.parameters.bootstrap_samples)
                qc_screen_sha = sha256(canonical_bytes(eligible[1]["screen"]))
            else:
                raise ApiError(422, "method_ineligible", "Method or parameters are not eligible for this EDI")
        elif dataset.modality == "gravity_station" and request.method_id == METHOD_ID and isinstance(request.parameters, JobParameters):
            method_memory, method_scratch, method_wall = METHOD_MEMORY_BYTES, METHOD_SCRATCH_BYTES, METHOD_WALL_SECONDS
            estimated_memory = 64 * 1024 * 1024 + 20 * dataset.byte_count
            estimated_scratch = 4 * dataset.byte_count
            qc_screen_sha = None
        else:
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
        memory = min(settings.worker_memory_bytes, method_memory)
        scratch = min(settings.worker_scratch_bytes, method_scratch)
        wall = min(settings.worker_wall_seconds, method_wall)
        if estimated_memory > memory or estimated_scratch > scratch:
            raise ApiError(413, "job_resource_ineligible", "Dataset exceeds this method's resource limits")
        raw_usage = (await session.execute(select(AccountUsage.raw_bytes).where(
            AccountUsage.user_id == user.id,
        ))).scalar_one_or_none() or 0
        if raw_usage + await account_derived_usage(session, user.id) + method_scratch > settings.account_quota_bytes:
            raise ApiError(507, "account_quota_exceeded", "Account private-byte quota exceeded")
        job_id = str(uuid.uuid4())
        parameters = request.parameters.model_dump(mode="json")
        immutable = {
            "schema": "geophysics.processing-request/v1", "job_id": job_id,
            "project_id": project_id, "dataset_id": dataset.id, "dataset_sha256": dataset.sha256,
            "method_id": request.method_id, "parameters": parameters,
        }
        if mt or profile:
            immutable.update(raw_asset_id=dataset.raw_asset_id, raw_sha256=dataset.raw_sha256)
            if profile:
                immutable.update(profile_child_sha256=profile_child_hash(),
                                 profile_code_hashes=profile_code_hashes(request.method_id))
            if qc_screen_sha is not None:
                immutable["qc_screen_sha256"] = qc_screen_sha
        if waveform:
            from app.waveform_contract import implementation_sha256
            immutable.update(waveform_sources=payload["sources"], scientific_request=payload["request"],
                             scientific_request_sha256=payload["scientific_request_sha256"],
                             implementation_sha256=implementation_sha256())
        preflight = {"estimated_memory_bytes": estimated_memory, "memory_limit_bytes": memory,
                     "scratch_limit_bytes": scratch, "wall_limit_seconds": wall}
        if mt or profile:
            preflight["estimated_scratch_bytes"] = estimated_scratch
        if waveform:
            preflight.update(estimated_scratch_bytes=estimated_scratch,
                memory_kind="platform_committed_or_cgroup_charge_not_rss", cpu_budget_ns=60000000000,
                cpu_stop_ns=57000000000)
        item = ProcessingJob(
            id=job_id, project_id=project_id, owner_id=user.id,
            dataset_id=dataset.id, dataset_sha256=dataset.sha256, method_id=request.method_id,
            request_json=immutable, request_sha256=sha256(canonical_bytes(immutable)),
            preflight=preflight,
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
        payload = _result_payload(settings, job)
        # Canonical lexical bytes preserve the stored digest and Python float
        # tokens for independently checked profile producer content.
        return Response(canonical_bytes(payload), media_type="application/json", headers={"Cache-Control": "no-store"})

    @router.get("/jobs/{job_id}/export")
    async def export_result(
        project_id: str, job_id: str, user: User = Depends(current_user),
        session: AsyncSession = Depends(get_session),
    ):
        job = await _owned_job(session, project_id, job_id, user)
        dataset = await _owned_dataset(session, project_id, job.dataset_id, user)
        data = _dataset_payload(settings, dataset)
        result = _result_payload(settings, job)
        if job.method_id == WAVEFORM_ID:
            from app.waveform_result import result_directory, zip_response
            directory=await result_directory(session,settings,job,result)
            return await asyncio.to_thread(zip_response,settings,directory,result)
        try:
            bundle = build_bundle(data, result, dataset.sha256, job.result_sha256)
        except ValueError as exc:
            raise ApiError(409, "derived_integrity_failed", "Processing bundle contract is invalid") from exc
        response = StreamingResponse(iter([bundle]), media_type="application/zip")
        response.headers["Content-Disposition"] = f'attachment; filename="processing-{job.id}.zip"'
        response.headers["Cache-Control"] = "no-store"
        return response

    @router.get('/jobs/{job_id}/artifacts/{name}')
    async def waveform_member(project_id: str,job_id: str,name: str,user: User=Depends(current_user),
                              session: AsyncSession=Depends(get_session)):
        job=await _owned_job(session,project_id,job_id,user)
        if job.method_id!=WAVEFORM_ID:
            raise ApiError(404,'not_found','Waveform member not found')
        payload=_result_payload(settings,job)
        row=next((item for item in payload['members'] if item['name']==name),None)
        if row is None:
            raise ApiError(404,'not_found','Waveform member not found')
        from app.waveform_result import result_directory, member_response
        directory=await result_directory(session,settings,job,payload)
        return member_response(directory,name,row)

    app.include_router(router)
