"""Owner-scoped projects, immutable uploaded originals, export and deletion."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
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
from app.models import AccountUsage, DeletionReceipt, Project, RawAsset, SourceRecord, User, utcnow
from app.schemas import ProjectCreate, ProjectUpdate, RawUploadInput


def _project_json(project: Project) -> dict:
    return {
        "id": project.id, "name": project.name, "description": project.description,
        "created_at": project.created_at.isoformat(), "updated_at": project.updated_at.isoformat(),
    }


def _source_json(source: SourceRecord) -> dict:
    return {
        "source_id": source.id, "original_filename": source.original_filename, "version": source.version,
        "provider": source.provider, "exact_url": source.exact_url,
        "doi": source.doi, "citation": source.citation, "retrieved_at": source.retrieved_at.isoformat(),
        "rights_statement": source.rights_statement, "rights_decision": source.rights_decision,
        "declared_format": source.declared_format, "expected_bytes": source.expected_bytes,
        "sha256": source.sha256, "attribution": source.attribution,
    }


def _asset_json(asset: RawAsset, source: SourceRecord) -> dict:
    return {
        "asset_id": asset.id, "project_id": asset.project_id, "source": _source_json(source),
        "filename": asset.filename, "mime": asset.client_mime, "detected_format": asset.detected_format,
        "byte_count": asset.byte_count, "sha256": asset.sha256, "physical_metadata": asset.physical_metadata,
        "validation_status": asset.validation_status, "created_at": asset.created_at.isoformat(),
        "download_url": f"/api/projects/{asset.project_id}/assets/{asset.id}/download",
    }


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


def _parse_upload_header(raw: str | None) -> RawUploadInput:
    if raw is None or len(raw.encode("utf-8")) > 16384:
        raise ApiError(422, "metadata_invalid", "X-Asset-Metadata must be JSON under 16 KiB", ["X-Asset-Metadata"])
    try:
        def nonfinite(_constant: str):
            raise ValueError("non-finite JSON number")

        value = json.loads(raw, parse_constant=nonfinite)
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
    path = checked_storage_path(settings, asset.storage_key)
    if not path.is_file() or path.stat().st_size != asset.byte_count or _sha256(path) != asset.sha256:
        raise ApiError(409, "raw_integrity_failed", "Stored original differs from its upload receipt")
    return path


def _make_export(path: Path, project: dict, rows: list[tuple[dict, Path]]) -> None:
    manifest = {"schema_version": 1, "project": project, "raw_assets": []}
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
        for asset, source in rows:
            member = f"raw/{asset['asset_id']}/{asset['filename']}"
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

    @router.get("/{project_id}/assets")
    async def list_assets(project_id: str, user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
        await _owned_project(session, project_id, user)
        rows = (await session.execute(
            select(RawAsset, SourceRecord).join(SourceRecord, RawAsset.source_id == SourceRecord.id).where(
                RawAsset.project_id == project_id, RawAsset.owner_id == user.id,
            ).order_by(RawAsset.created_at)
        )).all()
        return {"assets": [_asset_json(asset, source) for asset, source in rows]}

    @router.get("/{project_id}/assets/{asset_id}")
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

    @router.post("/{project_id}/assets", status_code=201)
    async def upload_asset(
        project_id: str, request: Request, user: User = Depends(current_user), session: AsyncSession = Depends(get_session),
    ):
        await _owned_project(session, project_id, user)
        meta = _parse_upload_header(request.headers.get("x-asset-metadata"))
        validate_declared_metadata(meta)
        if meta.source.rights_decision != "mirror":
            raise ApiError(422, "rights_not_mirrorable", "Private raw storage requires a mirror rights decision", ["source.rights_decision"])
        if request.headers.get("content-type", "").split(";", 1)[0].strip() != meta.mime:
            raise ApiError(415, "mime_format_mismatch", "Content-Type and declared MIME must agree")
        byte_limit = min(settings.max_upload_bytes, FORMAT_MAX_BYTES[meta.format])
        length = request.headers.get("content-length")
        if length and (not length.isdigit() or int(length) > byte_limit):
            raise ApiError(413, "upload_too_large", "Raw upload exceeds the byte limit")
        stage_dir = settings.data_dir / ".staging"
        stage_dir.mkdir(parents=True, exist_ok=True)
        stage = stage_dir / f"{uuid.uuid4()}.part"
        moved: Path | None = None
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
            if current + byte_count > settings.account_quota_bytes:
                raise ApiError(507, "account_quota_exceeded", "Account raw-byte quota exceeded")
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
                rights_decision=meta.source.rights_decision, declared_format=meta.format,
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
            await session.commit()
            committed = True
            return _asset_json(asset, source)
        finally:
            if not committed:
                await session.rollback()
                if moved is not None:
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
        hashes = [item.sha256 for item in assets]
        used = sum(item.byte_count for item in assets)
        project_dir = settings.data_dir / "projects" / str(user.id) / project_id
        deleting_dir = settings.data_dir / ".deleting" / f"{user.id}--{project_id}"
        deleting_dir.parent.mkdir(parents=True, exist_ok=True)
        if deleting_dir.exists():
            raise RuntimeError("project deletion recovery directory already exists")
        renamed = False
        try:
            if project_dir.exists():
                await asyncio.to_thread(project_dir.rename, deleting_dir)
                renamed = True
            await session.execute(delete(RawAsset).where(RawAsset.project_id == project_id, RawAsset.owner_id == user.id))
            await session.execute(delete(SourceRecord).where(SourceRecord.project_id == project_id, SourceRecord.owner_id == user.id))
            await session.execute(delete(Project).where(Project.id == project_id, Project.owner_id == user.id))
            usage = (await session.execute(select(AccountUsage).where(AccountUsage.user_id == user.id))).scalar_one_or_none()
            if usage is not None:
                usage.raw_bytes -= used
                if usage.raw_bytes < 0:
                    raise RuntimeError("account quota counter is inconsistent")
            receipt = DeletionReceipt(
                id=str(uuid.uuid4()), project_id=project_id, owner_id=user.id,
                deleted_at=utcnow(), asset_hashes=hashes, backup_purge_status="external_pending",
            )
            session.add(receipt)
            await session.commit()
        except Exception:
            await session.rollback()
            if renamed and not project_dir.exists():
                deleting_dir.rename(project_dir)
            raise
        if renamed:
            await asyncio.to_thread(shutil.rmtree, deleting_dir)
        backup = settings.data_dir / ".backups" / str(user.id) / project_id
        if backup.exists():
            await asyncio.to_thread(shutil.rmtree, backup)
        return {"deleted": True, "project_id": project_id, "receipt_id": receipt.id, "external_backup_status": "pending_reconciliation"}

    app.include_router(router)
