"""Actual Linux candidate socket qualification, never production activation."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import sqlite3
import stat
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bootstrap_service_state import (  # noqa: E402
    CONFIG, HEAD, STATE, BootstrapRunner, bounded_private_json, credentials, dedicated_identity,
    exclusive_private_file, operator_directory, verify_candidate,
    physical_binding,
)
from prepare_service_release import file_digest, no_links, verify_bundle  # noqa: E402
from stage_service_runtime import EVIDENCE, RELEASES, exclusive_json  # noqa: E402
from verify_local_service import verify  # noqa: E402

UNIT_ROOT = Path('/run/systemd/system')
RUN = Path('/run')
SECONDS = 180
MAX_QUALIFICATION_STATE_BYTES = 2 * 1024**3
MAX_QUALIFICATION_STATE_ENTRIES = 100000
LEGACY_HEAD = '0003_processing_jobs'
FORWARD_MIGRATION = 'app/migrations/versions/0004_waveform_artifacts.py'
FORWARD_MIGRATION_SHA256 = 'c08dde26f55aea87af39e9228013f23a6823de1cf54ba9163d164b0ebfb49bc0'
PROPERTIES = ('User', 'Group', 'MainPID', 'ActiveState', 'SubState', 'MemoryMax', 'MemorySwapMax',
              'MemoryCurrent', 'MemoryPeak', 'TasksMax', 'CPUQuotaPerSecUSec', 'NoNewPrivileges',
              'PrivateNetwork', 'ProtectSystem', 'ProtectHome', 'ProtectControlGroups',
              'CapabilityBoundingSet', 'RestrictAddressFamilies', 'ReadWritePaths')


def service_environment(path: Path, uid: int) -> dict[str, str]:
    no_links(path)
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o600:
        raise ValueError('private service environment differs')
    raw = path.read_bytes()
    if len(raw) > 8192:
        raise ValueError('service environment exceeds bound')
    values = {}
    for line in raw.decode('ascii').splitlines():
        if not re.fullmatch(r'GEOPHYSICS_[A-Z0-9_]+=[A-Za-z0-9_./:-]+', line):
            raise ValueError('service environment must use simple literal values')
        key, value = line.split('=', 1)
        if key in values:
            raise ValueError('duplicate service environment key')
        values[key] = value
    return values


def release_environment_selection(root: Path, release_id: str, uid: int) -> tuple[dict, dict]:
    if re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', release_id) is None:
        raise ValueError('invalid release environment identity')
    directory = root / 'releases' / release_id
    no_links(directory)
    info = directory.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError('release environment directory differs')
    values, hashes = {}, {}
    for name in ('api.env', 'worker.env'):
        path = directory / name
        values[name.split('.')[0]] = service_environment(path, uid)
        hashes[name] = file_digest(path)
    return values, hashes


def validate_active_environment_selection(root: Path, release_id: str, uid: int) -> dict:
    _, selected = release_environment_selection(root, release_id, uid)
    current = service_environment_hashes(root)
    if current != {name: value['sha256'] for name, value in selected.items()}:
        raise ValueError('global service environments do not match active release selection')
    return selected


def service_environment_hashes(directory: Path) -> dict[str, str]:
    return {name: file_digest(directory / name)['sha256'] for name in ('api.env', 'worker.env')}


def require_service_state(path: Path, identity: tuple[int, int]) -> None:
    """Check the private state root against its dedicated service identity."""
    no_links(path)
    info = path.stat()
    if (not stat.S_ISDIR(info.st_mode)
            or (info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode)) != (*identity, 0o700)):
        raise ValueError('private service state ownership or mode differs')


def stage_release_environment(release: Path, bundle_sha256: str, registry_source: Path | None = None,
                              registry_sha256: str | None = None) -> dict:
    """Stage immutable candidate envs and optional binding; never changes active globals."""
    if sys.platform != 'linux' or os.geteuid() != 0:
        raise ValueError('Linux root operator required')
    if release.parent != RELEASES or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', release.name) is None:
        raise ValueError('fixed candidate release path required')
    verify_bundle(release)
    if not re.fullmatch(r'[0-9a-f]{64}', bundle_sha256) or file_digest(release / 'release.json')['sha256'] != bundle_sha256:
        raise ValueError('candidate release digest differs')
    for path in (CONFIG, CONFIG / 'releases'):
        no_links(path)
        info = path.stat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError('existing private service state required')
    identity = dedicated_identity()
    if identity is None:
        raise ValueError('dedicated service identity required')
    uid, gid = identity
    require_service_state(STATE, identity)
    current = RELEASES.parent / 'current'
    active_release = current.resolve(strict=True)
    if active_release.parent != RELEASES:
        raise ValueError('active release path differs')
    if active_release == release.resolve(strict=True):
        raise ValueError('cannot stage environments for the active release')
    active_id = active_release.name
    source_dir = CONFIG / 'releases' / active_id
    base, _ = release_environment_selection(CONFIG, active_id, 0)
    if validate_active_environment_selection(CONFIG, active_id, 0) != {
            name: file_digest(source_dir / name) for name in ('api.env', 'worker.env')}:
        raise ValueError('active global environment changed')
    api, worker = dict(base['api']), dict(base['worker'])
    required_api = {'GEOPHYSICS_DATA_DIR': STATE.as_posix(),
                    'GEOPHYSICS_DB_PATH': (STATE / 'api.sqlite3').as_posix(),
                    'GEOPHYSICS_PUBLIC_ORIGIN': 'https://geophysics.ml.fasl-work.com',
                    'GEOPHYSICS_AUTH_MODE': 'local'}
    if any(api.get(key) != value for key, value in required_api.items()) or not re.fullmatch(
            r'[0-9a-f]{64}', api.get('GEOPHYSICS_AUTH_SECRET', '')):
        raise ValueError('active API environment profile differs')
    if any(worker.get(key) != value for key, value in required_api.items() if key not in {
            'GEOPHYSICS_PUBLIC_ORIGIN', 'GEOPHYSICS_AUTH_MODE'}):
        raise ValueError('active worker environment profile differs')
    for values in (api, worker):
        values.pop('GEOPHYSICS_PHYSICAL_BINDING_PATH', None)
        values.pop('GEOPHYSICS_PHYSICAL_BINDING_SHA256', None)
    binding_record = None
    if registry_source is not None or registry_sha256 is not None:
        registry_raw, binding_path, binding_digest, release_digest = physical_binding(
            registry_source, registry_sha256, release, STATE)
        if binding_path is None:
            raise ValueError('physical registry and digest must be supplied together')
        binding_dir = STATE / 'physical-operator-bindings'
        if not binding_dir.exists():
            binding_dir.mkdir(mode=0o700)
            os.chown(binding_dir, uid, gid)
        info = binding_dir.stat()
        if (not stat.S_ISDIR(info.st_mode) or (info.st_uid, info.st_gid) != (uid, gid)
                or stat.S_IMODE(info.st_mode) != 0o700):
            raise ValueError('physical registry directory ownership/mode differs')
        target = Path(binding_path)
        if target.exists():
            no_links(target)
            target_info = target.stat()
            if ((target_info.st_uid, target_info.st_gid, stat.S_IMODE(target_info.st_mode),
                 target_info.st_nlink) != (uid, gid, 0o600, 1) or target.read_bytes() != registry_raw):
                raise ValueError('existing candidate physical registry differs')
        else:
            exclusive_private_file(target, registry_raw, uid, gid)
        for values in (api, worker):
            values['GEOPHYSICS_PHYSICAL_BINDING_PATH'] = binding_path
            values['GEOPHYSICS_PHYSICAL_BINDING_SHA256'] = binding_digest
        binding_record = {'path': binding_path, 'sha256': binding_digest,
                          'release_manifest_sha256': release_digest}
    api_raw = ''.join(f'{key}={value}\n' for key, value in sorted(api.items())).encode('ascii')
    worker_raw = ''.join(f'{key}={value}\n' for key, value in sorted(worker.items())).encode('ascii')
    final = CONFIG / 'releases' / release.name
    if final.exists():
        _, existing = release_environment_selection(CONFIG, release.name, 0)
        expected = {'api.env': hashlib.sha256(api_raw).hexdigest(),
                    'worker.env': hashlib.sha256(worker_raw).hexdigest()}
        if {key: value['sha256'] for key, value in existing.items()} != expected:
            raise ValueError('candidate release environments already exist with different content')
        return {'release_id': release.name, 'service_environment_hashes': expected,
                'physical_binding': binding_record, 'created': False}
    temporary = CONFIG / 'releases' / ('.staging-' + release.name + '-' + secrets.token_hex(8))
    temporary.mkdir(mode=0o700)
    try:
        exclusive_private_file(temporary / 'api.env', api_raw)
        exclusive_private_file(temporary / 'worker.env', worker_raw)
        os.rename(temporary, final)
        descriptor = os.open(final.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except Exception:
        # Retain the exact private staging directory for operator inspection.
        raise
    return {'release_id': release.name,
        'service_environment_hashes': {'api.env': hashlib.sha256(api_raw).hexdigest(),
                                       'worker.env': hashlib.sha256(worker_raw).hexdigest()},
            'physical_binding': binding_record, 'created': True}


def validate_physical_binding(release: Path, environments: dict[str, dict[str, str]], uid: int) -> dict | None:
    names = ('GEOPHYSICS_PHYSICAL_BINDING_PATH', 'GEOPHYSICS_PHYSICAL_BINDING_SHA256')
    api, worker = environments['api'], environments['worker']
    configured = [tuple(key in values for key in names) for values in (api, worker)]
    if configured == [(False, False), (False, False)]:
        return None
    if configured != [(True, True), (True, True)]:
        raise ValueError('physical binding must be identically present in both service environments')
    binding = tuple(api[key] for key in names)
    if tuple(worker[key] for key in names) != binding:
        raise ValueError('physical binding environment differs between API and worker')
    expected_path, expected_digest = binding
    expected_file = (STATE / 'physical-operator-bindings' / (release.name + '.json')).as_posix()
    if expected_path != expected_file or not re.fullmatch(r'[0-9a-f]{64}', expected_digest):
        raise ValueError('physical binding path or digest is not canonical')
    path = STATE / 'physical-operator-bindings' / (release.name + '.json')
    binding_directory = path.parent
    no_links(binding_directory)
    directory_info = binding_directory.stat()
    if (not stat.S_ISDIR(directory_info.st_mode) or directory_info.st_uid != uid
            or stat.S_IMODE(directory_info.st_mode) != 0o700):
        raise ValueError('physical binding directory ownership or mode differs')
    no_links(path)
    info = path.stat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != uid or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_nlink != 1):
        raise ValueError('physical binding registry ownership or mode differs')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_digest:
        raise ValueError('physical binding registry hash differs')
    from app.operator_runtime import _check_registry, _strict_json, LOCKS
    registry = _strict_json(raw, cap=4 * 1024 * 1024, code='operator_registry')
    release_raw = (release / 'release.json').read_bytes()
    if hashlib.sha256(release_raw).hexdigest() != expected_digest_for_release(registry):
        raise ValueError('physical binding does not name candidate release.json')
    _check_registry(registry, release_raw)
    locks = {}
    directory = STATE.stat()
    if (directory.st_uid, directory.st_gid, stat.S_IMODE(directory.st_mode)) != (*dedicated_identity(), 0o700):
        raise ValueError('physical lock root ownership or mode differs')
    for name, marker in LOCKS:
        lock = STATE / name
        no_links(lock)
        lock_info = lock.stat()
        content = lock.read_bytes()
        if (not stat.S_ISREG(lock_info.st_mode) or lock_info.st_uid != uid or lock_info.st_nlink != 1
                or stat.S_IMODE(lock_info.st_mode) != 0o600 or content != marker):
            raise ValueError('physical lock ownership, mode or marker differs')
        locks[name] = {'sha256': hashlib.sha256(content).hexdigest(), 'uid': uid, 'mode': '0600'}
    return {'path': expected_path, 'sha256': expected_digest,
            'release_manifest_sha256': registry['release_manifest_sha256'], 'locks': locks}


def expected_digest_for_release(registry: dict) -> str:
    value = registry.get('release_manifest_sha256')
    if not isinstance(value, str) or re.fullmatch(r'[0-9a-f]{64}', value) is None:
        raise ValueError('physical binding release digest invalid')
    return value


def qualification_account(name: str) -> dict:
    if not re.fullmatch(r'geophysics-qualification-[0-9a-f]{12}', name):
        raise ValueError('invalid owned qualification name')
    # FastAPI Users EmailStr refuses reserved .invalid domains. This identifier
    # is syntactically valid only; no mailbox/DNS verification or SMTP is invoked.
    return {'username': 'qualification.' + name.rsplit('-', 1)[-1] + '@geophysics.ml.fasl-work.com',
            'password': secrets.token_urlsafe(32)}


def unit_texts(release: Path, token: str, environment_file: Path | None = None) -> tuple[str, str, str]:
    if not re.fullmatch(r'[0-9a-f]{12}', token):
        raise ValueError('invalid qualification identity')
    if release.parent != RELEASES or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', release.name):
        raise ValueError('unexpected candidate path')
    name = 'geophysics-qualification-' + token
    socket_path = RUN / (name + '.sock')
    api = (release / 'source/deploy/service/geophysics-api.service').read_text(encoding='utf-8')
    sock = (release / 'source/deploy/service/geophysics-api.socket').read_text(encoding='utf-8')
    if (api.count('/var/www/geophysics.ml.fasl-work.com/current') != 2
            or api.count('geophysics-api.socket') != 2
            or sock.count('/run/geophysics-api/api.sock') != 1
            or api.count('EnvironmentFile=/etc/geophysics/api.env') != 1):
        raise ValueError('reviewed production template changed')
    api = api.replace('/var/www/geophysics.ml.fasl-work.com/current', release.as_posix())
    api = api.replace('geophysics-api.socket', name + '.socket')
    if environment_file is not None:
        if (not environment_file.is_absolute() or '..' in environment_file.parts
                or not environment_file.as_posix().startswith(EVIDENCE.as_posix() + '/')):
            raise ValueError('qualification environment path differs')
        api = api.replace('EnvironmentFile=/etc/geophysics/api.env',
                          'EnvironmentFile=' + environment_file.as_posix())
    api = api.replace('[Install]\nWantedBy=multi-user.target', '')
    api = api.replace('Restart=on-failure', 'Restart=no\nRuntimeMaxSec=300')
    sock = sock.replace('/run/geophysics-api/api.sock', socket_path.as_posix())
    sock = sock.replace('[Install]\nWantedBy=sockets.target', '')
    if '[Install]' in api or '[Install]' in sock or '/current/' in api:
        raise ValueError('qualification must not enable or use current')
    return name, api, sock


class Commands:
    def __init__(self):
        self.deadline = time.monotonic() + SECONDS
        self.captured = 0

    def run(self, args: list[str], *, shutdown: bool = False) -> str:
        remaining = 30 if shutdown else min(30, self.deadline - time.monotonic())
        if remaining <= 0:
            raise ValueError('qualification wall budget exhausted')
        # Fixed system tools produce bounded show/verify output; no journal/env/log retrieval.
        result = subprocess.run(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=remaining, check=False,
                                env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'})
        self.captured += len(result.stdout)
        if self.captured > 65536:
            raise ValueError('qualification command output bound exceeded')
        if result.returncode:
            raise ValueError('qualification command refused')
        return result.stdout.decode('utf-8', errors='strict').strip()


def read_properties(raw: str) -> dict[str, str]:
    result = {}
    for line in raw.splitlines():
        key, separator, value = line.partition('=')
        if not separator or key not in PROPERTIES or key in result:
            raise ValueError('unexpected service property')
        result[key] = value
    if set(result) != set(PROPERTIES):
        raise ValueError('incomplete service property inventory')
    expected = {'User': 'geophysics', 'Group': 'geophysics', 'ActiveState': 'active',
                'SubState': 'running', 'MemoryMax': '536870912', 'MemorySwapMax': '0',
                'TasksMax': '96', 'CPUQuotaPerSecUSec': '1.500000s',
                'NoNewPrivileges': 'yes', 'PrivateNetwork': 'yes',
                'ProtectSystem': 'strict', 'ProtectHome': 'yes', 'ProtectControlGroups': 'yes',
                'CapabilityBoundingSet': '', 'RestrictAddressFamilies': 'AF_UNIX',
                'ReadWritePaths': '/var/lib/geophysics'}
    if any(result[key] != value for key, value in expected.items()) or not result['MainPID'].isdigit() or int(result['MainPID']) <= 0:
        raise ValueError('actual service restrictions differ')
    return result


def migration_digest(manifest: dict) -> str:
    selected = {key: value for key, value in manifest['source'].items()
                if key.startswith('app/migrations/versions/')}
    if not selected or len(selected) > 128:
        raise ValueError('committed migration inventory incomplete')
    return hashlib.sha256(json.dumps(selected, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode('ascii')).hexdigest()


def state_compatibility(bootstrap: dict, candidate: dict, original_bundle: Path | None = None,
                        original_sha: str | None = None) -> dict:
    previous_revision = bootstrap.get('database', {}).get('schema_revision')
    if (bootstrap.get('schema') != 'geophysics.service-bootstrap/v1'
            or bootstrap.get('bootstrapped') is not True
            or previous_revision not in {LEGACY_HEAD, HEAD}):
        raise ValueError('initial bootstrap schema/state differs')
    original = candidate
    if (original_bundle is None) != (original_sha is None):
        raise ValueError('explicit original bundle and digest required together')
    if original_bundle is not None:
        if (original_bundle.parent != RELEASES or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', original_bundle.name)
                or not re.fullmatch(r'[0-9a-f]{64}', original_sha)
                or file_digest(original_bundle / 'release.json')['sha256'] != original_sha):
            raise ValueError('original bundle identity differs')
        from stage_service_runtime import root_owned_tree
        if sys.platform == 'linux':
            operator_directory(original_bundle)
            for path in ('release.json', 'source', 'web'):
                root_owned_tree(original_bundle / path)
        original = verify_bundle(original_bundle)
    elif bootstrap.get('source_revision') != candidate['source_revision']:
        raise ValueError('later candidate requires explicit original bundle')
    if original['source_revision'] != bootstrap.get('source_revision'):
        raise ValueError('historical initial source revision differs')
    old_migrations = {key: value for key, value in original['source'].items()
                      if key.startswith('app/migrations/versions/')}
    new_migrations = {key: value for key, value in candidate['source'].items()
                      if key.startswith('app/migrations/versions/')}
    if (not old_migrations or len(old_migrations) > 128
            or 'app/migrations/versions/' + LEGACY_HEAD + '.py' not in old_migrations):
        raise ValueError('historical migration inventory incomplete')
    if any(new_migrations.get(name) != value for name, value in old_migrations.items()):
        raise ValueError('historical migration source changed')
    if 'app/migrations/versions/' + HEAD + '.py' not in new_migrations:
        raise ValueError('candidate migration head is absent')
    added = set(new_migrations) - set(old_migrations)
    if previous_revision == LEGACY_HEAD:
        if (added != {FORWARD_MIGRATION}
                or new_migrations[FORWARD_MIGRATION].get('sha256') != FORWARD_MIGRATION_SHA256):
            raise ValueError('migration compatibility changed; separate reviewed contract required')
        contract = {'from': LEGACY_HEAD, 'to': HEAD, 'migration': FORWARD_MIGRATION,
                    'sha256': FORWARD_MIGRATION_SHA256,
                    'operations': ['create waveform_dataset_sources', 'create waveform_result_artifacts'],
                    'data_rewrite': False, 'downgrade': 'forbidden'}
    else:
        if added or migration_digest(original) != migration_digest(candidate):
            raise ValueError('migration compatibility changed; separate reviewed contract required')
        contract = {'from': HEAD, 'to': HEAD, 'migration': None, 'data_rewrite': False,
                    'downgrade': 'forbidden'}
    result = {'initial_source_revision': original['source_revision'],
              'database_revision_before': previous_revision,
              'database_revision_after': HEAD, 'migration_inventory_sha256': migration_digest(candidate),
              'migration_compatibility': contract}
    if original_sha is not None:
        result['original_bundle_sha256'] = original_sha
    return result


def existing_database(path: Path, uid: int, gid: int, *, expected_revision: str = HEAD) -> dict:
    no_links(path)
    info = path.stat()
    if (not stat.S_ISREG(info.st_mode) or (info.st_uid, info.st_gid) != (uid, gid)
            or stat.S_IMODE(info.st_mode) != 0o600):
        raise ValueError('existing database ownership/mode differs')
    deadline = time.monotonic() + 5
    with sqlite3.connect('file:' + path.as_posix() + '?mode=ro', uri=True, timeout=2) as connection:
        connection.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
        connection.execute('PRAGMA query_only=ON')
        if connection.execute('PRAGMA quick_check').fetchall() != [('ok',)]:
            raise ValueError('existing database integrity failed')
        revision = connection.execute('SELECT version_num FROM alembic_version').fetchall()
        if revision != [(expected_revision,)]:
            raise ValueError('existing database schema differs')
        count = connection.execute('SELECT COUNT(*) FROM "user" WHERE is_active=1').fetchone()[0]
        if count < 1:
            raise ValueError('existing database requires an active internal account')
    return {'schema_revision': expected_revision, 'active_accounts': count,
            'uid': uid, 'gid': gid, 'mode': '0600'}


def _copy_tree(source: Path, target: Path, uid: int, gid: int, budget: dict) -> None:
    no_links(source)
    info = source.lstat()
    budget['entries'] += 1
    if budget['entries'] > MAX_QUALIFICATION_STATE_ENTRIES or not stat.S_ISDIR(info.st_mode):
        raise ValueError('qualification state tree entry invalid')
    target.mkdir(mode=0o700)
    os.chown(target, uid, gid)
    with os.scandir(source) as scan:
        for entry in sorted(scan, key=lambda item: item.name):
            src, dst = Path(entry.path), target / entry.name
            no_links(src)
            member = src.lstat()
            if stat.S_ISDIR(member.st_mode):
                _copy_tree(src, dst, uid, gid, budget)
            elif stat.S_ISREG(member.st_mode):
                budget['entries'] += 1
                budget['bytes'] += member.st_size
                if (budget['entries'] > MAX_QUALIFICATION_STATE_ENTRIES
                        or budget['bytes'] > MAX_QUALIFICATION_STATE_BYTES):
                    raise ValueError('qualification state copy exceeds bound')
                shutil.copyfile(src, dst, follow_symlinks=False)
                os.chmod(dst, 0o600)
                os.chown(dst, uid, gid)
            else:
                raise ValueError('qualification state contains unsupported filesystem entry')


def clone_private_state(source: Path, target: Path, uid: int, gid: int) -> dict:
    """Make an independent bounded copy; all migration/API writes stay off the live state."""
    if (source != STATE or target.parent != STATE
            or re.fullmatch(r'\.qualification-[0-9a-f]{12}', target.name) is None):
        raise ValueError('qualification clone path is not canonical')
    no_links(source)
    no_links(target)
    if target.exists():
        raise ValueError('existing qualification clone retained')
    source_db = source / 'api.sqlite3'
    no_links(source_db)
    source_info = source_db.stat()
    if (not stat.S_ISREG(source_info.st_mode) or source_info.st_size > MAX_QUALIFICATION_STATE_BYTES
            or (source_info.st_uid, source_info.st_gid) != (uid, gid)):
        raise ValueError('source database ownership differs')
    target.mkdir(mode=0o700)
    os.chown(target, uid, gid)
    budget = {'entries': 1, 'bytes': 0}
    with os.scandir(source) as scan:
        for entry in sorted(scan, key=lambda item: item.name):
            if entry.name == target.name:
                continue
            src = Path(entry.path)
            no_links(src)
            if entry.name in {'api.sqlite3', 'api.sqlite3-wal', 'api.sqlite3-shm'}:
                if entry.name != 'api.sqlite3' and not stat.S_ISREG(src.lstat().st_mode):
                    raise ValueError('SQLite sidecar type differs')
                continue  # SQLite backup below includes committed WAL frames.
            dst = target / entry.name
            if stat.S_ISDIR(src.lstat().st_mode):
                _copy_tree(src, dst, uid, gid, budget)
            else:
                raise ValueError('private state root contains an unsupported direct file')
    destination_db = target / 'api.sqlite3'
    source_uri = 'file:' + source_db.as_posix() + '?mode=ro'
    with sqlite3.connect(source_uri, uri=True, timeout=5) as original:
        original.execute('PRAGMA query_only=ON')
        expected_database_bytes = (original.execute('PRAGMA page_count').fetchone()[0]
                                    * original.execute('PRAGMA page_size').fetchone()[0])
        if budget['bytes'] + expected_database_bytes > MAX_QUALIFICATION_STATE_BYTES:
            raise ValueError('qualification state copy exceeds byte bound')
        with sqlite3.connect(destination_db) as clone:
            original.backup(clone, pages=256, sleep=0.05)
            if clone.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                raise ValueError('qualification database clone integrity failed')
            if clone.execute('PRAGMA foreign_key_check').fetchall():
                raise ValueError('qualification database clone foreign keys differ')
            if clone.execute('SELECT version_num FROM alembic_version').fetchall() != [(LEGACY_HEAD,)]:
                raise ValueError('qualification database clone schema differs')
    os.chmod(destination_db, 0o600)
    os.chown(destination_db, uid, gid)
    budget['bytes'] += destination_db.stat().st_size
    budget['entries'] += 1
    if budget['bytes'] > MAX_QUALIFICATION_STATE_BYTES:
        raise ValueError('qualification database clone exceeds byte bound')
    return {'path': target.as_posix(), 'source_database': file_digest(source_db),
            'clone_database': file_digest(destination_db), 'entries': budget['entries'],
            'copied_bytes': budget['bytes'], 'source_revision': LEGACY_HEAD}


def run(release: Path, receipt: Path, bundle_sha: str, runtime_sha: str, evidence: Path,
        bootstrap_receipt: Path, bootstrap_sha: str, owner_credentials: Path | None = None,
        original_bundle: Path | None = None, original_sha: str | None = None) -> dict:
    if sys.platform != 'linux' or os.geteuid() != 0:
        raise ValueError('Linux operator required')
    if release.parent != RELEASES or evidence.parent != EVIDENCE:
        raise ValueError('fixed application parent required')
    for parent in (RELEASES, EVIDENCE, UNIT_ROOT, RUN, CONFIG):
        operator_directory(parent)
    no_links(evidence)
    if evidence.exists():
        raise ValueError('existing evidence retained')
    current = RELEASES.parent / 'current'
    if current.resolve(strict=True) == release.resolve(strict=True):
        raise ValueError('active release cannot be qualified in parallel')
    import fcntl
    lock = os.open('/run/lock/geophysics-deploy.lock', os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(lock, 'wb') as handle:
        info = os.fstat(handle.fileno())
        if info.st_uid != 0 or not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
            raise ValueError('unexpected deployment lock')
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return _locked(release, receipt, bundle_sha, runtime_sha, evidence, current,
                       bootstrap_receipt, bootstrap_sha, owner_credentials, original_bundle, original_sha)


def _locked(release, receipt, bundle_sha, runtime_sha, evidence, current, bootstrap_receipt, bootstrap_sha,
            owner_credentials, original_bundle, original_sha):
    commands = Commands()
    initial_current = os.readlink(current)
    manifest = verify_candidate(release, receipt, bundle_sha, runtime_sha)
    if not re.fullmatch(r'[0-9a-f]{64}', bootstrap_sha) or file_digest(bootstrap_receipt)['sha256'] != bootstrap_sha:
        raise ValueError('bootstrap receipt changed')
    bootstrap = bounded_private_json(bootstrap_receipt)
    compatibility = state_compatibility(bootstrap, manifest, original_bundle, original_sha)
    identity = dedicated_identity()
    no_links(STATE)
    state = STATE.stat()
    if (identity is None or not stat.S_ISDIR(state.st_mode)
            or (state.st_uid, state.st_gid, stat.S_IMODE(state.st_mode)) != (*identity, 0o700)):
        raise ValueError('existing private identity/state required')
    candidate_config = CONFIG / 'releases' / release.name
    environment_values, environments = release_environment_selection(CONFIG, release.name, 0)
    if (bootstrap.get('release_id') == release.name
            and environments != bootstrap.get('release_environment_hashes')):
        raise ValueError('candidate release environment changed since bootstrap')
    active_release_id = Path(initial_current).name
    active_globals = validate_active_environment_selection(CONFIG, active_release_id, 0)
    sys.path.insert(0, str(release / 'source'))
    physical_binding = validate_physical_binding(release, environment_values, identity[0])
    bound_receipt = ({key: physical_binding[key] for key in ('path', 'sha256', 'release_manifest_sha256')}
                     if physical_binding is not None else None)
    if bootstrap.get('release_id') == release.name and bound_receipt != bootstrap.get('physical_binding'):
        raise ValueError('physical binding differs from immutable bootstrap receipt')
    for unit in ('geophysics-api.service', 'geophysics-api.socket', 'geophysics-worker.service'):
        status = commands.run(['/usr/bin/systemctl', 'show', unit, '--property=ActiveState', '--value'])
        if status not in ('inactive', 'failed', ''):
            raise ValueError('production writer active; parallel qualification refused')
    database = existing_database(STATE / 'api.sqlite3', *identity,
                                 expected_revision=compatibility['database_revision_before'])
    token = secrets.token_hex(6)
    name = 'geophysics-qualification-' + token
    qualification_state = STATE / ('.qualification-' + token)
    socket_path = RUN / (name + '.sock')
    paths = (UNIT_ROOT / (name + '.service'), UNIT_ROOT / (name + '.socket'))
    for path in (*paths, socket_path):
        no_links(path)
        if path.exists():
            raise ValueError('qualification target already exists')
    evidence.mkdir(mode=0o700)
    record = {'schema': 'geophysics.isolated-api/v1', 'source_revision': manifest['source_revision'],
              'qualifier_sha256': file_digest(Path(__file__))['sha256'], 'bundle_sha256': bundle_sha,
              'runtime_receipt_sha256': runtime_sha, 'created_at': datetime.now(timezone.utc).isoformat(),
              'bootstrap_receipt_sha256': bootstrap_sha,
              'state_compatibility': compatibility, 'existing_database': database,
              'initial_current': initial_current, 'environment_files': environments,
              'service_environment_hashes': service_environment_hashes(candidate_config),
              'active_environment_files': active_globals,
              'physical_binding': physical_binding,
              'unit_name': name, 'qualification_state': qualification_state.as_posix(),
              'transport_passed': False, 'stopped': False,
              'activated': False, 'host_admitted': False, 'full_release_accepted': False}
    started = False
    try:
        clone = clone_private_state(STATE, qualification_state, *identity)
        record['state_clone'] = clone
        migration_runner = BootstrapRunner(*identity, qualification_state)
        migration_runner.run('candidate-migration',
                             [str(release / '.venv/bin/python'), '-I', '-B', '-m', 'alembic',
                              '-c', 'app/alembic.ini', 'upgrade', HEAD], release / 'source')
        migrated_database = existing_database(qualification_state / 'api.sqlite3', *identity,
                                              expected_revision=HEAD)
        record['migration'] = {'compatibility': compatibility['migration_compatibility'],
                               'steps': migration_runner.steps, 'database': migrated_database,
                               'database_sha256': file_digest(qualification_state / 'api.sqlite3')['sha256']}
        api_values = dict(environment_values['api'])
        api_values['GEOPHYSICS_DATA_DIR'] = qualification_state.as_posix()
        api_values['GEOPHYSICS_DB_PATH'] = (qualification_state / 'api.sqlite3').as_posix()
        api_environment = evidence / 'api.env'
        exclusive_private_file(api_environment,
                               ''.join(f'{key}={value}\n' for key, value in sorted(api_values.items())).encode('ascii'))
        name, api, sock = unit_texts(release, token, api_environment)
        owner, other = None, None
        if owner_credentials is not None:
            owner = json.loads(credentials(bounded_private_json(owner_credentials)))
            other = qualification_account(name)
            exclusive_private_file(evidence / 'qualification-account.json', credentials(other))
            runner = BootstrapRunner(*identity, qualification_state)
            try:
                runner.run('qualification-account', [str(release / '.venv/bin/python'), '-I', '-B',
                           str(release / 'source/scripts/bootstrap_service_state.py'), '--internal-account'],
                           release / 'source', account=credentials(other))
            finally:
                record['account_provisioning'] = runner.steps
        for path, text in zip(paths, (api, sock), strict=True):
            exclusive_private_file(path, text.encode('utf-8'))
            os.chmod(path, 0o644)
            exclusive_private_file(evidence / path.name, text.encode('utf-8'))
        record['unit_files'] = {path.name: file_digest(path) for path in paths}
        commands.run(['/usr/bin/systemd-analyze', 'verify', *(str(path) for path in paths)])
        commands.run(['/usr/bin/systemctl', 'daemon-reload'])
        # Mark before start: a partial start failure must still stop these exact units.
        started = True
        commands.run(['/usr/bin/systemctl', 'start', name + '.socket'])
        last_error = None
        for _attempt in range(15):
            if time.monotonic() >= commands.deadline:
                raise ValueError('qualification wall budget exhausted')
            try:
                verify(str(socket_path))
                last_error = None
                break
            except (OSError, ValueError) as error:
                last_error = error
                time.sleep(0.2)
        if last_error is not None:
            raise ValueError('actual Unix API readiness failed') from None
        record['service_properties'] = read_properties(commands.run([
            '/usr/bin/systemctl', 'show', name + '.service', '--property=' + ','.join(PROPERTIES)]))
        info = socket_path.stat()
        import grp
        if (not stat.S_ISSOCK(info.st_mode) or info.st_uid != identity[0]
                or info.st_gid != grp.getgrnam('www-data').gr_gid or stat.S_IMODE(info.st_mode) != 0o660):
            raise ValueError('actual socket permissions differ')
        record['socket'] = {'mode': '0660', 'uid': info.st_uid, 'gid': info.st_gid}
        record['transport_passed'] = True
        if owner is not None:
            from qualify_api_workflows import workflows
            record['workflow_qualifier_sha256'] = file_digest(Path(__file__).with_name('qualify_api_workflows.py'))['sha256']
            workflows(str(socket_path), owner, other, commands.deadline, record)
    except Exception:
        record['failure'] = 'isolated_candidate_control_failed'
        raise
    finally:
        try:
            if started:
                commands.run(['/usr/bin/systemctl', 'stop', name + '.service', name + '.socket'], shutdown=True)
                states = [commands.run(['/usr/bin/systemctl', 'show', name + suffix,
                                        '--property=ActiveState', '--value'], shutdown=True)
                          for suffix in ('.service', '.socket')]
                if any(state not in ('inactive', 'failed') for state in states):
                    raise ValueError('owned qualification unit remains active')
            if os.readlink(current) != initial_current:
                raise ValueError('active release changed during qualification')
            record['stopped'] = True
            for path in paths:
                no_links(path)
                if path.exists():
                    if not stat.S_ISREG(path.stat().st_mode):
                        raise ValueError('owned qualification unit path changed')
                    path.unlink()
            if socket_path.exists():
                no_links(socket_path)
                if not stat.S_ISSOCK(socket_path.stat().st_mode):
                    raise ValueError('owned qualification socket path changed')
                socket_path.unlink()
            commands.run(['/usr/bin/systemctl', 'daemon-reload'], shutdown=True)
            if 'failure' not in record:
                no_links(qualification_state)
                if qualification_state.exists():
                    if qualification_state.parent != STATE or not qualification_state.name.startswith('.qualification-'):
                        raise ValueError('qualification state cleanup target changed')
                    shutil.rmtree(qualification_state)
                record['qualification_state_removed'] = True
        finally:
            record['wall_seconds'] = SECONDS - (commands.deadline - time.monotonic())
            exclusive_json(evidence / 'qualification.json', record)
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage-release-environment', action='store_true')
    parser.add_argument('--release', type=Path)
    parser.add_argument('--runtime-receipt', type=Path)
    parser.add_argument('--bundle-sha256')
    parser.add_argument('--runtime-sha256')
    parser.add_argument('--bootstrap-receipt', type=Path)
    parser.add_argument('--bootstrap-sha256')
    parser.add_argument('--original-bootstrap-bundle', type=Path)
    parser.add_argument('--original-bootstrap-bundle-sha256')
    parser.add_argument('--authenticated', action='store_true')
    parser.add_argument('--credentials', type=Path)
    parser.add_argument('--evidence', type=Path)
    parser.add_argument('--physical-binding', type=Path)
    parser.add_argument('--physical-binding-sha256')
    args = parser.parse_args()
    try:
        if args.stage_release_environment:
            if args.release is None or args.bundle_sha256 is None:
                raise ValueError('release and bundle digest required for environment staging')
            result = stage_release_environment(args.release, args.bundle_sha256, args.physical_binding,
                                              args.physical_binding_sha256)
            print(json.dumps(result, sort_keys=True))
            return 0
        required = (args.release, args.runtime_receipt, args.bundle_sha256, args.runtime_sha256,
                    args.bootstrap_receipt, args.bootstrap_sha256, args.evidence)
        if any(value is None for value in required):
            raise ValueError('candidate qualification arguments are incomplete')
        if args.authenticated != (args.credentials is not None):
            raise ValueError('authenticated qualification requires an explicit private owner file')
        result = run(args.release, args.runtime_receipt, args.bundle_sha256, args.runtime_sha256, args.evidence,
                     args.bootstrap_receipt, args.bootstrap_sha256, args.credentials,
                     args.original_bootstrap_bundle, args.original_bootstrap_bundle_sha256)
    except Exception:
        print('Isolated API qualification failed; retained evidence, no activation.', file=sys.stderr)
        return 2
    print('Actual candidate Unix API passed and stopped; scientific/full admission remain false.')
    return 0 if (result['transport_passed'] and result['stopped']
                 and (not args.authenticated or result.get('authenticated_workflows_passed') is True)) else 2


if __name__ == '__main__':
    raise SystemExit(main())
