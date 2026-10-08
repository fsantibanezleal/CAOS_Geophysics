"""Actual full corrected IRLS calibration/refit/frozen evaluation.

Same original shapes/candidates/scientific thresholds/caps. Failed fits retained,
outer values sealed until frozen evaluation, shallow typed evidence pools.
"""
import hashlib
from pathlib import Path
from time import monotonic

import numpy as np

import gravity_irls as plain
import gravity_irls_corrected as corrected
import gravity_irls_pool as pool


l2, survey = plain.l2, plain.survey
REQUEST_SCHEMA = 'gravity-survey-irls-corrected-calibration-request-1'
RESULT_SCHEMA = 'gravity-survey-irls-corrected-calibration-result-1'
EVALUATION_SCHEMA = 'gravity-survey-irls-corrected-evaluation-request-1'
SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
_SOURCES = dict(corrected._SOURCES, gravity_irls_pool=pool.SOURCE_SHA256,
                gravity_irls_corrected_workflow=SOURCE_SHA256)


def admit(request):
    survey._native_metadata(request)
    survey._keys(request, ('schema', 'plan', 'observations', 'noise', 'prior', 'policy', 'runtime_epoch'), 'corrected workflow')
    survey._enum(request['schema'], REQUEST_SCHEMA, 'corrected request schema')
    survey._enum(request['runtime_epoch'], corrected.RUNTIME_EPOCH, 'corrected workflow epoch')
    survey._keys(request['policy'], ('name', 'beta_candidates', 'optimizer', 'training', 'irls'), 'corrected policy')
    survey._enum(request['policy']['name'], corrected.POLICY, 'corrected policy name')
    projected = dict(request, schema='gravity-survey-irls-calibration-request-1', runtime_epoch=plain.RUNTIME_EPOCH,
                     policy=dict(request['policy'], name=plain.POLICY))
    # Original strict geometry/units/source/partition/value/noise/prior admission,
    # not a plain solver invocation or accepting a plain archive as corrected.
    accepted = plain._admit_request(projected)
    accepted.update(schema=REQUEST_SCHEMA, runtime_epoch=corrected.RUNTIME_EPOCH,
                    policy=survey._snapshot(request['policy']))
    return accepted


def _unstarted(rows, beta, reason):
    return dict(schema='gravity-corrected-unstarted-1', status='nonconverged' if reason == 'wall_cap' else 'failed',
                reason=reason, fit_rows=survey._readonly(rows), beta_candidate=beta,
                iterations=0, model_kg_m3=None)


def _fit(admitted, rows, beta, deadline):
    started = monotonic()
    if started > deadline:
        return pool.encode(_unstarted(rows, beta, 'wall_cap'))
    req, prior = admitted['plan']['request'], admitted['prior']
    problem = None
    try:
        problem = l2._build_problem(req, admitted['observations']['gz_up_mgal'],
            {k:admitted['noise'][k] for k in ('kind', 'values')}, prior, rows, beta,
            observation_rows=admitted['plan']['development_rows'])
        result = corrected.solve_partition(problem, prior, admitted['policy']['irls'], min(deadline, started+120.))
        return pool.encode(result)
    except (ValueError, RuntimeError, ArithmeticError) as error:
        # An actual source/setup/whole-cap failure is never a dummy native fit.
        if problem is not None:
            raise
        reason = 'wall_cap' if monotonic() > deadline else 'nonfinite' if isinstance(error, ArithmeticError) else 'engine_error'
        return pool.encode(_unstarted(rows, beta, reason))


def _summary(raw):
    return (raw['status'], raw['reason'], 0, None) if raw['schema'] == 'gravity-corrected-unstarted-1' else (
        raw['terminal']['status'], raw['terminal']['reason'], raw['iterations'], raw['model_kg_m3'])


def calibrate(request):
    started = monotonic()
    accepted = admit(request)
    deadline = started+1800.
    plan, prior = accepted['plan'], accepted['prior']
    req, development = plan['request'], plan['development_rows']
    observed = accepted['observations']['gz_up_mgal']
    noise = {k:accepted['noise'][k] for k in ('kind', 'values')}
    l2._weights(noise, np.arange(len(development), dtype=np.int64))
    diagnostics = l2._fit_diagnostics(req, noise, observed, prior, plan)
    fits, candidates = [], []
    for index, beta in enumerate(l2.BETA_CANDIDATES):
        folds = []
        for fold in plan['folds']:
            packed = _fit(accepted, fold['fit_rows'], beta, deadline)
            fit_index = len(fits)
            fits.append(packed)
            raw = pool.decode(packed)
            status, reason, _, model = _summary(raw)
            metrics = (None, None, None)
            if status == 'converged' and monotonic() <= deadline:
                try:
                    prediction = l2._bounded_prediction(req, model, deadline)
                    positions = np.searchsorted(development, fold['validation_rows'])
                    measured = l2._marginal_metrics(prediction[fold['validation_rows']], observed[positions], noise, positions)
                    if monotonic() <= deadline:
                        metrics = measured[:3]
                except (ValueError, RuntimeError, ArithmeticError):
                    pass
            folds.append(dict(fold=fold['fold'], solve=fit_index, status=status, reason=reason,
                validation_rows=survey._readonly(fold['validation_rows']), validation_phi_d=metrics[0],
                validation_wrms=metrics[1], validation_rmse_mgal=metrics[2]))
            raw = None
        valid = all(f['status'] == 'converged' for f in folds)
        scored = valid and all(f['validation_phi_d'] is not None for f in folds)
        score = float(sum(f['validation_phi_d'] for f in folds)/sum(len(f['validation_rows']) for f in folds)) if scored else None
        candidates.append(dict(index=index, beta_candidate=beta, eligible=bool(scored), folds=tuple(folds),
            score_q=score, reason='eligible' if scored else 'invalid_score' if valid else 'fold_failure'))
    selected = l2._selected_index(candidates)
    final, prediction, status = None, None, 'insufficient_candidates'
    if selected is not None:
        fits.append(_fit(accepted, development, l2.BETA_CANDIDATES[selected], deadline))
        final = 24
        raw = pool.decode(fits[24])
        final_status, _, _, model = _summary(raw)
        status = 'selected' if final_status == 'converged' else 'final_nonconverged'
        if model is not None:
            try:
                prediction = l2._bounded_prediction(req, model, deadline)
            except (ValueError, RuntimeError, ArithmeticError):
                status = 'final_prediction_failed'
        raw = None
    result = dict(schema=RESULT_SCHEMA, plan=plan, candidates=tuple(candidates), fits=tuple(fits),
        selected_index=selected, selection_status=status, final_solve=final,
        predictions=dict(rows=survey._readonly(np.arange(len(req['background_mgal']), dtype=np.int64)),
                         gz_up_mgal=survey._readonly(prediction) if prediction is not None else None),
        diagnostics=diagnostics, source_inventory=_SOURCES, request_sha256=survey._digest(request),
        runtime_epoch=corrected.RUNTIME_EPOCH, policy=corrected.POLICY, wall_seconds=float(monotonic()-started),
        scope=dict(field_eligible=False, full_M02_accepted=False, API_accepted=False, GPU_accepted=False,
                   host_accepted=False, geometry_error='not_propagated', training='not_applicable_classical'))
    l2._result_native_metadata(result)
    result['result_sha256'] = survey._digest(result)
    l2._result_native_metadata(result)
    return result


def validate(result, request):
    l2._result_native_metadata(dict(result=result, request=request))
    survey._keys(result, ('schema', 'plan', 'candidates', 'fits', 'selected_index', 'selection_status', 'final_solve',
        'predictions', 'diagnostics', 'source_inventory', 'request_sha256', 'runtime_epoch', 'policy', 'wall_seconds',
        'scope', 'result_sha256'), 'corrected calibration result')
    accepted = admit(request)
    if (result['schema'] != RESULT_SCHEMA or result['runtime_epoch'] != corrected.RUNTIME_EPOCH
        or result['policy'] != corrected.POLICY or result['source_inventory'] != _SOURCES
        or result['request_sha256'] != survey._digest(request)
        or result['result_sha256'] != survey._digest({k:v for k,v in result.items() if k != 'result_sha256'})
        or survey._digest(result['plan']) != survey._digest(accepted['plan'])
        or type(result['wall_seconds']) is not float or result['wall_seconds'] < 0.):
        raise ValueError('corrected calibration: whole original source/request/plan/result binding')
    survey._finite(result)
    for key in ('selected_index', 'final_solve'):
        if result[key] is not None and type(result[key]) is not int:
            raise ValueError('corrected calibration: literal selection index')
    survey._keys(result['predictions'], ('rows', 'gz_up_mgal'), 'corrected predictions')
    if type(result['fits']) is not tuple or len(result['fits']) not in (24, 25) or type(result['candidates']) is not tuple or len(result['candidates']) != 8:
        raise ValueError('corrected calibration: original8x3 plus selectedrefit')
    plan = accepted['plan']
    noise = {k:accepted['noise'][k] for k in ('kind', 'values')}
    def replay(index, rows, beta):
        raw = pool.decode(result['fits'][index])
        if raw['schema'] == 'gravity-corrected-unstarted-1':
            survey._keys(raw, ('schema', 'status', 'reason', 'fit_rows', 'beta_candidate', 'iterations', 'model_kg_m3'), 'explicit unstarted fit')
            if (raw['status'] not in ('failed', 'nonconverged') or raw['reason'] not in ('wall_cap', 'engine_error', 'nonfinite')
                or type(raw['iterations']) is not int or raw['iterations'] != 0
                or type(raw['beta_candidate']) is not float or raw['model_kg_m3'] is not None or raw['beta_candidate'] != beta
                or not np.array_equal(raw['fit_rows'], rows)):
                raise ValueError('corrected calibration: unavailable state/science substitution')
        else:
            problem = l2._build_problem(plan['request'], accepted['observations']['gz_up_mgal'], noise,
                accepted['prior'], rows, beta, observation_rows=plan['development_rows'])
            corrected.validate_partition(raw, problem, accepted['prior'], accepted['policy']['irls'])
        return _summary(raw)
    for index, candidate in enumerate(result['candidates']):
        survey._keys(candidate, ('index', 'beta_candidate', 'eligible', 'folds', 'score_q', 'reason'), 'corrected candidate')
        if (type(candidate['index']) is not int or type(candidate['eligible']) is not bool
            or type(candidate['beta_candidate']) is not float or type(candidate['folds']) is not tuple
            or candidate['index'] != index or candidate['beta_candidate'] != l2.BETA_CANDIDATES[index] or len(candidate['folds']) != 3):
            raise ValueError('corrected calibration: unchanged original candidate recipe')
        for j, (fold, original) in enumerate(zip(candidate['folds'], plan['folds'])):
            survey._keys(fold, ('fold', 'solve', 'status', 'reason', 'validation_rows', 'validation_phi_d', 'validation_wrms',
                               'validation_rmse_mgal'), 'corrected fold')
            if (type(fold['fold']) is not int or type(fold['solve']) is not int
                or fold['fold'] != original['fold'] or fold['solve'] != 3*index+j or not np.array_equal(fold['validation_rows'], original['validation_rows'])):
                raise ValueError('corrected calibration: original sealed partition')
            status, reason, _, model = replay(fold['solve'], original['fit_rows'], l2.BETA_CANDIDATES[index])
            if (status, reason) != (fold['status'], fold['reason']):
                raise ValueError('corrected calibration: actual retained status')
            if fold['validation_phi_d'] is not None:
                if status != 'converged':
                    raise ValueError('corrected calibration: failed fold scored')
                prediction = l2._physical_prediction(plan['request'], model)
                positions = np.searchsorted(plan['development_rows'], original['validation_rows'])
                metrics = l2._marginal_metrics(prediction[original['validation_rows']],
                    accepted['observations']['gz_up_mgal'][positions], noise, positions)
                plain._close(metrics[:3], tuple(fold[k] for k in ('validation_phi_d', 'validation_wrms', 'validation_rmse_mgal')), 'original score')
            elif fold['validation_wrms'] is not None or fold['validation_rmse_mgal'] is not None:
                raise ValueError('corrected calibration: incomplete unavailable score')
        valid = all(f['status'] == 'converged' for f in candidate['folds'])
        eligible = valid and all(f['validation_phi_d'] is not None for f in candidate['folds'])
        score = float(sum(f['validation_phi_d'] for f in candidate['folds'])/sum(len(f['validation_rows']) for f in candidate['folds'])) if eligible else None
        if (candidate['eligible'], candidate['score_q'], candidate['reason']) != (eligible, score, 'eligible' if eligible else 'invalid_score' if valid else 'fold_failure'):
            raise ValueError('corrected calibration: complete-fold eligibility')
    selected = l2._selected_index(result['candidates'])
    if selected != result['selected_index'] or len(result['fits']) != 24+(selected is not None):
        raise ValueError('corrected calibration: unchanged selection/refit')
    if selected is None:
        if result['selection_status'] != 'insufficient_candidates' or result['final_solve'] is not None or result['predictions']['gz_up_mgal'] is not None:
            raise ValueError('corrected calibration: unselected final state')
    else:
        status, _, _, model = replay(24, plan['development_rows'], l2.BETA_CANDIDATES[selected])
        expected = 'selected' if status == 'converged' else 'final_nonconverged'
        if result['final_solve'] != 24 or result['selection_status'] not in (expected, 'final_prediction_failed'):
            raise ValueError('corrected calibration: actual final refit')
        prediction = result['predictions']['gz_up_mgal']
        if prediction is not None:
            plain._close(l2._physical_prediction(plan['request'], model), prediction, 'actual final physical prediction')
        elif result['selection_status'] == 'selected':
            raise ValueError('corrected calibration: unavailable selected prediction')
    if not np.array_equal(result['predictions']['rows'], np.arange(len(plan['request']['background_mgal']), dtype=np.int64)):
        raise ValueError('corrected calibration: original prediction row order')
    if survey._digest(result['diagnostics']) != survey._digest(l2._fit_diagnostics(plan['request'], noise,
        accepted['observations']['gz_up_mgal'], accepted['prior'], plan)):
        raise ValueError('corrected calibration: original physical diagnostics')
    if (any(type(result['scope'].get(k)) is not bool for k in (
            'field_eligible', 'full_M02_accepted', 'API_accepted', 'GPU_accepted', 'host_accepted'))
        or result['scope'] != dict(field_eligible=False, full_M02_accepted=False, API_accepted=False, GPU_accepted=False,
        host_accepted=False, geometry_error='not_propagated', training='not_applicable_classical')):
        raise ValueError('corrected calibration: no stronger scope claim')
    return result


def evaluate(request):
    """Frozen outer marginal only, no fit/solver/recipe choice."""
    l2._result_native_metadata(request)
    survey._keys(request, ('schema', 'frozen_calibration', 'calibration_request', 'observations', 'noise'), 'corrected evaluation')
    survey._enum(request['schema'], EVALUATION_SCHEMA, 'corrected evaluation epoch')
    frozen = validate(request['frozen_calibration'], request['calibration_request'])
    if frozen['selection_status'] != 'selected':
        raise ValueError('corrected evaluation: unsuccessful frozen calibration')
    # Original public frozen marginal admits observations/noise without any
    # optimizer call. Closed lightweight projection is NEVER a corrected result
    # admission or method upgrade; original observed/hash/units gates reused.
    rows, observed, noise = frozen['plan']['outer_rows'], request['observations'], request['noise']
    survey._keys(observed, ('rows', 'gz_up_mgal', 'values_sha256', 'acceleration_unit', 'vertical_positive'), 'outer observations')
    survey._array(observed['rows'], rows.shape, 'outer rows', np.int64)
    survey._array(observed['gz_up_mgal'], rows.shape, 'outer observations')
    survey._enum(observed['acceleration_unit'], 'mGal', 'outer acceleration')
    survey._enum(observed['vertical_positive'], 'up', 'outer sign')
    survey._keys(noise, ('kind', 'values', 'unit', 'basis', 'citation', 'values_sha256', 'cross_partition_dependence'), 'outer noise')
    survey._enum(noise['kind'], ('diagonal_sd', 'full_covariance'), 'outer noise kind')
    covariance = noise['kind'] == 'full_covariance'
    survey._array(noise['values'], (len(rows), len(rows)) if covariance else rows.shape, 'outer noise values')
    survey._enum(noise['unit'], 'mGal^2' if covariance else 'mGal', 'outer noise units')
    survey._enum(noise['basis'], ('measured_gaussian', 'propagated_independent_gaussian', 'explicit_conditional_gaussian'), 'outer basis')
    survey._enum(noise['cross_partition_dependence'], ('declared_absent', 'possible_not_removed'), 'outer dependence')
    survey._text(noise['citation'], 'outer noise citation')
    survey._finite(dict(observations=observed, noise=noise))
    if (not np.array_equal(rows, observed['rows'])
        or observed['values_sha256'] != survey._digest({k:v for k,v in observed.items() if k != 'values_sha256'})
        or noise['values_sha256'] != survey._digest({k:noise[k] for k in ('kind', 'unit', 'values')} | {'rows':rows})):
        raise ValueError('corrected evaluation: original outer values/noise identity')
    prediction = survey._readonly(frozen['predictions']['gz_up_mgal'][rows])
    phi, wrms, rmse, residual, whitened = l2._marginal_metrics(prediction, observed['gz_up_mgal'],
        {k:noise[k] for k in ('kind', 'values')}, np.arange(len(rows), dtype=np.int64))
    result = dict(schema='gravity-survey-irls-corrected-evaluation-result-1', calibration_sha256=frozen['result_sha256'],
        observations=survey._snapshot(observed), noise_sha256=noise['values_sha256'], rows=survey._readonly(rows),
        predicted_mgal=prediction, residual_observed_minus_predicted_mgal=survey._readonly(residual),
        whitened_residual=survey._readonly(whitened), phi_d=phi, wrms=wrms, rmse_mgal=rmse,
        prediction_quality='within_declared_noise' if wrms <= 2. else 'poor_under_declared_noise',
        dependence=noise['cross_partition_dependence'], geometry_conditioning='fixed_not_propagated',
        field_truth=None, model_accuracy=None, field_eligible=False, full_M02_accepted=False)
    result['result_sha256'] = survey._digest(result)
    l2._result_native_metadata(dict(evaluation=result, frozen=frozen))
    return result
