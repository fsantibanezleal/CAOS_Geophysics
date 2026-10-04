"""Geometry-only partition controls before any sealed value or solver selection."""

from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
from time import monotonic

import numpy as np
import pytest
import choclo

import gravity_survey_l2 as survey
import gravity_l2 as l2


def request():
    # Test-owned specification helper; production cannot import a caller path.
    path = Path(__file__).resolve().parents[1] / 'data/test_gravity_survey_l2.py'
    spec = importlib.util.spec_from_file_location('_l2_authored_controls', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.planning_request()


def calibration_request():
    path = Path(__file__).resolve().parents[1] / 'data/test_gravity_survey_l2.py'
    spec = importlib.util.spec_from_file_location('_l2_selection_controls',path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.calibration_request()


def outer_request(result,values=None):
    rows = result['plan']['outer_rows']
    observed = {'rows':rows.copy(),'gz_up_mgal':np.zeros(len(rows)) if values is None else values,
                'acceleration_unit':'mGal','vertical_positive':'up'}
    observed['values_sha256'] = survey._digest(observed)
    noise = {'kind':'diagonal_sd','values':np.full(len(rows),.01),'unit':'mGal',
             'basis':'explicit_conditional_gaussian','citation':'Fixed authored conditional scale',
             'cross_partition_dependence':'declared_absent'}
    noise['values_sha256'] = survey._digest({key:noise[key] for key in ('kind','unit','values')}|{'rows':rows})
    return {'schema':'gravity-survey-l2-evaluation-request-1','frozen_calibration':result,
            'observations':observed,'noise':noise}


def test_exact_candidates_scores_failures_and_refit(monkeypatch):
    calls = []
    original = l2._solve_partition
    def observe(problem,prior,deadline=None):
        calls.append((problem['rows'].copy(),problem['beta_candidate'],prior['start_kg_m3'].copy()))
        return original(problem,prior,deadline)
    monkeypatch.setattr(l2,'_solve_partition',observe)
    req = calibration_request()
    result = l2.calibrate_gravity_l2(req)
    assert len(calls)==25 and result['selected_index']==7 and result['selection_status']=='selected'
    assert result['final_solve']['status']=='converged'
    assert all(c['eligible'] and c['score_q']==0. for c in result['candidates'])
    assert [c['beta_candidate'] for c in result['candidates']]==list(l2.BETA_CANDIDATES)
    for index,(rows,beta,start) in enumerate(calls):
        if index<24:
            np.testing.assert_array_equal(rows,req['plan']['folds'][index%3]['fit_rows'])
            assert beta==l2.BETA_CANDIDATES[index//3]
        else:
            np.testing.assert_array_equal(rows,req['plan']['development_rows'])
            assert beta==1000.
        np.testing.assert_array_equal(start,req['prior']['start_kg_m3'])
        assert not set(rows)&set(req['plan']['outer_rows'])
    assert not result['predictions']['gz_up_mgal'].flags.writeable
    assert result['scope']['full_M02_accepted'] is result['scope']['field_eligible'] is False
    assert result['provenance']['runtime_epoch']==l2.RUNTIME_EPOCH
    assert survey._digest({k:v for k,v in result.items() if k!='result_sha256'})==result['result_sha256']


def test_sealed_outer_and_inner_value_leakage(monkeypatch):
    result = l2.calibrate_gravity_l2(calibration_request())
    frozen_sha = result['result_sha256']
    def deny(*args,**kwargs): raise AssertionError('outer evaluation ran optimizer/refit')
    monkeypatch.setattr(l2,'_solve_partition',deny)
    monkeypatch.setattr(l2,'calibrate_gravity_l2',deny)
    outer = outer_request(result)
    evaluated = l2.evaluate_gravity_l2(outer)
    assert evaluated['wrms']==0. and evaluated['field_truth'] is evaluated['model_accuracy'] is None
    outer['observations']['gz_up_mgal'][:] = .03
    outer['observations']['values_sha256'] = survey._digest({k:v for k,v in outer['observations'].items() if k!='values_sha256'})
    other = l2.evaluate_gravity_l2(outer)
    np.testing.assert_array_equal(evaluated['predicted_mgal'],other['predicted_mgal'])
    assert other['wrms']==3. and other['prediction_quality']=='poor_under_declared_noise'
    assert result['result_sha256']==frozen_sha and result['selected_index']==7
    np.testing.assert_array_equal(other['residual_observed_minus_predicted_mgal'],outer['observations']['gz_up_mgal']-other['predicted_mgal'])


@pytest.mark.parametrize('fault',['one_fold','all_but_one','final'])
def test_selection_retains_failures_without_candidate_substitution(monkeypatch,fault):
    original,calls = l2._solve_partition,[]
    def failed(problem,prior,deadline=None):
        solved = original(problem,prior,deadline)
        index = len(calls)
        calls.append(problem['beta_candidate'])
        should_fail = (index==0 if fault=='one_fold' else index<21 if fault=='all_but_one' else index==24)
        if should_fail:
            solved.update(status='nonconverged',reason='line_search_failed',failed_trial={'iteration':solved['iterations'],'reason':'line_search_failed'})
        return solved
    monkeypatch.setattr(l2,'_solve_partition',failed)
    result = l2.calibrate_gravity_l2(calibration_request())
    assert len(result['candidates'])==8 and all(len(c['folds'])==3 for c in result['candidates'])
    if fault=='all_but_one':
        assert len(calls)==24 and result['selected_index'] is result['final_solve'] is None
        assert result['selection_status']=='insufficient_candidates'
    else:
        assert len(calls)==25 and result['selected_index']==7
        if fault=='one_fold':
            candidate = result['candidates'][0]
            assert candidate['score_q'] is None and not candidate['eligible']
            assert candidate['reason']=='fold_failure' and candidate['folds'][0]['validation_phi_d'] is None
            assert result['selection_status']=='selected'
        else:
            assert result['selection_status']=='final_nonconverged' and result['final_solve']['reason']=='line_search_failed'
            with pytest.raises(ValueError,match='nonconverged'): l2.evaluate_gravity_l2(outer_request(result))


def test_whole_workflow_expiry_does_not_launch_additional_fits(monkeypatch):
    req = calibration_request()
    clock_calls = []
    def clock():
        clock_calls.append(None)
        return 0. if len(clock_calls)==1 else 1801.
    def deny(*args,**kwargs): raise AssertionError('expired workflow launched native optimizer')
    monkeypatch.setattr(l2,'monotonic',clock)
    monkeypatch.setattr(l2,'_solve_partition',deny)
    result = l2.calibrate_gravity_l2(req)
    assert result['selection_status']=='insufficient_candidates' and result['final_solve'] is None
    for candidate in result['candidates']:
        assert not candidate['eligible'] and candidate['score_q'] is None
        for fold in candidate['folds']:
            solved = fold['solve']
            assert solved['reason']=='wall_cap' and solved['model_kg_m3'] is solved['phi_d'] is None
            assert solved['trace']['models_kg_m3'].shape==(0,48)


@pytest.mark.parametrize('fault',['prediction','score','final_prediction','late_prediction','late_score','late_final'])
def test_real_workflow_prediction_and_score_barriers_preserve_unavailable(monkeypatch,fault):
    clock=[monotonic()]
    monkeypatch.setattr(l2,'monotonic',lambda:clock[0])
    calls=[]
    native_prediction,native_score=l2._physical_prediction,l2._marginal_metrics
    def predict(req,model):
        value=native_prediction(req,model)
        calls.append('prediction')
        is_final=len(calls)==25
        if fault=='prediction' and len(calls)==1: raise RuntimeError('retained injected prediction failure')
        if fault=='final_prediction' and is_final: raise RuntimeError('retained final prediction failure')
        if fault=='late_prediction' or (fault=='late_final' and is_final): clock[0]+=1801.
        return value
    score_calls=[]
    def score(*args):
        value=native_score(*args)
        score_calls.append('score')
        if fault=='score' and len(score_calls)==1: raise RuntimeError('retained injected scoring failure')
        if fault=='late_score': clock[0]+=1801.
        return value
    monkeypatch.setattr(l2,'_physical_prediction',predict)
    monkeypatch.setattr(l2,'_marginal_metrics',score)
    result=l2.calibrate_gravity_l2(calibration_request())
    assert len(result['candidates'])==8 and all(len(c['folds'])==3 for c in result['candidates'])
    if fault in ('prediction','score'):
        first=result['candidates'][0]
        assert first['eligible'] is False and first['score_q'] is None
        assert first['reason']=='invalid_score'
        assert first['folds'][0]['solve']['status']=='converged'
        assert first['folds'][0]['validation_phi_d'] is None
        assert result['selection_status']=='selected' and result['selected_index']==7
    elif fault in ('late_prediction','late_score'):
        assert result['selection_status']=='insufficient_candidates'
        assert result['selected_index'] is result['final_solve'] is None
        assert all(c['eligible'] is False and c['score_q'] is None for c in result['candidates'])
        assert result['candidates'][0]['folds'][0]['validation_phi_d'] is None
    else:
        assert result['selected_index']==7 and result['selection_status']=='final_nonconverged'
        assert result['predictions']['gz_up_mgal'] is None
        final=result['final_solve']
        assert final['status']==('failed' if fault=='final_prediction' else 'nonconverged')
        assert final['reason']==('engine_error' if fault=='final_prediction' else 'wall_cap')
        assert final['model_kg_m3'] is not None
        assert final['failed_trial']=={'iteration':final['iterations'],'reason':final['reason']}
        with pytest.raises(ValueError,match='nonconverged'): l2.evaluate_gravity_l2(outer_request(result))
    assert survey._digest({k:v for k,v in result.items() if k!='result_sha256'})==result['result_sha256']


@pytest.mark.parametrize('fault',['extra','array','hash','model','source','epoch','status','prediction','units'])
def test_frozen_result_tamper_and_metadata_before_work(monkeypatch,fault):
    result = l2.calibrate_gravity_l2(calibration_request())
    altered = deepcopy(result)
    req = outer_request(altered)
    if fault=='extra': altered['future']=True
    if fault=='array': altered['final_solve']['trace']['models_kg_m3']=np.zeros((202,48))
    if fault=='hash': altered['result_sha256']='0'*64
    if fault=='model': altered['final_solve']['model_kg_m3'][0]=1.
    if fault=='source': altered['provenance']['forward_source_sha256']='0'*64
    if fault=='epoch': altered['provenance']['runtime_epoch']='m02-survey-l2-cpu-3'
    if fault=='status': altered['selection_status']='final_nonconverged'
    if fault=='prediction': altered['predictions']['gz_up_mgal'][0]=1.
    if fault=='units': req['observations']['acceleration_unit']='microGal'
    def deny(*args,**kwargs): raise AssertionError('tampered frozen record reached physics/optimization')
    monkeypatch.setattr(l2.forward,'forward_gravity',deny)
    monkeypatch.setattr(l2,'_solve_partition',deny)
    with pytest.raises((ValueError,TypeError)): l2.evaluate_gravity_l2(req)


def independent_line_roles(req):
    ordered = []
    for j in range(12):
        ids = tuple(sorted(f"station:{i}:{j}" for i in range(12)))
        encoded = json.dumps({"seed": 104729, "station_ids": ids}, sort_keys=True,
                             separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
        ordered.append((hashlib.sha256(encoded).hexdigest(), ids, j))
    order = [x[2] for x in sorted(ordered)]
    return order[:3], [order[3 + fold::3] for fold in range(3)]


def test_frozen_geometry_blocks_groups_buffers():
    req = request()
    plan = survey.plan_gravity_l2(req)
    outer, fold_lines = independent_line_roles(req)
    assert set(plan["outer_rows"] // 12) == set(outer)
    assert len(plan["outer_rows"]) == 36 and len(plan["development_rows"]) == 108
    assert len(plan["embargo_rows"]) == 0
    for fold in plan["folds"]:
        assert set(fold["validation_rows"] // 12) == set(fold_lines[fold["fold"]])
        assert len(fold["fit_rows"]) == 72 and len(fold["validation_rows"]) == 36
        assert not set(fold["fit_rows"]) & set(fold["validation_rows"])
        assert not set(fold["fit_rows"]) & set(plan["outer_rows"])
    perm = np.arange(143, -1, -1)
    reordered = deepcopy(req)
    for key, value in req["stations"].items():
        reordered["stations"][key] = value[perm] if type(value) is np.ndarray else tuple(value[i] for i in perm)
    reordered["background_mgal"] = req["background_mgal"][perm]
    other = survey.plan_gravity_l2(reordered)
    np.testing.assert_array_equal(np.sort(perm[other["outer_rows"]]), plan["outer_rows"])
    for a, b in zip(plan["folds"], other["folds"]):
        np.testing.assert_array_equal(np.sort(perm[b["fit_rows"]]), a["fit_rows"])


@pytest.mark.parametrize("kind", ["single_group", "buffer", "collinear", "huge_block_index", "too_few_rows"])
def test_partition_failures_no_retry_or_fallback(kind):
    req = request()
    if kind == "single_group": req["stations"]["partition_group_ids"] = ("campaign",) * 144
    if kind == "buffer": req["split"]["buffer_m"] = 10000.
    if kind == "collinear": req["stations"]["receivers_m"][:, 1] = 0.
    if kind == "huge_block_index": req["split"]["block_size_m"][:] = 1e-300
    if kind == "too_few_rows":
        req["stations"]["excluded"][::2] = True
        req["stations"]["exclusion_reasons"] = tuple("gap" if i % 2 == 0 else "" for i in range(144))
    with pytest.raises(ValueError): survey.plan_gravity_l2(req)


_LOCKED_PRISMS = (
    (((-85.,45.,-75.,35.,-135.,-45.),450.),),
    (((-135.,-25.,-95.,65.,-155.,-55.),400.),((35.,135.,-45.,105.,-205.,-95.),-300.)),
    (((-155.,165.,-145.,145.,-220.,-60.),125.),),
    (((-175.,185.,-165.,155.,-285.,-185.),300.),),
    (),
    (((-125.,-15.,-125.,-15.,-105.,-35.),250.),((15.,125.,15.,125.,-275.,-165.),500.)),
)


def locked_request(family,condition):
    """Literal frozen24spec; no seed/specimen replacement after measurements."""
    req = calibration_request()
    planning = request()
    points = planning['stations']['receivers_m']
    physical = np.array([sum(choclo.prism.gravity_u(*point,*box,density)*1e5 for box,density in _LOCKED_PRISMS[family]) for point in points])
    generator = np.random.Generator(np.random.PCG64(700001+100*family+condition))
    covariance = None
    if condition==1:
        distance = np.linalg.norm(points[:,None,:2]-points[None,:,:2],axis=2)
        covariance = .005**2*(.8*np.eye(144)+.2*np.exp(-distance/120.))
        errors = np.linalg.cholesky(covariance)@generator.standard_normal(144)
    else:
        errors = .005*generator.standard_normal(144)
    # Draw all noise before masks. c3 deliberately leaves its nuisance unmodelled.
    values = physical+errors
    if condition==3: values += .00002*points[:,0]+np.where(np.arange(144)%29==0,.05,0.)
    if condition==2:
        excluded = np.arange(144)%7==0
        planning['stations']['excluded'] = excluded
        planning['stations']['exclusion_reasons'] = tuple('control_gap' if v else '' for v in excluded)
    planning['source'].update(source_id=f'locked_l2:{family}:{condition}',raw_bytes=values.nbytes,
        raw_sha256=hashlib.sha256(values.astype('<f8').tobytes()).hexdigest(),
        processing_sha256=survey._digest({'source_prisms':_LOCKED_PRISMS[family],'family':family,'condition':condition,
            'seed':700001+100*family+condition,'generator':'numpy-2.2.6-PCG64','units':'mGal/up'}),
        normalization_sha256=survey._digest(values),citation='Frozen independent continuous Choclo prism plus declared conditional noise control')
    plan = survey.plan_gravity_l2(planning)
    rows = plan['development_rows']
    req['plan'] = plan
    req['observations']['rows'],req['observations']['gz_up_mgal'] = rows.copy(),values[rows].copy()
    req['observations']['values_sha256'] = survey._digest({k:v for k,v in req['observations'].items() if k!='values_sha256'})
    req['noise'].update(kind='full_covariance' if covariance is not None else 'diagonal_sd',
        values=covariance[np.ix_(rows,rows)] if covariance is not None else np.full(len(rows),.005),
        unit='mGal^2' if covariance is not None else 'mGal',
        cross_partition_dependence='possible_not_removed' if covariance is not None else 'declared_absent')
    req['noise']['values_sha256'] = survey._digest({k:req['noise'][k] for k in ('kind','unit','values')}|{'rows':rows})
    req['prior']['lengths_m'][:] = 100.
    req['prior']['geometry_sha256'] = survey._digest(plan['geometry'])
    return req,values,covariance


@pytest.mark.parametrize('family',range(6))
@pytest.mark.parametrize('condition',range(4))
def test_complete_locked_l2_control_matrix(family,condition,record_property):
    req,values,covariance = locked_request(family,condition)
    started = monotonic()
    result = l2.calibrate_gravity_l2(req)
    frozen_sha = result['result_sha256']
    measured = {'family':family,'condition':condition,'seed':700001+100*family+condition,
        'selection_status':result['selection_status'],'selected_index':result['selected_index'],
        'plan_sha256':result['plan']['plan_sha256'],'input_sha256':survey._digest(req),
        'calibration_sha256':frozen_sha,'runtime_epoch':l2.RUNTIME_EPOCH,'outer_wrms':None,'model_rmse_ratio':None,
        'candidates':tuple({'index':c['index'],'beta':c['beta_candidate'],'eligible':c['eligible'],'score_q':c['score_q'],
            'folds':tuple({'status':f['solve']['status'],'reason':f['solve']['reason'],
                'iterations':f['solve']['iterations'],'validation_phi_d':f['validation_phi_d'],
                'model_sha256':survey._digest(f['solve']['model_kg_m3'])} for f in c['folds'])} for c in result['candidates'])}
    if result['selection_status']=='selected':
        rows = result['plan']['outer_rows']
        outer = outer_request(result,values[rows].copy())
        if covariance is not None:
            outer['noise'].update(kind='full_covariance',values=covariance[np.ix_(rows,rows)],unit='mGal^2',cross_partition_dependence='possible_not_removed')
        else: outer['noise']['values'][:] = .005
        outer['noise']['values_sha256'] = survey._digest({k:outer['noise'][k] for k in ('kind','unit','values')}|{'rows':rows})
        evaluated = l2.evaluate_gravity_l2(outer)
        measured['outer_wrms'],measured['evaluation_sha256'] = evaluated['wrms'],evaluated['result_sha256']
        assert result['result_sha256']==frozen_sha
        # Truth is built ONLY after selected model freeze/evaluation, never supplied.
        bounds = np.array([[x,x+100.,y,y+100.,z,z+100.] for z in (-300.,-200.,-100.)
                           for y in (-200.,-100.,0.,100.) for x in (-200.,-100.,0.,100.)])
        truth = np.zeros(48)
        for box,density in _LOCKED_PRISMS[family]:
            lengths = np.maximum(0.,np.minimum(bounds[:,1::2],box[1::2])-np.maximum(bounds[:,::2],box[::2]))
            truth += density*np.prod(lengths,axis=1)/100.**3
        model = result['final_solve']['model_kg_m3']
        reference_error = float(np.linalg.norm(truth))
        measured['model_rmse_ratio'] = float(np.linalg.norm(model-truth)/reference_error) if reference_error>0 else None
        physical = np.array([sum(choclo.prism.gravity_u(*point,*box,float(density))*1e5 for box,density in zip(bounds,model))
                             for point in req['plan']['request']['stations']['receivers_m']])
        np.testing.assert_allclose(result['predictions']['gz_up_mgal'],physical,rtol=1e-7,atol=1e-10)
    measured['wall_seconds'] = monotonic()-started
    record_property('locked_l2_outcome',json.dumps(measured,sort_keys=True,allow_nan=False))
    assert len(result['candidates'])==8 and all(len(c['folds'])==3 for c in result['candidates'])
    if family in (0,1) and condition in (0,1):
        assert result['selection_status']=='selected',measured
        assert measured['outer_wrms']<=2.,measured
        assert measured['model_rmse_ratio']<1.,measured
