"""All frozen acquisition requests; foundation/source gates, not inverse PASS."""

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from magnetic_survey import plan_geometry
from magnetic_survey_json import canonical, parse_request
import physical_optimizer as linear
import physical_nonlinear_optimizer as nonlinear

spec = importlib.util.spec_from_file_location('full_request_control', Path(__file__).parents[1]/'fixtures'/'magnetic_survey'/'full_request.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


@pytest.mark.parametrize('regime', list('ABCDEF'))
@pytest.mark.parametrize('quantity', ['secondary_enu_nT', 'linear_tmi_nT', 'exact_total_anomaly_nT'])
def test_all_original_full_frozen_requests_with_private_evaluator(regime, quantity):
    core = nonlinear if quantity == 'exact_total_anomaly_nT' else linear
    binding = core.NonlinearBinding('physical_nonlinear_optimizer.solve_bounded_nonlinear', core.SOURCE_SHA256,
        core.VENDOR_SOURCE_SHA256, 'a'*64, core.RUNTIME_EPOCH, core.POLICY) if core is nonlinear else \
        core.OptimizerBinding('physical_optimizer.solve_bounded_physical', core.SOURCE_SHA256,
            'b'*64, 'a'*64, core.RUNTIME_EPOCH, core.POLICY)
    doc, raw, evaluator = fixture.generate(regime, quantity, binding)
    original = json.loads(raw)
    assert doc['source']['original_sha256'] == hashlib.sha256(raw).hexdigest()
    assert doc['source']['original_bytes'] == len(raw) and doc['source']['scope'] == 'complete_acquisition'
    assert doc['source']['kind'] == 'authored_synthetic' and not evaluator['field_truth']
    assert doc['geometry'] == original['geometry'] and doc['acquisition'] == original['acquisition']
    assert len(doc['prior']['start_si']['data']) == 528
    assert doc['observations']['values']['shape'] == [288, 3 if quantity == 'secondary_enu_nT' else 1]
    assert all(x == .5 for x in doc['noise']['values']['data'])
    assert doc['observations']['values'] == original['observations']
    assert 'bodies' not in doc and 'truth_field' not in doc
    assert evaluator['frozen_generator_modified'] is False
    plan = plan_geometry(parse_request(canonical(doc)))
    assert len(plan['partition']['outer_rows']['data']) == 72
    assert len(plan['partition']['development_rows']['data']) == 216
    assert all(len(f['fit_rows']['data']) == 144 and len(f['validation_rows']['data']) == 72 for f in plan['partition']['folds'])
    if regime == 'E':
        assert evaluator['truth_field']['I_deg'] == 37. and doc['inducing_field']['I_deg'] == -35.
    if regime == 'D':
        assert evaluator['bodies'][0]['remanence_A_m'] == [8.,-5.5,2.3]
    if regime == 'F':
        assert evaluator['bodies'] == [] and all(x == 0. for x in doc['observations']['values']['data'])
