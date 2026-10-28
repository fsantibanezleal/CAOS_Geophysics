"""Exclusive initial Linux private-state setup; no service activation or admission."""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import secrets
import selectors
import shutil
import signal
import sqlite3
import stat
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_service_release import file_digest, no_links, strict_json, verify_bundle  # noqa: E402
from stage_service_runtime import (  # noqa: E402
    EVIDENCE, RELEASES, exclusive_json, runtime_inventory, validate_interpreter,
)
from stage_python_runtime import NAME as PYTHON_RUNTIME_NAME, RUNTIMES as PYTHON_RUNTIMES  # noqa: E402
from stage_python_runtime import _receipt as python_runtime_receipt  # noqa: E402

STATE = Path('/var/lib/geophysics')
CONFIG = Path('/etc/geophysics')
HEAD = '0003_processing_jobs'
ORIGIN = 'https://geophysics.ml.fasl-work.com'
SECONDS = 120
OUTPUT = 65536
RUNTIME_RECEIPT_LIMIT = 16 * 1024**2


def bounded_private_json(path: Path, limit: int = OUTPUT) -> dict:
    no_links(path)
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o600:
        raise ValueError('private root-owned mode0600 input required')
    with path.open('rb') as handle:
        raw = handle.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('private input bound exceeded')
    value = strict_json(raw.removeprefix(b'\xef\xbb\xbf'), max_bytes=limit)
    if not isinstance(value, dict):
        raise ValueError('private input object required')
    return value


def credentials(value: dict) -> bytes:
    # Management records may include private notes; none enter the child.
    username, password = value.get('username'), value.get('password')
    if (not isinstance(username, str) or not 1 <= len(username) <= 320
            or not isinstance(password, str) or not 8 <= len(password) <= 1024):
        raise ValueError('invalid internal account input')
    return json.dumps({'username': username, 'password': password}, ensure_ascii=True).encode('ascii')


def require_absent(paths) -> None:
    for path in paths:
        no_links(path)
        if path.exists() or path.is_symlink():
            raise ValueError('existing state retained; initial bootstrap refused')


def operator_directory(path: Path) -> None:
    no_links(path)
    info = path.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
        raise ValueError('ordinary operator-owned parent required')


def operator_runtime(root: Path) -> None:
    # Inventory below separately restricts all interpreter/lib links.
    pending, count = [root], 0
    while pending:
        path = pending.pop()
        info = path.lstat()
        count += 1
        if count > 131072 or info.st_uid != 0 or (not path.is_symlink() and info.st_mode & 0o022):
            raise ValueError('runtime ownership or mode invalid')
        if stat.S_ISDIR(info.st_mode):
            with os.scandir(path) as entries:
                for entry in entries:
                    pending.append(Path(entry.path))
                    if len(pending) + count > 131072:
                        raise ValueError('runtime entries exceed bound')
        elif not (stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode)):
            raise ValueError('unexpected runtime node')


def verify_runtime_receipt(release: Path, manifest: dict, runtime: dict, bundle_sha: str) -> None:
    """Bind both installed service environments to the staged private interpreter."""
    if (runtime.get('schema') != 'geophysics.service-runtime/v2'
            or runtime.get('runtime_installed') is not True
            or runtime.get('gravity_runtime_installed') is not True
            or runtime.get('host_admitted') is not False
            or runtime.get('full_release_accepted') is not False
            or runtime.get('bundle_sha256') != bundle_sha
            or runtime.get('source_revision') != manifest.get('source_revision')):
        raise ValueError('runtime receipt does not bind this installed bundle')

    profile = runtime.get('interpreter_profile')
    if not isinstance(profile, dict) or set(profile) != {
            'path', 'implementation', 'version', 'platform', 'machine', 'sha256'}:
        raise ValueError('runtime receipt interpreter profile invalid')
    runtime_root = PYTHON_RUNTIMES / PYTHON_RUNTIME_NAME
    interpreter = runtime_root / 'python/bin/python3.12'
    if profile.get('path') != interpreter.as_posix():
        raise ValueError('runtime receipt interpreter path differs from pinned private runtime')
    pinned = python_runtime_receipt(runtime_root)
    if profile != pinned.get('interpreter') or profile != validate_interpreter(interpreter, release):
        raise ValueError('runtime receipt interpreter identity differs')

    audit = runtime.get('gravity_source_audit')
    if (not isinstance(audit, dict)
            or audit.get('schema') != 'geophysics.gravity-linux-runtime-verification/v1'
            or audit.get('ml_vps_host_admitted') is not False
            or audit.get('public_activation') is not False):
        raise ValueError('runtime receipt gravity source audit invalid')
    for key in ('requirements_sha256', 'gravity_requirements_sha256',
                'resolved_dependencies', 'gravity_resolved_dependencies'):
        if not isinstance(runtime.get(key), str) or not re.fullmatch(r'[0-9a-f]{64}', runtime[key]):
            raise ValueError('runtime receipt dependency digest invalid')

    for directory, key in (('.venv', 'runtime'), ('.venv-gravity', 'gravity_runtime')):
        installed = release / directory
        operator_runtime(installed)
        if runtime_inventory(installed, interpreter) != runtime.get(key):
            raise ValueError(f'installed {directory} differs from runtime receipt')


def verify_candidate(release: Path, receipt: Path, bundle_sha: str, runtime_sha: str) -> dict:
    for digest in (bundle_sha, runtime_sha):
        if not re.fullmatch(r'[0-9a-f]{64}', digest):
            raise ValueError('explicit SHA-256 required')
    operator_directory(release)
    runtime = bounded_private_json(receipt, 16 * 1024**2)
    if file_digest(release / 'release.json')['sha256'] != bundle_sha or file_digest(receipt)['sha256'] != runtime_sha:
        raise ValueError('candidate or runtime receipt changed')
    manifest = verify_bundle(release)
    verify_runtime_receipt(release, manifest, runtime, bundle_sha)
    from stage_service_runtime import root_owned_tree
    root_owned_tree(release / 'release.json')
    root_owned_tree(release / 'source')
    root_owned_tree(release / 'web')
    return manifest


def dedicated_identity():
    import grp
    import pwd

    try:
        user = pwd.getpwnam('geophysics')
    except KeyError:
        return None
    try:
        group = grp.getgrnam('geophysics')
    except KeyError:
        raise ValueError('service group missing') from None
    if (user.pw_uid == 0 or user.pw_gid == 0 or user.pw_gid != group.gr_gid
            or user.pw_shell not in ('/usr/sbin/nologin', '/sbin/nologin')
            or user.pw_dir != '/nonexistent' or group.gr_mem
            or len([u for u in pwd.getpwall() if u.pw_uid == user.pw_uid]) != 1):
        raise ValueError('existing service identity differs; no account changed')
    return user.pw_uid, user.pw_gid


def private_environment(state: Path, secret: str | None, *, binding_path: str | None = None,
                        binding_sha256: str | None = None) -> bytes:
    state_text = state.as_posix().rstrip('/')
    values = {'GEOPHYSICS_DATA_DIR': state_text, 'GEOPHYSICS_DB_PATH': state_text + '/api.sqlite3',
              'GEOPHYSICS_MT_ONLINE_ENABLED': '0', 'GEOPHYSICS_GRAVITY_L2_ONLINE_ENABLED': '0'}
    if secret is not None:
        if not re.fullmatch(r'[0-9a-f]{64}', secret):
            raise ValueError('invalid generated authentication secret')
        values.update(GEOPHYSICS_PUBLIC_ORIGIN=ORIGIN, GEOPHYSICS_AUTH_MODE='local', GEOPHYSICS_AUTH_SECRET=secret)
    if (binding_path is None) != (binding_sha256 is None):
        raise ValueError('physical binding environment must be complete')
    if binding_path is not None:
        if not re.fullmatch(r'[0-9a-f]{64}', binding_sha256 or ''):
            raise ValueError('invalid physical binding digest')
        values.update(GEOPHYSICS_PHYSICAL_BINDING_PATH=binding_path,
                      GEOPHYSICS_PHYSICAL_BINDING_SHA256=binding_sha256)
    for key, value in values.items():
        if not re.fullmatch(r'GEOPHYSICS_[A-Z0-9_]+', key) or not re.fullmatch(r'[A-Za-z0-9_./:-]+', value):
            raise ValueError('service environment is not literal')
    return ''.join(f'{k}={v}\n' for k, v in sorted(values.items())).encode('ascii')


def validate_binding_bytes(registry_raw: bytes, expected_sha256: str, release_raw: bytes) -> str:
    digest = __import__('hashlib').sha256(registry_raw).hexdigest()
    if digest != expected_sha256:
        raise ValueError('physical binding digest differs')
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from app.operator_runtime import _check_registry, _strict_json
    parsed = _strict_json(registry_raw, cap=4 * 1024 * 1024, code='operator_registry')
    _check_registry(parsed, release_raw)
    return parsed['release_manifest_sha256']


def physical_binding(source: Path | None, expected_sha256: str | None, release: Path,
                     state: Path) -> tuple[bytes | None, str | None, str | None, str | None]:
    """Read and validate an explicitly supplied registry before fresh-state writes."""
    if source is None:
        if expected_sha256 is not None:
            raise ValueError('physical binding digest requires registry')
        return None, None, None, None
    if not re.fullmatch(r'[0-9a-f]{64}', expected_sha256 or ''):
        raise ValueError('physical binding requires explicit SHA-256')
    if not source.is_absolute():
        raise ValueError('physical binding source must be absolute')
    no_links(source)
    fd = os.open(source, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != 0 or stat.S_IMODE(before.st_mode) != 0o600
                or before.st_size > 4 * 1024 * 1024):
            raise ValueError('physical binding source must be root-owned mode0600 regular file')
        chunks, total = [], 0
        while True:
            block = os.read(fd, min(65536, 4 * 1024 * 1024 + 1 - total))
            if not block:
                break
            chunks.append(block)
            total += len(block)
            if total > 4 * 1024 * 1024:
                raise ValueError('physical binding exceeds size bound')
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError('physical binding changed while read')
        registry_raw = b''.join(chunks)
    finally:
        os.close(fd)
    manifest_raw = (release / 'release.json').read_bytes()
    release_digest = validate_binding_bytes(registry_raw, expected_sha256, manifest_raw)
    target = state / 'physical-operator-bindings' / (release.name + '.json')
    if not target.is_absolute():
        raise ValueError('physical binding destination must be absolute')
    return registry_raw, target.as_posix(), expected_sha256, release_digest


def exclusive_private_file(path: Path, raw: bytes, uid: int = 0, gid: int = 0) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        os.fchmod(fd, 0o600)
        os.fchown(fd, uid, gid)
        with os.fdopen(fd, 'wb', closefd=False) as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(fd)
    finally:
        os.close(fd)


class BootstrapRunner:
    """One bounded owned process group; captures no child output in receipts."""
    def __init__(self, uid: int, gid: int, state: Path):
        self.uid, self.gid, self.state = uid, gid, state
        self.deadline = time.monotonic() + SECONDS
        self.steps = []
        self.captured = 0

    def child_setup(self):
        import resource
        os.umask(0o077)
        for key, maximum in ((resource.RLIMIT_AS, 1024**3), (resource.RLIMIT_CPU, 256),
                             (resource.RLIMIT_FSIZE, 256 * 1024**2), (resource.RLIMIT_NOFILE, 512)):
            resource.setrlimit(key, (maximum, maximum))
        os.setgroups([])
        os.setgid(self.gid)
        os.setuid(self.uid)

    def run(self, name: str, argv: list[str], cwd: Path, *, account: bytes | None = None) -> None:
        if account is not None and len(account) > 8192:
            raise ValueError('anonymous account input exceeds bound')
        env = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1',
               'PYTHONNOUSERSITE': '1', 'HOME': '/nonexistent', 'OPENBLAS_NUM_THREADS': '1',
               'OMP_NUM_THREADS': '1', 'GEOPHYSICS_DATA_DIR': str(self.state),
               'GEOPHYSICS_DB_PATH': str(self.state / 'api.sqlite3')}
        process, started, record = None, time.monotonic(), {'name': name, 'passed': False}
        try:
            if started >= self.deadline:
                raise ValueError('bootstrap wall budget exhausted')
            with selectors.DefaultSelector() as selector:
                process = subprocess.Popen(argv, cwd=cwd, env=env, start_new_session=True,
                                           preexec_fn=self.child_setup, stdin=subprocess.PIPE if account else subprocess.DEVNULL,
                                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                os.set_blocking(process.stdout.fileno(), False)
                selector.register(process.stdout, selectors.EVENT_READ)
                if account is not None:
                    os.set_blocking(process.stdin.fileno(), False)
                    selector.register(process.stdin, selectors.EVENT_WRITE)
                sent = 0
                while selector.get_map():
                    if time.monotonic() >= self.deadline:
                        raise ValueError('bootstrap wall limit exceeded')
                    for key, _ in selector.select(min(.1, self.deadline - time.monotonic())):
                        if key.fileobj is process.stdin:
                            try:
                                sent += os.write(key.fd, account[sent:])
                            except BrokenPipeError:
                                raise ValueError('account pipe closed') from None
                            if sent == len(account):
                                selector.unregister(process.stdin)
                                process.stdin.close()
                        else:
                            raw = os.read(key.fd, 65536)
                            if not raw:
                                selector.unregister(process.stdout)
                            self.captured += len(raw)
                            if self.captured > OUTPUT:
                                raise ValueError('bootstrap output exceeds bound')
                code = process.wait(timeout=max(.001, self.deadline - time.monotonic()))
                record['exit_code'] = code
                if code:
                    raise ValueError('bootstrap child failed; no secrets printed')
                record['passed'] = True
        finally:
            if process is not None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=5)
                for handle in (process.stdin, process.stdout):
                    if handle is not None:
                        handle.close()
            record['elapsed_seconds'] = time.monotonic() - started
            self.steps.append(record)


def inspect_database(path: Path, uid: int, gid: int) -> dict:
    no_links(path)
    info = path.stat()
    if (not stat.S_ISREG(info.st_mode) or (info.st_uid, info.st_gid) != (uid, gid)
            or stat.S_IMODE(info.st_mode) != 0o600):
        raise ValueError('private database ownership/mode differs')
    with sqlite3.connect('file:' + str(path) + '?mode=ro', uri=True) as connection:
        if connection.execute('PRAGMA quick_check').fetchall() != [('ok',)]:
            raise ValueError('database integrity failed')
        if connection.execute('SELECT version_num FROM alembic_version').fetchall() != [(HEAD,)]:
            raise ValueError('database migration head differs')
        users = connection.execute('SELECT COUNT(*) FROM "user" WHERE is_active=1').fetchone()[0]
        if users != 1:
            raise ValueError('initial internal account not uniquely provisioned')
    return {'schema_revision': HEAD, 'initial_active_accounts': users, 'uid': uid, 'gid': gid, 'mode': '0600'}


def bootstrap(release: Path, evidence: Path, account: bytes, manifest: dict, *, state=STATE, config=CONFIG,
              binding_bytes: bytes | None = None, binding_path: str | None = None,
              binding_sha256: str | None = None, binding_release_sha256: str | None = None,
              identity=dedicated_identity, runner_factory=BootstrapRunner, user_creator=None) -> dict:
    # Test injection only exists in this Python operator function, never the CLI.
    require_absent((state, config, evidence))
    if shutil.disk_usage(state.parent).free < 1024**3:
        raise ValueError('private-state capacity insufficient')
    existing = identity()
    evidence.mkdir(mode=0o700)
    receipt = {'schema': 'geophysics.service-bootstrap/v1', 'release_id': release.name,
               'created_at': datetime.now(timezone.utc).isoformat(),
               'source_revision': manifest['source_revision'], 'bootstrapped': False, 'activated': False,
               'host_admitted': False, 'full_release_accepted': False, 'user_created': False}
    runner = None
    try:
        if existing is None:
            if user_creator is None:
                subprocess.run(['/usr/sbin/useradd', '--system', '--user-group', '--no-create-home',
                                '--home-dir', '/nonexistent', '--shell', '/usr/sbin/nologin', 'geophysics'],
                               stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               check=True, timeout=15)
            else:
                user_creator()
            receipt['user_created'] = True
            existing = identity()
        if existing is None:
            raise ValueError('dedicated identity not established')
        uid, gid = existing
        if (binding_bytes is None) != (binding_path is None) or (binding_bytes is None) != (binding_sha256 is None) \
                or (binding_bytes is None) != (binding_release_sha256 is None):
            raise ValueError('physical binding arguments must be complete')
        state.mkdir(mode=0o700)
        os.chown(state, uid, gid)
        if binding_bytes is not None:
            binding_dir = state / 'physical-operator-bindings'
            binding_dir.mkdir(mode=0o700)
            os.chown(binding_dir, uid, gid)
            exclusive_private_file(binding_dir / (release.name + '.json'), binding_bytes, uid, gid)
        config.mkdir(mode=0o700)
        releases_config = config / 'releases'
        releases_config.mkdir(mode=0o700)
        release_config = releases_config / release.name
        release_config.mkdir(mode=0o700)
        api_raw = private_environment(state, secrets.token_hex(32), binding_path=binding_path,
                                      binding_sha256=binding_sha256)
        worker_raw = private_environment(state, None, binding_path=binding_path,
                                         binding_sha256=binding_sha256)
        exclusive_private_file(release_config / 'api.env', api_raw)
        exclusive_private_file(release_config / 'worker.env', worker_raw)
        exclusive_private_file(config / 'api.env', api_raw)
        exclusive_private_file(config / 'worker.env', worker_raw)
        runner = runner_factory(uid, gid, state)
        if binding_bytes is not None:
            runner.run('physical-locks', [str(release / '.venv/bin/python'), '-I', '-B',
                       str(release / 'source/scripts/ops_physical_bootstrap.py'),
                       '--data-root', state.as_posix()], release / 'source')
        python = str(release / '.venv/bin/python')
        cwd = release / 'source'
        runner.run('migrate', [python, '-B', '-m', 'alembic', '-c', 'app/alembic.ini', 'upgrade', HEAD], cwd)
        runner.run('internal-account', [python, '-I', '-B', str(cwd / 'scripts/bootstrap_service_state.py'),
                                      '--internal-account'], cwd, account=account)
        receipt['database'] = inspect_database(state / 'api.sqlite3', uid, gid)
        receipt['environment_hashes'] = {name: file_digest(config / name) for name in ('api.env', 'worker.env')}
        receipt['release_environment_hashes'] = {
            name: file_digest(release_config / name) for name in ('api.env', 'worker.env')}
        if binding_bytes is not None:
            receipt['physical_binding'] = {'path': binding_path, 'sha256': binding_sha256,
                                           'release_manifest_sha256': binding_release_sha256}
        receipt['steps'] = runner.steps
        receipt['bootstrapped'] = True
        exclusive_json(evidence / 'bootstrap.json', receipt)
        return receipt
    except Exception:
        receipt['bootstrapped'] = False
        receipt['steps'] = runner.steps if runner is not None else []
        receipt['failure'] = 'bootstrap failed; preserve state and inspect privately without printing credentials'
        exclusive_json(evidence / 'failed.json', receipt)
        raise


def internal_account() -> int:
    try:
        raw = sys.stdin.buffer.read(8193)
        value = strict_json(raw)
        if len(raw) > 8192 or not isinstance(value, dict) or set(value) != {'username', 'password'}:
            raise ValueError
        credentials(value)
        from provision_account import run
        from app.config import WorkerSettings
        asyncio.run(run(WorkerSettings.from_env(), value['username'], value['password'], False))
        return 0
    except Exception:
        return 2  # No credential/library exception payload reaches the controller.


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release', type=Path, required=True)
    parser.add_argument('--runtime-receipt', type=Path, required=True)
    parser.add_argument('--bundle-sha256', required=True)
    parser.add_argument('--runtime-sha256', required=True)
    parser.add_argument('--credentials', type=Path, required=True)
    parser.add_argument('--physical-binding', type=Path)
    parser.add_argument('--physical-binding-sha256')
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if sys.platform != 'linux' or os.geteuid() != 0:
            raise ValueError('Linux root operator required')
        if (not args.release.is_absolute() or args.release.parent != RELEASES
                or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', args.release.name)
                or not args.evidence.is_absolute() or args.evidence.parent != EVIDENCE
                or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', args.evidence.name)
                or not args.runtime_receipt.is_absolute() or not args.credentials.is_absolute()):
            raise ValueError('explicit private operator paths required')
        for parent in (RELEASES, EVIDENCE, STATE.parent, CONFIG.parent):
            operator_directory(parent)
        if (RELEASES.parent / 'current').resolve(strict=True) == args.release:
            raise ValueError('active release not a bootstrap candidate')
        import fcntl
        lock_fd = os.open('/run/lock/geophysics-deploy.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        with os.fdopen(lock_fd, 'a+b') as lock:
            lock_info = os.fstat(lock.fileno())
            if not stat.S_ISREG(lock_info.st_mode) or lock_info.st_uid != 0 or lock_info.st_mode & 0o022:
                raise ValueError('deployment lock ownership or mode differs')
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            require_absent((STATE, CONFIG, args.evidence))
            manifest = verify_candidate(args.release, args.runtime_receipt, args.bundle_sha256, args.runtime_sha256)
            identity = dedicated_identity()
            if identity is None:
                raise ValueError('dedicated service identity required')
            binding_bytes, binding_path, binding_sha256, binding_release_sha256 = physical_binding(
                args.physical_binding, args.physical_binding_sha256, args.release, STATE)
            account = credentials(bounded_private_json(args.credentials))
            os.umask(0o077)
            bootstrap(args.release, args.evidence, account, manifest, binding_bytes=binding_bytes,
                      binding_path=binding_path, binding_sha256=binding_sha256,
                      binding_release_sha256=binding_release_sha256)
    except Exception:
        print('Initial setup refused or failed; preserve private evidence/state. No service activated.', file=sys.stderr)
        return 1
    print('Internal account and private state provisioned; not activated or scientifically admitted.')
    return 0


if __name__ == '__main__':
    if sys.argv[1:] == ['--internal-account']:
        raise SystemExit(internal_account())
    raise SystemExit(main())
