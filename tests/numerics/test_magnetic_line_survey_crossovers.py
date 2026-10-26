"""Prospective disk-index crossover oracle and gap/height negatives."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'data-pipeline'))
import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_io as io
from magnetic_lines import crossovers


def fixture(tmp_path):
    spec = spec_from_file_location('crossing_original_controls', Path(__file__).parents[1]/'fixtures/magnetic_lines/generate.py')
    controls = module_from_spec(spec)
    spec.loader.exec_module(controls)
    raw, metadata, request = controls.geometry_input()
    source = tmp_path/'original.csv'
    source.write_bytes(raw)
    inspection = core.inspect_geometry(source, tmp_path/'geometry', metadata['original'], metadata['rights'],
        metadata['acquisition']['line_dictionary'], metadata['acquisition']['sensor_dictionary'])
    return controls, request, inspection


def test_global_spatial_index_keeps_all_original_candidate_pairs(tmp_path):
    from magnetic_line_survey_crossovers import geometry_crossovers
    controls, request, inspection = fixture(tmp_path)
    result = geometry_crossovers(tmp_path/'geometry', inspection, request['geometry_policy'],
                                 tmp_path/'crossovers', temp_root=tmp_path)
    ordinary = crossovers(controls.geometry_rows(), request['geometry_policy'])
    ref = result['table']
    actual = list(io.Reader(tmp_path/'crossovers').table(ref))
    assert result['candidates'] == len(ordinary) == len(actual)
    for new, old in zip(actual, ordinary, strict=True):
        for key in ('flight_segment_id','tie_segment_id','a','b','easting_m','northing_m',
                    'height_difference_m','time_separation_s','tolerance'):
            assert new[key] == old[key]
        assert 'missing_value' not in new['reasons']  # Measurement gate deferred.
        assert new['reasons'] == [r for r in old['reasons'] if r != 'missing_value']
    assert result['value_access'] == 'not_opened'


def test_candidate_limit_refuses_before_intersection_native_call(tmp_path, monkeypatch):
    import magnetic_line_survey_crossovers as module
    controls, request, inspection = fixture(tmp_path)
    monkeypatch.setattr(module, 'intersect_segments', lambda *a: pytest.fail('No native intersection before pair capacity'))
    with pytest.raises(core.SurveyError, match='resource_refused'):
        module.geometry_crossovers(tmp_path/'geometry', inspection, request['geometry_policy'],
                                   tmp_path/'crossovers', temp_root=tmp_path, candidate_limit=1)


def test_gap_and_height_rejected_pairs_are_not_deleted(tmp_path):
    from magnetic_line_survey_crossovers import geometry_crossovers
    _, request, inspection = fixture(tmp_path)
    policy = request['geometry_policy']
    policy['max_segment_gap_m'] = 1.
    policy['crossover']['max_height_separation_m'] = 0.
    result = geometry_crossovers(tmp_path/'geometry', inspection, policy, tmp_path/'crossovers', temp_root=tmp_path)
    actual = list(io.Reader(tmp_path/'crossovers').table(result['table']))
    assert actual and all(r['disposition'] == 'rejected' and 'gap' in r['reasons'] for r in actual)
    assert any('height_mismatch' in r['reasons'] for r in actual)
