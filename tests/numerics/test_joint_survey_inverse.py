"""Actual repeated calibration, bound paths and unaltered strict ledger controls."""
from copy import deepcopy

import numpy as np
import pytest

import joint_survey_compiled as compiled
import joint_survey_evaluation as evaluation
import joint_survey_plan as planner
import joint_survey_optimizer as optimizer
import joint_survey_resources as resources
import joint_survey_calibration_io as transport
from test_joint_survey_optimizer import calibrated as calibrated


def test_sealed_selection_and_changed_development_actual_fits(calibrated):
    _,case,problem,original,scratch=calibrated
    case=deepcopy(case)
    for modality in evaluation.MODALITIES:
        case['sealed'][modality]['observed']+=1000.
    case['truth']['source_density_kg_m3']*=10.
    case['truth']['source_susceptibility_si']*=.5
    unchanged=compiled.compile_joint_development({'schema':'joint-survey-compile-request-1',
        'survey_request':case['survey_request'],'development':case['development']})
    with resources.JointResourceBudget(str(scratch)) as budget:
        repeated=optimizer.calibrate_joint_development(unchanged,budget)
        transport.verify_joint_calibration(repeated,unchanged,budget)
    assert repeated['calibration_sha256']==original['calibration_sha256']
    assert planner._digest(repeated['selection'])==planner._digest(original['selection'])
    # Training changes are properly rehashed supplied measurements, not a changed
    # objective policy, tolerance, sealed input or optimizer argument.
    development=case['development'];d=development['gravity'];d['observed'][0]+=.1
    d['observations_sha256']=planner._digest({'rows':d['rows'],'observed':d['observed'],'unit':'mGal',
        'plan_sha256':problem.plan['plan_sha256']})
    changed=compiled.compile_joint_development({'schema':'joint-survey-compile-request-1',
        'survey_request':case['survey_request'],'development':development})
    with resources.JointResourceBudget(str(scratch)) as budget:
        fitted=optimizer.calibrate_joint_development(changed,budget)
        transport.verify_joint_calibration(fitted,changed,budget)
    assert fitted['development_sha256']!=original['development_sha256']
    assert fitted['calibration_sha256']!=original['calibration_sha256']
    assert not np.array_equal(fitted['candidates'][0]['result']['q'],original['candidates'][0]['result']['q'])


@pytest.mark.parametrize('fault',['active','binding','branch','alpha','negative_cg','fake_unused_cg','failed_trial','reason'])
def test_optimizer_controls_reject_forged_trace(calibrated,fault):
    _,_,problem,original,scratch=calibrated
    ledger=deepcopy(original);record=ledger['candidates'][0];trace=record['result']['trace']
    if fault=='active': trace['active_counts'][0]+=1
    elif fault=='binding': trace['binding_counts'][0]+=1
    elif fault=='branch': trace['branches'][0]=1-trace['branches'][0]
    elif fault=='alpha': trace['line_search_alphas'][0]*=.5
    elif fault=='negative_cg': trace['cg_counts'][0]=-1
    elif fault=='fake_unused_cg':
        record=next(c for c in ledger['candidates'] if np.any(~c['result']['trace']['cg_residuals_available']))
        trace=record['result']['trace'];index=np.flatnonzero(~trace['cg_residuals_available'])[0]
        trace['cg_abs_residuals'][index]=1.
    elif fault=='failed_trial': record['result']['failed_trial']['iteration']+=1
    else: record['result']['reason']='invented'
    with resources.JointResourceBudget(str(scratch)) as budget,pytest.raises(ValueError):
        transport.verify_joint_calibration(ledger,problem,budget)


@pytest.mark.parametrize('start_mode',['lower','upper','mixed','interior'])
def test_actual_physical_bound_paths(calibrated,start_mode):
    _,_,problem,ledger,scratch=calibrated
    allocation=optimizer.allocation_plan(problem);inventory=optimizer.reviewed_source_inventory()
    binding=optimizer.solver.NonlinearBinding(**ledger['optimizer_binding'])
    q=problem.lower.copy() if start_mode=='lower' else problem.upper.copy() if start_mode=='upper' else (
        np.where(np.arange(2*problem.n)%2,problem.lower,problem.upper) if start_mode=='mixed' else problem.start.copy())
    weights={'beta_gravity':1.,'beta_magnetic':1.,'coupling':1.}
    with resources.JointResourceBudget(str(scratch)) as budget:
        record=optimizer._candidate(problem,weights,q,16,'submitted',inventory,allocation,budget,binding)
    states=record['result']['trace']['models_q']
    assert np.array_equal(states[0],q)
    assert np.all(states>=problem.lower) and np.all(states<=problem.upper)
    assert record['stationarity_verified']==(record['result']['status']=='converged')
    assert np.all(record['result']['trace']['armijo_margins']<=0.)
    assert record['result']['iterations']<=250
