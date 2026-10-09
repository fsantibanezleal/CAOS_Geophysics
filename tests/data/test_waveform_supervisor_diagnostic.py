"""Authored private refusal controls, never root/science/extinction proof."""
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import waveform_m08_installation as authority
import waveform_m08_supervisor as supervisor
from tests.api.test_waveform_linux_installation import configuration

JOB = '11111111-1111-4111-8111-111111111111'
PRIVATE = 'secret /srv/private/source.mseed SQL password omega 1234'


def cfg():
    return configuration(authority)


def raised(kind=MemoryError, depth=0):
    root = cfg()['source_root']
    code = compile('def hidden(depth):\n    if depth: return hidden(depth-1)\n    raise kind(private)\nhidden(depth)',
        str(Path(root)/'scripts/waveform_m08_supervisor.py'),'exec')
    try:
        exec(code,dict(kind=kind,private=PRIVATE,depth=depth))
    except BaseException as error:
        return error
    raise AssertionError('expected authored exception')


def emitted(error, config=None, identifier=JOB):
    raw = supervisor.refusal_diagnostic(error,identifier,config,authority)
    assert type(raw) is bytes and len(raw) <= 8192 and raw.endswith(b'\n')
    assert raw.startswith(b'M08_SUPERVISION_DIAGNOSTIC:')
    assert PRIVATE.encode() not in raw and b'/srv/' not in raw and b'/opt/' not in raw
    value = json.loads(raw.split(b':',1)[1])
    assert set(value) == {'schema','reason','error_kind','job_id','configuration_sha256',
                          'source_revision','source_map_sha256','frames','native_proof'}
    assert value['schema'] == 'geophysics.waveform-private-refusal/v1'
    assert value['reason'] == 'supervision_refused' and value['native_proof'] is False
    return value


def test_source_bound_memory_failure_has_no_private_message():
    config = cfg()
    value = emitted(raised(),config)
    assert value['error_kind'] == 'MemoryError' and value['job_id'] == JOB
    assert value['configuration_sha256'] == authority.sha(authority.canonical(config))
    assert value['source_map_sha256'] == authority.sha(authority.canonical(config['source_hashes']))
    assert value['source_revision'] == config['source_revision']
    assert value['frames'] and all(row['source'] == 'scripts/waveform_m08_supervisor.py' for row in value['frames'])
    assert all(row['sha256'] == config['source_hashes'][row['source']] and type(row['line']) is int
               and row['line'] > 0 for row in value['frames'])
    assert all(set(row) == {'source','sha256','line'} for row in value['frames'])


@pytest.mark.parametrize('kind',[MemoryError,ValueError,TypeError,KeyError,OSError,EOFError,RuntimeError,AssertionError])
def test_exact_fixed_exception_classes(kind):
    assert emitted(raised(kind),cfg())['error_kind'] == kind.__name__


def test_unknown_exception_does_not_invoke_str_or_repr():
    class PrivateError(Exception):
        def __str__(self):
            raise AssertionError('private message accessed')
        def __repr__(self):
            raise AssertionError('private repr accessed')
    assert emitted(raised(PrivateError),cfg())['error_kind'] == 'OtherError'


def test_deep_source_trace_keeps_at_most_eight_frames():
    assert len(emitted(raised(depth=20),cfg())['frames']) == 8


@pytest.mark.parametrize('identifier',[None,'../private',True,'INVALID','AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA'])
def test_unchecked_job_is_not_echoed(identifier):
    assert emitted(raised(),cfg(),identifier)['job_id'] is None


@pytest.mark.parametrize('change',['missing','extra','source-hash','source-revision'])
def test_unavailable_binding_is_not_reconstructed(change):
    config = cfg()
    if change == 'missing':
        config = None
    elif change == 'extra':
        config['private_extra'] = PRIVATE
    elif change == 'source-hash':
        config['source_hashes']['scripts/waveform_m08_supervisor.py'] = PRIVATE
    else:
        config['source_revision'] = PRIVATE
    value = emitted(raised(),config)
    assert all(value[name] is None for name in ('configuration_sha256','source_revision','source_map_sha256'))
    assert value['frames'] == []


def test_diagnostic_has_no_source_or_linecache_reads(monkeypatch):
    error = raised()
    monkeypatch.setattr(Path,'read_text',lambda *a,**k:pytest.fail('source text read'))
    monkeypatch.setattr(Path,'read_bytes',lambda *a,**k:pytest.fail('source bytes read'))
    import linecache
    monkeypatch.setattr(linecache,'getline',lambda *a,**k:pytest.fail('source line read'))
    assert emitted(error,cfg())['frames']


def test_main_refusal_remains_exit_five_no_stdout(monkeypatch,capsys):
    config = cfg()
    monkeypatch.setattr(supervisor,'bootstrap',lambda:(authority,config))
    monkeypatch.setattr(sys,'argv',['fixed-supervisor',JOB])
    def fail(*args):
        raise MemoryError(PRIVATE)
    monkeypatch.setattr(supervisor,'supervise',fail)
    assert supervisor.main() == 5
    captured = capsys.readouterr()
    assert captured.out == '' and PRIVATE not in captured.err
    value = json.loads(captured.err.split(':',1)[1])
    assert value['error_kind'] == 'MemoryError' and value['job_id'] == JOB and value['native_proof'] is False


def test_main_diagnostic_failure_retains_fixed_fallback(monkeypatch,capsys):
    monkeypatch.setattr(supervisor,'bootstrap',lambda:(_ for _ in ()).throw(MemoryError(PRIVATE)))
    monkeypatch.setattr(supervisor,'refusal_diagnostic',lambda *a:(_ for _ in ()).throw(MemoryError(PRIVATE)))
    assert supervisor.main() == 5
    captured = capsys.readouterr()
    assert captured.out == '' and captured.err == 'waveform_supervision_refused\n'


def test_success_keeps_stderr_empty(monkeypatch,capsys):
    monkeypatch.setattr(supervisor,'bootstrap',lambda:(authority,cfg()))
    monkeypatch.setattr(supervisor,'supervise',lambda *args:0)
    monkeypatch.setattr(sys,'argv',['fixed-supervisor',JOB])
    assert supervisor.main() == 0
    assert capsys.readouterr().err == ''
