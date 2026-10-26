"""Actual cold Job checks, never caller-supplied accounting as admission."""
from hashlib import sha256
from pathlib import Path
import sys
import os

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'data-pipeline'))
import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_io as io
import magnetic_line_survey_runtime as runtime


def test_supplied_native_boolean_or_foreign_handle_cannot_open_global():
    for handle in (None, True, False, 0, -1, 3.0, '3', 987654321):
        with pytest.raises(core.SurveyError, match='resource_refused'):
            runtime.require_job(handle)


def test_counter_query_failure_refuses_instead_of_zero():
    class Failed:
        def QueryInformationJobObject(self, *args): return 0
    with pytest.raises(core.SurveyError, match='resource_refused'):
        runtime.query(Failed(), 1, 1, runtime.Accounting())


def test_owned_scratch_counts_actual_nested_bytes(tmp_path):
    (tmp_path/'member').write_bytes(b'123')
    (tmp_path/'cache').mkdir()
    (tmp_path/'cache'/'cell').write_bytes(b'4567')
    assert runtime.owned_bytes(tmp_path) == 7


def test_live_deleted_stage_member_is_not_a_terminal_accounting_substitute(tmp_path,monkeypatch):
    monkeypatch.setattr(runtime.os,'walk',lambda *args,**kwargs:iter([(str(tmp_path),[],['removed-stage.bin'])]))
    assert runtime.owned_bytes(tmp_path,allow_disappearing=True)==0
    with pytest.raises(FileNotFoundError):
        runtime.owned_bytes(tmp_path)
    def denied(*args,**kwargs):
        raise PermissionError('Counter scan unavailable')
    monkeypatch.setattr(runtime,'external_path',denied)
    with pytest.raises(PermissionError):
        runtime.owned_bytes(tmp_path,allow_disappearing=True)


def probe_plan(tmp_path, rows=8201, sources=66, mode='zero'):
    input_root = tmp_path/'input'
    input_root.mkdir()
    scratch = tmp_path/'scratch'
    scratch.mkdir()
    identities = sha256(b'fixed-value-free-resource-geometry').hexdigest()
    # Explicit independent resource geometry, NOT field source or S1 evidence.
    xyz = io.write_array(input_root, 'xyz', 'navigation',
        ((float(i % 103)*17., float(i//103)*23., 100.+(i % 7)) for i in range(rows)),
        [rows, 3], 'float64', 'm', identities)
    source = io.write_array(input_root, 'source', 'source_position',
        ((float(i % 11)*173., float(i//11)*251., -200.) for i in range(sources)),
        [sources, 3], 'float64', 'm', identities)
    plan = dict(schema='m03-native-probe-plan/1', mode=mode, input_root=str(input_root),
                coordinates=xyz, sources=source, damping=.01)
    path = scratch/'plan.json'
    path.write_bytes(base.canonical_bytes(plan))
    return path


@pytest.mark.skipif(sys.platform != 'win32', reason='Actual Windows containment required')
def test_actual_8201_row_full_global_zero_native_lifetime(tmp_path):
    path = probe_plan(tmp_path)
    packages = Path(os.environ['GEOPHYSICS_EXISTING_PACKAGE_ROOT'])
    receipt = runtime.run_worker(Path(sys.base_prefix)/'python.exe', packages, path.parent, path)
    assert receipt['verdict'] == 'component_pass', (receipt, (path.parent/'stderr.log').read_text())
    assert receipt['total_processes'] == 1 and receipt['active_processes'] == 0
    assert receipt['cpu_s'] > 0 and receipt['peak_rss_bytes'] > 0 and receipt['peak_committed_bytes'] > 0
    assert receipt['scratch_bytes'] == runtime.owned_bytes(path.parent)
    stored = base.strict_json((path.parent/'lifetime.json').read_bytes())
    assert stored['scratch_bytes'] == receipt['scratch_bytes']
    assert 'magnetic_line_survey_seal.py' in stored['source_sha256']
    ready = base.strict_json((path.parent/'native-ready.json').read_bytes())
    assert ready['rows'] == 8201 and ready['sources'] == 66 and ready['zero_target'] is True
    assert ready['objective'] == 0 and ready['scientific_acceptance'] == 'not_established'


@pytest.mark.skipif(sys.platform != 'win32', reason='Actual Windows containment required')
def test_actual_native_workload_cancellation_and_drain(tmp_path):
    path = probe_plan(tmp_path, rows=8201, sources=66, mode='cancel')
    packages = Path(os.environ['GEOPHYSICS_EXISTING_PACKAGE_ROOT'])
    # Cancel after native readiness, not during unmeasured interpreter startup.
    receipt = runtime.run_worker(Path(sys.base_prefix)/'python.exe', packages, path.parent, path,
                                 cancel_after=.2, cancel_when_ready=True)
    assert receipt['verdict'] == 'cancelled'
    assert (path.parent/'native-ready.json').is_file()
    assert receipt['stop_cpu_s'] <= 10 and receipt['stop_wall_s'] <= 10
    assert receipt['total_processes'] == 1 and receipt['active_processes'] == 0
