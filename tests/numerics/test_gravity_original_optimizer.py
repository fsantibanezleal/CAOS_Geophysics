"""Original physical controls, strict source recipe and same-clock native caps."""
from dataclasses import replace
from decimal import localcontext
from fractions import Fraction
import json
import os
from pathlib import Path
from time import monotonic

import choclo
import numpy as np
import pytest
from scipy.linalg import solve_triangular
from scipy.optimize import lsq_linear

import gravity_original_optimizer as public
from test_gravity_l2 import six_cell_control, tiny, noise, independent_r
from test_gravity_l2_selection import locked_request


def check_native(result):
    assert result['result']['status'] == 'converged', result['result']['reason']
    assert result['wall_seconds'] <= 120.
    r = result['result']
    assert r['iterations'] <= 200 and len(r['trace']['models_q']) <= 201
    counts = {}
    for c in r['conditioning_attempts']:
        assert c['failure'] is None and c['true_relative_residual'] <= 1e-6
        counts[c['iteration']] = counts.get(c['iteration'], 0)+c['iterations']
    assert max(counts.values(), default=0) <= 200
    assert all(c['trial'] < 20 for c in r['line_search_trials'])
    assert r['terminal_audits'][-1]['check']['passed']
    assert r['terminal_audits'][-1]['check']['disposed']
    assert r['terminal_audits'][-1]['check']['allocation']['maximum'] <= 2*1024**3
    assert result['identity']['beta_engine'] == len(result['fit_rows'])*result['beta_candidate']
    assert result['identity']['physical_scale'] == 1000.
    assert result['full_M02_accepted'] is result['host_accepted'] is False


@pytest.mark.parametrize('kind', ['diagonal_sd', 'full_covariance'])
@pytest.mark.parametrize('bound', [1500., 75.])
@pytest.mark.parametrize('start', ['zero', 'all_lower', 'all_upper', 'lower_upper',
    'upper_lower', 'lower_reference', 'upper_reference'])
def test_original_six_cell_same_science_and_native_limits(kind, bound, start):
    req, observed, spec, prior, jacobian, augmented, target = six_cell_control(kind, bound, start)
    result = public.solve_bounded_linear(req, observed, spec, prior,
        np.arange(5, dtype=np.int64), .01, deadline=monotonic()+120.)
    check_native(result)
    # Exactly the independent original Choclo/pairwise-R/Cholesky assertions.
    oracle = lsq_linear(augmented, target, bounds=(-bound/1000., bound/1000.),
        method='bvls', lsq_solver='exact', tol=1e-12, max_iter=1000)
    assert oracle.success
    q = result['result']['q']
    model_relative = np.linalg.norm(q-oracle.x)/max(1., np.linalg.norm(oracle.x))
    objective_relative = abs(np.linalg.norm(augmented@q-target)**2-2*oracle.cost)/max(1., 2*oracle.cost)
    prediction_absolute = np.max(np.abs(jacobian@((q-oracle.x)*1000.)))
    assert model_relative <= 1e-3 and objective_relative <= 1e-6 and prediction_absolute <= 1e-6
    assert np.max(np.abs((q-oracle.x)*1000.))/max(1., np.max(np.abs(oracle.x*1000.))) <= 1e-5
    assert prediction_absolute/max(1., np.max(np.abs(jacobian@(oracle.x*1000.)))) <= 1e-5
    np.testing.assert_array_equal(result['result']['trace']['models_q'][0], prior['start_kg_m3']/1000.)
    for state, phi in zip(result['result']['trace']['models_q'], result['result']['trace']['phi_engine']):
        np.testing.assert_allclose(phi, np.linalg.norm(augmented@state-target)**2, rtol=1e-10, atol=1e-12)


@pytest.mark.parametrize('ambient', [6, 28, 80])
def test_original_stored_precision_root_fraction_and_denial(ambient):
    # Actual native source construction, not an arbitrary root or inverse DTO.
    req, observed, prior, _, _ = tiny()
    rows = np.arange(4, dtype=np.int64)
    spec = noise()
    problem = public.physics._build_problem(req, observed, spec, prior, rows, .01)
    allocation = {'allocation_plan_sha256': 'c'*64, 'admitted_bytes': 2*1024**3}
    adapter = public._Objective(problem, prior, spec, rows, public.source_inventory(), allocation)
    q = np.array([.1, -.2, .3, -.4, .5])
    o = adapter.quadratic_operands(q)
    identity = adapter.identity()
    budget = dict(deadline=monotonic()+120., resource_limit_bytes=2*1024**3, admitted_bytes=2*1024**3)
    assert o.whitening.kind == 'stored_symmetric_precision_root'
    with localcontext() as c:
        c.prec = ambient
        enclosed = public.source.source_gradient(o, identity, q, **budget)
    def mv(a, v):
        return [sum(Fraction(float(x))*y for x, y in zip(row, v)) for row in a]
    fq = list(map(lambda v: Fraction(float(v)), q))
    residual = [v-Fraction(float(d)) for v, d in zip(mv(o.sensitivity, fq), o.observations)]
    expected = [2*v for v in mv(o.sensitivity.T, mv(o.whitening.values.T, mv(o.whitening.values, residual)))]
    delta = [v-Fraction(float(r)) for v, r in zip(fq, o.reference)]
    for t in o.terms:
        v = mv(t.derivative.T.toarray(), mv(t.weights.T.toarray(), mv(t.weights.toarray(), mv(t.derivative.toarray(), delta))))
        expected = [old+2*Fraction(o.beta)*Fraction(t.alpha)*x for old, x in zip(expected, v)]
    for v, (lo, hi) in zip(expected, enclosed):
        assert Fraction(lo) <= v <= Fraction(hi)
    changed = o.whitening.values.copy()
    changed[0, 0] = np.nextafter(changed[0, 0], np.inf)
    with pytest.raises(ValueError, match='symmetric precision root mismatch'):
        public.source.validate(replace(o, whitening=replace(o.whitening, values=changed)), identity, q, **budget)
    with pytest.raises(ValueError, match='Cholesky mismatch'):
        public.source.validate(replace(o, whitening=replace(o.whitening, kind='stored_lower_cholesky')), identity, q, **budget)


def test_no_optimizer_or_spd_injection_and_expired_clock(monkeypatch):
    req, observed, prior, _, _ = tiny()
    rows = np.arange(4, dtype=np.int64)
    monkeypatch.setattr(public.physics, '_build_problem', lambda *a, **k: pytest.fail('expired clock constructed native source'))
    with pytest.raises(public.physics.metric.DeadlineExceeded):
        public.solve_bounded_linear(req, observed, noise(), prior, rows, .01, deadline=monotonic()-1.)
    with pytest.raises(TypeError):
        public.solve_bounded_linear(req, observed, noise(), prior, rows, .01,
            deadline=monotonic()+120., metric=lambda x: x)


def test_resource_dictionary_is_a_sum_not_an_arbitrary_allowance():
    p = public.allocation_plan(4, 4, 12, True)
    expected = p['original_native']['maximum']+sum(p['source_arithmetic'].values())
    expected += sum(p['retained_audits'].values())+sum(p['terminal'].values())
    assert p['admitted_bytes'] == expected < p['original_limit_bytes'] == 2*1024**3
    assert p['CG'] == p['accepted'] == 200 and p['states'] == 201 and p['LS'] == 20
    with pytest.raises(ValueError):
        public.allocation_plan(2048, 2048, 4096, True)


def test_original_lowbeta_nonzero_initialization_prerequisite(record_property):
    req, observed, prior, _, _ = tiny()
    req['mesh']['active'][:] = True
    for key, value in [('lower_kg_m3', -1500.), ('upper_kg_m3', 1500.),
        ('start_kg_m3', 0.), ('reference_kg_m3', 0.)]:
        prior[key] = np.full(12, value)
    result = public.solve_bounded_linear(req, observed, noise(), prior,
        np.arange(4, dtype=np.int64), .0001, deadline=monotonic()+120.)
    record_property('result', repr(result['result']))
    check_native(result)


def serial(value):
    if type(value) is np.ndarray:
        return value.tolist()
    if type(value) is dict:
        return {k: serial(v) for k, v in value.items()}
    if type(value) in (tuple, list):
        return [serial(v) for v in value]
    return value


def test_original_locked_firstfold_accuracy():
    """ONE changed-source actual48-cell original24 prerequisite, no dependent retry."""
    request, _, _ = locked_request(0, 0)
    plan, prior = request['plan'], request['prior']
    rows, development = plan['folds'][0]['fit_rows'], plan['development_rows']
    observed = request['observations']['gz_up_mgal']
    spec = {k: request['noise'][k] for k in ('kind', 'values')}
    output = Path(os.environ['GEOPHYSICS_M02_GRAVITY_FIRSTFOLD_RECEIPT']).resolve()
    if output.exists() or any((p/'.git').exists() for p in output.parents):
        raise ValueError('new external immutable gravity firstfold receipt required')
    receipt = dict(schema='gravity-original48-firstfold-accuracy-1', accepted=False,
        input_sha256=public.physics.survey._digest(request), result=None, errors=None,
        original_family=0, original_condition=0, original_seed=700001, original_beta=.0001)
    try:
        result = public.solve_bounded_linear(plan['request'], observed, spec, prior, rows, .0001,
            observation_rows=development, deadline=monotonic()+120.)
        receipt['result'] = result
        check_native(result)
        assert len(result['result']['q']) == 48
        bounds = plan['geometry']['active_cell_bounds_m']
        points = plan['request']['stations']['receivers_m'][rows]
        j = np.array([[choclo.prism.gravity_u(*p, *b, 1.)*1e5 for b in bounds] for p in points])
        r = independent_r(bounds, prior['lengths_m'], prior['density_scale_kg_m3']/1000.)
        positions = np.searchsorted(development, rows)
        covariance = (spec['values'][np.ix_(positions, positions)] if spec['kind'] == 'full_covariance'
            else np.diag(spec['values'][positions]**2))
        l = np.linalg.cholesky(covariance)
        factor = np.vstack([solve_triangular(l, j*1000., lower=True), np.sqrt(len(rows)*.0001)*r])
        rhs = np.r_[solve_triangular(l, observed[positions]-plan['request']['background_mgal'][rows], lower=True),
            np.sqrt(len(rows)*.0001)*r@(prior['reference_kg_m3']/1000.)]
        oracle = lsq_linear(factor, rhs, bounds=(prior['lower_kg_m3']/1000., prior['upper_kg_m3']/1000.),
            method='bvls', lsq_solver='exact', tol=1e-12, max_iter=1000)
        assert oracle.success
        q = result['result']['q']
        error = q-oracle.x
        errors = dict(model_relative=float(np.linalg.norm(error)/max(1., np.linalg.norm(oracle.x))),
            model_physical_relative=float(np.max(abs(error*1000.))/max(1., np.max(abs(oracle.x*1000.)))),
            objective_relative=float(abs(np.linalg.norm(factor@q-rhs)**2-2*oracle.cost)/max(1., 2*oracle.cost)),
            physical_prediction_absolute=float(np.max(abs(j@(1000.*error)))))
        receipt['errors'] = errors
        assert errors['model_relative'] <= 1e-3
        assert errors['model_physical_relative'] <= 1e-5
        assert errors['objective_relative'] <= 1e-6
        assert errors['physical_prediction_absolute'] <= 1e-6
        receipt['accepted'] = True
    finally:
        with output.open('x', encoding='utf-8') as handle:
            json.dump(serial(receipt), handle, sort_keys=True, allow_nan=False)
