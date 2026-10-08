"""Authored counter sequencing only; not actual Windows/native admission."""
import pytest

import magnetic_native_runtime as runtime
import magnetic_line_survey_runtime as observed
from magnetic_survey_json import InputError


def sample(active=0, total=1, cpu=1., rss=4096, committed=8192):
    return dict(active_processes=active, total_processes=total, cpu_s=cpu,
                peak_rss_bytes=rss, peak_committed_bytes=committed)


@pytest.mark.parametrize('initial', [sample(active=1), sample(total=0)])
def test_process_signal_or_zero_birth_count_is_not_empty_job(monkeypatch, initial):
    rows = iter([initial, sample(cpu=2., rss=2048, committed=4096)])
    sleeps = []
    monkeypatch.setattr(observed, 'counters', lambda *_: next(rows))
    monkeypatch.setattr(runtime.time, 'sleep', sleeps.append)
    result = runtime.settled_job_counters(None, None, 1, 2)
    assert sleeps == [.01]
    assert result == sample(cpu=2.)  # Earlier peaks retained, never replaced by zero.


@pytest.mark.parametrize('row', [sample(active=2), sample(total=2), sample(active=-1)])
def test_foreign_or_invalid_counter_never_issues_lifetime(monkeypatch, row):
    monkeypatch.setattr(observed, 'counters', lambda *_: row)
    with pytest.raises(InputError, match='process-count proof failed'):
        runtime.settled_job_counters(None, None, 1, 2)


@pytest.mark.parametrize('active', [0, 1])
def test_exact_ten_second_reserve_does_not_infer_extinction(monkeypatch, active):
    clock = iter([1., 11.])
    monkeypatch.setattr(runtime.time, 'monotonic', lambda: next(clock))
    monkeypatch.setattr(observed, 'counters', lambda *_: sample(active=active))
    with pytest.raises(InputError, match='did not drain within reserve'):
        runtime.settled_job_counters(None, None, 1, 2)


def test_unavailable_counter_is_not_a_zero_sample(monkeypatch):
    def unavailable(*_):
        raise OSError('actual reader refusal control')
    monkeypatch.setattr(observed, 'counters', unavailable)
    with pytest.raises(OSError, match='reader refusal'):
        runtime.settled_job_counters(None, None, 1, 2)


def test_signalled_process_cannot_restart_existing_stop_reserve(monkeypatch):
    monkeypatch.setattr(runtime.time, 'monotonic', lambda: 11.)
    monkeypatch.setattr(observed, 'counters', lambda *_: sample())
    with pytest.raises(InputError, match='did not drain within reserve'):
        runtime.settled_job_counters(None, None, 1, 2, stopped=1.)
