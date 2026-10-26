"""Method-scoped candidate M11 worker using the pinned workflow CLI.

Run this worker instead of the general worker for the isolated candidate
deployment. It only claims M11 rows and publishes exact workflow files.
"""
from __future__ import annotations

import asyncio
import os
import shutil
import signal
import sys
import time
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app import physical_joint_dataset_contract as dataset_contract
from app import physical_joint_native_contract as native
from app.joint_job_routes import MEMBER_NAME, RESULT_SCHEMA, _proof
from app.joint_routes import (_ensure_parent_dirs, _registered_0006,
                              _remove_empty_dirs, _remove_new_file)
from app.models import ObservationDataset, ProcessingJob, utcnow
from app.physical_contract import byte_sha, canonical

METHOD = native.METHOD_ID
MAX_CHILD_OUTPUT = 256 * 1024


def _safe_external_root():
    value = os.environ.get("GEOPHYSICS_LOCAL_DATA_ROOT")
    if not value:
        raise RuntimeError("m11_external_data_root_unconfigured")
    return native.external_root(value)


def _workspace_root():
    root = _safe_external_root()
    base = root / "m11-candidate-jobs"
    if not base.exists():
        _mkdir_exclusive(base)
    elif base.is_symlink() or not base.is_dir() or base.lstat().st_mode & 0o077:
        raise RuntimeError("m11_workspace_root_invalid")
    with os.scandir(base) as entries:
        if sum(1 for _ in entries) >= 128:
            # Preserve interrupted inputs/results for operator review; never
            # adopt or recursively delete unknown scientific files. A finite
            # ceiling prevents unbounded recovery debris from being ignored.
            raise RuntimeError("m11_workspace_recovery_required")
    return base


def _mkdir_exclusive(path: Path):
    path.mkdir(mode=0o700, parents=False, exist_ok=False)
    info = path.lstat()
    if not path.is_dir() or path.is_symlink() or info.st_mode & 0o077:
        raise RuntimeError("m11_workspace_permissions")


async def _claim(settings, sessions, physical, worker_id):
    async with sessions() as session:
        await session.execute(text("BEGIN IMMEDIATE"))
        await _registered_0006(session)
        job = (await session.execute(select(ProcessingJob).where(
            ProcessingJob.method_id == METHOD, ProcessingJob.state == "queued",
        ).order_by(ProcessingJob.created_at, ProcessingJob.id).limit(1))).scalar_one_or_none()
        if job is None:
            await session.rollback()
            return None
        job.state = "running"
        job.started_at = utcnow()
        job.worker_id = worker_id
        await session.flush()
        await _proof(session, physical, job.owner_id, settings.account_quota_bytes)
        physical.leases.require_held()
        await session.commit()
        return job.id


async def _cancelled(sessions, job_id):
    async with sessions() as session:
        return bool((await session.execute(select(ProcessingJob.cancel_requested).where(
            ProcessingJob.id == job_id, ProcessingJob.method_id == METHOD,
        ))).scalar_one())


def _failure_member(state: str, reason: str):
    return {"api-failure.json": canonical({
        "schema": "geophysics.joint-job-failure/v1", "state": state,
        "reason": reason, "inverse_completed": False,
        "sealed_evaluation_completed": False, "scientific_acceptance": False,
        "public_activation": False,
    })}


async def _prepare_inputs(settings, sessions, physical, job_id, work: Path):
    from app.physical_joint_dataset_contract import SCHEMA
    async with sessions() as session:
        job = (await session.execute(select(ProcessingJob).where(
            ProcessingJob.id == job_id, ProcessingJob.method_id == METHOD,
        ))).scalar_one()
        dataset = (await session.execute(select(ObservationDataset).where(
            ObservationDataset.id == job.dataset_id, ObservationDataset.owner_id == job.owner_id,
            ObservationDataset.project_id == job.project_id,
        ))).scalar_one()
        files = physical.leases.files
        payload = native.bounded_json(files.read(dataset.storage_key, cap=native.MAX_JSON,
            expected_bytes=dataset.byte_count, expected_sha256=dataset.sha256))
        dataset_contract.validate_dataset(payload, dataset)
        rows = (await session.execute(text(
            "SELECT role,name,asset_id,source_id,raw_sha256,raw_bytes,source_version "
            "FROM joint_dataset_sources WHERE dataset_id=:dataset ORDER BY role,name"),
            {"dataset": dataset.id})).mappings().all()
        by_name = {(row["role"], row["name"]): row for row in rows}
        if payload.get("schema") != SCHEMA or set(by_name) != {
            (role, name) for role, members in payload["members"].items() for name in members
        }:
            raise ValueError("m11_dataset_dependency_inventory")

        development, sealed = work / "development", work / "sealed"
        _mkdir_exclusive(development)
        _mkdir_exclusive(sealed)
        copied = 0
        for role, members in payload["members"].items():
            directory = development if role == "development" else sealed
            for name, binding in members.items():
                row = by_name[role, name]
                if any(row[key] != binding[key] for key in (
                    "asset_id", "source_id", "raw_sha256", "raw_bytes", "source_version"
                )):
                    raise ValueError("m11_dataset_source_changed")
                count = int(binding["raw_bytes"])
                copied += count
                if copied > native.MAX_BYTES:
                    raise ValueError("m11_input_byte_bound")
                source_key = f"projects/{job.owner_id}/{job.project_id}/{binding['asset_id']}"
                body = files.read(source_key, cap=native.MAX_BYTES, expected_bytes=count,
                                  expected_sha256=binding["raw_sha256"])
                target = directory / name
                with target.open("xb") as stream:
                    stream.write(body)
                    stream.flush()
                    os.fsync(stream.fileno())
        return development, sealed


async def _drain_output(reader):
    data = bytearray()
    while True:
        block = await reader.read(65536)
        if not block:
            return bytes(data)
        if len(data) < MAX_CHILD_OUTPUT:
            data.extend(block[:MAX_CHILD_OUTPUT - len(data)])


async def _run_child(interpreter: Path, command: list[str], *, job_id, sessions):
    process = await asyncio.create_subprocess_exec(
        str(interpreter), *command, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL, start_new_session=True,
        env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PYTHONIOENCODING": "utf-8",
             "PYTHONDONTWRITEBYTECODE": "1", "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
             "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1"},
    )
    output_task = asyncio.create_task(_drain_output(process.stdout))
    started = time.monotonic()
    while process.returncode is None:
        try:
            await asyncio.wait_for(process.wait(), timeout=0.25)
        except TimeoutError:
            if await _cancelled(sessions, job_id):
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    await asyncio.wait_for(process.wait(), timeout=3)
                except TimeoutError:
                    os.killpg(process.pid, signal.SIGKILL)
                    await process.wait()
                break
            if time.monotonic() - started > 1810:
                os.killpg(process.pid, signal.SIGKILL)
                await process.wait()
                break
    output = await output_task
    return process.returncode, output, int((time.monotonic() - started) * 1000)


def _workflow_files(output: Path, state: str, job, *, failure_code=None):
    members = {}
    if output.is_dir() and not output.is_symlink():
        for path in sorted(output.rglob("*")):
            if path.is_symlink():
                raise ValueError("m11_output_link_forbidden")
            if not path.is_file():
                continue
            name = path.relative_to(output).as_posix()
            if MEMBER_NAME.fullmatch(name) is None:
                raise ValueError("m11_output_name_forbidden")
            size = path.stat().st_size
            if size <= 0:
                raise ValueError("m11_empty_output_member")
            members[name] = path.read_bytes()
            if sum(map(len, members.values())) > native.MAX_BYTES:
                raise ValueError("m11_output_byte_bound")
    if state == "succeeded":
        if "workflow.json" not in members:
            raise ValueError("m11_success_missing_workflow_receipt")
        receipt = native.bounded_json(members["workflow.json"])
        if receipt.get("schema") != "joint-survey-workflow-receipt-1" or receipt.get("status") != "completed" or receipt.get("inverse_completed") is not True:
            raise ValueError("m11_success_receipt_invalid")
    elif state == "cancelled":
        return _failure_member(state, failure_code or "user_cancelled")
    else:
        workflow = native.bounded_json(members["workflow.json"]) if "workflow.json" in members else None
        failure = native.bounded_json(members["failure.json"]) if "failure.json" in members else None
        if ((workflow is not None and workflow.get("status") == "completed")
                or (failure is not None and failure.get("status") != "failed")
                or (workflow is None and failure is None)):
            # A completed scientific receipt cannot be relabeled failed due to
            # a later instrument, custody or infrastructure error.
            return _failure_member(state, failure_code or "m11_terminal_validation_failed")
    if not members:
        members = _failure_member(state, failure_code or "workflow_interrupted")
    return members


async def _publish(settings, sessions, physical, job_id, state, members, *, failure_code=None,
                   wall_ms=None, peak_rss=None, scratch_bytes=None):
    files = physical.leases.files
    identity = None
    async with sessions() as session:
        await session.execute(text("BEGIN IMMEDIATE"))
        await _registered_0006(session)
        job = (await session.execute(select(ProcessingJob).where(
            ProcessingJob.id == job_id, ProcessingJob.method_id == METHOD,
        ))).scalar_one()
        if job.state != "running":
            raise RuntimeError("m11_terminal_state_changed")
        if await session.scalar(select(ProcessingJob.cancel_requested).where(ProcessingJob.id == job_id)):
            state = "cancelled"
            failure_code = "user_cancelled"
            members = _failure_member(state, failure_code)
        native_total = sum(len(value) for value in members.values())
        if not members or native_total > native.MAX_BYTES:
            raise ValueError("m11_terminal_member_bound")
        index_members = {name: {"byte_count": len(value), "sha256": byte_sha(value)}
                         for name, value in sorted(members.items())}
        index = {
            "schema": RESULT_SCHEMA, "state": state, "job_id": job.id,
            "owner_id": str(job.owner_id), "project_id": job.project_id,
            "dataset_id": job.dataset_id, "dataset_sha256": job.dataset_sha256,
            "method_id": job.method_id, "request_sha256": job.request_sha256,
            "native_bytes": native_total, "members": index_members,
            "scientific_acceptance": False, "authenticity_verified": False, "public_activation": False,
        }
        index_body = canonical(index)
        if len(index_body) > native.MAX_JSON:
            raise ValueError("m11_terminal_index_bound")
        result_key = f"derived/{job.owner_id}/{job.project_id}/results/{job.id}.json"
        writes = [(result_key, index_body, native.MAX_JSON)]
        artifact_rows = []
        for name, value in sorted(members.items()):
            key = f"derived/{job.owner_id}/{job.project_id}/joint/{job.id}/{name}"
            writes.append((key, value, native.MAX_BYTES))
            artifact_rows.append({"name": name, "storage_key": key, "byte_count": len(value),
                                 "sha256": byte_sha(value)})
        directories = []
        attempted = []
        commit_attempted = committed = False
        try:
            for key, body, cap in writes:
                directories.extend(_ensure_parent_dirs(files, key))
                try:
                    files.read(key, cap=cap)
                except FileNotFoundError:
                    attempted.append((key, cap))
                else:
                    raise FileExistsError("m11_result_target_exists")
                files.write_new(key, body, cap=cap)
            job.state = state
            job.finished_at = utcnow()
            job.result_key = result_key
            job.result_bytes = len(index_body)
            job.result_sha256 = byte_sha(index_body)
            job.wall_ms = wall_ms
            job.peak_rss_bytes = peak_rss
            job.scratch_bytes = scratch_bytes
            if state != "succeeded":
                job.error_code = failure_code or ("user_cancelled" if state == "cancelled" else "m11_workflow_failed")
                job.error_message = "M11 workflow did not complete successfully"
            for row in artifact_rows:
                await session.execute(text(
                    "INSERT INTO joint_result_artifacts "
                    "(job_id,name,owner_id,project_id,dataset_id,dataset_sha256,method_id,request_sha256,storage_key,byte_count,sha256) "
                    "VALUES (:job,:name,:owner,:project,:dataset,:dataset_sha,:method,:request_sha,:key,:bytes,:sha)"),
                    {"job": job.id, "name": row["name"], "owner": str(job.owner_id), "project": job.project_id,
                     "dataset": job.dataset_id, "dataset_sha": job.dataset_sha256, "method": METHOD,
                     "request_sha": job.request_sha256, "key": row["storage_key"], "bytes": row["byte_count"],
                     "sha": row["sha256"]})
            await session.flush()
            await _proof(session, physical, job.owner_id, settings.account_quota_bytes)
            physical.leases.require_held()
            commit_attempted = True
            await session.commit()
            committed = True
            identity = job.id
        finally:
            if not committed:
                await session.rollback()
                if not commit_attempted:
                    for key, cap in reversed(attempted):
                        _remove_new_file(files, key, cap)
                    _remove_empty_dirs(files, sorted(set(directories), key=len))
    return identity


async def _execute(settings, sessions, physical, job_id):
    execution_started = time.monotonic()
    try:
        if sys.platform != "linux":
            raise RuntimeError("m11_requires_pinned_linux_runtime")
        interpreter_value = os.environ.get("GEOPHYSICS_M11_PYTHON")
        if not interpreter_value:
            raise RuntimeError("m11_pinned_interpreter_unconfigured")
        interpreter = Path(interpreter_value)
        if not interpreter.is_absolute() or not interpreter.is_file() or interpreter.is_symlink():
            raise RuntimeError("m11_pinned_interpreter_invalid")
        root = _safe_external_root()
        base = _workspace_root()
    except Exception as error:
        failure = type(error).__name__[:70]
        members = _failure_member("failed", failure)
        await _publish(settings, sessions, physical, job_id, "failed", members, failure_code=failure,
                       wall_ms=int((time.monotonic() - execution_started) * 1000))
        return
    work = base / f"{job_id}-{uuid4()}"
    output = work / "output"
    scratch = work / "scratch"
    wall_ms = None
    peak_rss = scratch_bytes = None
    state, failure = "failed", "m11_workflow_launch_failed"
    members = None
    try:
        _mkdir_exclusive(work)
        _mkdir_exclusive(scratch)
        if await _cancelled(sessions, job_id):
            raise RuntimeError("m11_cancel_requested_before_start")
        development, sealed = await _prepare_inputs(settings, sessions, physical, job_id, work)
        repository = Path(__file__).resolve().parents[1]
        verifier = [str(repository / "scripts" / "verify_joint_linux_runtime.py")]
        code, output_bytes, _ = await _run_child(interpreter, verifier, job_id=job_id, sessions=sessions)
        if code != 0:
            raise RuntimeError("m11_runtime_pin_verification_failed")
        runtime = native.bounded_json(output_bytes.strip())
        if runtime.get("schema") != "geophysics.m11-linux-runtime-verification/v1":
            raise RuntimeError("m11_runtime_receipt_invalid")
        data_root = str(root)
        output_dir = str(output)
        scratch_dir = str(scratch)
        cli = str(repository / "scripts" / "run_joint_survey.py")
        common = ["--data-root", data_root, "--development", str(development), "--sealed", str(sealed),
                  "--output", output_dir, "--scratch-root", scratch_dir]
        code, output_bytes, _ = await _run_child(interpreter, [cli, "solve", *common],
                                                 job_id=job_id, sessions=sessions)
        if await _cancelled(sessions, job_id):
            state, failure = "cancelled", "user_cancelled"
        elif code == 0:
            validation_code, validation_bytes, _ = await _run_child(interpreter,
                [cli, "validate", *common], job_id=job_id, sessions=sessions)
            validation = native.bounded_json(validation_bytes.strip()) if validation_bytes.strip() else {}
            receipt_path = output / "workflow.json"
            receipt = native.bounded_json(receipt_path.read_bytes()) if receipt_path.is_file() else {}
            if (validation_code == 0 and validation.get("validated") is True
                    and receipt.get("status") == "completed" and receipt.get("inverse_completed") is True):
                # The browser's native result instrument is a separate,
                # post-freeze replay. It copies exact solver artifacts and
                # computes recorded state responses; it never refits.
                instrument_output = work / "instrument-output"
                instrument_cli = str(repository / "scripts" / "run_joint_instrument.py")
                instrument_common = ["--data-root", data_root, "--development", str(development),
                    "--sealed", str(sealed), "--original", output_dir,
                    "--output", str(instrument_output), "--scratch-root", scratch_dir]
                instrument_code, instrument_bytes, _ = await _run_child(
                    interpreter, [instrument_cli, "export", *instrument_common],
                    job_id=job_id, sessions=sessions)
                instrument = native.bounded_json(instrument_bytes.strip()) if instrument_bytes.strip() else {}
                instrument_validation_code, instrument_validation_bytes, _ = await _run_child(
                    interpreter, [instrument_cli, "validate", *instrument_common],
                    job_id=job_id, sessions=sessions)
                instrument_validation = (native.bounded_json(instrument_validation_bytes.strip())
                    if instrument_validation_bytes.strip() else {})
                if (instrument_code == 0 and instrument.get("validated") is True
                        and instrument.get("scientific_acceptance_verified") is False
                        and instrument_validation_code == 0
                        and instrument_validation.get("validated") is True):
                    state, failure = "succeeded", None
                    members = _workflow_files(instrument_output, state, None)
                    resource_receipts = [receipt.get("resources", {}),
                        validation.get("verification_resources", {}), instrument.get("resources", {}),
                        instrument_validation.get("resources", {})]
                    peak_values = [r.get("peak_sampled_rss_bytes") for r in resource_receipts
                                   if type(r.get("peak_sampled_rss_bytes")) is int]
                    scratch_values = [r.get("peak_sampled_scratch_bytes") for r in resource_receipts
                                      if type(r.get("peak_sampled_scratch_bytes")) is int]
                    peak_rss = max(peak_values, default=None)
                    scratch_bytes = max(scratch_values, default=None)
                else:
                    state, failure = "failed", "m11_state_instrument_validation_failed"
            else:
                state, failure = "failed", "m11_workflow_validation_failed"
        elif not (await _cancelled(sessions, job_id)):
            state, failure = "failed", "m11_workflow_nonzero_exit"
        if members is None:
            members = _workflow_files(output, state, None, failure_code=failure)
    except Exception as error:
        state, failure = ("cancelled", "user_cancelled") if await _cancelled(sessions, job_id) else ("failed", type(error).__name__[:70])
        try:
            members = _workflow_files(output, state, None, failure_code=failure)
        except Exception:
            # Preserve the terminal fact even when a partially written solver
            # member is malformed; do not strand the reservation in running.
            members = _failure_member(state, failure)
    finally:
        # Exact workspace is private to this worker; never accept a caller path.
        try:
            if work.exists() and not work.is_symlink():
                shutil.rmtree(work)
        except OSError:
            state, failure = "failed", "m11_workspace_cleanup_failed"
            members = _failure_member(state, failure)
    wall_ms = int((time.monotonic() - execution_started) * 1000)
    await _publish(settings, sessions, physical, job_id, state, members, failure_code=failure,
                   wall_ms=wall_ms, peak_rss=peak_rss, scratch_bytes=scratch_bytes)


async def run_once(settings, sessions: async_sessionmaker, physical) -> str | None:
    """Claim one M11 job and hold both participating locks through publication."""
    physical.leases.require_held()
    physical.worker.require_processing_held()
    worker_id = f"m11-{os.getpid()}-{uuid4()}"
    identifier = await _claim(settings, sessions, physical, worker_id)
    if identifier is None:
        return None
    await _execute(settings, sessions, physical, identifier)
    return identifier


async def run_forever(settings, sessions: async_sessionmaker, physical, *, poll_interval=0.5):
    if type(poll_interval) not in (int, float) or not 0 < poll_interval <= 30:
        raise ValueError("m11_worker_poll_interval")
    await physical.startup(settings, sessions)
    _workspace_root()
    while True:
        async with physical.leases.acquire():
            async with physical.worker.acquire_processing():
                identifier = await run_once(settings, sessions, physical)
        if identifier is None:
            await asyncio.sleep(poll_interval)
