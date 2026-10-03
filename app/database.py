"""Engine, migration check and private-file reconciliation."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import event, func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import Settings
from app.models import AccountUsage, DeletionReceipt, ObservationDataset, ProcessingJob, RawAsset
from app.processing_contract import (
    dataset_key, result_key,
    validate_dataset_identity, validate_result_identity, verified_json,
)


MIGRATION_HEAD = "0003_processing_jobs"


def make_engine(settings: Settings):
    engine = create_async_engine(settings.database_url, connect_args={"timeout": 30})

    @event.listens_for(engine.sync_engine, "connect")
    def sqlite_pragmas(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    return engine


async def require_migration_head(engine) -> None:
    async with engine.connect() as conn:
        try:
            revision = (await conn.execute(text("SELECT version_num FROM alembic_version"))).scalar_one_or_none()
        except Exception as exc:
            raise RuntimeError("API schema is absent; run the committed Alembic migration") from exc
    if revision != MIGRATION_HEAD:
        raise RuntimeError(f"API schema revision {revision!r} is not {MIGRATION_HEAD}")


async def reconcile_private_files(settings: Settings, sessions: async_sessionmaker) -> None:
    """Read-only startup audit: unknown private bytes require operator recovery."""
    root = settings.data_dir
    async with sessions() as session:
        await session.execute(text("BEGIN IMMEDIATE"))
        asset_rows = (await session.execute(select(
            RawAsset.id, RawAsset.owner_id, RawAsset.project_id, RawAsset.storage_key,
        ))).all()
        for asset_id, owner_id, project_id, storage_key in asset_rows:
            if storage_key != f"projects/{owner_id}/{project_id}/{asset_id}":
                raise RuntimeError("private_recovery_required: raw storage key disagrees with asset identity")
        keys = {storage_key for _asset_id, _owner_id, _project_id, storage_key in asset_rows}
        deleted = (await session.execute(select(DeletionReceipt.owner_id, DeletionReceipt.project_id))).all()
        totals = dict((await session.execute(
            select(RawAsset.owner_id, func.sum(RawAsset.byte_count)).group_by(RawAsset.owner_id)
        )).all())
        usage = dict((await session.execute(select(AccountUsage.user_id, AccountUsage.raw_bytes))).all())
        if any(usage.get(owner_id, 0) != count for owner_id, count in totals.items()):
            raise RuntimeError("private_recovery_required: account quota counter differs from stored assets")
        if any(owner_id not in totals and count != 0 for owner_id, count in usage.items()):
            raise RuntimeError("private_recovery_required: account quota counter has no matching assets")
        for name in (".staging", ".exports", ".deleting", ".job-staging"):
            directory = root / name
            if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
                raise RuntimeError(f"private_recovery_required: unexpected {name} entry")
            if directory.is_dir() and next(directory.iterdir(), None) is not None:
                raise RuntimeError(f"private_recovery_required: inspect preserved {name} bytes")
        projects_root = root / "projects"
        if projects_root.is_symlink() or (projects_root.exists() and not projects_root.is_dir()):
            raise RuntimeError("private_recovery_required: invalid projects directory")
        observed: set[str] = set()
        if projects_root.is_dir():
            for path in projects_root.rglob("*"):
                if path.is_symlink() or not (path.is_file() or path.is_dir()):
                    raise RuntimeError("private_recovery_required: unsafe project storage entry")
                if path.is_file():
                    key = path.relative_to(root).as_posix()
                    if key not in keys:
                        raise RuntimeError(f"private_recovery_required: unreferenced raw bytes: {key}")
                    observed.add(key)
        for key in keys:
            if key not in observed or not checked_storage_path(settings, key).is_file():
                raise RuntimeError(f"private_recovery_required: stored raw asset is missing: {key}")
        derived_keys: set[str] = set()
        datasets = (await session.execute(select(ObservationDataset))).scalars().all()
        for dataset in datasets:
            key = dataset_key(str(dataset.owner_id), dataset.project_id, dataset.id)
            if dataset.storage_key != key:
                raise RuntimeError("private_recovery_required: dataset key disagrees with identity")
            try:
                payload = verified_json(settings, key, dataset.sha256, dataset.byte_count)
                validate_dataset_identity(payload, dataset)
            except Exception as exc:
                raise RuntimeError("private_recovery_required: dataset bytes or schema changed") from exc
            derived_keys.add(key)
        jobs = (await session.execute(select(ProcessingJob))).scalars().all()
        for job in jobs:
            if job.state == "succeeded":
                key = result_key(str(job.owner_id), job.project_id, job.id)
                if job.result_key != key or not job.result_sha256 or job.result_bytes is None:
                    raise RuntimeError("private_recovery_required: result receipt is incomplete")
                try:
                    payload = verified_json(settings, key, job.result_sha256, job.result_bytes)
                    validate_result_identity(payload, job)
                except Exception as exc:
                    raise RuntimeError("private_recovery_required: result bytes or schema changed") from exc
                derived_keys.add(key)
            elif any(value is not None for value in (job.result_key, job.result_sha256, job.result_bytes)):
                raise RuntimeError("private_recovery_required: non-success job has result bytes")
        derived_root = root / "derived"
        if derived_root.is_symlink() or (derived_root.exists() and not derived_root.is_dir()):
            raise RuntimeError("private_recovery_required: invalid derived directory")
        derived_observed: set[str] = set()
        if derived_root.is_dir():
            for path in derived_root.rglob("*"):
                if path.is_symlink() or not (path.is_file() or path.is_dir()):
                    raise RuntimeError("private_recovery_required: unsafe derived storage entry")
                if path.is_file():
                    key = path.relative_to(root).as_posix()
                    if key not in derived_keys:
                        raise RuntimeError(f"private_recovery_required: unreferenced derivative: {key}")
                    derived_observed.add(key)
        if derived_observed != derived_keys:
            raise RuntimeError("private_recovery_required: referenced derivative is missing")
        for owner_id, project_id in deleted:
            backup = root / ".backups" / str(owner_id) / project_id
            if backup.exists() or backup.is_symlink():
                raise RuntimeError("private_recovery_required: deleted-project backup remains")
        await session.rollback()


def checked_storage_path(settings: Settings, storage_key: str) -> Path:
    parts = Path(storage_key).parts
    if len(parts) != 4 or parts[0] != "projects" or any(part in ("", ".", "..") for part in parts):
        raise RuntimeError("invalid private storage key")
    path = settings.data_dir.joinpath(*parts)
    root = settings.data_dir.resolve()
    if not path.resolve(strict=False).is_relative_to(root):
        raise RuntimeError("private storage path leaves the private root")
    for parent in (path, *path.parents):
        if parent == settings.data_dir:
            break
        if parent.is_symlink():
            raise RuntimeError("private storage path is a symlink")
    return path
