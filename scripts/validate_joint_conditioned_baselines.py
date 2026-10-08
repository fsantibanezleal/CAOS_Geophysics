"""Exclusive source-frozen384 ORIGINAL precision comparisons, actual public fits.

Reference optima are independent TEST oracles only. They are never passed to
production, used for fitting, projection rescue or source/metric construction.
"""
import argparse
from contextlib import redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'data-pipeline'),str(ROOT/'tests/numerics')]
# Harness-only explicit committed dependency checkout, not a survey import hook.
dependency=os.environ.get('GEOPHYSICS_M11_PUBLIC_DEPENDENCY')
if dependency: sys.path.append(str(Path(dependency)/'data-pipeline'))

import numpy as np
import joint_survey_cases as cases
import joint_survey_compiled as compiled
import joint_survey_conditioned as native
import joint_survey_files as files
import joint_survey_intake as intake
import joint_survey_plan as planner
import joint_survey_resources as resources
from joint_survey_serialization import _external,local_joint_data_root
from test_joint_survey_cases import independent_face_baseline,independent_problem,exact_kkt
from test_joint_survey_objective import kernels


def save(path,value):
    files.metadata_budget(value)
    with path.open('xb') as stream: stream.write(files._content(value))


def source():
    inventory=native.source_inventory()
    for path in (Path(__file__),ROOT/'data-pipeline/joint_survey_cases.py',
        ROOT/'tests/numerics/test_joint_survey_cases.py',ROOT/'tests/numerics/test_joint_survey_objective.py'):
        inventory[path.name]=intake._file_sha(path)
    return inventory


def native_diagnostics(destination,receipt):
    """Every native trace/direction/terminal/trial, with bounded individual files."""
    result=receipt['result'];destination.mkdir(mode=0o700)
    manifest=files.write_arrays(str(destination/'trace'),'trace.json','joint-conditioned-native-trace-1',
        {'status':result['status'],'reason':result['reason'],'iterations':result['iterations']},result['trace'])
    for label in ('conditioning_attempts','terminal_audits'):
        directory=destination/label;directory.mkdir(mode=0o700)
        for index,row in enumerate(result[label]):
            arrays={key:value for key,value in row.items() if type(value) is np.ndarray}
            payload={key:value for key,value in row.items() if key not in arrays}
            files.write_arrays(str(directory/f'n{index:03d}'),'native.json','joint-conditioned-native-diagnostic-1',payload,arrays)
    trials=destination/'line_search_trials';trials.mkdir(mode=0o700)
    for index in range(0,len(result['line_search_trials']),64):
        save(trials/f'n{index//64:03d}.json',{'schema':'joint-conditioned-native-trials-1',
            'start_index':index,'trials':result['line_search_trials'][index:index+64]})
    failed=result['failed_trial']
    if failed is not None:
        arrays={key:value for key,value in failed.items() if type(value) is np.ndarray}
        payload={key:value for key,value in failed.items() if key not in arrays}
        files.write_arrays(str(destination/'failed_trial'),'native.json','joint-conditioned-native-failed-trial-1',payload,arrays)
    return manifest['manifest_sha256']


def main():
    parser=argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--data-root');parser.add_argument('--output-root',required=True);parser.add_argument('--scratch-root',required=True)
    args=parser.parse_args();root=local_joint_data_root(args.data_root);out=_external(args.output_root);scratch=_external(args.scratch_root,existing=True)
    if (out==root or not out.is_relative_to(root) or out.exists()
            or out==scratch or out.is_relative_to(scratch) or scratch.is_relative_to(out)):
        raise ValueError('matrix: exclusive disjoint external roots required')
    original_sources=source();out.mkdir(mode=0o700);cells=[]
    for index in range(24):
        case=cases.make_joint_control(index);identity=planner._digest(case);name=case['case_id'];directory=out/name;directory.mkdir(mode=0o700)
        work=scratch/name;work.mkdir(mode=0o700)
        problem=compiled.compile_joint_development({'schema':'joint-survey-compile-request-1',
            'survey_request':case['survey_request'],'development':case['development']})
        Gg,Gm=kernels(case['survey_request']);records=[]
        with resources.JointResourceBudget(str(work)) as budget:
            for modality,G in (('gravity',Gg),('magnetic',Gm)):
                for beta in native.original.objective.BETAS:
                    stage=len(records)
                    with redirect_stdout(io.StringIO()): receipt=native.solve_original_baseline(problem,modality,beta,stage,budget)
                    result=receipt['result'];fit=directory/f'c{stage:02d}'
                    trace_sha=native_diagnostics(fit,receipt)
                    reference,Fref,_,refkkt,raw,rawkkt=independent_face_baseline(case,modality,G,beta)
                    A,b,lo,hi,start=independent_problem(case,modality,G,beta);q=result['q'];comparison=None
                    if q is not None:
                        _,kkt=exact_kkt(A,b,q,lo,hi,start);F=.5*float(np.linalg.norm(A@q-b)**2)
                        scale=case['survey_request']['prior']['density' if modality=='gravity' else 'susceptibility']['scale']
                        objective_error=abs(F-Fref)/max(1.,abs(Fref));model_error=float(np.linalg.norm(q-reference)/max(1.,np.linalg.norm(reference)))
                        prediction_error=float(np.max(np.abs(G@((q-reference)*scale))))
                        comparison={'relative_objective_error':objective_error,'normalized_model_error':model_error,
                            'physical_prediction_error':prediction_error,'normalized_exact_bound_kkt':kkt,
                            'objective_gate':objective_error<=1e-8,'model_gate':model_error<=1e-5,
                            'prediction_gate':prediction_error<=1e-8,'stationarity_gate':kkt<=1e-5,
                            'original_nearopt_gate':F<=Fref+1e-10+1e-9*Fref}
                    header={key:value for key,value in receipt.items() if key!='result'}
                    record={**header,'status':result['status'],'reason':result['reason'],'iterations':result['iterations'],
                        'source_binding':result['source_binding'],'trace_manifest_sha256':trace_sha,
                        'reference_exact_kkt':refkkt,'raw_reference_exact_kkt':rawkkt,'raw_reference_status':int(raw.status),
                        'actual':comparison,'scientific_precision_accepted':bool(result['status']=='converged' and comparison
                            and all(comparison[key] for key in ('objective_gate','model_gate','prediction_gate','stationarity_gate','original_nearopt_gate')))}
                    save(fit/'fit.json',record);records.append({'stage':stage,'modality':modality,'beta':beta,
                        'fit_sha256':intake._file_sha(fit/'fit.json'),'status':result['status'],'reason':result['reason'],
                        'actual':comparison,'scientific_precision_accepted':record['scientific_precision_accepted']})
                    print(json.dumps({'case_id':name,**records[-1]},sort_keys=True),flush=True)
            if planner._digest(case)!=identity or source()!=original_sources: raise RuntimeError('matrix: input/source drift')
            measured=budget.receipt(workflow_completed=True)
        cell={'schema':'joint-conditioned-baseline-cell-1','case_id':name,'input_sha256':identity,'records':records,
            'resources':measured,'scientific_precision_accepted':all(r['scientific_precision_accepted'] for r in records),
            'original_thresholds':{'relative_objective':1e-8,'normalized_model':1e-5,'physical_prediction':1e-8,'normalized_exact_kkt':1e-5,
                'nearopt_atol':1e-10,'nearopt_rtol':1e-9},'coupled_inversion_performed':False,'field_eligible':False,'public_activation':False}
        save(directory/'cell.json',cell);cells.append({'case_id':name,'cell_sha256':intake._file_sha(directory/'cell.json'),
            'scientific_precision_accepted':cell['scientific_precision_accepted']})
    summary={'schema':'joint-conditioned-baseline-matrix-1','source_inventory':original_sources,'records':cells,
        'cells_attempted':24,'actual_native_fits':384,'sources_unchanged':source()==original_sources,
        'scientific_precision_accepted':all(c['scientific_precision_accepted'] for c in cells),
        'historical_precision_failures_retained':True,'coupled_inversion_performed':False,'field_eligible':False,'public_activation':False}
    save(out/'matrix.json',summary)
    return 0 if summary['scientific_precision_accepted'] else 1


if __name__=='__main__': raise SystemExit(main())
