"""Single-worker, bounded child-process executor for private processing jobs."""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

import psutil
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.bundle import build_bundle
from app.config import Settings, WorkerSettings
from app.database import make_engine, reconcile_private_files, require_migration_head
from app.errors import ApiError
from app.models import ObservationDataset, ProcessingJob, RawAsset, utcnow
from app.mt_contract import M05_ID, M06_ID
from app.projects import _verified_file
from app.processing_contract import (
    METHOD_ID, canonical_bytes, checked_derived_path, dataset_key, result_key,
    sha256, validate_dataset_identity, validate_result_identity, verified_json,
)


@contextlib.contextmanager
def _worker_lock(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    lock_path = root / ".processing-worker.lock"
    if lock_path.is_symlink():
        raise RuntimeError("worker lock path is a symlink")
    with lock_path.open("a+b") as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        if os.name == "nt":
            import msvcrt
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise RuntimeError("another processing worker owns the lock") from exc
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise RuntimeError("another processing worker owns the lock") from exc
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


async def _recover_interrupted(sessions: async_sessionmaker) -> None:
    async with sessions() as session:
        await session.execute(text("BEGIN IMMEDIATE"))
        rows = (await session.execute(select(ProcessingJob).where(ProcessingJob.state == "running"))).scalars().all()
        for job in rows:
            job.state = "failed"
            job.error_code = "worker_interrupted"
            job.error_message = "Worker stopped before recording a result; inspect private staging before retry"
            job.finished_at = utcnow()
        await session.commit()


async def _claim(sessions: async_sessionmaker, worker_id: str) -> ProcessingJob | None:
    async with sessions() as session:
        await session.execute(text("BEGIN IMMEDIATE"))
        row = (await session.execute(select(ProcessingJob).where(
            ProcessingJob.state == "queued",
        ).order_by(ProcessingJob.created_at, ProcessingJob.id).limit(1))).scalar_one_or_none()
        if row is None:
            await session.rollback()
            return None
        row.state = "running"
        row.started_at = utcnow()
        row.worker_id = worker_id
        await session.commit()
        return row


async def _cancel_requested(sessions: async_sessionmaker, job_id: str) -> bool:
    async with sessions() as session:
        return bool((await session.execute(select(ProcessingJob.cancel_requested).where(
            ProcessingJob.id == job_id,
        ))).scalar_one())


def _command(job: ProcessingJob, input_path: Path, output_path: Path) -> list[str]:
    return [
        sys.executable, "-m", "app.compute", "--input", str(input_path), "--output", str(output_path),
        "--job-id", job.id, "--dataset-sha256", job.dataset_sha256,
        "--request-sha256", job.request_sha256,
        "--threshold", str(job.request_json["parameters"]["threshold"]),
        "--memory-limit", str(job.preflight["memory_limit_bytes"]),
        "--scratch-limit", str(job.preflight["scratch_limit_bytes"]),
    ]


def _mt_command(job: ProcessingJob, input_path: Path, raw_path: Path, output_path: Path,
                raw_bytes: int) -> list[str]:
    return [
        sys.executable, "-m", "app.mt_compute", "--input", str(input_path),
        "--raw", str(raw_path), "--output", str(output_path), "--job-id", job.id,
        "--dataset-sha256", job.dataset_sha256, "--request-sha256", job.request_sha256,
        "--raw-sha256", job.request_json["raw_sha256"], "--raw-bytes", str(raw_bytes),
        "--method-id", job.method_id,
        "--parameters", json.dumps(job.request_json["parameters"], sort_keys=True, separators=(",", ":")),
        "--qc-screen-sha256", job.request_json.get("qc_screen_sha256", ""),
        "--memory-limit", str(job.preflight["memory_limit_bytes"]),
        "--scratch-limit", str(job.preflight["scratch_limit_bytes"]),
    ]


def _terminate_tree(pid: int) -> None:
    try:
        root = psutil.Process(pid)
        processes = root.children(recursive=True) + [root]
    except psutil.NoSuchProcess:
        return
    for process in processes:
        with contextlib.suppress(psutil.NoSuchProcess, psutil.AccessDenied):
            process.terminate()
    _gone, alive = psutil.wait_procs(processes, timeout=2)
    for process in alive:
        with contextlib.suppress(psutil.NoSuchProcess, psutil.AccessDenied):
            process.kill()
    psutil.wait_procs(alive, timeout=2)


def _rss_tree(pid: int) -> int:
    try:
        process = psutil.Process(pid)
        members = [process, *process.children(recursive=True)]
        return sum(item.memory_info().rss for item in members if item.is_running())
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return 0


def _stage_bytes(stage: Path) -> int:
    entries = set(stage.iterdir())
    cache = stage / ".matplotlib"
    if any(item.is_symlink() or (not item.is_file() and item != cache) for item in entries):
        raise RuntimeError("unknown worker staging entry requires operator recovery")
    cached = set(cache.iterdir()) if cache in entries and cache.is_dir() else set()
    if cache in entries and not cache.is_dir() or any(item.is_symlink() or not item.is_file() for item in cached):
        raise RuntimeError("unknown worker cache entry requires operator recovery")
    return sum(item.stat().st_size for item in entries if item.is_file()) + sum(item.stat().st_size for item in cached)


def _clear_known_stage(stage: Path) -> None:
    expected = {stage / "result.json", stage / "stderr.txt"}
    snapshot = stage / "source.edi"
    cache = stage / ".matplotlib"
    entries = set(stage.iterdir())
    if (not expected <= entries or not entries <= expected | {cache, snapshot}
            or any(item.is_symlink() or not item.is_file() for item in expected | (entries & {snapshot}))):
        raise RuntimeError("unknown worker staging entry requires operator recovery")
    if cache in entries:
        if cache.is_symlink() or not cache.is_dir() or any(
            item.is_symlink() or not item.is_file() for item in cache.iterdir()
        ):
            raise RuntimeError("unknown worker cache entry requires operator recovery")
        for item in cache.iterdir():
            item.unlink()
        cache.rmdir()
    for item in expected:
        item.unlink()
    if snapshot in entries:
        snapshot.unlink()
    stage.rmdir()


async def _finish_failure(
    sessions: async_sessionmaker, job_id: str, code: str, message: str,
    *, wall_ms: int, peak_rss: int, scratch_bytes: int,
) -> None:
    async with sessions() as session:
        await session.execute(text("BEGIN IMMEDIATE"))
        job = (await session.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))).scalar_one()
        if job.state != "running":
            raise RuntimeError("job state changed while worker was executing")
        job.state = "cancelled" if code == "user_cancelled" else "failed"
        job.error_code = code
        job.error_message = message[:500]
        job.wall_ms = wall_ms
        job.peak_rss_bytes = peak_rss
        job.scratch_bytes = scratch_bytes
        job.finished_at = utcnow()
        await session.commit()


async def _execute(settings: Settings | WorkerSettings, sessions: async_sessionmaker, job: ProcessingJob, poll_interval: float) -> None:
    stage_root = settings.data_dir / ".job-staging"
    if stage_root.is_symlink():
        raise RuntimeError("worker staging root requires operator recovery")
    stage_root.mkdir(parents=True, exist_ok=True)
    stage = stage_root / job.id
    stage.mkdir()
    output = stage / "result.json"
    error_path = stage / "stderr.txt"
    input_key = dataset_key(str(job.owner_id), job.project_id, job.dataset_id)
    input_path = checked_derived_path(settings, input_key)
    started = time.monotonic()
    peak = 0
    scratch_peak = 0
    code: str | None = None
    message = ""
    process: subprocess.Popen | None = None
    try:
        if job.method_id in (M05_ID, M06_ID) and not settings.mt_online_enabled:
            raise ApiError(409, "host_admission_pending", "MT worker admission is closed")
        async with sessions() as session:
            dataset = (await session.execute(select(ObservationDataset).where(
                ObservationDataset.id == job.dataset_id, ObservationDataset.owner_id == job.owner_id,
                ObservationDataset.project_id == job.project_id,
            ))).scalar_one()
            asset = None
            if job.method_id in (M05_ID, M06_ID):
                asset = (await session.execute(select(RawAsset).where(
                    RawAsset.id == dataset.raw_asset_id, RawAsset.owner_id == job.owner_id,
                    RawAsset.project_id == job.project_id,
                ))).scalar_one_or_none()
        if dataset.sha256 != job.dataset_sha256 or dataset.storage_key != input_key:
            raise ApiError(409, "dataset_changed", "Admitted dataset identity changed")
        payload = verified_json(settings, input_key, dataset.sha256, dataset.byte_count)
        validate_dataset_identity(payload, dataset)
        if sha256(canonical_bytes(job.request_json)) != job.request_sha256 or job.method_id not in (METHOD_ID, M05_ID, M06_ID):
            raise ApiError(409, "request_changed", "Admitted request identity changed")
        raw_path = None
        if job.method_id in (M05_ID, M06_ID):
            if (asset is None or asset.id != job.request_json.get("raw_asset_id")
                    or asset.sha256 != job.request_json.get("raw_sha256")
                    or asset.sha256 != dataset.raw_sha256):
                raise ApiError(409, "raw_integrity_failed", "Admitted EDI original identity changed")
            raw_path = _verified_file(settings, asset)
        limits = job.preflight
        repo_root = Path(__file__).resolve().parents[1]
        environment = {
            "PATH": os.environ.get("PATH", ""), "PYTHONPATH": str(repo_root),
            "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8",
            "TMP": str(stage), "TEMP": str(stage), "TMPDIR": str(stage),
        }
        if os.name == "nt":
            for name in ("SYSTEMROOT", "SYSTEMDRIVE", "WINDIR", "PROGRAMDATA", "ALLUSERSPROFILE"):
                if name in os.environ:
                    environment[name] = os.environ[name]
        if raw_path is not None:
            # Scientific readers use Path.home(); keep their config/cache lookup
            # inside the per-job private staging boundary.
            environment["HOME"] = str(stage)
            environment["USERPROFILE"] = str(stage)
            environment["MPLCONFIGDIR"] = str(stage / ".matplotlib")
            for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                             "NUMEXPR_NUM_THREADS", "BLIS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
                environment[variable] = "1"
        with error_path.open("xb") as errors:
            process = subprocess.Popen(
                _command(job, input_path, output) if raw_path is None else
                _mt_command(job, input_path, raw_path, output, asset.byte_count),
                cwd=stage, env=environment,
                stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=errors,
                shell=False, start_new_session=(os.name == "posix"),
            )
            while process.poll() is None:
                peak = max(peak, _rss_tree(process.pid))
                scratch_peak = max(scratch_peak, _stage_bytes(stage))
                elapsed = time.monotonic() - started
                if await _cancel_requested(sessions, job.id):
                    code, message = "user_cancelled", "Owner cancelled processing"
                elif elapsed > limits["wall_limit_seconds"]:
                    code, message = "job_timeout", "Processing exceeded wall-time limit"
                elif peak > limits["memory_limit_bytes"]:
                    code, message = "job_memory_limit", "Processing exceeded RSS limit"
                elif scratch_peak > limits["scratch_limit_bytes"]:
                    code, message = "job_scratch_limit", "Processing exceeded scratch limit"
                if code:
                    _terminate_tree(process.pid)
                    break
                await asyncio.sleep(poll_interval)
            process.wait(timeout=5)
            if process.stdin is not None:
                process.stdin.close()
        peak = max(peak, _rss_tree(process.pid))
        scratch_peak = max(scratch_peak, _stage_bytes(stage))
        if code is None and scratch_peak > limits["scratch_limit_bytes"]:
            code, message = "job_scratch_limit", "Processing exceeded scratch limit"
        if code is None and time.monotonic() - started > limits["wall_limit_seconds"]:
            code, message = "job_timeout", "Processing exceeded wall-time limit"
        if code is None and await _cancel_requested(sessions, job.id):
            code, message = "user_cancelled", "Owner cancelled processing"
        if code is None and process.returncode != 0:
            detail = error_path.read_text(encoding="utf-8", errors="replace")[:300]
            code = "degenerate_mad_scale" if "degenerate_mad_scale" in detail else "processing_failed"
            message = detail or "Processing child exited without a result"
        if code is None and (not output.is_file() or output.is_symlink()):
            code, message = "result_missing", "Processing child produced no result"
        if code is None:
            result_bytes = output.read_bytes()
            if len(result_bytes) > limits["scratch_limit_bytes"]:
                code, message = "job_scratch_limit", "Result exceeds scratch limit"
            else:
                result = verified_json_from_bytes(result_bytes)
                validate_result_identity(result, job)
                if job.method_id == METHOD_ID:
                    import app.compute as compute
                else:
                    import app.mt_compute as compute
                if result.get("engine_sha256") != hashlib.sha256(Path(compute.__file__).read_bytes()).hexdigest():
                    raise ApiError(409, "engine_changed", "Processing engine digest differs from executed code")
                try:
                    build_bundle(payload, result, dataset.sha256, sha256(result_bytes))
                except ValueError as exc:
                    raise ApiError(409, "result_invalid", "Child result failed the typed bundle contract") from exc
                key = result_key(str(job.owner_id), job.project_id, job.id)
                target = checked_derived_path(settings, key)
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists() or target.is_symlink():
                    raise ApiError(409, "derived_state_unresolved", "Result target already exists")
                try:
                    os.link(output, target)
                except FileExistsError as exc:
                    raise ApiError(409, "derived_state_unresolved", "Result target appeared during installation") from exc
                async with sessions() as session:
                    await session.execute(text("BEGIN IMMEDIATE"))
                    current = (await session.execute(select(ProcessingJob).where(ProcessingJob.id == job.id))).scalar_one()
                    if current.cancel_requested or current.state != "running":
                        raise RuntimeError("job changed during result commit; preserve result for recovery")
                    current.state = "succeeded"
                    current.result_key = key
                    current.result_sha256 = sha256(result_bytes)
                    current.result_bytes = len(result_bytes)
                    current.wall_ms = int((time.monotonic() - started) * 1000)
                    current.peak_rss_bytes = peak
                    current.scratch_bytes = scratch_peak
                    current.finished_at = utcnow()
                    await session.commit()
        if code is not None:
            await _finish_failure(
                sessions, job.id, code, message,
                wall_ms=int((time.monotonic() - started) * 1000), peak_rss=peak,
                scratch_bytes=scratch_peak,
            )
        if not output.exists():
            output.touch(exist_ok=True)
        _clear_known_stage(stage)
    except Exception as exc:
        if process is not None and process.poll() is None:
            _terminate_tree(process.pid)
            process.wait(timeout=5)
        if isinstance(exc, ApiError):
            await _finish_failure(
                sessions, job.id, exc.code, exc.message,
                wall_ms=int((time.monotonic() - started) * 1000), peak_rss=peak,
                scratch_bytes=scratch_peak,
            )
            if not output.exists():
                output.touch(exist_ok=True)
            if not error_path.exists():
                error_path.touch(exist_ok=True)
            _clear_known_stage(stage)
        else:
            raise


def verified_json_from_bytes(raw: bytes) -> dict:
    import json
    try:
        value = json.loads(raw)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ApiError(409, "result_invalid", "Child result is not valid JSON") from exc
    if not isinstance(value, dict):
        raise ApiError(409, "result_invalid", "Child result is not a JSON object")
    try:
        canonical = canonical_bytes(value)
    except (TypeError, ValueError) as exc:
        raise ApiError(409, "result_invalid", "Child result contains invalid values") from exc
    if canonical != raw:
        raise ApiError(409, "result_invalid", "Child result is not canonical JSON")
    return value


async def run_one(settings: Settings | WorkerSettings, *, poll_interval: float = 0.05) -> str | None:
    """Process at most one job. Intended for the separate worker process and local gates."""
    with _worker_lock(settings.data_dir):
        engine = make_engine(settings)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            await require_migration_head(engine)
            await _recover_interrupted(sessions)
            await reconcile_private_files(settings, sessions)
            worker_id = f"{os.getpid()}-{uuid.uuid4()}"
            job = await _claim(sessions, worker_id)
            if job is None:
                return None
            await _execute(settings, sessions, job, poll_interval)
            return job.id
        finally:
            await engine.dispose()


async def run_forever(settings: Settings | WorkerSettings, *, poll_interval: float = 0.5) -> None:
    """Hold the singleton lock and audit once, then claim work without rescanning bytes."""
    with _worker_lock(settings.data_dir):
        engine = make_engine(settings)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            await require_migration_head(engine)
            await _recover_interrupted(sessions)
            await reconcile_private_files(settings, sessions)
            worker_id = f"{os.getpid()}-{uuid.uuid4()}"
            while True:
                job = await _claim(sessions, worker_id)
                if job is None:
                    await asyncio.sleep(poll_interval)
                else:
                    await _execute(settings, sessions, job, min(poll_interval, 0.1))
        finally:
            await engine.dispose()


def main() -> None:
    settings = WorkerSettings.from_env()
    asyncio.run(run_forever(settings))


if __name__ == "__main__":
    main()
