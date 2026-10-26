"""Fixed prospective resolution-v2 DAG; no historical holdout upgrade."""
from pathlib import Path

import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_contract_v2 as schema
import magnetic_line_survey_io as io


def run_resolution_plan(plan,workspace,job_handle,*,package_root,original_documents=None):
    from magnetic_line_survey_runtime import require_job
    require_job(job_handle)
    core._closed(plan,'schema csv_path geometry_root inspection metadata request request_root navigation_root '
        'auxiliary_roots reference_definitions run_id','seal')
    if plan['schema']!='m03-resolution-fit-plan/1':
        raise core.SurveyError('invalid_contract','seal')
    metadata=schema.validate('SurveyInput',plan['metadata'])
    request=schema.validate('SurveyRequest',plan['request'])
    workspace=io.external_path(workspace)
    from magnetic_line_survey_resolution_geometry import seal_resolution_geometry,verify_resolution_geometry
    print('m03-worker:resolution-fresh-value-free-seal',flush=True)
    sealed=seal_resolution_geometry(plan['geometry_root'],plan['inspection'],metadata,request,plan['request_root'],
        workspace/'sealed',temp_root=workspace,navigation_root=plan['navigation_root'])
    print('m03-worker:resolution-independent-maps-capacity',flush=True)
    verified=verify_resolution_geometry(plan['geometry_root'],plan['inspection'],metadata,request,plan['request_root'],
        workspace/'sealed',sealed,temp_root=workspace,navigation_root=plan['navigation_root'])
    core._write_member(workspace,'resolution-prevalue-verification.json',base.canonical_bytes(verified))
    # First magnetic/sigma decoding is strictly after the independently verified
    # fresh16-map/prospective97-fit proof, under the same real native Job.
    from magnetic_line_survey_measurements import decode_measurements
    print('m03-worker:resolution-original-measurements',flush=True)
    measurements=decode_measurements(plan['csv_path'],plan['geometry_root'],plan['inspection'],workspace/'measurements')
    from magnetic_line_survey_corrections import correct_instrument
    corrected=correct_instrument(workspace/'sealed',sealed,plan['geometry_root'],plan['inspection'],workspace/'measurements',
        measurements,metadata,request,workspace/'corrected',temp_root=workspace,
        auxiliary_roots=plan['auxiliary_roots'],reference_definitions=plan['reference_definitions'])
    from magnetic_line_survey_physical_fit import fit_corrected
    print('m03-worker:resolution-all96-inner-then-final',flush=True)
    fitted=fit_corrected(workspace/'sealed',sealed,workspace/'measurements',measurements,workspace/'corrected',corrected,
        metadata,request,workspace/'fit',temp_root=workspace,job_handle=job_handle)
    from magnetic_line_survey_grid import predict_grids
    print('m03-worker:resolution-full-global-grids',flush=True)
    grids=predict_grids(workspace/'sealed',sealed,workspace/'fit',fitted,metadata,request,
        workspace/'grids',temp_root=workspace,job_handle=job_handle)
    from magnetic_line_survey_environment import environment_identity
    environment=environment_identity(package_root,job_handle=job_handle)
    from magnetic_line_survey_result import assemble_fixed_result
    print('m03-worker:resolution-semantic-result',flush=True)
    result=assemble_fixed_result(workspace,sealed,measurements,corrected,fitted,grids,metadata,request,
        plan['request_root'],plan['navigation_root'],plan['auxiliary_roots'],plan['reference_definitions'],
        run_id=plan['run_id'],environment=environment,temp_root=workspace,job_handle=job_handle,
        original_documents=original_documents)
    core._write_member(Path(workspace),'resolution-fit-ready.json',base.canonical_bytes(dict(
        schema='m03-resolution-fit-ready/1',original=metadata['original'],rows=metadata['arrays'][0]['shape'][0],
        fit_sha256=base.digest(fitted),fit_count=fitted['fit']['fit_count'],evaluation_count=fitted['evaluation_count'],
        policy_epoch='resolution_v2',outer_status='opened_authored_diagnostic',field_acceptance='unresolved',
        full_result='assembled',result_sha256=base.digest(result),host_admission='not_established')))
    return 0
