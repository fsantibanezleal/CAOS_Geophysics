"""Actual complete 25-fit opened S1 diagnostic in one native Windows Job."""
from importlib.util import module_from_spec,spec_from_file_location
from pathlib import Path
import os
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'data-pipeline'))
import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_io as io
import magnetic_line_survey_runtime as runtime


def plan(tmp_path):
    spec = spec_from_file_location('diagnostic_geometry_helper',Path(__file__).with_name('test_magnetic_line_survey_geometry.py'))
    helper = module_from_spec(spec)
    spec.loader.exec_module(helper)
    controls,_,_,request,request_root = helper.fixture(tmp_path)
    raw,metadata,ordinary = controls.control_input('S1')
    csv = tmp_path/'actual-original-s1.csv'
    csv.write_bytes(raw)
    inspection = core.inspect_geometry(csv,tmp_path/'s1-geometry',metadata['original'],metadata['rights'],
        metadata['acquisition']['line_dictionary'],metadata['acquisition']['sensor_dictionary'])
    metadata['schema']='magnetic-line-survey-input/1'
    metadata['acquisition']['line_dictionary'],metadata['acquisition']['sensor_dictionary']=inspection['dictionaries']
    metadata.update(arrays=inspection['arrays'],auxiliaries=[])
    request['dataset_version_sha256']=base.dataset_identity(metadata['original']['csv_sha256'],base.digest(metadata))
    request['channel_sha256']=ordinary['channel_sha256']
    request['split']['sealed_values_sha256']=ordinary['split']['sealed_values_sha256']
    request['split']['geometry_manifest_sha256']=inspection['geometry_sha256']
    scratch = tmp_path/'s1-worker'
    scratch.mkdir()
    path = scratch/'plan.json'
    path.write_bytes(base.canonical_bytes(dict(schema='m03-global-control-plan/1',mode='opened_s1_diagnostic',
        csv_path=str(csv),geometry_root=str(tmp_path/'s1-geometry'),inspection=inspection,metadata=metadata,
        request=request,request_root=str(request_root))))
    return path


@pytest.mark.skipif(sys.platform!='win32',reason='Actual Windows containment required')
def test_actual_all_inner_and_final_global_s1_keeps_predictive_failure(tmp_path):
    path = plan(tmp_path)
    receipt = runtime.run_worker(Path(sys.base_prefix)/'python.exe',Path(os.environ['GEOPHYSICS_EXISTING_PACKAGE_ROOT']),path.parent,path)
    assert receipt['verdict']=='component_pass',(receipt,(path.parent/'stderr.log').read_text())
    result = base.strict_json((path.parent/'fit'/'blocked-diagnostic.json').read_bytes())
    assert result['fit']['fit_count']==25 and result['evaluation_count']==1
    assert result['s1_predictive_verdict']=='fail' and result['field_acceptance']=='unresolved'
    assert result['physical_reference_admission']=='not_established'
    assert result['fit']['selected_depth_m']==500. and result['fit']['selected_damping']==.0001
    assert abs(result['rmse_nT']-18.799740861734186)<=1e-7*18.799740861734186
    assert abs(result['s1_threshold_nT']-.25966396538773057)<=1e-12
    assert receipt['total_processes']==1 and receipt['active_processes']==0
    reader = io.Reader(path.parent/'fit')
    refs = [result['fit'][key] for key in ('candidates','sources','column_scales','coefficients')]+result['outer_arrays']
    for ref in refs:
        reader.verify(ref)
    assert result['fit']['candidates']['rows']==24
    reader.reject_unknown(extra=('blocked-diagnostic.json',))
