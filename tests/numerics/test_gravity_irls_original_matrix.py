"""Prospective source-correct epoch, literal original24 scientific assertions.

The original plain-IRLS positive test and failure archives remain unchanged.
Every actual state is exported before replay or accuracy can fail.
"""
import json
from pathlib import Path
from time import monotonic

import choclo
import numpy as np
import pytest

import gravity_irls_corrected_workflow as corrected_workflow
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


def original_archive_name(family, condition, request):
    identity = survey._digest(dict(runtime_epoch=irls.RUNTIME_EPOCH,
        source_inventory=corrected_workflow._Workflow('cpu3').sources,
        request_sha256=survey._digest(request)))
    return f'family{family}-condition{condition}-{identity[:16]}.gza'


def existing_original_archive(data, family, condition, request):
    """Reuse only an archive whose embedded request and complete source inventory match."""
    request_sha = survey._digest(request)
    sources = corrected_workflow._Workflow('cpu3').sources
    for path in sorted(data.glob(f'family{family}-condition{condition}*.gza')):
        try:
            wrapper = workflow.read_archive(data, path.name)
        except (OSError, ValueError, KeyError, TypeError):
            continue
        result = wrapper.get('result') if type(wrapper) is dict else None
        if (type(wrapper) is dict and wrapper.get('schema') == 'gravity-calibration-archive-1'
                and survey._digest(wrapper.get('request')) == request_sha
                and type(result) is dict and result.get('request_sha256') == request_sha
                and result.get('runtime_epoch') == irls.RUNTIME_EPOCH
                and result.get('source_inventory') == sources):
            return path.name
    return original_archive_name(family, condition, request)


def test_original_archive_name_binds_epoch_sources_and_request(monkeypatch):
    request, _, _ = original_request(0, 0)
    name = original_archive_name(0, 0, request)
    changed = dict(request, runtime_epoch=request['runtime_epoch']+'-changed')
    assert name == original_archive_name(0, 0, request)
    assert name.startswith('family0-condition0-') and name.endswith('.gza')
    assert name != original_archive_name(0, 1, request)
    assert name != original_archive_name(0, 0, changed)
    monkeypatch.setattr(corrected_workflow, 'SOURCE_SHA256', 'f'*64)
    assert name != original_archive_name(0, 0, request)


def test_original_archive_resume_requires_exact_request_and_all_sources(tmp_path, monkeypatch):
    request, _, _ = original_request(0, 0)
    request_sha = survey._digest(request)
    sources = corrected_workflow._Workflow('cpu3').sources
    archived = tmp_path/'family0-condition0-legacy-key.gza'
    archived.write_bytes(b'preserved fixture marker')
    wrapper = {'schema': 'gravity-calibration-archive-1', 'request': request,
        'result': {'request_sha256': request_sha, 'runtime_epoch': irls.RUNTIME_EPOCH,
            'source_inventory': sources}}
    monkeypatch.setattr(workflow, 'read_archive', lambda _root, _name: wrapper)
    assert existing_original_archive(tmp_path, 0, 0, request) == archived.name
    changed = dict(request, runtime_epoch=request['runtime_epoch']+'-changed')
    assert existing_original_archive(tmp_path, 0, 0, changed) == original_archive_name(0, 0, changed)
    monkeypatch.setattr(corrected_workflow, 'SOURCE_SHA256', 'f'*64)
    assert existing_original_archive(tmp_path, 0, 0, request) == original_archive_name(0, 0, request)


@pytest.mark.parametrize('condition', range(4))
@pytest.mark.parametrize('family', range(6))
def test_original24_source_correct_science(family, condition, record_property):
    request, values, covariance = original_request(family, condition)
    data, temp = archive_roots()
    archive_name = existing_original_archive(data, family, condition, request)
    archive_path = data/archive_name
    started = monotonic()
    resumed = archive_path.exists()
    if resumed:
        wrapper = workflow.read_archive(data, archive_name)
        if (wrapper.get('schema') != 'gravity-calibration-archive-1'
            or survey._digest(wrapper.get('request')) != survey._digest(request)):
            raise ValueError('original24 resume archive does not match the exact frozen request')
        result = wrapper.get('result')
    else:
        result = irls.calibrate(request)
    fits = tuple(pool.decode(fit) for fit in result['fits'])
    outcome = {'family': family, 'condition': condition, 'seed': 700001+100*family+condition,
        'request_sha256': survey._digest(request), 'result_sha256': result['result_sha256'],
        'runtime_epoch': irls.RUNTIME_EPOCH, 'selection_status': result['selection_status'],
        'selected_index': result['selected_index'], 'outer_wrms': None, 'model_rmse_ratio': None,
        'resumed_exact_archive': resumed,
        'fits': tuple({'status': irls_workflow_summary(fit)[0],
            'reason': irls_workflow_summary(fit)[1], 'iterations': fit['iterations'],
            'weight_updates': fit['terminal']['weight_updates'] if 'terminal' in fit else None}
            for fit in fits)}
    record_property('original24_irls_outcome', json.dumps(outcome, sort_keys=True, allow_nan=False))
    wrapper = {'schema': 'gravity-calibration-archive-1', 'request': request, 'result': result}
    if not resumed:
        workflow.publish_archive(data, temp, archive_name, wrapper)
    irls.validate(result, request)
    workflow.verify_calibration(workflow.read_archive(data, archive_name))
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
