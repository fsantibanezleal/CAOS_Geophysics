"""Explicit epoch boundaries; no old role relabel or large native allocation."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'data-pipeline'))
import magnetic_line_survey as core
import magnetic_line_survey_contract as v1
import magnetic_line_survey_contract_v2 as v2
import magnetic_line_survey_io as io
import magnetic_line_survey_representation as representation
from test_magnetic_line_survey_navigation import fixture, streamed_request


def test_explicit_axis_epoch_and_original_role_unchanged(tmp_path):
    root=tmp_path/'new'
    root.mkdir()
    identity=sha256(b'original-declared-east-axis').hexdigest()
    reference=representation.write_array(root,'east-axis','grid_axis',[-50.,0.,50.,100.],[4],'float64','m',identity)
    assert list(representation.Reader(root).cells(reference))==[-50.,0.,50.,100.]
    reader=representation.Reader(root)
    reader.verify(reference)
    reader.reject_unknown()
    with pytest.raises(core.SurveyError,match='invalid_contract'):
        v1.validate('ArrayRef',reference)
    with pytest.raises(core.SurveyError,match='invalid_contract'):
        io.Reader(root).verify(reference)
    wrong=deepcopy(reference)
    wrong['role']='grid_coordinate'
    with pytest.raises(core.SurveyError,match='invalid_contract'):
        v2.validate('ArrayRef',wrong)
    original_root=tmp_path/'original'
    original_root.mkdir()
    original=io.write_array(original_root,'original-row','row_id',['r0','r1'],[2],'ascii64','identity',
                            sha256(b'r0'.ljust(64,b'\0')+b'r1'.ljust(64,b'\0')).hexdigest())
    assert list(representation.Reader(original_root).cells(original))==['r0','r1']
    assert v1.validate('ArrayRef',original)==v2.validate('ArrayRef',original)


def test_dimensionless_transfer_and_navigation_row_caps_without_allocation(tmp_path):
    root=tmp_path/'new'
    root.mkdir()
    identity=sha256(b'geometry-only-cap-test').hexdigest()
    transfer=representation.write_array(root,'transfer','microlevel_transfer',[[0.,.5],[.5,1.]],
        [2,2],'float64','dimensionless',identity)
    assert list(representation.Reader(root).cells(transfer))==[0.,.5,.5,1.]
    wrong=deepcopy(transfer)
    wrong['unit']='nT'
    with pytest.raises(core.SurveyError,match='invalid_contract'):
        v2.validate('ArrayRef',wrong)
    navigation=deepcopy(transfer)
    navigation.update(array_id='nav',role='navigation',shape=[16000000,3],unit='m',
        manifest=dict(name='array-nav.json',bytes=1,sha256='0'*64))
    assert v2.validate('ArrayRef',navigation)['shape']==[16000000,3]
    with pytest.raises(core.SurveyError,match='invalid_contract'):
        v1.validate('ArrayRef',navigation)
    navigation['shape']=[16000001,3]
    with pytest.raises(core.SurveyError):
        v2.validate('ArrayRef',navigation)
    transfer['shape']=[2048,2049]
    with pytest.raises(core.SurveyError):
        v2.validate('ArrayRef',transfer)


def test_new_padding_matches_unchanged_ordinary_formula(tmp_path):
    _,metadata,_,inspection,lag,ordinary,_=fixture(tmp_path)
    request=streamed_request(tmp_path/'request',ordinary,metadata,inspection,lag)
    grid=deepcopy(request['grid'])
    grid['boundary_policy'].update(mode='zero_pad',pad_e_cells=grid['nx']//2,pad_n_cells=grid['ny']//2)
    assert v2.validate('SurveyGrid',grid)==grid
    grid['boundary_policy']['pad_e_cells']+=1
    # Existing historical parser remains unchanged, not silently repaired.
    assert v1.validate('SurveyGrid',grid)==grid
    with pytest.raises(core.SurveyError,match='resource_refused'):
        v2.validate('SurveyGrid',grid)
