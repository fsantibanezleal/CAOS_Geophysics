"""Runtime staging contract tests; not Linux installation or job admission."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import subprocess
import time
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import prepare_service_release as bundle  # noqa: E402
import stage_service_runtime as runtime  # noqa: E402


def candidate(tmp_path):
    source = tmp_path / 'source'
    source.mkdir()
    (source / 'requirements-api.txt').write_text('numpy==2.2.6\n', encoding='ascii')
    web = tmp_path / 'web'
    web.mkdir()
    (web / 'index.html').write_bytes(b'<p>actual bytes</p>')
    release = tmp_path / 'release'
    bundle.copy_bundle(source, web, release, ['requirements-api.txt'], 'a' * 40)
    return release, tmp_path / 'evidence', bundle.file_digest(release / 'release.json')['sha256']


class FakeInstaller:
    """Injected execution ordering only, not a claimed installed runtime."""
    fail = None
    mutate = False

    def __init__(self, evidence):
        self.evidence = evidence
        self.records = []
        self.deadline = time.monotonic() + 900

    def run(self, label, argv, cwd):
        self.records.append({'step': label, 'argv': argv})
        path = self.evidence / (label + '.log')
        path.write_bytes(b'fixture execution only\n')
        if label == 'venv':
            root = cwd / '.venv'
            (root / 'bin').mkdir(parents=True)
            (root / 'bin/python').write_bytes(b'not an actual executable')
            (root / 'pyvenv.cfg').write_bytes(b'fixture only')
        if label == self.fail:
            raise ValueError('fixture failure')
        if label == 'freeze' and self.mutate:
            (cwd / 'web/index.html').write_bytes(b'changed')
        return path


def exercise(tmp_path, monkeypatch, installer=FakeInstaller):
    release, evidence, digest = candidate(tmp_path)
    monkeypatch.setattr(runtime.shutil, 'disk_usage', lambda _: SimpleNamespace(free=runtime.INSTALL_RESERVE * 2))
    result = runtime.stage(release, evidence, digest, interpreter=Path(sys.executable).resolve(),
                           installer_factory=installer, check_ownership=False)
    return release, evidence, result


def test_success_is_runtime_only_and_installation_order(tmp_path, monkeypatch):
    release, evidence, result = exercise(tmp_path, monkeypatch)
    assert result['runtime_installed'] is True
    assert result['host_admitted'] is result['full_release_accepted'] is False
    assert [s['step'] for s in result['steps']] == ['venv', 'install', 'check', 'freeze']
    install = result['steps'][1]['argv']
    assert '--isolated' in install and '--no-cache-dir' in install and '--only-binary=:all:' in install
    assert 'https://pypi.org/simple' in install
    assert result['runtime']['regular_bytes'] > 0
    assert json.loads((evidence / 'runtime.json').read_bytes()) == result
    assert bundle.verify_bundle(release)['source_revision'] == 'a' * 40
    assert not (release / 'current').exists()


@pytest.mark.parametrize('existing', ['evidence', '.venv'])
def test_existing_state_not_overwritten(tmp_path, existing):
    release, evidence, digest = candidate(tmp_path)
    target = evidence if existing == 'evidence' else release / existing
    target.mkdir()
    (target / 'retain').write_bytes(b'protected')
    with pytest.raises(ValueError, match='existing'):
        runtime.stage(release, evidence, digest, check_ownership=False)
    assert (target / 'retain').read_bytes() == b'protected'


@pytest.mark.parametrize('digest', ['not-a-hash', 'b' * 64])
def test_digest_before_mutation(tmp_path, digest):
    release, evidence, _ = candidate(tmp_path)
    with pytest.raises(ValueError):
        runtime.stage(release, evidence, digest, check_ownership=False)
    assert not evidence.exists() and not (release / '.venv').exists()


@pytest.mark.parametrize('pin', ['numpy>=2', '-r other.txt', 'https://example.org/a.whl',
                               'numpy==2;python_version>="3"', 'numpy==2\nNumPy==2', '',
                               'numpy==2 # override'])
def test_no_unpinned_or_indirect_requirements(tmp_path, pin):
    path = tmp_path / 'requirements.txt'
    path.write_text(pin, encoding='ascii')
    with pytest.raises(ValueError):
        runtime.requirements(path)


def test_declared_requirements_are_accepted():
    assert runtime.requirements(ROOT / 'requirements-api.txt') == bundle.file_digest(ROOT / 'requirements-api.txt')['sha256']


def test_capacity_before_any_creation(tmp_path, monkeypatch):
    release, evidence, digest = candidate(tmp_path)
    monkeypatch.setattr(runtime.shutil, 'disk_usage', lambda _: SimpleNamespace(free=runtime.INSTALL_RESERVE - 1))
    with pytest.raises(ValueError, match='capacity'):
        runtime.stage(release, evidence, digest, check_ownership=False)
    assert not evidence.exists() and not (release / '.venv').exists()


@pytest.mark.parametrize('step', ['venv', 'install', 'check', 'freeze'])
def test_failure_retains_evidence_and_unaccepted_runtime(tmp_path, monkeypatch, step):
    class Failed(FakeInstaller):
        fail = step
    release, evidence, digest = candidate(tmp_path)
    monkeypatch.setattr(runtime.shutil, 'disk_usage', lambda _: SimpleNamespace(free=runtime.INSTALL_RESERVE * 2))
    with pytest.raises(ValueError, match='fixture'):
        runtime.stage(release, evidence, digest, interpreter=Path(sys.executable).resolve(),
                      installer_factory=Failed, check_ownership=False)
    failure = json.loads((evidence / 'failed.json').read_bytes())
    assert failure['runtime_installed'] is False
    assert failure['host_admitted'] is failure['full_release_accepted'] is False
    assert (release / '.venv/pyvenv.cfg').exists()
    assert not (evidence / 'runtime.json').exists()


def test_post_install_bundle_mutation_fails(tmp_path, monkeypatch):
    class Changed(FakeInstaller):
        mutate = True
    release, evidence, digest = candidate(tmp_path)
    monkeypatch.setattr(runtime.shutil, 'disk_usage', lambda _: SimpleNamespace(free=runtime.INSTALL_RESERVE * 2))
    with pytest.raises(ValueError, match='integrity'):
        runtime.stage(release, evidence, digest, interpreter=Path(sys.executable).resolve(),
                      installer_factory=Changed, check_ownership=False)
    assert (evidence / 'failed.json').exists() and not (evidence / 'runtime.json').exists()


def test_cli_on_workstation_never_installs(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(runtime.sys, 'platform', 'win32')
    assert runtime.main(['--release', str(tmp_path / 'anything'), '--evidence', str(tmp_path / 'e'),
                         '--bundle-sha256', 'a' * 64]) == 1
    assert not (tmp_path / 'e').exists()
    assert 'No activation' in capsys.readouterr().err


def test_isolated_cli_loads_only_trusted_sibling_source():
    result = subprocess.run([sys.executable, '-I', '-B', str(ROOT / 'scripts/stage_service_runtime.py'),
                             '--help'], capture_output=True, timeout=15)
    assert result.returncode == 0 and b'--bundle-sha256' in result.stdout


def test_inventory_rehashes_ordinary_files(tmp_path):
    root = tmp_path / '.venv'
    (root / 'bin').mkdir(parents=True)
    (root / 'bin/python').write_bytes(b'fixture')
    (root / 'pyvenv.cfg').write_bytes(b'fixture')
    before = runtime.runtime_inventory(root, Path(sys.executable).resolve())
    (root / 'pyvenv.cfg').write_bytes(b'mutated')
    after = runtime.runtime_inventory(root, Path(sys.executable).resolve())
    assert before != after


def test_inventory_byte_bound(tmp_path, monkeypatch):
    root = tmp_path / '.venv'
    root.mkdir()
    (root / 'member').write_bytes(b'123')
    monkeypatch.setattr(runtime, 'MAX_RUNTIME_BYTES', 2)
    with pytest.raises(ValueError, match='bound'):
        runtime.runtime_inventory(root, Path(sys.executable).resolve())


def test_exclusive_receipt_does_not_overwrite(tmp_path):
    path = tmp_path / 'receipt.json'
    runtime.exclusive_json(path, {'original': True})
    with pytest.raises(FileExistsError):
        runtime.exclusive_json(path, {'original': False})
    assert json.loads(path.read_bytes()) == {'original': True}


@pytest.mark.skipif(sys.platform != 'linux', reason='actual Linux installer process-group control')
@pytest.mark.parametrize('kind', ['pass', 'nonzero', 'timeout', 'overflow', 'descendant'])
def test_actual_installer_group_controls(tmp_path, monkeypatch, kind):
    (tmp_path / 'tmp').mkdir()
    runner = runtime.Installer(tmp_path)
    python = str(Path(sys.executable).resolve())
    if kind == 'pass':
        code = 'print("actual owned Linux child")'
    elif kind == 'nonzero':
        code = 'raise SystemExit(7)'
    elif kind == 'timeout':
        code = 'import time; time.sleep(5)'
        runner.deadline = time.monotonic() + .25
    elif kind == 'overflow':
        code = 'print("x"*4096)'
        monkeypatch.setattr(runtime, 'MAX_LOG', 64)
    else:
        # Child closes its inherited pipe, then tries a delayed owned write;
        # success of the leader must still drain its process group.
        code = ('import subprocess,sys; subprocess.Popen([sys.executable,"-I","-B","-c",'
                '"import os,time,pathlib;os.close(1);os.close(2);time.sleep(.5);'
                'pathlib.Path(\\\"late-write\\\").write_text(\\\"unexpected\\\")"])')
    command = [python, '-I', '-B', '-c', code]
    if kind in {'pass', 'descendant'}:
        runner.run('actual', command, tmp_path)
        assert runner.records[-1]['success'] is True
    else:
        with pytest.raises(ValueError):
            runner.run('actual', command, tmp_path)
        assert runner.records[-1]['success'] is False
    assert (tmp_path / 'actual.log').stat().st_size <= runtime.MAX_LOG
    assert os.getpid() > 0  # Only the owned child group is targeted, never this test process.
    if kind == 'descendant':
        time.sleep(.75)
        assert not (tmp_path / 'late-write').exists()
