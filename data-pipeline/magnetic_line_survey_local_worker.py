"""Fixed source-bound cold CLI dispatcher, before geometry/value decoding."""
from __future__ import annotations

import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_contract as schema
import magnetic_line_survey_io as io
from magnetic_line_survey_result import _refs,_pack


def run_local_plan(plan,workspace,job_handle,package_root):
    from magnetic_line_survey_runtime import require_job
    require_job(job_handle)
    core._closed(plan,'schema csv_path metadata_path request_path auxiliary_root run_id expected_environment','ingest')
    if plan['schema']!='m03-local-run-plan/2':
        raise core.SurveyError('invalid_contract','ingest')
    if plan['expected_environment'] is not None:
        # Inside the actual Job, before opening geometry or new values. A
        # changed source, engine, license or native binary cannot silently replay.
        from magnetic_line_survey_environment import environment_identity
        expected=schema.typed(plan['expected_environment'],'Environment')
        if environment_identity(package_root,job_handle=job_handle)!=expected:
            raise core.SurveyError('custody_mismatch','replay')
    workspace=io.external_path(workspace)
    source=io.external_path(plan['csv_path'],directory=False)
    auxiliary=io.external_path(plan['auxiliary_root'])
    metadata_bytes,metadata=schema.read_document(io.external_path(plan['metadata_path'],directory=False),'SurveyInput')
    request_bytes,request=schema.read_document(io.external_path(plan['request_path'],directory=False),'SurveyRequest')
    base._type(plan['run_id'],'ID','run_id',0)
    if metadata['rights']['decision']!='allowed' or metadata['rights']['private_processing']!='allowed':
        raise core.SurveyError('metadata_ineligible','ingest')
    from magnetic_line_survey_representation import Reader
    reader=Reader(auxiliary)
    lines=list(reader.table(metadata['acquisition']['line_dictionary']))
    sensors=list(reader.table(metadata['acquisition']['sensor_dictionary']))
    print('m03-worker:original-geometry-intake',flush=True)
    inspection=core.inspect_geometry(source,workspace/'geometry',metadata['original'],metadata['rights'],lines,sensors)
    if inspection['arrays']!=metadata['arrays'] or inspection['dictionaries']!=[
            metadata['acquisition']['line_dictionary'],metadata['acquisition']['sensor_dictionary']]:
        raise core.SurveyError('custody_mismatch','ingest')
    request_root=workspace/'request-original'
    request_root.mkdir()
    _pack(auxiliary,_refs(request['split']),request_root)
    navigation=None
    roots,definitions={},{}
    for operation in request['operations']:
        name=operation['operation']
        if name not in ('lag','diurnal','heading','main_field'):
            raise core.SurveyError('unsupported_operation','correction')
        root=workspace/('aux-'+name)
        root.mkdir()
        _pack(auxiliary,_refs(operation['parameters']),root)
        if name=='lag':
            navigation=root
        else:
            roots[name]=str(root)
        if name=='main_field':
            source_name='main_field-source.json'
            # This explicit source role is a local recipe convention. Its
            # canonical bytes must match the reviewed evaluator source SHA;
            # no URL, filename guess or original field-value inference.
            payload=base.read_bounded(core._plain_path(auxiliary/source_name),2097152)
            source_definition=base.strict_json(payload)
            core._closed(source_definition,'F_nT D_deg I_deg','correction')
            if base.digest(source_definition)!=operation['parameters']['evaluated_reference']['evaluator']['source_sha256']:
                raise core.SurveyError('custody_mismatch','correction')
            definitions[name]=core._write_member(root,source_name,payload)
    full=dict(schema='m03-full-result-plan/1',csv_path=str(source),geometry_root=str(workspace/'geometry'),
        inspection=inspection,metadata=metadata,request=request,request_root=str(request_root),
        navigation_root=str(navigation) if navigation is not None else None,
        auxiliary_roots=roots,reference_definitions=definitions,run_id=plan['run_id'])
    from magnetic_line_survey_corrections import run_instrument_worker
    return run_instrument_worker(full,workspace,job_handle,package_root=package_root,
        original_documents=dict(metadata=metadata_bytes,request=request_bytes))
