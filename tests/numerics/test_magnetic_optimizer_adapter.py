"""Real public optimizer composition, with independent test-only BVLS."""

import hashlib
import importlib.util
from pathlib import Path
from time import monotonic

import numpy as np
import pytest
from scipy.linalg import solve_triangular
from scipy.optimize import lsq_linear

from magnetic_inverse import MagneticQuantity
import magnetic_optimizer_adapter as adapter
import physical_optimizer as core


spec = importlib.util.spec_from_file_location('adapter_independent',
    Path(__file__).with_name('test_magnetic_survey_objective.py'))
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)


@pytest.fixture(scope='module')
def physical():
    return control.physical.__wrapped__()


def make(physical, quantity, covariance, penalty='l2', epsilon=0.):
    sim, g, independent, direction, _, _, _, r, volumes = physical
    op = MagneticQuantity(g, 50000.*direction, direction, 50000., quantity)
    geom = dict(origin_m=np.array(control.ORIGIN),
        hx_m=np.array(control.WIDTHS[0]),hy_m=np.array(control.WIDTHS[1]),
        hz_m=np.array(control.WIDTHS[2]),active=sim.active_cells.copy())
    reg = adapter.MagneticRegularizer(geom,control.QREF,np.array(control.LENGTHS),
        penalty,epsilon,control.Q)
    c = 3 if quantity == 'secondary_enu_nT' else 1
    kernel = .01*independent
    if c == 1:
        kernel = np.einsum('c,nca->na',direction,kernel.reshape(30,3,7))
    observed = (kernel @ control.Q).reshape(30,c)
    d = observed.size
    noise = {'kind':'diagonal_sd','values':np.full((30,c),.5)}
    if covariance:
        sigma = .5+.002*np.arange(d)
        noise = {'kind':'full_covariance','values':sigma[:,None]*sigma[None,:]*.22**np.abs(np.arange(d)[:,None]-np.arange(d))}
    obj = adapter.MagneticObjective(op,reg,observed,noise,np.zeros(7),np.full(7,10.),
        .3,'a'*64,'b'*64,0)
    return obj,kernel,observed,noise,r,volumes


@pytest.mark.parametrize('quantity',['secondary_enu_nT','linear_tmi_nT'])
@pytest.mark.parametrize('covariance',[False,True])
def test_actual_adapter_value_gradient_hessian_diagonal_and_free_face(physical,quantity,covariance):
    obj,kernel,d,noise,r,_ = make(physical,quantity,covariance)
    if covariance:
        lower = np.linalg.cholesky(noise['values'])
        wk = solve_triangular(lower,kernel,lower=True)
        wr = solve_triangular(lower,kernel@control.Q-d.ravel(),lower=True)
    else:
        wk = kernel/.5
        wr = (kernel@control.Q-d.ravel())/.5
    delta = control.Q-control.QREF
    phi = wr@wr+.3*np.linalg.norm(r@delta)**2
    gradient = 2*wk.T@wr+.6*r.T@(r@delta)
    hessian = 2*wk.T@wk+.6*r.T@r
    value,g,h = obj.evaluate(control.Q,True,True)
    np.testing.assert_allclose(value,phi,rtol=1e-10,atol=1e-10)
    np.testing.assert_allclose(g,gradient,rtol=1e-10,atol=1e-8)
    np.testing.assert_allclose(h@control.V,hessian@control.V,rtol=1e-10,atol=1e-8)
    np.testing.assert_allclose(obj.binding_diagonal(control.Q),np.diag(hessian),rtol=1e-10,atol=1e-8)
    free = np.array([0,2,6],dtype=np.int64)
    metric = obj.free_metric(control.Q,free)
    # Registered core action stores 1/diagonal once and then multiplies.
    # Division and reciprocal multiplication can differ by one native ulp.
    expected = np.zeros(7); expected[free] = (1./obj.binding_diagonal(control.Q))[free]*control.V[free]
    np.testing.assert_array_equal(metric@control.V,expected)
    assert obj.evaluate(control.Q) == value
    assert obj.evaluate(control.Q,False,True)[0] == value
    assert obj.evaluate(control.Q,True,False)[0] == value
    assert obj.components(control.Q)['phi_engine'] == value
    with pytest.raises((TypeError,ValueError)):
        obj.evaluate(control.Q,1,False)
    obj.release_state()
    assert obj.evaluate(control.Q) == value


@pytest.mark.parametrize('quantity',['secondary_enu_nT','linear_tmi_nT'])
@pytest.mark.parametrize('covariance',[False,True])
def test_real_public_linear_core_against_independent_bvls(physical,quantity,covariance):
    obj,kernel,d,noise,r,_ = make(physical,quantity,covariance)
    if covariance:
        lower = np.linalg.cholesky(noise['values'])
        wk,wd = solve_triangular(lower,kernel,lower=True),solve_triangular(lower,d.ravel(),lower=True)
    else:
        wk,wd = kernel/.5,d.ravel()/.5
    stacked = np.vstack([wk,np.sqrt(.3)*r])
    rhs = np.r_[wd,np.sqrt(.3)*r@control.QREF]
    reference = lsq_linear(stacked,rhs,bounds=(0.,10.),method='bvls',tol=1e-12,max_iter=10000)
    binding = core.OptimizerBinding('physical_optimizer.solve_bounded_physical',core.SOURCE_SHA256,
        hashlib.sha256(Path(adapter.certificate_source()).read_bytes()).hexdigest(),'a'*64,
        core.RUNTIME_EPOCH,core.POLICY)
    budget = core.OptimizerBudget(monotonic()+120.,200,805306368,1000000,'b'*64)
    result = adapter.solve_linear(obj,np.zeros(7),np.full(7,10.),np.zeros(7),budget=budget,binding=binding)
    assert result['status'] == 'converged', result['reason']
    np.testing.assert_allclose(result['q'],reference.x,rtol=0.,atol=1e-6)
    optimum = np.linalg.norm(stacked@reference.x-rhs)**2
    assert abs(result['phi_engine']-optimum)/max(1.,optimum) <= 1e-8
    assert np.sqrt(np.mean((kernel@(result['q']-reference.x))**2)) <= 1e-6
    _,gradient = obj.evaluate(result['q'],True,False)
    projected = gradient.copy()
    projected[(result['q'] <= 32*np.finfo(float).eps)&(gradient>0.)] = 0.
    projected[(result['q'] >= 10.-320*np.finfo(float).eps)&(gradient<0.)] = 0.
    initial = obj.evaluate(np.zeros(7),True,False)[1]
    assert np.linalg.norm(projected,np.inf) <= 1e-7*max(1.,np.linalg.norm(initial,np.inf))
    assert result['iterations'] > 0
    assert result['trace']['models_q'].shape[0] == result['iterations']+1


@pytest.mark.parametrize('epsilon',[.1,.05,.025,.0125,.00625,.003125,.0015625,.001])
def test_actual_sparse_fixed_surrogate_and_terms(physical,epsilon):
    obj,_,_,_,r,volumes = make(physical,'linear_tmi_nT',False,'sparse_smallness',epsilon)
    delta = control.Q-control.QREF
    weights = 1./np.sqrt(delta**2+epsilon**2)
    expected = np.sum(volumes/volumes.sum()*weights*delta**2)+np.linalg.norm(r[7:]@delta)**2
    np.testing.assert_allclose(obj.components(control.Q)['phi_m'],expected,rtol=1e-10,atol=1e-10)
    assert obj.identity()['physical_scale'] == .01
    assert obj.identity()['q_unit'] == 'chi_over_0.01'


def test_unregistered_nonlinear_and_wrong_source_binding_refuse(physical):
    obj,_,_,_,_,_ = make(physical,'linear_tmi_nT',False)
    binding = core.OptimizerBinding('physical_optimizer.solve_bounded_physical','c'*64,'d'*64,'a'*64,
                                    core.RUNTIME_EPOCH,core.POLICY)
    budget = core.OptimizerBudget(monotonic()+120.,200,805306368,1000000,'b'*64)
    with pytest.raises(ValueError,match='source'):
        adapter.solve_linear(obj,np.zeros(7),np.full(7,10.),np.zeros(7),budget=budget,binding=binding)
