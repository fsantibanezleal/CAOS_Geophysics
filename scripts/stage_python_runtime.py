"""Stage the hash-pinned CPython runtime in private app deployment storage."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tempfile
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_service_release import file_digest, no_links  # noqa: E402

EVIDENCE = Path('/var/lib/geophysics-deploy')
RUNTIMES = EVIDENCE / 'python-runtimes'
NAME = 'cpython-3.12.16-20261026-r3'
URL = ('https://github.com/astral-sh/python-build-standalone/releases/download/'
       '20261026/cpython-3.12.16%2B20261026-x86_64-unknown-linux-gnu-install_only.tar.gz')
SHA256 = '6a79e922e50006b601f29e688407659da1c2b86ebcd4e9c7254cf234be8b89de'
ARCHIVE_BYTES = 67921566
MAX_ARCHIVE = 80 * 1024**2
MAX_ENTRIES = 10000
MAX_UNPACKED = 512 * 1024**2


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _tree_digest(root: Path) -> tuple[str, int, int]:
    records, count, total = [], 0, 0
    for path in sorted(root.rglob('*'), key=lambda item: item.relative_to(root).as_posix()):
        info = path.lstat()
        rel = path.relative_to(root).as_posix()
        count += 1
        if count > MAX_ENTRIES or info.st_uid != 0:
            raise ValueError('interpreter tree owner, mode, or entry bound differs')
        if stat.S_ISDIR(info.st_mode):
            if info.st_mode & 0o022:
                raise ValueError('interpreter directory permissions differ')
            records.append([rel, 'dir'])
        elif stat.S_ISREG(info.st_mode):
            if info.st_mode & 0o022:
                raise ValueError('interpreter file permissions differ')
            total += info.st_size
            if total > MAX_UNPACKED:
                raise ValueError('interpreter tree byte bound exceeded')
            records.append([rel, 'file', info.st_size, _sha(path)])
        elif stat.S_ISLNK(info.st_mode):
            target = os.readlink(path)
            if (PurePosixPath(target).is_absolute() or '\\' in target
                    or not re.fullmatch(r'[A-Za-z0-9_./+-]{1,255}', target)):
                raise ValueError('interpreter link target differs')
            resolved = (PurePosixPath(rel).parent / target)
            parts = []
            for part in resolved.parts:
                if part in ('', '.'):
                    continue
                if part == '..':
                    if not parts:
                        raise ValueError('interpreter link escapes runtime root')
                    parts.pop()
                else:
                    parts.append(part)
            if not parts:
                raise ValueError('interpreter link resolves to runtime root')
            records.append([rel, 'link', target])
        else:
            raise ValueError('interpreter tree contains an unexpected node')
    raw = json.dumps(records, separators=(',', ':'), ensure_ascii=True).encode('ascii')
    return hashlib.sha256(raw).hexdigest(), count, total


def _verify_python(root: Path, *, installed_path: Path | None = None) -> dict:
    executable = root / 'python/bin/python3.12'
    info = executable.stat(follow_symlinks=False)
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or not info.st_mode & 0o111:
        raise ValueError('standalone interpreter executable differs')
    result = subprocess.run(
        [str(executable), '-I', '-B', '-c',
         'import ctypes,lzma,platform,sqlite3,ssl,sys,zlib;'
         'print("|".join((sys.implementation.name,platform.python_version(),'
         'sys.platform,platform.machine())))'],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        timeout=15, check=True, env={'PATH': '/usr/bin:/bin', 'PYTHONNOUSERSITE': '1',
                                     'PYTHONDONTWRITEBYTECODE': '1'})
    try:
        fields = result.stdout.decode('ascii').strip().split('|')
    except UnicodeDecodeError as exc:
        raise ValueError('standalone interpreter probe output differs') from exc
    if fields != ['cpython', '3.12.16', 'linux', 'x86_64']:
        raise ValueError('standalone interpreter platform/version differs')
    return {'path': (installed_path or executable).as_posix(), 'implementation': fields[0],
            'version': fields[1], 'platform': fields[2], 'machine': fields[3],
            'sha256': _sha(executable)}


def _receipt(path: Path) -> dict:
    no_links(path)
    info = path.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError('existing interpreter runtime root differs')
    manifest = json.loads((path / 'runtime.json').read_text(encoding='ascii'))
    if (manifest.get('schema') != 'geophysics.python-runtime/v1'
            or manifest.get('distribution_sha256') != SHA256
            or manifest.get('tree_sha256') != _tree_digest(path / 'python')[0]
            or manifest.get('interpreter') != _verify_python(path)):
        raise ValueError('existing interpreter runtime receipt differs')
    return manifest


def stage() -> dict:
    if sys.platform != 'linux' or os.geteuid() != 0:
        raise ValueError('Linux root operator required')
    for directory in (EVIDENCE, RUNTIMES):
        no_links(directory)
        if directory == RUNTIMES and not directory.exists():
            directory.mkdir(mode=0o700)
        info = directory.stat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError('private interpreter staging directory differs')
    target = RUNTIMES / NAME
    if target.exists():
        return _receipt(target)
    old_umask = os.umask(0o077)
    staging = Path(tempfile.mkdtemp(prefix='.staging-' + NAME + '-', dir=RUNTIMES))
    try:
        os.chmod(staging, 0o700)
        archive = staging / 'distribution.tar.gz'
        digest = hashlib.sha256()
        count = 0
        request = urllib.request.Request(URL, headers={'User-Agent': 'CAOS-Geophysics-runtime-stager/1'})
        with urllib.request.urlopen(request, timeout=60) as response, archive.open('xb') as output:
            if response.status != 200:
                raise ValueError('interpreter download response differs')
            while block := response.read(1024 * 1024):
                count += len(block)
                if count > MAX_ARCHIVE:
                    raise ValueError('interpreter archive byte bound exceeded')
                digest.update(block)
                output.write(block)
            output.flush()
            os.fsync(output.fileno())
        if count != ARCHIVE_BYTES or digest.hexdigest() != SHA256:
            raise ValueError('interpreter distribution digest differs')
        subprocess.run(['/usr/bin/tar', '-xzf', str(archive), '-C', str(staging),
                        '--no-same-owner', '--no-same-permissions'],
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=120, check=True)
        archive.unlink()
        tree = staging / 'python'
        for path in (tree, *tree.rglob('*')):
            info = path.lstat()
            if info.st_uid != 0:
                raise ValueError('interpreter extraction owner differs')
            if stat.S_ISDIR(info.st_mode):
                os.chmod(path, 0o755)
            elif stat.S_ISREG(info.st_mode):
                os.chmod(path, 0o755 if info.st_mode & 0o111 else 0o644)
            elif not stat.S_ISLNK(info.st_mode):
                raise ValueError('interpreter extraction contains an unexpected node')
        tree_hash, entries, unpacked = _tree_digest(tree)
        interpreter = _verify_python(staging, installed_path=target / 'python/bin/python3.12')
        receipt = {'schema': 'geophysics.python-runtime/v1', 'distribution': NAME,
                   'distribution_url': URL, 'distribution_sha256': SHA256,
                   'python': '3.12.16', 'platform': 'linux-x86_64',
                   'tree_sha256': tree_hash, 'entries': entries, 'unpacked_bytes': unpacked,
                   'interpreter': interpreter,
                   'created_at': datetime.now(timezone.utc).isoformat()}
        raw = json.dumps(receipt, sort_keys=True, separators=(',', ':')).encode('ascii')
        fd = os.open(staging / 'runtime.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        if target.exists():
            raise ValueError('interpreter target appeared during staging')
        os.rename(staging, target)
        return receipt
    except Exception:
        # Keep the exact failed staging directory for operator inspection.
        raise
    finally:
        os.umask(old_umask)


def main() -> int:
    try:
        result = stage()
    except Exception:
        print('Pinned Python runtime staging failed; retain private staging evidence.', file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
