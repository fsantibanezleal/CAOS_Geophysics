"""Byte custody and closed schema controls; no field-validity inference."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import struct
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'data-pipeline'))
import magnetic_line_contract as bounded
import magnetic_line_survey as core
import magnetic_line_survey_contract as contract
import magnetic_line_survey_io as io

HASH = sha256(b'ordered-source-identities').hexdigest()


def array(root, *, role='magnetic', dtype='float64', unit='nT', values=None, shape=None):
    values = [1., -2., 3.] if values is None else values
    return io.write_array(root, 'control', role, values, shape or [len(values)], dtype, unit, HASH)


def test_stream_8201_original_order_and_chunk_boundary(tmp_path):
    values = [float(i - 4096) for i in range(8201)]
    ref = array(tmp_path, values=values)
    assert list(io.Reader(tmp_path).cells(ref)) == values
    reader = io.Reader(tmp_path)
    chunks = list(reader.chunks(ref))
    assert [len(x)//8 for x in chunks] == [4096, 4096, 9]
    reader.reject_unknown()
    assert ref['ordered_ids_sha256'] == HASH


def test_source_positions_and_original_membership_are_typed_matrices(tmp_path):
    ref = io.write_array(tmp_path, 'sources', 'source_position', [[0., 2., -4.], [1., 3., -4.]],
                         [2, 3], 'float64', 'm', HASH)
    assert list(io.Reader(tmp_path).cells(ref)) == [0., 2., -4., 1., 3., -4.]
    member = io.write_array(tmp_path, 'members', 'source_block_member', [[4097, 0], [8200, 1]],
                            [2, 2], 'uint64', 'identity', HASH)
    assert list(io.Reader(tmp_path).cells(member)) == [4097, 0, 8200, 1]


def test_empty_exclusion_has_empty_hash_and_no_chunks(tmp_path):
    ref = array(tmp_path, role='partition_index', dtype='uint64', unit='identity', values=[])
    reader = io.Reader(tmp_path)
    assert list(reader.cells(ref)) == []
    manifest = bounded.strict_json(reader.member(ref['manifest']))
    assert manifest['content_sha256'] == sha256(b'').hexdigest() and manifest['pages'] == []
    reader.reject_unknown()


@pytest.mark.parametrize('mutation', ['extra', 'missing', 'boolean', 'float_integer', 'unit', 'dtype', 'shape', 'name', 'zero'])
def test_closed_ref_refuses_coercions_and_cross_role_changes(tmp_path, mutation):
    ref = array(tmp_path)
    bad = deepcopy(ref)
    if mutation == 'extra': bad['foreign'] = None
    if mutation == 'missing': del bad['mask_array_id']
    if mutation == 'boolean': bad['chunk_rows'] = True
    if mutation == 'float_integer': bad['shape'] = [3.0]
    if mutation == 'unit': bad['unit'] = 'm'
    if mutation == 'dtype': bad['dtype'] = 'uint64'
    if mutation == 'shape': bad['shape'] = [1, 3]
    if mutation == 'name': bad['manifest']['name'] = '../control.json'
    if mutation == 'zero': bad['shape'] = [0]
    with pytest.raises(core.SurveyError): contract.validate('ArrayRef', bad)


def test_actual_chunk_bytes_not_caller_hash_establish_custody(tmp_path):
    ref = array(tmp_path)
    chunk = tmp_path / 'array-control-00000000.bin'
    chunk.write_bytes(struct.pack('<3d', 1., 2., 3.))
    with pytest.raises(core.SurveyError, match='custody_mismatch'):
        list(io.Reader(tmp_path).cells(ref))


def test_shape_manifest_substitution_and_unknown_file_refuse(tmp_path):
    ref = array(tmp_path)
    bad = deepcopy(ref)
    bad['shape'] = [2]
    with pytest.raises(core.SurveyError, match='custody_mismatch'):
        list(io.Reader(tmp_path).cells(bad))
    reader = io.Reader(tmp_path)
    reader.verify(ref)
    (tmp_path / 'undeclared.txt').write_bytes(b'not admitted')
    with pytest.raises(core.SurveyError, match='custody_mismatch'): reader.reject_unknown()


def test_table_is_closed_canonical_length_prefixed(tmp_path):
    rows = [dict(row_index=4097, block_e=-2, block_n=3, source_index=0),
            dict(row_index=8200, block_e=-1, block_n=3, source_index=1)]
    ref = io.write_table(tmp_path, 'blocks', 'source_block', rows)
    reader = io.Reader(tmp_path)
    assert list(reader.table(ref)) == rows
    reader.reject_unknown()


@pytest.mark.parametrize('value', [True, float('nan'), float('inf'), '1'])
def test_binary_cells_refuse_non_native_nonfinite(value):
    with pytest.raises(core.SurveyError): io.encoded_cell(value, 'float64')


def test_explicit_external_roots_only(tmp_path, monkeypatch):
    monkeypatch.delenv('GEOPHYSICS_LOCAL_DATA_ROOT', raising=False)
    with pytest.raises(core.SurveyError): io.local_root()
    with pytest.raises(core.SurveyError): io.local_root('.')
    with pytest.raises(core.SurveyError): io.local_root(Path(__file__).resolve().parents[2])
    monkeypatch.setenv('GEOPHYSICS_LOCAL_DATA_ROOT', str(tmp_path))
    assert io.local_root() == tmp_path
    with io.scratch_directory(tmp_path) as directory:
        assert Path(directory).parent == tmp_path
    assert not Path(directory).exists()


def test_new_schemas_do_not_modify_bounded_contract():
    assert 'SurveyInput' not in bounded.SCHEMAS
    assert bounded.SCHEMAS['SourceGeometry']['max_sources'] == bounded.I(1, 256)


def test_writer_cannot_execute_foreign_scalar_conversion_hook(tmp_path):
    class Foreign:
        def item(self):
            pytest.fail('Foreign array/scalar hooks are not admitted')
    with pytest.raises(core.SurveyError):
        array(tmp_path, values=[Foreign()])


def test_source_and_grid_role_counts_refuse_before_member_creation(tmp_path):
    with pytest.raises(core.SurveyError):
        io.write_array(tmp_path,'sources','source_position',[],[65537,3],'float64','m',HASH)
    assert not list(tmp_path.iterdir())
    with pytest.raises(core.SurveyError):
        io.write_array(tmp_path,'grid','grid_value',[],[1025,1025],'float64','nT',HASH)
    assert not list(tmp_path.iterdir())
