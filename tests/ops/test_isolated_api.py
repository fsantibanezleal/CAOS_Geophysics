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


def test_candidate_unit_uses_private_clone_environment(release, tmp_path, monkeypatch):
    monkeypatch.setattr(qualifier, 'EVIDENCE', tmp_path)
    evidence = tmp_path / 'api-qualification'
    evidence.mkdir()
    environment = evidence / 'api.env'
    environment.write_text('GEOPHYSICS_AUTH_MODE=local\n', encoding='ascii')
    _, service, _ = qualifier.unit_texts(release, '123456abcdef', environment)
    assert f'EnvironmentFile={environment.as_posix()}' in service
    assert 'EnvironmentFile=/etc/geophysics/api.env' not in service


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


def test_legacy_service_environment_is_valid_without_physical_binding(tmp_path, monkeypatch):
    path = tmp_path / 'api.env'
    path.write_text('GEOPHYSICS_DATA_DIR=/var/lib/geophysics\nGEOPHYSICS_DB_PATH=/var/lib/geophysics/api.sqlite3\n')
    if sys.platform == 'linux':
        path.chmod(0o600)
        assert qualifier.service_environment(path, 0 if __import__('os').geteuid() == 0 else path.stat().st_uid)
    else:
        pytest.skip('actual root-owned environment metadata requires Linux')
    assert qualifier.validate_physical_binding(tmp_path, {'api': {}, 'worker': {}}, 0) is None


@pytest.mark.skipif(sys.platform != 'linux', reason='physical lock identity requires POSIX')
def test_bound_physical_state_checks_candidate_digest_registry_and_locks(tmp_path, monkeypatch):
    import hashlib
    import os
    state = tmp_path / 'state'
    state.mkdir(mode=0o700)
    state.chmod(0o700)
    monkeypatch.setattr(qualifier, 'STATE', state)
    monkeypatch.setattr(qualifier, 'dedicated_identity', lambda: (os.getuid(), os.getgid()))
    release = tmp_path / 'candidate'
    release.mkdir()
    release_manifest = {'schema': 'geophysics.service-release/v1', 'source_revision': 'a' * 40,
                        'qualification_only': True, 'full_release_accepted': False, 'source': {}, 'web': {}}
    release_raw = json.dumps(release_manifest, sort_keys=True, separators=(',', ':')).encode()
    release_digest = hashlib.sha256(release_raw).hexdigest()
    registry_value = {'schema': 'geophysics.physical-operator-binding/v1',
                      'release_manifest_sha256': release_digest, 'source_policy_sha256': 'b' * 64,
                      'approved_manifests': {}, 'approved_installations': {}}
    registry_raw = json.dumps(registry_value, sort_keys=True, separators=(',', ':')).encode()
    digest = hashlib.sha256(registry_raw).hexdigest()
    (release / 'release.json').write_bytes(release_raw)
    binding_root = state / 'physical-operator-bindings'
    binding_root.mkdir(mode=0o700)
    registry = binding_root / (release.name + '.json')
    registry.write_bytes(registry_raw)
    registry.chmod(0o600)
    from app.operator_runtime import LOCKS
    for name, marker in LOCKS:
        lock = state / name
        lock.write_bytes(marker)
        lock.chmod(0o600)
    env = {'GEOPHYSICS_PHYSICAL_BINDING_PATH': registry.as_posix(),
           'GEOPHYSICS_PHYSICAL_BINDING_SHA256': digest}
    (release / 'release.json').write_bytes(release_raw)
    result = qualifier.validate_physical_binding(release, {'api': dict(env), 'worker': dict(env)}, os.getuid())
    assert result['sha256'] == digest and len(result['locks']) == 2
    registry.write_bytes(registry_raw + b' ')
    with pytest.raises(ValueError, match='hash'):
        qualifier.validate_physical_binding(release, {'api': dict(env), 'worker': dict(env)}, os.getuid())


def test_binding_environment_partial_or_different_fails():
    with pytest.raises(ValueError, match='identically'):
        qualifier.validate_physical_binding(Path('/unused'),
            {'api': {'GEOPHYSICS_PHYSICAL_BINDING_PATH': '/x'}, 'worker': {}}, 0)
    with pytest.raises(ValueError, match='differs'):
        qualifier.validate_physical_binding(Path('/unused'),
            {'api': {'GEOPHYSICS_PHYSICAL_BINDING_PATH': '/x', 'GEOPHYSICS_PHYSICAL_BINDING_SHA256': 'a' * 64},
             'worker': {'GEOPHYSICS_PHYSICAL_BINDING_PATH': '/y', 'GEOPHYSICS_PHYSICAL_BINDING_SHA256': 'a' * 64}}, 0)


def test_rollback_restores_and_selects_previous_release_environment(tmp_path):
    import os
    if sys.platform != 'linux':
        pytest.skip('root-owned release environment metadata requires Linux')
    root = tmp_path / 'etc-geophysics'
    old = root / 'releases' / 'old-release'
    candidate = root / 'releases' / 'candidate-release'
    old.mkdir(parents=True, mode=0o700)
    candidate.mkdir(parents=True, mode=0o700)
    old.chmod(0o700)
    candidate.chmod(0o700)
    previous = {}
    for name in ('api.env', 'worker.env'):
        previous[name] = (f'GEOPHYSICS_DATA_DIR=/var/lib/geophysics\n'
                          f'GEOPHYSICS_PHYSICAL_BINDING_PATH=/var/lib/geophysics/physical-operator-bindings/old-release.json\n'
                          f'GEOPHYSICS_PHYSICAL_BINDING_SHA256={"a" * 64}\n').encode()
        newer = previous[name].replace(b'old-release', b'candidate-release').replace(b'a' * 64, b'b' * 64)
        (old / name).write_bytes(previous[name])
        (candidate / name).write_bytes(newer)
        (old / name).chmod(0o600)
        (candidate / name).chmod(0o600)
        (root / name).write_bytes(previous[name])
        (root / name).chmod(0o600)
    values, hashes = qualifier.release_environment_selection(root, 'old-release', os.getuid())
    assert values['api']['GEOPHYSICS_PHYSICAL_BINDING_SHA256'] == 'a' * 64
    assert qualifier.validate_active_environment_selection(root, 'old-release', os.getuid()) == hashes
    snapshots = {name: (root / name).read_bytes() for name in ('api.env', 'worker.env')}
    for name in snapshots:
        (root / name).write_bytes((candidate / name).read_bytes())
    with pytest.raises(ValueError, match='active release selection'):
        qualifier.validate_active_environment_selection(root, 'old-release', os.getuid())
    for name, raw in snapshots.items():
        (root / name).write_bytes(raw)
    assert qualifier.validate_active_environment_selection(root, 'old-release', os.getuid()) == hashes

    activation = (ROOT / 'deploy/activate-service.sh').read_text(encoding='utf-8')
    rollback = activation[activation.index('rollback() {'):activation.index('trap rollback ERR')]
    assert 'install -o root -g root -m 0600 "$state/previous.api.env" /etc/geophysics/api.env' in rollback
    assert 'install -o root -g root -m 0600 "$state/previous.worker.env" /etc/geophysics/worker.env' in rollback
    assert rollback.index('previous.api.env') < rollback.index('systemctl start geophysics-api.socket')
    assert 'rollback_env_restored" == true' in rollback
    assert 'install -o root -g root -m 0600 "$candidate_env_dir/api.env" /etc/geophysics/api.env' in activation
    candidate_install = 'install -o root -g root -m 0600 "$candidate_env_dir/api.env" /etc/geophysics/api.env'
    assert activation.index('environment_switched=true') < activation.index(candidate_install)


def test_qualification_emits_activation_environment_hash_contract(tmp_path):
    import hashlib
    candidate = tmp_path / 'release'
    candidate.mkdir()
    expected = {}
    for name in ('api.env', 'worker.env'):
        raw = f'GEOPHYSICS_DATA_DIR=/var/lib/geophysics\n{ name }=candidate\n'.encode()
        (candidate / name).write_bytes(raw)
        expected[name] = hashlib.sha256(raw).hexdigest()
    assert qualifier.service_environment_hashes(candidate) == expected
    activation = (ROOT / 'deploy/activate-service.sh').read_text(encoding='utf-8')
    assert "admission.get('service_environment_hashes') != environment_hashes" in activation


def test_release_staging_is_explicit_and_does_not_offer_active_env_overwrite():
    import inspect
    source = inspect.getsource(qualifier.stage_release_environment)
    assert 'cannot stage environments for the active release' in source
    assert 'os.rename(temporary, final)' in source
    assert "never changes active globals" in source
    assert 'require_service_state(STATE, identity)' in source
    assert 'for path in (STATE, CONFIG, CONFIG /' not in source


def test_private_service_state_is_checked_against_service_identity(tmp_path, monkeypatch):
    state = tmp_path / 'state'
    state.mkdir()
    info = state.stat()
    monkeypatch.setattr(qualifier.stat, 'S_IMODE', lambda _mode: 0o700)
    qualifier.require_service_state(state, (info.st_uid, info.st_gid))
    with pytest.raises(ValueError, match='ownership or mode'):
        qualifier.require_service_state(state, (info.st_uid + 1, info.st_gid))
    monkeypatch.setattr(qualifier.stat, 'S_IMODE', lambda _mode: 0o755)
    with pytest.raises(ValueError, match='ownership or mode'):
        qualifier.require_service_state(state, (info.st_uid, info.st_gid))


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
              'app/migrations/versions/0001_api_foundation.py': {'bytes': 6, 'sha256': '1' * 64},
              'app/migrations/versions/0002_private_storage_permission.py': {'bytes': 6, 'sha256': '2' * 64},
              'app/migrations/versions/0003_processing_jobs.py': {'bytes': 6, 'sha256': '3' * 64},
              'data-pipeline/ordinary.py': {'bytes': 7, 'sha256': 'c' * 64}}
    initial = {'source_revision': 'a' * 40, 'source': source}
    candidate = {'source_revision': 'b' * 40, 'source': dict(source)}
    candidate['source']['app/migrations/versions/0004_waveform_artifacts.py'] = {
        'bytes': 36, 'sha256': qualifier.FORWARD_MIGRATION_SHA256}
    candidate['source']['data-pipeline/ordinary.py'] = {'bytes': 8, 'sha256': 'd' * 64}
    bootstrap = {'schema': 'geophysics.service-bootstrap/v1', 'bootstrapped': True,
                 'source_revision': initial['source_revision'],
                 'database': {'schema_revision': qualifier.LEGACY_HEAD}}
    return bootstrap, initial, candidate


def test_same_source_binds_historical_bootstrap_without_reference():
    _, _, candidate = state_manifests()
    bootstrap = {'schema': 'geophysics.service-bootstrap/v1', 'bootstrapped': True,
                 'source_revision': candidate['source_revision'],
                 'database': {'schema_revision': qualifier.HEAD}}
    result = qualifier.state_compatibility(bootstrap, candidate)
    assert result['database_revision_before'] == result['database_revision_after'] == qualifier.HEAD
    assert result['migration_compatibility']['migration'] is None
    assert result['migration_inventory_sha256'] == qualifier.migration_digest(candidate)


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
    assert result['migration_compatibility']['from'] == qualifier.LEGACY_HEAD
    assert result['migration_compatibility']['to'] == qualifier.HEAD
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
    if fault == 'extra': candidate['source']['app/migrations/versions/0005.py'] = {'bytes': 2, 'sha256': 'f' * 64}
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


def test_qualification_clone_is_independent_and_preserves_live_database(tmp_path, monkeypatch):
    source = tmp_path / 'state'
    source.mkdir()
    monkeypatch.setattr(qualifier, 'STATE', source)
    monkeypatch.setattr(qualifier.os, 'chown', lambda *_args: None, raising=False)
    (source / 'projects/owner/project').mkdir(parents=True)
    (source / 'projects/owner/project/raw.bin').write_bytes(b'original raw bytes')
    (source / '.staging').mkdir()
    database = source / 'api.sqlite3'
    with sqlite3.connect(database) as connection:
        connection.execute('CREATE TABLE alembic_version(version_num TEXT)')
        connection.execute('INSERT INTO alembic_version VALUES (?)', (qualifier.LEGACY_HEAD,))
        connection.execute('CREATE TABLE sample(value TEXT)')
        connection.execute('INSERT INTO sample VALUES (\'live\')')
    target = source / '.qualification-123456abcdef'
    info = database.stat()
    result = qualifier.clone_private_state(source, target, info.st_uid, info.st_gid)
    with sqlite3.connect(target / 'api.sqlite3') as clone:
        clone.execute('UPDATE sample SET value=\'candidate\'')
        assert clone.execute('SELECT version_num FROM alembic_version').fetchone() == (qualifier.LEGACY_HEAD,)
    with sqlite3.connect(database) as original:
        assert original.execute('SELECT value FROM sample').fetchone() == ('live',)
    original_file = source / 'projects/owner/project/raw.bin'
    clone_file = target / 'projects/owner/project/raw.bin'
    assert clone_file.read_bytes() == original_file.read_bytes()
    assert not clone_file.samefile(original_file)
    assert result['source_revision'] == qualifier.LEGACY_HEAD
    assert result['clone_database']['sha256']
