"""Single-artifact owned numeric replay custody, not online magnetic execution.

Parent dispatchers call these functions after existing auth/CSRF. They never
change the service union, runtime flags or native controller themselves.
"""

from __future__ import annotations

from contextlib import contextmanager
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
from app.models import AccountUsage, ObservationDataset, ProcessingJob, Project, RawAsset, SourceRecord, utcnow
from app.processing_contract import canonical_bytes, dataset_key, checked_derived_path
from app.processing_storage import account_derived_usage

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
def _generation(raw, temp_root):
    """Fresh explicit external scratch; exact verified files only are removed."""
    science()
    from magnetic_local_paths import external_path
    from magnetic_result_export import import_zip
    root = external_path(temp_root)
    if not root.is_dir():
        _bad()
    stage = root / f"magnetic-replay-{uuid4()}"
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


async def install_dataset(session, settings, user, asset_id, request_raw, *, project_id):
    """Real immutable owned SQLite/file installation; no fitter is invoked."""
    if session.in_transaction():
        _bad("magnetic_transaction_active")
    target, created, committed_attempt = None, False, False
    body = None
    try:
        await session.execute(text("BEGIN IMMEDIATE"))
        _uuid(project_id)
        asset = (await session.execute(select(RawAsset).where(RawAsset.id == asset_id,
            RawAsset.owner_id == user.id, RawAsset.project_id == project_id))).scalar_one_or_none()
        if asset is None:
            _bad("not_found", 404)
        project = (await session.execute(select(Project).where(Project.id == asset.project_id,
            Project.owner_id == user.id))).scalar_one_or_none()
        source = (await session.execute(select(SourceRecord).where(SourceRecord.id == asset.source_id,
            SourceRecord.project_id == asset.project_id, SourceRecord.owner_id == user.id))).scalar_one_or_none()
        if source is None or project is None:
            _bad("not_found", 404)
        _source(asset, source, str(user.id), asset.project_id)
        from app.database import checked_storage_path
        if asset.storage_key != f"projects/{asset.owner_id}/{asset.project_id}/{asset.id}":
            _bad()
        original = _read(checked_storage_path(settings, asset.storage_key))
        payload = parse_magnetic_dataset(request_raw, original, dataset_id=str(uuid4()),
            owner_id=str(user.id), project_id=asset.project_id, asset=asset, source=source)
        previous = (await session.execute(select(ObservationDataset).where(
            ObservationDataset.raw_asset_id == asset.id,
            ObservationDataset.parser_version == payload["parser_version"]))).scalar_one_or_none()
        if previous is not None:
            if previous.owner_id != user.id or previous.project_id != asset.project_id:
                _bad("not_found", 404)
            old, _ = _dataset(settings, previous, asset, source)
            if old["request_utf8"].encode() != request_raw:
                _bad()
            session.expunge(previous)
            await session.rollback()
            return previous
        body = canonical_bytes(payload)
        usage = await session.get(AccountUsage, user.id)
        if usage is None or usage.raw_bytes + await account_derived_usage(session, user.id) + len(body) > settings.account_quota_bytes:
            _bad("quota_exceeded", 413)
        from app.magnetic_contract import MODALITY
        dataset = ObservationDataset(id=payload["dataset_id"], owner_id=user.id, project_id=asset.project_id,
            raw_asset_id=asset.id, version=1, parser_version=payload["parser_version"], modality=MODALITY,
            row_count=payload["dimensions"]["row"], raw_sha256=asset.sha256,
            sha256=hashlib.sha256(body).hexdigest(), byte_count=len(body),
            storage_key=dataset_key(str(user.id), asset.project_id, payload["dataset_id"]))
        target = checked_derived_path(settings, dataset.storage_key)
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        target = checked_derived_path(settings, dataset.storage_key)
        _write(target, body)
        created = True
        session.add(dataset)
        await session.flush()
        committed_attempt = True
        await session.commit()
        return dataset
    except BaseException:
        await session.rollback()
        if created and target is not None and target.exists() and not committed_attempt:
            if _read(target) == body:
                target.unlink()
            else:
                _bad("magnetic_custody_debt")
        raise


async def install_replay(session, settings, user, dataset_id, generation, *, project_id, temp_root):
    """Own fresh transaction; callers must finish any existing transaction first.

    No queued worker and no numerical inference occur. On uncertain commit retain
    the created file; startup inventory must reconcile it before service use.
    """
    if session.in_transaction():
        _bad("magnetic_transaction_active")
    target = None
    created = False
    committed_attempt = False
    raw = None
    try:
        await session.execute(text("BEGIN IMMEDIATE"))
        dataset, asset, source = await _owned(session, user, dataset_id, project_id)
        payload, request = _dataset(settings, dataset, asset, source)
        # Ownership and immutable raw/dataset custody precede numerical bundle
        # imports, generation path reads, export allocation and scratch writes.
        from magnetic_result_bundle import read_bundle
        from magnetic_result_export import export_zip
        from magnetic_local_paths import external_path
        imported = read_bundle(external_path(generation))
        temp = external_path(temp_root)
        archive = temp / f"magnetic-import-{uuid4()}.zip"
        export_zip(generation, archive)
        raw = _read(archive)
        archive.unlink()
        if canonical_bytes(imported["request"]) != canonical_bytes(request):
            _bad("magnetic_request_mismatch")
        usage = await session.get(AccountUsage, user.id)
        if usage is None:
            _bad()
        if usage.raw_bytes + await account_derived_usage(session, user.id) + len(raw) > settings.account_quota_bytes:
            _bad("quota_exceeded", 413)
        job_id = str(uuid4())
        binding = dict(job_id=job_id, dataset_id=dataset.id, source_id=payload["survey_source_id"],
            generation_sha256=imported["generation_sha256"],
            configuration_sha256=payload["geometry_plan"]["identity"]["configuration_sha256"],
            original_sha256=asset.sha256)
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
        # Verify the exact retained archive, not just the source directory that
        # was read before export. No serializer float roundtrip creates new data.
        with _generation(raw, temp) as (bundle, checked):
            if checked != imported:
                _bad()
            from magnetic_result_view import project_result
            view = project_result(bundle, binding)
            validate_owned_magnetic_result(view, user=user, job=job, dataset=dataset, expected_binding=binding)
        target = zip_result_path(settings, job.result_key)
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        target = zip_result_path(settings, job.result_key)
        _write(target, raw)
        created = True
        session.add(job)
        await session.flush()
        committed_attempt = True
        await session.commit()
        return job
    except BaseException:
        await session.rollback()
        if created and target is not None and target.exists() and not committed_attempt:
            if _read(target) == raw:
                target.unlink()
            else:
                _bad("magnetic_custody_debt")
        raise


async def read_dataset(session, settings, user, dataset_id, *, project_id):
    """Public owned lexical input read; no numerical inverse or native child."""
    dataset, asset, source = await _owned(session, user, dataset_id, project_id)
    return _dataset(settings, dataset, asset, source)[0]


async def read_method(session, settings, user, dataset_id, *, project_id):
    """Current source mapping only after the entire owned input is reverified."""
    dataset, asset, source = await _owned(session, user, dataset_id, project_id)
    payload, _ = _dataset(settings, dataset, asset, source)
    from app.magnetic_contract import method_mapping
    return method_mapping(payload, dataset)


async def read_replay(session, settings, user, job_id, *, project_id, temp_root, export=False):
    _uuid(project_id)
    job = (await session.execute(select(ProcessingJob).where(
        ProcessingJob.id == job_id, ProcessingJob.owner_id == user.id,
        ProcessingJob.project_id == project_id))).scalar_one_or_none()
    if job is None:
        _bad("not_found", 404)
    dataset, asset, source = await _owned(session, user, job.dataset_id, project_id)
    payload, request = _dataset(settings, dataset, asset, source)
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
    raw = _read(zip_result_path(settings, key))
    if len(raw) != job.result_bytes or hashlib.sha256(raw).hexdigest() != job.result_sha256:
        _bad()
    with _generation(raw, temp_root) as (bundle, imported):
        if (canonical_bytes(imported["request"]) != canonical_bytes(request)
                or imported["generation_sha256"] != binding.get("generation_sha256")
                or req["parameters"]["generation_sha256"] != binding.get("generation_sha256")
                or req["parameters"]["configuration_sha256"] != binding.get("configuration_sha256")):
            _bad()
        from magnetic_result_view import project_result
        view = project_result(bundle, binding)
        validate_owned_magnetic_result(view, user=user, job=job, dataset=dataset, expected_binding=binding)
    return raw if export else view


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
