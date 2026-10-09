"""Private reader refusal controls; no scientific/native acceptance claim."""
import json
import os
from pathlib import Path
import sys
import sqlite3

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import waveform_m08_installation as authority
import waveform_m08_owned_reader as reader
from tests.api.test_waveform_linux_installation import configuration

JOB = '11111111-1111-4111-8111-111111111111'
PRIVATE = 'SQL private /srv/secret/raw.mseed password 12345'


@pytest.mark.parametrize('phase',['setup','query','serialize','write'])
@pytest.mark.parametrize('kind',[MemoryError,ValueError,OSError,RuntimeError])
def test_child_fixed_tokens_never_include_exception_arguments(phase,kind):
    raw = reader.child_refusal_token(kind(PRIVATE),phase)
    assert raw == (phase+':'+kind.__name__+'\n').encode('ascii')
    assert len(raw) <= 64 and PRIVATE.encode() not in raw


def test_unknown_exception_does_not_read_message():
    class Unknown(Exception):
        def __str__(self):
            raise AssertionError('private message accessed')
    assert reader.child_refusal_token(Unknown(), 'query') == b'query:OtherError\n'
    assert reader.child_refusal_token(MemoryError(), PRIVATE) == b'unknown:OtherError\n'


def parsed(raw=b'query:MemoryError\n',status=2):
    config = configuration(authority)
    body = reader.reader_refusal_diagnostic(raw,status,config,JOB)
    assert body.startswith(b'M08_OWNED_READER_DIAGNOSTIC:') and body.endswith(b'\n')
    assert len(body) <= 2048 and PRIVATE.encode() not in body and b'/opt/' not in body
    value = json.loads(body.split(b':',1)[1])
    assert set(value) == {'schema','exit_code','child','job_id','configuration_sha256',
        'source_revision','source_map_sha256','native_proof'}
    assert value['native_proof'] is False and value['job_id'] == JOB
    assert value['configuration_sha256'] == authority.sha(authority.canonical(config))
    assert value['source_map_sha256'] == authority.sha(authority.canonical(config['source_hashes']))
    return value


def test_parent_binds_only_checked_closed_child_tokens():
    value = parsed()
    assert value['schema'] == 'geophysics.waveform-private-reader-refusal/v1'
    assert value['child'] == dict(phase='query',error_kind='MemoryError') and value['exit_code'] == 2


def test_actual_sqlite_error_and_registered_reader_line_have_no_message():
    code = compile('import sqlite3\nconnection=sqlite3.connect(":memory:")\nconnection.execute("SELECT missing_private_column")',reader.__file__,'exec')
    try:
        exec(code,{})
    except sqlite3.OperationalError as error:
        raw = reader.child_refusal_token(error,'query')
    assert raw == b'query:OperationalError:3:1\n'
    child = parsed(raw)['child']
    assert child['error_kind'] == 'OperationalError' and child['sqlite_errorcode'] == sqlite3.SQLITE_ERROR
    assert child['reader_frame'] == dict(source='scripts/waveform_m08_owned_reader.py',sha256='e'*64,line=3)
    assert b'missing_private_column' not in raw


def test_fixed_installed_domain_error_is_registered_not_inferred_from_class_name():
    module = reader.structural_input()
    assert reader.child_refusal_token(module.WaveformInputError('waveform_contract'),'query') == b'query:WaveformInputError\n'
    spoof = type('WaveformInputError',(Exception,),{})
    assert reader.child_refusal_token(spoof(PRIVATE),'query') == b'query:OtherError\n'


@pytest.mark.parametrize('raw',[b'query:OperationalError:0:1\n',b'query:OperationalError:03:1\n',
    b'query:OperationalError:2147483648:1\n',b'query:OperationalError:3:2147483648\n',
    b'query:MemoryError:3:1\n',b'query:OperationalError:3:-1\n',b'query:OperationalError:3:1:1\n'])
def test_extra_child_fields_are_closed_and_bounded(raw):
    assert parsed(raw)['child'] is None


@pytest.mark.parametrize('raw',[b'',b'query:MemoryError',b'query:MemoryError\nextra',
    b'private:MemoryError\n',b'query:CustomError\n',b'query:MemoryError\r\n',b'x'*65,b'\xff\n'])
def test_malformed_child_tokens_never_invent_cause(raw):
    assert parsed(raw)['child'] is None


@pytest.mark.parametrize('code',[-9,-24,1,255])
def test_actual_nonexception_exit_never_adopts_exception_token(code):
    value = parsed(status=code)
    assert value['exit_code'] == code and value['child'] is None


@pytest.mark.parametrize('code',[True,0,256,-256])
def test_nonfailure_or_unbounded_status_refuses(code):
    with pytest.raises(ValueError):
        parsed(status=code)


@pytest.mark.skipif(sys.platform != 'linux' or os.environ.get('M08_RUN_LINUX_NATIVE') != '1',
    reason='explicit root fork/irreversible-drop mechanics only, never scientific proof')
@pytest.mark.parametrize('kind',[MemoryError,ValueError])
def test_actual_owned_child_drop_bounds_closed_descriptors_and_diagnostic(kind,monkeypatch,capsys):
    import resource
    config = configuration(authority)
    assert os.geteuid() == 0
    sentinel_reader,sentinel_writer = os.pipe()
    def refused(config,identifier):
        assert os.getuid() == os.geteuid() == os.getgid() == os.getegid() == 61901
        assert os.getgroups() == [] and identifier == JOB
        assert resource.getrlimit(resource.RLIMIT_AS) == (256*1024**2,256*1024**2)
        assert resource.getrlimit(resource.RLIMIT_CPU) == (5,5)
        for fd in (sentinel_reader,sentinel_writer):
            with pytest.raises(OSError):
                os.fstat(fd)
        with pytest.raises(PermissionError):
            os.setuid(0)
        raise kind(PRIVATE)
    monkeypatch.setattr(reader,'query',refused)
    try:
        with pytest.raises(ValueError,match='waveform_owned_reader_refused'):
            reader.nonroot_query(config,JOB)
        raw = capsys.readouterr().err.encode()
        value = json.loads(raw.split(b':',1)[1])
        assert value['exit_code'] == 2 and value['child']['phase'] == 'query'
        assert value['child']['error_kind'] == kind.__name__
        assert value['child']['reader_frame']['source'] == 'scripts/waveform_m08_owned_reader.py'
        assert value['child']['reader_frame']['line'] > 0
        assert PRIVATE.encode() not in raw and value['native_proof'] is False
        # Parent ownership is unchanged, and no unowned descriptor is closed.
        assert os.geteuid() == 0
        os.fstat(sentinel_reader)
        os.fstat(sentinel_writer)
    finally:
        os.close(sentinel_reader)
        os.close(sentinel_writer)
