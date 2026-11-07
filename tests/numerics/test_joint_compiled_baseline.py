"""Closed adapter controls, not a native fit, compiler resource or science gate."""
from fractions import Fraction
from dataclasses import FrozenInstanceError

import numpy as np
import pytest
from scipy import sparse

import joint_survey_compiled_baseline as bridge
import joint_survey_optimizer as original


class ControlsBudget:
    """Checkpoint-only unit control; the actual solve entry rejects this type."""
    def __init__(self):
        self.calls = 0

    def checkpoint(self):
        self.calls += 1


def fixture():
    # Literal stored operand protocol control; no synthetic passed solve/export.
    p = original.compiled.JointDevelopmentProblem.__new__(original.compiled.JointDevelopmentProblem)
    p.n = 3
    p.plan = {'mesh': {'active': np.ones(3, dtype=bool), 'hx_m': np.ones(3),
        'hy_m': np.ones(1), 'hz_m': np.ones(1)},
        'prior': {'density': {'scale': 750.}, 'susceptibility': {'scale': .03}},
        'gravity': {'training_rows': [0, 1]}, 'magnetic': {'training_rows': [0, 1]}}
    p.start = np.array([.125, -.25, .0625]*2)
    p.reference = np.array([.03125, -.0625, .015625]*2)
    p.lower, p.upper = -np.ones(6), np.ones(6)
    p.scales = np.array([750.]*3+[.03]*3)
    p.J = {m: np.array([[1., .5, .25], [-.5, .25, 1.], [.25, -.5, .75]]) for m in ('gravity', 'magnetic')}
    p.A = {m: np.array([[.5, .25, -.125], [-.25, .75, .5]]) for m in p.J}
    p.d = {m: np.array([.125, -.25]) for m in p.J}
    p.R = sparse.vstack((sparse.diags([.5, .75, 1.]),
        sparse.csr_matrix([[-.25, .25, 0.], [0., -.5, .5]])), format='csr')
    p.development = {m: {'rows': np.arange(2, dtype=np.int64),
        'observed': np.array([.125, -.25]), 'noise_values': np.ones(2)} for m in p.J}
    p.development_sha256 = 'a'*64
    p.geometry = {'active_cell_centres_m': np.zeros((3, 3)),
        'active_cell_bounds_m': np.zeros((3, 6)), 'active_cell_volumes_m3': np.ones(3)}
    return p


def adapter(modality='gravity', beta=1., stage=0):
    p, budget = fixture(), ControlsBudget()
    return p, bridge.JointCompiledBaseline(p, modality, beta, stage, {'control': 'b'*64}, budget), budget


def literal(p, modality, q):
    """Independent binary rational original half-quadratic, no production terms."""
    qf = list(map(Fraction, q))
    ref = p.reference[:3] if modality == 'gravity' else p.reference[3:]
    A = [[Fraction(float(v)) for v in row] for row in p.A[modality]]
    R = [[Fraction(float(v)) for v in row] for row in p.R.toarray()]
    r = [sum(a*x for a, x in zip(row, qf))-Fraction(float(d)) for row, d in zip(A, p.d[modality])]
    s = [sum(a*(x-Fraction(float(y))) for a, x, y in zip(row, qf, ref)) for row in R]
    phi = (sum(v*v for v in r)+sum(v*v for v in s))/2
    g = [sum(row[i]*v for row, v in zip(A, r))+sum(row[i]*v for row, v in zip(R, s)) for i in range(3)]
    H = [[sum(row[i]*row[j] for row in A)+sum(row[i]*row[j] for row in R) for j in range(3)] for i in range(3)]
    return phi, g, H


@pytest.mark.parametrize('modality', ['gravity', 'magnetic'])
def test_actual_native_evaluate_hessian_gradient_delegation_and_literal_half(modality):
    p, a, budget = adapter(modality)
    assert bridge.JointCompiledBaseline.evaluate is original.JointOptimizerObjective.evaluate
    assert bridge.JointCompiledBaseline.hessian is original.JointOptimizerObjective.hessian
    assert bridge.JointCompiledBaseline.binding_diagonal is original.JointOptimizerObjective.binding_diagonal
    q = p.start[a.slice]
    phi, g, H = literal(p, modality, q)
    actual_phi, actual_g, action = a.evaluate(q, return_g=True, return_H=True)
    # Powers-of-two operands make these exact, no enlarged scientific tolerance.
    assert Fraction(actual_phi) == phi
    assert list(map(Fraction, actual_g)) == g
    assert np.array_equal(np.column_stack([action@e for e in np.eye(3)]), np.array(H, dtype=float))
    assert set(a.components(q)) == {'phi_d', 'phi_m', 'phi_engine'}
    assert a.weights['coupling'] == 0. and budget.calls > 0


@pytest.mark.parametrize('modality', ['gravity', 'magnetic'])
@pytest.mark.parametrize('beta', [.0001, .01, 1., 1000.])
def test_literal_source_objects_native13_identity_and_closed_allocation_rebinding(modality, beta):
    p, a, _ = adapter(modality, beta, 25)
    q = p.start[a.slice]
    o, identity, retained = a.compiled_operands(q), a.identity(), a.retained_compiled_problem()
    assert set(identity) == bridge.public.reduced.core.linear._IDENTITY_KEYS
    assert identity['beta_engine'] == 1. and identity['physical_scale'] == ((750.,) if modality == 'gravity' else (.03,))
    assert o.sensitivity is p.A[modality] and o.observations is p.d[modality] and o.prior is p.R
    assert o.physical_sensitivity is p.J[modality] and o.scientific_beta == beta
    assert np.shares_memory(o.reference, p.reference) and np.shares_memory(o.lower, p.lower)
    assert np.shares_memory(o.upper, p.upper)
    assert np.array_equal(o.active_full_indices, np.arange(3)) and o.mesh_shape == (3, 1, 1)
    assert retained.full_kernels[0] is p.J['gravity'] and retained.full_kernels[1] is p.J['magnetic']
    assert any(v is p.R.data for v in retained.development_arrays)
    assert all(v.dtype in (np.dtype('float64'), np.dtype('int64')) for v in retained.development_arrays)
    assert bridge.public.allocation_plan(o, identity, q, retained) == a.allocation
    assert identity['allocation_plan_sha256'] == a.allocation['allocation_plan_sha256'] != '0'*64
    assert a.allocation['resource_limit_bytes'] == 2*1024**3
    assert (a.allocation['CG'], a.allocation['accepted'], a.allocation['states'], a.allocation['LS'], a.allocation['seconds']) == (200, 200, 201, 20, 120.)
    assert a.allocation['admitted_bytes'] == (a.allocation['original_retained_problem_bytes']+
        a.allocation['original_native']['maximum']+sum(a.allocation['source_phase'].values())+
        sum(a.allocation['retained_audits'].values())+sum(a.allocation['terminal'].values()))


@pytest.mark.parametrize('modality,beta,stage,error,message', [
    (None, 1., 0, TypeError, 'compiled-baseline.modality: builtin string required'),
    ('joint', 1., 0, ValueError, 'compiled-baseline.modality'),
    ('gravity', True, 0, ValueError, 'original frozen scientific beta required'),
    ('magnetic', 0., 0, ValueError, 'original frozen scientific beta required'),
    ('gravity', .5, 0, ValueError, 'original frozen scientific beta required'),
    ('gravity', 1., True, ValueError, 'original stage index required'),
    ('gravity', 1., -1, ValueError, 'original stage index required'),
    ('gravity', 1., 26, ValueError, 'original stage index required')])
def test_original_closed_modality_beta_and_stage_controls(modality, beta, stage, error, message):
    with pytest.raises(error, match=message):
        adapter(modality, beta, stage)


def test_checkpoint_control_cannot_call_actual_measured_solve_or_install_callback():
    p = fixture()
    with pytest.raises(TypeError, match='actual original measured workflow budget'):
        bridge.solve_original_baseline(p, 'gravity', 1., 0, ControlsBudget())


def test_public_source_closure_is_exact_without_running_fit():
    inventory = bridge.source_inventory()
    assert all(inventory[name] == pin for name, pin in bridge.PINS.items())
    assert bridge.PUBLIC_COMMIT == 'f3022ef999b79004faa45e54c33adb3fdc9e0441'
    # The guarded per-file sequence retains the entire original source identity.
    assert all(inventory[name] == pin for name, pin in original.reviewed_source_inventory().items())


def test_fit_clock_is_owned_frozen_and_keeps_original_global_budget(tmp_path, monkeypatch):
    budget = bridge.resources.JointResourceBudget(str(tmp_path))
    global_started, global_deadline = budget.started, budget.deadline
    now = [global_started+7.]
    monkeypatch.setattr(bridge, 'monotonic', lambda: now[0])
    clock = bridge._FitBudget(budget)
    assert clock.started == now[0] and clock.deadline == now[0]+120.
    clock.checkpoint()
    with pytest.raises(FrozenInstanceError):
        clock.deadline = global_deadline
    now[0] = clock.deadline+.001
    with pytest.raises(RuntimeError, match='original baseline fit deadline'):
        clock.checkpoint()
    assert (budget.started, budget.deadline, budget.failure) == (global_started, global_deadline, None)
    # A subsequent fit uses remaining ORIGINAL workflow time, not a narrowed
    # previous fit clock. No elapsed workflow work is forgiven or restarted.
    now[0] = global_deadline-2.
    next_clock = bridge._FitBudget(budget)
    assert next_clock.deadline == global_deadline
    assert (budget.started, budget.deadline) == (global_started, global_deadline)
    with pytest.raises(TypeError, match='owned original fit clock'):
        bridge.source_inventory(ControlsBudget())


@pytest.mark.parametrize('changed', ['nan', 'infinite', 'narrowed', 'extended', 'boolean'])
def test_mutable_invalid_workflow_clock_refuses_before_inventory_or_constructor(tmp_path, monkeypatch, changed):
    budget = bridge.resources.JointResourceBudget(str(tmp_path))
    if changed == 'nan': budget.deadline = float('nan')
    elif changed == 'infinite': budget.deadline = float('inf')
    elif changed == 'narrowed': budget.deadline -= 1.
    elif changed == 'extended': budget.deadline += 1.
    else: budget.started = True
    before = (budget.started, budget.deadline)

    def forbidden(*args, **kwargs):
        raise AssertionError('invalid global clock must refuse before inventory/construction')

    monkeypatch.setattr(bridge, 'source_inventory', forbidden)
    monkeypatch.setattr(bridge, 'JointCompiledBaseline', forbidden)
    with pytest.raises(ValueError, match='original uninterrupted workflow clock required'):
        bridge.solve_original_baseline(fixture(), 'gravity', 1., 0, budget)
    assert budget.started is before[0] and budget.deadline is before[1]
    assert budget.samples == 0


@pytest.mark.parametrize('when', ['before', 'actual_sample'])
def test_global_clock_mutation_cannot_change_owned_fit_proof(tmp_path, monkeypatch, when):
    budget = bridge.resources.JointResourceBudget(str(tmp_path))
    clock = bridge._FitBudget(budget)
    original_clock = (clock.started, clock.deadline, clock.workflow_started, clock.workflow_deadline)
    actual_checkpoint = bridge.resources.JointResourceBudget.checkpoint

    def changed_sample(self):
        actual_checkpoint(self)
        self.deadline += 1.

    if when == 'before': budget.deadline += 1.
    else: monkeypatch.setattr(bridge.resources.JointResourceBudget, 'checkpoint', changed_sample)
    with pytest.raises(RuntimeError, match='original workflow clock changed during fit'):
        clock.checkpoint()
    assert (clock.started, clock.deadline, clock.workflow_started, clock.workflow_deadline) == original_clock
    assert budget.deadline == clock.workflow_deadline+1.  # Refuse, never repair or reset caller state.
    assert budget.samples == (0 if when == 'before' else 1)


def test_changed_source_inventory_crossing120_refuses_before_constructor_or_solve(tmp_path, monkeypatch):
    budget = bridge.resources.JointResourceBudget(str(tmp_path))
    original_budget = (budget.started, budget.deadline)
    now = [budget.started]
    monkeypatch.setattr(bridge, 'monotonic', lambda: now[0])
    calls = []

    def inventory(clock):
        assert type(clock) is bridge._FitBudget
        calls.append('inventory')
        now[0] = clock.deadline+.001
        return {'refusal_control': 'b'*64}

    def forbidden(*args, **kwargs):
        raise AssertionError('expired inventory must not call public solver')

    monkeypatch.setattr(bridge, 'source_inventory', inventory)
    monkeypatch.setattr(bridge.public, 'solve_bounded_linear', forbidden)
    # Actual constructor checkpoint must fail BEFORE operands or allocations.
    with pytest.raises(RuntimeError, match='original baseline fit deadline'):
        bridge.solve_original_baseline(fixture(), 'gravity', 1., 0, budget)
    assert calls == ['inventory'] and (budget.started, budget.deadline) == original_budget


def test_actual_defining_read_crossing120_stops_before_next_source_action(tmp_path, monkeypatch):
    budget = bridge.resources.JointResourceBudget(str(tmp_path))
    original_budget = (budget.started, budget.deadline)
    now = [budget.started]
    monkeypatch.setattr(bridge, 'monotonic', lambda: now[0])
    clock = bridge._FitBudget(budget)
    actual_read = bridge.Path.read_bytes
    reads = []

    def crossing_read(path):
        value = actual_read(path)
        reads.append(path)
        now[0] = clock.deadline+.001
        return value

    monkeypatch.setattr(bridge.Path, 'read_bytes', crossing_read)
    with pytest.raises(RuntimeError, match='original baseline fit deadline'):
        bridge.source_inventory(clock)
    assert reads == [bridge.Path(bridge.__file__)]
    assert (budget.started, budget.deadline, budget.failure) == (*original_budget, None)


def test_changed_constructor_allocation_crossing120_refuses_before_solver(tmp_path, monkeypatch):
    budget = bridge.resources.JointResourceBudget(str(tmp_path))
    original_budget = (budget.started, budget.deadline)
    now = [budget.started]
    monkeypatch.setattr(bridge, 'monotonic', lambda: now[0])
    actual_allocation = bridge.public.allocation_plan
    calls = []

    def inventory(clock):
        calls.append(('inventory', clock.deadline))
        now[0] += 3.
        return {'refusal_control': 'b'*64}

    def crossing_allocation(*args):
        allocation = actual_allocation(*args)
        calls.append(('allocation', now[0]))
        now[0] = original_budget[0]+120.001
        return allocation

    def forbidden(*args, **kwargs):
        raise AssertionError('expired constructor must not call public solver')

    monkeypatch.setattr(bridge, 'source_inventory', inventory)
    monkeypatch.setattr(bridge.public, 'allocation_plan', crossing_allocation)
    monkeypatch.setattr(bridge.public, 'solve_bounded_linear', forbidden)
    with pytest.raises(RuntimeError, match='original baseline fit deadline'):
        bridge.solve_original_baseline(fixture(), 'gravity', 1., 0, budget)
    assert [event[0] for event in calls] == ['inventory', 'allocation']
    assert (budget.started, budget.deadline, budget.failure) == (*original_budget, None)


def test_public_solver_receives_preinventory_deadline_without_construction_time_reset(tmp_path, monkeypatch):
    budget = bridge.resources.JointResourceBudget(str(tmp_path))
    original_budget = (budget.started, budget.deadline)
    now = [budget.started]
    monkeypatch.setattr(bridge, 'monotonic', lambda: now[0])
    actual_allocation = bridge.public.allocation_plan
    observed = []

    def inventory(clock):
        observed.append(clock)
        now[0] += 5.
        return {'refusal_control': 'b'*64}

    def counted_allocation(*args):
        value = actual_allocation(*args)
        now[0] += 3.
        return value

    def refusal_only(adapter, *args, **kwargs):
        assert now[0] == original_budget[0]+11.
        assert kwargs['budget'].deadline == observed[0].deadline == original_budget[0]+120.
        assert adapter.budget is observed[0] and adapter.budget.workflow is budget
        # Deadline also guards inherited actual native H actions, not just DTOs.
        action = adapter.hessian(adapter.start)
        now[0] = observed[0].deadline+.001
        with pytest.raises(RuntimeError, match='original baseline fit deadline'):
            action @ np.ones(adapter.n)
        raise RuntimeError('protocol-control-no-scientific-solve')

    monkeypatch.setattr(bridge, 'source_inventory', inventory)
    monkeypatch.setattr(bridge.public, 'allocation_plan', counted_allocation)
    monkeypatch.setattr(bridge.public, 'solve_bounded_linear', refusal_only)
    with pytest.raises(RuntimeError, match='protocol-control-no-scientific-solve'):
        bridge.solve_original_baseline(fixture(), 'gravity', 1., 0, budget)
    assert (budget.started, budget.deadline, budget.failure) == (*original_budget, None)
