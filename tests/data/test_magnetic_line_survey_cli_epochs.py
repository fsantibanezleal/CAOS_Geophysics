"""Closed explicit CLI policy dispatch; no new predictive or native assertion."""
from copy import deepcopy
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'data-pipeline'))
sys.path.insert(0,str(Path(__file__).parent))
import magnetic_line_contract as base
import magnetic_line_survey as core
from magnetic_line_survey_local_worker import decode_documents
from test_magnetic_line_survey_diagnostic import plan


def test_exact_original_documents_and_explicit_v2_pair(tmp_path):
    original=base.strict_json(plan(tmp_path).read_bytes())
    metadata,request=original['metadata'],original['request']
    first=base.canonical_bytes(metadata)
    second=base.canonical_bytes(request)
    assert decode_documents(first,second)==(metadata,request)
    new_metadata,new_request=deepcopy(metadata),deepcopy(request)
    new_metadata['schema']='magnetic-line-survey-input/2'
    new_request.update(schema='magnetic-line-survey-request/2',profile='m03-offline-stream/2')
    new_request['dataset_version_sha256']=base.dataset_identity(new_metadata['original']['csv_sha256'],base.digest(new_metadata))
    cfg=new_request['equivalent_sources']
    geometry=cfg.pop('source_geometry')
    cfg.update(source_geometries=[dict(geometry,block_e_m=width,block_n_m=width,max_sources=65536)
        for width in (400.,200.,100.,50.)],depth_candidates_m=[200.,500.],damping_candidates=[.0001,.01,1.,100.],
        candidate_order='width_descending_then_depth_then_damping_ascending',tie_break='larger_damping_then_depth_then_block_width')
    new_request['split']['tuning_candidate_order']='width_descending_then_depth_then_damping_ascending'
    assert decode_documents(base.canonical_bytes(new_metadata),base.canonical_bytes(new_request))==(new_metadata,new_request)
    for left,right in [(new_metadata,request),(metadata,new_request),([],request),(metadata,{})]:
        with pytest.raises(core.SurveyError):
            decode_documents(base.canonical_bytes(left),base.canonical_bytes(right))
    assert base.canonical_bytes(metadata)==first and base.canonical_bytes(request)==second
