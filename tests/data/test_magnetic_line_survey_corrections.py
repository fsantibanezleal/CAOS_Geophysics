"""Full original S3 instrument DAG, every source row, independent bounded oracle."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import sys
import os

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'data-pipeline'))
sys.path.insert(0, str(Path(__file__).parent))
import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_io as io
from test_magnetic_line_survey_navigation import fixture, streamed_request


def full_case(tmp_path,*,raw_mirroring='denied'):
    from magnetic_line_survey_seal import seal_geometry
    from magnetic_line_survey_measurements import decode_measurements
    _, metadata, ordinary_metadata, inspection, lag, ordinary, _ = fixture(tmp_path,raw_mirroring=raw_mirroring)
    request = streamed_request(tmp_path/'request', ordinary, metadata, inspection, lag)
    request['operations'] = [lag]+deepcopy(ordinary['operations'][1:])
    base_root, heading_root, reference_root = (tmp_path/name for name in ('base', 'heading', 'reference'))
    for root in (base_root, heading_root, reference_root):
        root.mkdir()
    series = request['operations'][1]['parameters']['base']
    records = series.pop('records')
    identity = sha256(b''.join(row['utc'].encode('ascii').ljust(30, b'\0') for row in records)).hexdigest()
    series.update(schema='magnetic-line-base-stream/1',
        utc=io.write_array(base_root, 'base-utc', 'utc', [r['utc'] for r in records], [len(records)], 'ascii30', 'UTC', identity),
        intensity=io.write_array(base_root, 'base-values', 'base', [r['intensity_nT'] for r in records], [len(records)], 'float64', 'nT', identity))
    calibration = request['operations'][2]['parameters']['calibration']
    assert calibration['calibration_row_ids']==[]
    calibration['calibration_row_ids'] = io.write_array(heading_root, 'calibration-ids', 'row_id', [], [0],
                                                     'ascii64', 'identity', sha256(b'').hexdigest())
    reference = request['operations'][3]['parameters']['evaluated_reference']
    original_reference = deepcopy(reference)
    rows = inspection['rows']
    row_hash = next(ref['ordered_ids_sha256'] for ref in inspection['arrays'] if ref['role']=='row_id')
    for key, role in (('vector_east_nT','reference_east'), ('vector_north_nT','reference_north'),
                      ('vector_up_nT','reference_up'), ('scalar_F_nT','reference_F')):
        reference[key] = io.write_array(reference_root, role, role, original_reference[key], [rows], 'float64', 'nT', row_hash)
    reference['epoch']['row_date_decimal_year'] = io.write_array(reference_root, 'reference-date', 'reference_date',
        original_reference['epoch']['row_date_decimal_year'], [rows], 'float64', 'decimal_year', row_hash)
    definition = core._write_member(reference_root, 'reference-definition.json',
                                    base.canonical_bytes(dict(F_nT=48000., D_deg=12., I_deg=55.)))
    reference['receipt_sha256']=base.digest({k:v for k,v in reference.items() if k!='receipt_sha256'})
    sealed=seal_geometry(tmp_path/'geometry', inspection, metadata, request, tmp_path/'request', tmp_path/'sealed',
                          temp_root=tmp_path, navigation_root=tmp_path/'navigation')
    measurements=decode_measurements(tmp_path/'s3-original.csv', tmp_path/'geometry', inspection, tmp_path/'measurements')
    return metadata, ordinary_metadata, inspection, ordinary, request, sealed, measurements, \
        dict(diurnal=base_root, heading=heading_root, main_field=reference_root), dict(main_field=definition)


def test_complete_original_s3_correction_edges(tmp_path, monkeypatch):
    from magnetic_line_survey_corrections import correct_instrument
    from magnetic_lines import apply_corrections
    metadata, ordinary_metadata, inspection, ordinary, request, sealed, measurements, roots, definitions = full_case(tmp_path)
    expected=apply_corrections((tmp_path/'s3-original.csv').read_bytes(), base.canonical_bytes(ordinary_metadata),
                              base.canonical_bytes(ordinary))
    monkeypatch.setattr(core, 'engines', lambda:pytest.fail('Streamed physical DAG uses no numerical fit'))
    result=correct_instrument(tmp_path/'sealed', sealed, tmp_path/'geometry', inspection, tmp_path/'measurements', measurements,
        metadata, request, tmp_path/'corrected', temp_root=tmp_path, auxiliary_roots=roots, reference_definitions=definitions)
    assert result['rows']==result['original_rows_retained']==363
    assert result['field_acceptance']=='unresolved' and result['numerical_admission']=='not_established'
    assert len(result['channels'])==5 and [e['operation'] for e in result['edges']]==['lag','diurnal','heading','main_field']
    reader=io.Reader(tmp_path/'corrected')
    for actual, oracle, mask in zip(result['channels'], expected['channels'], result['masks'], strict=True):
        assert list(reader.cells(actual['data']))==oracle['data']['values']
        assert not any(reader.cells(mask))
        assert actual['kind']==oracle['kind']
    final=result['channels'][-1]
    assert final['kind']=='scalar_total_field_anomaly'
    assert final['reference_receipt_sha256']==request['operations'][-1]['parameters']['evaluated_reference']['receipt_sha256']
    for index, edge in enumerate(result['edges']):
        assert edge['parent_sha256']==(result['input_channel_sha256'] if index==0 else result['edges'][index-1]['output_sha256'])
        assert edge['output_sha256']!=edge['parent_sha256']
        state=result['channels'][index+1]['state'][-1]
        assert state['status']=='applied' and state['evidence_sha256']==edge['evidence_sha256']
    assert sha256((tmp_path/'s3-original.csv').read_bytes()).hexdigest()==inspection['original']['csv_sha256']
    wrong=deepcopy(request)
    wrong['channel_sha256']='4'*64
    with pytest.raises(core.SurveyError, match='custody_mismatch'):
        correct_instrument(tmp_path/'sealed', sealed, tmp_path/'geometry', inspection, tmp_path/'measurements', measurements,
            metadata, wrong, tmp_path/'wrong', temp_root=tmp_path, auxiliary_roots=roots, reference_definitions=definitions)
    assert not (tmp_path/'wrong').exists()


def test_actual_original_s3_contained_physical_workflow(tmp_path):
    import magnetic_line_survey_runtime as runtime
    metadata, _, inspection, _, request, _, _, roots, definitions = full_case(tmp_path)
    worker = tmp_path/'worker'
    worker.mkdir()
    plan = dict(schema='m03-instrument-correction-plan/1', csv_path=str(tmp_path/'s3-original.csv'),
        geometry_root=str(tmp_path/'geometry'), inspection=inspection, metadata=metadata, request=request,
        request_root=str(tmp_path/'request'), navigation_root=str(tmp_path/'navigation'),
        auxiliary_roots={k:str(v) for k,v in roots.items()}, reference_definitions=definitions)
    path=worker/'plan.json'
    path.write_bytes(base.canonical_bytes(plan))
    receipt=runtime.run_worker(Path(sys.base_prefix)/'python.exe', Path(os.environ['GEOPHYSICS_EXISTING_PACKAGE_ROOT']), worker, path)
    assert receipt['verdict']=='component_pass', (receipt, (worker/'stderr.log').read_text())
    assert receipt['active_processes']==0 and receipt['total_processes']==1
    assert receipt['peak_rss_bytes']>0 and receipt['peak_committed_bytes']>0 and receipt['cpu_s']>0
    ready=base.strict_json((worker/'instrument-ready.json').read_bytes())
    assert ready['rows']==363 and ready['edges']==4 and ready['full_result']=='not_assembled'
    corrected=base.strict_json((worker/'corrected/instrument-corrections.json').read_bytes())
    assert corrected['original']==metadata['original'] and corrected['original_rows_retained']==363
    assert len(corrected['channels'])==5 and corrected['channels'][-1]['kind']=='scalar_total_field_anomaly'
    assert ready['result_sha256']==base.digest(corrected)
