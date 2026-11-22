"""Reusable actual physics against existing public and independent objectives."""
from copy import deepcopy

import numpy as np
import pytest

import gravity_forward
import magnetic_forward
import joint_survey_compiled as compiled
import joint_survey_objective as objective
from test_joint_survey_objective import body,independent_R,rehash


def compile_request(value):
    return {'schema':'joint-survey-compile-request-1','survey_request':value['survey_request'],
            'development':value['development']}


@pytest.mark.parametrize('covariance',[False,True])
def test_actual_objective_equivalence(covariance):
    value=body(covariance);problem=compiled.compile_joint_development(compile_request(value))
    q=np.r_[value['models']['density_kg_m3'],value['models']['susceptibility_si']]/problem.scales
    direction=value['direction_physical']/problem.scales
    result=problem.state(q,value['weights']);old=objective.evaluate_joint_objective(value)
    independent=independent_R(value['survey_request'])
    # Different valid ordering of face rows, same exact physical quadratic form.
    np.testing.assert_allclose((problem.R.T@problem.R).toarray(),independent.T@independent,atol=1e-14,rtol=1e-14)
    np.testing.assert_allclose(result['objective'],old['objective'],atol=1e-10,rtol=1e-9)
    np.testing.assert_allclose(result['gradient_normalized'],old['gradient_physical']*problem.scales,atol=1e-10,rtol=1e-9)
    for exact,key in ((True,'exact_hessian_vector_physical'),(False,'approx_hessian_vector_physical')):
        np.testing.assert_allclose(problem.hessian(q,value['weights'],exact=exact)@direction,
            old[key]*problem.scales,atol=1e-10,rtol=1e-9)
    predicted=problem.predict(q)
    for m in ('gravity','magnetic'):
        np.testing.assert_allclose(predicted[m][old['predictions'][m]['rows']],old['predictions'][m]['predicted'],atol=1e-8,rtol=0.)


def test_kernel_once(monkeypatch):
    counters={'gravity':0,'magnetic':0}
    for module,name,modality in ((gravity_forward,'forward_gravity','gravity'),(magnetic_forward,'forward_magnetic','magnetic')):
        actual=getattr(module,name)
        def wrapper(req,actual=actual,modality=modality):
            counters[modality]+=1
            return actual(req)
        monkeypatch.setattr(module,name,wrapper)
    value=body();problem=compiled.compile_joint_development(compile_request(value))
    for _ in range(3): problem.state(problem.start,value['weights'])
    assert counters=={'gravity':1,'magnetic':1}


def test_no_sealed_and_train_only():
    value=body();problem=compiled.compile_joint_development(compile_request(value));other=deepcopy(value)
    for m in ('gravity','magnetic'): other['development'][m]['observed'][2:]+=100.
    rehash(other);mutated=compiled.compile_joint_development(compile_request(other))
    a=problem.state(problem.start,value['weights']);b=mutated.state(mutated.start,value['weights'])
    assert a['objective']==b['objective']
    np.testing.assert_array_equal(a['gradient_normalized'],b['gradient_normalized'])
    for key in ('sealed','truth','callback'):
        req=compile_request(value);req[key]={}
        with pytest.raises((TypeError,ValueError)): compiled.compile_joint_development(req)
    other=deepcopy(value);other['development']['gravity']['observed'][0]+=.1;rehash(other)
    altered=compiled.compile_joint_development(compile_request(other))
    assert altered.state(altered.start,value['weights'])['objective']!=a['objective']


@pytest.mark.parametrize('change',['weight','bound','nonfinite','dtype'])
def test_native_state_rejection(change):
    value=body();problem=compiled.compile_joint_development(compile_request(value))
    q=problem.start.copy();weights=dict(value['weights'])
    if change=='weight': weights['coupling']=.02
    elif change=='bound': q[0]=problem.upper[0]+1.
    elif change=='nonfinite': q[0]=np.nan
    else: q=q.astype(np.float32)
    with pytest.raises((TypeError,ValueError)): problem.state(q,weights)
