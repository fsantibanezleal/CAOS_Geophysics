"""Current retained original S1, training-only root cause in a fresh actual Job."""
from hashlib import sha256
import os
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'data-pipeline'))
import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_runtime as runtime


def test_training_diagnosis_refuses_fictional_containment(tmp_path):
    from magnetic_line_survey_diagnosis import diagnose_retained_s1
    with pytest.raises(core.SurveyError,match='resource_refused'):
        diagnose_retained_s1({},tmp_path,0)
    assert not list(tmp_path.iterdir())


def test_actual_original_s1_training_root_cause_without_new_outer(tmp_path):
    from magnetic_line_survey_diagnosis import diagnose_retained_s1  # prospective symbol gate
    assert callable(diagnose_retained_s1)
    root=Path(os.environ['GEOPHYSICS_RETAINED_S1_DIAGNOSTIC'])
    original=Path(os.environ['GEOPHYSICS_RETAINED_S1_CSV'])
    plan=dict(schema='m03-training-diagnosis-plan/1',diagnostic_root=str(root),original_csv=str(original),
        retained_result_sha256=sha256((root/'fit/blocked-diagnostic.json').read_bytes()).hexdigest(),
        retained_seal_sha256=sha256((root/'sealed/geometry-seal.json').read_bytes()).hexdigest())
    path=tmp_path/'plan.json'
    path.write_bytes(base.canonical_bytes(plan))
    receipt=runtime.run_worker(Path(sys.base_prefix)/'python.exe',Path(os.environ['GEOPHYSICS_EXISTING_PACKAGE_ROOT']),tmp_path,path)
    assert receipt['verdict']=='component_pass',(receipt,(tmp_path/'stderr.log').read_text())
    result=base.strict_json((tmp_path/'training-diagnosis.json').read_bytes())
    assert result['original_s1_predictive_verdict']=='fail'
    assert result['new_outer_evaluations']==0 and result['production_fits']==0 and result['independent_training_oracles']==2
    assert result['rows']==294 and result['sources']==66
    assert abs(result['projection_rmse_nT']-3.5608746056014646)<1e-7
    assert abs(result['damped_oracle_rmse_nT']-3.5608761126551283)<1e-7
    assert result['max_prediction_difference_nT']<=result['frozen_prediction_tolerance_nT']
    assert result['relative_objective_difference']<=1e-8
    assert result['field_acceptance']=='unresolved'
