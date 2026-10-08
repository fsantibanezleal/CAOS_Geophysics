"""All approved v2 fits on unchanged opened original S3, never field success."""
from copy import deepcopy
import itertools
import os
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'data-pipeline'))
sys.path.insert(0,str(Path(__file__).parent))
import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_representation as representation
import magnetic_line_survey_runtime as runtime
import magnetic_line_survey_result as results
from magnetic_line_survey_physical_fit import select_resolution_candidate
from test_magnetic_line_survey_corrections import full_case


def test_resolution_selection_requires_all32_complete_training_averages():
    candidates=[dict(source_geometry_index=g,depth_m=depth,damping=damping,mean_rmse_nT=7.)
        for g,depth,damping in itertools.product(range(4),(200.,500.),(.0001,.01,1.,100.))]
    selected=select_resolution_candidate(candidates)
    assert (selected['source_geometry_index'],selected['depth_m'],selected['damping'])==(0,500.,100.)
    better=deepcopy(candidates)
    better[24]['mean_rmse_nT']=0.
    assert select_resolution_candidate(better)==better[24]
    for wrong in (candidates[:-1],list(reversed(candidates)),[candidates[0]]*32):
        with pytest.raises(core.SurveyError):
            select_resolution_candidate(wrong)
    for value in (None,True,float('nan'),float('inf'),-1.):
        wrong=deepcopy(candidates)
        wrong[0]['mean_rmse_nT']=value
        with pytest.raises(core.SurveyError):
            select_resolution_candidate(wrong)


def test_actual_all96_inner_and_final_resolution_dag_result(tmp_path):
    # Existing opened S3 instrument control and its original generator bytes;
    # no new physics, truth read, untouched label or source-specific retuning.
    metadata,_,inspection,_,request,_,_,roots,definitions=full_case(tmp_path)
    metadata['schema']='magnetic-line-survey-input/2'
    request.update(schema='magnetic-line-survey-request/2',profile='m03-offline-stream/2')
    request['dataset_version_sha256']=base.dataset_identity(metadata['original']['csv_sha256'],base.digest(metadata))
    cfg=request['equivalent_sources']
    geometry=cfg.pop('source_geometry')
    cfg.update(source_geometries=[dict(geometry,block_e_m=width,block_n_m=width,max_sources=65536) for width in (400.,200.,100.,50.)],
        depth_candidates_m=[200.,500.],damping_candidates=[.0001,.01,1.,100.],
        candidate_order='width_descending_then_depth_then_damping_ascending',tie_break='larger_damping_then_depth_then_block_width')
    request['split']['tuning_candidate_order']='width_descending_then_depth_then_damping_ascending'
    worker=tmp_path/'worker'
    worker.mkdir()
    plan=dict(schema='m03-resolution-fit-plan/1',csv_path=str(tmp_path/'s3-original.csv'),
        geometry_root=str(tmp_path/'geometry'),inspection=inspection,metadata=metadata,request=request,
        request_root=str(tmp_path/'request'),navigation_root=str(tmp_path/'navigation'),
        auxiliary_roots={key:str(value) for key,value in roots.items()},reference_definitions=definitions,
        run_id='opened-original-s3-resolution-v2')
    path=worker/'plan.json'
    path.write_bytes(base.canonical_bytes(plan))
    lifetime=runtime.run_worker(Path(sys.base_prefix)/'python.exe',Path(os.environ['GEOPHYSICS_EXISTING_PACKAGE_ROOT']),worker,path)
    assert lifetime['verdict']=='component_pass',(lifetime,(worker/'stdout.log').read_text(),(worker/'stderr.log').read_text())
    assert lifetime['total_processes']==1 and lifetime['active_processes']==0
    result=base.strict_json((worker/'result/result.json').read_bytes())
    ready=base.strict_json((worker/'resolution-fit-ready.json').read_bytes())
    assert ready['full_result']=='assembled' and ready['outer_status']=='opened_authored_diagnostic'
    assert result['policy_epoch']=='resolution_v2' and result['fit']['fit_count']==97
    assert result['inventory']['original_rows']==363 and result['partitions']['evaluation_count']==1
    assert result['geometry']['schema']=='magnetic-line-survey-geometry/2' and len(result['geometry']['source_maps'])==16
    assert result['fit']['candidates']['row_schema']=='candidate_fit_v2'
    reader=representation.Reader(worker/'result')
    candidates=list(reader.table(result['fit']['candidates']))
    assert len(candidates)==96 and all(row['verdict']['overall']=='pass' for row in candidates)
    assert result['verdict']['overall']=='unresolved' and result['evaluation']['verdict']['overall']=='unresolved'
    assert len(result['channels'])==5 and len(result['grid'])==2
    proof=base.strict_json((worker/'sealed/resolution-capacity-proof.json').read_bytes())
    assert proof['proof']['mandatory_fit_count']==97 and proof['proof']['logical_members']<=192
    assert (worker/'resolution-prevalue-verification.json').stat().st_mtime_ns<=(worker/'measurements/measurement-pass.json').stat().st_mtime_ns
    verified=results.verify_result(worker/'result',temp_root=tmp_path)
    assert verified['custody_and_semantics']=='pass' and verified['logical_members']<=192
    for change in ('epoch','fit_count','selected_geometry','source_counts'):
        wrong=deepcopy(result)
        if change=='epoch':wrong['policy_epoch']='fixed_basis_v1'
        elif change=='fit_count':wrong['fit']['fit_count']=25
        elif change=='selected_geometry':wrong['fit']['selected_source_geometry_index']=(wrong['fit']['selected_source_geometry_index']+1)%4
        else:wrong['geometry']['source_counts_by_geometry'][0][0]+=1
        with pytest.raises(core.SurveyError):
            results.verify_result(worker/'result',wrong,temp_root=tmp_path,allow_uncommitted=True)
