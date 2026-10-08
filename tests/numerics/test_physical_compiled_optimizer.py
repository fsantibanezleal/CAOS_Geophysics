"""Independent literal Fraction normalization; no fit or nonlinear admission."""
from dataclasses import replace
from decimal import Decimal, localcontext
from fractions import Fraction
from time import monotonic

import numpy as np
import pytest
import scipy.sparse as sp

import physical_compiled_optimizer as public
from test_physical_original_terminal import exact, hessian, fraction_solve


def fixture(beta=.0001, scale=750.):
    a = 3
    identity = dict(mode='fixed_linear_quadratic', runtime_epoch=public.LINEAR_EPOCH,
        objective_sha256='a'*64, source_inventory_sha256='b'*64, allocation_plan_sha256='c'*64,
        parameter_count=a, observation_rows=2, observation_components=1, beta_engine=1.,
        physical_scale=(scale,), q_unit='normalized_property_block', physical_unit='kg_m3', stage_index=25)
    q = np.array([.1, -.2, .05])
    A = np.array([[.5, .25, -.125], [-.25, .75, .5]])
    J = np.array([[1., .5, .25], [-.5, .25, 1.], [.25, -.5, .75]])
    R = sp.vstack((sp.diags([.5, .75, 1.]),
        sp.csr_matrix([[-.25, .25, 0.], [0., -.5, .5]])), format='csr')
    o = public.CompiledQuadraticOperands(public.source.owned.binding_for(identity, q), A,
        np.array([.125, -.25]), R, np.array([.025, -.05, .01]), -np.ones(a), np.ones(a),
        beta, J, np.arange(a, dtype=np.int64), (3, 1, 1))
    retained = public.RetainedCompiledProblem((J, J.copy()), (A, o.observations, q))
    plan = public.allocation_plan(o, identity, q, retained)
    identity['allocation_plan_sha256'] = plan['allocation_plan_sha256']
    o = replace(o, binding=public.source.owned.binding_for(identity, q))
    return o, identity, q, retained, plan


def literal(o, q):
    """Interpret STORED A/d/R as binary rationals, without production terms."""
    qf = list(map(Fraction, q)); ref = list(map(Fraction, o.reference))
    A = [[Fraction(float(v)) for v in row] for row in o.sensitivity]
    R = [[Fraction(float(v)) for v in row] for row in o.prior.toarray()]
    r = [sum(v*x for v, x in zip(row, qf))-Fraction(float(d))
        for row, d in zip(A, o.observations)]
    s = [sum(v*(x-y) for v, x, y in zip(row, qf, ref)) for row in R]
    b = Fraction(o.scientific_beta)
    phi = (sum(v*v for v in r)+b*sum(v*v for v in s))/2
    g = [sum(row[i]*v for row, v in zip(A, r))+b*sum(row[i]*v for row, v in zip(R, s))
        for i in range(len(q))]
    H = [[sum(row[i]*row[j] for row in A)+b*sum(row[i]*row[j] for row in R)
        for j in range(len(q))] for i in range(len(q))]
    return phi, g, H


@pytest.mark.parametrize('beta', [.0001, .01, 1., 1000.])
@pytest.mark.parametrize('scale', [750., .03])
def test_literal_half_beta_tuple_and_exact_original_factors(beta, scale):
    o, identity, q, _, plan = fixture(beta, scale)
    original, mapping = public._normalization(o, identity, q)
    public.source.validate(original, mapping['proof_identity'], q, deadline=monotonic()+120.,
        resource_limit_bytes=2*1024**3, admitted_bytes=plan['admitted_bytes'])
    phi, gradient, H = literal(o, q)
    assert exact(original, q) == (phi, gradient)
    assert hessian(original) == H
    assert identity['beta_engine'] == 1. and identity['physical_scale'] == (scale,)
    assert mapping['native_identity'] == identity and mapping['proof_identity'] != identity
    assert mapping['proof_identity']['beta_engine'] == beta and original.likelihood_scale == .5
    assert original.prediction_sensitivity is o.physical_sensitivity
    assert np.array_equal(np.vstack([(t.weights@t.derivative).toarray() for t in original.terms]), o.prior.toarray())


@pytest.mark.parametrize('ambient', [6, 28, 80])
def test_residual_same_run_bounds_exact_fraction_and_physical_units(ambient):
    o, identity, q, retained, plan = fixture()
    _, zero, H = literal(o, np.zeros(3))
    optimum = fraction_solve(H, [-v for v in zero])
    q = np.array(list(map(float, optimum)))
    assert np.all(np.abs(q) < 1.)
    q += np.array([1e-12, -2e-12, 1e-12])
    o = replace(o, binding=public.source.owned.binding_for(identity, q))
    _, g, _ = literal(o, q)
    owner = public._CompiledResidualTerminal(o, identity, q, np.array(list(map(float, g))), 1., plan,
        deadline=monotonic()+120., retained_audit_bytes=0)
    with localcontext() as ctx:
        ctx.prec = ambient
        record = owner.certify(public.source.owned.TerminalPolicy(1e-5, 1e-5, 1e-10, 1e-8))
    assert record['passed'] and record['disposed'] and owner.live_payload_bytes == 0
    delta = [Fraction(float(v))-target for v, target in zip(q, optimum)]
    model = Fraction(Decimal(record['bounds']['model_error_upper']))
    assert model**2 >= sum(v*v for v in delta)
    gap = sum(v*sum(h*x for h, x in zip(row, delta)) for v, row in zip(delta, H))/2
    assert Fraction(Decimal(record['bounds']['objective_gap_upper'])) >= gap
    physical = max(abs(sum(Fraction(float(v))*x for v, x in zip(row, delta))*Fraction(identity['physical_scale'][0]))
        for row in o.physical_sensitivity)
    assert Fraction(Decimal(record['bounds']['physical_prediction_error_upper'])) >= physical
    assert record['original_physical_prediction_limit'] == 1e-8
    assert record['compiled_mapping']['native_identity'] == identity
    assert record['allocation']['terminal_phase']['retained_audit_bytes'] >= plan['original_retained_problem_bytes']
    assert not record['native_fit_accepted'] and record['actions'] == 1


def test_original_retained_and_every_mapping_charge_sum_not_max():
    o, identity, q, retained, plan = fixture()
    old = 4*sum(v.nbytes for v in retained.full_kernels)+4*sum(v.nbytes for v in retained.development_arrays)
    old += 36*251*len(q)*8+512*(2*len(q))*8+64*1024**2
    assert plan['original_retained_problem_bytes'] == old
    assert plan['admitted_bytes'] == old+plan['original_native']['maximum']+sum(plan['source_phase'].values())+sum(
        plan['retained_audits'].values())+sum(plan['terminal'].values())
    assert plan['retained_audits']['compiled_chord_mapping_bytes'] == 4000*2048
    assert (plan['CG'], plan['accepted'], plan['states'], plan['LS'], plan['seconds']) == (200, 200, 201, 20, 120.)
    assert plan['terminal']['witness_bytes'] == 128*len(q)


@pytest.mark.parametrize('kind', ['beta', 'scale', 'binding', 'wrap', 'full_mesh', 'smallness', 'foreign_backing', 'full_problem'])
def test_closed_source_metadata_and_no_arbitrary_graph_or_storage(kind):
    o, identity, q, retained, _ = fixture()
    if kind == 'beta':
        identity['beta_engine'] = o.scientific_beta
    elif kind == 'scale':
        identity['physical_scale'] = 750.
    elif kind == 'binding':
        o = replace(o, binding=replace(o.binding, model_sha256='f'*64))
    elif kind == 'wrap':
        o = replace(o, mesh_shape=(1, 1, 3), active_full_indices=np.array([0, 1, 3], dtype=np.int64))
    elif kind == 'full_mesh':
        o = replace(o, mesh_shape=(4096, 2, 1))
    elif kind == 'smallness':
        R = o.prior.copy(); R.data[0] = 0.; o = replace(o, prior=R)
    elif kind == 'foreign_backing':
        parent = np.zeros((200, 3)); parent[:2] = o.sensitivity
        o = replace(o, sensitivity=parent[:2])
    else:
        retained = replace(retained, full_kernels=(o.physical_sensitivity.copy(),)*2)
    with pytest.raises(ValueError):
        if kind == 'full_problem':
            public.allocation_plan(o, identity, q, retained)
        else:
            public._normalization(o, identity, q)


def test_exact_binary_scale_outward_comparison_not_unscaled_acceptance():
    o, identity, q, _, plan = fixture()
    _, zero, H = literal(o, np.zeros(3))
    optimum = fraction_solve(H, [-v for v in zero])
    q = np.array(list(map(float, optimum)))+np.array([1e-8, -1e-8, 1e-8])
    o = replace(o, binding=public.source.owned.binding_for(identity, q))
    _, g, _ = literal(o, q)
    owner = public._CompiledResidualTerminal(o, identity, q, np.array(list(map(float, g))), 1., plan,
        deadline=monotonic()+120., retained_audit_bytes=0)
    record = owner.certify(public.source.owned.TerminalPolicy(1e-5, 1e-5, 1e-10, 1e-8))
    assert not record['passed'] and record['disposed']
    assert Decimal(record['unscaled_prediction_error_upper']) < Decimal(record['bounds']['physical_prediction_error_upper'])
    assert Decimal(record['bounds']['physical_prediction_error_upper']) > Decimal.from_float(1e-8)


def test_expired_public_clock_and_source_drift_before_native_calls(monkeypatch):
    o, identity, q, _, plan = fixture()
    budget = public.ConditionedBudget(monotonic()-1., 200, 2*1024**3,
        plan['admitted_bytes'], plan['allocation_plan_sha256'])
    with pytest.raises(public.source.intervals._Expired):
        public.solve_bounded_linear(object(), o.lower, o.upper, q, budget=budget, binding=None, terminal=None)
    monkeypatch.setattr(public, 'RESIDUAL_SHA256', 'f'*64)
    with pytest.raises(ValueError, match='literal residual source drift'):
        public._check_source()


class NativeProbe:
    """TEST delegation probe, never passed to a native minimize/fit."""
    def __init__(self, o, identity, retained):
        self.o, self.i, self.retained = o, identity, retained
        self.calls = []
    def identity(self):
        return self.i.copy()
    def compiled_operands(self, q):
        return replace(self.o, binding=public.source.owned.binding_for(self.i, q))
    def retained_compiled_problem(self):
        return self.retained
    def evaluate(self, *args):
        self.calls.append(('native_evaluate', args))
        return object()
    def components(self, *args):
        self.calls.append(('native_components', args))
        return object()
    def binding_diagonal(self, *args):
        self.calls.append(('native_diagonal', args))
        return object()
    def release_state(self):
        self.calls.append(('native_release', ()))


def test_proxy_native_delegation_and_closed_owned_metric_not_caller_factor():
    o, identity, q, retained, plan = fixture()
    native = NativeProbe(o, identity, retained)
    b = public.ConditionedBudget(monotonic()+120., 200, 2*1024**3, plan['admitted_bytes'], plan['allocation_plan_sha256'])
    proxy = public._CompiledObjective(native, b, q)
    assert proxy.components.__self__ is native
    assert proxy.binding_diagonal.__self__ is native and proxy.release_state.__self__ is native
    metric = proxy.metric_operands(q)
    assert metric.binding == o.binding and metric.likelihood_scale == .5 and metric.covariance is False
    assert np.array_equal(metric.regularizer.toarray(), (o.scientific_beta*(o.prior.T@o.prior)).toarray())
    assert not native.calls  # No copied physical evaluation/Hessian or fit.
    value = proxy.evaluate(q, True, True)
    assert type(value) is object and native.calls[0][0] == 'native_evaluate'
    assert native.calls[0][1][0] is q and native.calls[0][1][1:] == (True, True)


@pytest.mark.parametrize('field', ['sensitivity', 'observations', 'prior', 'scientific_beta', 'reference', 'physical_sensitivity'])
def test_frozen_operand_drift_cannot_reuse_proxy_or_certificate(field):
    o, identity, q, retained, plan = fixture()
    native = NativeProbe(o, identity, retained)
    b = public.ConditionedBudget(monotonic()+120., 200, 2*1024**3, plan['admitted_bytes'], plan['allocation_plan_sha256'])
    proxy = public._CompiledObjective(native, b, q)
    value = getattr(o, field)
    if field == 'scientific_beta':
        value = .001
    else:
        value = value.copy()
        if sp.issparse(value):
            value.data *= 2.
        else:
            value.flat[0] += .125
    native.o = replace(o, **{field: value})
    with pytest.raises(ValueError, match='frozen physical source operand drift'):
        proxy.original(q)
    assert not native.calls


@pytest.mark.parametrize('kind', ['identity', 'quota', 'digest', 'expiry'])
def test_exact_native_authority_resource_and_uninterrupted_deadline(kind):
    o, identity, q, retained, plan = fixture()
    native = NativeProbe(o, identity, retained)
    b = public.ConditionedBudget(monotonic()+120., 200, 2*1024**3, plan['admitted_bytes'], plan['allocation_plan_sha256'])
    if kind == 'quota':
        b = replace(b, admitted_bytes=b.admitted_bytes+1)
    if kind == 'digest':
        b = replace(b, allocation_plan_sha256='f'*64)
    if kind in ('quota', 'digest'):
        with pytest.raises(ValueError, match='owner-derived whole-Problem allocation'):
            public._CompiledObjective(native, b, q)
    else:
        proxy = public._CompiledObjective(native, b, q)
        if kind == 'expiry':
            proxy.budget = replace(b, deadline=monotonic()-1.)
            exception, message = public.source.intervals._Expired, None
        else:
            native.i = dict(identity, objective_sha256='d'*64)
            exception, message = ValueError, 'canonical native identity drift'
        with pytest.raises(exception, match=message):
            proxy.original(q)
    assert not native.calls


def test_expiration_during_terminal_conversion_disposes_without_acceptance(monkeypatch):
    o, identity, q, _, plan = fixture()
    _, zero, H = literal(o, np.zeros(3))
    optimum = fraction_solve(H, [-v for v in zero])
    q = np.array(list(map(float, optimum)))
    o = replace(o, binding=public.source.owned.binding_for(identity, q))
    _, g, _ = literal(o, q)
    owner = public._CompiledResidualTerminal(o, identity, q, np.array(list(map(float, g))), 1., plan,
        deadline=monotonic()+120., retained_audit_bytes=0)
    original = public.original_terminal.original_row_arithmetic
    def expired(digits, deadline):
        return original(digits, monotonic()-1.)
    monkeypatch.setattr(public.original_terminal, 'original_row_arithmetic', expired)
    with pytest.raises(public.source.intervals._Expired):
        owner.certify(public.source.owned.TerminalPolicy(1e-5, 1e-5, 1e-10, 1e-8))
    assert owner.live_payload_bytes == 0


@pytest.mark.parametrize('side', [-1., 1.])
@pytest.mark.parametrize('correct_sign', [False, True])
def test_compiled_coupled_free_face_cannot_hide_active_kkt(side, correct_sign):
    o, identity, _, _, _ = fixture(beta=.01)
    identity = dict(identity, observation_rows=3)
    A = np.array([[1., .5, .25], [.25, 1., -.5], [.5, .25, 1.]])
    o = replace(o, sensitivity=A, observations=np.zeros(3))
    target = np.array([side, .125, -.25])
    _, base, H = literal(o, target)
    wanted = [Fraction(-side if correct_sign else side)/4, Fraction(0), Fraction(0)]
    adjoint = [[Fraction(float(A[j, i])) for j in range(3)] for i in range(3)]
    d = fraction_solve(adjoint, [v-w for v, w in zip(base, wanted)])
    o = replace(o, observations=np.array(list(map(float, d))))
    _, g, _ = literal(o, target)
    change = fraction_solve([row[1:] for row in H[1:]], [-v for v in g[1:]])
    q = np.array([side]+[float(Fraction(float(v))+c) for v, c in zip(target[1:], change)])
    q[1:] += [1e-12, -1e-12]
    retained = public.RetainedCompiledProblem((o.physical_sensitivity, o.physical_sensitivity.copy()), (A, o.observations, q))
    plan = public.allocation_plan(o, identity, q, retained)
    identity['allocation_plan_sha256'] = plan['allocation_plan_sha256']
    o = replace(o, binding=public.source.owned.binding_for(identity, q))
    _, g, _ = literal(o, q)
    owner = public._CompiledResidualTerminal(o, identity, q, np.array(list(map(float, g))), 1., plan,
        deadline=monotonic()+120., retained_audit_bytes=0)
    record = owner.certify(public.source.owned.TerminalPolicy(1e-5, 1e-5, 1e-10, 1e-8))
    assert record['passed'] == correct_sign and record['active_sign_pass'] == correct_sign
    assert record['inside_original_bounds'] and record['disposed']
    assert record['free_indices'] == [1, 2] and record['witness_q'][0] == 0.
