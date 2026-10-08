"""Observer protocol/analytical controls, NOT actual full S2 acceptance."""
import copy
import importlib.util
from pathlib import Path

import pytest

from magnetic_survey_json import digest

spec = importlib.util.spec_from_file_location('frozen_matrix_observer',
    Path(__file__).parents[2]/'scripts/run_magnetic_frozen_matrix.py')
observer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(observer)


def analytical_record(regime, quantity='secondary_enu_nT'):
    doc = dict(source=dict(original_bytes=10, original_sha256='a'*64), processing=dict(quantity=quantity),
        geometry=dict(mesh=dict(origin_m=dict(data=[0., 0., 0.]), widths_x_m=dict(data=[1.]),
            widths_y_m=dict(data=[2.]), widths_z_m=dict(data=[3.]), active=dict(data=[True]))))
    evaluator = dict(schema='magnetic-s2-evaluator-1', regime=regime, quantity=quantity,
        modelling_request_sha256=digest(doc), original_bytes=10, field_truth=False,
        frozen_generator_modified=False, provenance=dict(original_sha256='a'*64), bodies=[])
    result = dict(status='complete', model=dict(chi_si=dict(data=[0.])),
        prediction=dict(values_nT=dict(data=[0., 0., 0.])), metrics=dict(outer=dict(rms_nT=1.3)))
    return result, doc, evaluator


def test_exact_null_wiring_and_selected_si_volume():
    result, doc, evaluator = analytical_record('F')
    observed = observer.observe_frozen_model(result, doc, evaluator)
    assert all(observed['null_control'].values())
    assert observed['model_evaluation']['fitted_integral_si_m3'] == 0.
    assert observed['model_evaluation']['fitted_centroid_m'] is None
    result['model']['chi_si']['data'] = [.01]
    observed = observer.observe_frozen_model(result, doc, evaluator)
    assert observed['null_control']['model_exactly_zero'] is False
    assert observed['model_evaluation']['fitted_integral_si_m3'] == .06
    assert observed['model_evaluation']['field_model_truth'] is None


@pytest.mark.parametrize('wrong', ['missing', 'quantity', 'failed', 'insufficient_degradation'])
def test_adverse_missing_failed_foreign_quantity_or_unresolved_is_not_pass(wrong):
    result, doc, evaluator = analytical_record('D')
    matched = dict(case='A:secondary_enu_nT', scientific_verdict='synthetic_predictive_pass', outer=dict(rms_nT=1.))
    if wrong == 'missing': matched = None
    if wrong == 'quantity': matched['case'] = 'A:linear_tmi_nT'
    if wrong == 'failed': matched['scientific_verdict'] = 'failed_no_complete_result'
    if wrong == 'insufficient_degradation': result['metrics']['outer']['rms_nT'] = 1.1
    record = observer.observe_frozen_model(result, doc, evaluator, matched_a=matched)
    assert record['adverse_discrimination']['verdict'].startswith('unresolved_')


@pytest.mark.parametrize('regime', ['D', 'E'])
def test_existing_twenty_percent_adverse_degradation_observer(regime):
    result, doc, evaluator = analytical_record(regime)
    matched = dict(case='A:secondary_enu_nT', scientific_verdict='synthetic_predictive_pass', outer=dict(rms_nT=1.))
    observed = observer.observe_frozen_model(result, doc, evaluator, matched_a=matched)
    assert observed['adverse_discrimination']['verdict'] == 'adverse_degradation_demonstrated'


@pytest.mark.parametrize('attack', ['request', 'source', 'bytes', 'field_claim', 'changed_generator', 'failed_result'])
def test_identity_or_claim_drift_refuses_before_model_observation(attack):
    result, doc, evaluator = copy.deepcopy(analytical_record('A'))
    if attack == 'request': evaluator['modelling_request_sha256'] = '0'*64
    if attack == 'source': evaluator['provenance']['original_sha256'] = '0'*64
    if attack == 'bytes': evaluator['original_bytes'] = 11
    if attack == 'field_claim': evaluator['field_truth'] = True
    if attack == 'changed_generator': evaluator['frozen_generator_modified'] = True
    if attack == 'failed_result': result['status'] = 'failed'
    with pytest.raises(ValueError):
        observer.observe_frozen_model(result, doc, evaluator)


@pytest.mark.parametrize('verdict', ['failed_no_complete_result', 'failed_native_lifetime', 'not_run',
    'synthetic_predictive_fail', 'unresolved_unable_to_discriminate', 'unresolved_unable_to_evaluate'])
def test_matrix_ledger_existence_cannot_make_scientific_process_pass(verdict):
    record = observer.matrix_observation_gate([dict(case='D:secondary_enu_nT', scientific_verdict=verdict)],
        ['D:secondary_enu_nT'])
    assert record['selected_controls_passed'] is False
    assert record['complete_original_linear_coverage'] is False
    assert record['full_method_accepted'] is False


def test_complete_original_linear_coverage_is_separate_from_admission():
    requested = [regime+':'+quantity for regime in 'ABCDEF' for quantity in ('secondary_enu_nT', 'linear_tmi_nT')]
    # Protocol controls only, these dictionaries are NOT measured scientific results.
    results = [dict(case=label, scientific_verdict=('adverse_degradation_demonstrated' if label[0] in 'DE'
        else 'null_numerical_control' if label[0] == 'F' else 'synthetic_predictive_pass')) for label in requested]
    record = observer.matrix_observation_gate(results, requested)
    assert record['selected_controls_passed'] is True and record['complete_original_linear_coverage'] is True
    assert record['field_source_verified'] is False and record['native_security_admitted'] is False
    results[5]['scientific_verdict'] = 'not_run'
    assert observer.matrix_observation_gate(results, requested)['selected_controls_passed'] is False


@pytest.mark.parametrize('requested', [['AB:secondary_enu_nT'], ['A:secondary_enu_nT']*2, [], ['A:wrong_quantity']])
def test_matrix_identity_preflight_before_numerical_birth(requested):
    with pytest.raises(ValueError):
        observer.matrix_observation_gate([dict(case=label, scientific_verdict='not_run') for label in requested], requested)
