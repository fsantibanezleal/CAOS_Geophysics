"""Independent training-only explanation of retained original S1 failure.

This is not a parameter search or a new predictive control. Two small bounded
linear-algebra oracles run on the already selected ORIGINAL training basis.
No new outer prediction, score, production fit or replacement survey is made.
"""
from __future__ import annotations

from hashlib import sha256
import math

import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_contract as schema
import magnetic_line_survey_io as io
from magnetic_line_survey_diagnostic import ORIGINAL_S1_SHA256


def diagnose_retained_s1(plan, workspace, job_handle):
    from magnetic_line_survey_runtime import require_job
    require_job(job_handle)
    core._closed(plan, 'schema diagnostic_root original_csv retained_result_sha256 retained_seal_sha256', 'fit')
    if plan['schema'] != 'm03-training-diagnosis-plan/1':
        raise core.SurveyError('invalid_contract', 'fit')
    for key in ('retained_result_sha256', 'retained_seal_sha256'):
        base._type(plan[key], 'Hash', 'diagnosis', 0)
    root = io.external_path(plan['diagnostic_root'])
    workspace = io.external_path(workspace)
    if (workspace/'training-diagnosis.json').exists() or workspace == root:
        raise core.SurveyError('custody_mismatch', 'fit')
    raw = base.read_bounded(core._plain_path(io.external_path(plan['original_csv'], directory=False)), 45539)
    if len(raw) != 45539 or sha256(raw).hexdigest() != ORIGINAL_S1_SHA256:
        raise core.SurveyError('custody_mismatch', 'fit')
    original = base.parse_csv(raw)['rows']
    result_bytes = base.read_bounded(core._plain_path(root/'fit'/'blocked-diagnostic.json'), 2097152)
    seal_bytes = base.read_bounded(core._plain_path(root/'sealed'/'geometry-seal.json'), 2097152)
    if sha256(result_bytes).hexdigest() != plan['retained_result_sha256'] or \
       sha256(seal_bytes).hexdigest() != plan['retained_seal_sha256']:
        raise core.SurveyError('custody_mismatch', 'fit')
    result = base.strict_json(result_bytes)
    core._closed(result, 'schema fit candidate_scores evaluation_count outer_arrays outer_scored outer_total '
                        'rmse_nT signal_rms_nT s1_threshold_nT s1_predictive_verdict field_acceptance '
                        'physical_reference_admission geometry_sha256 request_sha256 original', 'fit')
    seal = schema.validate('GeometrySeal', base.strict_json(seal_bytes))
    fit = schema.validate('FitReceipt', result['fit'])
    if len(original) != 363 or seal['rows'] != 363 or result['schema'] != 'm03-global-blocked-diagnostic/1' or \
       result['geometry_sha256'] != base.digest(seal) or result['original'] != seal['original'] or \
       result['original']['csv_sha256'] != ORIGINAL_S1_SHA256 or result['s1_predictive_verdict'] != 'fail' or \
       result['evaluation_count'] != 1 or fit['fit_count'] != 25 or \
       fit['selected_depth_m'] != 500. or fit['selected_damping'] != .0001 or \
       fit['sources']['shape'] != [66, 3] or fit['column_scales']['shape'] != [66] or fit['coefficients']['shape'] != [66]:
        raise core.SurveyError('custody_mismatch', 'fit')
    for key, role, identifier in (('sources','source_position','final-sources'),
                                  ('column_scales','source_scale','final-scales'),
                                  ('coefficients','coefficient','final-coefficients')):
        ref = fit[key]
        if ref['role'] != role or ref['array_id'] != identifier or ref['mask_array_id'] is not None or \
           ref['ordered_ids_sha256'] != fit['sources']['ordered_ids_sha256']:
            raise core.SurveyError('custody_mismatch', 'fit')
    reader = io.Reader(root/'sealed')
    for ref in seal['arrays']+seal['dictionaries']:
        reader.verify(ref)
    reader.reject_unknown(extra=('geometry-seal.json',))
    trains = [ref for ref in seal['arrays'] if ref['array_id'] == 'f0-train' and ref['role'] == 'partition_index']
    if len(trains) != 1 or trains[0]['shape'] != [294]:
        raise core.SurveyError('custody_mismatch', 'fit')
    positions = list(reader.cells(trains[0]))
    if positions != sorted(set(positions)) or any(not 0 <= pos < 363 for pos in positions):
        raise core.SurveyError('custody_mismatch', 'fit')
    training = [original[pos] for pos in positions]
    training_hash = sha256(b''.join(row['row_id'].encode('ascii').ljust(64, b'\0') for row in training)).hexdigest()
    if training_hash != trains[0]['ordered_ids_sha256'] or any(row['line_id'] == 'F04' for row in training):
        raise core.SurveyError('custody_mismatch', 'fit')
    fitted_reader = io.Reader(root/'fit')
    fit_refs = [fit[key] for key in ('candidates', 'sources', 'column_scales', 'coefficients')]+result['outer_arrays']
    for ref in fit_refs:
        fitted_reader.verify(ref)  # Outer bytes custody only; never enter an oracle.
    fitted_reader.reject_unknown(extra=('blocked-diagnostic.json',))
    source_cells = list(fitted_reader.cells(fit['sources']))
    from magnetic_line_validation import source_blocks
    config = dict(version='half_open_training_blocks/1', origin_e_m=-1600., origin_n_m=-1600., block_e_m=400., block_n_m=400.,
        edge_policy='floor_half_open_positive_side', representative='unweighted_xy_mean_fsum_sorted_row_ids',
        vertical_policy='minimum_training_upward_minus_depth', max_sources=256)
    expected = source_blocks(training, config, 500.)['sources']
    if source_cells != [row[key] for row in expected for key in ('easting_m', 'northing_m', 'upward_m')]:
        raise core.SurveyError('custody_mismatch', 'fit')
    np, _ = core.engines()
    from scipy.linalg import lstsq, svd
    from threadpoolctl import threadpool_limits
    xyz = np.array([[row[key] for key in ('easting_m', 'northing_m', 'upward_m')] for row in training], dtype=np.float64)
    y = np.array([row['magnetic_nT'] for row in training], dtype=np.float64)
    sources = np.array(source_cells, dtype=np.float64).reshape(66, 3)
    q = np.array(list(fitted_reader.cells(fit['coefficients'])), dtype=np.float64)
    recorded_scales = np.array(list(fitted_reader.cells(fit['column_scales'])), dtype=np.float64)
    distance = np.sqrt(np.sum((xyz[:, None, :] - sources[None, :, :])**2, axis=2))
    if not np.isfinite(distance).all() or np.any(distance <= 0):
        raise core.SurveyError('nonconverged', 'fit')
    g = 1/distance
    scales = np.std(g, axis=0, ddof=0)
    scale_error = float(np.max(np.abs(scales-recorded_scales)/scales))
    if not np.isfinite(scales).all() or np.any(scales <= 0) or scale_error > 1e-12:
        raise core.SurveyError('nonconverged', 'fit')
    a = g/scales
    augmented = np.vstack((a, math.sqrt(.0001)*np.eye(66)))
    rhs = np.concatenate((y, np.zeros(66)))
    with threadpool_limits(limits=1):
        coefficient, _, augmented_rank, augmented_singular = lstsq(augmented, rhs, lapack_driver='gelsd')
        u, singular, _ = svd(a, full_matrices=False)
    cutoff = np.finfo(np.float64).eps * max(a.shape) * singular[0]
    rank = int(np.count_nonzero(singular > cutoff))
    projection_residual = y-u[:, :rank]@(u[:, :rank].T@y)
    oracle_prediction = a@coefficient
    prediction = g@q
    objective = float(np.sum((oracle_prediction-y)**2)+.0001*np.sum(coefficient**2))
    objective_error = abs(objective-fit['solve']['objective'])/max(objective, fit['solve']['objective'])
    rmse = lambda values: math.sqrt(math.fsum(float(v)**2 for v in values)/len(values))
    prediction_error = float(np.max(np.abs(prediction-oracle_prediction)))
    tolerance = 1e-7*max(1., rmse(oracle_prediction))
    if augmented_rank != 66 or prediction_error > tolerance or objective_error > 1e-8:
        raise core.SurveyError('nonconverged', 'fit')
    diagnosis = dict(schema='m03-original-s1-training-diagnosis/1', original_sha256=ORIGINAL_S1_SHA256,
        retained_result_sha256=plan['retained_result_sha256'], retained_seal_sha256=plan['retained_seal_sha256'],
        training_ids_sha256=training_hash, source_manifest_sha256=fit['sources']['manifest']['sha256'], rows=294, sources=66,
        depth_m=500., damping=.0001, numerical_rank=rank, numerical_rank_cutoff=float(cutoff),
        projection_rmse_nT=rmse(projection_residual), damped_oracle_rmse_nT=rmse(y-oracle_prediction),
        retained_fit_training_rmse_nT=rmse(y-prediction), independent_objective_nT2=objective,
        relative_objective_difference=objective_error, relative_scale_difference=scale_error,
        max_prediction_difference_nT=prediction_error, frozen_prediction_tolerance_nT=tolerance,
        augmented_condition=float(augmented_singular[0]/augmented_singular[-1]),
        original_s1_predictive_verdict='fail', new_outer_evaluations=0, production_fits=0, independent_training_oracles=2,
        root_cause='selected_original_basis_training_representation_error_not_observed_solver_disagreement',
        limits='Numerical training projection is not a rigorous outer-error bound or a universal 1/r impossibility result',
        field_acceptance='unresolved')
    core._write_member(workspace, 'training-diagnosis.json', base.canonical_bytes(diagnosis))
    return 0
