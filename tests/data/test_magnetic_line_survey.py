"""Allocation controls for the distinct provisional M03 streamed profile."""
from importlib import import_module
from pathlib import Path
import sys
import json
from hashlib import sha256

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "data-pipeline"))


def module():
    return import_module("magnetic_line_survey")


def test_phase_allocation_capacity():
    p = module()
    bounds = p.allocation_bounds(8000000, 65536, 1048576, 4194304)
    assert bounds["fit_buffer_bytes"] == 3324665856
    assert bounds["transform_buffer_bytes"] == 2415919104
    assert bounds["fit_buffer_bytes"] < 4 * 1024**3
    small = p.plan_capacity(1000, 200, raw_bytes=100000)
    assert small["kernel_pair_bound"] == 1000 * 200 * 4004 * 25
    assert small["resource_state"] == "unmeasured"
    assert small["profile"] == "m03-offline-stream/1"
    # Geometry at simultaneous raw/source maxima exceeds the all-fit work cap;
    # a byte formula below RAM limit is NOT an admitted execution.
    with pytest.raises(p.SurveyError, match="resource_refused"):
        p.plan_capacity(8000000, 65536)


@pytest.mark.parametrize("n,m", [(True, 4), (3., 4), (0, 4), (8000001, 4),
                                  (3, False), (3, 65537), (3, -1)])
def test_capacity_native_counts(n, m):
    p = module()
    with pytest.raises(p.SurveyError):
        p.plan_capacity(n, m)


def test_auxiliary_and_scratch_capacity():
    p = module()
    plan = p.plan_capacity(200, 30, auxiliary_rows=1200,
                           crossover_candidates=900, raw_bytes=100000,
                           auxiliary_bytes=50000, exported_cells=1024,
                           fft_cells=4096)
    assert plan["scratch_bound_bytes"] == (
        2 * 150000 + 512 * 200 + 256 * 30 + 256 * 900 +
        256 * 1024 + 128 * 4096 + 268435456)
    for key, value in [("auxiliary_rows", 16000001), ("raw_bytes", 4294967297),
                       ("crossover_candidates", 8000001), ("exported_cells", 1048577),
                       ("fft_cells", 4194305), ("auxiliary_bytes", True)]:
        with pytest.raises(p.SurveyError):
            p.plan_capacity(200, 30, **{key: value})


def test_no_dense_global_or_hidden_tiles():
    p = module()
    plan = p.plan_capacity(1000000, 1000)
    assert plan["fit_buffer_bytes"] < 8 * 1000000 * 1000
    assert plan["resource_state"] == "unmeasured"
    # No old ordinary module edits/monkeypatched global limits.
    assert p.ROW_LIMIT == 8000000 and p.SOURCE_LIMIT == 65536


def test_safe_native_error_without_arbitrary_details():
    p = module()
    error = p.SurveyError("invalid_contract", "fit")
    assert error.error == {
        "schema": "magnetic-line-survey-error/1", "code": "invalid_contract",
        "stage": "fit", "field": None, "message": "invalid_contract:fit",
        "partial_manifest_sha256": None}
    assert str(error) == "invalid_contract:fit"


HEADER = ('row_id,line_id,line_kind,sensor_id,ordinal,utc,easting_m,northing_m,'
          'upward_m,terrain_upward_m,clearance_m,magnetic_nT,uncertainty_nT,heading_deg\n')


def raw_rows(count=5, value='NaN'):
    # Authored ingestion control, NOT field data or predictive evidence.
    return (HEADER + ''.join(
        f'r{i},L{i%2},flight,S0,{i},2026-01-01T00:00:00Z,{i},-3,100,20,80,{value},Infinity,90\n'
        for i in range(count))).encode()


def intake_args(tmp_path, raw):
    csv = tmp_path / 'original.csv'
    csv.write_bytes(raw)
    original = dict(csv_sha256=sha256(raw).hexdigest(), csv_bytes=len(raw),
                    source_url=None, provider_identifier=None, retrieval_utc=None)
    rights = dict(evidence_uri=None, evidence_sha256=None, decision='allowed',
                  private_processing='allowed', derivative_publication='denied',
                  raw_mirroring='denied', attribution=['Original synthetic intake control'])
    lines = [dict(line_id=f'L{i}', kind='flight', description='Authored line',
                  provider_code=None) for i in range(2)]
    sensors = [dict(sensor_id='S0', description='Authored sensor',
                    provider_column=None, unit='nT')]
    return csv, tmp_path / 'fresh', original, rights, lines, sensors


def test_source_order_chunk_custody(tmp_path, monkeypatch):
    p = module()
    monkeypatch.setattr(p, 'engines', lambda: pytest.fail('No numerical import at intake'))
    args = intake_args(tmp_path, raw_rows(8201))
    result = p.inspect_geometry(*args)
    assert set(result) == {'schema', 'original', 'rows', 'lines', 'sensors',
                           'arrays', 'dictionaries', 'geometry_sha256', 'value_access'}
    assert result['schema'] == 'm03-geometry-inspection/1'
    assert result['rows'] == 8201 and result['lines'] == 2 and result['sensors'] == 1
    assert result['value_access'] == 'not_opened'
    assert {a['role'] for a in result['arrays']} == {
        'row_id', 'line_index', 'sensor_index', 'ordinal', 'utc', 'easting',
        'northing', 'upward', 'terrain_upward', 'clearance', 'heading', 'missing_mask'}
    assert not list(args[1].glob('*.csv'))
    assert not list(args[1].glob('*magnetic*'))
    row = next(a for a in result['arrays'] if a['role'] == 'row_id')
    manifest = json.loads((args[1] / row['manifest']['name']).read_bytes())
    assert manifest['content_sha256'] == sha256(b''.join(
        f'r{i}'.encode().ljust(64, b'\0') for i in range(8201))).hexdigest()
    page = json.loads((args[1] / manifest['pages'][0]['file']['name']).read_bytes())
    assert [c['rows'] for c in page['entries']] == [4096, 4096, 9]
    assert p.verify_geometry_inspection(args[1], result) == result
    assert args[0].read_bytes() == raw_rows(8201)


def test_geometry_seal_precedes_value_access(tmp_path):
    p = module()
    one = intake_args(tmp_path, raw_rows(value='NaN'))
    a = p.inspect_geometry(*one)
    another = tmp_path / 'other'
    another.mkdir()
    two = intake_args(another, raw_rows(value='9e9999'))
    b = p.inspect_geometry(*two)
    assert a['geometry_sha256'] == b['geometry_sha256']
    assert a['arrays'] == b['arrays']
    assert a['original'] != b['original']
    # Neither inspection is a full geometry seal or physically admitted result.
    assert 'capacity' not in a and 'numerical_success' not in a


@pytest.mark.parametrize('change', [
    lambda b: b.replace(b'r1,L1', b'r0,L1'),
    lambda b: b.replace(b'r2,L0,flight,S0,2', b'r2,L0,flight,S0,0'),
    lambda b: b.replace(b'r1,L1,flight', b'r1,L1,tie'),
    lambda b: b.replace(b'r1,L1,flight,S0', b'r1,L1,flight,S1'),
    lambda b: b.replace(b',100,20,80,', b',1e-999,20,80,'),
    lambda b: b.replace(b',-3,100,', b',Infinity,100,'),
    lambda b: b.replace(b',NaN,Infinity,', b',' + b'1'*129 + b',Infinity,'),
    lambda b: b.replace(b',NaN,Infinity,', b',"12",Infinity,'),
    lambda b: b.replace(b'2026-01-01T00:00:00Z', b'2026-02-30T00:00:00Z'),
    lambda b: b.replace(b'row_id', b'\xffrow_id'),
    lambda b: b + b'x'*4097,
])
def test_streaming_record_and_geometry_refusals(tmp_path, change):
    p = module()
    with pytest.raises(p.SurveyError):
        p.inspect_geometry(*intake_args(tmp_path, change(raw_rows())))


def test_closed_input_and_original_identity(tmp_path):
    p = module()
    args = list(intake_args(tmp_path, raw_rows()))
    args[2]['csv_sha256'] = '0'*64
    with pytest.raises(p.SurveyError, match='custody_mismatch'):
        p.inspect_geometry(*args)
    assert not (args[1] / 'inspection.json').exists()


def test_private_permission_and_fresh_destination(tmp_path):
    p = module()
    args = list(intake_args(tmp_path, raw_rows()))
    args[3]['private_processing'] = 'unresolved'
    with pytest.raises(p.SurveyError, match='metadata_ineligible'):
        p.inspect_geometry(*args)
    assert not args[1].exists()
    args[3]['private_processing'] = 'allowed'
    args[1].mkdir()
    marker = args[1] / 'protected'
    marker.write_bytes(b'keep')
    with pytest.raises(p.SurveyError):
        p.inspect_geometry(*args)
    assert marker.read_bytes() == b'keep'


def test_streaming_unknown_file_and_chunk_drift(tmp_path):
    p = module()
    args = intake_args(tmp_path, raw_rows())
    result = p.inspect_geometry(*args)
    payload = next(args[1].glob('array-row_id-*.bin'))
    payload.write_bytes(b'X' + payload.read_bytes()[1:])
    with pytest.raises(p.SurveyError, match='custody_mismatch'):
        p.verify_geometry_inspection(args[1], result)


def test_source_link_substitution_refuses(tmp_path):
    import os
    p = module()
    args = list(intake_args(tmp_path, raw_rows()))
    link = tmp_path / 'hard.csv'
    os.link(args[0], link)
    args[0] = link
    with pytest.raises(p.SurveyError, match='custody_mismatch'):
        p.inspect_geometry(*args)


def save_rehashed_receipt(root, receipt):
    # Adversarial test helper, not a scientific producer or a trusted receipt.
    (root / 'inspection.json').write_bytes(module()._contract().canonical_bytes(receipt))


def test_unknown_member_and_rehashed_metadata_refused(tmp_path):
    import copy
    p = module()
    args = intake_args(tmp_path, raw_rows())
    result = p.inspect_geometry(*args)
    unknown = args[1] / 'undeclared.bin'
    unknown.write_bytes(b'not a member')
    with pytest.raises(p.SurveyError):
        p.verify_geometry_inspection(args[1], result)
    unknown.unlink()  # Only this test-owned adversarial member.
    for key, value in [('rows', 5.0), ('lines', True), ('sensors', True),
                       ('original', {**result['original'], 'extra': 1})]:
        altered = copy.deepcopy(result)
        altered[key] = value
        save_rehashed_receipt(args[1], altered)
        with pytest.raises(p.SurveyError):
            p.verify_geometry_inspection(args[1], altered)
    save_rehashed_receipt(args[1], result)
    assert p.verify_geometry_inspection(args[1], result) == result


def test_missing_geometry_is_null_not_observed_zero(tmp_path):
    import struct
    p = module()
    raw = raw_rows().replace(b',100,20,80,', b',,,,').replace(b',90\n', b',\n')
    args = intake_args(tmp_path, raw)
    result = p.inspect_geometry(*args)
    assert 'numerical_success' not in result
    mask_bytes = (args[1] / 'array-missing_mask-00000000.bin').read_bytes()
    assert struct.unpack('<5I', mask_bytes) == (78,)*5
    assert (args[1] / 'array-upward-00000000.bin').read_bytes() == b'\0'*40


def test_actual_growth_during_read_cannot_publish(tmp_path, monkeypatch):
    p = module()
    args = intake_args(tmp_path, raw_rows())
    original = p._geometry_record
    calls = []
    def changing_source(tokens, contract):
        if not calls:
            with args[0].open('ab') as stream:
                stream.write(b'new bytes appended during processing\n')
            calls.append(True)
        return original(tokens, contract)
    monkeypatch.setattr(p, '_geometry_record', changing_source)
    with pytest.raises(p.SurveyError):
        p.inspect_geometry(*args)
    assert calls and not (args[1] / 'inspection.json').exists()


def test_geometry_verifier_rejects_rehashed_duplicate_ids(tmp_path):
    p = module()
    args = intake_args(tmp_path, raw_rows())
    result = p.inspect_geometry(*args)
    # _manifest_chunks is a test-only adversarial source after byte verification.
    # Verify uniqueness independently, not only matching a supplied geometry hash.
    original = p._manifest_chunks
    from unittest.mock import patch
    def duplicate_stream(root, ref, known, array):
        for chunk in original(root, ref, known, array):
            if array and ref['role'] == 'row_id':
                chunk = chunk[:64] + chunk[:64] + chunk[128:]
            yield chunk
    with patch.object(p, '_manifest_chunks', duplicate_stream):
        with pytest.raises(p.SurveyError):
            p.verify_geometry_inspection(args[1], result)
