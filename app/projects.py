"""Owner-scoped projects, immutable uploaded originals, export and deletion."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import uuid
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import ValidationError
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.database import checked_storage_path
from app.errors import ApiError
from app.formats import FORMAT_MAX_BYTES, validate_declared_metadata, validate_file_envelope
from app.models import (
    AccountUsage, DeletionReceipt, ObservationDataset, ProcessingJob,
    Project, RawAsset, SourceRecord, User, utcnow,
)
from app.processing_storage import account_derived_usage, exact_derived_project, purge_exact_derived
from app.profile_archive_delete import prepare_archive_deletion
from app.physical_project_delete import prepare_physical_project_deletion
from app.schemas import ProjectCreate, ProjectUpdate, RawUploadInput
from app.views import RawAssetListView, RawAssetView, asset_view, stored_utc


def _project_json(project: Project) -> dict:
    return {
        "id": project.id, "name": project.name, "description": project.description,
        "created_at": stored_utc(project.created_at).isoformat().replace("+00:00", "Z"),
        "updated_at": stored_utc(project.updated_at).isoformat().replace("+00:00", "Z"),
    }


def _asset_json(asset: RawAsset, source: SourceRecord) -> dict:
    return asset_view(asset, source).model_dump(mode="json")


async def _owned_project(session: AsyncSession, project_id: str, user: User) -> Project:
    project = (await session.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == user.id)
    )).scalar_one_or_none()
    if project is None:
        raise ApiError(404, "not_found", "Project not found")
    return project


async def _owned_asset(session: AsyncSession, project_id: str, asset_id: str, user: User):
    await _owned_project(session, project_id, user)
    row = (await session.execute(
        select(RawAsset, SourceRecord).join(SourceRecord, RawAsset.source_id == SourceRecord.id).where(
            RawAsset.id == asset_id, RawAsset.project_id == project_id, RawAsset.owner_id == user.id,
            SourceRecord.owner_id == user.id,
        )
    )).one_or_none()
    if row is None:
        raise ApiError(404, "not_found", "Raw asset not found")
    return row


def _parse_upload_header(raw: str | None, *, physical_enabled=False) -> RawUploadInput:
    if raw is None or len(raw.encode("utf-8")) > 16384:
        raise ApiError(422, "metadata_invalid", "X-Asset-Metadata must be JSON under 16 KiB", ["X-Asset-Metadata"])
    try:
        def nonfinite(_constant: str):
            raise ValueError("non-finite JSON number")

        value = json.loads(raw, parse_constant=nonfinite)
        if type(value) is dict and value.get('format') == 'gravity_stations_json':
            if not physical_enabled:
                raise ApiError(409, 'physical_admission_closed', 'Physical originals require the installed private participant')
            from app.physical_upload import parse_physical_upload_header
            return parse_physical_upload_header(raw)
        return RawUploadInput.model_validate(value)
    except (ValueError, ValidationError) as exc:
        if isinstance(exc, ValidationError):
            fields = [".".join(str(part) for part in item["loc"]) for item in exc.errors()]
        else:
            fields = ["X-Asset-Metadata"]
        raise ApiError(422, "metadata_invalid", "Upload metadata is invalid", fields) from exc


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verified_file(settings: Settings, asset: RawAsset) -> Path:
    if asset.storage_key != f"projects/{asset.owner_id}/{asset.project_id}/{asset.id}":
        raise ApiError(409, "raw_integrity_failed", "Stored original path disagrees with its upload receipt")
    path = checked_storage_path(settings, asset.storage_key)
    if not path.is_file() or path.stat().st_size != asset.byte_count or _sha256(path) != asset.sha256:
        raise ApiError(409, "raw_integrity_failed", "Stored original differs from its upload receipt")
    return path


def _exact_project_directory(settings: Settings, owner_id: str, project_id: str, assets: list[RawAsset]) -> Path:
    try:
        directory = checked_storage_path(settings, f"projects/{owner_id}/{project_id}/__probe__").parent
    except RuntimeError as exc:
        raise ApiError(409, "raw_state_unresolved", "Project raw storage requires operator review") from exc
    if not directory.exists():
        if assets:
            raise ApiError(409, "raw_state_unresolved", "Project raw files are missing")
        return directory
    if directory.is_symlink() or not directory.is_dir():
        raise ApiError(409, "raw_state_unresolved", "Project raw storage requires operator review")
    expected = {directory / asset.id for asset in assets}
    actual = set(directory.iterdir())
    if actual != expected or any(path.is_symlink() or not path.is_file() for path in actual):
        raise ApiError(409, "raw_state_unresolved", "Project contains unreferenced or unsafe raw bytes")
    for asset in assets:
        _verified_file(settings, asset)
    return directory


def _purge_exact_deletion_directory(directory: Path, assets: list[RawAsset]) -> None:
    expected = {directory / asset.id: asset for asset in assets}
    if set(directory.iterdir()) != set(expected):
        raise RuntimeError("private_recovery_required: deletion directory contains unknown bytes")
    for path, asset in expected.items():
        if path.is_symlink() or not path.is_file() or path.stat().st_size != asset.byte_count or _sha256(path) != asset.sha256:
            raise RuntimeError("private_recovery_required: deletion directory bytes changed")
    for path in expected:
        path.unlink()
    directory.rmdir()


def _require_supported_deletion_paths(raw_directory, derived_directory, assets, manifest, *, platform):
    """Reject unsupported rename targets before rows or original files change."""
    if platform != "nt":
        return
    paths = [raw_directory, derived_directory, *(raw_directory / asset.id for asset in assets)]
    for item in manifest:
        relative = (item["relative_path"] if item["kind"] == "waveform_artifact"
                    else f"{item['kind']}s/{item['id']}.json")
        paths.append(derived_directory / relative)
    for path in paths:
        value = str(path)
        if ("\0" in value or value.startswith(("\\\\?\\", "\\\\.\\"))
                or len(value.encode("utf-16-le")) // 2 >= 260):
            raise ApiError(503, "deletion_storage_unavailable",
                           "Project deletion destinations exceed supported storage paths; originals are unchanged")


def _require_no_project_backup(settings: Settings, owner_id: str, project_id: str) -> None:
    path = settings.data_dir / ".backups" / owner_id / project_id
    if not path.resolve(strict=False).is_relative_to(settings.data_dir.resolve()):
        raise ApiError(409, "backup_state_unresolved", "Project backup path requires operator review")
    for item in (path, path.parent, path.parent.parent):
        if item.is_symlink() or (item != path and item.exists() and not item.is_dir()):
            raise ApiError(409, "backup_state_unresolved", "Project backup path requires operator review")
    if path.exists():
        raise ApiError(409, "backup_reconciliation_required", "Project backup exists; operator reconciliation is required before deletion")


def _make_export(path: Path, project: dict, rows: list[tuple[dict, Path]]) -> None:
    manifest = {"schema_version": 1, "project": project, "raw_assets": []}
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
        for asset, source in rows:
            member = f"raw/{asset['asset_id']}/{asset['original_filename']}"
            digest = hashlib.sha256()
            count = 0
            with source.open("rb") as input_file, archive.open(member, "w", force_zip64=True) as output:
                for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
                    digest.update(chunk)
                    count += len(chunk)
                    output.write(chunk)
            if digest.hexdigest() != asset["sha256"] or count != asset["byte_count"]:
                raise ApiError(409, "raw_integrity_failed", "Stored original differs from its upload receipt")
            manifest["raw_assets"].append({**asset, "zip_member": member})
        archive.writestr("manifest.json", json.dumps(manifest, sort_keys=True, separators=(",", ":")))


def install_project_routes(app, settings: Settings, current_user, get_session) -> None:
    router = APIRouter(prefix="/api/projects", tags=["projects"])

    @router.post("", status_code=201)
    async def create_project(payload: ProjectCreate, user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
        now = utcnow()
        project = Project(
            id=str(uuid.uuid4()), owner_id=user.id, name=payload.name, description=payload.description,
            created_at=now, updated_at=now,
        )
        session.add(project)
        await session.commit()
        return _project_json(project)

    @router.get("")
    async def list_projects(user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
        projects = (await session.execute(
            select(Project).where(Project.owner_id == user.id).order_by(Project.created_at.desc())
        )).scalars().all()
        return {"projects": [_project_json(item) for item in projects]}

    @router.get("/{project_id}")
    async def get_project(project_id: str, user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
        return _project_json(await _owned_project(session, project_id, user))

    @router.patch("/{project_id}")
    async def update_project(
        project_id: str, payload: ProjectUpdate, user: User = Depends(current_user), session: AsyncSession = Depends(get_session),
    ):
        project = await _owned_project(session, project_id, user)
        if payload.name is not None:
            project.name = payload.name
        if payload.description is not None:
            project.description = payload.description
        project.updated_at = utcnow()
        await session.commit()
        return _project_json(project)

    @router.get("/{project_id}/assets", response_model=RawAssetListView)
    async def list_assets(project_id: str, user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
        await _owned_project(session, project_id, user)
        rows = (await session.execute(
            select(RawAsset, SourceRecord).join(SourceRecord, RawAsset.source_id == SourceRecord.id).where(
                RawAsset.project_id == project_id, RawAsset.owner_id == user.id,
            ).order_by(RawAsset.created_at)
        )).all()
        return {"assets": [_asset_json(asset, source) for asset, source in rows]}

    @router.get("/{project_id}/assets/{asset_id}", response_model=RawAssetView)
    async def get_asset(
        project_id: str, asset_id: str, user: User = Depends(current_user), session: AsyncSession = Depends(get_session),
    ):
        asset, source = await _owned_asset(session, project_id, asset_id, user)
        return _asset_json(asset, source)

    @router.get("/{project_id}/assets/{asset_id}/download")
    async def download_asset(
        project_id: str, asset_id: str, user: User = Depends(current_user), session: AsyncSession = Depends(get_session),
    ):
        asset, _source = await _owned_asset(session, project_id, asset_id, user)
        path = await asyncio.to_thread(_verified_file, settings, asset)
        response = FileResponse(path, media_type=asset.client_mime, filename=asset.filename)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-SHA256"] = asset.sha256
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @router.post("/{project_id}/assets", status_code=201, response_model=RawAssetView)
    async def upload_asset(
        project_id: str, request: Request, user: User = Depends(current_user), session: AsyncSession = Depends(get_session),
    ):
        await _owned_project(session, project_id, user)
        from app.physical_assembly import PhysicalAssembly
        physical = getattr(request.app.state, 'physical_assembly', None)
        meta = _parse_upload_header(request.headers.get("x-asset-metadata"),
            physical_enabled=isinstance(physical, PhysicalAssembly))
        is_physical = meta.format == 'gravity_stations_json'
        if not is_physical:
            validate_declared_metadata(meta)
        if meta.source.rights_decision == "forbidden":
            raise ApiError(422, "rights_forbidden", "Forbidden sources cannot be stored", ["source.rights_decision"])
        if request.headers.get("content-type", "").split(";", 1)[0].strip() != meta.mime:
            raise ApiError(415, "mime_format_mismatch", "Content-Type and declared MIME must agree")
        byte_limit = min(settings.max_upload_bytes, 16*1024*1024 if is_physical else FORMAT_MAX_BYTES[meta.format])
        length = request.headers.get("content-length")
        if length and (not length.isdigit() or int(length) > byte_limit):
            raise ApiError(413, "upload_too_large", "Raw upload exceeds the byte limit")
        stage_dir = settings.data_dir / ".staging"
        stage_dir.mkdir(parents=True, exist_ok=True)
        stage = stage_dir / f"{uuid.uuid4()}.part"
        moved: Path | None = None
        commit_attempted = False
        committed = False
        digest = hashlib.sha256()
        byte_count = 0
        try:
            fd = os.open(stage, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as output:
                async for chunk in request.stream():
                    byte_count += len(chunk)
                    if byte_count > byte_limit:
                        raise ApiError(413, "upload_too_large", "Raw upload exceeds the byte limit")
                    digest.update(chunk)
                    await asyncio.to_thread(output.write, chunk)
            if byte_count == 0:
                raise ApiError(422, "empty_upload", "Raw upload is empty")
            if meta.source.expected_bytes is not None and byte_count != meta.source.expected_bytes:
                raise ApiError(422, "expected_bytes_mismatch", "Uploaded byte count differs from the source declaration")
            sha = digest.hexdigest()
            if meta.source.expected_sha256 is not None and sha != meta.source.expected_sha256.lower():
                raise ApiError(422, "expected_sha256_mismatch", "Uploaded SHA-256 differs from the source declaration")
            if is_physical:
                from app.physical_upload import validate_physical_upload
                validate_physical_upload(stage, meta)
            else:
                validate_file_envelope(stage, meta)
            await session.rollback()
            await session.execute(text("BEGIN IMMEDIATE"))
            await session.refresh(user)
            await _owned_project(session, project_id, user)
            if meta.format == "miniseed":
                companion = meta.physical.geometry["stationxml_asset_id"]
                match = (await session.execute(select(RawAsset.id).where(
                    RawAsset.id == companion, RawAsset.owner_id == user.id,
                    RawAsset.project_id == project_id, RawAsset.detected_format == "stationxml",
                ))).scalar_one_or_none()
                if match is None:
                    raise ApiError(422, "stationxml_missing", "MiniSEED requires an owned StationXML asset", ["physical.geometry.stationxml_asset_id"])
            usage = (await session.execute(select(AccountUsage).where(AccountUsage.user_id == user.id))).scalar_one_or_none()
            current = usage.raw_bytes if usage else 0
            derived = await account_derived_usage(session, user.id)
            if current + derived + byte_count > settings.account_quota_bytes:
                raise ApiError(507, "account_quota_exceeded", "Account private-byte quota exceeded")
            if usage is None:
                session.add(AccountUsage(user_id=user.id, raw_bytes=byte_count))
            else:
                usage.raw_bytes += byte_count
            source_id = str(uuid.uuid4())
            asset_id = str(uuid.uuid4())
            latest = (await session.execute(select(func.max(SourceRecord.version)).where(
                SourceRecord.project_id == project_id,
                SourceRecord.owner_id == user.id,
                SourceRecord.original_filename == meta.filename,
            ))).scalar_one()
            source_version = (latest or 0) + 1
            key = f"projects/{user.id}/{project_id}/{asset_id}"
            now = utcnow()
            source = SourceRecord(
                id=source_id, project_id=project_id, owner_id=user.id, original_filename=meta.filename,
                version=source_version, provider=meta.source.provider,
                exact_url=None, doi=meta.source.doi, citation=meta.source.citation,
                retrieved_at=now, rights_statement=meta.source.rights_statement,
                rights_decision=meta.source.rights_decision,
                private_storage_permission=meta.source.private_storage_permission, declared_format=meta.format,
                expected_bytes=byte_count, sha256=sha, attribution=meta.source.attribution,
            )
            asset = RawAsset(
                id=asset_id, project_id=project_id, owner_id=user.id, source_id=source_id,
                filename=meta.filename, client_mime=meta.mime, detected_format=meta.format,
                byte_count=byte_count, sha256=sha, storage_key=key,
                physical_metadata=meta.physical.model_dump(mode="json"),
                validation_status="raw_metadata_checked", created_at=now,
            )
            session.add(source)
            await session.flush()
            session.add(asset)
            await session.flush()
            target = checked_storage_path(settings, key)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                raise RuntimeError("new asset storage key already exists")
            await asyncio.to_thread(os.replace, stage, target)
            moved = target
            commit_attempted = True
            await session.commit()
            committed = True
            return _asset_json(asset, source)
        finally:
            if not committed:
                await session.rollback()
                if moved is not None and not commit_attempted:
                    moved.unlink(missing_ok=True)
            stage.unlink(missing_ok=True)

    @router.get("/{project_id}/export")
    async def export_project(
        project_id: str, user: User = Depends(current_user), session: AsyncSession = Depends(get_session),
    ):
        project = await _owned_project(session, project_id, user)
        rows = (await session.execute(
            select(RawAsset, SourceRecord).join(SourceRecord, RawAsset.source_id == SourceRecord.id).where(
                RawAsset.project_id == project_id, RawAsset.owner_id == user.id,
            ).order_by(RawAsset.id)
        )).all()
        items = [(_asset_json(asset, source), checked_storage_path(settings, asset.storage_key)) for asset, source in rows]
        export_dir = settings.data_dir / ".exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        archive = export_dir / f"{uuid.uuid4()}.zip"
        try:
            await asyncio.to_thread(_make_export, archive, _project_json(project), items)
        except Exception:
            archive.unlink(missing_ok=True)
            raise

        async def chunks():
            try:
                with archive.open("rb") as stream:
                    while data := await asyncio.to_thread(stream.read, 1024 * 1024):
                        yield data
            finally:
                archive.unlink(missing_ok=True)

        response = StreamingResponse(chunks(), media_type="application/zip")
        response.headers["Content-Disposition"] = f'attachment; filename="project-{project_id}.zip"'
        response.headers["Cache-Control"] = "no-store"
        return response

    @router.delete("/{project_id}")
    async def delete_project(
        project_id: str, user: User = Depends(current_user), session: AsyncSession = Depends(get_session),
    ):
        await _owned_project(session, project_id, user)
        await session.rollback()
        await session.execute(text("BEGIN IMMEDIATE"))
        await session.refresh(user)
        await _owned_project(session, project_id, user)
        assets = (await session.execute(select(RawAsset).where(
            RawAsset.project_id == project_id, RawAsset.owner_id == user.id,
        ))).scalars().all()
        datasets = (await session.execute(select(ObservationDataset).where(
            ObservationDataset.project_id == project_id, ObservationDataset.owner_id == user.id,
        ))).scalars().all()
        jobs = (await session.execute(select(ProcessingJob).where(
            ProcessingJob.project_id == project_id, ProcessingJob.owner_id == user.id,
        ))).scalars().all()
        archive_entries = await prepare_archive_deletion(
            app, settings, session, str(user.id), project_id, jobs,
        )
        from app.models import WaveformResultArtifact
        waveform_artifacts=(await session.execute(select(WaveformResultArtifact).where(
            WaveformResultArtifact.job_id.in_([job.id for job in jobs])))).scalars().all()
        assets.sort(key=lambda item: item.id)
        hashes = [item.sha256 for item in assets]
        manifest = [{"asset_id": item.id, "sha256": item.sha256, "byte_count": item.byte_count} for item in assets]
        used = sum(item.byte_count for item in assets)
        project_dir = await asyncio.to_thread(_exact_project_directory, settings, str(user.id), project_id, assets)
        physical_delete,physical_plan=await prepare_physical_project_deletion(
            app,settings,session,str(user.id),project_id,archive_entries)
        if physical_plan is None:
            derived_dir, derived_manifest = await asyncio.to_thread(
                exact_derived_project, settings, str(user.id), project_id, datasets, jobs, waveform_artifacts,
            )
        else:
            inventory=physical_plan['inventory']
            derived_dir=settings.data_dir/'derived'/str(user.id)/project_id
            derived_manifest=([dict(kind='dataset',id=r['dataset_id'],sha256=r['sha256'],byte_count=r['bytes'])
                for r in inventory['datasets']]+[dict(kind='result',id=r['job_id'],sha256=r['result_sha256'],byte_count=r['result_bytes'])
                for r in inventory['jobs'] if r['state']=='succeeded']+[dict(kind='waveform_artifact',id=r['job_id'],name=r['name'],
                relative_path=f"waveforms/{r['job_id']}/{r['name']}",sha256=r['sha256'],byte_count=r['bytes'])
                for r in inventory['waveform_artifacts']])
        _require_no_project_backup(settings, str(user.id), project_id)
        deleting_dir = settings.data_dir / ".deleting" / f"{user.id}--{project_id}"
        deleting_derived = settings.data_dir / ".deleting" / f"{user.id}--{project_id}--derived"
        _require_supported_deletion_paths(deleting_dir, deleting_derived, assets, derived_manifest, platform=os.name)
        if deleting_dir.parent.is_symlink():
            raise ApiError(409, "raw_state_unresolved", "Deletion recovery path requires operator review")
        if physical_plan is None: deleting_dir.parent.mkdir(parents=True, exist_ok=True)
        if any(path.exists() or path.is_symlink() for path in (deleting_dir, deleting_derived)):
            raise ApiError(409, "raw_state_unresolved", "Project deletion recovery directory already exists")
        renamed_raw = False
        renamed_derived = False
        commit_attempted = False
        if physical_plan is not None:
            # Exact declaration survives a subsequent move/crash; original rows
            # still charge every file once. Same exclusive request owns both TXs.
            await session.commit()
            await session.execute(text('BEGIN IMMEDIATE'))
            await physical_delete.recheck(settings,session,physical_plan)
        try:
            if project_dir.exists():
                if physical_plan is None: await asyncio.to_thread(project_dir.rename, deleting_dir)
                else: await physical_delete.move(settings,physical_plan,'projects')
                renamed_raw = True
            if derived_dir.exists():
                if physical_plan is None: await asyncio.to_thread(derived_dir.rename, deleting_derived)
                else: await physical_delete.move(settings,physical_plan,'derived')
                renamed_derived = True
            if physical_plan is not None:
                await physical_delete.recheck(settings,session,physical_plan)
                from app.physical_async_sql import run_native_transaction
                await run_native_transaction(session,'retire_project_forest_relations',owner_id=str(user.id),project_id=project_id)
            from app.models import WaveformDatasetSource, WaveformResultArtifact
            await session.execute(delete(WaveformResultArtifact).where(
                WaveformResultArtifact.job_id.in_([job.id for job in jobs])))
            await session.execute(delete(WaveformDatasetSource).where(
                WaveformDatasetSource.dataset_id.in_([dataset.id for dataset in datasets])))
            await session.execute(delete(ProcessingJob).where(
                ProcessingJob.project_id == project_id, ProcessingJob.owner_id == user.id,
            ))
            if physical_plan is None:
                await session.execute(delete(ObservationDataset).where(
                    ObservationDataset.project_id == project_id, ObservationDataset.owner_id == user.id,
                ))
            else:
                # Immediate RESTRICT parent links require children before roots;
                # ordinals are family identities, not list order or count.
                for dataset in sorted(physical_plan['inventory']['datasets'],key=lambda r:r['version'],reverse=True):
                    await session.execute(delete(ObservationDataset).where(ObservationDataset.id==dataset['dataset_id'],
                        ObservationDataset.project_id==project_id,ObservationDataset.owner_id==user.id))
                await run_native_transaction(session,'retire_project_forest_families',owner_id=str(user.id),project_id=project_id)
            await session.execute(delete(RawAsset).where(RawAsset.project_id == project_id, RawAsset.owner_id == user.id))
            await session.execute(delete(SourceRecord).where(SourceRecord.project_id == project_id, SourceRecord.owner_id == user.id))
            await session.execute(delete(Project).where(Project.id == project_id, Project.owner_id == user.id))
            usage = (await session.execute(select(AccountUsage).where(AccountUsage.user_id == user.id))).scalar_one_or_none()
            if usage is not None:
                usage.raw_bytes -= used
                if usage.raw_bytes < 0:
                    raise RuntimeError("account quota counter is inconsistent")
            receipt = DeletionReceipt(
                id=physical_plan['custody']['deletion_receipt_id'] if physical_plan is not None else str(uuid.uuid4()), project_id=project_id, owner_id=user.id,
                deleted_at=utcnow(), asset_hashes=hashes, asset_manifest=manifest,
                derived_manifest=derived_manifest + archive_entries,
                backup_purge_status="not_attempted",
            )
            session.add(receipt)
            if physical_plan is not None:
                await session.flush()
                await physical_delete.transfer(settings,session,physical_plan)
            commit_attempted = True
            await session.commit()
        except BaseException:
            await session.rollback()
            if not commit_attempted:
                if renamed_derived and not derived_dir.exists():
                    if physical_plan is None: deleting_derived.rename(derived_dir)
                    else: await physical_delete.move(settings,physical_plan,'derived',reverse=True)
                if renamed_raw and not project_dir.exists():
                    if physical_plan is None: deleting_dir.rename(project_dir)
                    else: await physical_delete.move(settings,physical_plan,'projects',reverse=True)
            raise
        if physical_plan is not None:
            await physical_delete.cleanup(settings,session,physical_plan)
        else:
            if renamed_raw:
                await asyncio.to_thread(_purge_exact_deletion_directory, deleting_dir, assets)
            if renamed_derived:
                await asyncio.to_thread(purge_exact_derived, deleting_derived, derived_manifest)
        return {
            "deleted": True, "project_id": project_id, "receipt_id": receipt.id,
            "retained_profile_archives": len(archive_entries),
            "backup_erasure_status": "not_attempted",
            "external_backup_status": "not_configured" if settings.auth_mode == "local" else "pending_reconciliation",
        }

    app.include_router(router)
