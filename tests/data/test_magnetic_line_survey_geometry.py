"""Disk planner compared with immutable original geometry semantics."""
from copy import deepcopy
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from hashlib import sha256
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'data-pipeline'))
import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_contract as schema
import magnetic_line_survey_geometry as geometry
import magnetic_line_survey_io as io
from magnetic_line_validation import make_partitions


def fixture(tmp_path):
    spec = spec_from_file_location('original_geometry_controls', Path(__file__).parents[1]/'fixtures/magnetic_lines/generate.py')
    controls = module_from_spec(spec)
    spec.loader.exec_module(controls)
    raw, metadata, ordinary = controls.geometry_input()
    csv = tmp_path/'original.csv'
    csv.write_bytes(raw)
    inspection = core.inspect_geometry(csv, tmp_path/'geometry', metadata['original'], metadata['rights'],
                         metadata['acquisition']['line_dictionary'], metadata['acquisition']['sensor_dictionary'])
    request_root = tmp_path/'request'
    request_root.mkdir()
    request = deepcopy(ordinary)
    request['schema'] = 'magnetic-line-survey-request/1'
    request.update(profile='m03-offline-stream/1', solver={key:spec[1] for key,spec in schema.SCHEMAS['SolverPolicy'].items()})
    split = request['split']
    split['version'] = 'full_lines_buffered_ties_stream/1'
    split['geometry_manifest_sha256'] = inspection['geometry_sha256']
    def identities(name, values):
        digest = sha256(b''.join(value.encode('ascii').ljust(64,b'\0') for value in sorted(values))).hexdigest()
        return io.write_array(request_root, name, 'row_id', sorted(values), [len(values)], 'ascii64', 'identity', digest)
    split['outer_line_ids'] = identities('outer', ordinary['split']['outer_line_ids'])
    split['anchor_line_ids'] = identities('anchors', ordinary['split']['anchor_line_ids'])
    split['heldout_blocks'] = io.write_table(request_root, 'outer-blocks', 'spatial_block', ordinary['split']['heldout_blocks'])
    for index, fold in enumerate(split['inner_folds']):
        original = ordinary['split']['inner_folds'][index]
        fold['validation_line_ids'] = identities(f'inner{index}', original['validation_line_ids'])
        fold['validation_blocks'] = io.write_table(request_root, f'inner-blocks{index}', 'spatial_block', original['validation_blocks'])
    request['equivalent_sources']['source_geometry']['version'] = 'half_open_training_blocks_stream/1'
    request['equivalent_sources']['weight_multiplier'] = 1
    return controls, ordinary, inspection, request, request_root


def test_disk_partitions_and_sources_match_original_no_value_access(tmp_path, monkeypatch):
    controls, ordinary, inspection, request, request_root = fixture(tmp_path)
    monkeypatch.setattr(core, 'engines', lambda: pytest.fail('Geometry must not import numerical engines'))
    result = geometry.plan_partitions(tmp_path/'geometry', inspection, request, request_root,
                                      tmp_path/'plan', temp_root=tmp_path)
    expected = make_partitions(controls.geometry_rows(), ordinary)
    assert result['value_access'] == 'not_opened' and result['complete_geometry_seal'] is False
    reader = io.Reader(tmp_path/'plan')
    rows = controls.geometry_rows()
    originals = [dict(training_ids=expected['outer_training_ids'], validation_ids=expected['outer_validation_ids'],
                      source_positions=expected['outer_source_positions'])]+expected['inner']
    for actual, original in zip(result['partitions'], originals, strict=True):
        training = [rows[pos]['row_id'] for pos in reader.cells(actual['training'])]
        validation = [rows[pos]['row_id'] for pos in reader.cells(actual['validation'])]
        assert training == original['training_ids'] and validation == original['validation_ids']
        assert list(reader.cells(actual['sources'])) == [v[key] for v in original['source_positions']
                                                        for key in ('easting_m','northing_m','upward_m')]
        reader.verify(actual['source_members'])
        reader.verify(actual['source_blocks'])
        reader.verify(actual['exclusions'])
    reader.reject_unknown(extra=('partition-plan.json',))


def test_different_value_identity_does_not_enter_geometry_plan(tmp_path):
    _, _, inspection, request, request_root = fixture(tmp_path)
    first = geometry.plan_partitions(tmp_path/'geometry', inspection, request, request_root,
                                     tmp_path/'first', temp_root=tmp_path)
    changed = deepcopy(request)
    changed['channel_sha256'] = '1'*64
    changed['split']['sealed_values_sha256'] = '2'*64
    second = geometry.plan_partitions(tmp_path/'geometry', inspection, changed, request_root,
                                      tmp_path/'second', temp_root=tmp_path)
    assert first['partitions'] == second['partitions'] and first['capacity'] == second['capacity']


def test_geometry_or_source_budget_mutation_refuses(tmp_path):
    _, _, inspection, request, request_root = fixture(tmp_path)
    request['split']['geometry_manifest_sha256'] = '0'*64
    with pytest.raises(core.SurveyError, match='custody_mismatch'):
        geometry.plan_partitions(tmp_path/'geometry', inspection, request, request_root,
                                  tmp_path/'bad-geometry', temp_root=tmp_path)
    request['split']['geometry_manifest_sha256'] = inspection['geometry_sha256']
    request['equivalent_sources']['source_geometry']['max_sources'] = 1
    with pytest.raises(core.SurveyError, match='resource_refused'):
        geometry.plan_partitions(tmp_path/'geometry', inspection, request, request_root,
                                  tmp_path/'bad-sources', temp_root=tmp_path)
