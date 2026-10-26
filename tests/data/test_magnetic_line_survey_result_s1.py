"""The opened original S1 failure survives the complete retained Result path."""
import os
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'data-pipeline'))
sys.path.insert(0,str(Path(__file__).parent))
import magnetic_line_contract as base
import magnetic_line_survey_result as results
import magnetic_line_survey_runtime as runtime
from test_magnetic_line_survey_diagnostic import plan


def test_original_s1_full_result_keeps_original_predictive_failure(tmp_path):
    path=plan(tmp_path)
    envelope=base.strict_json(path.read_bytes())
    del envelope['mode']
    envelope.update(schema='m03-full-result-plan/1',navigation_root=None,
                    auxiliary_roots={},reference_definitions={},run_id='opened-original-s1-full-result')
    path.write_bytes(base.canonical_bytes(envelope))
    lifetime=runtime.run_worker(Path(sys.base_prefix)/'python.exe',
        Path(os.environ['GEOPHYSICS_EXISTING_PACKAGE_ROOT']),path.parent,path)
    assert lifetime['verdict']=='component_pass',(lifetime,(path.parent/'stderr.log').read_text())
    assert lifetime['total_processes']==1 and lifetime['active_processes']==0
    result=base.strict_json((path.parent/'result/result.json').read_bytes())
    assert result['inventory']['original_rows']==363 and result['fit']['fit_count']==25
    assert result['input']['original']['csv_sha256']=='ac28e5f7c8344b94ebe0c408484eede8ade5a4074c8ef44661bcfe774ff0bfae'
    assert result['partitions']['evaluation_count']==1
    assert abs(result['evaluation']['rmse_nT']-18.799740861734186)<=1e-7*18.799740861734186
    assert result['evaluation']['verdict']['overall']=='fail' and result['verdict']['overall']=='fail'
    assert abs(max(1e-6,.05*result['evaluation']['signal_rms_nT'])-.25966396538773057)<=1e-12
    gate=next(item for item in result['evaluation']['verdict']['gates'] if item['gate_id']=='predictive')
    assert gate['verdict']=='fail'
    verified=results.verify_result(path.parent/'result',temp_root=tmp_path)
    assert verified['custody_and_semantics']=='pass' and verified['rows']==363
    assert verified['selected_model_recomputation']=='not_executed'
