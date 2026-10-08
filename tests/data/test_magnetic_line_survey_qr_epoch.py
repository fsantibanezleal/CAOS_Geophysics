"""Independent small QR controls/strict adverse contracts, not field fixtures."""
from copy import deepcopy
import itertools
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'data-pipeline'))
import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_contract_v2 as previous
import magnetic_line_survey_contract_qr as schema
import magnetic_line_survey_qr as qr
import magnetic_line_survey_representation_qr as representation
import magnetic_line_survey_capacity_v2 as original_capacity
import magnetic_line_survey_qr_execution as execution
from magnetic_line_survey_physical_fit_qr import select_resolution_candidate
from test_magnetic_line_survey_hp import dense_case


@pytest.fixture(scope='module')
def receipt():
    _,xyz,sources,_,y,_,_,_=dense_case(False)
    return qr.solve_qr(core.GlobalOperator(xyz,sources),y,.0001)['receipt']


def test_actual_native_receipt_and_exact_separate_policy(receipt):
    assert schema.validate('QRSolve',receipt)==receipt
    assert schema.validate('QRPolicy',schema.POLICY)==schema.POLICY
    assert not {'istop','iterations','conda_estimate','normar_estimate'}&receipt.keys()
    with pytest.raises(core.SurveyError):previous.validate('SolverReceipt',receipt)
    assert schema.SCHEMAS['SurveyResult']['schema']==base.literal('magnetic-line-survey-result/3')
    assert previous.SCHEMAS['SurveyResult']['schema']==base.literal('magnetic-line-survey-result/2')


@pytest.mark.parametrize('change',[
    'extra','epoch','istop','iterations','native_info','inverse_info','bool_status','B_domain','A_estimate',
    'condition_limit','diagonal','dimensions','dense_bytes','dense_slots','lwork','gradient','objective',
    'relative_ratio','nan','inf','blas_hash','blas_thread','duplicate_blas','wrapper','verdict'])
def test_actual_success_receipt_cannot_hide_adverse_metadata(receipt,change):
    wrong=deepcopy(receipt)
    if change=='extra':wrong['unused']='allowed'
    elif change=='epoch':wrong['epoch']='resolution_v2'
    elif change in ('istop','iterations'):wrong[change]=0
    elif change=='native_info':wrong['lapack_info']=2
    elif change=='inverse_info':wrong['triangular_inverse_info']=1
    elif change=='bool_status':wrong['lapack_info']=False
    elif change=='B_domain':wrong['condition_domain']='A recurrence estimate'
    elif change=='A_estimate':wrong['conda_estimate']=wrong['condition_upper_bound']
    elif change=='condition_limit':wrong['condition_upper_bound']=1e8
    elif change=='diagonal':wrong['triangular_diagonal_min_abs']=0.
    elif change=='dimensions':wrong['augmented_rows']+=1
    elif change=='dense_bytes':wrong['dense_capacity']['augmented_matrix_bytes']-=8
    elif change=='dense_slots':wrong['dense_capacity']['augmented_buffer_slots']=1
    elif change=='lwork':wrong['lwork']+=1
    elif change=='gradient':
        wrong['original_diagnostics']['stationarity_relative']=1.00001e-9
        wrong['original_diagnostics']['stationarity_inf']=1.00001e-9*wrong['original_diagnostics']['gradient_denominator']
    elif change=='objective':wrong['original_diagnostics']['objective']+=1.
    elif change=='relative_ratio':wrong['original_diagnostics']['stationarity_relative']=0.
    elif change=='nan':wrong['original_diagnostics']['stationarity_inf']=float('nan')
    elif change=='inf':wrong['condition_upper_bound']=float('inf')
    elif change=='blas_hash':wrong['engine_identity']['blas'][0]['sha256']='0'*64
    elif change=='blas_thread':wrong['engine_identity']['blas'][0]['threads']=2
    elif change=='duplicate_blas':wrong['engine_identity']['blas'][1]=wrong['engine_identity']['blas'][0]
    elif change=='wrapper':wrong['engine_identity']['flapack_sha256']='0'*64
    else:wrong['numerical_verdict']='pass'
    with pytest.raises(core.SurveyError):schema.validate('QRSolve',wrong)


def test_actual_qr_table_custody_roundtrip_and_legacy_refusal(tmp_path,receipt):
    # Repeated actual small-control receipts test encoding, not a claimed
    # 96-fit scientific run. The physical owner verifier must prove all maps.
    rows=[dict(source_geometry_index=g,fold_id=fold,depth_m=depth,damping=.0001,solve=receipt,
        scored=3,excluded=0,rmse_nT=1.,verdict=dict(overall='pass',gates=[dict(gate_id='solve',verdict='pass',
            evidence_sha256=base.digest(receipt),reason=None)],numerical_success=True,reasons=[]))
        for g,depth,fold,_ in itertools.product(range(4),(200.,500.),('A','B','C'),range(4))]
    ref=representation.write_table(tmp_path,'qr-control','candidate_fit_qr_v3',rows)
    reader=representation.Reader(tmp_path)
    assert list(reader.table(ref))==rows
    assert base.strict_json(reader.member(ref['manifest']))['schema']=='magnetic-line-table-manifest/3'
    reader.reject_unknown()
    with pytest.raises(core.SurveyError):previous.validate('TableRef',ref)
    for count in (25,95,97):
        wrong=deepcopy(ref);wrong['rows']=count
        with pytest.raises(core.SurveyError):schema.validate('TableRef',wrong)
    identity_rows=[dict(sequence=index,source_geometry_index=0,fold_id='A' if index<96 else 'final',
        depth_m=200.,damping=.0001,solve=receipt) for index in range(97)]
    root=tmp_path/'identity';root.mkdir()
    table=representation.write_table(root,'qr-identities','qr_solve_identity',identity_rows)
    assert list(representation.Reader(root).table(table))==identity_rows


def test_selection_has_all32_training_only_means_and_exact_original_ties():
    candidates=[dict(source_geometry_index=g,depth_m=depth,damping=damping,mean_rmse_nT=7.)
        for g,depth,damping in itertools.product(range(4),(200.,500.),(.0001,.01,1.,100.))]
    assert select_resolution_candidate(candidates)==candidates[7]
    for wrong in (candidates[:-1],candidates[::-1],[candidates[0]]*32):
        with pytest.raises(core.SurveyError):select_resolution_candidate(wrong)
    wrong=deepcopy(candidates);wrong[0]['outer_rmse_nT']=0.
    with pytest.raises(core.SurveyError):select_resolution_candidate(wrong)


def test_original_s1_rule_not_a_qr_numerics_pass():
    # Exact unchanged adverse historical pair, not new acquisition values.
    assert 18.799740863534037>max(1e-6,.05*(.25966396538773057/.05))
    assert schema.SCHEMAS['FitReceipt']['fit_count']==base.literal(97)
    assert schema.SCHEMAS['SurveyResult']['policy_epoch']==base.literal(schema.POLICY_EPOCH)


def test_complete_full_epoch_proof_adds_exact_c_member_before_allocation():
    training=[294,168,195,249];validation=[33,66,66,33]
    sources=[[66,45,48,57],[148,91,101,127],[240,137,164,203],[292,168,193,247]]
    old,proof=original_capacity.plan_capacity(363,training,validation,sources,logical_members=125,arrays=104)
    geometry=dict(rows=363,source_counts_by_geometry=sources,arrays=[
        dict(array_id=f'f{f}-{name}',shape=[counts[f]]) for f in range(4)
        for name,counts in (('train',training),('validation',validation))])
    cap,new=execution.full_capacity(geometry,dict(capacity=old,proof=proof))
    assert new['logical_members']==128 and new['arrays']==104
    assert new['mandatory_fit_count']==new['maximum_fit_count']==97
    assert new['final_scaled_coefficients_bytes']==8*292
    assert new['additional_physical_members']==5
    assert cap['profile']=='m03-offline-direct-qr/1'
    assert cap['scratch_bound_bytes']<=core.SCRATCH_LIMIT
    proof['logical_members']=191
    with pytest.raises(core.SurveyError):execution.full_capacity(geometry,dict(capacity=old,proof=proof))


def test_execution_source_inventory_is_complete_and_separate():
    from hashlib import sha256
    source_hashes=execution.source_identity()
    assert len(source_hashes)==len(execution.SOURCES)
    assert source_hashes['magnetic_line_survey.py']=='f59c8fde2a3094bf0cb9c06b0bbcff5392a54dbda08a208f986a35365f19f6a0'
    assert source_hashes['magnetic_lines.py']=='347556cd6a3be788470a0af5638d113f95d750dfa7be9a263272a2fe15075f66'
    assert source_hashes['magnetic_line_survey_contract_v2.py']==sha256(Path(previous.__file__).read_bytes()).hexdigest()
    assert {'magnetic_line_survey_worker_qr.py','magnetic_line_survey_result_qr.py',
        'magnetic_line_survey_local_worker_qr.py','magnetic_line_survey_export_qr.py'}<=source_hashes.keys()
