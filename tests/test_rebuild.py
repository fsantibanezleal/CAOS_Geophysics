import hashlib
import json
from pathlib import Path
import numpy as np
import pytest
import torch
from electromagnetics import impedance,torch_impedance,curves
from geology import registry,properties,volume_grid,seismic_model,VOLUME_SHAPE
from potential import operators,invert
from joint import cross_gradient
from learning import InverseCNN,ObservationAE,load_checkpoint,generate
from seismic import simulate

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data/derived/v2"


def test_mt_halfspace_and_split_homogeneous_layer():
    f=np.geomspace(.001,1000,64)
    z=impedance(np.array([100.]),[],f)
    response=curves(z,f)
    np.testing.assert_allclose(response["apparent"],100,rtol=1e-12)
    np.testing.assert_allclose(response["phase"],45,rtol=1e-12)
    np.testing.assert_allclose(impedance(np.array([100.,100.,100.]),[500,600],f),z,rtol=1e-12)


def test_mt_autodiff_parity_and_directional_derivative():
    f=torch.logspace(-3,2,36,dtype=torch.float64)
    h=torch.tensor([300.,550.],dtype=torch.float64)
    x=torch.tensor(np.log([300.,15.,900.]),requires_grad=True)
    z=torch_impedance(x,h,f)
    np.testing.assert_allclose(z.detach().numpy(),impedance(x.detach().exp().numpy(),h.numpy(),f.numpy()),rtol=1e-12)
    objective=z.abs().square().sum();objective.backward()
    direction=torch.tensor([.3,-.7,.4],dtype=torch.float64);eps=1e-5
    fd=(torch_impedance(x.detach()+eps*direction,h,f).abs().square().sum()-torch_impedance(x.detach()-eps*direction,h,f).abs().square().sum())/(2*eps)
    assert float(fd)==pytest.approx(float(x.grad@direction),rel=1e-6)


def test_gravity_independent_prism_and_linear_scaling():
    from discretize import TensorMesh
    from simpeg import maps
    from simpeg.potential_fields import gravity
    from choclo.prism import gravity_u
    mesh=TensorMesh([[100.],[100.],[100.]],origin=[-50,-50,-100])
    loc=np.array([[0.,0.,50.],[130.,30.,80.]])
    survey=gravity.Survey(gravity.sources.SourceField([gravity.receivers.Point(loc,components="gz")]))
    G=gravity.simulation.Simulation3DIntegral(mesh,survey=survey,rhoMap=maps.IdentityMap(nP=1),engine="geoana").G
    independent=np.array([gravity_u(*p,-50.,50.,-50.,50.,-100.,0.,1000.)*1e5 for p in loc])
    np.testing.assert_allclose(G[:,0],independent,rtol=1e-5)
    assert np.all(G[:,0]<0)
    # SimPEG stores this small operator as float32.
    np.testing.assert_allclose(G@np.array([.7]),.7*G[:,0],rtol=1e-7)


def test_inverse_improves_data_fit():
    mesh,_,G,_=operators()
    truth=properties('stock',mesh.cell_centers)[0]
    d=G@truth
    for sparse in (False,True):
        out=invert(G,d,.006,.018,sparse)
        assert np.linalg.norm(out['residual'])<np.linalg.norm(d)*.2


def test_cross_gradient_parallel_and_orthogonal():
    z,y,x=torch.meshgrid(*(torch.arange(float(n)) for n in VOLUME_SHAPE),indexing='ij')
    assert torch.max(torch.abs(cross_gradient(x,3*x)))==0
    assert torch.mean(cross_gradient(x,y).square())>0


@pytest.mark.parametrize('family',['gravity','magnetics','mt','seismic','joint','learned'])
def test_all_artifact_cells(family):
    for case in registry():
        if case['family']!=family:continue
        for path in (DATA/case['id']).glob('*.json'):
            run=json.loads(path.read_text(encoding='utf-8'))
            for method_id,m in run['methods'].items():
                assert np.isfinite(m['model']).all()
                if family=='mt':
                    pred=impedance(np.asarray(m['model']),run['thickness'],np.asarray(run['frequencies']))
                    np.testing.assert_allclose(pred.real,m['predicted']['real'],rtol=2e-5,atol=1e-10)
                elif family=='seismic':
                    obs=np.asarray(run['observed']);pred=np.asarray(m['predicted']);res=np.asarray(m['residual'])
                    # JSON exports 7 significant digits, so cancellation has an absolute rounding floor.
                    np.testing.assert_allclose(obs-pred,res,rtol=1e-4,atol=2e-6*max(np.max(abs(obs)),np.max(abs(pred))))
                    assert m['metrics']['relative_mse']<m['metrics']['initial_relative_mse']
                    assert np.asarray(run['truth']).shape==(96,128)
                    assert np.asarray(run['wavefields']).shape[1:]==(96,128)
                    assert np.std(run['wavefields'])>0
                    expected_receivers=(torch.linspace(6,120,run['parameters']['receivers']).long()*12.5).tolist()
                    assert run['receivers']==expected_receivers
                elif method_id not in ('cnn','autoencoder'):
                    np.testing.assert_allclose(np.asarray(run['survey']['observed'])-m['predicted'],m['residual'],rtol=1e-3,atol=1e-4)


def test_learning_split_hashes_and_checkpoint_inference():
    meta=json.loads((DATA/'models/training.json').read_text())
    centers=volume_grid().cell_centers
    seen=set()
    for count,seed in zip(meta['split_counts'],meta['seeds']):
        for model in generate(centers,count,seed):
            digest=hashlib.sha256(model.tobytes()).hexdigest()
            assert digest not in seen,'Duplicate model across or within splits'
            seen.add(digest)
    run=json.loads((DATA/'LEARNED_CNN/reference.json').read_text(encoding='utf-8'))
    x=torch.tensor(np.asarray(run['survey']['observed'])/meta['input_scale'],dtype=torch.float32).reshape(1,1,16,16)
    with torch.no_grad():
        cnn=load_checkpoint(InverseCNN(),DATA/'models/cnn.json')
        ae=load_checkpoint(ObservationAE(),DATA/'models/autoencoder.json')
        np.testing.assert_allclose(cnn(x)[0].numpy()*meta['target_scale'],run['methods']['cnn']['model'],atol=.003)
        np.testing.assert_allclose(ae(x).flatten().numpy()*meta['input_scale'],run['methods']['autoencoder']['predicted'],atol=1e-5)
    assert len(meta['models']['cnn']['test_errors'])==160


def test_deepwave_cuda_adjoint_directional_derivative():
    assert torch.cuda.is_available(),'GPU execution is a release requirement'
    v=torch.tensor(seismic_model('normal_fault'),dtype=torch.float64,device='cuda',requires_grad=True)
    target=simulate(v.detach()+100,nt=1000)
    def objective(model):return (simulate(model,nt=1000)-target).square().mean()
    loss=objective(v);loss.backward()
    direction=v.grad.detach()/v.grad.detach().norm()
    eps=1.
    with torch.no_grad():fd=(objective(v+eps*direction)-objective(v-eps*direction))/(2*eps)
    adj=(v.grad*direction).sum()
    assert float(adj)>0
    assert float(fd)==pytest.approx(float(adj),rel=2e-3)


def test_ingest_rejects_invalid_and_sorts():
    from ingest import validate_table
    a=np.array([[10,10,50,1,.1],[0,0,50,2,.1],[10,0,50,3,.1],[0,10,50,4,.1]],dtype=float)
    b=validate_table(a)
    np.testing.assert_array_equal(b[:,:2],[[0,0],[10,0],[0,10],[10,10]])
    for column,value in [(0,np.nan),(4,0),(4,-1)]:
        invalid=a.copy();invalid[0,column]=value
        with pytest.raises(ValueError):validate_table(invalid)
    invalid=a.copy();invalid[1,:3]=invalid[0,:3]
    with pytest.raises(ValueError):validate_table(invalid)


def test_user_csv_inverse_executes(tmp_path):
    from ingest import invert_csv
    rows=['east_m,north_m,up_m,value,sigma']
    for y in [-100,0,100]:
        for x in [-100,0,100]:rows.append(f'{x},{y},50,{-0.1/(1+(x*x+y*y)/10000)},0.005')
    source=tmp_path/'input.csv';source.write_text('\n'.join(rows))
    out=tmp_path/'result.json';invert_csv(source,'gravity',out)
    result=json.loads(out.read_text())
    assert len(result['results']['irls']['model'])==1344
    assert len(result['results']['l2']['predicted'])==9
