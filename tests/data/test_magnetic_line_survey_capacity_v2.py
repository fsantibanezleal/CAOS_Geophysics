"""Integer-only prospective refusal controls; no target/outer/native allocation."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'data-pipeline'))
import magnetic_line_survey as core
from magnetic_line_survey_capacity_v2 import plan_capacity


def test_all_96_shapes_and_unknown_final_bound(monkeypatch):
    monkeypatch.setattr(core,'engines',lambda:pytest.fail('No native import before proof'))
    n=[100,60,55,50]
    v=[20,15,16,17]
    m=[[10,6,5,4],[20,12,10,8],[40,24,20,16],[80,48,40,32]]
    capacity,proof=plan_capacity(120,n,v,m,exported_cells=100,fft_cells=100,
        retained_member_bytes=50000,retained_index_bytes=30000,logical_members=150,arrays=100,dictionaries=10)
    assert proof['mandatory_fit_count']==proof['maximum_fit_count']==97
    assert sum(shape['fit_count'] for shape in proof['inner_shapes'])==96
    assert len({(s['source_geometry_index'],s['fold_index']) for s in proof['inner_shapes']})==12
    expected_inner=sum(8*4004*n[f]*m[g][f] for g in range(4) for f in range(1,4))
    expected_scores=sum(8*v[f]*m[g][f] for g in range(4) for f in range(1,4))
    expected_final=4004*n[0]*80
    assert capacity['kernel_pair_bound']==expected_inner+expected_scores+expected_final+(20+100)*80
    assert proof['final_fit_pairs']==expected_final
    assert proof['map_bytes']==sum(16*n[f]+24*m[g][f] for g in range(4) for f in range(4))
    assert capacity['resource_state']=='unmeasured'
    optional,extra=plan_capacity(120,n,v,m,exported_cells=100,fft_cells=100,comparator=True)
    assert extra['maximum_fit_count']==98 and extra['mandatory_fit_count']==97
    assert optional['kernel_pair_bound']==capacity['kernel_pair_bound']+expected_final+120*80


@pytest.mark.parametrize('field,value',[
    ('auxiliary_rows',16000001),('crossover_candidates',8000001),('exported_cells',1048577),
    ('fft_cells',4194305),('raw_bytes',4294967297),('auxiliary_bytes',4294967297),
    ('logical_members',193),('arrays',129),('dictionaries',17),('retained_index_bytes',34359738368),
    ('retained_member_bytes',34359738368),('comparator',1),
])
def test_unchanged_caps_refuse_without_native(field,value,monkeypatch):
    monkeypatch.setattr(core,'engines',lambda:pytest.fail('Refusal must precede import'))
    with pytest.raises(core.SurveyError):
        plan_capacity(120,[100,60,55,50],[20,15,16,17],[[10,6,5,4]]*4,**{field:value})


def test_invalid_shapes_and_actual_pair_ceiling(monkeypatch):
    monkeypatch.setattr(core,'engines',lambda:pytest.fail('Refusal must precede import'))
    with pytest.raises(core.SurveyError):
        plan_capacity(120,[100,60,55,50],[20,15,16,17],[[101,6,5,4]]*4)
    with pytest.raises(core.SurveyError):
        plan_capacity(120,[100,60,55,50],[21,15,16,17],[[10,6,5,4]]*4)
    with pytest.raises(core.SurveyError,match='resource_refused'):
        plan_capacity(1000000,[800000]*4,[200000]*4,[[65536]*4]*4)
