"""Deterministic qualified controls -> ONE frozen QR acquisition run -> custody.

No automatic matrix retry or outer-driven retuning. Failed immutable outputs
remain evidence; a later downstream repair must not rerun the fit matrix.
"""
import argparse
from hashlib import sha256
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

PRODUCT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PRODUCT/'data-pipeline'))


def main():
    import magnetic_line_contract as base
    import magnetic_line_survey as core
    import magnetic_line_survey_io as io
    import magnetic_line_survey_qr_execution as execution
    import magnetic_line_survey_runtime as runtime
    from magnetic_line_survey_qr_prerequisite import HISTORICAL_PLAN_SHA,HISTORICAL_FAILURE_SHA
    parser=argparse.ArgumentParser()
    parser.add_argument('--retained-root',required=True)
    parser.add_argument('--prerequisite',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    output=Path(args.output)
    if output.exists():raise core.SurveyError('custody_mismatch','seal')
    io.external_path(output.parent);output.mkdir()
    retained=io.external_path(args.retained_root)
    prerequisite=io.external_path(args.prerequisite,directory=False)
    if sha256(prerequisite.read_bytes()).hexdigest()!=execution.PREREQUISITE_SHA:
        raise core.SurveyError('custody_mismatch','seal')
    original=base.read_bounded(core._plain_path(retained/'worker/plan.json'),2097152)
    failure=base.read_bounded(core._plain_path(retained/'worker/fit/physical-fit-failure.json'),2097152)
    if sha256(original).hexdigest()!=HISTORICAL_PLAN_SHA or sha256(failure).hexdigest()!=HISTORICAL_FAILURE_SHA:
        raise core.SurveyError('custody_mismatch','seal')
    source_pins=execution.source_identity()
    tests=[PRODUCT/'tests/data'/name for name in ('test_magnetic_line_survey_qr.py','test_magnetic_line_survey_qr_epoch.py')]
    test_pins={path.name:sha256(path.read_bytes()).hexdigest() for path in tests}
    xml=output/'qualified-controls.xml'
    packages=Path(os.environ['GEOPHYSICS_EXISTING_PACKAGE_ROOT']).resolve(strict=True)
    executable=Path(sys.base_prefix)/'python.exe'
    code="import sys,runpy;sys.path.insert(0,sys.argv.pop(1));runpy.run_module('pytest',run_name='__main__')"
    system_temp=output/'system-temp';system_temp.mkdir()
    # System scratch is an owned sibling of retained data, never its ancestor.
    environment=dict(os.environ,PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTHONDONTWRITEBYTECODE='1',TEMP=str(system_temp),TMP=str(system_temp))
    for key in ('OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS','NUMBA_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
        environment[key]='1'
    completed=subprocess.run([str(executable),'-B','-S','-c',code,str(packages),*[str(test) for test in tests],
        '-q','-p','no:cacheprovider',f'--junitxml={xml}',f'--basetemp={output}/controls-temp'],
        cwd=PRODUCT,env=environment,check=False)
    if completed.returncode!=0:return completed.returncode
    suites=ET.parse(xml).getroot().findall('testsuite')
    if sum(int(s.get('tests','0')) for s in suites)!=43 or \
       any(int(s.get(k,'0')) for s in suites for k in ('errors','failures','skipped')) or \
       source_pins!=execution.source_identity() or test_pins!={path.name:sha256(path.read_bytes()).hexdigest() for path in tests}:
        raise core.SurveyError('custody_mismatch','seal')
    core._write_member(output,'qualified-controls.json',base.canonical_bytes(dict(schema='m03-qr-epoch-controls/1',
        epoch=execution.schema.POLICY_EPOCH,tests=43,verdict='component_pass',source_sha256=source_pins,
        test_sha256=test_pins,xml_sha256=sha256(xml.read_bytes()).hexdigest(),field8201='not_verified')))
    plan=base.strict_json(original)
    plan.update(schema='m03-resolution-qr-fit-plan/1',capacity_root=str(retained/'worker/sealed'),
        prerequisite=str(prerequisite),run_id='opened-original-s3-augmented-direct-qr-v3')
    worker=output/'worker';worker.mkdir()
    core._write_member(worker,'plan.json',base.canonical_bytes(plan))
    receipt=runtime.run_worker(executable,packages,worker,worker/'plan.json')
    print(base.canonical_bytes(receipt).decode('ascii'),flush=True)
    if receipt['verdict']!='component_pass':return 2
    from magnetic_line_survey_result_qr import verify_result
    from magnetic_line_survey_export_qr import export_result,verify_export
    checked=verify_result(worker/'result',temp_root=output)
    result=base.strict_json(base.read_bounded(core._plain_path(worker/'result/result.json'),2097152))
    from magnetic_line_survey_representation_qr import Reader
    reader=Reader(worker/'result')
    rows=list(reader.table(result['fit']['candidates']))
    identities=list(reader.table(result['fit']['solve_identities']))
    if len(rows)!=96 or len(identities)!=97 or result['fit']['fit_count']!=97 or \
       result['inventory']['original_rows']!=363 or result['partitions']['evaluation_count']!=1:
        raise core.SurveyError('custody_mismatch','replay')
    # Positive completed Result is then challenged without fitting or opening
    # another outer experiment. Every mutation must fail the real verifier.
    from copy import deepcopy
    for change in ('epoch','fit_count','selected_geometry','source_counts','gradient','legacy_status','c_hash','overall','outer_count','edge'):
        wrong=deepcopy(result)
        if change=='epoch':wrong['policy_epoch']='resolution_v2'
        elif change=='fit_count':wrong['fit']['fit_count']=25
        elif change=='selected_geometry':wrong['fit']['selected_source_geometry_index']=(wrong['fit']['selected_source_geometry_index']+1)%4
        elif change=='source_counts':wrong['geometry']['source_counts_by_geometry'][0][0]+=1
        elif change=='gradient':wrong['fit']['solve']['original_diagnostics']['stationarity_relative']=1.1e-9
        elif change=='legacy_status':wrong['fit']['solve']['istop']=0
        elif change=='c_hash':wrong['fit']['scaled_coefficients']['sha256']='0'*64
        elif change=='overall':wrong['verdict']['overall']='pass'
        elif change=='outer_count':wrong['partitions']['evaluation_count']=0
        else:wrong['channels'][1]['state'][-1]['output_channel_sha256']='0'*64
        try:verify_result(worker/'result',wrong,temp_root=output,allow_uncommitted=True)
        except core.SurveyError:continue
        raise core.SurveyError('custody_mismatch','replay')
    exported=export_result(worker/'result',output/'private-export',scope='private',temp_root=output,original_csv=plan['csv_path'])
    if verify_export(output/'private-export',temp_root=output)!=exported:raise core.SurveyError('custody_mismatch','replay')
    from magnetic_line_survey_cli_qr import verify_local
    native=verify_local(worker/'result',output/'cold-verification',temp_root=output)
    core._write_member(output,'qr-epoch-result.json',base.canonical_bytes(dict(schema='m03-qr-epoch-result/1',
        epoch=execution.schema.POLICY_EPOCH,result_sha256=base.digest(result),rows=363,
        fit_count=97,candidate_count=96,outer_evaluation_count=1,outer_status='opened_authored_diagnostic',
        numerical_verdict='component_pass',predictive_verdict=result['evaluation']['verdict']['overall'],
        rmse_nT=result['evaluation']['rmse_nT'],signal_rms_nT=result['evaluation']['signal_rms_nT'],
        selected={key:result['fit'][key] for key in ('selected_source_geometry_index','selected_depth_m','selected_damping')},
        maximum_original_gradient=max(item['solve']['original_diagnostics']['stationarity_relative'] for item in identities),
        maximum_condition_upper_bound=max(item['solve']['condition_upper_bound'] for item in identities),
        actual_custody=checked,adverse_result_mutations=10,native_selected_model_verification=native,
        export=exported,replay='unresolved' if exported['replay']=='unresolved' else 'not_executed',
        historical_S1='fail_unchanged',historical_opened100_50='fail_unchanged',historical_v2='fail_unchanged',
        historical_HP='fail_unchanged',field8201='not_verified',host_admission='not_established')))
    return 0


if __name__=='__main__':raise SystemExit(main())
