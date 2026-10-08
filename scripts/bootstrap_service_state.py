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
from stage_service_runtime import EVIDENCE, PYTHON, RELEASES, exclusive_json, runtime_inventory  # noqa: E402

STATE = Path('/var/lib/geophysics')
CONFIG = Path('/etc/geophysics')
HEAD = '0003_processing_jobs'
ORIGIN = 'https://geophysics.ml.fasl-work.com'
SECONDS = 120
OUTPUT = 65536


def bounded_private_json(path: Path, limit: int = OUTPUT) -> dict:
    no_links(path)
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o600:
        raise ValueError('private root-owned mode0600 input required')
    with path.open('rb') as handle:
        raw = handle.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('private input bound exceeded')
    value = strict_json(raw.removeprefix(b'\xef\xbb\xbf'))
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


def verify_candidate(release: Path, receipt: Path, bundle_sha: str, runtime_sha: str) -> dict:
    for digest in (bundle_sha, runtime_sha):
        if not re.fullmatch(r'[0-9a-f]{64}', digest):
            raise ValueError('explicit SHA-256 required')
    operator_directory(release)
    runtime = bounded_private_json(receipt, 16 * 1024**2)
    if file_digest(release / 'release.json')['sha256'] != bundle_sha or file_digest(receipt)['sha256'] != runtime_sha:
        raise ValueError('candidate or runtime receipt changed')
    manifest = verify_bundle(release)
    if (runtime.get('schema') != 'geophysics.service-runtime/v1' or runtime.get('runtime_installed') is not True
            or runtime.get('bundle_sha256') != bundle_sha
            or runtime.get('source_revision') != manifest['source_revision']):
        raise ValueError('runtime receipt does not bind this installed bundle')
    from stage_service_runtime import root_owned_tree
    root_owned_tree(release / 'release.json')
    root_owned_tree(release / 'source')
    root_owned_tree(release / 'web')
    operator_runtime(release / '.venv')
    if runtime_inventory(release / '.venv', PYTHON) != runtime.get('runtime'):
        raise ValueError('installed runtime changed')
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


def private_environment(state: Path, secret: str | None) -> bytes:
    values = {'GEOPHYSICS_DATA_DIR': state.as_posix(), 'GEOPHYSICS_DB_PATH': (state / 'api.sqlite3').as_posix(),
              'GEOPHYSICS_MT_ONLINE_ENABLED': '0'}
    if secret is not None:
        if not re.fullmatch(r'[0-9a-f]{64}', secret):
            raise ValueError('invalid generated authentication secret')
        values.update(GEOPHYSICS_PUBLIC_ORIGIN=ORIGIN, GEOPHYSICS_AUTH_MODE='local', GEOPHYSICS_AUTH_SECRET=secret)
    for key, value in values.items():
        if not re.fullmatch(r'GEOPHYSICS_[A-Z_]+', key) or not re.fullmatch(r'[A-Za-z0-9_./:-]+', value):
            raise ValueError('service environment is not literal')
    return ''.join(f'{k}={v}\n' for k, v in sorted(values.items())).encode('ascii')


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
              identity=dedicated_identity, runner_factory=BootstrapRunner, user_creator=None) -> dict:
    # Test injection only exists in this Python operator function, never the CLI.
    require_absent((state, config, evidence))
    if shutil.disk_usage(state.parent).free < 1024**3:
        raise ValueError('private-state capacity insufficient')
    existing = identity()
    evidence.mkdir(mode=0o700)
    receipt = {'schema': 'geophysics.service-bootstrap/v1', 'created_at': datetime.now(timezone.utc).isoformat(),
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
        state.mkdir(mode=0o700)
        os.chown(state, uid, gid)
        config.mkdir(mode=0o700)
        exclusive_private_file(config / 'api.env', private_environment(state, secrets.token_hex(32)))
        exclusive_private_file(config / 'worker.env', private_environment(state, None))
        runner = runner_factory(uid, gid, state)
        python = str(release / '.venv/bin/python')
        cwd = release / 'source'
        runner.run('migrate', [python, '-B', '-m', 'alembic', '-c', 'app/alembic.ini', 'upgrade', HEAD], cwd)
        runner.run('internal-account', [python, '-I', '-B', str(cwd / 'scripts/bootstrap_service_state.py'),
                                      '--internal-account'], cwd, account=account)
        receipt['database'] = inspect_database(state / 'api.sqlite3', uid, gid)
        receipt['environment_hashes'] = {name: file_digest(config / name) for name in ('api.env', 'worker.env')}
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
            account = credentials(bounded_private_json(args.credentials))
            os.umask(0o077)
            bootstrap(args.release, args.evidence, account, manifest)
    except Exception:
        print('Initial setup refused or failed; preserve private evidence/state. No service activated.', file=sys.stderr)
        return 1
    print('Internal account and private state provisioned; not activated or scientifically admitted.')
    return 0


if __name__ == '__main__':
    if sys.argv[1:] == ['--internal-account']:
        raise SystemExit(internal_account())
    raise SystemExit(main())
