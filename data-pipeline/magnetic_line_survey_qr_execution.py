"""Pre-value separate full QR policy and exact resource/source binding."""
from hashlib import sha256
from pathlib import Path

import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_contract_qr as schema
from magnetic_line_survey_qr_prerequisite import _capacity
from magnetic_line_survey_environment import SOURCES as PREVIOUS_SOURCES

PREREQUISITE_SHA='a5de816bb05f879716c326996cae1492977f10e84dd0b7a920569f283493055d'
EXTRA_SOURCES=('magnetic_line_survey_qr','magnetic_line_survey_hp','magnetic_line_survey_capacity_hp',
    'magnetic_line_survey_capacity_qr','magnetic_line_survey_contract_qr','magnetic_line_survey_representation_qr',
    'magnetic_line_survey_physical_fit_qr','magnetic_line_survey_grid_qr','magnetic_line_survey_result_qr',
    'magnetic_line_survey_environment_qr','magnetic_line_survey_qr_execution','magnetic_line_survey_worker_qr',
    'magnetic_line_survey_cli_qr','magnetic_line_survey_export_qr','magnetic_line_survey_local_worker_qr','magnetic_line_survey_runtime',
    'magnetic_line_survey_worker','magnetic_line_survey_qr_prerequisite','magnetic_line_survey_qr_controls',
    'magnetic_line_survey_hp_prerequisite','magnetic_line_survey_preparation_capacity',
    'magnetic_line_survey_inspection','magnetic_line_survey_bundle')
SOURCES=tuple(dict.fromkeys((*PREVIOUS_SOURCES,*EXTRA_SOURCES)))


def full_capacity(geometry,original_proof):
    capacity,proof=_capacity(geometry,original_proof)
    capacity,proof=dict(capacity),dict(proof)
    size=8*capacity['sources']
    proof['logical_members']+=1
    proof['retained_member_bytes']+=size
    proof['additional_physical_members']+=1
    proof['final_scaled_coefficients_bytes']=size
    capacity['scratch_bound_bytes']+=size
    if proof['logical_members']>192 or capacity['scratch_bound_bytes']>core.SCRATCH_LIMIT:
        raise core.SurveyError('resource_refused','seal')
    return capacity,proof


def source_identity():
    return {name+'.py':sha256(Path(__file__).with_name(name+'.py').read_bytes()).hexdigest() for name in SOURCES}


def create_execution(geometry,metadata,request,original_proof,*,metadata_bytes,request_bytes):
    capacity,proof=full_capacity(geometry,original_proof)
    return dict(schema='m03-qr-execution/1',epoch=schema.POLICY_EPOCH,policy=schema.POLICY,
        original=geometry['original'],geometry_sha256=base.digest(geometry),
        metadata_sha256=sha256(metadata_bytes).hexdigest(),request_sha256=sha256(request_bytes).hexdigest(),
        prerequisite_sha256=PREREQUISITE_SHA,source_sha256=source_identity(),capacity=capacity,proof=proof,value_access='not_opened')


def verify_execution(execution,geometry,metadata,request,root,*,source_environment,document_hashes):
    core._closed(execution,'schema epoch policy original geometry_sha256 metadata_sha256 request_sha256 '
        'prerequisite_sha256 source_sha256 capacity proof value_access','replay')
    proof_path=Path(root)/'resolution-capacity-proof.json'
    raw=base.read_bounded(core._plain_path(proof_path),4194304)
    old=base.strict_json(raw)
    # Full scientific map verification independently reconstructs this original
    # proof too; here the new QR extension must match it exactly, not an echo.
    expected_capacity,expected_proof=full_capacity(geometry,old)
    expected_sources={item['module_name']+'.py':item['sha256'] for item in source_environment['loaded_modules']
        if item['module_name'] in SOURCES}
    if execution['schema']!='m03-qr-execution/1' or execution['epoch']!=schema.POLICY_EPOCH or \
       schema.validate('QRPolicy',execution['policy'])!=schema.POLICY or execution['original']!=metadata['original'] or \
       execution['geometry_sha256']!=base.digest(geometry) or execution['prerequisite_sha256']!=PREREQUISITE_SHA or \
       execution['metadata_sha256']!=document_hashes['metadata'] or execution['request_sha256']!=document_hashes['request'] or \
       execution['value_access']!='not_opened' or execution['capacity']!=expected_capacity or execution['proof']!=expected_proof or \
       execution['source_sha256']!=expected_sources or set(expected_sources)!={name+'.py' for name in SOURCES}:
        raise core.SurveyError('custody_mismatch','replay')
    return execution
