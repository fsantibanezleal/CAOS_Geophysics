"""Explicit operator recovery of exact terminal profile evidence, never science."""
from __future__ import annotations

import asyncio
import ctypes
import json
import os
import re
import stat

from sqlalchemy import select

from app.database import make_engine, require_migration_head
from app.models import ObservationDataset, ProcessingJob, RawAsset, SourceRecord
from app.processing_contract import canonical_bytes, checked_derived_path, result_key, sha256
from app.profile_execution import KEYS, closed, validate_installation
from app.profile_linux_exec import JOB_KEYS, DATA_KEYS, RAW_KEYS, ORIGIN_KEYS, recorded_installation_binding, uuid
from app.profile_linux_worker import directory_fd, identity, installed_command, regular_at, relation, require, bounded_stream, finish_streams

ARCHIVE_CAP = 256*1024**2
STAGE_CAP = 64*1024**2
RECOVERY_KEYS = set("schema job_id receipt_sha256 intent_sha256 installation retained_stage_identity terminal known_root_copies_removed".split())
MANIFEST_KEYS = set("schema job_id request_sha256 installation stage_identity members recovery uncommitted_duplicate".split())


def rename_exclusive(source_fd,name,target_fd):
    """Same-filesystem atomic archive; an existing target is never overwritten."""
    library = ctypes.CDLL(None,use_errno=True)
    rename = library.renameat2
    rename.argtypes = [ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(source_fd,name.encode("ascii"),target_fd,name.encode("ascii"),1):
        error = ctypes.get_errno()
        raise OSError(error,os.strerror(error))


def write_exclusive(fd,name,body):
    member = os.open(name,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o400,dir_fd=fd)
    with os.fdopen(member,"wb") as stream:
        stream.write(body)
        stream.flush()
        os.fsync(stream.fileno())
    os.fsync(fd)


def validate_recovery(record,receipt,job,installation,stage_identity):
    closed(record,RECOVERY_KEYS)
    closed(receipt,KEYS)
    validate_installation(receipt,installation)
    require(record["schema"] == "geophysics.profile-linux-recovery/v1" and record["job_id"] == job.id and
            receipt["job_id"] == job.id and receipt["request_sha256"] == job.request_sha256 and
            receipt["dataset_sha256"] == job.dataset_sha256 and receipt["raw_sha256"] == job.request_json["raw_sha256"] and
            record["receipt_sha256"] == sha256(canonical_bytes(receipt)) and record["installation"] == installation and
            record["known_root_copies_removed"] is True and
            record["retained_stage_identity"] == receipt["retained_stage_identity"] == stage_identity)
    from app.profile_execution import digest
    digest(record["intent_sha256"])
    units = {"geophysics-profile-"+job.id+".service","geophysics-profile-guardian-"+job.id+".scope"}
    closed(record["terminal"],units)
    for unit,state in record["terminal"].items():
        require(type(state) is dict and set(state) in (
            {"MainPID","ActiveState","SubState","ControlGroup"},{"ActiveState","SubState","ControlGroup"}) and
            ("MainPID" in state or unit.endswith(".scope")) and state.get("MainPID","0") == "0" and
            state["ActiveState"] in ("inactive","failed") and state["SubState"] in ("dead","failed","exited") and
            state["ControlGroup"] in ("","/system.slice/"+unit))


def stage_inventory(fd,receipt):
    names = set(os.listdir(fd))
    require("linux-execution.json" in names and names <= {"result.json","linux-stderr.txt","linux-execution.json"})
    inventory = {}
    for name in names:
        cap = 65536 if name == "linux-execution.json" else 8*1024**2 if name == "result.json" else 32*1024**2
        body = regular_at(fd,name,cap)
        record = dict(bytes=len(body),sha256=sha256(body))
        if name != "linux-execution.json":
            require(record == receipt["retained"].get("result.json" if name == "result.json" else "stderr.txt"))
        inventory[name] = record
    for producer,name in (("result.json","result.json"),("stderr.txt","linux-stderr.txt")):
        if producer in receipt["retained"]:
            require(name in inventory)
    require(sum(record["bytes"] for record in inventory.values()) <= STAGE_CAP)
    return inventory


def reverify_archive(fd,manifest):
    closed(manifest,MANIFEST_KEYS)
    require(type(manifest["members"]) is dict and "linux-execution.json" in manifest["members"] and
            set(manifest["members"]) <= {"result.json","linux-stderr.txt","linux-execution.json"})
    require(set(os.listdir(fd)) == set(manifest["members"]) | {"manifest.json"})
    require(regular_at(fd,"manifest.json",262144) == canonical_bytes(manifest))
    for name,record in manifest["members"].items():
        body = regular_at(fd,name,record["bytes"])
        require(dict(bytes=len(body),sha256=sha256(body)) == record)


def archive_usage(fd):
    """Bounded flat archive census; unknown or linked evidence refuses."""
    names = os.listdir(fd)
    require(len(names) < 128)
    total = 0
    for name in names:
        match = re.fullmatch(r"([a-f0-9-]{36})(\.intent\.json)?",name)
        require(match is not None)
        uuid(match[1])
        info = os.stat(name,dir_fd=fd,follow_symlinks=False)
        require(info.st_uid == os.geteuid() and not info.st_mode & 0o077)
        if match[2]:
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and 0 < info.st_size <= 262144)
            total += info.st_size
        else:
            require(stat.S_ISDIR(info.st_mode))
            child = os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
            try:
                children = os.listdir(child)
                require(set(children) <= {"result.json","linux-stderr.txt","linux-execution.json","manifest.json"})
                for leaf in children:
                    metadata = os.stat(leaf,dir_fd=child,follow_symlinks=False)
                    require(stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1 and metadata.st_uid == os.geteuid()
                        and not metadata.st_mode & 0o077 and 0 <= metadata.st_size <= STAGE_CAP)
                    total += metadata.st_size
            finally:
                os.close(child)
        require(total <= ARCHIVE_CAP)
    return total


async def recover_job(settings,identifier):
    """Caller must hold the existing worker lock; job state is never changed."""
    require(os.name == "posix" and os.geteuid() != 0)
    uuid(identifier)
    engine,sessions = make_engine(settings)
    fds = []
    process = None
    readers = []
    try:
        await require_migration_head(engine)
        async with sessions() as session:
            job = await session.get(ProcessingJob,identifier)
            require(job is not None and job.state in ("failed","cancelled","succeeded"))
            dataset = (await session.execute(select(ObservationDataset).where(ObservationDataset.id == job.dataset_id,
                ObservationDataset.owner_id == job.owner_id,ObservationDataset.project_id == job.project_id))).scalar_one()
            raw = (await session.execute(select(RawAsset).where(RawAsset.id == dataset.raw_asset_id,
                RawAsset.owner_id == job.owner_id,RawAsset.project_id == job.project_id))).scalar_one()
            origin = (await session.execute(select(SourceRecord).where(SourceRecord.id == raw.source_id,
                SourceRecord.owner_id == job.owner_id,SourceRecord.project_id == job.project_id))).scalar_one()
        command,config = installed_command(settings,job,with_configuration=True)
        installation = recorded_installation_binding(config,relation(job,JOB_KEYS),relation(dataset,DATA_KEYS),
            relation(raw,RAW_KEYS),relation(origin,ORIGIN_KEYS))
        stage_parent = directory_fd(settings.data_dir/".job-staging")
        fds.append(stage_parent)
        archive = settings.data_dir/".profile-retained"
        require(not archive.is_symlink())
        archive.mkdir(mode=0o700,exist_ok=True)
        archive_fd = directory_fd(archive)
        fds.append(archive_fd)
        intent_name = identifier+".intent.json"
        intent_exists = intent_name in os.listdir(archive_fd)
        if intent_exists:
            manifest = json.loads(regular_at(archive_fd,intent_name,262144))
            closed(manifest,MANIFEST_KEYS)
            require(manifest["schema"] == "geophysics.profile-retained-stage/v1" and manifest["job_id"] == identifier and
                    manifest["installation"] == installation and manifest["request_sha256"] == job.request_sha256)
        if identifier in os.listdir(stage_parent):
            stage_fd = os.open(identifier,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=stage_parent)
            fds.append(stage_fd)
            info = os.fstat(stage_fd)
            held = dict(device=info.st_dev,inode=info.st_ino)
            receipt_bytes = regular_at(stage_fd,"linux-execution.json",65536)
            receipt = json.loads(receipt_bytes)
            require(receipt_bytes == canonical_bytes(receipt))
            inventory = stage_inventory(stage_fd,receipt) if not intent_exists else manifest["members"]
            if intent_exists:
                require(held == manifest["stage_identity"])
        else:
            require(intent_exists and identifier in os.listdir(archive_fd))
            stage_fd = os.open(identifier,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=archive_fd)
            fds.append(stage_fd)
            reverify_archive(stage_fd,manifest)
            held = manifest["stage_identity"]
            receipt = json.loads(regular_at(stage_fd,"linux-execution.json",65536))
            inventory = manifest["members"]
        process = await asyncio.create_subprocess_exec(*command[:-1],"--recover",identifier,
            stdin=asyncio.subprocess.DEVNULL,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,
            env={"PATH":"/usr/bin:/bin","PYTHONDONTWRITEBYTECODE":"1","PYTHONIOENCODING":"utf-8"})
        readers = [asyncio.create_task(bounded_stream(process.stdout,65536)),asyncio.create_task(bounded_stream(process.stderr,8192))]
        await asyncio.wait_for(process.wait(),45)
        stdout,_ = await finish_streams(readers)
        require(process.returncode == 0)
        recovery = json.loads(stdout)
        require(stdout == canonical_bytes(recovery)+b"\n")
        validate_recovery(recovery,receipt,job,installation,held)
        target = checked_derived_path(settings,result_key(str(job.owner_id),job.project_id,identifier))
        duplicate = None
        duplicate_present = False
        if job.state != "succeeded" and target.exists():
            target_fd = directory_fd(target.parent)
            fds.append(target_fd)
            body = regular_at(target_fd,target.name,8*1024**2)
            producer = regular_at(stage_fd,"result.json",8*1024**2)
            result = json.loads(producer)
            result.update(linux_execution=receipt,linux_installation=installation)
            require(body == canonical_bytes(result) and job.result_key is None)
            duplicate = dict(bytes=len(body),sha256=sha256(body),name=target.name)
            duplicate_present = True
        elif job.state == "succeeded":
            require(target.exists() and job.result_key == result_key(str(job.owner_id),job.project_id,identifier))
            target_fd = directory_fd(target.parent)
            fds.append(target_fd)
            published = regular_at(target_fd,target.name,8*1024**2)
            require(len(published) == job.result_bytes and sha256(published) == job.result_sha256)
        if intent_exists and not duplicate_present and job.state != "succeeded":
            duplicate = manifest["uncommitted_duplicate"]
        if not intent_exists:
            usage = archive_usage(archive_fd)
            require(usage+sum(record["bytes"] for record in inventory.values())+262144 <= ARCHIVE_CAP)
            manifest = dict(schema="geophysics.profile-retained-stage/v1",job_id=identifier,request_sha256=job.request_sha256,
                installation=installation,stage_identity=held,members=inventory,recovery=recovery,uncommitted_duplicate=duplicate)
            write_exclusive(archive_fd,intent_name,canonical_bytes(manifest))
        else:
            require(manifest["recovery"] == recovery and manifest["uncommitted_duplicate"] == duplicate)
        if identifier in os.listdir(stage_parent):
            if "manifest.json" not in os.listdir(stage_fd):
                write_exclusive(stage_fd,"manifest.json",canonical_bytes(manifest))
            reverify_archive(stage_fd,manifest)
            require(identity(os.stat(identifier,dir_fd=stage_parent,follow_symlinks=False)) == (held["device"],held["inode"]))
            rename_exclusive(stage_parent,identifier,archive_fd)
            os.fsync(stage_parent)
            os.fsync(archive_fd)
        if duplicate_present:
            async with sessions() as session:
                current = await session.get(ProcessingJob,identifier)
                require(current is not None and current.state == job.state and current.result_key is None and
                        current.request_sha256 == job.request_sha256)
            body = regular_at(target_fd,target.name,duplicate["bytes"])
            require(sha256(body) == duplicate["sha256"])
            os.unlink(target.name,dir_fd=target_fd)
            os.fsync(target_fd)
        return manifest
    finally:
        if process is not None and process.returncode is None:
            # Recovery itself is bounded and never runs scientific work. A
            # caller timeout cannot erase an unfinished archive or root journal.
            try:
                await asyncio.wait_for(process.wait(),45)
            except asyncio.TimeoutError:
                pass
        for reader in readers:
            if not reader.done():
                reader.cancel()
        if readers:
            await asyncio.gather(*readers,return_exceptions=True)
        for fd in reversed(fds):
            os.close(fd)
        await engine.dispose()
