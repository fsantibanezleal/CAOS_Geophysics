"""Owned worker adapter for the fixed installation-owned Linux supervisor."""
from __future__ import annotations

import asyncio
import contextlib
import json
import os
from pathlib import Path
import stat
import time

from sqlalchemy import select, text

from app.bundle import build_bundle
from app.errors import ApiError
from app.models import ObservationDataset, ProcessingJob, RawAsset, SourceRecord, utcnow
from app.processing_contract import canonical_bytes, checked_derived_path, dataset_key, result_key, sha256, validate_dataset_identity, validate_result_identity, verified_json
from app.profile_execution import attach_execution, validate_terminal
from app.profile_linux_exec import JOB_KEYS, DATA_KEYS, RAW_KEYS, ORIGIN_KEYS, installation_binding, validate_configuration, uuid
from app.projects import _verified_file

CONFIG = Path("/etc/fasl/geophysics-profile-runtime.json")
STREAM_DRAIN_SECONDS = 5


def require(value):
    if not value:
        raise ApiError(409,"profile_execution_invalid","Profile execution identity or custody is unresolved")


def identity(info):
    return info.st_dev,info.st_ino


def directory_fd(path):
    require(path.is_absolute())
    fd = os.open("/",os.O_RDONLY|os.O_DIRECTORY)
    try:
        for name in path.parts[1:]:
            child = os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def regular_at(fd,name,cap):
    member = os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
    try:
        before = os.fstat(member)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and 0 <= before.st_size <= cap)
        with os.fdopen(os.dup(member),"rb") as stream:
            raw = stream.read(cap+1)
        after = os.fstat(member)
        require(len(raw) == before.st_size and (identity(before),before.st_size,before.st_mtime_ns,before.st_ctime_ns) ==
                (identity(after),after.st_size,after.st_mtime_ns,after.st_ctime_ns))
        return raw
    finally:
        os.close(member)


def installed_command(settings,job,*,with_configuration=False):
    """Only root installation configuration chooses this privileged executable."""
    require(os.name == "posix" and settings.profile_linux_supervisor is not None)
    uuid(job.id)
    parent = directory_fd(CONFIG.parent)
    try:
        for path in (CONFIG,*CONFIG.parents):
            info = path.lstat()
            require(info.st_uid == 0 and not info.st_mode & 0o022 and not stat.S_ISLNK(info.st_mode))
        config = json.loads(regular_at(parent,CONFIG.name,65536))
    finally:
        os.close(parent)
    validate_configuration(config)
    expected = Path(config["source_root"])/"scripts/profile_linux_supervisor.py"
    require(expected == settings.profile_linux_supervisor and config["data_root"] == str(settings.data_dir)
            and settings.database_path == settings.data_dir/"api.sqlite3" and config["python"] == str(settings.profile_python))
    for path in (expected,*expected.parents):
        info = path.lstat()
        require(info.st_uid == 0 and not info.st_mode & 0o022 and not stat.S_ISLNK(info.st_mode))
    source = directory_fd(expected.parent)
    try:
        require(sha256(regular_at(source,expected.name,2*1024**2)) == config["source_hashes"]["scripts/profile_linux_supervisor.py"])
    finally:
        os.close(source)
    command = ["/usr/bin/sudo","-n","/usr/bin/python3","-I","-B",str(expected),job.id]
    return (command,config) if with_configuration else command


def relation(record,keys):
    """Exact SQL relation snapshot; UUID owners use the same canonical SQL form."""
    return {key:str(getattr(record,key)) if key == "owner_id" else getattr(record,key) for key in keys}


async def bounded_stream(stream,cap):
    chunks = bytearray()
    while True:
        block = await stream.read(4096)
        if not block:
            return bytes(chunks)
        require(len(chunks)+len(block) <= cap)
        chunks.extend(block)


async def finish_streams(readers):
    """Byte bounds alone do not bound a retained writer after launcher exit."""
    return await asyncio.wait_for(asyncio.gather(*readers),STREAM_DRAIN_SECONDS)


def eligible_publication(current,extinction_proved):
    require(current is not None and current.state == "running")
    if current.cancel_requested:
        code = "user_cancelled" if extinction_proved else "profile_extinction_unproved"
        raise ApiError(409,code,"Profile stopped before eligible result publication")


async def execute(settings,sessions,job,poll_interval):
    from app.worker import _cancel_requested, _finish_failure
    started = time.monotonic()
    stage_fd = None
    process = None
    readers = []
    reason = None
    peak = scratch = None
    stage = settings.data_dir/".job-staging"/job.id
    committed = False
    extinction_proved = False
    try:
        require(settings.profile_online_enabled)
        command,configuration = installed_command(settings,job,with_configuration=True)
        async with sessions() as session:
            dataset = (await session.execute(select(ObservationDataset).where(
                ObservationDataset.id == job.dataset_id,ObservationDataset.owner_id == job.owner_id,
                ObservationDataset.project_id == job.project_id))).scalar_one()
            asset = (await session.execute(select(RawAsset).where(RawAsset.id == dataset.raw_asset_id,
                RawAsset.owner_id == job.owner_id,RawAsset.project_id == job.project_id))).scalar_one()
            origin = (await session.execute(select(SourceRecord).where(SourceRecord.id == asset.source_id,
                SourceRecord.owner_id == job.owner_id,SourceRecord.project_id == job.project_id))).scalar_one()
        installation = installation_binding(configuration,relation(job,JOB_KEYS),relation(dataset,DATA_KEYS),
            relation(asset,RAW_KEYS),relation(origin,ORIGIN_KEYS))
        key = dataset_key(str(job.owner_id),job.project_id,job.dataset_id)
        require(dataset.storage_key == key and dataset.sha256 == job.dataset_sha256 and
                asset.sha256 == job.request_json["raw_sha256"] and asset.id == job.request_json["raw_asset_id"] and
                sha256(canonical_bytes(job.request_json)) == job.request_sha256)
        payload = verified_json(settings,key,dataset.sha256,dataset.byte_count)
        validate_dataset_identity(payload,dataset)
        _verified_file(settings,asset)
        parent = stage.parent
        require(not parent.is_symlink())
        parent.mkdir(exist_ok=True)
        stage.mkdir(mode=0o700)
        stage_fd = directory_fd(stage)
        held = identity(os.fstat(stage_fd))
        process = await asyncio.create_subprocess_exec(*command,cwd=stage,
            env={"PATH":"/usr/bin:/bin","PYTHONDONTWRITEBYTECODE":"1","PYTHONIOENCODING":"utf-8"},
            stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
        readers = [asyncio.create_task(bounded_stream(process.stdout,65536)),
                   asyncio.create_task(bounded_stream(process.stderr,8192))]
        waiting = asyncio.create_task(process.wait())
        while not waiting.done():
            if await _cancel_requested(sessions,job.id):
                reason = "user_cancelled"
            elif time.monotonic()-started > job.preflight["wall_limit_seconds"]:
                reason = "job_timeout"
            elif any(task.done() and task.exception() is not None for task in readers):
                reason = "profile_execution_invalid"
            if reason:
                process.stdin.write(b"CANCEL\n")
                with contextlib.suppress(BrokenPipeError,ConnectionResetError):
                    await process.stdin.drain()
                break
            await asyncio.sleep(min(poll_interval,.1))
        await asyncio.wait_for(asyncio.shield(waiting),40)
        stdout,stderr = await finish_streams(readers)
        receipt = json.loads(stdout)
        require(stdout == canonical_bytes(receipt)+b"\n" and identity(stage.lstat()) == held)
        stored = regular_at(stage_fd,"linux-execution.json",65536)
        require(stored == canonical_bytes(receipt))
        validate_terminal(receipt,job,dict(device=held[0],inode=held[1]),installation)
        extinction_proved = True
        if reason:
            raise ApiError(409,reason,"Profile stopped before eligible result publication")
        require(process.returncode == 0 and len(stderr) <= 8192)
        require(set(os.listdir(stage_fd)) == {"result.json","linux-stderr.txt","linux-execution.json"})
        producer = regular_at(stage_fd,"result.json",8*1024**2)
        diagnostics = regular_at(stage_fd,"linux-stderr.txt",32*1024**2)
        require(receipt["retained"]["stderr.txt"] == {"bytes":len(diagnostics),"sha256":sha256(diagnostics)})
        result = attach_execution(producer,receipt,job,dict(device=held[0],inode=held[1]),installation)
        validate_result_identity(result,job)
        encoded = canonical_bytes(result)
        build_bundle(payload,result,dataset.sha256,sha256(encoded))
        require(len(encoded) <= job.preflight["scratch_limit_bytes"])
        peak = receipt["resources"]["sampled_unit_rss_peak_bytes"]
        scratch = len(producer)+len(diagnostics)+len(stored)+len(encoded)
        require(scratch <= job.preflight["scratch_limit_bytes"])
        target_key = result_key(str(job.owner_id),job.project_id,job.id)
        target = checked_derived_path(settings,target_key)
        target.parent.mkdir(parents=True,exist_ok=True)
        target_fd = directory_fd(target.parent)
        try:
            require(identity(stage.lstat()) == held)
            fd = os.open(target.name,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600,dir_fd=target_fd)
            with os.fdopen(fd,"wb") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.fsync(target_fd)
        finally:
            os.close(target_fd)
        async with sessions() as session:
            await session.execute(text("BEGIN IMMEDIATE"))
            current = await session.get(ProcessingJob,job.id)
            eligible_publication(current,extinction_proved)
            current.state,current.result_key = "succeeded",target_key
            current.result_sha256,current.result_bytes = sha256(encoded),len(encoded)
            current.wall_ms,current.peak_rss_bytes,current.scratch_bytes = int((time.monotonic()-started)*1000),peak,scratch
            current.finished_at = utcnow()
            await session.commit()
            committed = True
        require(identity(stage.lstat()) == held and set(os.listdir(stage_fd)) == {"result.json","linux-stderr.txt","linux-execution.json"})
        for name,body in (("result.json",producer),("linux-stderr.txt",diagnostics),("linux-execution.json",stored)):
            require(regular_at(stage_fd,name,len(body)) == body)
        for name in ("result.json","linux-stderr.txt","linux-execution.json"):
            os.unlink(name,dir_fd=stage_fd)
        stage.rmdir()
    except (ApiError,OSError,ValueError,TypeError,KeyError,asyncio.TimeoutError) as error:
        if committed:
            raise RuntimeError("Profile published result preserved; exact stage recovery required") from error
        if process is not None and process.stdin is not None:
            process.stdin.close()  # Root guardian owns extinction; never signal a root PID.
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(process.wait(),40)
        code = ("profile_extinction_unproved" if process is not None and not extinction_proved else
                reason or (error.code if isinstance(error,ApiError) else "profile_execution_invalid"))
        await _finish_failure(sessions,job.id,code,"Profile execution failed; original and retained evidence preserved",
            wall_ms=int((time.monotonic()-started)*1000),peak_rss=peak,scratch_bytes=scratch)
    finally:
        if process is not None and process.stdin is not None:
            process.stdin.close()
        for reader in readers:
            if not reader.done():
                reader.cancel()
        if readers:
            await asyncio.gather(*readers,return_exceptions=True)
        if stage_fd is not None:
            os.close(stage_fd)
