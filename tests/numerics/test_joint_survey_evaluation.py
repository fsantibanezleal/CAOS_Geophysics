"""Frozen physical evaluation, file commitments, and adverse private exports."""
from copy import deepcopy
import json

import numpy as np
import pytest

import joint_survey_compiled as compiled
import joint_survey_evaluation as evaluation
import joint_survey_files as files
import joint_survey_intake as intake
import joint_survey_plan as planner
import joint_survey_model_export as model_export
from test_joint_survey_intake import fixture,write_request


@pytest.fixture(params=[False,True],ids=['diagonal','covariance'])
def prepared(tmp_path,request):
    development=tmp_path/'development';development.mkdir()
    doc,_=fixture(development,covariance=request.param)
    admitted=intake.load_joint_development(str(development))
    problem=compiled.compile_joint_development({'schema':'joint-survey-compile-request-1',
        'survey_request':admitted['survey_request'],'development':admitted['development']})
    arrays={}
    for m in evaluation.MODALITIES:
        rows=problem.plan[m]['sealed_rows'];n=len(rows)
        arrays[m+'_rows']=rows;arrays[m+'_observed']=np.arange(n,dtype=np.float64)+.3
        arrays[m+'_noise']=np.eye(n)*.25 if request.param else np.full(n,.5)
    sealed=tmp_path/'sealed'
    manifest=evaluation.write_joint_sealed(str(sealed),problem.plan,arrays)
    doc['sealed_manifest']=manifest;write_request(development,doc)
    frozen=evaluation.freeze_joint_model(problem,problem.start,
        {'beta_gravity':.001,'beta_magnetic':.01,'coupling':.1})
    loaded=evaluation.load_joint_sealed(str(sealed),problem,frozen,manifest)
    return tmp_path,problem,frozen,loaded,manifest,sealed


def test_actual_marginal_metrics_and_result_roundtrip(prepared):
    root,problem,frozen,sealed,_,_=prepared
    freeze_dir=root/'frozen';evaluation.write_frozen_model(str(freeze_dir),frozen,problem)
    reread=evaluation.load_frozen_model(str(freeze_dir),problem)
    assert planner._digest(reread)==planner._digest(frozen)
    result=evaluation.evaluate_frozen_joint(problem,reread,sealed)
    state=problem.state(frozen['q'],frozen['weights'])
    assert result['payload']['terms']==state['terms']
    for m in evaluation.MODALITIES:
        for p in evaluation.PARTITIONS:
            base=m+'_'+p+'_';arrays=result['arrays'];metrics=result['payload']['metrics'][m][p]
            np.testing.assert_array_equal(arrays[base+'signed_residual'],arrays[base+'predicted']-arrays[base+'observed'])
            assert metrics['chi_square']==float(arrays[base+'whitened_residual']@arrays[base+'whitened_residual'])
            assert metrics['wrms']==np.sqrt(metrics['chi_square']/metrics['count'])
        assert result['payload']['claims']['cross_partition_dependence'][m]==problem.plan[m]['noise']['cross_partition']
    assert not result['payload']['claims']['inverse_completed']
    assert not result['payload']['claims']['field_eligible']
    destination=root/'result';evaluation.write_joint_result(str(destination),result)
    assert evaluation.validate_joint_result(str(destination),problem,frozen,sealed)['validated']
    assert len(list(destination.iterdir()))==32
    for value in result['arrays'].values(): assert not value.flags.writeable and value.flags.owndata
    with pytest.raises(FileExistsError): evaluation.write_joint_result(str(destination),result)


@pytest.mark.parametrize('bad',['frozen_hash','q','weights','plan','origin','sealed_commitment'])
def test_freeze_and_committed_file_rejection_precedes_sealed_load(prepared,monkeypatch,bad):
    _,problem,frozen,_,manifest,directory=prepared
    frozen=deepcopy(frozen);manifest=deepcopy(manifest)
    if bad=='frozen_hash': frozen['frozen_sha256']='a'*64
    elif bad=='q': frozen['q'][0]=np.nextafter(frozen['q'][0],np.inf)
    elif bad=='weights': frozen['weights']['coupling']=.01
    elif bad=='plan': frozen['plan_sha256']='b'*64
    elif bad=='origin': frozen['origin']='optimized_selection'
    else: manifest['gravity']['observations_file_sha256']='c'*64
    def forbidden(*a,**k): pytest.fail('invalid commitment read sealed value')
    monkeypatch.setattr(np,'load',forbidden)
    monkeypatch.setattr(intake,'_file_sha',forbidden)
    with pytest.raises((ValueError,TypeError)):
        evaluation.load_joint_sealed(str(directory),problem,frozen,manifest)


@pytest.mark.parametrize('bad',['observed','rows','stale','extra'])
def test_native_sealed_tampering_is_not_trusted(prepared,bad):
    _,problem,frozen,sealed,_,_=prepared;sealed=deepcopy(sealed)
    if bad=='observed': sealed['arrays']['gravity_observed'][0]+=.1
    elif bad=='rows': sealed['arrays']['gravity_rows'][0]=0
    elif bad=='stale': sealed['frozen_sha256']='c'*64
    else: sealed['truth']='not admitted'
    with pytest.raises(ValueError): evaluation.evaluate_frozen_joint(problem,frozen,sealed)


@pytest.mark.parametrize('bad',['shape','dtype','extra','boolean_shape','duplicate','truncated'])
def test_sealed_all_descriptors_precede_value_load(prepared,monkeypatch,bad):
    _,problem,frozen,_,manifest,directory=prepared
    document=json.loads((directory/'sealed.json').read_bytes())
    if bad=='shape': document['arrays']['magnetic_observed']['shape']=[2049]
    elif bad=='dtype': document['arrays']['magnetic_observed']['dtype']='>f8'
    elif bad=='boolean_shape': document['arrays']['magnetic_observed']['shape']=[True]
    elif bad=='extra': document['payload']['callback']='not allowed'
    elif bad=='truncated': (directory/'gravity_rows.npy').write_bytes(b'bad header')
    if bad=='duplicate': (directory/'sealed.json').write_bytes(b'{"schema":1,"schema":2}')
    else: (directory/'sealed.json').write_text(json.dumps(document),encoding='utf-8')
    monkeypatch.setattr(np,'load',lambda *a,**k:pytest.fail('metadata/header violation loaded values'))
    monkeypatch.setattr(intake,'_file_sha',lambda *a,**k:pytest.fail('metadata/header violation hashed values'))
    with pytest.raises((ValueError,TypeError)):
        evaluation.load_joint_sealed(str(directory),problem,frozen,manifest)


def test_result_summary_or_array_forgery_fails_recomputation(prepared):
    root,problem,frozen,sealed,_,_=prepared
    result=evaluation.evaluate_frozen_joint(problem,frozen,sealed)
    result['payload']['metrics']['gravity']['sealed']['wrms']=0.
    destination=root/'false-summary';evaluation.write_joint_result(str(destination),result)
    with pytest.raises(ValueError,match='scientific metadata'):
        evaluation.validate_joint_result(str(destination),problem,frozen,sealed)
    result=evaluation.evaluate_frozen_joint(problem,frozen,sealed)
    result['arrays']['magnetic_sealed_predicted']=np.zeros_like(result['arrays']['magnetic_sealed_predicted'])
    destination=root/'false-prediction';evaluation.write_joint_result(str(destination),result)
    with pytest.raises(ValueError,match='physical replay'):
        evaluation.validate_joint_result(str(destination),problem,frozen,sealed)


def test_no_optimizer_claim_from_supplied_model(prepared):
    _,problem,frozen,sealed,_,_=prepared
    assert frozen['selection_sha256'] is None
    with pytest.raises(ValueError):
        evaluation.freeze_joint_model(problem,problem.start,frozen['weights'],selection_sha256='a'*64)
    # Hashes do not prove an externally imported calibration ledger or authorship.
    assert not evaluation.evaluate_frozen_joint(problem,frozen,sealed)['payload']['claims']['inverse_completed']


def test_exact_bound_kkt_no_epsilon_activation():
    lower=np.array([0.,0.,0.]);upper=np.ones(3);q=np.array([0.,1.,np.nextafter(0.,1.)])
    g=np.array([3.,-2.,4.])
    assert evaluation.projected_kkt(q,g,lower,upper)==4.
    assert evaluation.projected_kkt(q[:2],g[:2],lower[:2],upper[:2])==0.


def test_external_writer_guard_before_scans(tmp_path,monkeypatch):
    repository=tmp_path/'repo';repository.mkdir();(repository/'.git').mkdir()
    monkeypatch.setattr(np,'isfinite',lambda *a,**k:pytest.fail('repository writer scanned values'))
    with pytest.raises(ValueError,match='repository'):
        files.write_arrays(str(repository/'output'),'result.json','x',{}, {'q':np.zeros(2)})


def test_physical_units_and_actual_geometry_export(prepared):
    root,problem,frozen,_,_,_=prepared
    record=model_export.physical_model_record(problem,frozen)
    np.testing.assert_array_equal(record['arrays']['density_kg_m3'],frozen['q'][:problem.n]*problem.scales[:problem.n])
    np.testing.assert_array_equal(record['arrays']['susceptibility_si'],frozen['q'][problem.n:]*problem.scales[problem.n:])
    np.testing.assert_array_equal(record['arrays']['active_cell_bounds_m'],problem.geometry['active_cell_bounds_m'])
    assert record['payload']['density_unit']=='kg_m3' and record['payload']['susceptibility_unit']=='si'
    assert not record['payload']['inverse_execution_asserted_by_this_model']
    destination=root/'physical'
    model_export.write_physical_model(str(destination),problem,frozen)
    assert model_export.validate_physical_model(str(destination),problem,frozen)['physical_model_verified']
    forged=model_export.physical_model_record(problem,frozen);forged['arrays']['density_kg_m3']=np.zeros(problem.n)
    files.write_arrays(str(root/'forged-model'),'model.json','joint-survey-physical-model-file-1',forged['payload'],forged['arrays'])
    if np.any(frozen['q'][:problem.n]!=0):
        with pytest.raises(ValueError): model_export.validate_physical_model(str(root/'forged-model'),problem,frozen)
