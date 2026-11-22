"""Actual maximum-count full workflow resource gate, not a recovery benchmark."""
import argparse
from contextlib import redirect_stdout
import io
from pathlib import Path
import sys

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'data-pipeline'),str(ROOT/'tests/numerics')]

import numpy as np  # noqa: E402
import joint_survey_plan as planner  # noqa: E402
import joint_survey_evaluation as evaluation  # noqa: E402
import joint_survey_workflow as workflow  # noqa: E402
import joint_survey_files as files  # noqa: E402
from joint_survey_serialization import local_joint_data_root,write_joint_development,_external  # noqa: E402
from test_joint_survey_plan import request  # noqa: E402


def maximum_request():
    survey=request();mesh=survey['mesh'];full=4096;count=2048
    mesh.update(origin_m=np.array([-500.,-500.,-200.]),hx_m=np.full(64,10.),hy_m=np.full(8,20.),hz_m=np.full(8,20.),
        active=np.arange(full)%2==0)
    for m in ('gravity','magnetic'):
        survey[m].update(receivers_m=np.column_stack((np.linspace(-600.,300.,count),np.full(count,-550.),np.full(count,100.))),
            mask=np.zeros(count,dtype=np.bool_),missing_reasons=('',)*count,groups=np.arange(count,dtype=np.int64),
            partition=np.arange(count,dtype=np.int64)%3)
        survey[m]['source']['citation']='Authored analytical zero-property resource control, not a field or recovery benchmark'
        survey[m]['noise'].update(kind='full_covariance',unit=survey[m]['unit']+'^2',cross_partition='declared_absent')
    def set_count(n):
        active=np.zeros(full,dtype=np.bool_);active[np.arange(n)*2]=True;mesh['active']=active
        for prop in ('density','susceptibility'):
            survey['prior'][prop].update(lower=np.full(n,-1500. if prop=='density' else 0.),
                upper=np.full(n,1500. if prop=='density' else .1),start=np.zeros(n),reference=np.zeros(n))
    lo=1;hi=2048
    while lo<hi:
        mid=(lo+hi+1)//2;set_count(mid)
        try: planner._contract(survey)
        except ValueError as exc:
            if 'resources:' not in str(exc): raise
            hi=mid-1
        else: lo=mid
    n=lo;set_count(n+1)
    try: planner._contract(survey)
    except ValueError as exc:
        if 'resources:' not in str(exc): raise
    else: raise RuntimeError('resource cap+1 unexpectedly admitted')
    set_count(n)
    plan=planner.plan_joint_survey(survey);development={'plan_sha256':plan['plan_sha256']};sealed={}
    for m in ('gravity','magnetic'):
        rows=np.r_[plan[m]['training_rows'],plan[m]['validation_rows']]
        observed=np.zeros(len(rows));noise=np.eye(len(rows))
        development[m]={'rows':rows,'observed':observed,'noise_values':noise,
            'observations_sha256':planner._digest({'rows':rows,'observed':observed,'unit':plan[m]['unit'],'plan_sha256':plan['plan_sha256']}),
            'noise_sha256':planner._digest({'rows':rows,'noise_values':noise,'unit':plan[m]['noise']['unit'],
                'kind':plan[m]['noise']['kind'],'plan_sha256':plan['plan_sha256']})}
        held=plan[m]['sealed_rows'];sealed.update({m+'_rows':held,m+'_observed':np.zeros(len(held)),m+'_noise':np.eye(len(held))})
    assert plan['resources']['projected_kernel_bytes']<=128*1024**2
    return survey,plan,development,sealed


def main():
    parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    parser.add_argument('--data-root',required=True);parser.add_argument('--scratch-root',required=True)
    args=parser.parse_args();data=local_joint_data_root(args.data_root);scratch=_external(args.scratch_root,existing=True)
    survey,plan,development,sealed=maximum_request()
    manifest=evaluation.write_joint_sealed(str(data/'sealed'),plan,sealed)
    write_joint_development(str(data/'development'),{'schema':'joint-survey-write-request-1','survey_request':survey,
        'development':development,'sealed_manifest':manifest,'originals':None})
    n=len(survey['prior']['density']['start'])
    print(f'maximum simultaneous resource input admitted:4096full/{n}active/2048+2048receivers/SPD covariance, exact n+1 rejected',flush=True)
    with redirect_stdout(io.StringIO()):
        receipt=workflow.solve_joint_workflow(data_root=str(data),development=str(data/'development'),sealed=str(data/'sealed'),
            output=str(data/'output'),scratch=str(scratch))
    verification=workflow.validate_joint_workflow(data_root=str(data),development=str(data/'development'),sealed=str(data/'sealed'),
        output=str(data/'output'),scratch=str(scratch))
    result={'schema':'joint-survey-resource-gate-1','full_cells':4096,'active_cells':n,'receivers_per_modality':2048,
        'full_covariance':True,'projected_kernel_bytes':plan['resources']['projected_kernel_bytes'],
        'maximum_simultaneous_export_admission':True,'active_count_plus_one_rejected':True,
        'workflow':receipt,'verification':verification,'nonzero_nominal_gate':'separate frozen24-case matrix',
        'recovery_benchmark':False,'field_eligible':False,'public_activation':False}
    files.metadata_budget(result)
    with (data/'resource-gate.json').open('xb') as stream: stream.write(files._content(result))
    print(files._content(result).decode(),flush=True)
    return 0 if receipt['status']=='completed' and verification['validated'] else 1


if __name__=='__main__': raise SystemExit(main())
