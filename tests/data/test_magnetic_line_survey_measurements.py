"""Measurement decode is separate from unopened geometry inspection."""
from hashlib import sha256
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'data-pipeline'))
import magnetic_line_survey as core
import magnetic_line_survey_io as io


def control(tmp_path, count=8201, value='NaN'):
    spec = spec_from_file_location('original_survey_intake_controls', Path(__file__).with_name('test_magnetic_line_survey.py'))
    controls = module_from_spec(spec)
    spec.loader.exec_module(controls)
    args = controls.intake_args(tmp_path, controls.raw_rows(count, value=value))
    inspection = core.inspect_geometry(*args)
    return args, inspection


def test_original_8201_negative_is_not_field_measurement_acceptance(tmp_path):
    from magnetic_line_survey_measurements import decode_measurements
    args, inspection = control(tmp_path)
    assert inspection['rows'] == 8201 and inspection['value_access'] == 'not_opened'
    with pytest.raises(core.SurveyError, match='metadata_ineligible'):
        decode_measurements(args[0], args[1], inspection, tmp_path/'measurements')


def test_measurement_second_pass_retains_ids_masks_and_original_bytes(tmp_path):
    from magnetic_line_survey_measurements import decode_measurements
    args, inspection = control(tmp_path, count=7, value='')
    # The original control deliberately carries invalid sigma too; this second
    # independently authored input makes sigma missing, not an invented error.
    raw = args[0].read_bytes().replace(b'Infinity', b'')
    other = tmp_path/'other'
    other.mkdir()
    spec = spec_from_file_location('measurement_intake_controls', Path(__file__).with_name('test_magnetic_line_survey.py'))
    controls = module_from_spec(spec)
    spec.loader.exec_module(controls)
    arguments = controls.intake_args(other, raw)
    inspected = core.inspect_geometry(*arguments)
    result = decode_measurements(arguments[0], arguments[1], inspected, tmp_path/'measurements')
    reader = io.Reader(tmp_path/'measurements')
    refs = {r['role']:r for r in result['arrays']}
    assert list(reader.cells(refs['magnetic'])) == [0.]*7
    assert list(reader.cells(refs['uncertainty'])) == [0.]*7
    assert list(reader.cells(refs['missing_mask'])) == [48]*7
    assert refs['magnetic']['mask_array_id'] == 'measurement-missing'
    assert result['original'] == arguments[2] and arguments[0].read_bytes() == raw
    reader.reject_unknown(extra=('measurement-pass.json',))


def test_original_change_after_geometry_refuses_before_measurement_result(tmp_path):
    from magnetic_line_survey_measurements import decode_measurements
    args, inspection = control(tmp_path, count=5, value='1')
    args[0].write_bytes(args[0].read_bytes().replace(b',1,Infinity,', b',2,,', 1))
    with pytest.raises(core.SurveyError, match='custody_mismatch'):
        decode_measurements(args[0], args[1], inspection, tmp_path/'measurements')
