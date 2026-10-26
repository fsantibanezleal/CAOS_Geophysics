"""Support oracle: exact closed hull and nearest-training distance, no values."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'data-pipeline'))
import magnetic_line_survey as core
import magnetic_line_survey_io as io
from magnetic_line_validation import _coverage


def fixture(tmp_path):
    spec = spec_from_file_location('support_geometry_controls', Path(__file__).with_name('test_magnetic_line_survey_geometry.py'))
    controls = module_from_spec(spec)
    spec.loader.exec_module(controls)
    generator, ordinary, inspected, request, request_root = controls.fixture(tmp_path)
    from magnetic_line_survey_geometry import plan_partitions
    planned = plan_partitions(tmp_path/'geometry', inspected, request, request_root, tmp_path/'partitions',temp_root=tmp_path)
    return generator, inspected, request, planned


def test_disk_hull_and_validation_support_match_original(tmp_path, monkeypatch):
    from magnetic_line_survey_support import plan_support
    generator, inspection, request, planned = fixture(tmp_path)
    monkeypatch.setattr(core, 'engines', lambda: pytest.fail('Support seal cannot open numerical engines/values'))
    result = plan_support(tmp_path/'geometry', inspection, request, tmp_path/'partitions', planned,
                          tmp_path/'support',temp_root=tmp_path)
    reader = io.Reader(tmp_path/'support')
    indexes = io.Reader(tmp_path/'partitions')
    rows = generator.geometry_rows()
    for actual, part in zip(result['partitions'],planned['partitions'], strict=True):
        training = [rows[i] for i in indexes.cells(part['training'])]
        validation = [rows[i] for i in indexes.cells(part['validation'])]
        expected,_ = _coverage(training,validation,request['grid']['support_radius_m'])
        masks = list(reader.cells(actual['validation_mask']))
        assert sum(value == 0 for value in masks) == expected['eligible_count']
        assert actual['coverage'] == expected['fraction']
    assert result['value_access'] == 'not_opened'
    from magnetic_lines import support_masks
    # Only the geometry part of the ordinary oracle is compared here. The
    # authored placeholder is not a field measurement or predictive control.
    geometric_rows = [dict(row,magnetic_nT=1.) for row in rows]
    training = [geometric_rows[i] for i in indexes.cells(planned['partitions'][0]['training'])]
    expected = support_masks(geometric_rows,training,request['grid'],request['geometry_policy'],sensor_id=request['sensor_id'])
    assert result['sampling_resolved'] == expected['sampling_resolved']
    assert all(bool(mask & (1<<12)) == (not expected['sampling_resolved']) for mask in reader.cells(result['grid_mask']))


def test_spectrum_cannot_claim_geometry_support_through_holes(tmp_path):
    from magnetic_line_survey_support import plan_support
    _, inspection, request, planned = fixture(tmp_path)
    request['grid']['origin_e_m'] = 1e7
    request['grid']['origin_n_m'] = 1e7
    from magnetic_line_survey_geometry import plan_partitions
    planned = plan_partitions(tmp_path/'geometry',inspection,request,tmp_path/'request',
                               tmp_path/'new-partitions',temp_root=tmp_path)
    result = plan_support(tmp_path/'geometry',inspection,request,tmp_path/'new-partitions',planned,
                          tmp_path/'support',temp_root=tmp_path)
    mask = list(io.Reader(tmp_path/'support').cells(result['grid_mask']))
    assert mask and all(value & (1 << 10) for value in mask)
    assert result['spectrum_geometrically_qualified'] is False


def test_original_ordinal_gap_keeps_grid_tube_mask_not_cv_hole(tmp_path):
    from magnetic_line_survey_support import plan_support
    from magnetic_line_survey_geometry import plan_partitions
    from hashlib import sha256
    spec = spec_from_file_location('gap_fixture',Path(__file__).parents[1]/'fixtures/magnetic_lines/generate.py')
    controls = module_from_spec(spec)
    spec.loader.exec_module(controls)
    rows = controls.geometry_rows()
    for row in rows:
        if row['line_id']=='F00' and row['ordinal']>=16:
            row['ordinal'] += 1
    # Reuse the independently fixed request/dictionaries, with exact new raw
    # and geometry identity. No magnetic values exist in this control.
    helper_spec = spec_from_file_location('gap_geometry_helper',Path(__file__).with_name('test_magnetic_line_survey_geometry.py'))
    helper = module_from_spec(helper_spec)
    helper_spec.loader.exec_module(helper)
    _,_,old,request,request_root = helper.fixture(tmp_path)
    _,metadata,_ = controls.geometry_input()
    raw = controls.csv_bytes(rows)
    source = tmp_path/'gap.csv'
    source.write_bytes(raw)
    metadata['original'].update(csv_sha256=sha256(raw).hexdigest(),csv_bytes=len(raw))
    inspection = core.inspect_geometry(source,tmp_path/'gap-geometry',metadata['original'],metadata['rights'],
        metadata['acquisition']['line_dictionary'],metadata['acquisition']['sensor_dictionary'])
    request['split']['geometry_manifest_sha256'] = inspection['geometry_sha256']
    planned = plan_partitions(tmp_path/'gap-geometry',inspection,request,request_root,tmp_path/'gap-partitions',temp_root=tmp_path)
    result = plan_support(tmp_path/'gap-geometry',inspection,request,tmp_path/'gap-partitions',planned,
                          tmp_path/'gap-support',temp_root=tmp_path)
    assert any(mask & (1<<4) for mask in io.Reader(tmp_path/'gap-support').cells(result['grid_mask']))
    assert all(p['coverage']==1 for p in result['partitions'])
