"""Actual original S2 fold brackets; no full-survey calibration leakage."""
from importlib.util import module_from_spec,spec_from_file_location
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'data-pipeline'))
import magnetic_line_survey as core
import magnetic_line_survey_io as io


def fixture(tmp_path):
    spec = spec_from_file_location('value_crossover_helper',Path(__file__).parents[1]/'data/test_magnetic_line_survey_geometry.py')
    helper = module_from_spec(spec)
    spec.loader.exec_module(helper)
    controls,_,_,request,request_root = helper.fixture(tmp_path)
    raw,metadata,ordinary = controls.control_input('S2')
    csv = tmp_path/'s2-original.csv'
    csv.write_bytes(raw)
    inspection = core.inspect_geometry(csv,tmp_path/'s2-geometry',metadata['original'],metadata['rights'],
        metadata['acquisition']['line_dictionary'],metadata['acquisition']['sensor_dictionary'])
    request['split']['geometry_manifest_sha256']=inspection['geometry_sha256']
    from magnetic_line_survey_geometry import plan_partitions
    planned = plan_partitions(tmp_path/'s2-geometry',inspection,request,request_root,tmp_path/'partitions',temp_root=tmp_path)
    from magnetic_line_survey_crossovers import geometry_crossovers
    crossed = geometry_crossovers(tmp_path/'s2-geometry',inspection,request['geometry_policy'],tmp_path/'crossovers',temp_root=tmp_path)
    from magnetic_line_survey_measurements import decode_measurements
    measured = decode_measurements(csv,tmp_path/'s2-geometry',inspection,tmp_path/'measurements')
    return controls,metadata,ordinary,inspection,request,planned,crossed,measured


def test_fold_crossover_values_match_actual_original_s2(tmp_path):
    from magnetic_line_survey_crossover_values import crossover_values
    from magnetic_lines import crossovers
    from magnetic_line_validation import make_partitions
    control,metadata,ordinary,inspection,request,planned,crossed,measured = fixture(tmp_path)
    result = crossover_values(tmp_path/'s2-geometry',inspection,request['geometry_policy'],tmp_path/'crossovers',crossed,
        tmp_path/'partitions',planned['partitions'][0]['training'],tmp_path/'measurements',measured,metadata['uncertainty'],
        tmp_path/'values',temp_root=tmp_path)
    expected_parts = make_partitions(control.control_rows('S2'),ordinary)
    expected = crossovers(control.control_rows('S2'),ordinary['geometry_policy'],expected_parts['outer_training_ids'],metadata['uncertainty'])
    actual = list(io.Reader(tmp_path/'values').table(result['table']))
    assert actual==expected
    assert result['admitted_constraints']>0
    from magnetic_line_survey_crossover_values import incidence_constraints
    from magnetic_line_survey_leveling import solve_incidence
    from magnetic_lines import level_offsets
    solved = solve_incidence(incidence_constraints(tmp_path/'s2-geometry',inspection,tmp_path/'values',result,temp_root=tmp_path),
                             'unweighted',temp_root=tmp_path)
    original = level_offsets(control.control_rows('S2'),ordinary['geometry_policy'],expected_parts['outer_training_ids'],'unweighted',metadata['uncertainty'])
    assert max(abs(solved['offsets'][key]-value) for key,value in original['offsets'].items())<=1e-9


def test_original_empty_inner_a_calibration_stays_empty_and_ineligible(tmp_path):
    from magnetic_line_survey_crossover_values import crossover_values
    from magnetic_line_survey_leveling import solve_incidence
    _,metadata,_,inspection,request,planned,crossed,measured = fixture(tmp_path)
    result = crossover_values(tmp_path/'s2-geometry',inspection,request['geometry_policy'],tmp_path/'crossovers',crossed,
        tmp_path/'partitions',planned['partitions'][1]['training'],tmp_path/'measurements',measured,metadata['uncertainty'],
        tmp_path/'values',temp_root=tmp_path)
    assert result['admitted_constraints']==0
    from magnetic_line_survey_crossover_values import incidence_constraints
    with pytest.raises(core.SurveyError,match='metadata_ineligible'):
        solve_incidence(incidence_constraints(tmp_path/'s2-geometry',inspection,tmp_path/'values',result,temp_root=tmp_path),
                        'unweighted',temp_root=tmp_path)
