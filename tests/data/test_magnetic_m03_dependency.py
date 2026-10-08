"""Current owner source protocol; no numerical/process/field qualification."""
import hashlib
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

import magnetic_native_runtime as runtime
import magnetic_line_survey_runtime as observed
from magnetic_survey_json import InputError, canonical, digest
from run_magnetic_survey import reviewed_binding, source_inventory


ROOT = Path(__file__).parents[2]
spec = importlib.util.spec_from_file_location('m04_current_m03_gate',
    ROOT/'scripts/check_magnetic_m03_dependency.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def test_actual_current_seven_module_binding_without_any_fit():
    report = gate.qualify(ROOT/'data-pipeline')
    assert report['status'] == 'source_protocol_pass'
    assert report['epoch'] == 'physical-gncg-original-noise-reduced-joseph-candidate-9'
    assert report['dependency_sources'] == gate.DEPENDENCY_SOURCES
    assert len(report['observation_sources']) == 7
    assert not any(report[k] for k in ('m03_run_worker_invoked', 'fit_started',
        'native_process_started', 'full_method_accepted', 'field_source_verified',
        'native_security_admitted'))


@pytest.mark.parametrize('name', list(gate.DEPENDENCY_SOURCES))
def test_current_exact_source_drift_refuses_before_import(tmp_path, monkeypatch, name):
    # Actual supplied files, not a mocked file hash success.
    for item in gate.DEPENDENCY_SOURCES:
        (tmp_path/(item+'.py')).write_bytes((ROOT/'data-pipeline'/(item+'.py')).read_bytes())
    with (tmp_path/(name+'.py')).open('ab') as stream:
        stream.write(b'\n# Changed source must not import.\n')
    monkeypatch.setattr(gate.importlib, 'import_module', lambda *_: pytest.fail('No drifted import'))
    with pytest.raises(ValueError, match='source drift: '+name):
        gate.qualify(tmp_path)


def test_old_reference_or_shadow_loaded_module_cannot_qualify(monkeypatch):
    real = gate.importlib.import_module
    monkeypatch.setattr(gate.importlib, 'import_module', lambda name: SimpleNamespace(
        __file__=str(Path(__file__))) if name == 'magnetic_line_survey_runtime' else real(name))
    with pytest.raises(ValueError, match='Foreign loaded M03 dependency root'):
        gate.qualify(ROOT/'data-pipeline')


def test_existing_old_five_module_binding_refuses_before_fit(tmp_path):
    import physical_original_optimizer as core
    sources = source_inventory(original=True)
    old_sources = {k: v for k, v in sources.items()
        if k not in ('magnetic_lines', 'magnetic_line_validation')}
    old = dict(schema='magnetic-local-binding-1', scope='local_candidate_only',
        review_reference='Retained old inventory, never automatically upgraded',
        sources=old_sources, source_inventory_sha256=digest(old_sources),
        runtime_epoch=core.LINEAR_EPOCH, policy=core.POLICY)
    path = tmp_path/'old-binding.json'
    raw = canonical(old)
    path.write_bytes(raw)
    with pytest.raises(InputError, match='Complete reviewed loaded-source inventory mismatch'):
        reviewed_binding(path, True)
    assert path.read_bytes() == raw


def test_fresh_binding_records_actual_corrected_io_and_runtime(tmp_path):
    import physical_original_optimizer as core
    sources = source_inventory(original=True)
    new = dict(schema='magnetic-local-binding-1', scope='local_candidate_only',
        review_reference='Current seven-module source protocol, not scientific admission',
        sources=sources, source_inventory_sha256=digest(sources),
        runtime_epoch=core.LINEAR_EPOCH, policy=core.POLICY)
    path = tmp_path/'current-binding.json'
    path.write_bytes(canonical(new))
    bound = reviewed_binding(path, True)
    assert bound.source_inventory_sha256 == digest(sources)
    assert sources['magnetic_line_survey_runtime'] == hashlib.sha256(Path(observed.__file__).read_bytes()).hexdigest()
    assert set(Path(name).stem for name in runtime.observation_pins()) == set(gate.DEPENDENCY_SOURCES)


@pytest.mark.parametrize('bad', [None, False, True, 0, -1, '1', [], {}])
def test_invalid_job_refuses_before_native_api_or_scientific_import(monkeypatch, bad):
    from magnetic_line_survey import SurveyError
    monkeypatch.setattr(observed, 'apis', lambda: pytest.fail('No native API before valid handle'))
    with pytest.raises(SurveyError, match='resource_refused:fit'):
        observed.require_job(bad)


def test_query_failure_stays_refusal_not_empty_accounting():
    from magnetic_line_survey import SurveyError
    api = SimpleNamespace(QueryInformationJobObject=lambda *_: False)
    with pytest.raises(SurveyError, match='resource_refused:fit'):
        observed.query(api, 1, 1, observed.Accounting())


def test_current_file_validation_keeps_leaf_type_and_repository_refusals(tmp_path):
    from magnetic_line_survey import SurveyError
    from magnetic_line_survey_io import external_path
    regular = tmp_path/'journal.bin'
    regular.write_bytes(b'Retained actual regular leaf')
    assert external_path(regular, directory=False) == regular
    with pytest.raises(SurveyError):
        external_path(regular, directory=True)
    (tmp_path/'.git').mkdir()
    with pytest.raises(SurveyError):
        external_path(regular, directory=False)
    assert regular.read_bytes() == b'Retained actual regular leaf'
