import numpy as np
import pytest
import torch
from spatial_inverse import differences, precision, solve, conditional_ensemble
from spatial_inverse import geometry
from evaluation import evaluate
from petrophysics import fit_prior
from joint import mixture_nll, cross_gradient, spatial_energy, structural_negative_control
from geology import VOLUME_SHAPE, VOLUME_SPACING


def test_physical_derivatives_and_positive_precision():
    shape=(4,5,6);spacing=(80.,60.,40.)
    z,y,x=np.meshgrid(np.arange(4)*40,np.arange(5)*60,np.arange(6)*80,indexing='ij')
    field=3*x+2*y-z
    for (D,_,_),expected in zip(differences(shape,spacing),(-1,2,3)):
        np.testing.assert_allclose(D@field.ravel(),expected,atol=1e-12)
    Q=precision(shape,spacing).toarray()
    np.testing.assert_allclose(Q,Q.T,atol=1e-12)
    assert np.linalg.eigvalsh(Q).min()>0


def test_sigma_changes_inverse_and_final_state_is_exact():
    rng=np.random.default_rng(68910)
    G=rng.normal(size=(32,120));truth=rng.normal(size=120)
    d=G@truth+rng.normal(size=32)*.1
    a,states=solve(G,d,.1,(4,5,6),(80.,60.,40.))
    b,_=solve(G,d,1.,(4,5,6),(80.,60.,40.))
    assert np.linalg.norm(a-b)>1e-3
    np.testing.assert_array_equal(a,states['frames'][-1])
    assert np.mean(((G@a-d)/.1)**2)==pytest.approx(1.,rel=1e-6)
    with pytest.raises(ValueError):solve(G,d,0.,(4,5,6),(80.,60.,40.))


def test_conditional_ensemble_repeats_and_does_not_claim_posterior():
    rng=np.random.default_rng(4);G=rng.normal(size=(12,24));d=rng.normal(size=12)
    _,states=solve(G,d,.1,(2,3,4),(80.,80.,70.))
    args=(G,d,.1,(2,3,4),(80.,80.,70.),states['solver']['beta'],741)
    a,b=conditional_ensemble(*args),conditional_ensemble(*args)
    assert a==b
    assert np.all(np.asarray(a['upper'])>=a['lower'])
    assert 'Not a posterior' in a['conditioning']


def test_evaluation_rejects_perfect_data_but_failed_model():
    truth=np.array([0.,0.,1.,1.]);model=-truth
    metrics,verdict=evaluate(model,truth,np.ones(4),np.ones(4),.1,np.ones(4,bool))
    assert metrics['wrms']==0
    assert verdict['status']=='failed'
    assert 'no-improvement-over-initial-model' in verdict['reason_codes']


def test_gmm_fit_independent_repeatable_and_gradient():
    prior=fit_prior();assert prior==fit_prior()
    assert len(prior['samples'])==640
    assert prior['em_negative_log_likelihood'][-1]<=prior['em_negative_log_likelihood'][0]
    a=torch.tensor([.1,.8],dtype=torch.float64,requires_grad=True)
    b=torch.tensor([.2,.9],dtype=torch.float64,requires_grad=True)
    loss,prob=mixture_nll(a,b,prior);loss.backward()
    np.testing.assert_allclose(prob.detach().sum(1),1.)
    eps=1e-6
    fd=(mixture_nll(a.detach()+eps,b.detach(),prior)[0]-mixture_nll(a.detach()-eps,b.detach(),prior)[0])/(2*eps)
    assert float(fd)==pytest.approx(float(a.grad.sum()),rel=1e-6)


def test_cross_gradient_uses_metre_spacing():
    z,y,x=torch.meshgrid(torch.arange(4.),torch.arange(5.),torch.arange(6.),indexing='ij')
    coarse=cross_gradient(x,y,(4,5,6),(2.,2.,2.))
    fine=cross_gradient(x,y,(4,5,6),(1.,1.,1.))
    torch.testing.assert_close(fine,4*coarse)


def test_cross_gradient_physical_amplitude_and_spatial_energy():
    shape=(4,5,6);spacing=(80.,60.,40.)
    z,y,x=torch.meshgrid(torch.arange(4)*40.,torch.arange(5)*60.,torch.arange(6)*80.,indexing='ij')
    cross=cross_gradient(2*x,3*y,shape,spacing)
    torch.testing.assert_close(cross[0],torch.full(shape,-6.))
    torch.testing.assert_close(cross[1:],torch.zeros_like(cross[1:]))
    rng=np.random.default_rng(8651)
    model=rng.normal(size=np.prod(VOLUME_SHAPE))
    weights=geometry(VOLUME_SHAPE,VOLUME_SPACING)[0]**2
    direct=model@precision(VOLUME_SHAPE,VOLUME_SPACING)@model
    computed=spatial_energy(torch.tensor(model),torch.tensor(weights).reshape(VOLUME_SHAPE))
    assert float(computed)==pytest.approx(float(direct),rel=1e-12)


def test_joint_conflict_labels_both_coupled_methods():
    assert structural_negative_control('joint','conflict')
    assert structural_negative_control('pgi','conflict')
    assert not structural_negative_control('joint-uncoupled','conflict')
    assert not structural_negative_control('joint','shared')


def test_joint_conflict_verdict_and_optimized_uncoupled_reference(monkeypatch):
    from types import SimpleNamespace
    import joint
    shape=(2,2,2);spacing=(80.,80.,70.)
    rng=np.random.default_rng(8892)
    gravity_operator=rng.normal(size=(6,8))
    magnetic_operator=rng.normal(size=(6,8))
    density=np.array([.45,.45,0.,0.,0.,0.,0.,0.])
    susceptibility=np.array([0.,0.,0.,0.,.03,.03,0.,0.])
    initial_density=np.array([.2,.1,.1,0.,0.,0.,0.,0.])
    initial_magnetic=np.array([0.,.01,0.,0.,.01,0.,0.,0.])
    active=np.array([True,True,True,True,False,False])
    run=dict(seed=881,variant='reference',geometry='conflict',truth=density.tolist(),
             secondary_truth=susceptibility.tolist(),
             survey=dict(observed=(gravity_operator@density).tolist(),sigma=.1,active=active.tolist()),
             parameters=dict(height_m=60),
             methods={'l2':dict(model=initial_density.tolist(),solver=dict(beta=.1))})
    monkeypatch.setattr(joint,'VOLUME_SHAPE',shape)
    monkeypatch.setattr(joint,'VOLUME_SPACING',spacing)
    monkeypatch.setattr(joint,'invert',lambda *args,**kwargs:
                        dict(model=initial_magnetic.tolist(),solver=dict(beta=.1)))
    original_gradient=joint.cross_gradient
    monkeypatch.setattr(joint,'cross_gradient',lambda a,b:
                        original_gradient(a,b,shape,spacing))
    centers=np.stack(np.meshgrid(np.arange(2),np.arange(2),np.arange(2),indexing='ij'),-1).reshape(-1,3)
    cache={60:(SimpleNamespace(cell_centers=centers),None,gravity_operator,magnetic_operator)}
    joint.attach(run,cache,iterations=2)
    uncoupled=run['methods']['joint-uncoupled']
    assert uncoupled['evaluation']['status']!='negative-control'
    assert uncoupled['metrics']['model_rmse']!=pytest.approx(
        np.sqrt(np.mean((initial_density-density)**2)),abs=1e-7)
    for method in ('joint','pgi'):
        result=run['methods'][method]
        identity=result['state_identity']
        np.testing.assert_allclose(result['frames'][identity['final_frame_index']],
                                   result['model'],rtol=0,atol=1e-14)
        assert identity['selected_iteration']==2
        data,regular,cross,mixture=result['objective_terms'][-1]
        expected=data+regular+result['solver']['cross_gradient_weight']*cross
        expected+=result['solver']['mixture_weight']*mixture
        assert result['history'][-1]==pytest.approx(expected,rel=1e-12)
        assert result['evaluation']['status']=='negative-control'
        assert result['evaluation']['reason_codes'].count(
            'structural-coupling-prior-conflicts-with-reference')==1
        assert 'deliberately-misspecified-physical-model' not in result['evaluation']['reason_codes']
        assert result['metrics']['independent_model_rmse']==pytest.approx(
            uncoupled['metrics']['model_rmse'])
        assert result['metrics']['independent_baseline_ratio']==pytest.approx(
            result['metrics']['model_rmse']/uncoupled['metrics']['model_rmse'])
        assert result['metrics']['independent_magnetic_model_rmse']==pytest.approx(
            uncoupled['metrics']['magnetic_model_rmse'])
        assert result['metrics']['independent_magnetic_baseline_ratio']==pytest.approx(
            result['metrics']['magnetic_model_rmse']/uncoupled['metrics']['magnetic_model_rmse'])
        assert result['solver']['matched_baseline_method']=='joint-uncoupled'


def test_independent_magnetic_prism_and_vector_convention():
    from discretize import TensorMesh
    from simpeg import maps
    from simpeg.potential_fields import magnetics
    from simpeg.utils.mat_utils import dip_azimuth2cartesian
    from choclo.prism import magnetic_field
    from potential import vector_matrix
    mesh=TensorMesh([[100.],[100.],[100.]],origin=[-50.,-50.,-100.])
    locations=np.array([[0.,0.,50.],[130.,30.,80.],[-30.,130.,120.]])
    direction=dip_azimuth2cartesian(np.array([60.]),np.array([12.]))[0]
    survey=magnetics.Survey(magnetics.sources.UniformBackgroundField(
        [magnetics.receivers.Point(locations,components='tmi')],amplitude=50000,inclination=60,declination=12))
    G=magnetics.simulation.Simulation3DIntegral(mesh,survey=survey,chiMap=maps.IdentityMap(nP=1),engine='geoana').G
    mu0=4*np.pi*1e-7
    magnetization=direction*50000e-9/mu0
    independent=np.array([np.dot(magnetic_field(*point,-50.,50.,-50.,50.,-100.,0.,*magnetization),direction)*1e9 for point in locations])
    np.testing.assert_allclose(G[:,0],independent,rtol=2e-6)
    np.testing.assert_allclose(vector_matrix(mesh,locations)@direction,G[:,0],rtol=2e-6)
    # One cell cannot distinguish component-major from cell-major vector order.
    two_cells=TensorMesh([[100.,100.],[100.],[100.]],origin=[-100.,-50.,-100.])
    survey_two=magnetics.Survey(magnetics.sources.UniformBackgroundField(
        [magnetics.receivers.Point(locations,components='tmi')],amplitude=50000,inclination=60,declination=12))
    scalar=magnetics.simulation.Simulation3DIntegral(
        two_cells,survey=survey_two,chiMap=maps.IdentityMap(nP=two_cells.nC),engine='geoana').G
    susceptibility=np.array([.03,.08])
    vector_parameters=np.concatenate([susceptibility*component for component in direction])
    np.testing.assert_allclose(vector_matrix(two_cells,locations)@vector_parameters,
                               scalar@susceptibility,rtol=2e-6,atol=2e-5)
