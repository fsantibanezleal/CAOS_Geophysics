"""Original S3 full-row reference custody and independent source reconstruction."""
from copy import deepcopy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'data-pipeline'))
sys.path.insert(0, str(Path(__file__).parent))
import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_io as io
from test_magnetic_line_survey_navigation import fixture, streamed_request


def full_reference(tmp_path):
    from magnetic_line_survey_seal import seal_geometry
    _, metadata, ordinary_metadata, inspection, lag, ordinary, _ = fixture(tmp_path)
    request = streamed_request(tmp_path/'request', ordinary, metadata, inspection, lag)
    sealed = seal_geometry(tmp_path/'geometry', inspection, metadata, request, tmp_path/'request',
                           tmp_path/'sealed', temp_root=tmp_path, navigation_root=tmp_path/'navigation')
    original = ordinary['operations'][3]['parameters']['evaluated_reference']
    reference = deepcopy(original)
    root = tmp_path/'reference'
    root.mkdir()
    rows = inspection['rows']
    identity = next(ref['ordered_ids_sha256'] for ref in inspection['arrays'] if ref['role']=='row_id')
    for key, role in (('vector_east_nT', 'reference_east'), ('vector_north_nT', 'reference_north'),
                      ('vector_up_nT', 'reference_up'), ('scalar_F_nT', 'reference_F')):
        reference[key] = io.write_array(root, role, role, original[key], [rows], 'float64', 'nT', identity)
    reference['epoch']['row_date_decimal_year'] = io.write_array(root, 'reference-date', 'reference_date',
        original['epoch']['row_date_decimal_year'], [rows], 'float64', 'decimal_year', identity)
    definition = core._write_member(root, 'reference-definition.json',
                                    base.canonical_bytes(dict(F_nT=48000., D_deg=12., I_deg=55.)))
    reference['receipt_sha256'] = base.digest({k:v for k,v in reference.items() if k!='receipt_sha256'})
    return root, reference, metadata, sealed['geometry'], definition, ordinary_metadata, original


def test_full_original_s3_reference_source_epoch_and_corrected_geometry(tmp_path, monkeypatch):
    from magnetic_line_survey_reference import validate_authored_reference
    root, reference, metadata, seal, definition, _, original = full_reference(tmp_path)
    monkeypatch.setattr(core, 'engines', lambda: pytest.fail('Reference verification imports no native engine'))
    receipt = validate_authored_reference(root, reference, metadata, seal, tmp_path/'sealed', definition=definition)
    assert receipt['rows']==363 and receipt['field_acceptance']=='unresolved'
    assert receipt['coordinates_sha256']==original['coordinates_sha256']
    assert receipt['canonical_source_sha256']==original['evaluator']['source_sha256']
    assert receipt['reference_sha256']!=original['receipt_sha256']
    assert len(receipt['arrays'])==5
    wrong = deepcopy(reference)
    wrong['coordinates_sha256']='1'*64
    wrong['receipt_sha256']=base.digest({k:v for k,v in wrong.items() if k!='receipt_sha256'})
    with pytest.raises(core.SurveyError, match='custody_mismatch'):
        validate_authored_reference(root, wrong, metadata, seal, tmp_path/'sealed', definition=definition)
    wrong = deepcopy(reference)
    wrong['evaluator']['source_sha256']='2'*64
    wrong['receipt_sha256']=base.digest({k:v for k,v in wrong.items() if k!='receipt_sha256'})
    with pytest.raises(core.SurveyError, match='custody_mismatch'):
        validate_authored_reference(root, wrong, metadata, seal, tmp_path/'sealed', definition=definition)
    wrong = deepcopy(reference)
    wrong['epoch']['row_utc_sha256']='3'*64
    wrong['receipt_sha256']=base.digest({k:v for k,v in wrong.items() if k!='receipt_sha256'})
    with pytest.raises(core.SurveyError, match='custody_mismatch'):
        validate_authored_reference(root, wrong, metadata, seal, tmp_path/'sealed', definition=definition)
    field = deepcopy(metadata)
    field['source_kind']='field_acquisition'
    with pytest.raises(core.SurveyError, match='metadata_ineligible'):
        validate_authored_reference(tmp_path/'absent', reference, field, seal, tmp_path/'absent', definition=definition)
    assert not (tmp_path/'absent').exists()
