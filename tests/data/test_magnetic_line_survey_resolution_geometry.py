"""Actual value-free sixteen-map seal; no numerical/outer acceptance claim."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'data-pipeline'))
sys.path.insert(0,str(Path(__file__).parent))
import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_representation as representation
from magnetic_line_survey_resolution_geometry import seal_resolution_geometry,verify_resolution_geometry
from test_magnetic_line_survey_navigation import fixture,streamed_request


def test_actual_363row_prevalue_resolution_seal_all16maps(tmp_path,monkeypatch):
    _,metadata,_,inspection,lag,ordinary,_=fixture(tmp_path)
    request=streamed_request(tmp_path/'request',ordinary,metadata,inspection,lag)
    metadata['schema']='magnetic-line-survey-input/2'
    request.update(schema='magnetic-line-survey-request/2',profile='m03-offline-stream/2')
    request['dataset_version_sha256']=base.dataset_identity(metadata['original']['csv_sha256'],base.digest(metadata))
    cfg=request['equivalent_sources']
    geometry=cfg.pop('source_geometry')
    cfg.update(source_geometries=[dict(geometry,block_e_m=width,block_n_m=width,max_sources=65536) for width in (400.,200.,100.,50.)],
        candidate_order='width_descending_then_depth_then_damping_ascending',tie_break='larger_damping_then_depth_then_block_width',
        depth_candidates_m=[200.,500.],damping_candidates=[.0001,.01,1.,100.])
    request['split']['tuning_candidate_order']='width_descending_then_depth_then_damping_ascending'
    monkeypatch.setattr(core,'engines',lambda:pytest.fail('No numerical engine before fresh value-free seal'))
    from magnetic_line_survey_measurements import decode_measurements
    monkeypatch.setattr('magnetic_line_survey_measurements.decode_measurements',lambda *a,**k:pytest.fail('No magnetic values before seal'))
    assert callable(decode_measurements)
    original=sha256((tmp_path/'s3-original.csv').read_bytes()).hexdigest()
    receipt=seal_resolution_geometry(tmp_path/'geometry',inspection,metadata,request,tmp_path/'request',tmp_path/'resolution',
        temp_root=tmp_path,navigation_root=tmp_path/'navigation')
    seal=receipt['geometry']
    assert seal['value_access']=='not_opened' and receipt['actual_numerical_fit_count']==0
    assert seal['schema']=='magnetic-line-survey-geometry/2' and len(seal['source_maps'])==16
    reader=representation.Reader(tmp_path/'resolution')
    proof=base.strict_json(reader.member(receipt['capacity_proof']))
    assert proof['proof']['mandatory_fit_count']==proof['proof']['maximum_fit_count']==97
    assert sum(item['fit_count'] for item in proof['proof']['inner_shapes'])==96
    assert proof['request_sha256']==base.digest(request) and proof['value_access']=='not_opened'
    assert len(seal['arrays'])<=128 and len(seal['dictionaries'])<=16 and proof['proof']['logical_members']<=192
    assert proof['capacity']['kernel_pair_bound']==sum(proof['proof'][key] for key in (
        'inner_fit_pairs','inner_prediction_pairs','final_fit_pairs','final_prediction_pairs','final_verification_pairs','comparator_pairs'))
    for item in seal['source_maps']:
        g=item['source_geometry_index']
        fold=['final','A','B','C'].index(item['fold_id'])
        assert item['sources']['shape'][0]==seal['source_counts_by_geometry'][g][fold]
        indexes=list(reader.cells(item['training']))
        cells=list(reader.cells(item['source_members']))
        assert cells[::2]==indexes and all(0<=source<item['sources']['shape'][0] for source in cells[1::2])
        assert item['source_members']['ordered_ids_sha256']==item['training']['ordered_ids_sha256']
    assert sha256((tmp_path/'s3-original.csv').read_bytes()).hexdigest()==original
    assert receipt['partitions']['request_sha256']==base.digest(request)
    assert all(set(part)=={'fold_id','training','validation','exclusions'} for part in receipt['partitions']['partitions'])
    wrong=deepcopy(request)
    wrong['equivalent_sources']['source_geometries'][1]['block_e_m']=123.
    with pytest.raises(core.SurveyError):
        seal_resolution_geometry(tmp_path/'geometry',inspection,metadata,wrong,tmp_path/'request',tmp_path/'bad',
            temp_root=tmp_path,navigation_root=tmp_path/'navigation')
    assert not (tmp_path/'bad').exists()
    verification=verify_resolution_geometry(tmp_path/'geometry',inspection,metadata,request,tmp_path/'request',
        tmp_path/'resolution',receipt,temp_root=tmp_path,navigation_root=tmp_path/'navigation')
    assert verification['capacity_and_maps']=='pass' and verification['source_maps']==16
    assert verification['source_counts_by_geometry']==seal['source_counts_by_geometry']
    assert verification['actual_numerical_fit_count']==0 and verification['mandatory_fit_count']==97
    for field,value in [('value_access','opened'),('actual_numerical_fit_count',97),('native_admission','pass')]:
        wrong=deepcopy(receipt)
        wrong[field]=value
        with pytest.raises(core.SurveyError):
            verify_resolution_geometry(tmp_path/'geometry',inspection,metadata,request,tmp_path/'request',
                tmp_path/'resolution',wrong,temp_root=tmp_path,navigation_root=tmp_path/'navigation')
