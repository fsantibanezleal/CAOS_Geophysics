"""Trusted linear composition controls using actual SimPEG physics and proof.

Dense bounded least squares below is an independent test oracle, never a runtime
optimizer. This does not register a magnetic driver or certify nonlinear physics.
"""
from dataclasses import replace
import hashlib
import importlib.util
from pathlib import Path
from time import monotonic

import numpy as np
import pytest
import scipy.sparse as sp
from scipy.sparse.linalg import LinearOperator
from scipy.optimize import lsq_linear

import gravity_l2 as l2
import gravity_l2_precision as precision
import physical_optimizer as core


def _controls():
    path = Path(__file__).with_name('test_gravity_l2.py')
    spec = importlib.util.spec_from_file_location('_physical_test_oracles', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NativeObjective:
    """Test-owned adapter of genuine official misfit/regularizer calls."""
    def __init__(self, kind='full_covariance', bounded=False, null=False):
        controls = _controls()
        req, data, prior, bounds, _ = controls.tiny()
        if bounded:
            prior['lower_kg_m3'][:] = -100.
            prior['upper_kg_m3'][:] = 100.
        if null:
            data = req['background_mgal'].copy()
            prior['reference_kg_m3'][:] = 0.
        self.problem = l2._build_problem(req, data, controls.noise(kind), prior,
                                        np.arange(4, dtype=np.int64), .01)
        self.lower = prior['lower_kg_m3']/1000.
        self.upper = prior['upper_kg_m3']/1000.
        self.start = prior['start_kg_m3']/1000.
        self.beta = self.problem['beta_engine']
        self.r = controls.independent_r(bounds, prior['lengths_m'], 1.)
        weighted = self.problem['misfit'].W @ self.problem['simulation'].G
        self.diagonal = (2*np.sum(weighted*weighted, axis=0)
                         + self.beta*self.problem['regularization'].deriv2(self.start).diagonal())
        digest = hashlib.sha256()
        for array in (self.problem['simulation'].G, self.problem['misfit'].W.toarray(),
                      self.problem['misfit'].data.dobs, self.r, self.problem['reference_q'],
                      self.lower, self.upper, np.array([self.beta])):
            digest.update(array.tobytes())
        self.identity_value = {
            'mode': 'fixed_linear_quadratic', 'runtime_epoch': core.RUNTIME_EPOCH,
            'objective_sha256': digest.hexdigest(), 'source_inventory_sha256': 'a'*64,
            'q_unit': 'g/cc', 'physical_unit': 'kg/m3', 'physical_scale': 1000.,
            'parameter_count': 5, 'observation_rows': 4, 'observation_components': 1,
            'beta_engine': self.beta, 'stage_index': 0, 'allocation_plan_sha256': 'b'*64}
        self.calls, self.released, self.certificates = 0, 0, []

    def identity(self):
        return dict(self.identity_value)

    def components(self, q):
        pd, pm = float(self.problem['misfit'](q)), float(self.problem['regularization'](q))
        return {'phi_d': pd, 'phi_m': pm, 'phi_engine': float(pd+self.beta*pm)}

    def evaluate(self, q, return_g=False, return_H=False):
        self.calls += 1
        phi = self.components(q)['phi_engine']
        result = [phi]
        if return_g:
            result.append(self.problem['misfit'].deriv(q)+self.beta*self.problem['regularization'].deriv(q))
        if return_H:
            result.append(LinearOperator((5, 5), matvec=lambda v:
                self.problem['misfit'].deriv2(q, v)+self.beta*self.problem['regularization'].deriv2(q, v),
                dtype=np.float64))
        return tuple(result) if len(result)>1 else phi

    def binding_diagonal(self, q):
        return self.diagonal.copy()

    def free_metric(self, q, free_indices):
        action = np.zeros(5)
        action[free_indices] = 1./self.diagonal[free_indices]
        return sp.linalg.aslinearoperator(sp.diags(action))

    def certify(self, q, qt, native_gradient, native_phi, native_phi_trial, iteration, trial, deadline):
        proof = precision._CertifiedDelta(self.problem, self.lower, self.upper, deadline)
        record = proof.evaluate(q, qt, native_gradient, iteration, trial, native_phi, native_phi_trial)
        self.certificates.append(record)
        return record

    def release_state(self):
        self.released += 1


def _arguments(obj, *, steps=200, deadline=None):
    binding = core.OptimizerBinding('physical_optimizer.solve_bounded_physical',
        core.SOURCE_SHA256, hashlib.sha256(Path(precision.__file__).read_bytes()).hexdigest(),
        obj.identity_value['source_inventory_sha256'], core.RUNTIME_EPOCH, core.POLICY)
    budget = core.OptimizerBudget(monotonic()+120. if deadline is None else deadline, steps,
        2*1024**3, 16*1024**2, obj.identity_value['allocation_plan_sha256'])
    return dict(budget=budget, binding=binding)


def _solve(obj, **kwargs):
    return core.solve_bounded_physical(obj, obj.lower, obj.upper, obj.start, **_arguments(obj, **kwargs))


@pytest.mark.parametrize('kind', ['diagonal_sd', 'full_covariance'])
@pytest.mark.parametrize('bounded', [False, True])
def test_GS02_real_native_linear_optimum_and_strict_certificates(kind, bounded, record_property):
    obj = NativeObjective(kind, bounded)
    result = _solve(obj)
    assert result['status'] == 'converged', result
    assert result['reason'] in ('absolute_stationary', 'kkt_stable')
    g, w = obj.problem['simulation'].G, obj.problem['misfit'].W.toarray()
    matrix = np.vstack((w@g, np.sqrt(obj.beta)*obj.r))
    rhs = np.r_[w@obj.problem['misfit'].data.dobs,
                np.sqrt(obj.beta)*obj.r@obj.problem['reference_q']]
    oracle = lsq_linear(matrix, rhs, bounds=(obj.lower, obj.upper), tol=1e-12,
                        method='bvls', max_iter=1000)
    assert oracle.success
    np.testing.assert_allclose(result['q'], oracle.x, rtol=1e-7, atol=1e-8)
    np.testing.assert_allclose(g@result['q'], g@oracle.x, rtol=1e-7, atol=1e-9)
    assert result['phi_engine'] == obj.components(result['q'])['phi_engine']
    assert obj.released == 1
    assert result['iterations']>0 and len(obj.certificates)>=result['iterations']
    for cert in obj.certificates:
        precision._validate_record(cert)
    assert sum(c['decision']=='certified_accept' for c in obj.certificates)==result['iterations']
    record_property('native_outcome', result['status'].upper()+'/'+result['reason'].upper())
    record_property('certificate_outcome', 'CERTIFIED_ACCEPT')
    record_property('iterations', result['iterations'])
    assert set(result)=={'status','reason','q','phi_d','phi_m','phi_engine','kkt_normalized',
                         'iterations','trace','failed_trial'}
    assert set(result['trace'])=={'models_q','phi_d','phi_m','phi_engine','kkt_normalized',
                                'relative_changes','line_search_counts','cg_counts'}
    assert not result['q'].flags.writeable


def test_GS01_all_actual_vendor_callable_combinations():
    obj = NativeObjective()
    for gradient in (False, True):
        for hessian in (False, True):
            output = obj.evaluate(obj.start, gradient, hessian)
            values = output if gradient or hessian else (output,)
            assert len(values)==1+gradient+hessian
            assert type(values[0]) is float and np.isfinite(values[0])
            if gradient: assert values[1].shape==(5,)
            if hessian:
                np.testing.assert_allclose(values[-1]@np.ones(5),
                    obj.problem['misfit'].deriv2(obj.start, np.ones(5))+
                    obj.beta*obj.problem['regularization'].deriv2(obj.start, np.ones(5)))


def test_GS09_null_has_no_manufactured_steps():
    obj = NativeObjective(null=True)
    result = _solve(obj, steps=0)
    assert result['status']=='converged' and result['reason']=='absolute_stationary'
    assert result['iterations']==0 and len(result['trace']['models_q'])==1
    assert obj.certificates==[] and obj.released==1


def test_GS09_shared_step_ledger_retains_real_terminal():
    obj = NativeObjective()
    result = _solve(obj, steps=1)
    assert result['status']=='nonconverged' and result['reason']=='iteration_cap'
    assert result['iterations']==1 and len(result['trace']['models_q'])==2
    assert sum(c['decision']=='certified_accept' for c in obj.certificates)==1


def test_GS09_expired_no_callback_no_partial_state():
    obj = NativeObjective()
    result = _solve(obj, deadline=monotonic()-1.)
    assert result['status']=='nonconverged' and result['reason']=='wall_cap'
    assert result['q'] is None and result['phi_engine'] is None
    assert len(result['trace']['models_q'])==0 and obj.calls==0
    assert obj.certificates==[]


def test_GS07_nonlinear_remains_explicitly_unsupported():
    obj = NativeObjective()
    obj.identity_value['mode']='nonlinear_gauss_newton'
    result = _solve(obj)
    assert result['status']=='failed' and result['reason']=='dependency_unsupported'
    assert result['q'] is None and obj.calls==0


@pytest.mark.parametrize('field,value', [('optimizer_source_sha256','0'*64),
    ('runtime_epoch','wrong'), ('policy','wrong'), ('accepted_export','gravity_l2._solve_partition'),
    ('source_inventory_sha256','c'*64), ('certificate_source_sha256',None)])
def test_GS10_wrong_binding_rejects_before_callbacks(field,value):
    obj = NativeObjective()
    args = _arguments(obj)
    args['binding']=replace(args['binding'], **{field:value})
    with pytest.raises(ValueError):
        core.solve_bounded_physical(obj,obj.lower,obj.upper,obj.start,**args)
    assert obj.calls==0


@pytest.mark.parametrize('field,value', [('remaining_steps',201),('remaining_steps',True),
    ('admitted_bytes',2*1024**3+1),('admitted_bytes',0),('deadline',float('inf')),
    ('allocation_plan_sha256','c'*64)])
def test_GS10_bad_admission_rejects_before_callbacks(field,value):
    obj=NativeObjective()
    args=_arguments(obj)
    args['budget']=replace(args['budget'], **{field:value})
    with pytest.raises(ValueError):
        core.solve_bounded_physical(obj,obj.lower,obj.upper,obj.start,**args)
    assert obj.calls==0


@pytest.mark.parametrize('fault', ['identity','component','gradient','hessian','metric','certificate'])
def test_GS10_malformed_or_stale_callback_fails_closed(fault):
    obj=NativeObjective()
    if fault=='identity':
        original=obj.evaluate
        def evaluate(*args):
            obj.identity_value['objective_sha256']='d'*64
            return original(*args)
        obj.evaluate=evaluate
    if fault=='component':
        original=obj.components
        obj.components=lambda q: dict(original(q), extra=0.)
    if fault=='gradient':
        original=obj.evaluate
        def evaluate(q,g=False,h=False):
            values=original(q,g,h)
            return (values[0],np.full(5,np.nan),values[2]) if g and h else values
        obj.evaluate=evaluate
    if fault=='hessian':
        original=obj.evaluate
        def evaluate(q,g=False,h=False):
            values=original(q,g,h)
            return (values[0],values[1],np.eye(5)) if g and h else values
        obj.evaluate=evaluate
    if fault=='metric': obj.free_metric=lambda q,free: sp.linalg.aslinearoperator(sp.eye(5))
    if fault=='certificate': obj.certify=lambda *args: {'decision':'certified_accept'}
    result=_solve(obj)
    assert result['status']=='failed' and result['reason'] in ('state_mismatch','nonfinite','engine_error')
    assert result['iterations']==0 and obj.released==1


def test_GS04_true_H_residual_checked_before_vendor_deletes_H(monkeypatch):
    obj=NativeObjective()
    monkeypatch.setattr(core.optimization.ProjectedGNCG,'findSearchDirection',
                        lambda self: -self.g*1e-12)
    result=_solve(obj)
    assert result['status']=='nonconverged' and result['reason']=='cg_cap'
    assert result['iterations']==0 and obj.certificates==[]


def test_GS09_deadline_after_actual_acceptance_retains_and_charges_step(monkeypatch):
    obj=NativeObjective()
    clock=[monotonic()]
    monkeypatch.setattr(core,'monotonic',lambda: clock[0])
    original=core.optimization.ProjectedGNCG.doEndIteration
    def end(self,xt):
        original(self,xt)
        clock[0]+=121.
    monkeypatch.setattr(core.optimization.ProjectedGNCG,'doEndIteration',end)
    result=_solve(obj,deadline=clock[0]+120.)
    assert result['reason']=='wall_cap' and result['status']=='nonconverged'
    assert result['iterations']==1 and len(result['trace']['models_q'])==2
    assert sum(c['decision']=='certified_accept' for c in obj.certificates)==1
    assert result['q'] is not None and result['phi_engine']==obj.components(result['q'])['phi_engine']


def test_GS04_exact_native_binding_release_precedes_any_CG():
    obj=NativeObjective(bounded=True)
    obj.start[:]=obj.lower
    result=_solve(obj)
    assert result['status']=='converged',result
    assert result['trace']['cg_counts'][0]==0
    assert result['iterations']>0


def test_GS05_complete_certificate_boundary_no_partial_acceptance():
    obj=NativeObjective()
    original=obj.certify
    def certify(*args):
        value=original(*args)
        value['native_phi_current']=value['native_phi_current']+1.
        return value
    obj.certify=certify
    result=_solve(obj)
    assert result['reason']=='state_mismatch' and result['iterations']==0


@pytest.mark.parametrize('fault',['nan','project','list','subclass','shape'])
def test_GS10_bounds_are_exact_native_owned_inputs(fault):
    obj=NativeObjective()
    start=obj.start.copy()
    if fault=='nan': start[0]=np.nan
    if fault=='project': start[0]=obj.upper[0]+1.
    if fault=='list': start=start.tolist()
    if fault=='subclass': start=start.view(type('Foreign', (np.ndarray,), {}))
    if fault=='shape': start=start.reshape(1,5)
    with pytest.raises(ValueError):
        core.solve_bounded_physical(obj,obj.lower,obj.upper,start,**_arguments(obj))
    assert obj.calls==0
