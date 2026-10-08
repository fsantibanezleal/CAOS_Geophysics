"""Pre-science source-order controls, not actual Win32 Job admission."""
import sys
from types import SimpleNamespace

import pytest

import magnetic_native_worker as worker


def test_explicit_frozen_sources_precede_historical_embedded_roots(tmp_path, monkeypatch):
    roots = [tmp_path/name for name in ('science', 'public9', 'lines', 'packages')]
    for root in roots:
        root.mkdir()
    historical = str(tmp_path/'historical-product-root')
    monkeypatch.setattr(sys, 'path', [historical, *sys.path])
    monkeypatch.setattr(sys, 'argv', [worker.__file__, '--packages', str(roots[-1]),
        '--dependencies', *map(str, roots[:-1]), '--job-handle', '123', '--plan', str(tmp_path/'not-read.json')])
    observed = []
    class StopBeforeScience(Exception):
        pass
    def membership(handle):
        assert handle == 123
        observed.extend(sys.path[:4])
        raise StopBeforeScience()
    monkeypatch.setitem(sys.modules, 'magnetic_line_survey_runtime', SimpleNamespace(require_job=membership, apis=None))
    with pytest.raises(StopBeforeScience):
        worker.main()
    assert observed == [str(root.resolve()) for root in roots]
    assert sys.path.index(historical) >= 4


def test_missing_explicit_dependency_refuses_before_membership(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, 'argv', [worker.__file__, '--packages', str(tmp_path),
        '--dependencies', str(tmp_path/'missing'), '--job-handle', '123', '--plan', str(tmp_path/'not-read.json')])
    def forbidden(*args):
        raise AssertionError('No Job/science birth on missing source root')
    monkeypatch.setitem(sys.modules, 'magnetic_line_survey_runtime', SimpleNamespace(require_job=forbidden, apis=None))
    with pytest.raises(FileNotFoundError):
        worker.main()
