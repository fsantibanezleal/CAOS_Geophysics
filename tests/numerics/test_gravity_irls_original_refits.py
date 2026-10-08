"""Original frozen positive calibration: actual 32 refits for each noise kind.

Only source-correct full24 archives can supply the frozen recipe. No repeated
calibration, truth supplied to fitting, caller operator or posterior claim.
"""
from copy import deepcopy
import json

import numpy as np
import pytest

import gravity_irls_original as irls
import gravity_irls_pool as pool
import gravity_noise_refits as refits
import gravity_survey_l2 as survey
import gravity_workflow_io as workflow
from test_gravity_irls_original_matrix import archive_roots, original_request


@pytest.fixture(scope='module', params=(0, 1), ids=('diagonal', 'full_covariance'))
def actual(request):
    data, temp = archive_roots()
    frozen = workflow.read_archive(data, f'family0-condition{request.param}.gza')
    req, calibrated = frozen['request'], frozen['result']
    expected, _, _ = original_request(0, request.param)
    assert survey._digest(req) == survey._digest(expected), 'noise must consume the exact original matrix fixture'
    assert req['schema'] == irls.REQUEST_SCHEMA and calibrated['runtime_epoch'] == irls.RUNTIME_EPOCH
    assert calibrated['selection_status'] == 'selected'
    result = refits.refit_gravity_noise(req, calibrated)
    # Retain failures before any assertion/replay. This is not an archive upgrade.
    workflow.publish_archive(data, temp, f'noise32-condition{request.param}.gza', result)
    return req, calibrated, result


def test_actual_original_noise_precision_and_caps(actual, monkeypatch, record_property):
    req, frozen, result = actual
    fits = tuple(pool.decode(encoded) for encoded in refits._decode_records(result['records'])['fits'])
    record_property('original_noise32', json.dumps({'noise': req['noise']['kind'],
        'calibration_sha256': frozen['result_sha256'], 'result_sha256': result['result_sha256'],
        'successful': int(np.count_nonzero(result['successful'])),
        'wall_seconds': result['wall_seconds'],
        'fits': tuple({'iterations': fit['iterations'],
            'status': fit.get('terminal', fit).get('status'),
            'reason': fit.get('terminal', fit).get('reason'),
            'wall_seconds': fit.get('wall_seconds')} for fit in fits)}, sort_keys=True, allow_nan=False))
    assert result['count'] == 32 and len(fits) == 32 and result['seed'] == 20261008
    generator = np.random.Generator(np.random.PCG64(20261008))
    draws = generator.standard_normal((32, len(req['observations']['rows'])))
    noise = req['noise']
    expected = (draws*noise['values'] if noise['kind'] == 'diagonal_sd'
        else draws@np.linalg.cholesky(noise['values']).T) + req['observations']['gz_up_mgal']
    np.testing.assert_array_equal(result['targets_mgal'], expected)
    assert np.any(result['targets_mgal'] != req['observations']['gz_up_mgal'])
    assert any(fit['iterations'] > 0 for fit in fits)
    assert result['wall_seconds'] <= 1800.
    for fit in fits:
        assert fit['iterations'] <= 200
        if 'wall_seconds' in fit:
            assert fit['wall_seconds'] <= 120.
        if 'stages' in fit:
            np.testing.assert_array_equal(fit['initialization']['trace']['models_kg_m3'][0],
                req['prior']['start_kg_m3'])
            assert len(fit['stages']) <= 21
    before = frozen['result_sha256']
    monkeypatch.setattr(irls, 'solve_partition', lambda *a, **k: pytest.fail('noise replay called optimizer'))
    monkeypatch.setattr(irls.original.reduced.core, '_solve', lambda *a, **k: pytest.fail('noise replay called minimize'))
    refits.validate_noise_refits(result, req, frozen)
    assert frozen['result_sha256'] == before
    assert result['posterior'] is result['coverage_calibrated'] is False and result['field_truth'] is None
    # New prospective positive gate; old failed-refit tests/archives stay literal.
    assert np.all(result['successful']), 'all actual failed books retained before this assertion'


@pytest.mark.parametrize('fault', ('target', 'beta', 'missing', 'success', 'coverage'))
def test_original_noise_rehashed_denials(actual, fault):
    req, frozen, value = actual
    bad = deepcopy(value)
    if fault == 'target': bad['targets_mgal'][0, 0] += .01
    if fault == 'beta': bad['beta_candidate'] = 1.
    if fault == 'missing':
        decoded = refits._decode_records(bad['records'])
        bad['records'] = refits._records(decoded['fits'][:-1], decoded['stage_books'])
    if fault == 'success': bad['successful'][0] = not bad['successful'][0]
    if fault == 'coverage': bad['coverage_calibrated'] = True
    bad['result_sha256'] = survey._digest({k: v for k, v in bad.items() if k != 'result_sha256'})
    with pytest.raises(ValueError):
        refits.validate_noise_refits(bad, req, frozen)
