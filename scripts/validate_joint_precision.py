"""Add independent exact-face baseline predicates; never repair production q."""
import argparse
import hashlib
from pathlib import Path
import sys

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'data-pipeline'),str(ROOT/'tests/numerics')]

import numpy as np  # noqa: E402
import joint_survey_cases as cases  # noqa: E402
import joint_survey_evaluation as evaluation  # noqa: E402
import joint_survey_files as files  # noqa: E402
import joint_survey_intake as intake  # noqa: E402
import joint_survey_plan as planner  # noqa: E402
import joint_survey_resources as resources  # noqa: E402
import joint_survey_calibration_io as transport  # noqa: E402
from joint_survey_serialization import local_joint_data_root,_external  # noqa: E402
from joint_survey_workflow import _compile  # noqa: E402
from test_joint_survey_cases import independent_face_baseline,independent_problem,exact_kkt  # noqa: E402
from test_joint_survey_objective import kernels  # noqa: E402


def compare_baselines(case,ledger):
    result=[]
    for modality,G in zip(evaluation.MODALITIES,kernels(case['survey_request'])):
        for candidate in ledger['candidates'][:16]:
            if candidate['modality']!=modality: continue
            beta=candidate['weights']['beta_'+modality]
            qface,cost,_,face_kkt,raw,raw_kkt=independent_face_baseline(case,modality,G,beta)
            A,b,lo,hi,start=independent_problem(case,modality,G,beta)
            q=candidate['result']['q'];actual=None
            if q is not None:
                _,kkt=exact_kkt(A,b,q,lo,hi,start)
                delta=abs(.5*float(np.linalg.norm(A@q-b)**2)-cost)/max(1.,abs(cost))
                model_error=float(np.linalg.norm(q-qface)/max(1.,np.linalg.norm(qface)))
                prop='density' if modality=='gravity' else 'susceptibility'
                scale=case['survey_request']['prior'][prop]['scale']
                prediction_error=float(np.max(np.abs(G@((q-qface)*scale))))
                actual={'relative_objective_error':delta,'normalized_model_error':model_error,
                    'physical_prediction_error':prediction_error,'exact_kkt_normalized':kkt,
                    'objective_gate':delta<=1e-8,'model_gate':model_error<=1e-5,
                    'prediction_gate':prediction_error<=1e-8,'stationarity_gate':kkt<=1e-5}
            result.append({'stage':candidate['stage'],'modality':modality,'beta':beta,
                'production_status':candidate['result']['status'],'production_reason':candidate['result']['reason'],
                'raw_reference_status':int(raw.status),'raw_reference_exact_kkt':raw_kkt,
                'raw_reference_stationarity_gate':raw_kkt<=1e-5,
                'exact_face_reference_kkt':face_kkt,'reference_stationarity_gate':face_kkt<=1e-5,'actual':actual})
    return tuple(result)


def main():
    parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    parser.add_argument('--data-root',required=True);parser.add_argument('--scratch-root',required=True)
    args=parser.parse_args();data=local_joint_data_root(args.data_root);scratch=_external(args.scratch_root,existing=True)
    if data==scratch or data.is_relative_to(scratch) or scratch.is_relative_to(data): raise ValueError('precision: disjoint roots')
    output=data/'exact-face-validation';destination=output/'face-inverse-controls.json'
    if output.exists(): raise FileExistsError('precision: exclusive supplemental receipt directory required')
    matrix_bytes=intake._read_bounded(data/'matrix.json',planner.MAX_METADATA_BYTES)
    matrix=intake._parse_json(matrix_bytes)
    planner._keys(matrix,('schema','records','source_sha256','cells_attempted','complete_cli_workflows',
        'original_precision_failures_retained','field_eligible','public_activation','scientific_precision_accepted'),'matrix')
    if matrix['schema']!='joint-survey-matrix-1' or matrix['cells_attempted']!=24 or len(matrix['records'])!=24:
        raise ValueError('precision: complete frozen24-case matrix required')
    output.mkdir(mode=0o700)
    records=[];original_hashes={data/'matrix.json':hashlib.sha256(matrix_bytes).hexdigest()}
    all_comparisons=[]
    for index,summary in enumerate(matrix['records']):
        case=cases.make_joint_control(index);cell=data/case['case_id']
        original=intake._read_bounded(cell/'matrix-cell.json',planner.MAX_METADATA_BYTES)
        if hashlib.sha256(original).hexdigest()!=summary['cell_sha256']: raise ValueError('precision: original cell hash drift')
        original_hashes[cell/'matrix-cell.json']=summary['cell_sha256']
        receipt=intake._parse_json(original)
        if summary['case_id']!=case['case_id'] or receipt['input_sha256']!=planner._digest(case):
            raise ValueError('precision: original fixed control identity drift')
        if receipt['workflow']['status']!='completed':
            records.append({'case_id':case['case_id'],'status':'unresolved','reason':'original_workflow_not_completed'})
            continue
        _,problem=_compile(cell/'development')
        with resources.JointResourceBudget(str(scratch)) as budget:
            ledger=transport.load_joint_calibration(str(cell/'output'/'calibration'),problem,budget)
            if ledger['calibration_sha256']!=receipt['calibration_sha256']: raise ValueError('precision: original fit identity drift')
            comparisons=compare_baselines(case,ledger)
            measured=budget.receipt(workflow_completed=True)
        manifest=cell/'output/calibration/calibration.json';digest=intake._file_sha(manifest)
        original_hashes[manifest]=digest
        packet={'case_id':case['case_id'],'status':'evaluated','calibration_sha256':ledger['calibration_sha256'],
            'calibration_manifest_sha256':digest,
            'comparisons':comparisons,'resources':measured}
        files.metadata_budget(packet);encoded=files._content(packet)
        with (output/(case['case_id']+'.json')).open('xb') as stream: stream.write(encoded)
        records.append({'case_id':case['case_id'],'status':'evaluated','calibration_sha256':ledger['calibration_sha256'],
            'supplement_sha256':hashlib.sha256(encoded).hexdigest(),'baseline_controls':len(comparisons)})
        all_comparisons.extend(comparisons)
        print(case['case_id'],'exact-face predicates recorded; original failures retained',flush=True)
    predicates=('objective_gate','model_gate','prediction_gate','stationarity_gate')
    comparisons=all_comparisons
    failures={key:sum(v['actual'] is None or not v['actual'][key] for v in comparisons) for key in predicates}
    result={'schema':'joint-survey-face-inverse-controls-1','matrix_sha256':hashlib.sha256(matrix_bytes).hexdigest(),
        'records':tuple(records),'baseline_controls':len(comparisons),'predicate_failures':failures,
        'all_scientific_predicates_pass':len(comparisons)==384 and not any(failures.values()),
        'original_records_unchanged':True,'original_precision_failures_retained':True,'field_eligible':False,
        'public_activation':False,'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    for path,digest in original_hashes.items():
        if intake._file_sha(path)!=digest: raise ValueError('precision: original records changed during supplemental evaluation')
    files.metadata_budget(result)
    with destination.open('xb') as stream: stream.write(files._content(result))
    print('exact-face predicate failures:',failures,flush=True)
    return 0 if result['all_scientific_predicates_pass'] else 1


if __name__=='__main__': raise SystemExit(main())
