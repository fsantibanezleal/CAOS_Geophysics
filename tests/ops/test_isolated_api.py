"""Isolated unit/transport boundaries; actual systemd execution is separate."""

from pathlib import Path
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
