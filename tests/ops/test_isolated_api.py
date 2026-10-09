"""Isolated unit/transport boundaries; actual systemd execution is separate."""

from pathlib import Path
import json
import sqlite3
from types import SimpleNamespace
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import qualify_isolated_api as qualifier  # noqa: E402


@pytest.fixture
def release(tmp_path, monkeypatch):
    monkeypatch.setattr(qualifier, 'RELEASES', tmp_path / 'releases')
    path = qualifier.RELEASES / 'candidate'
    templates = path / 'source/deploy/service'
    templates.mkdir(parents=True)
    for name in ('geophysics-api.socket', 'geophysics-api.service'):
        (templates / name).write_bytes((ROOT / 'deploy/service' / name).read_bytes())
    return path


def test_exact_candidate_unit_keeps_production_sandbox(release):
    name, service, socket = qualifier.unit_texts(release, '123456abcdef')
    assert name == 'geophysics-qualification-123456abcdef'
    assert str(release.as_posix()) + '/source' in service
    assert str(release.as_posix()) + '/.venv/bin/python' in service
    assert f'Requires={name}.socket\nAfter={name}.socket' in service
    assert f'ListenStream=/run/{name}.sock' in socket
    for literal in ('User=geophysics', 'Group=geophysics', 'MemoryMax=512M', 'MemorySwapMax=0',
                    'TasksMax=96', 'PrivateNetwork=yes', 'RestrictAddressFamilies=AF_UNIX',
                    'NoNewPrivileges=yes', 'CapabilityBoundingSet=\n', 'KillMode=control-group',
                    'ReadWritePaths=/var/lib/geophysics', 'EnvironmentFile=/etc/geophysics/api.env',
                    'RuntimeMaxSec=300', 'Restart=no', '--fd 3'):
        assert literal in service
    assert '[Install]' not in service + socket
    assert '/current/' not in service and 'ListenStream=0.' not in socket
    assert 'SocketMode=0660' in socket and 'SocketGroup=www-data' in socket


@pytest.mark.parametrize('token', ['', 'x' * 12, 'a' * 13, '../api', 'ABCDEF123456', 'a;reboot'])
def test_no_caller_selected_unit_target(release, token):
    with pytest.raises(ValueError, match='identity'):
        qualifier.unit_texts(release, token)


def test_template_drift_fails_before_mutation(release):
    path = release / 'source/deploy/service/geophysics-api.service'
    path.write_text(path.read_text().replace('After=geophysics-api.socket', 'After=unexpected.socket'))
    with pytest.raises(ValueError, match='template changed'):
        qualifier.unit_texts(release, 'a' * 12)


def properties():
    values = dict.fromkeys(qualifier.PROPERTIES, '0')
    values.update(User='geophysics', Group='geophysics', MainPID='123', ActiveState='active', SubState='running',
                  MemoryMax='536870912', MemorySwapMax='0', TasksMax='96', NoNewPrivileges='yes',
                  CPUQuotaPerSecUSec='1.500000s',
                  PrivateNetwork='yes', ProtectSystem='strict', ProtectHome='yes', ProtectControlGroups='yes',
                  CapabilityBoundingSet='', RestrictAddressFamilies='AF_UNIX', ReadWritePaths='/var/lib/geophysics')
    return values


def encode(values):
    return '\n'.join(f'{k}={v}' for k, v in values.items())


def test_closed_nonsecret_property_inventory():
    assert qualifier.read_properties(encode(properties())) == properties()
    for raw in (encode(properties()) + '\nEnvironment=secret', encode(properties()) + '\nUser=root',
                encode(properties()).replace('User=geophysics\n', ''), 'unexpected'):
        with pytest.raises(ValueError):
            qualifier.read_properties(raw)


@pytest.mark.parametrize('key,value', [('User', 'root'), ('MemoryMax', 'infinity'), ('MemorySwapMax', 'infinity'),
                                      ('CPUQuotaPerSecUSec', 'infinity'), ('CPUQuotaPerSecUSec', '2s'),
                                      ('NoNewPrivileges', 'no'), ('PrivateNetwork', 'no'),
                                      ('CapabilityBoundingSet', 'cap_setuid'), ('MainPID', '0'),
                                      ('RestrictAddressFamilies', 'AF_UNIX AF_INET')])
def test_actual_restrictions_must_match(key, value):
    values = properties()
    values[key] = value
    with pytest.raises(ValueError, match='restrictions'):
        qualifier.read_properties(encode(values))


def test_commands_never_emit_captured_error(monkeypatch, capsys):
    def fail(*args, **kwargs):
        assert kwargs['env'] == {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'}
        return subprocess.CompletedProcess(args[0], 1, b'test-secret-must-not-echo')
    monkeypatch.setattr(subprocess, 'run', fail)
    with pytest.raises(ValueError, match='command refused'):
        qualifier.Commands().run(['/usr/bin/systemctl', 'show', 'test'])
    captured = capsys.readouterr()
    assert not captured.out + captured.err


def test_deadline_and_command_output_bounds(monkeypatch):
    controller = qualifier.Commands()
    controller.deadline = 0
    with pytest.raises(ValueError, match='wall budget'):
        controller.run(['/usr/bin/systemctl'])
    monkeypatch.setattr(subprocess, 'run', lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, b'x' * 65537))
    with pytest.raises(ValueError, match='output bound'):
        qualifier.Commands().run(['/usr/bin/systemctl'])


def test_outside_linux_never_creates_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(qualifier.sys, 'platform', 'win32')
    with pytest.raises(ValueError, match='Linux'):
        qualifier.run(tmp_path, tmp_path, 'a' * 64, 'b' * 64, tmp_path / 'untouched', tmp_path, 'c' * 64)
    assert not (tmp_path / 'untouched').exists()


def state_manifests():
    source = {'app/migrations/env.py': {'bytes': 5, 'sha256': 'a' * 64},
              'app/migrations/versions/0003_processing_jobs.py': {'bytes': 6, 'sha256': 'b' * 64},
              'data-pipeline/ordinary.py': {'bytes': 7, 'sha256': 'c' * 64}}
    initial = {'source_revision': 'a' * 40, 'source': source}
    candidate = {'source_revision': 'b' * 40, 'source': dict(source)}
    candidate['source']['data-pipeline/ordinary.py'] = {'bytes': 8, 'sha256': 'd' * 64}
    bootstrap = {'schema': 'geophysics.service-bootstrap/v1', 'bootstrapped': True,
                 'source_revision': initial['source_revision'],
                 'database': {'schema_revision': qualifier.HEAD}}
    return bootstrap, initial, candidate


def test_same_source_binds_historical_bootstrap_without_reference():
    bootstrap, initial, _ = state_manifests()
    assert qualifier.state_compatibility(bootstrap, initial) == {
        'initial_source_revision': 'a' * 40, 'schema_revision': qualifier.HEAD,
        'migration_inventory_sha256': qualifier.migration_digest(initial)}


def test_later_candidate_requires_original_hash_and_full_reverification(tmp_path, monkeypatch):
    bootstrap, initial, candidate = state_manifests()
    with pytest.raises(ValueError, match='original bundle'):
        qualifier.state_compatibility(bootstrap, candidate)
    monkeypatch.setattr(qualifier, 'RELEASES', tmp_path)
    reference = tmp_path / 'initial'
    reference.mkdir()
    (reference / 'source').mkdir()
    (reference / 'web').mkdir()
    (reference / 'release.json').write_text(json.dumps(initial))
    sha = qualifier.file_digest(reference / 'release.json')['sha256']
    calls = []
    def verify(root):
        calls.append(root)
        return initial
    monkeypatch.setattr(qualifier, 'verify_bundle', verify)
    result = qualifier.state_compatibility(bootstrap, candidate, reference, sha)
    assert calls == [reference] and result['initial_source_revision'] == 'a' * 40
    assert result['original_bundle_sha256'] == sha
    with pytest.raises(ValueError, match='original bundle'):
        qualifier.state_compatibility(bootstrap, candidate, reference, '0' * 64)


@pytest.mark.parametrize('fault', ['changed', 'extra', 'missing', 'head', 'revision', 'failed'])
def test_compatibility_refuses_schema_changes_and_historical_relabel(tmp_path, monkeypatch, fault):
    bootstrap, initial, candidate = state_manifests()
    monkeypatch.setattr(qualifier, 'RELEASES', tmp_path)
    reference = tmp_path / 'initial'
    reference.mkdir()
    (reference / 'source').mkdir()
    (reference / 'web').mkdir()
    (reference / 'release.json').write_text(json.dumps(initial))
    sha = qualifier.file_digest(reference / 'release.json')['sha256']
    monkeypatch.setattr(qualifier, 'verify_bundle', lambda _: initial)
    path = 'app/migrations/versions/0003_processing_jobs.py'
    if fault == 'changed': candidate['source'][path] = {'bytes': 6, 'sha256': 'e' * 64}
    if fault == 'extra': candidate['source']['app/migrations/versions/0004.py'] = {'bytes': 2, 'sha256': 'f' * 64}
    if fault == 'missing': candidate['source'].pop(path)
    if fault == 'head': bootstrap['database']['schema_revision'] = '0002'
    if fault == 'revision': bootstrap['source_revision'] = 'c' * 40
    if fault == 'failed': bootstrap['bootstrapped'] = False
    with pytest.raises(ValueError):
        qualifier.state_compatibility(bootstrap, candidate, reference, sha)


def actual_database(tmp_path, monkeypatch, *, head=None, users=2):
    path = tmp_path / 'private.sqlite3'
    with sqlite3.connect(path) as connection:
        connection.execute('CREATE TABLE alembic_version(version_num TEXT)')
        connection.execute('INSERT INTO alembic_version VALUES (?)', (head or qualifier.HEAD,))
        connection.execute('CREATE TABLE "user"(is_active INTEGER, secret TEXT)')
        connection.executemany('INSERT INTO "user" VALUES (1, ?)', [('must-not-emit',)] * users)
    original = Path.stat
    def info(self, *args, **kwargs):
        actual = original(self, *args, **kwargs)
        if self == path:
            return SimpleNamespace(st_mode=0o100600, st_uid=123, st_gid=456)
        return actual
    # Real SQLite bytes/query, injected permission metadata only on Windows;
    # actual Linux permissions are separately measured on the candidate host.
    monkeypatch.setattr(Path, 'stat', info)
    monkeypatch.setattr(qualifier, 'no_links', lambda _: None)
    return path


def test_existing_plural_database_is_readonly_and_does_not_require_one_user(tmp_path, monkeypatch, capsys):
    path = actual_database(tmp_path, monkeypatch)
    before = path.read_bytes()
    result = qualifier.existing_database(path, 123, 456)
    assert result == {'schema_revision': qualifier.HEAD, 'active_accounts': 2,
                      'uid': 123, 'gid': 456, 'mode': '0600'}
    assert path.read_bytes() == before and not capsys.readouterr().out
    assert 'secret' not in json.dumps(result) and 'must-not-emit' not in json.dumps(result)


@pytest.mark.parametrize('fault', ['head', 'no_users', 'owner', 'mode', 'corrupt'])
def test_existing_database_refusal_preserves_bytes(tmp_path, monkeypatch, fault):
    path = actual_database(tmp_path, monkeypatch, head='0002' if fault == 'head' else None,
                           users=0 if fault == 'no_users' else 2)
    if fault == 'mode':
        monkeypatch.setattr(qualifier.stat, 'S_IMODE', lambda _: 0o644)
    if fault == 'corrupt': path.write_bytes(b'not a database')
    before = path.read_bytes()
    with pytest.raises((ValueError, sqlite3.DatabaseError)):
        qualifier.existing_database(path, 999 if fault == 'owner' else 123, 456)
    assert path.read_bytes() == before
