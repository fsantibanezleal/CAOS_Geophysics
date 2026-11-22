"""Actual26-fit physical calibration, frozen selection, and full replay controls."""
from copy import deepcopy

import numpy as np
import pytest

import joint_survey_cases as cases
import joint_survey_compiled as compiled
import joint_survey_optimizer as optimizer
import joint_survey_calibration_io as transport
import joint_survey_evaluation as evaluation
import joint_survey_files as files
import joint_survey_resources as resources
import joint_survey_workflow as workflow
from joint_survey_serialization import write_joint_development


@pytest.fixture(scope='module')
def calibrated(tmp_path_factory):
    root=tmp_path_factory.mktemp('actual-calibration')
    case=cases.make_joint_control(0)
    problem=compiled.compile_joint_development({'schema':'joint-survey-compile-request-1',
        'survey_request':case['survey_request'],'development':case['development']})
    scratch=root/'scratch';scratch.mkdir()
    with resources.JointResourceBudget(str(scratch)) as budget:
        ledger=optimizer.calibrate_joint_development(problem,budget)
        transport.verify_joint_calibration(ledger,problem,budget)
    return root,case,problem,ledger,scratch


def test_all_actual_fits_and_stationary_separate_baselines(calibrated):
    _,_,problem,ledger,_=calibrated
    assert ledger['status']=='selected',ledger['reason']
    assert len(ledger['candidates'])==26
    assert set(ledger['selected_baselines'])=={'gravity','magnetic'}
    for c in ledger['candidates']:
        assert c['result']['iterations']<=250
        if c['result']['status']=='converged': assert c['stationarity_verified']
        assert c['physical_trace'].shape[1]==(problem.n if c['modality'] else 2*problem.n)
        assert c['terms_trace'].shape[1]==5
        if c['modality']:
            other='magnetic' if c['modality']=='gravity' else 'gravity'
            assert c['validation_wrms'].keys()=={c['modality']}
            assert np.all(c['terms_trace'][:,1 if other=='magnetic' else 0]==0.)
    assert not ledger['selection']['refit'] and not ledger['selection']['lambda0_refitted']
    if ledger['reason']=='no_validated_coupling_benefit': assert ledger['selection']['weights']['coupling']==0.


def test_calibration_exclusive_export_and_frozen_replay(calibrated):
    root,_,problem,ledger,scratch=calibrated
    destination=root/'ledger'
    with resources.JointResourceBudget(str(scratch)) as budget:
        transport.write_joint_calibration(str(destination),ledger,problem,budget)
        loaded=transport.load_joint_calibration(str(destination),problem,budget)
        assert loaded['calibration_sha256']==ledger['calibration_sha256']
        selected=loaded['selection']
        frozen=evaluation.freeze_joint_model(problem,selected['q'],selected['weights'],origin='optimized_selection',
            selection_sha256=loaded['calibration_sha256'])
        assert transport.verify_joint_calibration(loaded,problem,budget,frozen=frozen)['inverse_completed']
        with pytest.raises(FileExistsError): transport.write_joint_calibration(str(destination),ledger,problem,budget)


@pytest.mark.parametrize('fault',['q','stationarity','selection','beta','precision','hash','trace'])
def test_actual_replay_rejects_forged_pass(calibrated,fault):
    _,_,problem,ledger,scratch=calibrated;ledger=deepcopy(ledger)
    if fault=='q': ledger['candidates'][0]['result']['q'][0]+=.01
    elif fault=='stationarity': ledger['candidates'][0]['stationarity_verified']=not ledger['candidates'][0]['stationarity_verified']
    elif fault=='selection': ledger['selection']['q'][0]+=.01
    elif fault=='beta': ledger['candidates'][0]['weights']['beta_gravity']=.01
    elif fault=='precision': ledger['candidates'][0]['identity']['runtime_epoch']='relaxed'
    elif fault=='hash': ledger['calibration_sha256']='b'*64
    else: ledger['candidates'][0]['terms_trace'][0,0]+=.01
    with resources.JointResourceBudget(str(scratch)) as budget,pytest.raises((ValueError,RuntimeError)):
        transport.verify_joint_calibration(ledger,problem,budget)


def test_full_cli_evaluate_and_validate_real_files(calibrated,capsys,monkeypatch):
    root,case,problem,_,_=calibrated
    data=root/'data';data.mkdir();scratch=root/'cli-scratch';scratch.mkdir()
    sealed={}
    for m in evaluation.MODALITIES:
        for source,label in (('rows','rows'),('observed','observed'),('noise_values','noise')):
            sealed[m+'_'+label]=case['sealed'][m][source]
    manifest=evaluation.write_joint_sealed(str(data/'sealed'),problem.plan,sealed)
    write_joint_development(str(data/'development'),{'schema':'joint-survey-write-request-1','survey_request':case['survey_request'],
        'development':case['development'],'sealed_manifest':manifest,'originals':None})
    frozen=evaluation.freeze_joint_model(problem,problem.start,{'beta_gravity':.001,'beta_magnetic':.001,'coupling':0.})
    evaluation.write_frozen_model(str(data/'supplied'),frozen,problem)
    args=['--data-root',str(data),'--development',str(data/'development'),'--sealed',str(data/'sealed'),
          '--output',str(data/'evaluation'),'--scratch-root',str(scratch)]
    assert workflow.main(['evaluate',*args,'--frozen',str(data/'supplied')])==0
    assert '"inverse_completed": false' in capsys.readouterr().out
    assert workflow.main(['validate',*args])==0
    assert '"validated": true' in capsys.readouterr().out
    assert workflow.main(['evaluate',*args,'--frozen',str(data/'supplied')])==1
    assert not (data/'evaluation'/'calibration').exists()
    solved_args=args.copy();solved_args[solved_args.index(str(data/'evaluation'))]=str(data/'solved')
    original=evaluation.load_joint_sealed
    reads=[]
    def after_freeze(*a,**k):
        assert (data/'solved'/'frozen'/'frozen.json').is_file()
        assert (data/'solved'/'calibration'/'calibration.json').is_file()
        reads.append(True)
        return original(*a,**k)
    monkeypatch.setattr(evaluation,'load_joint_sealed',after_freeze)
    assert workflow.main(['solve',*solved_args])==0
    capsys.readouterr()
    assert workflow.main(['validate',*solved_args])==0
    assert '"inverse_completed": true' in capsys.readouterr().out
    assert len(reads)==2
    with pytest.raises(SystemExit): workflow.main(['evaluate','--dev','untrusted-abbreviation'])


def test_calibration_api_cannot_admit_sealed_or_truth(calibrated):
    _,case,problem,_,scratch=calibrated
    with resources.JointResourceBudget(str(scratch)) as budget:
        with pytest.raises(TypeError): optimizer.calibrate_joint_development(problem,budget,sealed=case['sealed'])
        with pytest.raises(TypeError): optimizer.calibrate_joint_development(problem,budget,truth=case['truth'])


@pytest.mark.parametrize('phase',['first_actual_fit','durable_freeze'])
def test_adverse_abort_retains_genuine_states_without_reading_sealed(calibrated,tmp_path,monkeypatch,phase):
    import json
    import time
    _,case,problem,_,_=calibrated
    data=tmp_path/'data';data.mkdir();scratch=tmp_path/'scratch';scratch.mkdir()
    sealed={m+'_'+label:case['sealed'][m][source] for m in evaluation.MODALITIES
        for source,label in (('rows','rows'),('observed','observed'),('noise_values','noise'))}
    manifest=evaluation.write_joint_sealed(str(data/'sealed'),problem.plan,sealed)
    write_joint_development(str(data/'development'),{'schema':'joint-survey-write-request-1',
        'survey_request':case['survey_request'],'development':case['development'],'sealed_manifest':manifest,'originals':None})
    monkeypatch.setattr(evaluation,'load_joint_sealed',lambda *a,**k:pytest.fail('aborted workflow read sealed values'))
    actual=[]
    if phase=='first_actual_fit':
        original=optimizer.solver.solve_bounded_nonlinear
        def expire_after_actual(*a,**k):
            result=original(*a,**k)
            actual.append(result)
            a[0].budget.deadline=time.monotonic()-1.
            return result
        monkeypatch.setattr(optimizer.solver,'solve_bounded_nonlinear',expire_after_actual)
    else:
        original=transport.verify_joint_calibration
        def expire_after_freeze(ledger,problem,budget,**kwargs):
            if kwargs.get('frozen') is not None: budget.deadline=time.monotonic()-1.
            return original(ledger,problem,budget,**kwargs)
        monkeypatch.setattr(transport,'verify_joint_calibration',expire_after_freeze)
    status=workflow.solve_joint_workflow(data_root=str(data),development=str(data/'development'),sealed=str(data/'sealed'),
        output=str(data/'failed'),scratch=str(scratch))
    assert status['status']=='failed' and status['reason']=='workflow_deadline'
    assert not status['inverse_completed'] and not status['resources']['complete_workflow_resource_pass']
    assert not (data/'failed'/'result').exists()
    document=json.loads((data/'failed'/'aborted'/'aborted.json').read_bytes())
    payload=document['payload']
    assert not payload['scientific_replay_completed'] and not payload['sealed_values_read_started']
    assert payload['frozen_selection_created']==(phase=='durable_freeze')
    if phase=='first_actual_fit':
        assert actual[0]['iterations']>0 and len(payload['verified_candidates'])==0
        saved=np.load(data/'failed'/'aborted'/'last_models_q.npy',allow_pickle=False)
        assert np.array_equal(saved,actual[0]['trace']['models_q'])
        assert payload['last_attempt']['result']['status']==actual[0]['status']
    else:
        assert len(payload['verified_candidates'])==26 and payload['last_attempt'] is None
    with pytest.raises((OSError,ValueError)): workflow.validate_joint_workflow(data_root=str(data),
        development=str(data/'development'),sealed=str(data/'sealed'),output=str(data/'failed'),scratch=str(scratch))


def test_real_cli_entrypoint_evaluation_in_fresh_process(calibrated,tmp_path):
    import json
    import os
    from pathlib import Path
    import subprocess
    import sys
    data=calibrated[0]/'data';scratch=tmp_path/'scratch';scratch.mkdir()
    root=Path(__file__).resolve().parents[2]
    env=dict(os.environ,PYTHONPATH=str(Path(np.__file__).parents[1]),PYTHONDONTWRITEBYTECODE='1')
    args=['--data-root',str(data),'--development',str(data/'development'),'--sealed',str(data/'sealed'),
        '--output',str(data/'subprocess-evaluation'),'--scratch-root',str(scratch)]
    for command,extra in (('evaluate',['--frozen',str(data/'supplied')]),('validate',[])):
        process=subprocess.run([sys.executable,'-B','-S',str(root/'scripts/run_joint_survey.py'),command,*args,*extra],
            env=env,cwd=str(tmp_path),capture_output=True,text=True,timeout=1800)
        assert process.returncode==0,process.stdout+process.stderr
        status=json.loads(process.stdout.strip().splitlines()[-1])
        assert not status['inverse_completed']


def test_metadata_cap_precedes_whole_tree_or_array_scan(monkeypatch):
    monkeypatch.setattr(np,'isfinite',lambda *a,**k:pytest.fail('metadata guard scanned array'))
    with pytest.raises(ValueError): files.metadata_budget({'a':tuple({} for _ in range(262145))})
