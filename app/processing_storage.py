"""Exact derived-byte inventory and deletion; unknown state is never swept."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.errors import ApiError
from app.models import ObservationDataset, ProcessingJob
from app.mt_contract import M05_ID, M06_ID, M05_SCRATCH_BYTES, M06_SCRATCH_BYTES
from app.processing_contract import (
    METHOD_SCRATCH_BYTES, checked_derived_path, dataset_key, result_key, sha256,
    validate_dataset_identity, validate_result_identity, verified_json,
)


async def account_derived_usage(session: AsyncSession, owner_id) -> int:
    datasets = (await session.execute(select(func.coalesce(func.sum(ObservationDataset.byte_count), 0)).where(
        ObservationDataset.owner_id == owner_id,
    ))).scalar_one()
    results = (await session.execute(select(func.coalesce(func.sum(ProcessingJob.result_bytes), 0)).where(
        ProcessingJob.owner_id == owner_id, ProcessingJob.state == "succeeded",
    ))).scalar_one()
    active_methods = (await session.execute(select(ProcessingJob.method_id).where(
        ProcessingJob.owner_id == owner_id, ProcessingJob.state.in_(["queued", "running"]),
    ))).scalars().all()
    reservations = {M05_ID: M05_SCRATCH_BYTES, M06_ID: M06_SCRATCH_BYTES}
    return int(datasets) + int(results) + sum(
        reservations.get(method_id, METHOD_SCRATCH_BYTES) for method_id in active_methods
    )


def exact_derived_project(
    settings: Settings, owner_id: str, project_id: str,
    datasets: list[ObservationDataset], jobs: list[ProcessingJob],
) -> tuple[Path, list[dict]]:
    directory = settings.data_dir / "derived" / owner_id / project_id
    if not directory.resolve(strict=False).is_relative_to(settings.data_dir.resolve()):
        raise ApiError(409, "derived_state_unresolved", "Derived project path requires operator review")
    for path in (directory, directory.parent, directory.parent.parent):
        if path.is_symlink() or (path.exists() and not path.is_dir()):
            raise ApiError(409, "derived_state_unresolved", "Derived project path requires operator review")
    expected: dict[Path, dict] = {}
    for dataset in datasets:
        key = dataset_key(owner_id, project_id, dataset.id)
        if dataset.storage_key != key:
            raise ApiError(409, "derived_state_unresolved", "Dataset storage identity differs from receipt")
        path = checked_derived_path(settings, key)
        payload = verified_json(settings, key, dataset.sha256, dataset.byte_count)
        validate_dataset_identity(payload, dataset)
        expected[path] = {"kind": "dataset", "id": dataset.id, "sha256": dataset.sha256,
                          "byte_count": dataset.byte_count}
    for job in jobs:
        if job.state in {"queued", "running"}:
            raise ApiError(409, "project_jobs_active", "Cancel or finish active jobs before deleting the project")
        if job.state == "succeeded":
            key = result_key(owner_id, project_id, job.id)
            if job.result_key != key or job.result_sha256 is None or job.result_bytes is None:
                raise ApiError(409, "derived_state_unresolved", "Job result receipt is incomplete")
            path = checked_derived_path(settings, key)
            payload = verified_json(settings, key, job.result_sha256, job.result_bytes)
            validate_result_identity(payload, job)
            expected[path] = {"kind": "result", "id": job.id, "sha256": job.result_sha256,
                              "byte_count": job.result_bytes}
        elif any(value is not None for value in (job.result_key, job.result_sha256, job.result_bytes)):
            raise ApiError(409, "derived_state_unresolved", "Non-success job has unexpected result metadata")
    if not expected:
        if directory.exists():
            raise ApiError(409, "derived_state_unresolved", "Unreferenced derived project directory requires recovery")
        return directory, []
    if not directory.is_dir():
        raise ApiError(409, "derived_state_unresolved", "Derived project bytes are missing")
    allowed_dirs = {path.parent for path in expected}
    observed = set(directory.rglob("*"))
    if observed != set(expected) | allowed_dirs or any(path.is_symlink() for path in observed):
        raise ApiError(409, "derived_state_unresolved", "Derived project contains unknown or unsafe bytes")
    manifest = [expected[path] for path in sorted(expected)]
    return directory, manifest


def purge_exact_derived(directory: Path, manifest: list[dict]) -> None:
    expected = {directory / f"{item['kind'] + 's'}/{item['id']}.json": item for item in manifest}
    allowed_dirs = {path.parent for path in expected}
    if set(directory.rglob("*")) != set(expected) | allowed_dirs:
        raise RuntimeError("private_recovery_required: deletion directory contains unknown derivatives")
    for path, item in expected.items():
        if (path.is_symlink() or not path.is_file() or path.stat().st_size != item["byte_count"]
                or sha256(path.read_bytes()) != item["sha256"]):
            raise RuntimeError("private_recovery_required: deletion derivative changed")
    for path in expected:
        path.unlink()
    for subdirectory in allowed_dirs:
        subdirectory.rmdir()
    directory.rmdir()
