"""Actual Linux candidate socket qualification, never production activation."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import secrets
import stat
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bootstrap_service_state import (  # noqa: E402
    CONFIG, STATE, BootstrapRunner, bounded_private_json, credentials, dedicated_identity,
    exclusive_private_file, operator_directory, verify_candidate,
)
from prepare_service_release import file_digest, no_links  # noqa: E402
from stage_service_runtime import EVIDENCE, RELEASES, exclusive_json  # noqa: E402
from verify_local_service import verify  # noqa: E402

UNIT_ROOT = Path('/run/systemd/system')
RUN = Path('/run')
SECONDS = 180
PROPERTIES = ('User', 'Group', 'MainPID', 'ActiveState', 'SubState', 'MemoryMax', 'MemorySwapMax',
              'MemoryCurrent', 'MemoryPeak', 'TasksMax', 'CPUQuotaPerSecUSec', 'NoNewPrivileges',
              'PrivateNetwork', 'ProtectSystem', 'ProtectHome', 'ProtectControlGroups',
              'CapabilityBoundingSet', 'RestrictAddressFamilies', 'ReadWritePaths')


def unit_texts(release: Path, token: str) -> tuple[str, str, str]:
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
            or sock.count('/run/geophysics-api/api.sock') != 1):
        raise ValueError('reviewed production template changed')
    api = api.replace('/var/www/geophysics.ml.fasl-work.com/current', release.as_posix())
    api = api.replace('geophysics-api.socket', name + '.socket')
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
                'TasksMax': '96', 'NoNewPrivileges': 'yes', 'PrivateNetwork': 'yes',
                'ProtectSystem': 'strict', 'ProtectHome': 'yes', 'ProtectControlGroups': 'yes',
                'CapabilityBoundingSet': '', 'RestrictAddressFamilies': 'AF_UNIX',
                'ReadWritePaths': '/var/lib/geophysics'}
    if any(result[key] != value for key, value in expected.items()) or not result['MainPID'].isdigit() or int(result['MainPID']) <= 0:
        raise ValueError('actual service restrictions differ')
    return result


def run(release: Path, receipt: Path, bundle_sha: str, runtime_sha: str, evidence: Path,
        bootstrap_receipt: Path, bootstrap_sha: str, owner_credentials: Path | None = None) -> dict:
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
                       bootstrap_receipt, bootstrap_sha, owner_credentials)


def _locked(release, receipt, bundle_sha, runtime_sha, evidence, current, bootstrap_receipt, bootstrap_sha,
            owner_credentials):
    commands = Commands()
    initial_current = os.readlink(current)
    manifest = verify_candidate(release, receipt, bundle_sha, runtime_sha)
    if not re.fullmatch(r'[0-9a-f]{64}', bootstrap_sha) or file_digest(bootstrap_receipt)['sha256'] != bootstrap_sha:
        raise ValueError('bootstrap receipt changed')
    bootstrap = bounded_private_json(bootstrap_receipt)
    if (bootstrap.get('schema') != 'geophysics.service-bootstrap/v1' or bootstrap.get('bootstrapped') is not True
            or bootstrap.get('source_revision') != manifest['source_revision']):
        raise ValueError('initial bootstrap does not bind this candidate')
    identity = dedicated_identity()
    no_links(STATE)
    state = STATE.stat()
    if (identity is None or not stat.S_ISDIR(state.st_mode)
            or (state.st_uid, state.st_gid, stat.S_IMODE(state.st_mode)) != (*identity, 0o700)):
        raise ValueError('existing private identity/state required')
    environments = {}
    for filename in ('api.env', 'worker.env'):
        path = CONFIG / filename
        no_links(path)
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o600:
            raise ValueError('private service environment differs')
        environments[filename] = file_digest(path)
    if environments != bootstrap.get('environment_hashes'):
        raise ValueError('stable private environments changed')
    for unit in ('geophysics-api.service', 'geophysics-api.socket', 'geophysics-worker.service'):
        status = commands.run(['/usr/bin/systemctl', 'show', unit, '--property=ActiveState', '--value'])
        if status not in ('inactive', 'failed', ''):
            raise ValueError('production writer active; parallel qualification refused')
    name, api, sock = unit_texts(release, secrets.token_hex(6))
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
              'initial_current': initial_current, 'environment_files': environments,
              'unit_name': name, 'transport_passed': False, 'stopped': False,
              'activated': False, 'host_admitted': False, 'full_release_accepted': False}
    started = False
    try:
        owner, other = None, None
        if owner_credentials is not None:
            owner = json.loads(credentials(bounded_private_json(owner_credentials)))
            other = {'username': 'qualification.' + name.rsplit('-', 1)[-1] + '@geophysics.invalid',
                     'password': secrets.token_urlsafe(32)}
            exclusive_private_file(evidence / 'qualification-account.json', credentials(other))
            runner = BootstrapRunner(*identity, STATE)
            runner.run('qualification-account', [str(release / '.venv/bin/python'), '-I', '-B',
                       str(release / 'source/scripts/bootstrap_service_state.py'), '--internal-account'],
                       release / 'source', account=credentials(other))
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
        finally:
            record['wall_seconds'] = SECONDS - (commands.deadline - time.monotonic())
            exclusive_json(evidence / 'qualification.json', record)
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release', type=Path, required=True)
    parser.add_argument('--runtime-receipt', type=Path, required=True)
    parser.add_argument('--bundle-sha256', required=True)
    parser.add_argument('--runtime-sha256', required=True)
    parser.add_argument('--bootstrap-receipt', type=Path, required=True)
    parser.add_argument('--bootstrap-sha256', required=True)
    parser.add_argument('--authenticated', action='store_true')
    parser.add_argument('--credentials', type=Path)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.authenticated != (args.credentials is not None):
            raise ValueError('authenticated qualification requires an explicit private owner file')
        result = run(args.release, args.runtime_receipt, args.bundle_sha256, args.runtime_sha256, args.evidence,
                     args.bootstrap_receipt, args.bootstrap_sha256, args.credentials)
    except Exception:
        print('Isolated API qualification failed; retained evidence, no activation.', file=sys.stderr)
        return 2
    print('Actual candidate Unix API passed and stopped; scientific/full admission remain false.')
    return 0 if (result['transport_passed'] and result['stopped']
                 and (not args.authenticated or result.get('authenticated_workflows_passed') is True)) else 2


if __name__ == '__main__':
    raise SystemExit(main())
