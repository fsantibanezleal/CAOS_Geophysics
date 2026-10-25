"""Actual original frozen workflows, independent face oracle, unchanged caps."""
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import discretize
import numpy as np
import pytest
from simpeg import maps
from simpeg.regularization import CrossGradient

import joint_survey_instrument as instrument
import joint_survey_resources as resources
from test_joint_survey_oracles import explicit_faces,models
from test_joint_survey_plan import request


@pytest.mark.parametrize('sparse',[False,True])
@pytest.mark.parametrize('control',['nonparallel','constant','parallel','antiparallel'])
def test_exact_face_gram(sparse,control):
    req=request()
    if sparse:
        req['mesh']['active'][[2,5,8]]=False
        for prop in ('density','susceptibility'):
            for key in ('lower','upper','start','reference'):
                req['prior'][prop][key]=req['prior'][prop][key][req['mesh']['active']]
    q,_,_=models(req);n=len(q)//2
    if control=='constant': q[:n]=.3
    elif control=='parallel': q[n:]=.5+.1*q[:n]
    elif control=='antiparallel': q[n:]=.5-.1*q[:n]
    tensor=discretize.TensorMesh([req['mesh'][k] for k in ('hx_m','hy_m','hz_m')],origin=req['mesh']['origin_m'])
    exact=CrossGradient(tensor,maps.Wires(('density',n),('susceptibility',n)),
        active_cells=req['mesh']['active'],approx_hessian=False)
    G,A,v,axes=explicit_faces(req);factor=req['prior']['coupling_length_m']**4/v.sum()
    problem=SimpleNamespace(n=n,cross_exact=exact,factor=factor,_admit_state=lambda q,w:None)
    result=instrument.exact_face_gram(problem,q)
    a=G@q[:n];b=G@q[n:];B=np.sqrt(v)[:,None]*A
    p=B@(a*a);t=B@(b*b);h=B@(a*b)
    for key,value in zip(instrument.GRAM,(p,t,h,factor*(p*t-h*h))):
        np.testing.assert_allclose(result[key],value,atol=1e-10,rtol=1e-9)
    np.testing.assert_allclose(result['face_contribution'].sum(),factor*exact(q),atol=1e-10,rtol=1e-9)
    if control=='nonparallel':
        centre_a=np.column_stack([A[:,axes==axis]@a[axes==axis] for axis in range(3)])
        centre_b=np.column_stack([A[:,axes==axis]@b[axes==axis] for axis in range(3)])
        vector_energy=factor*np.sum(v*np.linalg.norm(np.cross(centre_a,centre_b),axis=1)**2)
        assert abs(vector_energy-result['face_contribution'].sum())>1e-8
    else: assert abs(result['face_contribution'].sum())<=1e-12


def test_precompute_cap(monkeypatch):
    payload={'original_file_sha256':{}}
    specs={f'c{i:02d}_response':('<f8',(251,2048)) for i in range(100)}
    monkeypatch.setattr(np,'empty',lambda *a,**k:pytest.fail('allocation before whole projection'))
    with pytest.raises(ValueError,match='projected whole byte cap'):
        instrument._admit_projection(specs,payload,0)
    with pytest.raises(ValueError): instrument._admit_projection({'bad':('<f8',(252,1))},payload,0)


@pytest.fixture(scope='module')
def bundle(tmp_path_factory):
    configured=os.environ.get('GEOPHYSICS_JOINT_MATRIX_FIXTURE')
    if not configured: pytest.skip('actual external full24 workflow fixture required')
    root=Path(configured);case=root/'joint-control-00'
    output=root/(tmp_path_factory.mktemp('instrument-name').name+'-instrument')
    scratch=tmp_path_factory.mktemp('instrument-scratch')
    args={'data_root':str(root),'development':str(case/'development'),'sealed':str(case/'sealed'),
        'original':str(case/'output'),'output':str(output),'scratch':str(scratch)}
    receipt=instrument.state_instrument_workflow(**args)
    with resources.JointResourceBudget(str(scratch)) as budget:
        _,paths=instrument._paths(**args,existing=True)
        problem,frozen,sealed,ledger,hashes,size=instrument._load(root,paths,budget)
        payload,arrays,specs=instrument._expected(problem,frozen,sealed,ledger,hashes,size,budget)
    return args,receipt,problem,frozen,sealed,ledger,payload,arrays,specs


def test_full_bundle_replay(bundle):
    args,receipt,*_=bundle
    assert receipt['validated'] and not receipt['scientific_acceptance_verified']
    assert not receipt['refit'] and receipt['resources']['complete_workflow_resource_pass']
    again=instrument.state_instrument_workflow(**args,validate=True)
    assert again['instrument_manifest_sha256']==receipt['instrument_manifest_sha256']
    with pytest.raises(FileExistsError): instrument.state_instrument_workflow(**args)
    with pytest.raises(SystemExit): instrument.main(['export','--dev','untrusted'])
    original=Path(args['original']);output=Path(args['output'])
    for relative in instrument._inventory(original)[0]:
        assert (output/relative).read_bytes()==(original/relative).read_bytes()
    assert hashlib.sha256((output/'instrument/instrument.json').read_bytes()).hexdigest()==receipt['instrument_manifest_sha256']


def test_state_responses(bundle):
    _,_,problem,frozen,sealed,ledger,payload,arrays,_=bundle
    assert len(payload['entries'])==28
    for entry in payload['entries']:
        key=entry['key']
        if key=='selected': states=frozen['q'][None,:]
        elif key=='baseline': states=np.concatenate([ledger['candidates'][ledger['selected_baselines'][m]]['result']['q'] for m in ('gravity','magnetic')])[None,:]
        else: states=ledger['candidates'][entry['stage']]['result']['trace']['models_q']
        for i,q in enumerate(states):
            for m in ('gravity','magnetic') if entry['modality'] is None else (entry['modality'],):
                sl=slice(0,problem.n) if m=='gravity' else slice(problem.n,2*problem.n)
                physical=q[sl]*problem.scales[sl] if entry['modality'] is None else q*problem.scales[sl]
                # Independent response multiplication, no instrument prediction call.
                prediction=problem.J[m]@physical
                for part in ('training','validation','sealed'):
                    prefix=key+'_'+m+'_'+part+'_';rows=problem.plan[m][part+'_rows']
                    np.testing.assert_array_equal(arrays[prefix+'predicted'][i],prediction[rows])
                    observed=sealed['arrays'][m+'_observed'] if part=='sealed' else problem.development[m]['observed'][
                        :len(rows)] if part=='training' else problem.development[m]['observed'][-len(rows):]
                    residual=prediction[rows]-observed
                    np.testing.assert_array_equal(arrays[prefix+'signed_residual'][i],residual)
                    white=arrays[prefix+'whitened_residual'][i]
                    np.testing.assert_array_equal(arrays[prefix+'metrics'][i],
                        [np.sqrt(np.mean(residual**2)),np.sqrt((white@white)/len(rows)),white@white])
        if entry['modality'] is not None:
            other='magnetic' if entry['modality']=='gravity' else 'gravity'
            assert not any(name.startswith(key+'_'+other) for name in arrays)
            assert not any(key+'_'+name in arrays for name in instrument.GRAM)
    assert any(c['result']['status']=='nonconverged' for c in ledger['candidates'])


def test_source_or_frame_tampering_rejects(bundle):
    args,_,*_=bundle;output=Path(args['output']);manifest=output/'instrument/instrument.json'
    original=manifest.read_bytes();document=json.loads(original)
    document['payload']['coupling_factor']*=2
    manifest.write_bytes(json.dumps(document).encode())
    try:
        with pytest.raises(ValueError,match='metadata drift'): instrument.state_instrument_workflow(**args,validate=True)
    finally: manifest.write_bytes(original)
