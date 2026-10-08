"""Single-artifact owned numeric replay custody, not online magnetic execution.

Parent dispatchers call these functions after existing auth/CSRF. They never
change the service union, runtime flags or native controller themselves.
"""

from __future__ import annotations

from contextlib import contextmanager
import asyncio
import hashlib
import json
import os
import stat
from uuid import uuid4

from sqlalchemy import select, text

from app.errors import ApiError
from app.magnetic_contract import (science, validate_magnetic_dataset, _source, _uuid,
                                  parse_magnetic_dataset, validate_physical_record)
from app.magnetic_results import LOCAL_MAGNETIC_METHOD_ID, validate_owned_magnetic_result
from app.models import ObservationDataset, ProcessingJob, Project, RawAsset, SourceRecord, utcnow
from app.processing_contract import canonical_bytes, dataset_key, checked_derived_path

MAX_ZIP = 128 * 1024**2
REQUEST_KEYS = frozenset("schema dataset_id dataset_sha256 method_id parameters".split())
PARAMETER_KEYS = frozenset("request_sha256 generation_sha256 configuration_sha256".split())


def _bad(code="derived_integrity_failed", status=409):
    raise ApiError(status, code, "Owned magnetic result custody could not be verified")


def zip_result_key(owner_id, project_id, job_id):
    for value in (owner_id, project_id, job_id):
        _uuid(value)
    return f"derived/{owner_id}/{project_id}/results/{job_id}.zip"


def zip_result_path(settings, key):
    science()
    from magnetic_local_paths import external_path
    parts = key.split("/")
    if (len(parts) != 5 or parts[0] != "derived" or parts[3] != "results"
            or not parts[4].endswith(".zip")
            or zip_result_key(parts[1], parts[2], parts[4][:-4]) != key):
        _bad()
    root = external_path(settings.data_dir)
    path = external_path(root.joinpath(*parts))
    if not path.is_relative_to(root):
        _bad()
    return path


def _read(path, maximum=MAX_ZIP):
    try:
        return _read_held(path, maximum)
    except OSError:
        _bad()


def _read_held(path, maximum):
    from magnetic_local_paths import external_path
    path = external_path(path)
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0) | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(fd, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= maximum:
            _bad()
        raw = stream.read(maximum + 1)
        after = os.fstat(stream.fileno())
        visible = path.stat(follow_symlinks=False)
        identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        # Python3.12 on Windows exposes changed-time through fstat but creation
        # time through path.stat's deprecated st_ctime. Never compare those two
        # different clocks as one identity. Both held-FD snapshots still include
        # changed-time; visible path must match dev/inode/size/mtime.
        path_identity = lambda s: identity(s)[:-1] if os.name == "nt" else identity(s)
        if identity(before) != identity(after) or path_identity(after) != path_identity(visible) or len(raw) != before.st_size:
            _bad()
    return raw


def _write(path, raw):
    """Exclusive private creation and readback, never chmod/adopt old bytes."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
                 | getattr(os, "O_BINARY", 0), 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    if _read(path) != raw:
        _bad()


@contextmanager
def _generation(raw, temp_root, *, stage_name=None):
    """Fresh explicit external scratch; exact verified files only are removed."""
    science()
    from magnetic_local_paths import external_path
    from magnetic_result_export import import_zip
    root = external_path(temp_root)
    if not root.is_dir():
        _bad()
    stage = root / (stage_name or f"magnetic-replay-{uuid4()}")
    stage.mkdir(mode=0o700)
    archive, bundle = stage / "numeric.zip", stage / "generation"
    _write(archive, raw)
    # An unsuccessful import may retain unknown interrupted custody. Do not sweep.
    imported = import_zip(archive, bundle)
    inventory = {p: hashlib.sha256(_read(p)).hexdigest() for p in bundle.iterdir()}
    try:
        yield bundle, imported
    finally:
        if (set(stage.iterdir()) != {archive, bundle} or set(bundle.iterdir()) != set(inventory)
                or _read(archive) != raw
                or any(hashlib.sha256(_read(p)).hexdigest() != sha for p, sha in inventory.items())):
            _bad("magnetic_custody_debt")
        for p in inventory:
            p.unlink()
        bundle.rmdir()
        archive.unlink()
        stage.rmdir()


async def _owned(session, user, dataset_id, project_id):
    _uuid(project_id)
    owner = user.id
    dataset = (await session.execute(select(ObservationDataset).where(
        ObservationDataset.id == dataset_id, ObservationDataset.owner_id == owner,
        ObservationDataset.project_id == project_id))).scalar_one_or_none()
    if dataset is None:
        _bad("not_found", 404)
    project = (await session.execute(select(Project).where(Project.id == dataset.project_id, Project.owner_id == owner))).scalar_one_or_none()
    asset = (await session.execute(select(RawAsset).where(RawAsset.id == dataset.raw_asset_id,
        RawAsset.owner_id == owner, RawAsset.project_id == dataset.project_id))).scalar_one_or_none()
    if project is None or asset is None:
        _bad("not_found", 404)
    source = (await session.execute(select(SourceRecord).where(SourceRecord.id == asset.source_id,
        SourceRecord.owner_id == owner, SourceRecord.project_id == dataset.project_id))).scalar_one_or_none()
    if source is None:
        _bad("not_found", 404)
    _source(asset, source, str(owner), dataset.project_id)
    return dataset, asset, source


def _dataset(settings, dataset, asset, source):
    key = dataset_key(str(dataset.owner_id), dataset.project_id, dataset.id)
    if dataset.storage_key != key:
        _bad()
    raw = _read(checked_derived_path(settings, key), maximum=16 * 1024**2)
    if len(raw) != dataset.byte_count or hashlib.sha256(raw).hexdigest() != dataset.sha256:
        _bad()
    payload = json.loads(raw)
    if canonical_bytes(payload) != raw:
        _bad()
    request = validate_magnetic_dataset(payload, dataset)
    validate_physical_record(request, asset)
    if (payload["source_record_id"] != source.id or asset.sha256 != dataset.raw_sha256
            or asset.byte_count != payload["parent_raw_bytes"]
            or payload["rights_decision"] != source.rights_decision
            or payload["private_storage_permission"] != source.private_storage_permission):
        _bad()
    from app.database import checked_storage_path
    if asset.storage_key != f"projects/{asset.owner_id}/{asset.project_id}/{asset.id}":
        _bad()
    original = _read(checked_storage_path(settings, asset.storage_key))
    if len(original) != asset.byte_count or hashlib.sha256(original).hexdigest() != asset.sha256:
        _bad()
    from app.magnetic_contract import verify_original_columns
    verify_original_columns(original, request, asset)
    return payload, request



async def _owned_asset(session, user, asset_id, project_id):
    _uuid(project_id)
    asset = (await session.execute(select(RawAsset).where(RawAsset.id == asset_id,
        RawAsset.owner_id == user.id, RawAsset.project_id == project_id))).scalar_one_or_none()
    if asset is None:
        _bad("not_found", 404)
    project = (await session.execute(select(Project).where(Project.id == project_id,
        Project.owner_id == user.id))).scalar_one_or_none()
    source = (await session.execute(select(SourceRecord).where(SourceRecord.id == asset.source_id,
        SourceRecord.project_id == project_id, SourceRecord.owner_id == user.id))).scalar_one_or_none()
    if source is None or project is None:
        _bad("not_found", 404)
    _source(asset, source, str(user.id), project_id)
    return asset, source


def _parse_owned_original(settings, asset, source, request_raw, dataset_id):
    from app.database import checked_storage_path
    if asset.storage_key != f"projects/{asset.owner_id}/{asset.project_id}/{asset.id}":
        _bad()
    original = _read(checked_storage_path(settings, asset.storage_key))
    return parse_magnetic_dataset(request_raw, original, dataset_id=dataset_id,
        owner_id=str(asset.owner_id), project_id=asset.project_id, asset=asset, source=source)


async def _install_charged_dataset(session, settings, user, asset_id, request_raw, *, project_id, owner, cancelled):
    from app.magnetic_custody_owner import bounded_work, LIFETIME
    from app.magnetic_line_survey_models import SurveyDatasetAttempt
    from app.magnetic_contract import MODALITY
    asset, source = await _owned_asset(session, user, asset_id, project_id)
    for item in (asset, source):
        session.expunge(item)
    await session.rollback()
    timeout = min(120, settings.worker_wall_seconds)
    payload = await bounded_work(_parse_owned_original, settings, asset, source, request_raw, str(uuid4()), timeout=timeout)
    previous = (await session.execute(select(ObservationDataset).where(
        ObservationDataset.raw_asset_id == asset.id,
        ObservationDataset.parser_version == payload["parser_version"]))).scalar_one_or_none()
    if previous is not None:
        if previous.owner_id != user.id or previous.project_id != project_id:
            _bad("not_found", 404)
        session.expunge(previous)
        await session.rollback()
        old, _ = await bounded_work(_dataset, settings, previous, asset, source, timeout=timeout)
        if old["request_utf8"].encode() != request_raw or cancelled.is_set():
            _bad("magnetic_custody_interrupted")
        return previous
    await session.rollback()
    body = canonical_bytes(payload)
    if not 0 < len(body) <= 16*1024**2:
        _bad("magnetic_dataset_capacity_refused", 413)
    dataset = ObservationDataset(id=payload["dataset_id"], owner_id=user.id, project_id=project_id,
        raw_asset_id=asset.id, version=1, parser_version=payload["parser_version"], modality=MODALITY,
        row_count=payload["dimensions"]["row"], raw_sha256=asset.sha256,
        sha256=hashlib.sha256(body).hexdigest(), byte_count=len(body),
        storage_key=dataset_key(str(user.id), project_id, payload["dataset_id"]))
    snapshot = _sources(dataset, asset, source)
    if cancelled.is_set():
        raise asyncio.CancelledError()
    attempt = await owner.reserve(session, settings, user, dataset, operation="dataset", sources=snapshot)
    identifier = attempt.id
    files = owner.physical.leases.files
    try:
        await session.execute(text("BEGIN IMMEDIATE"))
        current_asset, current_source = await _owned_asset(session, user, asset_id, project_id)
        if _sources(dataset, current_asset, current_source) != snapshot:
            _bad("magnetic_custody_debt")
        row = await session.get(SurveyDatasetAttempt, identifier)
        row.state = "publication_uncertain"
        row.inventory = [dict(kind="dataset", id=dataset.id, relative_path=f"datasets/{dataset.id}.json",
                              byte_count=len(body), sha256=dataset.sha256)]
        await session.commit()
        if cancelled.is_set():
            raise asyncio.CancelledError()
        for key in ("derived", f"derived/{user.id}", f"derived/{user.id}/{project_id}", f"derived/{user.id}/{project_id}/datasets"):
            files.create_directory(key, exist_ok=True)
            files.private_directory_identity(key)
        await bounded_work(lambda: files.write_new(dataset.storage_key, body, cap=16*1024**2), timeout=timeout)
        if cancelled.is_set():
            raise asyncio.CancelledError()
        await session.execute(text("BEGIN IMMEDIATE"))
        current_asset, current_source = await _owned_asset(session, user, asset_id, project_id)
        if _sources(dataset, current_asset, current_source) != snapshot:
            _bad("magnetic_custody_debt")
        row = await session.get(SurveyDatasetAttempt, identifier)
        if row.state != "publication_uncertain":
            _bad("magnetic_custody_debt")
        session.add(dataset)
        await session.flush()
        row.state = "published"
        row.dataset_id = dataset.id
        row.inventory = []
        row.retained_bytes = 0
        row.lifetime = dict(schema=LIFETIME, work_completed=True, scratch_removed=True, native_admission=False)
        row.finished_at = utcnow()
        await session.commit()
        return dataset
    except BaseException as error:
        await _record_debt(session, identifier, error)
        raise


async def install_dataset(session, settings, user, asset_id, request_raw, *, project_id):
    """Fresh owned worker session; caller auth/unrelated transaction is untouched."""
    from app.magnetic_custody_owner import owner_for, drain
    owner = owner_for(session)
    owner.physical.leases.require_held()
    cancelled = asyncio.Event()

    async def run():
        if owner.sessions is None:
            _bad("magnetic_custody_session_binding")
        async with owner.sessions() as work_session, owner.lifetime(work_session, settings):
            return await _install_charged_dataset(work_session, settings, user, asset_id, request_raw,
                project_id=project_id, owner=owner, cancelled=cancelled)

    pending = asyncio.create_task(run())
    try:
        return await asyncio.shield(pending)
    except asyncio.CancelledError:
        cancelled.set()
        try:
            await drain(pending)
        except BaseException:
            pass
        raise


def _sources(dataset, asset, source):
    return dict(dataset_id=dataset.id, dataset_sha256=dataset.sha256,
        raw_asset_id=asset.id, raw_sha256=asset.sha256, raw_bytes=asset.byte_count,
        source_record_id=source.id, physical_metadata_sha256=hashlib.sha256(canonical_bytes(asset.physical_metadata)).hexdigest(),
        rights_decision=source.rights_decision,
        private_storage_permission=source.private_storage_permission)


def _prepare_replay(generation, request, stage, binding):
    from magnetic_result_bundle import read_bundle
    from magnetic_result_export import export_zip
    from magnetic_result_view import project_result
    from magnetic_local_paths import external_path
    imported = read_bundle(external_path(generation))
    if canonical_bytes(imported["request"]) != canonical_bytes(request):
        _bad("magnetic_request_mismatch")
    archive = stage / "source.zip"
    export_zip(generation, archive)
    raw = _read(archive)
    binding = {**binding, "generation_sha256": imported["generation_sha256"]}
    with _generation(raw, stage, stage_name="check") as (bundle, checked):
        if checked != imported:
            _bad()
        view = project_result(bundle, binding)
    return raw, imported, view, binding


def _finish_stage(stage, raw):
    # Only the exact reverified copy and empty checked directory are removed.
    if set(stage.iterdir()) != {stage / "source.zip"} or _read(stage / "source.zip") != raw:
        _bad("magnetic_custody_debt")
    (stage / "source.zip").unlink()
    stage.rmdir()


async def _record_debt(session, attempt_id, error):
    from app.magnetic_line_survey_models import SurveyDatasetAttempt
    await session.rollback()
    await session.execute(text("BEGIN IMMEDIATE"))
    row = await session.get(SurveyDatasetAttempt, attempt_id)
    if row is None:
        _bad("magnetic_custody_debt")
    if row.state != "published":
        row.state = "publication_uncertain" if row.state == "publication_uncertain" else "failed"
        # No inferred zero from an inaccessible/unknown/partial namespace.
        row.retained_bytes = row.reservation_bytes
        row.error_code = error.code if isinstance(error, ApiError) else "magnetic_custody_interrupted"
        row.lifetime = dict(schema="magnetic-owned-custody-incomplete-1", work_completed=True, scratch_removed=False, native_admission=False)
        row.finished_at = utcnow()
        await session.commit()


async def _install_charged_replay(session, settings, user, dataset_id, generation, *, project_id, cancelled, owner):
    from app.magnetic_custody_owner import bounded_work, LIFETIME
    from app.magnetic_line_survey_models import SurveyDatasetAttempt
    if session.in_transaction():
        _bad("magnetic_transaction_active")
    dataset, asset, source = await _owned(session, user, dataset_id, project_id)
    snapshot = _sources(dataset, asset, source)
    for item in (dataset, asset, source):
        session.expunge(item)
    await session.rollback()
    timeout = min(120, settings.worker_wall_seconds)
    # Read-only complete source validation is outside the writer transaction.
    payload, request = await bounded_work(_dataset, settings, dataset, asset, source, timeout=timeout)
    if cancelled.is_set():
        raise asyncio.CancelledError()
    job_id = str(uuid4())
    attempt = await owner.reserve(session, settings, user, dataset, operation="import", sources=snapshot, job_id=job_id)
    attempt_id = attempt.id
    files = owner.physical.leases.files
    stage_key = attempt.input_json["stage_key"]
    stage = settings.data_dir / stage_key
    try:
        owner.require(session, settings)
        files.create_directory(".magnetic-custody", exist_ok=True)
        files.private_directory_identity(".magnetic-custody")
        files.create_directory(stage_key)
        files.private_directory_identity(stage_key)
        binding = dict(job_id=job_id, dataset_id=dataset.id, source_id=payload["survey_source_id"],
            configuration_sha256=payload["geometry_plan"]["identity"]["configuration_sha256"], original_sha256=asset.sha256)
        raw, imported, view, binding = await bounded_work(_prepare_replay, generation, request, stage, binding, timeout=timeout)
        if cancelled.is_set():
            raise asyncio.CancelledError()
        request_json = dict(schema="magnetic-owned-replay-request-1", dataset_id=dataset.id,
            dataset_sha256=dataset.sha256, method_id=LOCAL_MAGNETIC_METHOD_ID,
            parameters={k: (payload["request_sha256"] if k == "request_sha256" else binding[k]) for k in PARAMETER_KEYS})
        job = ProcessingJob(id=job_id, owner_id=user.id, project_id=dataset.project_id,
            dataset_id=dataset.id, dataset_sha256=dataset.sha256, method_id=LOCAL_MAGNETIC_METHOD_ID,
            request_json=request_json, request_sha256=hashlib.sha256(canonical_bytes(request_json)).hexdigest(),
            preflight=dict(schema="magnetic-owned-replay-custody-1", magnetic_binding=binding,
                source_record_id=source.id, request_sha256=payload["request_sha256"], online_admitted=False),
            state="succeeded", cancel_requested=False, finished_at=utcnow(),
            result_key=zip_result_key(str(user.id), dataset.project_id, job_id),
            result_sha256=hashlib.sha256(raw).hexdigest(), result_bytes=len(raw))
        validate_owned_magnetic_result(view, user=user, job=job, dataset=dataset, expected_binding=binding)
        await session.execute(text("BEGIN IMMEDIATE"))
        fresh, current_asset, current_source = await _owned(session, user, dataset_id, project_id)
        if _sources(fresh, current_asset, current_source) != snapshot:
            _bad("magnetic_custody_debt")
        row = await session.get(SurveyDatasetAttempt, attempt_id)
        row.state = "publication_uncertain"
        # Save exact permanent target identity BEFORE exclusive creation.
        row.inventory = [dict(kind="magnetic_result", id=job_id, relative_path=f"results/{job_id}.zip",
                              byte_count=len(raw), sha256=job.result_sha256)]
        await session.commit()
        if cancelled.is_set():
            raise asyncio.CancelledError()
        for key in ("derived", f"derived/{user.id}", f"derived/{user.id}/{project_id}", f"derived/{user.id}/{project_id}/results"):
            files.create_directory(key, exist_ok=True)
            files.private_directory_identity(key)
        await bounded_work(lambda: files.write_new(job.result_key, raw, cap=MAX_ZIP), timeout=timeout)
        await bounded_work(_finish_stage, stage, raw, timeout=timeout)
        if cancelled.is_set():
            raise asyncio.CancelledError()
        await session.execute(text("BEGIN IMMEDIATE"))
        fresh, current_asset, current_source = await _owned(session, user, dataset_id, project_id)
        if _sources(fresh, current_asset, current_source) != snapshot:
            _bad("magnetic_custody_debt")
        row = await session.get(SurveyDatasetAttempt, attempt_id)
        if row.state != "publication_uncertain":
            _bad("magnetic_custody_debt")
        session.add(job)
        await session.flush()
        row.state = "published"
        row.inventory = []
        row.retained_bytes = 0
        row.lifetime = dict(schema=LIFETIME, work_completed=True, scratch_removed=True, native_admission=False)
        row.finished_at = utcnow()
        await session.commit()
        return job
    except BaseException as error:
        # All synchronous work has actually completed before this path runs.
        await _record_debt(session, attempt_id, error)
        raise


async def install_replay(session, settings, user, dataset_id, generation, *, project_id, temp_root):
    """Reserved local custody under existing owner guards; never an online fit."""
    from app.magnetic_custody_owner import owner_for, drain
    owner = owner_for(session)
    owner.physical.leases.require_held()
    if temp_root != settings.data_dir / ".magnetic-custody":
        _bad("magnetic_custody_root_binding")
    cancelled = asyncio.Event()

    async def run():
        if owner.sessions is None:
            _bad("magnetic_custody_session_binding")
        async with owner.sessions() as work_session, owner.lifetime(work_session, settings):
            return await _install_charged_replay(work_session, settings, user, dataset_id, generation,
                project_id=project_id, cancelled=cancelled, owner=owner)

    pending = asyncio.create_task(run())
    try:
        return await asyncio.shield(pending)
    except asyncio.CancelledError:
        cancelled.set()
        try:
            await drain(pending)
        except BaseException:
            pass
        raise


async def read_dataset(session, settings, user, dataset_id, *, project_id):
    """Public owned lexical input read; no numerical inverse or native child."""
    return await _read_input(session, settings, user, dataset_id, project_id=project_id)


async def read_method(session, settings, user, dataset_id, *, project_id):
    """Current source mapping only after the entire owned input is reverified."""
    return await _read_input(session, settings, user, dataset_id, project_id=project_id, method=True)


async def _read_input(session, settings, user, dataset_id, *, project_id, method=False):
    from app.magnetic_custody_owner import owner_for, drain, bounded_work
    from app.magnetic_contract import method_mapping
    owner = owner_for(session)
    owner.physical.leases.require_held()

    async def run():
        if owner.sessions is None:
            _bad("magnetic_custody_session_binding")
        async with owner.sessions() as work_session, owner.lifetime(work_session, settings):
            dataset, asset, source = await _owned(work_session, user, dataset_id, project_id)
            snapshot = _sources(dataset, asset, source)
            for item in (dataset, asset, source):
                work_session.expunge(item)
            await work_session.rollback()
            timeout = min(120, settings.worker_wall_seconds)
            payload, _ = await bounded_work(_dataset, settings, dataset, asset, source, timeout=timeout)
            result = await bounded_work(method_mapping, payload, dataset, timeout=timeout) if method else payload
            fresh, current_asset, current_source = await _owned(work_session, user, dataset_id, project_id)
            if _sources(fresh, current_asset, current_source) != snapshot:
                _bad("magnetic_custody_debt")
            return result

    pending = asyncio.create_task(run())
    try:
        return await asyncio.shield(pending)
    except asyncio.CancelledError:
        try:
            await drain(pending)
        except BaseException:
            pass
        raise


async def _read_charged_replay(session, settings, user, job_id, *, project_id, owner, cancelled, export=False):
    from app.magnetic_custody_owner import bounded_work, LIFETIME
    from app.magnetic_line_survey_models import SurveyDatasetAttempt
    if session.in_transaction():
        _bad("magnetic_transaction_active")
    timeout = min(120, settings.worker_wall_seconds)
    _uuid(project_id)
    job = (await session.execute(select(ProcessingJob).where(
        ProcessingJob.id == job_id, ProcessingJob.owner_id == user.id,
        ProcessingJob.project_id == project_id))).scalar_one_or_none()
    if job is None:
        _bad("not_found", 404)
    dataset, asset, source = await _owned(session, user, job.dataset_id, project_id)
    snapshot = _sources(dataset, asset, source)
    for item in (job, dataset, asset, source):
        session.expunge(item)
    await session.rollback()
    payload, request = await bounded_work(_dataset, settings, dataset, asset, source, timeout=timeout)
    req, preflight = job.request_json, job.preflight
    if (job.state != "succeeded" or job.method_id != LOCAL_MAGNETIC_METHOD_ID or job.cancel_requested
            or job.dataset_sha256 != dataset.sha256 or job.project_id != dataset.project_id
            or type(req) is not dict or set(req) != REQUEST_KEYS or req["schema"] != "magnetic-owned-replay-request-1"
            or type(req["parameters"]) is not dict or set(req["parameters"]) != PARAMETER_KEYS
            or req["dataset_id"] != dataset.id or req["dataset_sha256"] != dataset.sha256
            or req["method_id"] != LOCAL_MAGNETIC_METHOD_ID
            or hashlib.sha256(canonical_bytes(req)).hexdigest() != job.request_sha256
            or type(preflight) is not dict or set(preflight) != {"schema", "magnetic_binding", "source_record_id", "request_sha256", "online_admitted"}
            or preflight["schema"] != "magnetic-owned-replay-custody-1" or preflight["online_admitted"] is not False
            or preflight["source_record_id"] != source.id or preflight["request_sha256"] != payload["request_sha256"]
            or req["parameters"]["request_sha256"] != payload["request_sha256"]):
        _bad()
    binding = preflight["magnetic_binding"]
    key = zip_result_key(str(user.id), dataset.project_id, job.id)
    if job.result_key != key:
        _bad()
    raw = await bounded_work(_read, zip_result_path(settings, key), timeout=timeout)
    if len(raw) != job.result_bytes or hashlib.sha256(raw).hexdigest() != job.result_sha256:
        _bad()

    if cancelled.is_set():
        raise asyncio.CancelledError()
    attempt = await owner.reserve(session, settings, user, dataset,
        operation="export" if export else "read", sources=snapshot, job_id=job.id)
    identifier, stage_key = attempt.id, attempt.input_json["stage_key"]
    files = owner.physical.leases.files
    stage = settings.data_dir / stage_key
    try:
        files.create_directory(".magnetic-custody", exist_ok=True)
        files.private_directory_identity(".magnetic-custody")
        files.create_directory(stage_key)
        files.private_directory_identity(stage_key)
        view = await bounded_work(_project_checked, raw, stage, request, binding, req, user, job, dataset, timeout=timeout)
        if cancelled.is_set():
            raise asyncio.CancelledError()
        files.verify_directory(stage_key, expected_files=[])
        stage.rmdir()
        await session.execute(text("BEGIN IMMEDIATE"))
        fresh, current_asset, current_source = await _owned(session, user, dataset.id, project_id)
        if _sources(fresh, current_asset, current_source) != snapshot:
            _bad("magnetic_custody_debt")
        current_job = await session.get(ProcessingJob, job.id)
        if (current_job.state, current_job.result_sha256, current_job.result_bytes, current_job.request_sha256,
                current_job.cancel_requested, current_job.preflight) != (
                job.state, job.result_sha256, job.result_bytes, job.request_sha256, job.cancel_requested, job.preflight):
            _bad("magnetic_custody_debt")
        row = await session.get(SurveyDatasetAttempt, identifier)
        row.state = "published"
        row.lifetime = dict(schema=LIFETIME, work_completed=True, scratch_removed=True, native_admission=False)
        row.finished_at = utcnow()
        await session.commit()
        return raw if export else view
    except BaseException as error:
        await _record_debt(session, identifier, error)
        raise


def _project_checked(raw, stage, request, binding, req, user, job, dataset):
    with _generation(raw, stage, stage_name="check") as (bundle, imported):
        if (canonical_bytes(imported["request"]) != canonical_bytes(request)
                or imported["generation_sha256"] != binding.get("generation_sha256")
                or req["parameters"]["generation_sha256"] != binding.get("generation_sha256")
                or req["parameters"]["configuration_sha256"] != binding.get("configuration_sha256")):
            _bad()
        from magnetic_result_view import project_result
        view = project_result(bundle, binding)
        validate_owned_magnetic_result(view, user=user, job=job, dataset=dataset, expected_binding=binding)
    return view


async def read_replay(session, settings, user, job_id, *, project_id, temp_root, export=False):
    from app.magnetic_custody_owner import owner_for, drain
    owner = owner_for(session)
    owner.physical.leases.require_held()
    if temp_root != settings.data_dir / ".magnetic-custody":
        _bad("magnetic_custody_root_binding")
    cancelled = asyncio.Event()

    async def run():
        if owner.sessions is None:
            _bad("magnetic_custody_session_binding")
        async with owner.sessions() as work_session, owner.lifetime(work_session, settings):
            return await _read_charged_replay(work_session, settings, user, job_id,
                project_id=project_id, owner=owner, cancelled=cancelled, export=export)

    pending = asyncio.create_task(run())
    try:
        return await asyncio.shield(pending)
    except asyncio.CancelledError:
        cancelled.set()
        try:
            await drain(pending)
        except BaseException:
            pass
        raise


def exact_zip_inventory(settings, job):
    """Deletion/restart dispatcher seam AFTER full owned read_replay validation."""
    key = zip_result_key(str(job.owner_id), job.project_id, job.id)
    if job.state != "succeeded" or job.method_id != LOCAL_MAGNETIC_METHOD_ID or job.result_key != key:
        _bad()
    raw = _read(zip_result_path(settings, key))
    if len(raw) != job.result_bytes or hashlib.sha256(raw).hexdigest() != job.result_sha256:
        _bad()
    return {"kind": "magnetic_result", "id": job.id, "relative_path": f"results/{job.id}.zip",
            "byte_count": len(raw), "sha256": job.result_sha256}
