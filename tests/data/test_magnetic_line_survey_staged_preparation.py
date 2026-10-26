"""Default-cap actual full original geometry, no science/field grant."""
from copy import deepcopy
import os
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'data-pipeline'))
import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_inspection as inspection
import magnetic_line_survey_preparation_capacity as capacity
import magnetic_line_survey_runtime as runtime
from test_magnetic_line_survey_bundle import fixture,entry


def test_exact_default_phase_proof_and_hard_limit_refusals():
    first=capacity.inspection_capacity(53714,[20000,20000],[1000000])
    assert first['scratch_bound_bytes']==16*1024**2
    second=capacity.preparation_capacity(363,1000000,69)
    I=4096*(16+(2048*69+4095)//4096)
    assert second['index_and_journal_bytes']==2*I
    assert second['scratch_bound_bytes']==1000000+2*I+65536*363+134217728
    assert second['dataset_reservation_bytes']==18*1024**2+second['scratch_bound_bytes']<1024**3
    for args in ((True,1000000,69),(363,True,69),(363,1000000,True),(8000000,1000000,69)):
        with pytest.raises(core.SurveyError):capacity.preparation_capacity(*args)
    for limits in (dict(memory_bytes=4*1024**3+1,scratch_bytes=1,cpu_s=1,wall_s=1,parent_cpu_s=1),{'memory_bytes':True},{}):
        with pytest.raises(core.SurveyError):runtime.checked_limits(limits)


def test_inspection_no_index_and_full_count_then_independent_rebind(tmp_path):
    plan=fixture(tmp_path/'original');plan['schema']='m03-owner-inspection-plan/1'
    receipt=inspection._inspect(plan)
    assert receipt['rows']==363 and receipt['value_access']=='not_opened'
    assert receipt['bundle_members']==[69]
    assert receipt['next_phase']['dataset_reservation_bytes']<1024**3
    assert not list((tmp_path/'original').glob('bundle-index*'))
    wrong=deepcopy(plan);wrong['original']['sha256']='a'*64
    with pytest.raises(core.SurveyError):inspection._inspect(wrong)


@pytest.mark.skipif(sys.platform!='win32',reason='Actual Windows Job required')
def test_actual_native_two_stages_stricter_default_caps(tmp_path):
    plan=fixture(tmp_path/'original');plan['schema']='m03-owner-inspection-plan/1'
    executable=Path(sys.base_prefix)/'python.exe';packages=Path(os.environ['GEOPHYSICS_EXISTING_PACKAGE_ROOT'])
    first=tmp_path/'inspection';first.mkdir();path=first/'plan.json';path.write_bytes(base.canonical_bytes(plan))
    caps=dict(memory_bytes=512*1024**2,scratch_bytes=16*1024**2,cpu_s=600,wall_s=600,parent_cpu_s=300)
    lifetime=runtime.run_worker(executable,packages,first,path,configured_limits=caps)
    assert lifetime['verdict']=='component_pass',(lifetime,(first/'stderr.log').read_text(),(first/'stdout.log').read_text())
    assert lifetime['enforced_limits']==caps and lifetime['active_processes']==0
    assert not (first/'bundle-index.sqlite3').exists() and not (first/'auxiliary').exists()
    receipt=base.strict_json((first/'inspection.json').read_bytes())
    assert receipt['rows']==363 and receipt['next_phase']['dataset_reservation_bytes']<1024**3
    second=tmp_path/'preparation';second.mkdir()
    next_plan={**plan,'schema':'m03-owner-preparation-plan/2','inspection':entry(first/'inspection.json')}
    path=second/'plan.json';path.write_bytes(base.canonical_bytes(next_plan))
    caps={**caps,'scratch_bytes':receipt['next_phase']['scratch_bound_bytes']}
    lifetime=runtime.run_worker(executable,packages,second,path,configured_limits=caps)
    assert lifetime['verdict']=='component_pass',(lifetime,(second/'stderr.log').read_text(),(second/'stdout.log').read_text())
    result=base.strict_json((second/'preparation.json').read_bytes())
    assert result['rows']==363 and result['physical_members']==69
    assert result['capacity']==receipt['next_phase'] and result['value_access']=='not_opened'
    assert lifetime['scratch_bytes']==runtime.owned_bytes(second)
    assert lifetime['scratch_bytes']<=receipt['next_phase']['scratch_bound_bytes']
    assert not list(second.rglob('*coefficients*')) and not (second/'result').exists()
