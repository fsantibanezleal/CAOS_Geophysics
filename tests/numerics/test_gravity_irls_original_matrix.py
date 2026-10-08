"""Prospective source-correct epoch, literal original24 scientific assertions.

The original plain-IRLS positive test and failure archives remain unchanged.
Every actual state is exported before replay or accuracy can fail.
"""
import json
import os
from pathlib import Path
from time import monotonic

import choclo
import numpy as np
import pytest

import gravity_irls_original as irls
import gravity_irls_pool as pool
import gravity_survey_l2 as survey
import gravity_workflow_io as workflow
from test_gravity_irls import policy
from test_gravity_l2_selection import _LOCKED_PRISMS, locked_request, outer_request


def original_request(family, condition):
    request, values, covariance = locked_request(family, condition)
    request.update(schema=irls.REQUEST_SCHEMA, runtime_epoch=irls.RUNTIME_EPOCH)
    request['policy'].update(name=irls.POLICY, irls=policy())
    return request, values, covariance


def archive_roots():
    # Explicit device custody, never repository or system-temp fallback.
    data = workflow.external_root(None, 'GEOPHYSICS_M02_IRLS_MATRIX_DATA_ROOT')
    temp = workflow.external_root(None, 'GEOPHYSICS_M02_IRLS_MATRIX_TEMP_ROOT')
    return Path(data), Path(temp)


@pytest.mark.parametrize('condition', range(4))
@pytest.mark.parametrize('family', range(6))
def test_original24_source_correct_science(family, condition, record_property):
    request, values, covariance = original_request(family, condition)
    started = monotonic()
    result = irls.calibrate(request)
    fits = tuple(pool.decode(fit) for fit in result['fits'])
    outcome = {'family': family, 'condition': condition, 'seed': 700001+100*family+condition,
        'request_sha256': survey._digest(request), 'result_sha256': result['result_sha256'],
        'runtime_epoch': irls.RUNTIME_EPOCH, 'selection_status': result['selection_status'],
        'selected_index': result['selected_index'], 'outer_wrms': None, 'model_rmse_ratio': None,
        'fits': tuple({'status': irls_workflow_summary(fit)[0],
            'reason': irls_workflow_summary(fit)[1], 'iterations': fit['iterations'],
            'weight_updates': fit['terminal']['weight_updates'] if 'terminal' in fit else None}
            for fit in fits)}
    record_property('original24_irls_outcome', json.dumps(outcome, sort_keys=True, allow_nan=False))
    data, temp = archive_roots()
    wrapper = {'schema': 'gravity-calibration-archive-1', 'request': request, 'result': result}
    workflow.publish_archive(data, temp, f'family{family}-condition{condition}.gza', wrapper)
    irls.validate(result, request)
    workflow.verify_calibration(workflow.read_archive(data, f'family{family}-condition{condition}.gza'))
    assert len(result['candidates']) == 8 and all(len(c['folds']) == 3 for c in result['candidates'])
    assert result['wall_seconds'] <= 1800.
    for fit in fits:
        assert fit['iterations'] <= 200
        if 'wall_seconds' in fit:
            assert fit['wall_seconds'] <= 120.
        if 'stages' in fit:
            assert len(fit['stages']) <= 21
    if result['selection_status'] == 'selected':
        rows = result['plan']['outer_rows']
        outer = outer_request(result, values[rows].copy())
        outer.update(schema=irls.EVALUATION_SCHEMA, calibration_request=request)
        if covariance is not None:
            outer['noise'].update(kind='full_covariance', values=covariance[np.ix_(rows, rows)],
                unit='mGal^2', cross_partition_dependence='possible_not_removed')
        else:
            outer['noise']['values'][:] = .005
        outer['noise']['values_sha256'] = survey._digest(
            {k: outer['noise'][k] for k in ('kind', 'unit', 'values')} | {'rows': rows})
        evaluated = irls.evaluate(outer)
        outcome['outer_wrms'] = evaluated['wrms']
        bounds = result['plan']['geometry']['active_cell_bounds_m']
        truth = np.zeros(len(bounds))
        for box, density in _LOCKED_PRISMS[family]:
            lengths = np.maximum(0., np.minimum(bounds[:, 1::2], box[1::2])
                - np.maximum(bounds[:, ::2], box[::2]))
            truth += density*np.prod(lengths, axis=1)/np.prod(bounds[:, 1::2]-bounds[:, ::2], axis=1)
        model = fits[24]['model_kg_m3']
        baseline = float(np.linalg.norm(truth))
        outcome['model_rmse_ratio'] = float(np.linalg.norm(model-truth)/baseline) if baseline > 0. else None
        independent = np.array([sum(choclo.prism.gravity_u(*point, *box, float(density))*1e5
            for box, density in zip(bounds, model))
            for point in request['plan']['request']['stations']['receivers_m']])
        np.testing.assert_allclose(independent, result['predictions']['gz_up_mgal'], rtol=1e-7, atol=1e-10)
        workflow.publish_archive(data, temp, f'outer-family{family}-condition{condition}.gza',
            {'schema': 'gravity-evaluation-archive-1', 'request': outer, 'result': evaluated})
    outcome['wall_seconds'] = monotonic()-started
    record_property('original24_irls_scored', json.dumps(outcome, sort_keys=True, allow_nan=False))
    # Literal original positives: no relaxed threshold or reinterpretation.
    if family in (0, 1) and condition in (0, 1):
        assert result['selection_status'] == 'selected', outcome
        assert outcome['outer_wrms'] <= 2., outcome
        assert outcome['model_rmse_ratio'] < 1., outcome


def irls_workflow_summary(fit):
    from gravity_irls_corrected_workflow import _Workflow
    return _Workflow('cpu3')._summary(fit)
