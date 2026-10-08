"""Single-worker fixed waveform supervisor dispatch; no native fallback."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

from sqlalchemy import select

from app.errors import ApiError
from app.models import ObservationDataset
from app.processing_contract import canonical_bytes, dataset_key, sha256, verified_json, validate_dataset_identity
from app.waveform_contract import INPUT, METHOD_ID, context_path, context_available, implementation_sha256
from app.waveform_processing import validate_source_rows
from app.waveform_result import publish_result


def read_context(settings):
    if not context_available(settings):
        raise ApiError(409, "waveform_context_unavailable", "Waveform native context is absent or invalid")
    value = INPUT.bounded_json(context_path(settings).read_bytes(), 65536)
    from waveform_m08_files import open_input, validate_path
    if value["platform"] == "linux":
        from waveform_m08_linux import image_sha as binary_sha
    else:
        from waveform_m08_windows import binary_sha

    python = validate_path(value["python"])
    admission = validate_path(value["admission_path"])
    if value["platform"] != ("windows" if os.name == "nt" else "linux"):
        raise ApiError(409, "waveform_context_unavailable", "Waveform native context is for another platform")
    if binary_sha(python) != value["python_sha256"]:
        raise ApiError(
            409, "waveform_context_unavailable", "Waveform interpreter differs from its selected context"
        )
    with open_input(admission, 65536) as handle:
        if hashlib.sha256(handle.read_bytes()).hexdigest() != value["admission_sha256"]:
            raise ApiError(
                409, "waveform_context_unavailable", "Waveform native admission differs from its selected context"
            )
    return value


def bind_job_context(context, stage_root, stage, job_id):
    """Derive an exact private child-parent binding from the selected root.

    This records the new directory identity; it does not grant host acceptance
    or replace any ABI, code, runtime, or review evidence in the selected record.
    """
    if context["platform"] == "linux":
        from app.waveform_linux_exec import bind_context
        return bind_context(context, stage_root, stage, job_id)
    from waveform_m08_windows import decode_control, canonical
    from waveform_m08_files import open_input, open_output, validate_path
    from copy import deepcopy

    with open_input(context["admission_path"], 65536) as handle:
        raw = handle.read_bytes()
    if sha256(raw) != context["admission_sha256"]:
        raise ApiError(409, "waveform_context_unavailable", "Selected waveform admission changed")
    value = decode_control(raw)
    if validate_path(value["parent"]["path"]) != stage_root:
        raise ApiError(409, "waveform_context_unavailable", "Selected waveform staging root differs")
    with open_output(stage_root) as root:
        if list(root.identity) != value["parent"]["identity"]:
            raise ApiError(409, "waveform_context_unavailable", "Selected waveform staging identity changed")
        with open_output(stage) as child:
            bound = deepcopy(value)
            bound["parent"] = {
                "path": str(stage), "identity": list(child.identity),
                "context_receipt_sha256": sha256(canonical({
                    "selected_admission_sha256": context["admission_sha256"], "job_id": job_id,
                    "parent_identity": list(child.identity),
                })),
            }
    path = stage / "admission.json"
    encoded = canonical(bound)
    with path.open("xb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    # The native validator performs every original ABI/code/runtime check on
    # this derivative before constructing a job or launching a child.
    return {**context, "admission_path": str(path), "admission_sha256": sha256(encoded)}


def command(context, paths):
    script = Path(__file__).resolve().parents[1] / "scripts" / "process_waveform_m08.py"
    return [
        context["python"],
        "-B",
        str(script),
        "--mseed",
        str(paths["miniseed"]),
        "--stationxml",
        str(paths["stationxml"]),
        "--request",
        str(paths["request"]),
        "--out",
        str(paths["out"]),
        "--python",
        context["python"],
        "--admission",
        context["admission_path"],
    ]


async def execute(settings, sessions, job, poll_interval):
    """Real fixed CLI/supervisor only. Preserved stages demand exact recovery."""
    from app.worker import _cancel_requested, _finish_failure

    start = time.monotonic()
    process = None
    stage = None
    try:
        if job.method_id != METHOD_ID or sha256(canonical_bytes(job.request_json)) != job.request_sha256:
            raise ApiError(409, "request_changed", "Waveform admitted request changed")
        if job.request_json.get("implementation_sha256") != implementation_sha256():
            raise ApiError(409, "waveform_engine_changed", "Waveform implementation differs from the admitted job")
        context = read_context(settings)
        async with sessions() as session:
            dataset = (
                await session.execute(
                    select(ObservationDataset).where(
                        ObservationDataset.id == job.dataset_id,
                        ObservationDataset.owner_id == job.owner_id,
                        ObservationDataset.project_id == job.project_id,
                    )
                )
            ).scalar_one()
            if dataset.sha256 != job.dataset_sha256:
                raise ApiError(409, "dataset_changed", "Waveform admitted index changed")
            payload = verified_json(
                settings,
                dataset_key(str(job.owner_id), job.project_id, job.dataset_id),
                dataset.sha256,
                dataset.byte_count,
            )
            validate_dataset_identity(payload, dataset)
            if (
                payload["sources"] != job.request_json["waveform_sources"]
                or payload["request"] != job.request_json["scientific_request"]
                or payload["scientific_request_sha256"] != job.request_json["scientific_request_sha256"]
            ):
                raise ApiError(409, "request_changed", "Waveform index/request binding changed")
            paths = await validate_source_rows(session, settings, dataset, payload)
        stage_root = settings.data_dir / ".job-staging"
        if stage_root.is_symlink():
            raise ApiError(409, "waveform_context_unavailable", "Waveform staging parent is unsafe")
        stage_root.mkdir(exist_ok=True)
        stage = stage_root / job.id
        stage.mkdir(mode=0o700)
        context = bind_job_context(context, stage_root, stage, job.id)
        raw = json.dumps(
            payload["request"], sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        ).encode("ascii")
        if len(raw) > 65536:
            raise ApiError(413, "waveform_request_invalid", "Waveform request exceeds its byte cap")
        request = stage / "request.json"
        with request.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        paths.update(request=request, out=stage / "export")
        # Admission validates this exact private parent and code/runtime before native launch.
        environment = {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONIOENCODING": "utf-8",
            "TMP": str(stage),
            "TEMP": str(stage),
            "TMPDIR": str(stage),
        }
        if os.name == "nt":
            for key in ("SYSTEMROOT", "SYSTEMDRIVE", "WINDIR"):
                if key in os.environ:
                    environment[key] = os.environ[key]
        with (stage / "stdout.json").open("xb") as out, (stage / "stderr.txt").open("xb") as err:
            process = subprocess.Popen(
                command(context, paths),
                cwd=stage,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=out,
                stderr=err,
                shell=False,
            )
            while process.poll() is None:
                reason = None
                if await _cancel_requested(sessions, job.id):
                    reason = "user_cancelled"
                elif time.monotonic() - start > job.preflight["wall_limit_seconds"]:
                    reason = "job_timeout"
                elif bounded_stage_bytes(stage) > job.preflight["scratch_limit_bytes"]:
                    reason = "job_scratch_limit"
                elif (stage / "stdout.json").stat().st_size > 65536 or (stage / "stderr.txt").stat().st_size > 65536:
                    reason = "waveform_log_limit"
                if reason:
                    # Observer owns the sole Windows job handle: its exit closes the job.
                    # Linux observer death requires its separately implemented unit binding.
                    process.kill()
                    process.wait(timeout=5)
                    raise ApiError(409, reason, "Waveform processing stopped before eligible publication")
                await asyncio.sleep(min(poll_interval, 0.05))
            process.wait(timeout=5)
        if (stage / "stdout.json").stat().st_size > 65536 or (stage / "stderr.txt").stat().st_size > 65536:
            raise ApiError(409, "waveform_log_limit", "Waveform observer log exceeds its bound")
        outcome = INPUT.bounded_json((stage / "stdout.json").read_bytes(), 65536)
        if process.returncode not in (0, 2) or outcome.get("reason") != "measured":
            raise ApiError(
                409, "waveform_processing_failed", "Waveform supervisor did not produce an eligible scientific export"
            )
        run_id = outcome.get("run_id")
        import re

        if type(run_id) is not str or re.fullmatch("[a-f0-9]{32}", run_id) is None:
            raise ApiError(409, "waveform_resource_invalid", "Waveform run identity is invalid")
        native = stage / f"export.a4-{run_id}"
        from waveform_m08_windows import decode_control
        receipt = decode_control((native / "eligibility.json").read_bytes())
        release = decode_control((native / "release.json").read_bytes())
        if (
            sha256(
                json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()
            )
            != outcome["receipt_sha256"]
        ):
            raise ApiError(409, "waveform_resource_invalid", "Waveform final receipt differs from the observer result")
        if sha256(json.dumps(release, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()) != outcome["release_sha256"]:
            raise ApiError(409, "waveform_resource_invalid", "Waveform release differs from the observer result")
        await publish_result(settings, sessions, job, stage / "export", receipt, release)
        # Successful stage custody is handled separately from publication.
        # Retain it on any ambiguous commit or unknown-file condition.
        await finalize_success_stage(settings, sessions, job, stage, receipt, release)
    except (ApiError, INPUT.WaveformInputError, OSError, KeyError, ValueError) as error:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        code = error.code if isinstance(error, ApiError) else "waveform_processing_failed"
        message = (
            error.message if isinstance(error, ApiError) else "Waveform processing failed without eligible publication"
        )
        scratch = None
        if stage is not None:
            try:
                scratch = bounded_stage_bytes(stage)
            except (ApiError, OSError):
                code = "waveform_stage_invalid"
        async with sessions() as session:
            from app.models import ProcessingJob
            current = await session.get(ProcessingJob, job.id)
            if current.state != "running":
                raise RuntimeError("Waveform terminal stage requires recovery; published state preserved") from None
        await _finish_failure(
            sessions,
            job.id,
            code,
            message,
            wall_ms=int((time.monotonic() - start) * 1000),
            peak_rss=None,
            scratch_bytes=scratch,
        )


def bounded_stage_bytes(stage):
    """Bound traversal before retaining entries; unknown/unsafe files fail closed."""
    pending = [(stage, 0)]
    count = 0
    total = 0
    while pending:
        directory, depth = pending.pop()
        # Native environment accounting permits depth 8 / 1024 entries. Include
        # the two enclosing native-stage levels and the finite export members.
        if depth > 10 or directory.is_symlink():
            raise ApiError(409, "waveform_stage_invalid", "Waveform staging inventory is unsafe")
        with os.scandir(directory) as entries:
            for entry in entries:
                count += 1
                if count > 1150 or entry.is_symlink():
                    raise ApiError(409, "waveform_stage_invalid", "Waveform staging inventory is unsafe")
                if entry.is_dir(follow_symlinks=False):
                    pending.append((Path(entry.path), depth + 1))
                elif entry.is_file(follow_symlinks=False):
                    total += entry.stat(follow_symlinks=False).st_size
                else:
                    raise ApiError(409, "waveform_stage_invalid", "Waveform staging inventory is unsafe")
    return total


async def finalize_success_stage(settings, sessions, job, stage, receipt, release):
    """Remove only a committed successful stage with a verified exact inventory."""
    from app.models import ProcessingJob, WaveformResultArtifact
    from app.processing_contract import result_key
    from app.waveform_result import local_export, verified_artifacts, checked_resources
    from waveform_m08_files import open_input

    async with sessions() as session:
        current = await session.get(ProcessingJob, job.id)
        if current.state != "succeeded":
            raise ApiError(409, "waveform_stage_invalid", "Publication is not confirmed; stage retained")
        payload = verified_json(settings, result_key(str(job.owner_id), job.project_id, job.id),
                                current.result_sha256, current.result_bytes)
        rows = (await session.execute(select(WaveformResultArtifact).where(
            WaveformResultArtifact.job_id == job.id))).scalars().all()
        verified_artifacts(settings, current, payload, rows)
        if payload["resources"] != checked_resources(receipt, release):
            raise ApiError(409, "waveform_stage_invalid", "Committed resource evidence changed")
    native = stage / ("export.a4-" + receipt["run_id"])
    if set(stage.iterdir()) != {stage / name for name in
                               ("request.json", "admission.json", "stdout.json", "stderr.txt", "export", native.name)}:
        raise ApiError(409, "waveform_stage_invalid", "Unknown success staging entry; stage retained")
    local_export(stage / "export")
    names = {p.name for p in native.iterdir()}
    linux = receipt.get("schema") in {"caos.m08-linux-resources.v1", "caos.m08-linux-resources.v2"}
    if linux:
        if names != {"eligibility.json", "release.json"}:
            raise ApiError(409, "waveform_stage_invalid", "Unknown Linux staging entry; stage retained")
    else:
        local_export(native / "science")
        from waveform_m08_windows import CONTROL_NAMES
        if not {"science", "environment", "eligibility.json", "release.json"} <= names or not names <= CONTROL_NAMES | {"science", "environment"}:
            raise ApiError(409, "waveform_stage_invalid", "Unknown native staging entry; stage retained")
    # Cache bytes belong to this exclusive cold-start profile, not user originals.
    # Accept only finite known matplotlib/Windows cold-start inventories, never
    # arbitrary cache files. Every byte is accounted and hashed below first.
    for path in (native / "environment").rglob("*"):
        rel = path.relative_to(native / "environment").as_posix()
        import re
        if path.is_dir():
            valid = rel in {"matplotlib", ".matplotlib", ".cache", ".cache/matplotlib", "Microsoft", "Microsoft/Windows",
                           "Microsoft/Windows/Caches", "system-profile", "system-profile/Microsoft", "system-profile/Microsoft/Windows",
                           "system-profile/Microsoft/Windows/Caches"}
        else:
            valid = (re.fullmatch(r"(?:matplotlib|\.matplotlib|\.cache/matplotlib)/fontlist-v[0-9]{1,3}(?:\.[0-9]{1,3}){0,2}\.json", rel) is not None
                     or rel in {"Microsoft/Windows/Caches/cversions.3.db",
                                "system-profile/Microsoft/Windows/Caches/cversions.2.db",
                                "system-profile/Microsoft/Windows/Caches/{6AF0698E-D558-4F6E-9B3C-3716689AF493}.2.ver0x0000000000000001.db",
                                "system-profile/Microsoft/Windows/Caches/{783F4448-920D-4105-B6F0-18511E85DE5B}.2.ver0x0000000000000001.db",
                                "system-profile/Microsoft/Windows/Caches/{DDF571F2-BE98-426D-8288-1A9A39C3FDA2}.2.ver0x0000000000000001.db"})
        if not valid:
            raise ApiError(409, "waveform_stage_invalid", "Unknown environment entry; stage retained")
    inventory = []
    directories = []
    bounded_stage_bytes(stage)
    for path in stage.rglob("*"):
        if path.is_symlink() or getattr(path.stat(follow_symlinks=False), "st_file_attributes", 0) & 0x400:
            raise ApiError(409, "waveform_stage_invalid", "Unsafe staging entry; stage retained")
        if path.is_dir():
            directories.append(path)
        elif path.is_file():
            size = path.stat().st_size
            if size == 0 and path != stage / "stderr.txt":
                raise ApiError(409, "waveform_stage_invalid", "Empty staging entry; stage retained")
            if size:
                with open_input(path, 16777216) as held:
                    raw = held.read_bytes()
                inventory.append((path, size, sha256(raw)))
            else:
                inventory.append((path, 0, sha256(b"")))
        else:
            raise ApiError(409, "waveform_stage_invalid", "Unsupported staging entry; stage retained")
    # Check the entire finite manifest before deleting any material entry.
    for path, size, digest in inventory:
        if path.stat().st_size != size or sha256(path.read_bytes()) != digest:
            raise ApiError(409, "waveform_stage_invalid", "Staging changed; stage retained")
    for path, _, _ in inventory:
        path.unlink()
    for directory in sorted(directories, key=lambda p: len(p.parts), reverse=True):
        directory.rmdir()
    stage.rmdir()
