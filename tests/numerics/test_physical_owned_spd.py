"""Actual native physics/CG and independent tiny oracle; no production oracle."""
from dataclasses import replace
from decimal import Decimal
from time import monotonic

import numpy as np
import pytest
import scipy.sparse as sp
from scipy.optimize import lsq_linear

import physical_conditioned_optimizer as core
import physical_owned_spd as owned
import gravity_l2_precision as precision
from test_physical_optimizer import NativeObjective
from test_physical_nonlinear_optimizer import ActualObjective


class Physical(NativeObjective):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.identity_value['runtime_epoch'] = core.LINEAR_EPOCH

    def metric_operands(self, q):
        problem = self.problem
        return owned.MetricOperands(owned.binding_for(self.identity(), q), 4, 4, 5, True,
            (self.beta*problem['regularization'].deriv2(q)).tocsr().sorted_indices(),
            np.ascontiguousarray(problem['misfit'].W@problem['simulation'].G))

    def quadratic_operands(self, q):
        problem = self.problem
        reg = problem['regularization']
        terms = tuple(owned.QuadraticTerm(float(alpha), child.W.tocsr(),
            child.f_m_deriv(problem['reference_q']).tocsr())
            for alpha, child in zip(reg.multipliers, reg.objfcts) if alpha > 0. and child.W.shape[0])
        return owned.QuadraticOperands(owned.binding_for(self.identity(), q),
            problem['simulation'].G, problem['misfit'].W.tocsr(), problem['misfit'].data.dobs,
            problem['reference_q'], 1., self.beta, terms, problem['simulation'].G)


class NonlinearPhysical(ActualObjective):
    """Real installed physical objective, couplingZERO explicitly, not exempted."""
    def __init__(self):
        super().__init__()
        self.weight = 0.
        h = self.hessian(self.start, False)
        self.diag = np.array([(h@np.eye(len(self.start))[i])[i] for i in range(len(self.start))])
        self.requests = []

    def identity(self):
        return dict(super().identity(), runtime_epoch=core.NONLINEAR_EPOCH)

    def metric_operands(self, q):
        self.requests.append(q.copy())
        return owned.MetricOperands(owned.binding_for(self.identity(), q), 3, 3, len(q), False,
            sp.diags(np.full(len(q), self.beta), format='csr'), self.A, .5)


def arguments(obj, *, steps=None, kkt=1e-7, bounds=False, deadline=None):
    identity = obj.identity()
    linear = identity['mode'] == 'fixed_linear_quadratic'
    binding = core.ConditionedBinding('physical_conditioned_optimizer.'+('solve_bounded_linear' if linear else 'solve_bounded_nonlinear'),
        core.SOURCE_SHA256, owned.SOURCE_SHA256, owned.KERNEL_SHA256, core.VENDOR_SOURCE_SHA256,
        __import__('hashlib').sha256(__import__('pathlib').Path(precision.__file__).read_bytes()).hexdigest(),
        identity['source_inventory_sha256'], identity['runtime_epoch'], core.POLICY)
    budget = core.ConditionedBudget(monotonic()+120. if deadline is None else deadline,
        (200 if linear else 250) if steps is None else steps, 2*1024**3, 2*1024**3,
        identity['allocation_plan_sha256'])
    terminal = owned.TerminalPolicy(kkt, 1e-5 if bounds else None, 1e-8 if bounds else None, 1e-8 if bounds else None)
    return dict(budget=budget, binding=binding, terminal=terminal)


def run(obj, **kwargs):
    fn = core.solve_bounded_linear if obj.identity()['mode'] == 'fixed_linear_quadratic' else core.solve_bounded_nonlinear
    lower, upper = (obj.lower, obj.upper) if isinstance(obj, Physical) else (np.zeros(len(obj.start)), np.ones(len(obj.start)))
    return fn(obj, lower, upper, obj.start, **arguments(obj, **kwargs))


@pytest.mark.parametrize('fault', ['callback', 'model', 'count', 'csr', 'jitter_graph', 'native', 'plan'])
def test_closed_operands(fault, monkeypatch):
    obj = Physical()
    actual = obj.metric_operands
    def wrong(q):
        value = actual(q)
        if fault == 'callback':
            return lambda v: v
        if fault == 'model':
            return replace(value, binding=replace(value.binding, model_sha256='f'*64))
        if fault == 'count':
            return replace(value, fit_components=2)
        if fault == 'csr':
            value.regularizer.indptr[-1] += 1
        if fault == 'jitter_graph':
            value.regularizer.data[value.regularizer.indices != np.repeat(np.arange(5), np.diff(value.regularizer.indptr))] = 1.
        return value
    obj.metric_operands = wrong
    if fault == 'native':
        monkeypatch.setattr(owned.kernel, '_LOADED_PINS', ('x', 'y', 'z'))
    args = arguments(obj)
    if fault == 'plan':
        args['budget'] = replace(args['budget'], admitted_bytes=1)
    result = core.solve_bounded_linear(obj, obj.lower, obj.upper, obj.start, **args)
    assert result['status'] != 'converged' and result['reason'] == 'metric_construction_failed', result
    assert result['iterations'] == 0 and len(result['trace']['models_q']) == 1
    assert len(result['conditioning_attempts']) == 1 and result['conditioning_attempts'][0]['failure']
    assert obj.released == 1


def test_original_resource_dictionary():
    identity = dict(Physical().identity(), parameter_count=528, observation_rows=144, observation_components=3)
    q = np.zeros(528)
    dto = owned.MetricOperands(owned.binding_for(identity, q), 864, 432, 528, False,
        sp.eye(528, format='csr'), np.zeros((432, 528)))
    allocation = owned.validate_operands(dto, identity, q, 805306368)
    assert allocation['setup'] == 674078720 and allocation['action'] == 645446928
    assert allocation['line_search'] == 761838864 and allocation['maximum'] < 805306368
    with pytest.raises(ValueError):
        owned.validate_operands(replace(dto, fit_components=216), identity, q, 805306368)
    with pytest.raises(ValueError):
        owned.validate_operands(dto, identity, q, allocation['maximum']-1)


@pytest.mark.parametrize('nonlinear', [False, True])
def test_native_caps_and_residual(monkeypatch, nonlinear):
    obj = NonlinearPhysical() if nonlinear else Physical()
    actual = core.optimization.ProjectedGNCG.findSearchDirection
    calls = []
    def observe(opt):
        calls.append((opt.cg_maxiter, opt.cg_rtol, opt.cg_atol, opt.maxIterLS, opt.maxIter))
        return actual(opt)
    monkeypatch.setattr(core.optimization.ProjectedGNCG, 'findSearchDirection', observe)
    result = run(obj)
    assert result['status'] == 'converged', result['reason']
    assert calls and all(c == ((512, 1e-6, 0., 30, 250) if nonlinear else (200, 1e-6, 0., 20, 200)) for c in calls)
    for row in result['conditioning_attempts']:
        if row['branch'] == 'cg':
            assert row['true_relative_residual'] <= 1e-6 and row['iterations'] <= (512 if nonlinear else 200)
            assert row['metric_actions'] > 0 and row['payload_bytes'] > 0
    assert result['terminal_audits'][-1]['check']['passed']


def test_refresh_disposal_failure(monkeypatch):
    live = []
    actual = owned.OwnedMetric
    class Observed(actual):
        def __init__(self, *args, **kwargs):
            assert all(m.live_payload_bytes == 0 for m in live)
            super().__init__(*args, **kwargs)
            live.append(self)
    monkeypatch.setattr(owned, 'OwnedMetric', Observed)
    obj = NonlinearPhysical()
    result = run(obj, steps=200)
    assert result['status'] == 'converged' and live
    assert all(m.live_payload_bytes == 0 for m in live)
    cg_rows = [row for row in result['conditioning_attempts'] if row['branch'] == 'cg']
    assert all(any(np.array_equal(row['q'], q) for q in obj.requests) for row in cg_rows)
    if len(cg_rows) > 1:
        assert cg_rows[0]['operand_sha256'] != cg_rows[1]['operand_sha256']


def test_failed_true_residual_retained(monkeypatch):
    obj = Physical()
    monkeypatch.setattr(core.optimization.ProjectedGNCG, 'findSearchDirection', lambda opt: -opt.g*1e-12)
    result = run(obj)
    assert result['reason'] == 'cg_cap' and result['iterations'] == 0
    row = result['conditioning_attempts'][0]
    assert row['direction'] is not None and row['true_relative_residual'] > 1e-6 and row['failure'] == 'cg_cap'


@pytest.mark.parametrize('bounded', [False, True])
def test_terminal_bounds(bounded):
    obj = Physical(bounded=bounded)
    # A feasible native state, ORIGINAL independent tiny bounded least-squares
    # oracle only; it is never used by either production export.
    g, w, beta = obj.problem['simulation'].G, obj.problem['misfit'].W.toarray(), obj.beta
    matrix = np.vstack((w@g, np.sqrt(beta)*obj.r))
    rhs = np.r_[w@obj.problem['misfit'].data.dobs, np.sqrt(beta)*obj.r@obj.problem['reference_q']]
    oracle = lsq_linear(matrix, rhs, bounds=(obj.lower, obj.upper), method='bvls', tol=1e-13)
    assert oracle.success
    q = .75*oracle.x+.25*obj.start
    bounds = owned.quadratic_bounds(obj.quadratic_operands(q), obj.identity(), q, obj.lower, obj.upper, monotonic()+120., 4)
    assert np.linalg.norm(q-oracle.x) <= float(Decimal(bounds['model_error_upper']))
    assert max(abs(g@(q-oracle.x))) <= float(Decimal(bounds['physical_prediction_error_upper']))
    assert obj.components(q)['phi_engine']-obj.components(oracle.x)['phi_engine'] <= float(Decimal(bounds['objective_gap_upper']))
    assert Decimal(bounds['mu_lower']) > 0
    with pytest.raises(ValueError, match='nonlinear GN'):
        owned.terminal_check(owned.TerminalPolicy(1e-7, model_error_limit=1e-5), q, np.zeros(5), obj.lower, obj.upper,
            1., identity=dict(obj.identity(), mode='nonlinear_gauss_newton'), deadline=monotonic()+120.)


@pytest.mark.parametrize('bounded', [False, True])
def test_original_physical_fit(bounded):
    obj = Physical(bounded=bounded)
    result = run(obj, bounds=True)
    assert result['status'] == 'converged', result['reason']
    assert result['iterations'] <= 200 and len(result['trace']['models_q']) == result['iterations']+1
    assert result['terminal_audits'][-1]['check']['passed']
    assert all(c['decision'] != 'certified_accept' or Decimal(c['armijo_margin_interval'][1]) < 0 for c in obj.certificates)
    assert obj.released == 1


def test_zero_caps_no_restart_and_pg_precedes_factor(monkeypatch):
    obj = Physical()
    result = run(obj, steps=0)
    assert result['reason'] == 'iteration_cap' and result['iterations'] == 0 and not result['conditioning_attempts']
    expired = run(Physical(), deadline=monotonic()-1.)
    assert expired['reason'] == 'wall_cap' and expired['q'] is None
    obj = Physical(bounded=True)
    obj.start[:] = obj.lower
    result = run(obj)
    assert result['conditioning_attempts'][0]['branch'] == 'pg'
    assert result['conditioning_attempts'][0]['metric_actions'] == 0


def test_no_callback_terminal_approval():
    obj = Physical()
    with pytest.raises(ValueError):
        core.solve_bounded_linear(obj, obj.lower, obj.upper, obj.start,
            **dict(arguments(obj), terminal=lambda *args: True))
    assert obj.calls == 0


def test_original_half_normalization_and_no_tuning():
    obj = NonlinearPhysical()
    dto = obj.metric_operands(obj.start)
    assert dto.likelihood_scale == .5 and np.array_equal(dto.whitened_jacobian, obj.A)
    h = obj.evaluate(obj.start, False, True)[1]
    v = np.linspace(-.2, .3, len(obj.start))
    np.testing.assert_allclose(h@v, dto.regularizer@v+2*dto.likelihood_scale*dto.whitened_jacobian.T@(dto.whitened_jacobian@v),
                               rtol=1e-14, atol=1e-15)
    with pytest.raises(ValueError):
        owned.validate_operands(replace(dto, likelihood_scale=.51), obj.identity(), obj.start, 2*1024**3)


@pytest.mark.parametrize('nonlinear', [False, True])
def test_deadline_after_actual_acceptance_retains_step(monkeypatch, nonlinear):
    obj = NonlinearPhysical() if nonlinear else Physical()
    clock = [monotonic()]
    for module in (core, core.linear, core.nonlinear, owned.kernel):
        monkeypatch.setattr(module, 'monotonic', lambda: clock[0])
    original = core.optimization.ProjectedGNCG.doEndIteration
    def expired_after_acceptance(opt, q):
        original(opt, q)
        clock[0] += 1801. if nonlinear else 121.
    monkeypatch.setattr(core.optimization.ProjectedGNCG, 'doEndIteration', expired_after_acceptance)
    result = run(obj, deadline=clock[0]+(1800. if nonlinear else 120.))
    assert result['reason'] == 'wall_cap' and result['status'] != 'converged'
    assert result['iterations'] == 1 and len(result['trace']['models_q']) == 2
    assert not np.array_equal(result['q'], obj.start)
    assert len([r for r in result['line_search_trials'] if r['accepted']]) == 1


def test_actual_failed_metric_disposal_without_diagonal_rescue(monkeypatch):
    obj = Physical()
    actual = owned.OwnedMetric
    instances = []
    class FailedAction(actual):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            instances.append(self)
        def apply(self, v):
            super().apply(v)
            raise ArithmeticError('Actual action failure retained, no fallback')
    monkeypatch.setattr(owned, 'OwnedMetric', FailedAction)
    result = run(obj)
    assert result['reason'] == 'metric_construction_failed' and result['iterations'] == 0
    assert len(result['conditioning_attempts']) == 1 and len(instances) == 1
    assert all(m.live_payload_bytes == 0 for m in instances)
    assert not result['line_search_trials'] and obj.released == 1


def test_actual_quartic_graph_not_automatically_admitted():
    obj = NonlinearPhysical()
    obj.weight = .01
    q = obj.reference+.03*np.sin(np.arange(len(obj.start)))
    # Actual installed CrossGradient PSD search contribution, NOT a made-up
    # visual scalar or an adapter assertion that its factor graph is firstorder.
    combined = (sp.eye(len(q), format='csr')*obj.beta+obj.weight*obj.psd.deriv2(q)).tocsr().sorted_indices()
    dto = replace(obj.metric_operands(q), regularizer=combined)
    with pytest.raises(ValueError):
        owned.validate_operands(dto, obj.identity(), q, 2*1024**3)


class HalfPhysical(Physical):
    """Literal original half-normalized data AND prior; same native optimum."""
    def components(self, q):
        return {k: .5*v for k, v in super().components(q).items()}

    def evaluate(self, q, return_g=False, return_H=False):
        problem = self.problem
        pd, pm = float(problem['misfit'](q)), float(problem['regularization'](q))
        result = [float(.5*pd+.5*self.beta*pm)]
        if return_g:
            result.append(.5*(problem['misfit'].deriv(q)+self.beta*problem['regularization'].deriv(q)))
        if return_H:
            result.append(sp.linalg.LinearOperator((5, 5), dtype=np.float64,
                matvec=lambda v: .5*(problem['misfit'].deriv2(q, v)+self.beta*problem['regularization'].deriv2(q, v))))
        return tuple(result) if return_g or return_H else result[0]

    def binding_diagonal(self, q):
        return .5*self.diagonal

    def metric_operands(self, q):
        original = super().metric_operands(q)
        return replace(original, regularizer=(original.regularizer*.5).tocsr(), likelihood_scale=.5)

    def quadratic_operands(self, q):
        original = super().quadratic_operands(q)
        return replace(original, likelihood_scale=.5,
                       terms=tuple(replace(t, alpha=.5*t.alpha) for t in original.terms))

    def certify(self, q, qt, gradient, phi, phit, iteration, trial, deadline):
        proof = owned.certify_quadratic_chord(self.quadratic_operands(q), self.identity(), q, qt, gradient,
            phi, phit, iteration, trial, deadline, source_components=4, covariance=True, resource_limit_bytes=2*1024**3)
        self.certificates.append(proof)
        return proof


@pytest.mark.parametrize('bounded', [False, True])
def test_public_half_certificate_fit(bounded):
    obj = HalfPhysical(bounded=bounded)
    args = arguments(obj, bounds=True)
    args['binding'] = replace(args['binding'], certificate_source_sha256=owned.SOURCE_SHA256)
    result = core.solve_bounded_linear(obj, obj.lower, obj.upper, obj.start, **args)
    assert result['status'] == 'converged', result['reason']
    assert result['terminal_audits'][-1]['check']['passed']
    assert sum(p['decision'] == 'certified_accept' for p in obj.certificates) == result['iterations']
    assert all(p['decision'] != 'certified_accept' or (Decimal(p['slope_interval'][1]) < 0
        and Decimal(p['armijo_margin_interval'][1]) < 0) for p in obj.certificates)
    g, w = obj.problem['simulation'].G, obj.problem['misfit'].W.toarray()
    matrix = np.vstack((w@g, np.sqrt(obj.beta)*obj.r))
    rhs = np.r_[w@obj.problem['misfit'].data.dobs, np.sqrt(obj.beta)*obj.r@obj.problem['reference_q']]
    oracle = lsq_linear(matrix, rhs, bounds=(obj.lower, obj.upper), method='bvls', tol=1e-13)
    assert oracle.success
    np.testing.assert_allclose(result['q'], oracle.x, rtol=1e-7, atol=1e-8)
    np.testing.assert_allclose(g@result['q'], g@oracle.x, rtol=1e-7, atol=1e-9)


@pytest.mark.parametrize('fault', ['zero', 'non_descent', 'clock', 'memory'])
def test_public_certificate_negatives(fault):
    obj = HalfPhysical()
    q = obj.start.copy()
    phi, gradient = obj.evaluate(q, True)
    qt = q-1e-4*gradient
    deadline = monotonic()+120.
    limit = 2*1024**3
    if fault == 'zero':
        qt = q.copy()
    if fault == 'non_descent':
        qt = q+1e-4*gradient
    if fault == 'clock':
        deadline = monotonic()-1.
    if fault == 'memory':
        limit = 1
    args = (obj.quadratic_operands(q), obj.identity(), q, qt, gradient, phi, obj.evaluate(qt), 0, 0, deadline)
    if fault == 'memory':
        with pytest.raises(ValueError):
            owned.certify_quadratic_chord(*args, source_components=4, covariance=True, resource_limit_bytes=limit)
    else:
        proof = owned.certify_quadratic_chord(*args, source_components=4, covariance=True, resource_limit_bytes=limit)
        assert proof['decision'] != 'certified_accept'
        assert proof['cause'] == {'zero': 'zero_displacement', 'non_descent': 'non_descent', 'clock': 'wall_cap'}[fault]


def test_public_nested_delta_independent_decimal_oracle():
    from decimal import localcontext
    obj = HalfPhysical()
    q = obj.start.copy()
    phi, gradient = obj.evaluate(q, True)
    qt = q-1e-4*gradient
    operands = obj.quadratic_operands(q)
    proof = obj.certify(q, qt, gradient, phi, obj.evaluate(qt), 0, 0, monotonic()+120.)
    # Independent direct80-digit FULL nested objective, not production's delta
    # identity or interval arithmetic. No production solver uses this oracle.
    def matvec(matrix, vector):
        return [sum(Decimal.from_float(float(coef))*v for coef, v in zip(row, vector)) for row in matrix]
    def objective(value):
        vector = [Decimal.from_float(float(v)) for v in value]
        pred = matvec(operands.g, vector)
        wr = matvec(operands.w.toarray(), [v-Decimal.from_float(float(d)) for v, d in zip(pred, operands.dobs)])
        result = Decimal.from_float(operands.likelihood_scale)*sum(v*v for v in wr)
        delta = [v-Decimal.from_float(float(ref)) for v, ref in zip(vector, operands.reference)]
        for term in operands.terms:
            r = matvec(term.weights.toarray(), matvec(term.derivative.toarray(), delta))
            result += Decimal.from_float(operands.beta)*Decimal.from_float(term.alpha)*sum(v*v for v in r)
        return result
    with localcontext() as context:
        context.prec = 80
        actual = objective(qt)-objective(q)
    lo, hi = map(Decimal, proof['delta_interval'])
    assert lo <= actual <= hi and proof['decision'] == 'certified_accept'


@pytest.mark.parametrize('ambient_digits', [6, 28, 80])
def test_source_error_bounds_enclose_exact_fraction_under_ambient_context(ambient_digits):
    from decimal import localcontext
    from fractions import Fraction
    # Exact scientific positive smallness F(q)=q^2, optimum0 in the original
    # feasible box. The actual distance/gap are rational, not a rounded oracle.
    q = np.array([np.nextafter(1., 2.)])
    identity = dict(mode='fixed_linear_quadratic', runtime_epoch=core.LINEAR_EPOCH,
        objective_sha256='a'*64, source_inventory_sha256='b'*64,
        allocation_plan_sha256='c'*64, q_unit='test-native', physical_unit='test-physical',
        physical_scale=1., parameter_count=1, observation_rows=1,
        observation_components=1, beta_engine=1., stage_index=0)
    operands = owned.QuadraticOperands(owned.binding_for(identity, q), np.zeros((1, 1)),
        sp.eye(1, format='csr'), np.zeros(1), np.zeros(1), 1., 1.,
        (owned.QuadraticTerm(1., sp.eye(1, format='csr'), sp.eye(1, format='csr')),), np.ones((1, 1)))
    with localcontext() as context:
        context.prec = ambient_digits
        bounds = owned.quadratic_bounds(operands, identity, q, np.array([-2.]),
            np.array([2.]), monotonic()+120., 1)
    exact_distance = Fraction(float(q[0]))
    assert Fraction(Decimal(bounds['model_error_upper'])) >= exact_distance
    assert Fraction(Decimal(bounds['objective_gap_upper'])) >= exact_distance**2
    assert Fraction(Decimal(bounds['physical_prediction_error_upper'])) >= exact_distance
