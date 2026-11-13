"""Actual original native fits, independent precision references, no fallback."""
import os
from pathlib import Path
import sys

import numpy as np
import pytest
from scipy import sparse

# Explicit test dependency configuration only. Product has no user import hook,
# machine path, private helper dependency or dependency-source copy.
dependency=os.environ.get('GEOPHYSICS_M11_PUBLIC_DEPENDENCY')
if dependency: sys.path.append(str(Path(dependency)/'data-pipeline'))

import joint_survey_cases as cases
import joint_survey_compiled as compiled
import joint_survey_conditioned as conditioned
import joint_survey_optimizer as original
import joint_survey_resources as resources
from test_joint_survey_cases import independent_face_baseline,independent_problem,exact_kkt
from test_joint_survey_objective import kernels


def problem_for(index):
    case=cases.make_joint_control(index)
    problem=compiled.compile_joint_development({'schema':'joint-survey-compile-request-1',
        'survey_request':case['survey_request'],'development':case['development']})
    return case,problem


@pytest.mark.parametrize('index',[0,1,8,9])
def test_original_operands(index,tmp_path):
    case,problem=problem_for(index)
    with resources.JointResourceBudget(str(tmp_path)) as budget:
        inventory=conditioned.source_inventory()
        for stage,modality in enumerate(('gravity','magnetic')):
            allocation=conditioned.allocation_plan(problem,modality)
            new=conditioned.JointQuadraticObjective(problem,modality,.1,stage,inventory,allocation,budget)
            old=original.JointOptimizerObjective(problem,new.weights,new.start,stage,inventory,allocation,budget,modality)
            phi,g,H=new.evaluate(new.start,True,True);expected=old.evaluate(old.start,True,True)
            assert phi==expected[0];np.testing.assert_array_equal(g,expected[1])
            for vector in np.eye(problem.n): np.testing.assert_array_equal(H@vector,expected[2]@vector)
            factors=new.quadratic_operands(new.start).terms
            # Reconstruct literal ORIGINAL row order before multiplying. Summing
            # per-axis rounded normal matrices is not the original CSR reduction.
            positions={tuple(problem.R.indices[problem.R.indptr[i]:problem.R.indptr[i+1]]):i for i in range(problem.R.shape[0])}
            rows=[None]*problem.R.shape[0]
            for factor in factors:
                block=(factor.weights@factor.derivative).tocsr()
                block.sort_indices()
                for i in range(block.shape[0]):
                    entry=block[i].tocsr();position=positions[tuple(entry.indices)]
                    assert rows[position] is None;rows[position]=entry
            assert all(row is not None for row in rows)
            rebuilt=sparse.vstack(rows,format='csr')
            for attribute in ('indptr','indices','data'):
                np.testing.assert_array_equal(getattr(rebuilt,attribute),getattr(problem.R,attribute))
            np.testing.assert_array_equal((rebuilt.T@rebuilt).toarray(),(problem.R.T@problem.R).toarray())
            for factor in factors: assert factor.alpha==.5
            np.testing.assert_array_equal(new.A,problem.A[modality]);np.testing.assert_array_equal(new.d,problem.d[modality])
            np.testing.assert_array_equal(new.prediction_rows,problem.J[modality]*problem.scales[new.slice])
            assert allocation['admitted_bytes']==allocation['original_problem']['admitted_bytes']+allocation['owned_metric']['maximum']
            assert new.identity()['observation_components']==1 and new.identity()['runtime_epoch']==conditioned.public.LINEAR_EPOCH


@pytest.mark.parametrize('modality,beta',[('gravity',100.),('magnetic',.0001),('gravity',.0001),('magnetic',1000.)])
def test_public_native_fit(modality,beta,tmp_path,record_property):
    case,problem=problem_for(0)
    with resources.JointResourceBudget(str(tmp_path)) as budget:
        receipt=conditioned.solve_original_baseline(problem,modality,beta,0,budget)
    result=receipt['result'];trace=result['trace']
    assert trace['models_q'].shape[1]==problem.n and 1<=len(trace['models_q'])<=201
    assert receipt['coupled_inversion_performed'] is False
    assert receipt['scientific_acceptance_verified'] is False
    assert result['runtime_epoch']==conditioned.public.LINEAR_EPOCH
    # Preserve real statuses, do not fabricate PASS from an API binding.
    record_property('actual_status',result['status']);record_property('actual_stop',result['reason'])
    for attempt in result['conditioning_attempts']:
        assert attempt['iterations']<=200
        if attempt['true_relative_residual'] is not None: assert attempt['true_relative_residual']<=1e-6
    if result['status']=='converged':
        assert result['terminal_audits'] and result['terminal_audits'][-1]['check']['passed']
    if beta>=100.: assert result['status']=='converged'
    else: assert result['status']=='nonconverged' and result['reason']=='line_search_failed'
    sl=slice(0,problem.n) if modality=='gravity' else slice(problem.n,2*problem.n)
    assert np.all(trace['models_q']>=problem.lower[sl]) and np.all(trace['models_q']<=problem.upper[sl])


def test_factor_and_resource_caps(tmp_path,monkeypatch):
    _,problem=problem_for(0)
    with resources.JointResourceBudget(str(tmp_path)) as budget:
        inventory=conditioned.source_inventory();allocation=conditioned.allocation_plan(problem,'gravity')
        for modality in (None,'coupled',True):
            with pytest.raises((ValueError,TypeError)):
                conditioned.JointQuadraticObjective(problem,modality,.1,0,inventory,allocation,budget)
        first=problem.R.data[0];problem.R.data[0]=0.
        try:
            with pytest.raises(ValueError): conditioned.original_terms(problem)
        finally: problem.R.data[0]=first
        monkeypatch.setattr(conditioned.public,'SOURCE_SHA256','0'*64)
        with pytest.raises(RuntimeError): conditioned.source_inventory()


@pytest.mark.parametrize('modality,beta',[('gravity',100.),('magnetic',1000.)])
def test_original_precision_controls(modality,beta,tmp_path):
    case,problem=problem_for(0)
    with resources.JointResourceBudget(str(tmp_path)) as budget:
        receipt=conditioned.solve_original_baseline(problem,modality,beta,0,budget)
    assert receipt['result']['status']=='converged'
    G=kernels(case['survey_request'])[0 if modality=='gravity' else 1]
    reference,Fref,_,refkkt,_,_=independent_face_baseline(case,modality,G,beta)
    A,b,lo,hi,start=independent_problem(case,modality,G,beta);q=receipt['result']['q']
    F=.5*float(np.linalg.norm(A@q-b)**2);_,kkt=exact_kkt(A,b,q,lo,hi,start)
    scale=case['survey_request']['prior']['density' if modality=='gravity' else 'susceptibility']['scale']
    assert refkkt<=1e-5 and kkt<=1e-5
    assert abs(F-Fref)/max(1.,abs(Fref))<=1e-8
    assert np.linalg.norm(q-reference)/max(1.,np.linalg.norm(reference))<=1e-5
    assert np.max(np.abs(G@((q-reference)*scale)))<=1e-8
    assert F<=Fref+1e-10+1e-9*Fref
