"""Durable native custody, independent of numerical acceptance and SQL commit.

Parent owns the singleton, write guard, project tombstone and incomplete stages.
No cleanup or scientific state transition is performed by publication/recovery.
"""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
import hashlib
import os
from pathlib import Path
import re
import stat
import zipfile

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, func, select, text

from app import joint_execution as ex
from app.config import Settings
from app.errors import ApiError
from app.joint_datasets import validate_source_rows
from app.joint_models import JointResultArtifact
from app.models import AccountUsage, ObservationDataset, ProcessingJob, User
from app.processing_contract import checked_derived_path, result_key, verified_json

METHOD = 'joint.gravity-magnetic-native/v1'
SCHEMA = 'geophysics.joint-result-custody/v1'
MAX_FILES = 1100
INDEX_CAP = 256 * 1024
ACTIVE = {'queued', 'running'}
TERMINAL = {'succeeded', 'failed', 'cancelled'}
_NAME = re.compile(r'(?:workflow\.json|failure\.json|(?:calibration|frozen|models|result|instrument|aborted)/[a-z][a-z0-9_]{0,120}\.(?:json|npy))\Z')


def _io(path):
    """Keep literal ledger keys portable; use native long-path IO on Windows."""
    path = Path(path)
    if os.name == 'nt' and not str(path).startswith('\\\\?\\'):
        value = str(path.absolute())
        return Path('\\\\?\\UNC\\' + value[2:] if value.startswith('\\\\') else '\\\\?\\' + value)
    return path


async def _drained_io(operation, *args):
    """Cancellation cannot release caller guards while a file writer still runs."""
    task = asyncio.create_task(asyncio.to_thread(operation, *args))
    cancelled = False
    while not task.done():
        try: await asyncio.shield(task)
        except asyncio.CancelledError: cancelled = True
    value = task.result()
    if cancelled: raise asyncio.CancelledError
    return value


def _require(value, reason='joint_result_recovery_required'):
    if not value:
        raise ApiError(409, reason, 'Native result custody requires reconciliation')


def _name(value):
    _require(type(value) is str and _NAME.fullmatch(value), 'joint_result_member_invalid')
    return value


def _binding(job):
    value = {key: str(getattr(job, key)) for key in (
        'id', 'owner_id', 'project_id', 'dataset_id', 'dataset_sha256', 'method_id', 'request_sha256')}
    value['job_id'] = value.pop('id')
    for key in ('job_id', 'owner_id', 'project_id', 'dataset_id'):
        ex.identity(value[key])
    ex.sha(value['dataset_sha256']); ex.sha(value['request_sha256'])
    _require(value['method_id'] == METHOD, 'joint_result_method_invalid')
    _require(ex.digest(ex.canonical(job.request_json)) == value['request_sha256'], 'joint_request_changed')
    return value


def artifact_key(job, name):
    value = _binding(job)
    return f"derived/{value['owner_id']}/{value['project_id']}/joint/{value['job_id']}/{_name(name)}"


def artifact_path(settings, key):
    _require(type(key) is str and '\\' not in key, 'joint_result_path_invalid')
    parts = key.split('/')
    _require(len(parts) in (6, 7) and parts[0] == 'derived' and parts[3] == 'joint', 'joint_result_path_invalid')
    for index in (1, 2, 4): ex.identity(parts[index])
    _name('/'.join(parts[5:]))
    root = ex.ordinary(_io(settings.data_dir), directory=True, external=True)
    path = root.joinpath(*parts)
    _require(path.is_relative_to(root), 'joint_result_path_invalid')
    # Check existing components BEFORE mkdir/open, including Windows junctions.
    for parent in reversed(path.parents):
        if parent.is_relative_to(root) and parent.exists():
            info = parent.lstat()
            _require(stat.S_ISDIR(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    if path.exists() or path.is_symlink(): _file(path)
    return path


def _file(path):
    path = _io(path); info = path.lstat()
    _require(stat.S_ISREG(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    return path


def _hash(path, expected=None, *, admitted=False):
    path = _file(path) if admitted else ex.ordinary(_io(path), external=True)
    before = path.stat()
    with path.open('rb') as stream:
        held = os.fstat(stream.fileno())
        _require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
                 (held.st_dev, held.st_ino, held.st_size, held.st_mtime_ns))
        hashed = hashlib.file_digest(stream, 'sha256').hexdigest()
        _require(_stat(os.fstat(stream.fileno())) == _stat(held))
    _require(_stat(path.stat()) == _stat(before))
    value = {'byte_count': before.st_size, 'sha256': hashed}
    if expected is not None: _require(value == expected)
    return value


def _stat(value):
    # atime can change on a legitimate read. ctime is compared within its own
    # namespace, never equated between Windows held and named descriptors.
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns


def inventory(directory):
    """Whole stat/name/cap admission precedes any hash, decode or copy."""
    directory = ex.ordinary(_io(directory), directory=True, external=True)
    snapshots = {directory: _stat(directory.stat())}
    observed = list(directory.rglob('*'))
    files = {}; directories = set(); total = 0
    for path in observed:
        if path.is_dir():
            ex.ordinary(path, directory=True, external=True); directories.add(path)
            snapshots[path] = _stat(path.stat())
        else:
            _file(path)
            name = _name(path.relative_to(directory).as_posix())
            size = path.stat().st_size
            _require(0 < size <= ex.CAP, 'joint_result_size_invalid')
            total += size; files[name] = path
    _require(0 < len(files) <= MAX_FILES and total <= ex.CAP, 'joint_result_whole_cap')
    allowed = {p.parent for p in files.values() if p.parent != directory}
    _require(directories == allowed, 'joint_result_unknown_directory')
    def hashed(item):
        name, path = item
        return name, _hash(path, admitted=True)
    with ThreadPoolExecutor(max_workers=4) as workers:
        values = dict(workers.map(hashed, sorted(files.items())))
    _require(all(_stat(ex.ordinary(path, directory=True, external=True).stat()) == before
                 for path, before in snapshots.items()))
    _require(set(directory.rglob('*')) == set(files.values()) | directories)
    return values


def validate_index(payload, job):
    ex.fields(payload, ('schema', *_binding(job), 'state', 'members', 'native_bytes',
                        'scientific_acceptance', 'authenticity_verified', 'public_activation'))
    _require(payload['schema'] == SCHEMA and payload['state'] == job.state and job.state in TERMINAL)
    _require(all(payload[k] == v for k, v in _binding(job).items()))
    _require(all(payload[k] is False for k in ('scientific_acceptance', 'authenticity_verified', 'public_activation')))
    members = payload['members']
    _require(type(members) is dict and 0 < len(members) <= MAX_FILES)
    total = 0
    for name, member in members.items():
        _name(name); ex.fields(member, ('byte_count', 'sha256'))
        _require(type(member['byte_count']) is int and 0 < member['byte_count'] <= ex.CAP)
        ex.sha(member['sha256']); total += member['byte_count']
    _require(type(payload['native_bytes']) is int and total == payload['native_bytes'] and total <= ex.CAP)


def verified_artifacts(settings, job, payload, rows):
    validate_index(payload, job)
    _require(len(rows) == len(payload['members']) and len({r.name for r in rows}) == len(rows))
    for row in rows:
        _require(all(str(getattr(row, k)) == v for k, v in _binding(job).items()))
        _require(row.storage_key == artifact_key(job, row.name))
        _require(payload['members'].get(row.name) == {'byte_count': row.byte_count, 'sha256': row.sha256})
    root = settings.data_dir / 'derived' / str(job.owner_id) / job.project_id / 'joint' / job.id
    _require(inventory(root) == payload['members'])
    return [{'kind': 'joint_artifact', 'id': job.id, 'name': row.name,
             'relative_path': f'joint/{job.id}/{row.name}', 'byte_count': row.byte_count, 'sha256': row.sha256}
            for row in sorted(rows, key=lambda row: row.name)]


async def _source(settings, session, job):
    dataset = await session.get(ObservationDataset, job.dataset_id)
    _require(dataset is not None and str(dataset.owner_id) == str(job.owner_id)
             and dataset.project_id == job.project_id and dataset.sha256 == job.dataset_sha256)
    payload = verified_json(settings, dataset.storage_key, dataset.sha256, dataset.byte_count)
    try:
        await validate_source_rows(settings, session, dataset, payload)
    except ValueError as error:
        raise ApiError(409, 'joint_source_changed', 'Native source custody changed') from error
    return dataset


async def _write_transaction(session):
    _require(session.in_transaction(), 'joint_result_transaction_required')
    _require((await session.execute(text('PRAGMA foreign_keys'))).scalar_one() == 1,
             'joint_result_foreign_keys_required')
    # No commit, rollback, independent connection or inferred write-guard grant.


def _copy(source, target, binding, *, admitted=False):
    source, target = _io(source), _io(target)
    if not admitted:
        target.parent.mkdir(parents=True, exist_ok=True)
        ex.ordinary(target.parent, directory=True, external=True)
    total = 0; hashed = hashlib.sha256()
    with (_file(source) if admitted else ex.ordinary(source, external=True)).open('rb') as incoming, target.open('xb') as outgoing:
        before = os.fstat(incoming.fileno())
        while chunk := incoming.read(1024 * 1024):
            total += len(chunk); _require(total <= binding['byte_count'])
            hashed.update(chunk); outgoing.write(chunk)
        outgoing.flush(); os.fsync(outgoing.fileno())
        _require(_stat(os.fstat(incoming.fileno())) == _stat(before))
    _require({'byte_count': total, 'sha256': hashed.hexdigest()} == binding)
    _hash(target, binding, admitted=admitted)


def _copy_tree(source, root, members):
    source, root = _io(source), _io(root)
    _require(inventory(source) == members)
    root.parent.mkdir(parents=True, exist_ok=True)
    ex.ordinary(root.parent, directory=True, external=True)
    root.mkdir()  # Exclusive job tree; never merge or adopt uncertain bytes.
    for name in sorted({str(Path(name).parent) for name in members if '/' in name}):
        (root / name).mkdir(); ex.ordinary(root / name, directory=True, external=True)
    def copied(item):
        name, binding = item
        _copy(source / name, root / name, binding, admitted=True)
    with ThreadPoolExecutor(max_workers=4) as workers:
        list(workers.map(copied, members.items()))
    _require(inventory(source) == members and inventory(root) == members)


async def retain_terminal_output(settings, session, job, output, *, available_bytes,
                                 retained_bytes, admission=None):
    """Copy originals and flush exact rows; caller owns commit and all guards.

    available_bytes is actual quota remaining after canonical existing usage;
    retained_bytes includes the existing stage/scratch charge, never just output.
    Neither is upload controlled. Uncertain bytes remain after any failure.
    """
    await _write_transaction(session)
    _binding(job); _require(job.state in TERMINAL, 'joint_result_terminal_required')
    _require(all(value is None for value in (job.result_key, job.result_sha256, job.result_bytes)))
    _require(not (await session.execute(select(JointResultArtifact.job_id).where(
        JointResultArtifact.job_id == job.id))).first())
    await _source(settings, session, job)
    if job.state == 'succeeded':
        _require(admission is not None, 'joint_current_execution_required')
        from app.joint_worker import completed_child
        control_path, control_sha = admission
        control, raw = ex.read_json(control_path)
        _require(ex.digest(raw) == control_sha)
        context, _ = ex.read_json(control['context_path'])
        _require(all(control[k] == v for k, v in _binding(job).items() if k in control))
        digest, failure = completed_child(control_sha, control, context, Path(control['stage']))
        outcome, _ = ex.read_json(Path(control['stage']) / 'supervisor.json')
        _require(failure is None and outcome['execution_completed'] is True
                 and outcome['child_receipt_sha256'] == digest
                 and Path(output) == Path(control['stage']) / 'export', 'joint_current_execution_required')
    members = await asyncio.to_thread(inventory, output)
    payload = {'schema': SCHEMA, **_binding(job), 'state': job.state, 'members': members,
               'native_bytes': sum(item['byte_count'] for item in members.values()),
               'scientific_acceptance': False, 'authenticity_verified': False, 'public_activation': False}
    raw = ex.canonical(payload); _require(len(raw) <= INDEX_CAP)
    _require(type(available_bytes) is int and type(retained_bytes) is int and retained_bytes >= payload['native_bytes'])
    # A caller may lower remaining quota, never supply a larger allowance than
    # the actual ledger. The canonical union must count joint rows exactly once.
    from app.processing_storage import joint_base_derived_usage
    usage = await session.get(AccountUsage, job.owner_id)
    ledger = (usage.raw_bytes if usage else 0) + await joint_base_derived_usage(session, job.owner_id)
    ledger += await accounting_delta(session, job.owner_id, generic_reservation=8 * 1024**2)
    _require(available_bytes <= settings.account_quota_bytes - ledger, 'account_quota_exceeded')
    _require(retained_bytes + payload['native_bytes'] + len(raw) <= available_bytes, 'account_quota_exceeded')
    root = _io(settings.data_dir / 'derived' / str(job.owner_id) / job.project_id / 'joint' / job.id)
    _require(not root.exists() and not root.is_symlink(), 'joint_result_existing_bytes_require_recovery')
    # All grammar, size, source and quota checks precede first mkdir/copy.
    artifact_path(settings, artifact_key(job, next(iter(members))))
    await _drained_io(_copy_tree, Path(output), root, members)
    key = result_key(str(job.owner_id), job.project_id, job.id)
    target = _io(checked_derived_path(settings, key))
    target.parent.mkdir(parents=True, exist_ok=True)
    ex.ordinary(target.parent, directory=True, external=True)
    with target.open('xb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    _require(await asyncio.to_thread(inventory, output) == members)
    await _source(settings, session, job)
    for name, binding in members.items():
        session.add(JointResultArtifact(**_binding(job), name=name,
            storage_key=artifact_key(job, name), **binding))
    job.result_key = key; job.result_sha256 = ex.digest(raw); job.result_bytes = len(raw)
    await session.flush()
    await read_result(settings, session, job)
    if job.state == 'succeeded':
        # Copies and final source/audit consume the SAME original job deadline.
        _, failure = completed_child(control_sha, control, context, Path(control['stage']))
        _require(failure is None, 'joint_current_execution_required')
    return payload


async def read_result(settings, session, job):
    _binding(job)
    _require(job.result_key == result_key(str(job.owner_id), job.project_id, job.id)
             and job.result_sha256 is not None and type(job.result_bytes) is int
             and 0 < job.result_bytes <= INDEX_CAP, 'joint_result_not_ready')
    await _source(settings, session, job)
    payload = verified_json(settings, job.result_key, job.result_sha256, job.result_bytes)
    rows = (await session.execute(select(JointResultArtifact).where(JointResultArtifact.job_id == job.id))).scalars().all()
    await asyncio.to_thread(verified_artifacts, settings, job, payload, rows)
    return payload, rows


async def accounting_delta(session, owner_id, *, generic_reservation):
    """Add to canonical accounting once; success indices already counted there."""
    rows = (await session.execute(select(ProcessingJob).where(
        ProcessingJob.owner_id == owner_id, ProcessingJob.method_id == METHOD))).scalars().all()
    artifacts = (await session.execute(select(func.coalesce(func.sum(JointResultArtifact.byte_count), 0)).where(
        JointResultArtifact.owner_id == owner_id))).scalar_one()
    _require(type(generic_reservation) is int and 0 <= generic_reservation <= ex.CAP)
    return int(artifacts) + sum((ex.CAP - generic_reservation) if job.state in ACTIVE else
        (job.result_bytes or 0) if job.state != 'succeeded' else 0 for job in rows)


async def audit_results(settings, session):
    """No stale/unknown bytes are adopted, swept, or silently uncharged."""
    jobs = (await session.execute(select(ProcessingJob).where(ProcessingJob.method_id == METHOD))).scalars().all()
    rows = (await session.execute(select(JointResultArtifact))).scalars().all()
    known = {job.id: job for job in jobs}
    _require(all(row.job_id in known for row in rows))
    expected = set()
    for job in jobs:
        bound = [r for r in rows if r.job_id == job.id]
        if job.result_key is None:
            _require(not bound and job.result_bytes is None and job.result_sha256 is None)
            continue
        payload, _ = await read_result(settings, session, job)
        expected.update(artifact_path(settings, artifact_key(job, name)) for name in payload['members'])
    derived = _io(settings.data_dir / 'derived')
    if derived.exists():
        for owner in derived.iterdir():
            ex.ordinary(owner, directory=True, external=True)
            for project in owner.iterdir():
                ex.ordinary(project, directory=True, external=True)
                root = project / 'joint'
                if not root.exists(): continue
                ex.ordinary(root, directory=True, external=True)
                observed = set(root.rglob('*'))
                allowed = {p for path in expected if path.is_relative_to(root)
                           for p in path.parents if p != root and p.is_relative_to(root)}
                _require(observed == {p for p in expected if p.is_relative_to(root)} | allowed)
    return sum(row.byte_count for row in rows)


async def project_manifest(settings, session, owner_id, project_id):
    """Parent unions these into its one exact derived/tombstone manifest."""
    jobs = (await session.execute(select(ProcessingJob).where(
        ProcessingJob.owner_id == owner_id, ProcessingJob.project_id == project_id,
        ProcessingJob.method_id == METHOD))).scalars().all()
    manifest = []
    for job in jobs:
        _require(job.state not in ACTIVE, 'project_jobs_active')
        if job.result_key is None:
            _require(job.result_bytes is None and job.result_sha256 is None)
            continue
        payload, rows = await read_result(settings, session, job)
        manifest.append({'kind': 'result', 'id': job.id, 'relative_path': f'results/{job.id}.json',
                         'byte_count': job.result_bytes, 'sha256': job.result_sha256})
        manifest.extend(verified_artifacts(settings, job, payload, rows))
    return manifest


async def delete_artifact_rows(session, owner_id, project_id, job_ids):
    """Called after parent's exact rename, before its job/tombstone co-commit.

    Only restrictive artifact rows are removed. Root/source/family/job deletion
    and all byte/tombstone authority remain in the caller's one transaction.
    """
    await _write_transaction(session)
    jobs = (await session.execute(select(ProcessingJob).where(
        ProcessingJob.owner_id == owner_id, ProcessingJob.project_id == project_id,
        ProcessingJob.method_id == METHOD))).scalars().all()
    _require(type(job_ids) is set and {job.id for job in jobs} == job_ids)
    _require(all(job.state in TERMINAL for job in jobs), 'project_jobs_active')
    await session.execute(delete(JointResultArtifact).where(
        JointResultArtifact.owner_id == owner_id, JointResultArtifact.project_id == project_id,
        JointResultArtifact.job_id.in_(job_ids)))


def recovery_report(directory, members):
    """Read-only original hashes; no fabricated ledger adoption or unlink."""
    root = ex.ordinary(_io(directory), directory=True, external=True)
    _require(type(members) is dict and len(members) <= MAX_FILES)
    expected = {_name(name): binding for name, binding in members.items()}
    observed = {}; dirs = set(); paths = []
    for path in root.rglob('*'):
        if path.is_dir():
            ex.ordinary(path, directory=True, external=True); dirs.add(path.relative_to(root).as_posix())
        else: paths.append(ex.ordinary(path, external=True))
    _require(len(paths) <= MAX_FILES and sum(path.stat().st_size for path in paths) <= ex.CAP,
             'joint_recovery_whole_cap')
    for path in paths: observed[path.relative_to(root).as_posix()] = _hash(path)
    known_dirs = {str(Path(name).parent).replace('\\', '/') for name in expected if '/' in name}
    return {'schema': 'geophysics.joint-recovery-inspection/v1',
            'exact': sorted(name for name, binding in expected.items() if observed.get(name) == binding),
            'missing': sorted(set(expected) - set(observed)),
            'changed': sorted(name for name, binding in expected.items() if name in observed and observed[name] != binding),
            'unknown': sorted(set(observed) - set(expected)),
            'unknown_directories': sorted(dirs - known_dirs),
            'observed_bytes': sum(item['byte_count'] for item in observed.values()),
            'reconciled': False, 'scientific_acceptance': False}


def purge_exact_job(directory, members):
    """Only parent's already renamed isolated job tree, after tombstone commit."""
    root = ex.ordinary(_io(directory), directory=True, external=True)
    _require(root.parent.name == 'joint' and root.parent.parent.parent.name == '.deleting',
             'joint_purge_requires_renamed_custody')
    ex.identity(root.name)
    owner_project = root.parent.parent.name.removesuffix('--derived').split('--')
    _require(root.parent.parent.name.endswith('--derived') and len(owner_project) == 2,
             'joint_purge_requires_renamed_custody')
    for value in owner_project: ex.identity(value)
    _require(inventory(root) == members)
    paths = [root / _name(name) for name in members]
    # Revalidate all bytes before deleting anything; unknown files always refuse.
    for path in paths: _hash(path, members[path.relative_to(root).as_posix()])
    _require(inventory(root) == members)
    dirs = {p.parent for p in paths if p.parent != root}
    for path in paths: path.unlink()
    for parent in dirs: parent.rmdir()
    root.rmdir()


def write_archive(settings, job, payload, rows, target):
    verified_artifacts(settings, job, payload, rows)
    with Path(target).open('xb') as output, zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_STORED) as archive:
        _archive_members(archive, settings, job, payload, rows)
    verified_artifacts(settings, job, payload, rows)


def _archive_members(archive, settings, job, payload, rows):
    for row in sorted(rows, key=lambda row: row.name):
        # Complete tree/key admission precedes this loop. Each opened original
        # is still checked while held and against its named identity afterward.
        path = _file(settings.data_dir / row.storage_key)
        before = _stat(path.stat()); hashed = hashlib.sha256(); count = 0
        with path.open('rb') as stream, archive.open(row.name, 'w', force_zip64=True) as member:
            held = _stat(os.fstat(stream.fileno()))
            # Windows named/CRT held ctime namespaces differ; compare identity
            # across namespaces, then each ctime only against its own snapshot.
            _require(held[:4] == before[:4])
            while chunk := stream.read(1024 * 1024):
                count += len(chunk); _require(count <= row.byte_count)
                hashed.update(chunk); member.write(chunk)
            _require(_stat(os.fstat(stream.fileno())) == held)
        _require(count == row.byte_count and hashed.hexdigest() == row.sha256
                 and _stat(path.stat()) == before)
    archive.writestr('private-custody-index.json', ex.canonical(payload))
    # Must close BEFORE ZipFile emits its central directory/end record. A
    # failed final inventory can never be a complete accepted streamed archive.
    verified_artifacts(settings, job, payload, rows)


def archive_byte_count(payload):
    """Exact ASCII ZIP_STORED/forced-member ZIP64 + descriptors + plain index.

    All counts/offsets are below the original256MiB and1100-member limits, so
    central-directory ZIP64 extensions/end records are not needed. Native local
    headers have a20-byte ZIP64 extra and24-byte streaming descriptor; the
    plain index has a16-byte descriptor. No comments or incidental extra fields.
    """
    index = ex.canonical(payload)
    _require(len(index) <= INDEX_CAP)
    total = 22 + len(index) + 92 + 2 * len('private-custody-index.json')
    for name, member in payload['members'].items():
        total += member['byte_count'] + 120 + 2 * len(_name(name).encode('ascii'))
    _require(total <= ex.CAP, 'joint_export_whole_cap')
    return total


def archive_response(settings, job, payload, rows):
    from app.joint_archive import ArchivePipe, JointArchiveResponse
    validate_index(payload, job)
    count = archive_byte_count(payload)
    def produce(output):
        verified_artifacts(settings, job, payload, rows)
        with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_STORED) as archive:
            _archive_members(archive, settings, job, payload, rows)
    return JointArchiveResponse(ArchivePipe(produce, byte_count=count, cap=ex.CAP), job_id=job.id)


def install_joint_result_routes(app, settings: Settings, current_user, get_session):
    router = APIRouter(prefix='/api/projects/{project_id}/joint-results', tags=['joint-results'])

    async def owned(session, project_id, job_id, user):
        job = (await session.execute(select(ProcessingJob).where(ProcessingJob.id == job_id,
            ProcessingJob.project_id == project_id, ProcessingJob.owner_id == user.id,
            ProcessingJob.method_id == METHOD))).scalar_one_or_none()
        if job is None: raise ApiError(404, 'not_found', 'Native result not found for this account')
        return job

    @router.get('')
    async def history(project_id: str, user: User = Depends(current_user), session=Depends(get_session)):
        from app.models import Project
        project = (await session.execute(select(Project.id).where(
            Project.id == project_id, Project.owner_id == user.id))).scalar_one_or_none()
        if project is None: raise ApiError(404, 'not_found', 'Project not found for this account')
        jobs = (await session.execute(select(ProcessingJob).where(ProcessingJob.project_id == project_id,
            ProcessingJob.owner_id == user.id, ProcessingJob.method_id == METHOD).order_by(
                ProcessingJob.created_at.desc()).limit(201))).scalars().all()
        _require(len(jobs) <= 200, 'joint_history_page_required')
        payload = {'schema': 'geophysics.joint-custody-history/v1', 'owner_id': str(user.id),
                'project_id': project_id, 'jobs': [{**_binding(job), 'state': job.state,
                    'cancel_requested': job.cancel_requested, 'error_code': job.error_code,
                    'index_available': job.result_key is not None,
                    'result_sha256': job.result_sha256, 'result_bytes': job.result_bytes} for job in jobs]}
        from fastapi.responses import JSONResponse
        return JSONResponse(payload, headers={'Cache-Control': 'no-store', 'Vary': 'Cookie'})

    @router.get('/{job_id}')
    async def index(project_id: str, job_id: str, user: User = Depends(current_user), session=Depends(get_session)):
        job = await owned(session, project_id, job_id, user)
        payload, _ = await read_result(settings, session, job)
        from fastapi.responses import JSONResponse
        return JSONResponse(payload, headers={'Cache-Control': 'no-store', 'Vary': 'Cookie', 'X-Content-SHA256': job.result_sha256})

    @router.get('/{job_id}/members')
    async def member(project_id: str, job_id: str, name: str, user: User = Depends(current_user), session=Depends(get_session)):
        job = await owned(session, project_id, job_id, user)
        payload, rows = await read_result(settings, session, job)
        _name(name)
        row = next((r for r in rows if r.name == name), None)
        if row is None: raise ApiError(404, 'not_found', 'Native member not found')
        path = artifact_path(settings, row.storage_key)
        # Hold the verified descriptor through transmission, not a later FileResponse reopen.
        stream = path.open('rb'); before = os.fstat(stream.fileno())
        hashed = hashlib.file_digest(stream, 'sha256').hexdigest()
        if hashed != row.sha256 or before.st_size != row.byte_count:
            stream.close(); _require(False)
        stream.seek(0)
        async def chunks():
            try:
                while chunk := await asyncio.to_thread(stream.read, 1024 * 1024): yield chunk
                _require(_stat(os.fstat(stream.fileno())) == _stat(before))
            finally: stream.close()
        return StreamingResponse(chunks(), media_type='application/octet-stream', headers={
            'Cache-Control': 'no-store', 'Vary': 'Cookie', 'X-Content-SHA256': row.sha256,
            'Content-Length': str(row.byte_count), 'X-Content-Type-Options': 'nosniff'})

    @router.get('/{job_id}/export')
    async def export(project_id: str, job_id: str, user: User = Depends(current_user), session=Depends(get_session)):
        job = await owned(session, project_id, job_id, user)
        payload, rows = await read_result(settings, session, job)
        # No persistent temporary ZIP, including exception/disconnect paths.
        # The ASGI response owns and drains its bounded producer before return.
        return archive_response(settings, job, payload, rows)

    app.include_router(router)
