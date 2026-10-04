"""Install a measured API-only release runtime; never activate or accept it."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_service_release import file_digest, no_links, verify_bundle  # noqa: E402

RELEASES = Path('/var/www/geophysics.ml.fasl-work.com/releases')
EVIDENCE = Path('/var/lib/geophysics-deploy')
PYTHON = Path('/usr/bin/python3')
INSTALL_RESERVE = 4 * 1024**3
MAX_RUNTIME_BYTES = 3 * 1024**3
MAX_RUNTIME_FILES = 65536
MAX_RUNTIME_ENTRIES = 131072
MAX_LOG = 16 * 1024**2
MAX_RECEIPT = 16 * 1024**2
SECONDS = 900
PIN = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]*(?:\[[A-Za-z0-9_,.-]+\])?==[A-Za-z0-9][A-Za-z0-9_.+-]*')


def exclusive_json(path: Path, value: dict) -> None:
    raw = json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    if len(raw) > MAX_RECEIPT:
        raise ValueError('runtime receipt exceeds byte bound')
    with path.open('xb') as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def requirements(path: Path) -> str:
    no_links(path)
    with path.open('rb') as handle:
        raw = handle.read(65537)
    if len(raw) > 65536:
        raise ValueError('requirements byte bound exceeded')
    names = set()
    for line in raw.decode('ascii').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if not PIN.fullmatch(line):
            raise ValueError('requirements must contain simple exact version pins only')
        name = re.sub(r'[-_.]+', '-', re.split(r'[\[=]', line, maxsplit=1)[0].lower())
        if name in names:
            raise ValueError('duplicate requirement')
        names.add(name)
    if not names:
        raise ValueError('empty runtime requirements')
    return hashlib.sha256(raw).hexdigest()


def root_owned_tree(root: Path) -> None:
    """Linux operator-owned input; not a hostile concurrent-root race sandbox."""
    no_links(root)
    pending = [root]
    count = 0
    while pending:
        item = pending.pop()
        info = item.lstat()
        count += 1
        if count > MAX_RUNTIME_ENTRIES or info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError('release input ownership/mode/entry bound failed')
        if stat.S_ISDIR(info.st_mode):
            with os.scandir(item) as entries:
                for entry in entries:
                    pending.append(Path(entry.path))
                    if len(pending) + count > MAX_RUNTIME_ENTRIES:
                        raise ValueError('release input entry bound exceeded')
        elif not stat.S_ISREG(info.st_mode):
            raise ValueError('release input contains an unexpected node')


def runtime_relative(value: str) -> str:
    if (not isinstance(value, str) or not value or len(value) > 1024
            or any(not re.fullmatch(r'[A-Za-z0-9_. -]+', part) or part in ('.', '..')
                   or part != part.strip() or part.endswith('.') for part in value.split('/'))):
        raise ValueError('unsafe runtime member name')
    return value


def runtime_inventory(root: Path, interpreter: Path, *, deadline: float | None = None) -> dict:
    no_links(root)
    actual_python = interpreter.resolve(strict=True)
    python_record = file_digest(actual_python)
    if not root.is_dir():
        raise ValueError('runtime directory absent')
    files, links = {}, {}
    pending = [root]
    count = total = 0
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as scan:
            for item in scan:
                if deadline is not None and time.monotonic() >= deadline:
                    raise ValueError('runtime inventory transaction wall limit exceeded')
                count += 1
                if count > MAX_RUNTIME_ENTRIES:
                    raise ValueError('runtime entry bound exceeded')
                path = Path(item.path)
                name = runtime_relative(path.relative_to(root).as_posix())
                if item.is_symlink():
                    target = path.resolve(strict=True)
                    if name == 'lib64' and os.readlink(path) == 'lib' and target == root / 'lib' and target.is_dir():
                        links[name] = {'target': 'lib', 'kind': 'directory'}
                    elif name in {'bin/python', 'bin/python3', 'bin/python3.12'} and target == actual_python:
                        links[name] = {'target': os.readlink(path), 'resolved': str(target), **python_record}
                    else:
                        raise ValueError('unexpected runtime link')
                    continue
                no_links(path)
                if item.is_dir(follow_symlinks=False):
                    pending.append(path)
                elif item.is_file(follow_symlinks=False):
                    files[name] = file_digest(path)
                    total += files[name]['bytes']
                    if len(files) > MAX_RUNTIME_FILES or total > MAX_RUNTIME_BYTES:
                        raise ValueError('runtime byte/file bound exceeded')
                else:
                    raise ValueError('unexpected runtime node')
    if 'pyvenv.cfg' not in files or not (root / 'bin/python').is_file():
        raise ValueError('not a complete virtual environment')
    return {'files': dict(sorted(files.items())), 'links': dict(sorted(links.items())),
            'regular_bytes': total, 'interpreter': {'path': str(actual_python), **python_record}}


class Installer:
    """Bounded Linux process groups; no secrets forwarded into pip."""

    def __init__(self, evidence: Path):
        self.evidence = evidence
        self.deadline = time.monotonic() + SECONDS
        self.logged = 0
        self.records = []

    @staticmethod
    def limits() -> None:
        import resource
        for key, limit in ((resource.RLIMIT_AS, 2 * 1024**3), (resource.RLIMIT_CPU, 240),
                           (resource.RLIMIT_FSIZE, 256 * 1024**2), (resource.RLIMIT_NOFILE, 512)):
            resource.setrlimit(key, (limit, limit))

    def run(self, label: str, argv: list[str], cwd: Path) -> Path:
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise ValueError('installer transaction wall limit exceeded')
        log = self.evidence / (label + '.log')
        start = time.monotonic()
        env = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1',
               'PYTHONNOUSERSITE': '1', 'TMPDIR': str(self.evidence / 'tmp'),
               'PIP_DISABLE_PIP_VERSION_CHECK': '1', 'PIP_NO_INPUT': '1',
               'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1'}
        process = None
        success = False
        record = {'step': label, 'argv': argv, 'outcome': 'failed'}
        try:
            with log.open('xb') as output, selectors.DefaultSelector() as selector:
                process = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                           stderr=subprocess.STDOUT, start_new_session=True,
                                           preexec_fn=self.limits)
                os.set_blocking(process.stdout.fileno(), False)
                selector.register(process.stdout, selectors.EVENT_READ)
                while selector.get_map():
                    if time.monotonic() >= self.deadline:
                        raise ValueError('installer transaction wall limit exceeded')
                    for key, _ in selector.select(min(.2, self.deadline - time.monotonic())):
                        block = os.read(key.fd, 65536)
                        if not block:
                            selector.unregister(key.fileobj)
                            continue
                        self.logged += len(block)
                        if self.logged > MAX_LOG:
                            raise ValueError('installer captured log bound exceeded')
                        output.write(block)
                code = process.wait(timeout=max(.001, self.deadline - time.monotonic()))
                record['exit_code'] = code
                if code != 0:
                    raise ValueError('installer step failed; inspect retained private log')
                record['outcome'] = 'pass'
                output.flush()
                os.fsync(output.fileno())
                success = True
        finally:
            if process is not None:
                # Always drain the process group, including after a successful
                # leader whose closed-output descendant might otherwise survive.
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=5)
                if process.stdout is not None:
                    process.stdout.close()
            record['elapsed_seconds'] = time.monotonic() - start
            record['success'] = success
            self.records.append(record)
        return log


def stage(release: Path, evidence: Path, expected_digest: str, *, interpreter: Path = PYTHON,
          installer_factory=Installer, check_ownership=True) -> dict:
    deadline = time.monotonic() + SECONDS
    if not re.fullmatch(r'[0-9a-f]{64}', expected_digest):
        raise ValueError('explicit manifest SHA-256 required')
    no_links(release)
    no_links(evidence)
    if evidence.exists() or (release / '.venv').exists() or (release / '.venv').is_symlink():
        raise ValueError('existing runtime/evidence retained; choose a fresh candidate')
    if file_digest(release / 'release.json')['sha256'] != expected_digest:
        raise ValueError('supplied bundle digest differs')
    manifest = verify_bundle(release)
    if check_ownership:
        root_owned_tree(release)
    requirement_hash = requirements(release / 'source/requirements-api.txt')
    if shutil.disk_usage(release).free < INSTALL_RESERVE or shutil.disk_usage(evidence.parent).free < MAX_RECEIPT + MAX_LOG:
        raise ValueError('runtime staging capacity insufficient')
    evidence.mkdir(mode=0o700)
    (evidence / 'tmp').mkdir(mode=0o700)
    runner = installer_factory(evidence)
    runner.deadline = min(runner.deadline, deadline)
    receipt = {'schema': 'geophysics.service-runtime/v1', 'source_revision': manifest['source_revision'],
               'bundle_sha256': expected_digest, 'requirements_sha256': requirement_hash,
               'created_at': datetime.now(timezone.utc).isoformat(), 'runtime_installed': False,
               'host_admitted': False, 'full_release_accepted': False}
    try:
        runner.run('venv', [str(interpreter), '-I', '-B', '-m', 'venv', str(release / '.venv')], release)
        python = str(release / '.venv/bin/python')
        runner.run('install', [python, '-I', '-B', '-m', 'pip', '--isolated', 'install', '--no-cache-dir',
                              '--only-binary=:all:', '--index-url', 'https://pypi.org/simple',
                              '-r', str(release / 'source/requirements-api.txt')], release)
        runner.run('check', [python, '-I', '-B', '-m', 'pip', '--isolated', 'check'], release)
        freeze = runner.run('freeze', [python, '-I', '-B', '-m', 'pip', '--isolated', 'freeze', '--all'], release)
        if verify_bundle(release) != manifest:
            raise ValueError('bundle changed during runtime installation')
        receipt['runtime'] = runtime_inventory(release / '.venv', interpreter, deadline=runner.deadline)
        receipt['resolved_dependencies'] = file_digest(freeze)
        if time.monotonic() >= runner.deadline:
            raise ValueError('runtime transaction wall limit exceeded')
        receipt['runtime_installed'] = True
        receipt['steps'] = runner.records
        exclusive_json(evidence / 'runtime.json', receipt)
        return receipt
    except Exception:
        receipt['runtime_installed'] = False
        receipt['steps'] = runner.records
        # Do not serialize dependency exception repr or environment values.
        receipt['failure'] = 'runtime staging failed; retain candidate and private logs'
        exclusive_json(evidence / 'failed.json', receipt)
        raise


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--bundle-sha256', required=True)
    args = parser.parse_args(argv)
    try:
        if sys.platform != 'linux' or os.geteuid() != 0:
            raise ValueError('Linux operator execution required')
        if (not args.release.is_absolute() or args.release.parent != RELEASES
                or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', args.release.name)
                or not args.evidence.is_absolute() or args.evidence.parent != EVIDENCE
                or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', args.evidence.name)):
            raise ValueError('explicit application release/evidence scope required')
        for parent in (RELEASES, EVIDENCE):
            no_links(parent)
            info = parent.stat()
            if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
                raise ValueError('operator-owned application staging parent required')
        if (RELEASES.parent / 'current').resolve(strict=True) == args.release:
            raise ValueError('active release must not be modified')
        stage(args.release, args.evidence, args.bundle_sha256)
    except Exception:
        print('Runtime staging failed; inspect retained private evidence. No activation performed.', file=sys.stderr)
        return 1
    print('API-only runtime installed and measured; not activated, host-admitted or fully accepted.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
