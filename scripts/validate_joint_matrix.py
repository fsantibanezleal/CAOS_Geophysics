"""Frozen24-case actual supplied-survey methodology and private CLI matrix."""
import argparse
from contextlib import redirect_stdout
import hashlib
import io
from pathlib import Path
import sys

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'data-pipeline'),str(ROOT/'tests/numerics')]

import numpy as np  # noqa: E402
import joint_survey_cases as cases  # noqa: E402
import joint_survey_compiled as compiled  # noqa: E402
import joint_survey_evaluation as evaluation  # noqa: E402
import joint_survey_calibration_io as transport  # noqa: E402
import joint_survey_files as files  # noqa: E402
import joint_survey_plan as planner  # noqa: E402
import joint_survey_resources as resources  # noqa: E402
import joint_survey_workflow as workflow  # noqa: E402
from joint_survey_serialization import local_joint_data_root,write_joint_development,_external  # noqa: E402
from test_joint_survey_cases import independent_problem,independent_baseline,exact_kkt  # noqa: E402
from test_joint_survey_objective import kernels  # noqa: E402


def _save(path,value):
    files.metadata_budget(value)
    with path.open('xb') as stream: stream.write(files._content(value))


def run_cell(index,data,scratch):
    case=cases.make_joint_control(index);identity=planner._digest(case)
    cell=data/case['case_id'];cell.mkdir(mode=0o700)
    work=scratch/case['case_id'];work.mkdir(mode=0o700)
    problem=compiled.compile_joint_development({'schema':'joint-survey-compile-request-1',
        'survey_request':case['survey_request'],'development':case['development']})
    sealed={m+'_'+label:case['sealed'][m][source] for m in evaluation.MODALITIES
        for source,label in (('rows','rows'),('observed','observed'),('noise_values','noise'))}
    manifest=evaluation.write_joint_sealed(str(cell/'sealed'),problem.plan,sealed)
    write_joint_development(str(cell/'development'),{'schema':'joint-survey-write-request-1',
        'survey_request':case['survey_request'],'development':case['development'],'sealed_manifest':manifest,'originals':None})
    # Genuine strict solve/export/evaluation. Vendor text is not an artifact.
    with redirect_stdout(io.StringIO()):
        receipt=workflow.solve_joint_workflow(data_root=str(data),development=str(cell/'development'),
            sealed=str(cell/'sealed'),output=str(cell/'output'),scratch=str(work))
    if planner._digest(case)!=identity: raise RuntimeError('validation: control inputs mutated')
    result={'case_id':case['case_id'],'input_sha256':identity,'family':case['family'],'regime':case['regime'],
        'covariance':bool(index%2),'workflow':receipt,'replay':None,'baseline_controls':{},'truth_metrics':{},
        'field_eligible':False,'scientific_precision_accepted':False}
    if receipt['status']=='completed':
        result['replay']=workflow.validate_joint_workflow(data_root=str(data),development=str(cell/'development'),
            sealed=str(cell/'sealed'),output=str(cell/'output'),scratch=str(work))
    elif (cell/'output'/'aborted').exists():
        result.update(calibration_sha256=None,candidate_counts={},selected_coupling=None,forced_positive_vs_baseline=())
        _save(cell/'matrix-cell.json',result)
        print(case['case_id'],'aborted',receipt['reason'],flush=True)
        return result
    with resources.JointResourceBudget(str(work)) as budget:
        ledger=transport.load_joint_calibration(str(cell/'output'/'calibration'),problem,budget)
        physical_kernels=kernels(case['survey_request'])
        for m,G in zip(evaluation.MODALITIES,physical_kernels):
            controls=[]
            for c in ledger['candidates']:
                if c['modality']!=m: continue
                beta=c['weights']['beta_'+m];A,b,lo,hi,start=independent_problem(case,m,G,beta)
                reference,_,reference_kkt=independent_baseline(case,m,G,beta)
                q=c['result']['q'];actual=None
                if q is not None:
                    _,kkt=exact_kkt(A,b,q,lo,hi,start)
                    ref_f=.5*float(np.linalg.norm(A@reference.x-b)**2);own_f=.5*float(np.linalg.norm(A@q-b)**2)
                    delta=abs(own_f-ref_f)/max(1.,abs(ref_f))
                    model_error=float(np.linalg.norm(q-reference.x)/max(1.,np.linalg.norm(reference.x)))
                    prop='density' if m=='gravity' else 'susceptibility';scale=case['survey_request']['prior'][prop]['scale']
                    prediction_error=float(np.max(np.abs(G@((q-reference.x)*scale))))
                    actual={'exact_kkt_normalized':kkt,'relative_objective_error':delta,
                        'normalized_model_error':model_error,'physical_prediction_error':prediction_error,
                        'objective_gate':delta<=1e-8,'model_gate':model_error<=1e-5,'prediction_gate':prediction_error<=1e-8,
                        'stationarity_gate':kkt<=1e-5}
                controls.append({'stage':c['stage'],'beta':beta,'production_status':c['result']['status'],
                    'raw_reference_status':int(reference.status),'raw_reference_exact_kkt':reference_kkt,
                    'raw_reference_stationarity_gate':reference_kkt<=1e-5,'actual':actual})
            result['baseline_controls'][m]=tuple(controls)
        if ledger['selection'] is not None:
            q=ledger['selection']['q'];n=problem.n
            for m,prop,sl in (('gravity','density',slice(0,n)),('magnetic','susceptibility',slice(n,2*n))):
                truth=case['truth']['coarse_'+('density_kg_m3' if m=='gravity' else 'susceptibility_si')]
                model=q[sl]*problem.scales[sl]
                result['truth_metrics'][m]={'physical_rmse':float(np.sqrt(np.mean((model-truth)**2))),
                    'unit':'kg_m3' if prop=='density' else 'si','refined_source_mismatch':True,'recovery_verified':False}
        result['calibration_sha256']=ledger['calibration_sha256']
        result['candidate_counts']={'converged':sum(c['result']['status']=='converged' for c in ledger['candidates']),
            'failed':sum(c['result']['status']=='failed' for c in ledger['candidates']),
            'nonconverged':sum(c['result']['status']=='nonconverged' for c in ledger['candidates']),
            'eligible_positive':sum(c['eligible'] for c in ledger['candidates'][16:])}
        result['selected_coupling']=None if ledger['selection'] is None else ledger['selection']['weights']['coupling']
        result['forced_positive_vs_baseline']=tuple({'stage':c['stage'],'lambda':c['weights']['coupling'],
            'eligible':c['eligible'],'validation_wrms':c['validation_wrms']} for c in ledger['candidates'][16:])
    _save(cell/'matrix-cell.json',result)
    print(case['case_id'],receipt['status'],receipt.get('reason',ledger['reason']),result['candidate_counts'],flush=True)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    parser.add_argument('--data-root',required=True);parser.add_argument('--scratch-root',required=True)
    args=parser.parse_args();data=local_joint_data_root(args.data_root);scratch=_external(args.scratch_root,existing=True)
    if data==scratch or data.is_relative_to(scratch) or scratch.is_relative_to(data): raise ValueError('validation: disjoint roots')
    records=[]
    for index in range(24): records.append(run_cell(index,data,scratch))
    source={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (
        Path(__file__),ROOT/'data-pipeline/joint_survey_cases.py',ROOT/'data-pipeline/joint_survey_optimizer.py')}
    compact=tuple({'case_id':r['case_id'],'cell_sha256':hashlib.sha256(files._content(r)).hexdigest(),
        'family':r['family'],'regime':r['regime'],'covariance':r['covariance'],'workflow_status':r['workflow']['status'],
        'candidate_counts':r['candidate_counts'],'selected_coupling':r['selected_coupling'],
        'replay_validated':r['replay'] is not None and r['replay']['validated']} for r in records)
    summary={'schema':'joint-survey-matrix-1','records':compact,'source_sha256':source,
        'cells_attempted':24,'complete_cli_workflows':sum(r['workflow']['status']=='completed' for r in records),
        'original_precision_failures_retained':True,'field_eligible':False,'public_activation':False,
        'scientific_precision_accepted':False}
    _save(data/'matrix.json',summary)
    return 0 if all(r['workflow']['status']=='completed' for r in records) else 1


if __name__=='__main__': raise SystemExit(main())
