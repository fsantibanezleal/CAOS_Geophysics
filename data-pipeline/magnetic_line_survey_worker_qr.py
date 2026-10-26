"""Fixed full QR epoch DAG; fresh seal, exact 97 solves, no holdout upgrade."""
from pathlib import Path

import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_contract_qr as schema
from magnetic_line_survey_qr_execution import create_execution,full_capacity,PREREQUISITE_SHA
import magnetic_line_survey_io as io


def run_qr_plan(plan,workspace,job_handle,*,package_root,original_documents=None):
    from magnetic_line_survey_runtime import require_job
    require_job(job_handle)
    core._closed(plan,'schema csv_path geometry_root inspection metadata request request_root navigation_root '
        'auxiliary_roots reference_definitions run_id capacity_root prerequisite','seal')
    if plan['schema']!='m03-resolution-qr-fit-plan/1':
        raise core.SurveyError('invalid_contract','seal')
    metadata=schema.validate('SurveyInput',plan['metadata'])
    request=schema.validate('SurveyRequest',plan['request'])
    workspace=io.external_path(workspace)
    prerequisite=base.read_bounded(core._plain_path(io.external_path(plan['prerequisite'],directory=False)),2097152)
    from hashlib import sha256
    if sha256(prerequisite).hexdigest()!=PREREQUISITE_SHA:raise core.SurveyError('custody_mismatch','seal')
    reviewed=base.strict_json(prerequisite)
    if reviewed['solve']['numerical_verdict']!='component_pass' or reviewed['outer_evaluation_count']!=0:
        raise core.SurveyError('custody_mismatch','seal')
    capacity_root=io.external_path(plan['capacity_root'])
    prior=schema.validate('GeometrySeal',base.strict_json(base.read_bounded(core._plain_path(capacity_root/'geometry-seal.json'),2097152)))
    prior_proof=base.strict_json(base.read_bounded(core._plain_path(capacity_root/'resolution-capacity-proof.json'),4194304))
    if prior['original']!=metadata['original']:raise core.SurveyError('custody_mismatch','seal')
    planned=full_capacity(prior,prior_proof) # BEFORE fresh maps or new measurement values.
    from magnetic_line_survey_resolution_geometry import seal_resolution_geometry,verify_resolution_geometry
    print('m03-worker:qr-fresh-value-free-seal',flush=True)
    sealed=seal_resolution_geometry(plan['geometry_root'],plan['inspection'],metadata,request,plan['request_root'],
        workspace/'sealed',temp_root=workspace,navigation_root=plan['navigation_root'])
    print('m03-worker:qr-independent-maps-capacity',flush=True)
    verified=verify_resolution_geometry(plan['geometry_root'],plan['inspection'],metadata,request,plan['request_root'],
        workspace/'sealed',sealed,temp_root=workspace,navigation_root=plan['navigation_root'])
    core._write_member(workspace,'resolution-prevalue-verification.json',base.canonical_bytes(verified))
    current_proof=base.strict_json(base.read_bounded(core._plain_path(workspace/'sealed/resolution-capacity-proof.json'),4194304))
    if sealed['geometry']!=prior or full_capacity(sealed['geometry'],current_proof)!=planned:
        raise core.SurveyError('custody_mismatch','seal')
    documents=original_documents or dict(metadata=base.canonical_bytes(metadata),request=base.canonical_bytes(request))
    execution=create_execution(sealed['geometry'],metadata,request,current_proof,
        metadata_bytes=documents['metadata'],request_bytes=documents['request'])
    core._write_member(workspace,'qr-execution.json',base.canonical_bytes(execution))
    # First magnetic/sigma decoding is strictly after the independently verified
    # fresh16-map/prospective97-fit proof, under the same real native Job.
    from magnetic_line_survey_measurements import decode_measurements
    print('m03-worker:qr-original-measurements',flush=True)
    measurements=decode_measurements(plan['csv_path'],plan['geometry_root'],plan['inspection'],workspace/'measurements')
    from magnetic_line_survey_corrections import correct_instrument
    corrected=correct_instrument(workspace/'sealed',sealed,plan['geometry_root'],plan['inspection'],workspace/'measurements',
        measurements,metadata,request,workspace/'corrected',temp_root=workspace,
        auxiliary_roots=plan['auxiliary_roots'],reference_definitions=plan['reference_definitions'])
    from magnetic_line_survey_physical_fit_qr import fit_corrected
    print('m03-worker:qr-all96-inner-then-final',flush=True)
    fitted=fit_corrected(workspace/'sealed',sealed,workspace/'measurements',measurements,workspace/'corrected',corrected,
        metadata,request,workspace/'fit',temp_root=workspace,job_handle=job_handle)
    from magnetic_line_survey_grid_qr import predict_grids
    print('m03-worker:qr-full-global-grids',flush=True)
    grids=predict_grids(workspace/'sealed',sealed,workspace/'fit',fitted,metadata,request,
        workspace/'grids',temp_root=workspace,job_handle=job_handle)
    from magnetic_line_survey_environment_qr import environment_identity
    environment=environment_identity(package_root,job_handle=job_handle)
    from magnetic_line_survey_result_qr import assemble_fixed_result
    print('m03-worker:qr-semantic-result',flush=True)
    result=assemble_fixed_result(workspace,sealed,measurements,corrected,fitted,grids,metadata,request,
        plan['request_root'],plan['navigation_root'],plan['auxiliary_roots'],plan['reference_definitions'],
        run_id=plan['run_id'],environment=environment,temp_root=workspace,job_handle=job_handle,
        execution=execution,original_documents=original_documents)
    core._write_member(Path(workspace),'qr-fit-ready.json',base.canonical_bytes(dict(
        schema='m03-qr-fit-ready/1',original=metadata['original'],rows=metadata['arrays'][0]['shape'][0],
        fit_sha256=base.digest(fitted),fit_count=fitted['fit']['fit_count'],evaluation_count=fitted['evaluation_count'],
        policy_epoch=schema.POLICY_EPOCH,outer_status='opened_authored_diagnostic',field_acceptance='unresolved',
        full_result='assembled',result_sha256=base.digest(result),host_admission='not_established')))
    return 0
