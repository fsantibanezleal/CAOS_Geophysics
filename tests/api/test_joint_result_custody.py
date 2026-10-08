"""Actual allocated SQL/auth and retained native bytes, no numerical execution.

The failed job explicitly records custody_fixture_no_execution. Its unchanged
historical output is archival test data, never a new successful scientific fit.
"""
import asyncio
import hashlib
import io
import os
from pathlib import Path
import shutil
import zipfile
from functools import partial
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, text

from app import joint_execution as ex
from app import joint_result as result
from app.errors import ApiError
from app.joint_models import JointResultArtifact
from app.models import ProcessingJob
from test_joint_successor import successor as successor, allocated_harness as allocated_harness
from test_joint_protected import joint_harness as joint_harness
from test_joint_datasets import upload_pair, create_dataset


def local_account(harness, email):
    from app.accounts import provision_account
    password = 'private-native-custody-test-872'
    harness.client.portal.call(partial(provision_account, harness.app.state.sessions, email, password))
    response = harness.request('POST', '/api/auth/cookie/login', data={'username': email, 'password': password})
    assert response.status_code == 204, response.text
    assert harness.messages == []
    return harness.client.get('/api/auth/me').json()['id']


@pytest.fixture
def custody(allocated_harness, monkeypatch, tmp_path, request):
    from app import server
    original = server.install_processing_routes
    def install(app, settings, current_user, get_session):
        original(app, settings, current_user, get_session)
        result.install_joint_result_routes(app, settings, current_user, get_session)
    monkeypatch.setattr(server, 'install_processing_routes', install)
    harness = allocated_harness(auth_mode='local')
    owner = local_account(harness, 'custody-owner@example.org'); project = harness.project()['id']
    response = create_dataset(harness, project, upload_pair(harness, project))
    assert response.status_code == 201, response.text
    dataset = response.json()
    identity_request = {'schema': 'custody-test-historical-native-bytes/v1', 'execution_performed': False}
    job_id = str(uuid4())
    async def seed():
        async with harness.app.state.sessions() as session:
            session.add(ProcessingJob(id=job_id, owner_id=UUID(owner), project_id=project,
                dataset_id=dataset['dataset_id'], dataset_sha256=dataset['sha256'],
                method_id=result.METHOD, request_json=identity_request, request_sha256=ex.digest(ex.canonical(identity_request)),
                preflight={'scientific_execution': False}, state='failed',
                error_code='custody_fixture_no_execution'))
            await session.commit()
    asyncio.run(seed())
    output = Path(os.environ['GEOPHYSICS_JOINT_INSTRUMENT_FIXTURE'])
    assert output.is_dir(), 'actual external retained full native instrument required'
    if request.node.name != 'test_actual_full_native_publication_index_download_export_accounting':
        # Genuine partial failure custody: selected unchanged real output files,
        # not a manufactured completed inverse or another full scientific run.
        partial = tmp_path / 'actual-retained-partial'; partial.mkdir()
        shutil.copyfile(output / 'workflow.json', partial / 'workflow.json')
        (partial / 'calibration').mkdir()
        native = next((output / 'calibration').glob('*.npy'))
        shutil.copyfile(native, partial / 'calibration' / native.name)
        output = partial
    return harness, owner, project, job_id, output


def retained(custody, *, commit=True, available=512 * 1024**2, retained_bytes=None):
    harness, _, _, job_id, output = custody
    members = result.inventory(output)
    async def retain():
        async with harness.app.state.sessions() as session:
            await session.execute(text('BEGIN IMMEDIATE'))
            job = await session.get(ProcessingJob, job_id)
            payload = await result.retain_terminal_output(harness.settings, session, job, output,
                available_bytes=available, retained_bytes=retained_bytes if retained_bytes is not None else
                sum(m['byte_count'] for m in members.values()))
            assert job.state == 'failed' and job.error_code == 'custody_fixture_no_execution'
            if commit: await session.commit()
            else: await session.rollback()
            return payload
    return asyncio.run(retain())


def test_actual_full_native_publication_index_download_export_accounting(custody, tmp_path):
    harness, owner, project, job_id, output = custody
    before = result.inventory(output); payload = retained(custody)
    assert payload['members'] == before and payload['scientific_acceptance'] is False
    base = f'/api/projects/{project}/joint-results/{job_id}'
    response = harness.request('GET', base)
    assert response.status_code == 200, response.text
    assert response.json() == payload and response.headers['cache-control'] == 'no-store'
    assert response.headers['vary'] == 'Cookie'
    assert response.headers['x-content-sha256'] == ex.digest(ex.canonical(payload))
    assert len(before) > 500
    sample_array = next(name for name in before if name.startswith('models/') and name.endswith('.npy'))
    for name in ('workflow.json', 'instrument/instrument.json', sample_array):
        received = harness.request('GET', base + '/members', params={'name': name})
        assert received.status_code == 200, received.text
        assert received.content == (output / name).read_bytes()
        assert received.headers['x-content-sha256'] == before[name]['sha256']
        assert received.headers['vary'] == 'Cookie'
    archive = harness.request('GET', base + '/export')
    assert archive.status_code == 200, archive.text
    assert archive.headers['vary'] == 'Cookie'
    assert len(archive.content) == int(archive.headers['content-length']) == result.archive_byte_count(payload)
    history = harness.request('GET', f'/api/projects/{project}/joint-results')
    assert history.status_code == 200, history.text
    assert history.headers['cache-control'] == 'no-store' and history.headers['vary'] == 'Cookie'
    assert history.json()['jobs'][0]['state'] == 'failed'
    for name, body in (('actual-export.zip', archive.content), ('actual-index.json', response.content),
                       ('actual-history.json', history.content)):
        with (tmp_path / name).open('xb') as stream: stream.write(body)
    with zipfile.ZipFile(io.BytesIO(archive.content)) as zipped:
        assert set(zipped.namelist()) == set(before) | {'private-custody-index.json'}
        for name, member in before.items():
            body = zipped.read(name)
            assert len(body) == member['byte_count'] and hashlib.sha256(body).hexdigest() == member['sha256']
        assert zipped.read('private-custody-index.json') == ex.canonical(payload)
    export_root = harness.settings.data_dir / '.exports'
    assert not export_root.exists() and not export_root.is_symlink()
    async def audit():
        async with harness.app.state.sessions() as session:
            charged = await result.accounting_delta(session, UUID(owner), generic_reservation=8 * 1024**2)
            assert charged == payload['native_bytes'] + len(ex.canonical(payload))
            assert await result.audit_results(harness.settings, session) == payload['native_bytes']
            manifest = await result.project_manifest(harness.settings, session, UUID(owner), project)
            assert sum(m['byte_count'] for m in manifest) == charged
            assert len(manifest) == len(before) + 1
    asyncio.run(audit())
    assert result.inventory(output) == before
    local_account(harness, 'custody-other@example.org')
    for path in (base, base + '/members', base + '/export'):
        assert harness.request('GET', path, params={'name': 'workflow.json'}).status_code == 404


@pytest.mark.parametrize('change', ['member', 'directory'])
def test_real_archive_mid_write_drift_withholds_end_record_and_drains(custody, monkeypatch, change):
    from app.joint_archive import ArchivePipe
    harness, _, _, job_id, output = custody
    originals = result.inventory(output); payload = retained(custody)
    async def context():
        async with harness.app.state.sessions() as session:
            job = await session.get(ProcessingJob, job_id)
            _, rows = await result.read_result(harness.settings, session, job)
            return job, rows
    job, rows = asyncio.run(context())
    target = result.artifact_path(harness.settings, next(row.storage_key for row in rows if row.name.endswith('.npy')))
    actual_write = ArchivePipe.write; changed = False
    def drift(pipe, body):
        nonlocal changed
        written = actual_write(pipe, body)
        if not changed and bytes(body).startswith(b'\x93NUMPY'):
            changed = True
            if change == 'member':
                with target.open('ab') as stream: stream.write(b'actual mid-write custody drift')
            else: (target.parent / 'unknown-empty').mkdir()
        return written
    monkeypatch.setattr(ArchivePipe, 'write', drift)
    response = result.archive_response(harness.settings, job, payload, rows); transferred = bytearray()
    async def execute():
        async def send(message):
            if message['type'] == 'http.response.body': transferred.extend(message.get('body', b''))
        async def receive(): await asyncio.Event().wait()
        with pytest.raises(ApiError):
            await response({'type': 'http', 'asgi': {'spec_version': '2.4'}}, receive, send)
    asyncio.run(execute())
    assert changed and not response.pipe.thread.is_alive()
    assert b'PK\x05\x06' not in transferred
    with pytest.raises(zipfile.BadZipFile): zipfile.ZipFile(io.BytesIO(transferred))
    export_root = harness.settings.data_dir / '.exports'
    assert not export_root.exists() and not export_root.is_symlink()
    assert result.inventory(output) == originals  # Only this test's retained copy changed.


@pytest.mark.parametrize('failure', ['quota', 'undercharge', 'successful_without_execution', 'request', 'source'])
def test_refusals_before_first_durable_write(custody, failure):
    harness, _, _, job_id, output = custody
    async def execute():
        async with harness.app.state.sessions() as session:
            await session.execute(text('BEGIN IMMEDIATE'))
            job = await session.get(ProcessingJob, job_id)
            if failure == 'successful_without_execution': job.state = 'succeeded'
            if failure == 'request': job.request_json = {'changed': True}
            if failure == 'source':
                from app.models import RawAsset
                rows = (await session.execute(select(RawAsset).where(RawAsset.project_id == job.project_id))).scalars().all()
                path = result._io(harness.settings.data_dir / rows[0].storage_key)
                with path.open('ab') as stream: stream.write(b'changed')
            with pytest.raises((ApiError, ValueError)):
                await result.retain_terminal_output(harness.settings, session, job, output,
                    available_bytes=1 if failure == 'quota' else harness.settings.account_quota_bytes,
                    retained_bytes=0 if failure == 'undercharge' else ex.CAP)
            await session.rollback()
    asyncio.run(execute())
    assert not list(result._io(harness.settings.data_dir / 'derived').glob('*/*/joint'))


def test_uncertain_rollback_keeps_actual_bytes_and_audit_refuses(custody):
    harness, owner, project, job_id, _ = custody
    payload = retained(custody, commit=False)
    root = result._io(harness.settings.data_dir / 'derived' / owner / project / 'joint' / job_id)
    assert result.inventory(root) == payload['members']
    async def inspect():
        async with harness.app.state.sessions() as session:
            assert not (await session.execute(select(JointResultArtifact))).first()
            with pytest.raises(ApiError): await result.audit_results(harness.settings, session)
    asyncio.run(inspect())
    report = result.recovery_report(root, payload['members'])
    assert len(report['exact']) == len(payload['members']) and report['reconciled'] is False
    assert report['observed_bytes'] == payload['native_bytes']
    # An uncertain retry never overwrites/adopts original bytes.
    with pytest.raises(ApiError, match='Native result custody'): retained(custody)
    assert result.inventory(root) == payload['members']


def test_uncertain_commit_ack_preserves_rows_bytes_and_charge(custody):
    harness, owner, project, job_id, output = custody
    async def lost_ack():
        async with harness.app.state.sessions() as session:
            await session.execute(text('BEGIN IMMEDIATE'))
            job = await session.get(ProcessingJob, job_id)
            members = result.inventory(output)
            await result.retain_terminal_output(harness.settings, session, job, output,
                available_bytes=512 * 1024**2, retained_bytes=sum(m['byte_count'] for m in members.values()))
            await session.commit()
            try: raise RuntimeError('actual_commit_ack_lost')
            except RuntimeError: await session.rollback()
        async with harness.app.state.sessions() as session:
            job = await session.get(ProcessingJob, job_id)
            payload, _ = await result.read_result(harness.settings, session, job)
            assert await result.accounting_delta(session, UUID(owner), generic_reservation=8 * 1024**2) == payload['native_bytes'] + job.result_bytes
            assert await result.audit_results(harness.settings, session) == payload['native_bytes']
    asyncio.run(lost_ack())
    assert harness.request('GET', f'/api/projects/{project}/joint-results/{job_id}').status_code == 200


def test_genuine_original_failed_ledgers_remain_byte_exact(tmp_path):
    root = Path(os.environ['GEOPHYSICS_JOINT_DURABLE_ABORT_FIXTURE'])
    members = result.inventory(root)
    assert 'failure.json' in members and any(name.startswith('aborted/') for name in members)
    copied = tmp_path / 'retained-failed-native'
    result._copy_tree(root, copied, members)
    assert result.inventory(copied) == members and result.inventory(root) == members
    assert result.recovery_report(copied, members)['reconciled'] is False


@pytest.mark.parametrize('change', ['unknown', 'changed', 'missing', 'empty_directory'])
def test_storage_drift_blocks_download_export_and_purge_preserving_bytes(custody, change):
    harness, owner, project, job_id, _ = custody
    payload = retained(custody)
    root = result._io(harness.settings.data_dir / 'derived' / owner / project / 'joint' / job_id)
    name = next(iter(payload['members']))
    if change == 'unknown':
        with (root / 'foreign.bin').open('xb') as stream: stream.write(b'original unknown bytes')
    if change == 'changed':
        with (root / name).open('ab') as stream: stream.write(b'changed')
    if change == 'missing': (root / name).rename(root / 'missing-retained.bin')
    if change == 'empty_directory': (root / 'unknown').mkdir()
    snapshot = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    base = f'/api/projects/{project}/joint-results/{job_id}'
    for suffix in ('', '/export', '/members'):
        assert harness.request('GET', base + suffix, params={'name': 'workflow.json'}).status_code == 409
    with pytest.raises(ApiError): result.purge_exact_job(root, payload['members'])
    assert snapshot == {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}


def test_artifact_delete_rollback_and_exact_isolated_purge(custody, tmp_path):
    harness, owner, project, job_id, _ = custody
    payload = retained(custody)
    async def rows():
        async with harness.app.state.sessions() as session:
            await session.execute(text('BEGIN IMMEDIATE'))
            with pytest.raises(ApiError): await result.delete_artifact_rows(session, UUID(owner), project, set())
            await result.delete_artifact_rows(session, UUID(owner), project, {job_id})
            assert not (await session.execute(select(JointResultArtifact))).first()
            await session.rollback()
            assert len((await session.execute(select(JointResultArtifact))).scalars().all()) == len(payload['members'])
    asyncio.run(rows())
    # Destruction only of this explicitly copied isolated fixture, not originals.
    isolated = tmp_path / '.deleting' / f'{owner}--{project}--derived' / 'joint' / job_id
    source = harness.settings.data_dir / 'derived' / owner / project / 'joint' / job_id
    assert isolated.resolve().is_relative_to(tmp_path.resolve()) and isolated != source
    shutil.copytree(result._io(source), result._io(isolated))
    with pytest.raises(ApiError, match='Native result custody'): result.purge_exact_job(source, payload['members'])
    result.purge_exact_job(isolated, payload['members'])
    assert not result._io(isolated).exists() and result.inventory(source) == payload['members']


@pytest.mark.parametrize('change', ['traversal', 'emptydir', 'filecap', 'bytescap'])
def test_whole_admission_before_hash(tmp_path, monkeypatch, change):
    root = tmp_path / 'admission'; root.mkdir()
    with (root / 'workflow.json').open('xb') as stream: stream.write(b'original actual bounded transport')
    if change == 'traversal':
        with (root / '..foreign.json').open('xb') as stream: stream.write(b'unknown')
    if change == 'emptydir': (root / 'calibration').mkdir()
    if change == 'filecap': monkeypatch.setattr(result, 'MAX_FILES', 0)
    if change == 'bytescap': monkeypatch.setattr(ex, 'CAP', 1)
    def forbidden(*args): raise AssertionError('hash before whole admission')
    monkeypatch.setattr(result, '_hash', forbidden)
    with pytest.raises(ApiError): result.inventory(root)
