"""Original domain denials and actual native SD/stored-L scientific controls.

The external magnetic source fixture is explicit, read-only qualification
input. The BVLS comparison is test-only and never a production fallback.
"""
from dataclasses import replace
from decimal import Decimal, localcontext
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from time import monotonic

import numpy as np
import pytest
from scipy.linalg import solve_triangular
from scipy.optimize import lsq_linear

import physical_original_optimizer as optimizer
import physical_original_quadratic as source
import physical_owned_spd as owned
import magnetic_original_optimizer as bridge
from test_physical_original_quadratic import operands


@pytest.mark.parametrize('ambient', [6, 28, 80])
def test_original_direction_both_endpoints_and_strict_domain(ambient):
    o, identity, q = operands(projected=True)
    direction = o.projection.copy()
    domain = optimizer.OriginalMagneticDomain(o.binding, np.array([0., 0., 10.]), 10., direction, 'linear_tmi_nT')
    with localcontext() as context:
        context.prec = ambient
        passed, ratio = optimizer.magnetic_domain_check(domain, o, q, q, deadline=monotonic()+120.)
        assert passed and Decimal(ratio) > Decimal.from_float(1e-8)
        # Original affine field hits exactly zero at the actual trial endpoint.
        g = np.zeros_like(o.sensitivity)
        g[2::3, 0] = -10.
        cancelled = replace(o, sensitivity=g)
        assert not optimizer.magnetic_domain_check(domain, cancelled, q,
            np.array([1., 0., 0.]), deadline=monotonic()+120.)[0]
    with pytest.raises(ValueError, match='quantity'):
        optimizer.magnetic_domain_check(replace(domain, quantity='exact_total_anomaly_nT'), o, q, q, deadline=monotonic()+120.)
    with pytest.raises(ValueError, match='quantity'):
        optimizer.magnetic_domain_check(replace(domain, quantity='secondary_enu_nT'), o, q, q, deadline=monotonic()+120.)
    with pytest.raises(ValueError, match='original'):
        optimizer.magnetic_domain_check(replace(domain, binding=replace(o.binding, model_sha256='f'*64)), o, q, q, deadline=monotonic()+120.)


def native_control():
    path = Path(os.environ['GEOPHYSICS_M02_MAGNETIC_SOURCE']).resolve()
    spec = importlib.util.spec_from_file_location('original_magnetic_controls',
        path/'tests/numerics/test_magnetic_optimizer_adapter.py')
    control = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(control)
    return control


def binding_for(objective):
    return optimizer.ConditionedBinding('physical_original_optimizer.solve_bounded_linear',
        optimizer.SOURCE_SHA256, owned.SOURCE_SHA256, owned.KERNEL_SHA256,
        optimizer.VENDOR_SOURCE_SHA256, source.SOURCE_SHA256, objective.inventory,
        optimizer.LINEAR_EPOCH, optimizer.POLICY)


def assert_caps(result, elapsed):
    assert elapsed <= 120.
    assert result['iterations'] <= 200 and len(result['trace']['models_q']) <= 201
    phases = {}
    for row in result['conditioning_attempts']:
        assert row['failure'] is None
        assert row['true_relative_residual'] <= 1e-6
        phases[row['iteration']] = phases.get(row['iteration'], 0)+row['iterations']
    assert max(phases.values(), default=0) <= 200
    assert all(c['trial'] < 20 for c in result['line_search_trials'])
    assert all(c['passed'] for c in result['magnetic_domain_checks'])
    assert result['terminal_audits'][-1]['check']['passed']
    assert result['terminal_audits'][-1]['check']['disposed']
    assert result['terminal_audits'][-1]['check']['allocation']['maximum'] <= 805306368


@pytest.mark.parametrize('quantity', ['secondary_enu_nT', 'linear_tmi_nT'])
@pytest.mark.parametrize('covariance', [False, True])
def test_actual_original_noise_native_accuracy(quantity, covariance):
    control = native_control()
    physical = control.physical.__wrapped__()
    obj, kernel, d, noise, r, _ = control.make(physical, quantity, covariance)
    started = monotonic()
    budget = optimizer.ConditionedBudget(started+120., 200, 805306368, 805306368, obj.allocation)
    result = bridge.solve_magnetic_original(obj, np.zeros(7), source_components=90,
        budget=budget, binding=binding_for(obj), terminal=owned.TerminalPolicy(1e-7, 1e-6, 1e-8, 1e-6))
    elapsed = monotonic()-started
    assert result['status'] == 'converged', result
    assert_caps(result, elapsed)
    if covariance:
        lower = np.linalg.cholesky(noise['values'])
        wk, wd = solve_triangular(lower, kernel, lower=True), solve_triangular(lower, d.ravel(), lower=True)
    else:
        wk, wd = kernel/.5, d.ravel()/.5
    stacked = np.vstack([wk, np.sqrt(.3)*r])
    rhs = np.r_[wd, np.sqrt(.3)*r@control.control.QREF]
    oracle = lsq_linear(stacked, rhs, bounds=(0., 10.), method='bvls', tol=1e-12, max_iter=10000)
    np.testing.assert_allclose(result['q'], oracle.x, rtol=0., atol=1e-6)
    optimum = np.linalg.norm(stacked@oracle.x-rhs)**2
    assert abs(result['phi_engine']-optimum)/max(1., optimum) <= 1e-8
    assert np.sqrt(np.mean((kernel@(result['q']-oracle.x))**2)) <= 1e-6
    obj.release_state()


def serial(value):
    if type(value) is np.ndarray:
        return value.tolist()
    if type(value) is dict:
        return {k: serial(v) for k, v in value.items()}
    if type(value) in (tuple, list):
        return [serial(v) for v in value]
    return value


@pytest.mark.parametrize('public_proof', [bridge.certify_magnetic_original_state,
    bridge.certify_magnetic_original_residual_state])
def test_closed_actual_state_proof_and_denials(monkeypatch, public_proof):
    control = native_control()
    obj, *_ = control.make(control.physical.__wrapped__(), 'secondary_enu_nT', False)
    kwargs = dict(source_components=90,
        budget=optimizer.ConditionedBudget(monotonic()+120., 0, 805306368, 805306368, obj.allocation),
        binding=binding_for(obj), terminal=owned.TerminalPolicy(1e-7, 1e-6, 1e-8, 1e-6))
    # An actual nonstationary state is proved/rejected, never moved to an oracle
    # optimum or described as a native fit. No CG/minimize may run here.
    def forbidden(*args, **kw):
        pytest.fail('state proof cannot invoke native minimize')
    monkeypatch.setattr(optimizer.reduced.core.linear.optimization.ProjectedGNCG, 'minimize', forbidden)
    q = np.zeros(7, dtype=np.float64)
    result = public_proof(obj, q, **kwargs)
    assert not result['check']['passed'] and result['check']['disposed']
    assert obj._cache is None and np.array_equal(q, np.zeros(7))
    assert result['normalization'] == 'absolute_unit_state_only'
    assert not any(result[k] for k in ('native_fit_accepted', 'full_method_accepted', 'host_accepted'))
    for changed in (dict(binding=replace(kwargs['binding'], runtime_epoch='foreign')),
        dict(binding=replace(kwargs['binding'], certificate_source_sha256='f'*64)),
        dict(budget=replace(kwargs['budget'], admitted_bytes=True)),
        dict(budget=replace(kwargs['budget'], allocation_plan_sha256='f'*64))):
        with pytest.raises(ValueError):
            public_proof(obj, q, **dict(kwargs, **changed))
    with pytest.raises(optimizer.source.intervals._Expired):
        public_proof(obj, q,
            **dict(kwargs, budget=replace(kwargs['budget'], deadline=monotonic()-1.)))
    with pytest.raises(TypeError):
        public_proof(object(), q, **kwargs)


def test_residual_state_literal_source_drift_is_refused(monkeypatch):
    import physical_original_residual_terminal as residual
    control = native_control()
    obj, *_ = control.make(control.physical.__wrapped__(), 'secondary_enu_nT', False)
    monkeypatch.setattr(residual, 'SOURCE_SHA256', 'f'*64)
    with pytest.raises(ValueError, match='closed residual source drift'):
        bridge.certify_magnetic_original_residual_state(obj, np.zeros(7), source_components=90,
            budget=optimizer.ConditionedBudget(monotonic()+120., 0, 805306368, 805306368, obj.allocation),
            binding=binding_for(obj), terminal=owned.TerminalPolicy(1e-7, 1e-6, 1e-8, 1e-6))
    assert obj._cache is None


def test_production_residual_epoch_owns_proof_without_neumann_fallback(monkeypatch):
    control = native_control()
    obj, *_ = control.make(control.physical.__wrapped__(), 'secondary_enu_nT', False)
    def forbidden(*args, **kwargs):
        pytest.fail('residual production epoch cannot fall back to Neumann')
    monkeypatch.setattr(optimizer.accuracy, 'OwnedOriginalTerminal', forbidden)
    started = monotonic()
    result = bridge.solve_magnetic_original(obj, np.zeros(7), source_components=90,
        budget=optimizer.ConditionedBudget(started+120., 200, 805306368, 805306368, obj.allocation),
        binding=binding_for(obj), terminal=owned.TerminalPolicy(1e-7, 1e-6, 1e-8, 1e-6))
    assert result['status'] == 'converged'
    assert_caps(result, monotonic()-started)
    assert result['runtime_epoch'] == 'physical-gncg-original-noise-reduced-joseph-candidate-9'
    assert result['policy'] == 'closed-original-noise-reduced-joseph-free-face-residual-accuracy-2'
    assert result['source_binding']['original_residual_terminal'] == optimizer.RESIDUAL_TERMINAL_SHA256
    for row in result['terminal_audits']:
        if row['check'] is not None:
            check = row['check']
            assert check['proof_basis'] == 'original_physical_residual_strong_convexity'
            assert check['actions'] == (1 if check['free_indices'] else 0)
            assert check['disposed']


def test_production_residual_source_drift_before_native_evaluation(monkeypatch):
    control = native_control()
    obj, *_ = control.make(control.physical.__wrapped__(), 'secondary_enu_nT', False)
    def forbidden(*args, **kwargs):
        pytest.fail('drifted residual source cannot reach physical evaluation')
    monkeypatch.setattr(obj, 'evaluate', forbidden)
    monkeypatch.setattr(optimizer.residual_accuracy, 'SOURCE_SHA256', 'f'*64)
    with pytest.raises(ValueError, match='closed residual certificate source drift'):
        bridge.solve_magnetic_original(obj, np.zeros(7), source_components=90,
            budget=optimizer.ConditionedBudget(monotonic()+120., 200, 805306368, 805306368, obj.allocation),
            binding=binding_for(obj), terminal=owned.TerminalPolicy(1e-7, 1e-6, 1e-8, 1e-6))
    assert obj._cache is None


def test_actual_original_full528_firstfold_strong_accuracy():
    """Exactly one new source epoch/prerequisite; dependent matrix is external."""
    from magnetic_likelihood import SealedLikelihood
    from magnetic_calibration import mesh_from_metadata
    from magnetic_inverse import build_operator
    from magnetic_optimizer_adapter import MagneticObjective, MagneticRegularizer
    from magnetic_survey_json import digest
    from run_magnetic_survey import source_inventory
    path = Path(os.environ['GEOPHYSICS_M02_FROZEN_REQUEST']).resolve()
    output = Path(os.environ['GEOPHYSICS_M02_FIRSTFOLD_RECEIPT']).resolve()
    if output.exists() or any((p/'.git').exists() for p in output.parents):
        raise ValueError('new external immutable firstfold receipt required')
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == '4563ce1d24703dd6d19f63445e085fd8c348a36461c7cb86fbde015197f3dd2c'
    reader = SealedLikelihood(raw)
    rows = tuple(reader.plan['partition']['folds'][0]['fit_rows']['data'])
    observed, noise = reader.read(rows, role='fit', fold=0)
    assert observed.shape == (144, 3) and noise['kind'] == 'diagonal_sd'
    prior = reader.metadata['prior']
    lower, upper, start, reference = [np.array(prior[k]['data'], dtype=np.float64)/.01
        for k in ('lower_si', 'upper_si', 'start_si', 'reference_si')]
    assert len(start) == 528
    sources = source_inventory()
    historical = json.loads(path.with_name('binding.json').read_bytes())['sources']
    for name in ('magnetic_inverse_precision', 'magnetic_forward', 'magnetic_inverse', 'magnetic_optimizer_adapter'):
        assert sources[name] == historical[name]
    sources.update(physical_original_optimizer=optimizer.SOURCE_SHA256,
        physical_original_quadratic=source.SOURCE_SHA256,
        physical_original_terminal=optimizer.accuracy.SOURCE_SHA256,
        magnetic_original_optimizer=bridge.SOURCE_SHA256, physical_owned_spd=owned.SOURCE_SHA256)
    started = monotonic()
    deadline = started+120.
    op = build_operator(raw, rows, deadline=deadline)
    reg = MagneticRegularizer(mesh_from_metadata(reader.metadata), reference,
        np.array(prior['lengths_m']['data'], dtype=np.float64), 'l2', 0., start)
    allocation = digest(dict(original=reader.plan['preflight'], source_components=864,
        fit_components=432, parameters=528, original_limit=805306368,
        source_epoch=optimizer.LINEAR_EPOCH))
    obj = MagneticObjective(op, reg, observed, noise, lower, upper, .0001, digest(sources), allocation, 0)
    receipt = dict(schema='original-noise-full528-firstfold-accuracy-1', accepted=False,
        request_sha256=hashlib.sha256(raw).hexdigest(), original_fit_rows=rows,
        source_inventory=sources, beta=.0001, source_components=864, fit_components=432,
        original_active=528, limits=dict(CG=200, rtol=1e-6, atol=0., accepted=200, LS=20, seconds=120.),
        result=None, elapsed_seconds=None, errors=None)
    try:
        budget = optimizer.ConditionedBudget(deadline, 200, 805306368, 805306368, allocation)
        result = bridge.solve_magnetic_original(obj, start, source_components=864, budget=budget,
            binding=binding_for(obj), terminal=owned.TerminalPolicy(1e-7, 1e-6, 1e-8, 1e-6))
        receipt.update(result=result, elapsed_seconds=monotonic()-started)
        assert result['status'] == 'converged', result['reason']
        assert_caps(result, receipt['elapsed_seconds'])
        # Original independent oracle. No production import or optimizer path.
        g = op.operand_snapshot()[0]
        sigma = noise['values'].ravel()
        factor = np.vstack([np.sqrt(t['alpha'])*(t['weights'][:, None]*t['derivative'].toarray())
            for t in reg.terms()])
        stacked = np.vstack([g/sigma[:, None], np.sqrt(.0001)*factor])
        rhs = np.r_[observed.ravel()/sigma, np.sqrt(.0001)*factor@reference]
        oracle = lsq_linear(stacked, rhs, bounds=(lower, upper), method='bvls', tol=1e-12, max_iter=10000)
        optimum = np.linalg.norm(stacked@oracle.x-rhs)**2
        errors = dict(model_max=float(np.max(abs(result['q']-oracle.x))),
            objective_relative=float(abs(result['phi_engine']-optimum)/max(1., optimum)),
            prediction_rms=float(np.sqrt(np.mean((g@(result['q']-oracle.x))**2))))
        receipt['errors'] = errors
        np.testing.assert_allclose(result['q'], oracle.x, rtol=0., atol=1e-6)
        assert errors['objective_relative'] <= 1e-8
        assert errors['prediction_rms'] <= 1e-6
        gradient = obj.evaluate(result['q'], True, False)[1]
        projected = gradient.copy()
        projected[(result['q'] == lower)&(gradient > 0.)] = 0.
        projected[(result['q'] == upper)&(gradient < 0.)] = 0.
        initial = obj.evaluate(start, True, False)[1]
        assert np.linalg.norm(projected, np.inf) <= 1e-7*max(1., np.linalg.norm(initial, np.inf))
        receipt['accepted'] = True
    finally:
        obj.release_state()
        with output.open('x', encoding='utf-8') as handle:
            json.dump(serial(receipt), handle, sort_keys=True, allow_nan=False)
