"""Fixed nonroot installed waveform client and closed historical receipt checks."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
import stat
import time

from scripts.waveform_m08_installation import (
    canonical, decode, directory_fd, installation_binding,
    installed_argv, installed_cwd, installed_environment, read_installation,
    require, sha, uuid, validate_installation_binding,
)

from app.waveform_linux_execution import identity, validate_terminal


def installed_snapshot(settings):
    require(os.name == "posix" and os.getuid() == os.geteuid() != 0)
    config = read_installation(complete=False)
    require(config["uid"] == os.geteuid() and config["gid"] == os.getegid() and
            Path(config["data_root"]) == settings.data_dir and settings.database_path == settings.data_dir/"api.sqlite3")
    from app.waveform_contract import implementation_sha256
    require(implementation_sha256() == sha(canonical(config["source_hashes"])))
    return config


async def _capture(stream, cap, first=None):
    data = bytearray()
    emitted = False
    failure = None
    while True:
        part = await stream.read(4096)
        if not part:
            if first is not None and not emitted and not first.done():
                first.set_exception(ValueError("waveform_terminal_unproved"))
            if failure is not None:
                raise failure
            return bytes(data)
        if failure is None:
            try:
                require(len(data)+len(part) <= cap)
                data.extend(part)
                if first is not None and not emitted and not first.done() and b"\n" in data:
                    raw = bytes(data).split(b"\n",1)[0]
                    receipt = decode(raw,65536)
                    require(raw == canonical(receipt))
                    first.set_result(receipt)
                    emitted = True
            except (ValueError,TypeError):
                failure = ValueError("waveform_terminal_unproved")
                if first is not None and not first.done():
                    first.set_exception(failure)
        # Refused bytes remain bounded; still consume the held pipe until EOF.


async def drain_owned_helper(spawn, readers):
    try:
        process = await spawn
    except Exception:
        return  # Creation failed without returning an owned Process handle.
    if process.stdin is not None:
        process.stdin.close()
    if not readers:
        readers.extend((asyncio.create_task(_capture(process.stdout,65544)),
                        asyncio.create_task(_capture(process.stderr,65536))))
    while True:
        try:
            await process.wait()
        except Exception:
            # Uncertain reap retains the caller's authority. No numeric PID or
            # root signal, second timeout escape or fabricated extinction.
            await asyncio.sleep(.05)
            continue
        if process.returncode is not None:
            break
        await asyncio.sleep(.05)
    await asyncio.gather(*readers,return_exceptions=True)
    for stream in (process.stdout,process.stderr):
        while not stream.at_eof():
            try:
                await stream.read(4096)
            except Exception:
                # No EOF evidence: retain the exact actor/lease, not success.
                await asyncio.sleep(.05)


async def mandatory_helper_drain(spawn, readers):
    guard = asyncio.create_task(drain_owned_helper(spawn,readers))
    cancelled = False
    while True:
        try:
            await asyncio.shield(guard)
            return cancelled
        except asyncio.CancelledError:
            cancelled = True


async def finish_streams(readers):
    _,pending = await asyncio.wait(readers,timeout=5)
    if pending:
        raise asyncio.TimeoutError("waveform_stream_debt")
    return [reader.result() for reader in readers]


from app.waveform_stage import cleanup_stage, verify_stage


def failure_code(error, requested, terminal, proved):
    """Only already validated terminals authorize a known stopped classification."""
    from app.errors import ApiError
    if not proved:
        return "waveform_execution_unproved"
    if requested and terminal["lifecycle"]["caller"]["reason"] == "cancelled":
        return requested
    if isinstance(error,ApiError):
        if terminal["outcome"].get("reason") == "measured":
            # A post-science DB cancel can stop installation without claiming
            # that science itself was interrupted or synthesizing native timing.
            return error.code
        if error.code == "waveform_processing_failed":
            return error.code
    return "waveform_execution_unproved"


def terminal_proved(terminal,job,stage_fd,installation):
    """Resource ApiError is a refused receipt, never a running-job escape."""
    from app.errors import ApiError
    if terminal is None:
        return False
    try:
        validate_terminal(terminal,job,identity(stage_fd),installation)
    except (ApiError,ValueError,OSError,KeyError,TypeError):
        return False
    return True


async def execute(settings,sessions,job,poll_interval):
    """No root PID signals. Only closed CANCEL/EOF and posttransaction COMMIT."""
    from app.errors import ApiError
    from app.worker import _cancel_requested,_finish_failure
    from app.waveform_result import publish_result
    from app.processing_contract import canonical_bytes
    from app.models import ProcessingJob
    began = time.monotonic()
    process = spawn = None
    drains = []
    parent_fd = stage_fd = None
    requested = None
    terminal = None
    try:
        try:
            config = installed_snapshot(settings)
        except (OSError,ValueError,TypeError,KeyError):
            raise ApiError(409,"waveform_context_unavailable","Fixed nonroot waveform installation is absent or changed") from None
        require(sha(canonical_bytes(job.request_json)) == job.request_sha256 and job.method_id == "seismic.waveform-qc-classical/v1")
        uuid(job.id)
        installation = installation_binding(config,job.id)
        if await _cancel_requested(sessions,job.id):
            raise ApiError(409,"user_cancelled","Waveform publication cancelled before native launch")
        stage_root = settings.data_dir/".job-staging"
        stage_root.mkdir(mode=0o700,exist_ok=True)
        parent_fd = directory_fd(stage_root)
        os.mkdir(job.id,0o700,dir_fd=parent_fd)
        stage_fd = os.open(job.id,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=parent_fd)
        require(os.fstat(stage_fd).st_uid == config["uid"] and stat.S_IMODE(os.fstat(stage_fd).st_mode) == 0o700)
        held = identity(stage_fd)
        spawn = asyncio.create_task(asyncio.create_subprocess_exec(*installed_argv(config,job.id),cwd=installed_cwd(config),
            env=installed_environment(config),stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE))
        process = await asyncio.shield(spawn)
        first = asyncio.get_running_loop().create_future()
        drains = [asyncio.create_task(_capture(process.stdout,65544,first)),
                  asyncio.create_task(_capture(process.stderr,65536))]
        while not first.done():
            for drain in drains:
                if drain.done():
                    drain.result()
            if requested is None:
                if await _cancel_requested(sessions,job.id):
                    requested = "user_cancelled"
                elif time.monotonic()-began > job.preflight["wall_limit_seconds"]:
                    requested = "job_timeout"
                if requested:
                    process.stdin.write(b"CANCEL\n")
                    await process.stdin.drain()
            if time.monotonic()-began > job.preflight["wall_limit_seconds"]+22:
                raise ValueError("waveform_terminal_unproved")
            await asyncio.sleep(min(poll_interval,.05))
        terminal = first.result()
        validate_terminal(terminal,job,held,installation)
        require(identity(stage_fd) == held)
        if terminal["outcome"].get("reason") != "measured":
            reason = requested if requested and terminal["lifecycle"]["caller"]["reason"] == "cancelled" else "waveform_processing_failed"
            raise ApiError(409,reason,"Waveform stopped with proved source-bound terminal extinction")
        verify_stage(stage_fd,held,terminal)
        fresh = installed_snapshot(settings)
        validate_installation_binding(installation_binding(fresh,job.id),checked=installation)
        await publish_result(settings,sessions,job,stage_root/job.id/"export",terminal["native"]["eligibility"],
                             terminal["native"]["release"],linux_execution=terminal,linux_installation=installation,
                             linux_stage_fd=stage_fd)
        # COMMIT follows successful ordinary SQL publication, never a native result flag.
        process.stdin.write(b"COMMIT\n")
        await process.stdin.drain()
        process.stdin.close()
        await asyncio.wait_for(asyncio.shield(asyncio.create_task(process.wait())),5)
        stdout,stderr = await finish_streams(drains)
        require(process.returncode == 0 and stdout == canonical(terminal)+b"\nCLEAN\n" and not stderr)
        async with sessions() as session:
            current = await session.get(ProcessingJob,job.id)
            require(current.state == "succeeded")
            from app.processing_contract import verified_json
            from app.waveform_result import result_directory
            payload = verified_json(settings,current.result_key,current.result_sha256,current.result_bytes)
            await result_directory(session,settings,current,payload)
        cleanup_stage(parent_fd,stage_fd,job.id,terminal)
    except (ApiError,OSError,ValueError,KeyError,TypeError,asyncio.TimeoutError) as error:
        if process is not None and process.stdin is not None:
            process.stdin.close()  # Independent guardian owns caller-loss extinction.
        proved = terminal_proved(terminal,job,stage_fd,installation)
        async with sessions() as session:
            current = await session.get(ProcessingJob,job.id)
            if current.state != "running":
                # Publication may have committed. Preserve state/stage for exact recovery.
                raise RuntimeError("Waveform publication/custody requires exact recovery") from None
        code = error.code if process is None and isinstance(error,ApiError) else failure_code(error,requested,terminal,proved)
        await _finish_failure(sessions,job.id,code,"Waveform stage retained; eligible publication unavailable",
                              wall_ms=int((time.monotonic()-began)*1000),peak_rss=None,scratch_bytes=None)
    finally:
        cancelled = False
        try:
            if spawn is not None:
                cancelled = await mandatory_helper_drain(spawn,drains)
        finally:
            for fd in (stage_fd,parent_fd):
                if fd is not None:
                    os.close(fd)
        if cancelled:
            raise asyncio.CancelledError()
