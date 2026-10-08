"""Original independent S3 navigation, aligned before measurement access."""
from copy import deepcopy
from hashlib import sha256
from importlib.util import module_from_spec,spec_from_file_location
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'data-pipeline'))
import magnetic_line_survey as core
import magnetic_line_survey_io as io


def streamed_request(root, ordinary, metadata, inspection, operation):
    import magnetic_line_contract as base
    import magnetic_line_survey_contract as schema
    root.mkdir()
    request=deepcopy(ordinary)
    request['schema']='magnetic-line-survey-request/1'
    request.update(profile='m03-offline-stream/1',solver={key:spec[1] for key,spec in schema.SCHEMAS['SolverPolicy'].items()})
    request['operations']=[operation]
    request['dataset_version_sha256']=base.dataset_identity(inspection['original']['csv_sha256'],base.digest(metadata))
    split=request['split']
    split.update(version='full_lines_buffered_ties_stream/1',geometry_manifest_sha256=inspection['geometry_sha256'])
    def ids(name,values):
        values=sorted(values)
        identity=sha256(b''.join(v.encode('ascii').ljust(64,b'\0') for v in values)).hexdigest()
        return io.write_array(root,name,'row_id',values,[len(values)],'ascii64','identity',identity)
    split['outer_line_ids']=ids('outer',ordinary['split']['outer_line_ids'])
    split['anchor_line_ids']=ids('anchors',ordinary['split']['anchor_line_ids'])
    split['heldout_blocks']=io.write_table(root,'outer-blocks','spatial_block',ordinary['split']['heldout_blocks'])
    for index,fold in enumerate(split['inner_folds']):
        old=ordinary['split']['inner_folds'][index]
        fold['validation_line_ids']=ids(f'inner{index}',old['validation_line_ids'])
        fold['validation_blocks']=io.write_table(root,f'inner-blocks{index}','spatial_block',old['validation_blocks'])
    request['equivalent_sources']['source_geometry']['version']='half_open_training_blocks_stream/1'
    request['equivalent_sources']['weight_multiplier']=1
    return request


def fixture(tmp_path):
    spec=spec_from_file_location('original_navigation_controls',Path(__file__).parents[1]/'fixtures/magnetic_lines/generate.py')
    controls=module_from_spec(spec)
    spec.loader.exec_module(controls)
    raw,metadata,request=controls.instrument_input()
    original_metadata=deepcopy(metadata)
    csv=tmp_path/'s3-original.csv'
    csv.write_bytes(raw)
    inspection=core.inspect_geometry(csv,tmp_path/'geometry',metadata['original'],metadata['rights'],
        metadata['acquisition']['line_dictionary'],metadata['acquisition']['sensor_dictionary'])
    lines={line['line_id']:index for index,line in enumerate(metadata['acquisition']['line_dictionary'])}
    operation=deepcopy(request['operations'][0])
    nav=operation['parameters']['navigation']
    records=nav.pop('records')
    aux=tmp_path/'navigation'
    aux.mkdir()
    identifiers=[f'nav.{index:06d}' for index in range(len(records))]
    identity=sha256(b''.join(r.encode('ascii').ljust(64,b'\0') for r in identifiers)).hexdigest()
    nav.update(schema='magnetic-line-navigation-stream/1',
        row_ids=io.write_array(aux,'nav-ids','row_id',identifiers,[len(records)],'ascii64','identity',identity),
        utc=io.write_array(aux,'nav-utc','utc',[r['utc'] for r in records],[len(records)],'ascii30','UTC',identity),
        line_index=io.write_array(aux,'nav-lines','line_index',[lines[r['line_id']] for r in records],[len(records)],'uint32','identity',identity),
        xyz=io.write_array(aux,'nav-xyz','navigation',[[r[k] for k in ('easting_m','northing_m','upward_m')] for r in records],
                           [len(records),3],'float64','m',identity))
    metadata['schema']='magnetic-line-survey-input/1'
    metadata['acquisition']['line_dictionary'],metadata['acquisition']['sensor_dictionary']=inspection['dictionaries']
    metadata.update(arrays=inspection['arrays'],auxiliaries=[])
    return controls,metadata,original_metadata,inspection,operation,request,records


def test_original_s3_navigation_alignment_matches_actual_brackets(tmp_path,monkeypatch):
    from magnetic_line_survey_navigation import align_geometry
    from magnetic_line_contract import parse_csv
    from magnetic_lines import apply_instrument_corrections
    _,metadata,ordinary,inspection,operation,request,_=fixture(tmp_path)
    monkeypatch.setattr(core,'engines',lambda:pytest.fail('Navigation seal is value-free and stdlib-only'))
    result=align_geometry(tmp_path/'geometry',inspection,metadata,operation,tmp_path/'navigation',tmp_path/'aligned',temp_root=tmp_path)
    rows=parse_csv((tmp_path/'s3-original.csv').read_bytes())['rows']
    expected,masks=apply_instrument_corrections(rows,ordinary,request['operations'][0],[[] for _ in rows])
    reader=io.Reader(tmp_path/'aligned')
    assert list(reader.cells(result['coordinates']))==[r[k] for r in expected for k in ('easting_m','northing_m','upward_m')]
    assert not any(reader.cells(result['mask']))
    assert result['value_access']=='not_opened' and result['field_acceptance']=='unresolved'
    from magnetic_lines import reference_coordinates_sha256
    assert result['coordinates_sha256']==reference_coordinates_sha256(expected,ordinary['coordinates']['vertical_datum'])
    # Exact relative-nanosecond fraction, not rounded absolute UTC floats.
    fractional=deepcopy(operation)
    fractional['parameters']['tau_s']=.2500000001
    changed=align_geometry(tmp_path/'geometry',inspection,metadata,fractional,tmp_path/'navigation',tmp_path/'fractional',temp_root=tmp_path)
    oracle,_=apply_instrument_corrections(rows,ordinary,dict(request['operations'][0],parameters=dict(
        request['operations'][0]['parameters'],tau_s=.2500000001)),[[] for _ in rows])
    assert list(io.Reader(tmp_path/'fractional').cells(changed['coordinates']))==[r[k] for r in oracle for k in ('easting_m','northing_m','upward_m')]
    outside=deepcopy(operation)
    outside['parameters']['tau_s']=10000.
    unsupported=align_geometry(tmp_path/'geometry',inspection,metadata,outside,tmp_path/'navigation',tmp_path/'unsupported',temp_root=tmp_path)
    assert unsupported['unsupported_rows']==len(rows)
    assert set(io.Reader(tmp_path/'unsupported').cells(unsupported['mask']))=={1<<5}
    assert list(io.Reader(tmp_path/'unsupported').cells(unsupported['coordinates']))==[r[k] for r in rows for k in ('easting_m','northing_m','upward_m')]
    # The owner seal must use aligned geometry in EVERY downstream stage.
    from magnetic_line_survey_seal import seal_geometry
    streamed=streamed_request(tmp_path/'request',request,metadata,inspection,operation)
    sealed=seal_geometry(tmp_path/'geometry',inspection,metadata,streamed,tmp_path/'request',tmp_path/'sealed',
                         temp_root=tmp_path,navigation_root=tmp_path/'navigation')
    assert sealed['geometry']['coordinates_sha256']==result['coordinates_sha256']
    assert sealed['geometry']['capacity']['auxiliary_rows']==operation['parameters']['navigation']['row_ids']['shape'][0]
    from magnetic_line_validation import make_partitions
    expected_parts=make_partitions(expected,request)
    seal_reader=io.Reader(tmp_path/'sealed')
    originals=[dict(training_ids=expected_parts['outer_training_ids'],source_positions=expected_parts['outer_source_positions'])]+expected_parts['inner']
    for part,original in zip(sealed['partitions']['partitions'],originals,strict=True):
        assert [rows[p]['row_id'] for p in seal_reader.cells(part['training'])]==original['training_ids']
        assert list(seal_reader.cells(part['sources']))==[v[k] for v in original['source_positions'] for k in ('easting_m','northing_m','upward_m')]
    import magnetic_line_contract as base
    for stage in ('partitions','crossovers','support'):
        assert sealed[stage]['navigation_sha256']==base.digest(sealed['navigation'])
    for ref in sealed['geometry']['arrays']+sealed['geometry']['dictionaries']:
        seal_reader.verify(ref)
    seal_reader.reject_unknown(extra=('geometry-seal.json',))
    assert sha256((tmp_path/'s3-original.csv').read_bytes()).hexdigest()==inspection['original']['csv_sha256']


def test_clock_and_already_subtracted_state_refuse_before_alignment(tmp_path):
    from magnetic_line_survey_navigation import align_geometry
    _,metadata,_,inspection,operation,_,_=fixture(tmp_path)
    original_clock=operation['parameters']['navigation']['clock']['synchronization_evidence_sha256']
    operation['parameters']['navigation']['clock']['synchronization_evidence_sha256']='1'*64
    with pytest.raises(core.SurveyError,match='metadata_ineligible'):
        align_geometry(tmp_path/'geometry',inspection,metadata,operation,tmp_path/'navigation',tmp_path/'bad-clock',temp_root=tmp_path)
    metadata['quantity'].update(kind='scalar_total_field_anomaly',sign_definition='total_minus_reference')
    with pytest.raises(core.SurveyError,match='metadata_ineligible'):
        align_geometry(tmp_path/'geometry',inspection,metadata,operation,tmp_path/'navigation',tmp_path/'bad-state',temp_root=tmp_path)
    assert not (tmp_path/'bad-clock').exists() and not (tmp_path/'bad-state').exists()
    metadata['quantity'].update(kind='scalar_total_intensity',sign_definition='measured_total_intensity')
    operation['parameters']['navigation']['clock']['synchronization_evidence_sha256']=original_clock
    operation['parameters']['navigation']['identity']['canonical_records_sha256']='2'*64
    with pytest.raises(core.SurveyError,match='custody_mismatch'):
        align_geometry(tmp_path/'geometry',inspection,metadata,operation,tmp_path/'navigation',tmp_path/'bad-identity',temp_root=tmp_path)
    assert not (tmp_path/'bad-identity').exists()
