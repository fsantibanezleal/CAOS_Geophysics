"""Global incidence calibration: original gauges and independent dense oracle."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'data-pipeline'))
import magnetic_line_survey as core


def test_sparse_offsets_match_original_weighted_global_graph(tmp_path):
    from magnetic_line_survey_leveling import solve_incidence
    from magnetic_lines import solve_offsets
    edges = [dict(flight='F0',tie='T0',difference_nT=2.,variance_nT2=.3),
             dict(flight='F1',tie='T0',difference_nT=-3.,variance_nT2=.7),
             dict(flight='F0',tie='T1',difference_nT=1.6,variance_nT2=.2),
             dict(flight='F1',tie='T1',difference_nT=-3.3,variance_nT2=.5)]
    expected = solve_offsets(edges,'admitted_inverse_variance')
    actual = solve_incidence(iter(edges),'admitted_inverse_variance',temp_root=tmp_path)
    assert actual['components'][0]['gauge_line_id']=='T0'
    assert actual['components'][0]['rank']==3 and actual['components'][0]['absolute_datum'] is False
    assert max(abs(actual['offsets'][key]-value) for key,value in expected['offsets'].items())<=1e-9
    assert max(abs(a-b) for a,b in zip(actual['residuals'],expected['residuals'],strict=True))<=1e-9


def test_disconnected_components_keep_separate_gauges_not_common_datum(tmp_path):
    from magnetic_line_survey_leveling import solve_incidence
    edges = [dict(flight='F0',tie='T0',difference_nT=2.,variance_nT2=None),
             dict(flight='F1',tie='T1',difference_nT=-3.,variance_nT2=None)]
    actual = solve_incidence(iter(edges),'unweighted',temp_root=tmp_path)
    assert len(actual['components'])==2 and actual['common_relative_gauge'] is False
    assert actual['offsets']['T0']==actual['offsets']['T1']==0.


def test_empty_actual_fold_and_unknown_sigma_refuse_unchanged(tmp_path):
    from magnetic_line_survey_leveling import solve_incidence
    with pytest.raises(core.SurveyError,match='metadata_ineligible'):
        solve_incidence(iter([]),'unweighted',temp_root=tmp_path)
    with pytest.raises(core.SurveyError,match='metadata_ineligible'):
        solve_incidence(iter([dict(flight='F0',tie='T0',difference_nT=2.,variance_nT2=None)]),
                        'admitted_inverse_variance',temp_root=tmp_path)


def test_max_plus_one_edges_refuse_before_numerical_import(tmp_path,monkeypatch):
    from magnetic_line_survey_leveling import solve_incidence
    monkeypatch.setattr(core,'engines',lambda:pytest.fail('Overflow must refuse before import'))
    edge = dict(flight='F0',tie='T0',difference_nT=2.,variance_nT2=None)
    with pytest.raises(core.SurveyError,match='resource_refused'):
        solve_incidence(iter([edge,edge]),'unweighted',temp_root=tmp_path,edge_limit=1)


def test_unknown_weight_and_line_role_does_not_silently_qualify(tmp_path,monkeypatch):
    from magnetic_line_survey_leveling import solve_incidence
    monkeypatch.setattr(core,'engines',lambda:pytest.fail('Malformed graph must precede import'))
    edge = dict(flight='F0',tie='F0',difference_nT=2.,variance_nT2=None)
    with pytest.raises(core.SurveyError,match='invalid_contract'):
        solve_incidence(iter([edge]),'unweighted',temp_root=tmp_path)
    with pytest.raises(core.SurveyError,match='invalid_contract'):
        solve_incidence(iter([]),'normalized_weights',temp_root=tmp_path)
