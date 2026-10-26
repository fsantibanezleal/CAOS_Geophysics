"""Contained owner execution of the immutable, already-opened original S1.

This is a diagnostic component of the future complete owner workflow, NOT a
provider adapter, field result, deployment route or public activation path.
"""
from __future__ import annotations

from pathlib import Path

import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_contract as schema
import magnetic_line_survey_io as io


ORIGINAL_S1_SHA256 = 'ac28e5f7c8344b94ebe0c408484eede8ade5a4074c8ef44661bcfe774ff0bfae'


def run_opened_s1(plan, workspace, job_handle):
    from magnetic_line_survey_runtime import require_job
    require_job(job_handle)
    if type(plan) is not dict or set(plan)!={'schema','mode','csv_path','geometry_root','inspection','metadata','request','request_root'} or \
       plan['schema']!='m03-global-control-plan/1' or plan['mode']!='opened_s1_diagnostic':
        raise core.SurveyError('invalid_contract','seal')
    metadata = schema.validate('SurveyInput',plan['metadata'])
    request = schema.validate('SurveyRequest',plan['request'])
    if metadata['source_kind']!='original_synthetic_acquisition' or metadata['authored_control'] is None or \
       metadata['authored_control']['regime']!='S1' or metadata['original']['csv_sha256']!=ORIGINAL_S1_SHA256 or \
       metadata['original']['csv_bytes']!=45539 or request['operations']:
        raise core.SurveyError('metadata_ineligible','fit')
    workspace = io.external_path(workspace)
    from magnetic_line_survey_seal import seal_geometry
    from magnetic_line_survey_measurements import decode_measurements
    from magnetic_line_survey_fit import blocked_global_diagnostic
    print('m03-worker:seal',flush=True)
    sealed = seal_geometry(plan['geometry_root'],plan['inspection'],metadata,request,plan['request_root'],
                           workspace/'sealed',temp_root=workspace)
    print('m03-worker:measurements',flush=True)
    measurements = decode_measurements(plan['csv_path'],plan['geometry_root'],plan['inspection'],workspace/'measurements')
    print('m03-worker:global-fits',flush=True)
    result = blocked_global_diagnostic(workspace/'sealed',sealed,workspace/'measurements',measurements,
        metadata,request,workspace/'fit',temp_root=workspace,job_handle=job_handle)
    # Bind all algorithm returns to the original; do not upgrade the S1
    # predictive failure or missing physical-reference admission on convergence.
    core._write_member(workspace,'diagnostic-ready.json',base.canonical_bytes(dict(schema='m03-opened-s1-ready/1',
        original_sha256=ORIGINAL_S1_SHA256,result_sha256=base.digest(result),fit_count=result['fit']['fit_count'],
        evaluation_count=result['evaluation_count'],s1_predictive_verdict=result['s1_predictive_verdict'],
        field_acceptance='unresolved',scientific_acceptance='not_established')))
    return 0
