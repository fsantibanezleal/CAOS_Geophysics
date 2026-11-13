"""Source-bound corrected IRLS matrix on the frozen original24 controls.

Receipts and scratch stay in explicit device data roots. Failures are archived
before assertions and remain failures when a compatible receipt is replayed.
"""
import json
from time import monotonic

import choclo
import numpy as np
import pytest
from simpeg import maps, regularization

import gravity_irls_corrected_workflow as corrected_workflow
import gravity_irls_pool as pool
import gravity_l2 as l2
import gravity_survey_l2 as survey
import gravity_workflow_io as transport
from test_gravity_irls import policy
from test_gravity_l2_selection import _LOCKED_PRISMS, locked_request, outer_request


def corrected_request(family, condition):
    request, values, covariance = locked_request(family, condition)
    engine = corrected_workflow._Workflow('cpu2')
    request.update(schema=engine.request_schema, runtime_epoch=engine.engine.RUNTIME_EPOCH)
    request['policy'].update(name=engine.engine.POLICY, irls=policy())
    return request, values, covariance


def archive_roots():
    data = transport.external_root(None, 'GEOPHYSICS_M02_IRLS_CORRECTED_DATA_ROOT')
    temp = transport.external_root(None, 'GEOPHYSICS_M02_IRLS_CORRECTED_TEMP_ROOT')
    return data, temp


def archive_name(family, condition, request):
    engine = corrected_workflow._Workflow('cpu2')
    identity = survey._digest(dict(runtime_epoch=engine.engine.RUNTIME_EPOCH,
        source_inventory=engine.sources, request_sha256=survey._digest(request)))
    return f'corrected-family{family}-condition{condition}-{identity[:16]}.gza'


def outer_archive_name(family, condition, calibration_sha256, observations_sha256, noise_sha256):
    """Keep each outer receipt bound to the exact calibration/data/noise triple."""
    identities = (calibration_sha256, observations_sha256, noise_sha256)
    if any(type(value) is not str or len(value) != 64
           or any(char not in '0123456789abcdef' for char in value) for value in identities):
        raise ValueError('outer archive identity must contain three lowercase SHA-256 digests')
    return (f'corrected-outer-family{family}-condition{condition}-'
            f'{calibration_sha256[:12]}-{observations_sha256[:12]}-{noise_sha256[:12]}.gza')


def compatible_outer_archive(data, family, condition, expected):
    """Reuse only a byte-decoded receipt with the exact evaluated wrapper."""
    expected_sha = survey._digest(expected)
    pattern = f'corrected-outer-family{family}-condition{condition}*.gza'
    for name in sorted(path.name for path in data.glob(pattern)):
        try:
            retained = transport.read_archive(data, name)
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if survey._digest(retained) == expected_sha:
            return name
    return None


def compatible_archive(data, family, condition, request):
    request_sha = survey._digest(request)
    engine = corrected_workflow._Workflow('cpu2')
    for name in sorted(path.name for path in data.glob(f'corrected-family{family}-condition{condition}-*.gza')):
        try:
            value = transport.read_archive(data, name)
        except (OSError, ValueError, KeyError, TypeError):
            continue
        result = value.get('result') if type(value) is dict else None
        if (type(value) is dict and value.get('schema') == 'gravity-calibration-archive-1'
            and survey._digest(value.get('request')) == request_sha
            and type(result) is dict and result.get('request_sha256') == request_sha
            and result.get('runtime_epoch') == engine.engine.RUNTIME_EPOCH
            and result.get('source_inventory') == engine.sources):
            return name
    return archive_name(family, condition, request)


def test_corrected_archive_identity_and_resume(tmp_path, monkeypatch):
    request, _, _ = corrected_request(0, 0)
    name = archive_name(0, 0, request)
    assert name == archive_name(0, 0, request)
    assert name != archive_name(0, 1, request)
    assert name != archive_name(1, 0, request)
    changed = dict(request, runtime_epoch=request['runtime_epoch']+'-changed')
    assert name != archive_name(0, 0, changed)
    outer_name = outer_archive_name(0, 0, 'a'*64, 'b'*64, 'c'*64)
    assert outer_name != outer_archive_name(0, 0, 'd'*64, 'b'*64, 'c'*64)
    assert outer_name != outer_archive_name(0, 0, 'a'*64, 'd'*64, 'c'*64)
    assert outer_name != outer_archive_name(0, 0, 'a'*64, 'b'*64, 'd'*64)
    monkeypatch.setitem(corrected_workflow._SOURCES, 'gravity_irls_corrected_workflow', 'f'*64)
    assert name != archive_name(0, 0, request)

    data = tmp_path/'data'
    data.mkdir()
    receipt = data/'corrected-family0-condition0-legacy.gza'
    receipt.write_bytes(b'preserved test marker')
    request_sha = survey._digest(request)
    engine = corrected_workflow._Workflow('cpu2')
    wrapper = {'schema':'gravity-calibration-archive-1','request':request,
        'result':{'request_sha256':request_sha,'runtime_epoch':engine.engine.RUNTIME_EPOCH,
                  'source_inventory':engine.sources}}
    monkeypatch.setattr(transport, 'read_archive', lambda _root, _name: wrapper)
    assert compatible_archive(data, 0, 0, request) == receipt.name
    assert compatible_archive(data, 0, 1, request) == archive_name(0, 1, request)
    assert compatible_archive(data, 0, 0, changed) == archive_name(0, 0, changed)

    outer_receipt = data/'corrected-outer-family0-condition0-legacy.gza'
    outer_receipt.write_bytes(b'preserved outer marker')
    outer_wrapper = {'schema':'gravity-evaluation-archive-1','result':{'calibration_sha256':'a'*64}}
    monkeypatch.setattr(transport, 'read_archive', lambda _root, name: outer_wrapper
        if name == outer_receipt.name else (_ for _ in ()).throw(ValueError('missing receipt')))
    assert compatible_outer_archive(data, 0, 0, outer_wrapper) == outer_receipt.name
    assert compatible_outer_archive(data, 0, 0, dict(outer_wrapper, result={'calibration_sha256':'b'*64})) is None


@pytest.mark.parametrize('condition', range(4))
@pytest.mark.parametrize('family', range(6))
def test_original24_corrected_science(family, condition, record_property):
    request, values, covariance = corrected_request(family, condition)
    data, temp = archive_roots()
    name = compatible_archive(data, family, condition, request)
    target = data/name
    started = monotonic()
    resumed = target.exists()
    if resumed:
        wrapper = transport.read_archive(data, name)
        if (wrapper.get('schema') != 'gravity-calibration-archive-1'
            or survey._digest(wrapper.get('request')) != survey._digest(request)):
            raise ValueError('corrected original24 archive differs from frozen request')
    else:
        result = corrected_workflow.calibrate(request)
        wrapper = {'schema':'gravity-calibration-archive-1','request':request,'result':result}
        # Persist the actual outcome before scientific checks or independent replay.
        transport.publish_archive(data, temp, name, wrapper)
        wrapper = transport.read_archive(data, name)
    result = wrapper['result']

    engine = corrected_workflow._Workflow('cpu2')
    fits = tuple(pool.decode(item) for item in result['fits'])
    outcome = {'family':family,'condition':condition,'seed':700001+100*family+condition,
        'request_sha256':survey._digest(request),'result_sha256':result['result_sha256'],
        'runtime_epoch':engine.engine.RUNTIME_EPOCH,'selection_status':result['selection_status'],
        'selected_index':result['selected_index'],'calibration_wall_seconds':result['wall_seconds'],
        'outer_wrms':None,'model_rmse_ratio':None,'resumed_exact_archive':resumed,
        'fits':tuple({'status':engine._summary(fit)[0],'reason':engine._summary(fit)[1],
            'iterations':fit['iterations'],'wall_seconds':fit.get('wall_seconds'),
            'weight_updates':fit.get('terminal',{}).get('weight_updates')} for fit in fits)}
    record_property('corrected_original24_outcome', json.dumps(outcome, sort_keys=True, allow_nan=False))

    assert len(result['candidates']) == 8 and all(len(item['folds']) == 3 for item in result['candidates'])
    assert result['wall_seconds'] <= 1800., outcome
    for fit in fits:
        assert fit['iterations'] <= 200, outcome
        if fit.get('wall_seconds') is not None:
            assert fit['wall_seconds'] <= 120., outcome
        if fit.get('stages') is not None:
            assert len(fit['stages']) <= 21, outcome

    if result['selection_status'] == 'selected':
        rows = result['plan']['outer_rows']
        outer = outer_request(result, values[rows].copy())
        outer.update(schema=engine.evaluation_schema, calibration_request=request)
        if covariance is not None:
            outer['noise'].update(kind='full_covariance', values=covariance[np.ix_(rows, rows)],
                unit='mGal^2', cross_partition_dependence='possible_not_removed')
        else:
            outer['noise']['values'][:] = .005
        outer['noise']['values_sha256'] = survey._digest(
            {key:outer['noise'][key] for key in ('kind','unit','values')} | {'rows':rows})
        evaluated = corrected_workflow.evaluate(outer)
        outcome['outer_wrms'] = evaluated['wrms']
        prediction = result['predictions']['gz_up_mgal'][rows]
        expected = l2._marginal_metrics(prediction, outer['observations']['gz_up_mgal'],
            {key:outer['noise'][key] for key in ('kind', 'values')}, np.arange(len(rows), dtype=np.int64))
        for actual, reference, field in zip(
                (evaluated['phi_d'], evaluated['wrms'], evaluated['rmse_mgal'],
                 evaluated['residual_observed_minus_predicted_mgal'], evaluated['whitened_residual']),
                expected, ('phi_d', 'wrms', 'rmse_mgal', 'residual', 'whitened_residual')):
            np.testing.assert_allclose(actual, reference, rtol=1e-12, atol=1e-12, err_msg=field)
        if (evaluated['calibration_sha256'] != result['result_sha256']
            or evaluated['noise_sha256'] != outer['noise']['values_sha256']
            or survey._digest({key:value for key,value in evaluated.items() if key != 'result_sha256'})
                != evaluated['result_sha256']):
            raise ValueError('corrected outer result identity')

        bounds = result['plan']['geometry']['active_cell_bounds_m']
        truth = np.zeros(len(bounds))
        for box, density in _LOCKED_PRISMS[family]:
            lengths = np.maximum(0., np.minimum(bounds[:,1::2], box[1::2])
                - np.maximum(bounds[:,::2], box[::2]))
            truth += density*np.prod(lengths, axis=1)/np.prod(bounds[:,1::2]-bounds[:,::2], axis=1)
        final = pool.decode(result['fits'][result['final_solve']])
        model = final['model_kg_m3']
        baseline = float(np.linalg.norm(truth))
        outcome['model_rmse_ratio'] = float(np.linalg.norm(model-truth)/baseline) if baseline else None
        independent = np.array([sum(choclo.prism.gravity_u(*point, *box, float(density))*1e5
            for box, density in zip(bounds, model))
            for point in request['plan']['request']['stations']['receivers_m']])
        np.testing.assert_allclose(independent, result['predictions']['gz_up_mgal'], rtol=1e-7, atol=1e-10)
        evaluation_name = outer_archive_name(family, condition, result['result_sha256'],
            outer['observations']['values_sha256'], outer['noise']['values_sha256'])
        evaluation_path = data/evaluation_name
        evaluation_wrapper = {'schema':'gravity-evaluation-archive-1',
            'evaluation_schema':engine.evaluation_schema,'frozen_calibration':result,
            'calibration_request':request, **{key:value for key,value in outer.items() if key != 'schema'},
            'result':evaluated}
        compatible_name = compatible_outer_archive(data, family, condition, evaluation_wrapper)
        if compatible_name is None and not evaluation_path.exists():
            transport.publish_archive(data, temp, evaluation_name, evaluation_wrapper)
            compatible_name = evaluation_name
        elif compatible_name is None:
            compatible_name = evaluation_name
        retained = transport.read_archive(data, compatible_name)
        if survey._digest(retained) != survey._digest(evaluation_wrapper):
            raise ValueError('corrected outer archive differs from independently evaluated result')
    else:
        # An unsuccessful calibration has no frozen outer evaluation. Replay it
        # exactly once here; selected calibrations are fully replayed by evaluate.
        transport.verify_calibration(wrapper)

    outcome['wall_seconds'] = monotonic()-started
    record_property('corrected_original24_scored', json.dumps(outcome, sort_keys=True, allow_nan=False))
    if family in (0, 1) and condition in (0, 1):
        assert result['selection_status'] == 'selected', outcome
        assert outcome['outer_wrms'] <= 2., outcome
        assert outcome['model_rmse_ratio'] < 1., outcome


def test_cpu2_terminal_certificate_frozen_candidate6_fold2(record_property):
    """Replay the approved terminal certificate on the locked 48-cell case."""
    request, _, _ = corrected_request(0, 0)
    workflow = corrected_workflow._Workflow('cpu2')
    admitted = workflow.admit(request)
    fold = admitted['plan']['folds'][2]
    started = monotonic()
    packed = workflow._fit(admitted, fold['fit_rows'], l2.BETA_CANDIDATES[6], started+120.)
    fit = pool.decode(packed)
    terminal = fit['terminal']
    stages = fit['stages']
    final = stages[-1]
    certificate = terminal['fixed_point_certificate']
    result_summary = {
        'candidate': 6, 'fold': 2, 'beta': l2.BETA_CANDIDATES[6],
        'request_sha256': survey._digest(request),
        'source_inventory_sha256': survey._digest(fit['source_inventory']),
        'status': terminal['status'], 'reason': terminal['reason'],
        'iterations': fit['iterations'], 'weight_updates': terminal['weight_updates'],
        'wall_seconds': fit['wall_seconds'],
        'final_three_changes': terminal['stage_changes'][-3:],
        'certificate': certificate,
        'research_only': True, 'product_acceptance': False,
    }
    record_property('cpu2_terminal_certificate_case',
                    json.dumps(result_summary, sort_keys=True, allow_nan=False))

    assert terminal['status'] == 'converged', result_summary
    assert terminal['reason'] == 'irls_fixed_point_certificate', result_summary
    assert terminal['weight_updates'] == 20 and len(stages) == 21
    assert fit['iterations'] <= 200 and fit['wall_seconds'] <= 120.
    assert final['index'] == 20 and final['inner']['status'] == 'converged'
    assert final['inner']['reason'] == 'absolute_stationary'
    assert final['inner']['iterations'] == 0 and final['inner']['failed_trial'] is None
    assert result_summary['final_three_changes'][0]['weights_relative'] > 1e-6
    assert result_summary['final_three_changes'][1:] == (
        {'model_relative': 0.0, 'weights_relative': 0.0},
        {'model_relative': 0.0, 'weights_relative': 0.0},
    )

    start, stop = final['adopted_row'], final['stop_row']
    q = np.array(fit['models_q'][stop], dtype=np.float64, copy=True)
    assert np.array_equal(fit['models_q'][start], q)
    assert np.array_equal(final['inner']['trace']['models_q'][-1], q)
    assert np.array_equal(final['inner']['q'], q)

    # Rebuild the fixed SimPEG Sparse objective independently of the producer's
    # certificate function and compare every physical weight and KKT quantity.
    noise = {key: admitted['noise'][key] for key in ('kind', 'values')}
    problem = l2._build_problem(admitted['plan']['request'],
        admitted['observations']['gz_up_mgal'], noise, admitted['prior'],
        fold['fit_rows'], l2.BETA_CANDIDATES[6],
        observation_rows=admitted['plan']['development_rows'])
    simulation, alpha = problem['simulation'], problem['alpha']
    independent_sparse = regularization.Sparse(
        simulation.mesh, active_cells=simulation.active_cells,
        mapping=maps.IdentityMap(nP=len(problem['reference_q'])),
        reference_model=problem['reference_q'].copy(), reference_model_in_smooth=True,
        alpha_s=alpha[0], alpha_x=alpha[1], alpha_y=alpha[2], alpha_z=alpha[3],
        norms=[1., 2., 2., 2.], gradient_type='components', irls_scaled=True)
    for component, threshold in zip(independent_sparse.objfcts,
                                    admitted['policy']['irls']['epsilon_floor']):
        component.irls_threshold = threshold
    independent_sparse.update_weights(q)
    independent_weights = tuple(np.array(component.get_weights('irls'), copy=True)
                                for component in independent_sparse.objfcts)
    independent_weight_hashes = tuple(survey._digest(weight) for weight in independent_weights)
    assert np.array_equal(independent_weights[0], final['adopted_weights'])
    assert independent_weight_hashes == tuple(final['weight_sha256'])

    gradient = np.asarray(problem['misfit'].deriv(q)
                          + problem['beta_engine']*independent_sparse.deriv(q))
    lower = admitted['prior']['lower_kg_m3']/1000.
    upper = admitted['prior']['upper_kg_m3']/1000.
    projected = gradient.copy()
    projected[(q <= lower) & (gradient > 0.)] = 0.
    projected[(q >= upper) & (gradient < 0.)] = 0.
    kkt_inf = float(np.linalg.norm(projected, ord=np.inf))
    smallness_hessian = independent_sparse.objfcts[0].deriv2(q)
    diagonal = np.asarray(smallness_hessian.diagonal(), dtype=np.float64)
    curvature_min = float(np.min(diagonal))
    convexity_lower_bound = float(problem['beta_engine']*curvature_min)
    assert np.isfinite(diagonal).all() and np.all(diagonal > 0.)
    assert kkt_inf <= 1e-12
    assert certificate['projected_kkt_inf'] == kkt_inf
    assert certificate['smallness_min_curvature'] == curvature_min
    assert certificate['strict_convexity_lower_bound'] == convexity_lower_bound > 0.
    assert certificate['weight_sha256'] == independent_weight_hashes
    assert certificate['model_sha256'] == survey._digest(q)
    assert certificate['source_inventory_sha256'] == workflow.engine._INVENTORY
