"""Initial-state unit boundaries; injected setup is not actual-host admission."""

import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import bootstrap_service_state as setup  # noqa: E402


def test_credentials_project_notes_not_forwarded():
    raw = setup.credentials({'username': 'operator@example.org', 'password': 'test-only-password',
                             'private_note': 'never forwarded'})
    assert json.loads(raw) == {'username': 'operator@example.org', 'password': 'test-only-password'}
    assert b'private_note' not in raw and b'never forwarded' not in raw


@pytest.mark.parametrize('value', [{}, {'username': True, 'password': 'long-enough'},
                                  {'username': 'x', 'password': 'short'},
                                  {'username': 'x', 'password': 'x' * 1025},
                                  {'username': 'x' * 321, 'password': 'long-enough'}])
def test_invalid_credential_input_never_echoed(value):
    with pytest.raises(ValueError, match='invalid internal account input'):
        setup.credentials(value)


def test_worker_environment_storage_only():
    worker = setup.private_environment(setup.STATE, None)
    api = setup.private_environment(setup.STATE, 'a' * 64)
    assert b'AUTH' not in worker and b'PUBLIC_ORIGIN' not in worker and b'SMTP' not in api + worker
    assert b'GEOPHYSICS_MT_ONLINE_ENABLED=0\n' in worker
    assert b'GEOPHYSICS_AUTH_MODE=local\n' in api
    assert setup.ORIGIN.encode() in api


@pytest.mark.parametrize('secret', ['', 'fake', 'x' * 64, 'a' * 63])
def test_environment_secret_requires_generated_hex(secret):
    with pytest.raises(ValueError):
        setup.private_environment(setup.STATE, secret)


@pytest.mark.parametrize('state', ['state;command', 'state with whitespace', 'state\nINJECT=value'])
def test_literal_environment_refuses_injection(state):
    with pytest.raises(ValueError, match='literal'):
        setup.private_environment(Path('/' + state), None)


@pytest.mark.parametrize('existing', ['directory', 'file'])
def test_existing_state_never_reused(tmp_path, existing):
    path = tmp_path / 'retained'
    if existing == 'directory':
        path.mkdir()
    else:
        path.write_bytes(b'protected')
    with pytest.raises(ValueError, match='existing'):
        setup.require_absent((path,))
    assert path.exists()


def test_initial_function_refuses_before_evidence_or_identity(tmp_path):
    state, config, evidence = (tmp_path / p for p in ('state', 'config', 'evidence'))
    state.mkdir()
    def forbidden():
        pytest.fail('existing-state refusal must precede account lookup/creation')
    with pytest.raises(ValueError, match='existing'):
        setup.bootstrap(tmp_path / 'release', evidence, b'private', {'source_revision': 'a' * 40},
                        state=state, config=config, identity=forbidden)
    assert not evidence.exists() and not config.exists()


def test_low_capacity_does_not_create_state(tmp_path, monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(setup.shutil, 'disk_usage', lambda _: SimpleNamespace(free=1024**3 - 1))
    with pytest.raises(ValueError, match='capacity'):
        setup.bootstrap(tmp_path / 'release', tmp_path / 'evidence', b'private', {'source_revision': 'a' * 40},
                        state=tmp_path / 'state', config=tmp_path / 'config')
    assert not (tmp_path / 'evidence').exists()


def test_cli_non_linux_never_mutates(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(setup.sys, 'platform', 'win32')
    result = setup.main(['--release', str(tmp_path / 'release'), '--runtime-receipt', str(tmp_path / 'runtime'),
                         '--bundle-sha256', 'a' * 64, '--runtime-sha256', 'b' * 64,
                         '--credentials', str(tmp_path / 'credentials'), '--evidence', str(tmp_path / 'evidence')])
    assert result == 1 and not list(tmp_path.iterdir())
    assert 'No service activated' in capsys.readouterr().err


def test_isolated_help_and_private_stdin_errors_are_redacted():
    command = [sys.executable, '-I', '-B', str(ROOT / 'scripts/bootstrap_service_state.py')]
    help_result = subprocess.run(command + ['--help'], capture_output=True, timeout=15)
    assert help_result.returncode == 0 and b'--runtime-sha256' in help_result.stdout
    secret = b'test-only-sentinel-secret'
    rejected = subprocess.run(command + ['--internal-account'], input=secret, capture_output=True, timeout=15)
    assert rejected.returncode == 2 and not rejected.stdout and not rejected.stderr


@pytest.mark.skipif(sys.platform != 'linux', reason='actual Linux exclusive mode and ownership primitives')
def test_private_file_exclusive(tmp_path):
    path = tmp_path / 'private'
    setup.exclusive_private_file(path, b'original', os.getuid(), os.getgid())
    assert path.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        setup.exclusive_private_file(path, b'replacement', os.getuid(), os.getgid())
    assert path.read_bytes() == b'original'


@pytest.mark.skipif(sys.platform != 'linux', reason='actual Linux UID/mode setup')
@pytest.mark.parametrize('failure', [None, 'migrate', 'internal-account'])
def test_injected_initial_transaction_preserves_partial_failure(tmp_path, failure):
    uid, gid = os.getuid(), os.getgid()
    state, config, evidence = (tmp_path / p for p in ('state', 'config', 'evidence'))
    class FakeRunner:
        def __init__(self, *_):
            self.steps = []
        def run(self, name, argv, cwd, *, account=None):
            self.steps.append({'name': name, 'passed': name != failure})
            assert all('test-only-password' not in arg for arg in argv)
            if name == failure:
                raise ValueError('injected failure only')
            if name == 'migrate':
                with sqlite3.connect(state / 'api.sqlite3') as db:
                    db.execute('CREATE TABLE alembic_version(version_num TEXT)')
                    db.execute('INSERT INTO alembic_version VALUES (?)', (setup.HEAD,))
                    db.execute('CREATE TABLE "user"(is_active INTEGER)')
                (state / 'api.sqlite3').chmod(0o600)
            else:
                assert json.loads(account)['password'] == 'test-only-password'
                with sqlite3.connect(state / 'api.sqlite3') as db:
                    db.execute('INSERT INTO "user" VALUES (1)')
    account = setup.credentials({'username': 'operator@example.org', 'password': 'test-only-password'})
    call = lambda: setup.bootstrap(tmp_path / 'release', evidence, account, {'source_revision': 'a' * 40},
                                   state=state, config=config, identity=lambda: (uid, gid), runner_factory=FakeRunner)
    if failure:
        with pytest.raises(ValueError, match='injected'):
            call()
        receipt = json.loads((evidence / 'failed.json').read_bytes())
        assert receipt['bootstrapped'] is False and not (evidence / 'bootstrap.json').exists()
    else:
        receipt = call()
        assert receipt['bootstrapped'] is True and receipt['database']['initial_active_accounts'] == 1
    assert receipt['activated'] is receipt['host_admitted'] is receipt['full_release_accepted'] is False
    assert state.is_dir() and config.is_dir()
    assert all('test-only-password' not in p.read_text() for p in evidence.iterdir() if p.is_file())
    assert all('test-only-password' not in p.read_text() for p in config.iterdir())
    before = (config / 'api.env').read_bytes()
    with pytest.raises(ValueError, match='existing'):
        call()
    assert (config / 'api.env').read_bytes() == before


@pytest.mark.skipif(sys.platform != 'linux' or os.geteuid() != 0, reason='actual root-to-service process controls')
@pytest.mark.parametrize('kind', ['pass', 'nonzero', 'timeout', 'overflow', 'descendant', 'stdin'])
def test_actual_bootstrap_process_groups(tmp_path, kind):
    # Same OS controls, using a private test root and a fixed existing non-root UID.
    import pwd
    nobody = pwd.getpwnam('nobody')
    tmp_path.chmod(0o755)
    for p in tmp_path.parents:
        if p.name.startswith('pytest-'):
            p.chmod(0o755)
    os.chown(tmp_path, nobody.pw_uid, nobody.pw_gid)
    runner = setup.BootstrapRunner(nobody.pw_uid, nobody.pw_gid, tmp_path)
    account = None
    if kind == 'pass':
        code = 'import os; assert os.getuid()!=0; print("bounded")'
    elif kind == 'stdin':
        code = 'import sys; assert sys.stdin.buffer.read()==b"private-input"'
        account = b'private-input'
    elif kind == 'nonzero':
        code = 'raise SystemExit(7)'
    elif kind == 'timeout':
        runner.deadline = setup.time.monotonic() + .25
        code = 'import time; time.sleep(5)'
    elif kind == 'overflow':
        code = 'print("x"*65537)'
    else:
        code = ('import subprocess,sys; subprocess.Popen([sys.executable,"-I","-B","-c",'
                '"import os,time,pathlib;os.close(1);os.close(2);time.sleep(.5);'
                'pathlib.Path(\\\"late-write\\\").write_text(\\\"unexpected\\\")"])')
    argv = ['/usr/bin/python3', '-I', '-B', '-c', code]
    if kind in {'pass', 'stdin', 'descendant'}:
        runner.run('actual', argv, tmp_path, account=account)
        assert runner.steps[-1]['passed'] is True
    else:
        with pytest.raises(ValueError):
            runner.run('actual', argv, tmp_path)
        assert runner.steps[-1]['passed'] is False
    if kind == 'descendant':
        setup.time.sleep(.75)
        assert not (tmp_path / 'late-write').exists()
