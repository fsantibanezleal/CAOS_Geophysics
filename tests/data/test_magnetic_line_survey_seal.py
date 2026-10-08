"""Complete no-lag geometry seal binds all value-free producer stages."""
from copy import deepcopy
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'data-pipeline'))
import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_contract as schema
import magnetic_line_survey_io as io


def fixture(tmp_path):
    spec = spec_from_file_location('sealed_geometry_controls',Path(__file__).with_name('test_magnetic_line_survey_geometry.py'))
    helper = module_from_spec(spec)
    spec.loader.exec_module(helper)
    controls,_,inspection,request,request_root = helper.fixture(tmp_path)
    _,metadata,_ = controls.geometry_input()
    metadata['schema'] = 'magnetic-line-survey-input/1'
    metadata['acquisition']['line_dictionary'],metadata['acquisition']['sensor_dictionary'] = inspection['dictionaries']
    metadata.update(arrays=inspection['arrays'],auxiliaries=[])
    request['dataset_version_sha256'] = base.dataset_identity(inspection['original']['csv_sha256'],base.digest(metadata))
    return metadata,inspection,request,request_root


def test_complete_geometry_seal_is_closed_and_value_free(tmp_path,monkeypatch):
    from magnetic_line_survey_seal import seal_geometry
    metadata,inspection,request,request_root = fixture(tmp_path)
    # Native intersection is allowed after pair capacity; values remain absent.
    result = seal_geometry(tmp_path/'geometry',inspection,metadata,request,request_root,tmp_path/'sealed',temp_root=tmp_path)
    seal = schema.validate('GeometrySeal',result['geometry'])
    assert seal['value_access']=='not_opened' and seal['rows']==363
    from magnetic_line_validation import make_partitions
    spec = spec_from_file_location('independent_seal_oracle',Path(__file__).parents[1]/'fixtures/magnetic_lines/generate.py')
    control = module_from_spec(spec)
    spec.loader.exec_module(control)
    _,_,ordinary = control.geometry_input()
    expected = make_partitions(control.geometry_rows(),ordinary)
    assert seal['source_counts']==[len(expected['outer_source_positions'])]+[len(f['source_positions']) for f in expected['inner']]
    from magnetic_lines import reference_coordinates_sha256
    assert seal['coordinates_sha256']==reference_coordinates_sha256(control.geometry_rows(),metadata['coordinates']['vertical_datum'])
    assert seal['crossover_candidates'] > 0 and seal['segments'] == 352
    reader = io.Reader(tmp_path/'sealed')
    for ref in seal['arrays']+seal['dictionaries']:
        reader.verify(ref)
    reader.reject_unknown(extra=('geometry-seal.json',))


def test_datum_and_acquisition_policy_cannot_be_silently_defaulted(tmp_path):
    from magnetic_line_survey_seal import seal_geometry
    metadata,inspection,request,request_root = fixture(tmp_path)
    request['geometry_policy']['max_segment_gap_m']=metadata['acquisition']['max_segment_gap_m']+1
    with pytest.raises(core.SurveyError,match='metadata_ineligible'):
        seal_geometry(tmp_path/'geometry',inspection,metadata,request,request_root,tmp_path/'sealed',temp_root=tmp_path)


def test_provider_grid_is_not_relabelled_as_flight_lines(tmp_path):
    from magnetic_line_survey_seal import seal_geometry
    metadata,inspection,request,request_root = fixture(tmp_path)
    metadata['source_kind']='provider_grid'
    metadata['authored_control']=None
    with pytest.raises(core.SurveyError,match='metadata_ineligible'):
        seal_geometry(tmp_path/'geometry',inspection,metadata,request,request_root,tmp_path/'sealed',temp_root=tmp_path)
