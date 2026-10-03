"""Source-pinned ordinary weighted L2 primitives; no public API/field claim.

The private problem constructor is for admitted native requests and independent
small mathematical controls. No user-prepared engine/kernel objects are accepted.
"""

import numpy as np
import scipy.linalg as la
import scipy.sparse as sp
from simpeg import data, data_misfit, maps, regularization

import gravity_forward as forward
import gravity_survey_l2 as survey


RUNTIME_EPOCH = 'm02-survey-l2-cpu-1'
FORWARD_SOURCE = '46d205a453147cc18697464e4a6deda2920d0d88307e366b6fd336d9a1ac07d5'
BETA_CANDIDATES = (.0001, .001, .01, .1, 1., 10., 100., 1000.)


def _weights(noise, indices):
    """Independent principal-block symmetric whitening, not joint conditioning."""
    survey._keys(noise, ('kind', 'values'), 'private noise')
    survey._enum(noise['kind'], ('diagonal_sd', 'full_covariance'), 'noise.kind')
    values = noise['values']
    survey._array(values, (None,) if noise['kind'] == 'diagonal_sd' else (None, None), 'noise.values')
    n = len(values)
    if not 1 <= n <= 2048 or (noise['kind'] == 'full_covariance' and values.shape != (n, n)):
        raise ValueError('noise: count/shape outside ordinary covariance cap')
    survey._array(indices, (None,), 'noise.rows', np.int64)
    if not 1 <= len(indices) <= n: raise ValueError('noise: marginal row count')
    if not np.isfinite(values).all() or np.any(indices < 0) or np.any(indices >= n):
        raise ValueError('noise: nonfinite values or invalid rows')
    if noise['kind'] == 'diagonal_sd':
        if np.any(values <= 0): raise ValueError('noise: positive SD required, no floor')
        with np.errstate(over='raise', divide='raise', invalid='raise'):
            inverse = 1. / values[indices]
        if not np.isfinite(inverse).all(): raise ValueError('noise: nonfinite inverse SD')
        return sp.diags(inverse, format='csr')
    if not np.array_equal(values, values.T): raise ValueError('noise: exact declared covariance symmetry required')
    cov = values[np.ix_(indices, indices)]
    try:
        chol = la.cholesky(cov, lower=True, check_finite=True, overwrite_a=False)
        eigenvalues, vectors = la.eigh(cov, driver='evd', check_finite=True, overwrite_a=False)
    except la.LinAlgError as exc:
        raise ValueError('noise: covariance must be SPD without jitter') from exc
    if not np.isfinite(eigenvalues).all() or eigenvalues[0] <= 0 or eigenvalues[-1] / eigenvalues[0] > 1e8:
        raise ValueError('noise: positive eigenvalues and condition<=1e8 required')
    with np.errstate(over='raise', divide='raise', invalid='raise'):
        weights = (vectors * (1. / np.sqrt(eigenvalues))) @ vectors.T
        # Only the derived W is symmetrized. Original covariance is not changed.
        weights = (weights + weights.T) * .5
        identity = np.eye(len(cov))
        inverse_chol = la.solve_triangular(chol, identity, lower=True, check_finite=True)
        precision = inverse_chol.T @ inverse_chol
        normalized_identity_error = la.norm(weights @ cov @ weights.T - identity, ord=np.inf)
        relative_precision_error = la.norm(weights.T @ weights - precision, ord=np.inf) / la.norm(precision, ord=np.inf)
    if (not np.isfinite(weights).all() or not np.isfinite(normalized_identity_error)
            or not np.isfinite(relative_precision_error) or normalized_identity_error > 1e-7
            or relative_precision_error > 1e-7):
        raise ValueError('noise: symmetric precision-root validation failed')
    return sp.csr_matrix(weights)


def _build_problem(request, observations, noise, prior, rows, beta_candidate):
    """Real fitting simulation and official objectives; never substitute a kernel."""
    forward._runtime()
    survey._array(rows, (None,), 'fit_rows', np.int64)
    survey._array(observations, (len(request['stations']['receivers_m']),), 'observations')
    if not 1 <= len(rows) <= 2048 or np.any(rows < 0) or np.any(rows >= len(observations)):
        raise ValueError('fit: row count/identity invalid')
    survey._float(beta_candidate, 'beta_candidate', positive=True)
    active_count = int(np.count_nonzero(request['mesh']['active']))
    receivers = request['stations']['receivers_m'][rows]
    verified = forward.forward_gravity({'schema': 'gravity-prism-forward-request-1', 'frame': request['frame'],
                                       'mesh': request['mesh'], 'receivers_m': receivers,
                                       'density_kg_m3': np.zeros(active_count), 'engine': request['engine']})
    mesh_spec = request['mesh']
    tensor = forward.discretize.TensorMesh([mesh_spec[key] for key in ('hx_m', 'hy_m', 'hz_m')],
                                          origin=mesh_spec['origin_m'])
    rx = forward.gravity.receivers.Point(receivers, components='gz')
    field = forward.gravity.sources.SourceField(receiver_list=[rx])
    geometry = verified['geometry']
    fitting = forward.gravity.simulation.Simulation3DIntegral(
        tensor, survey=forward.gravity.survey.Survey(field), active_cells=mesh_spec['active'],
        rhoMap=maps.IdentityMap(nP=active_count), engine='geoana', store_sensitivities='ram',
        sensitivity_dtype=np.float64, n_processes=1)
    corners = fitting._nodes[fitting._unique_inv.T]
    if not np.array_equal(corners, geometry['active_cell_bounds_m'][:, forward.CORNER_COLUMNS]):
        raise RuntimeError('engine: fitting prism corners differ from independently verified forward geometry')
    kernel = fitting.G
    if not np.isfinite(kernel).all() or not np.allclose(
            kernel / 1000., verified['jacobian_mgal_per_kg_m3'], rtol=1e-10, atol=1e-12):
        raise RuntimeError('engine: physical fitting Jacobian identity mismatch')
    weights = _weights(noise, rows)
    fixed_background = request['background_mgal'][rows]
    # Official simulation predicts Gq. Move independently fixed b to the data;
    # its residual is still Gq+b-d. No intercept/background fit is introduced.
    engine_data = data.Data(fitting.survey, dobs=observations[rows] - fixed_background)
    misfit = data_misfit.L2DataMisfit(data=engine_data, simulation=fitting)
    misfit.W = weights
    volume = float(np.sum(geometry['active_cell_volumes_m3']))
    scale = prior['density_scale_kg_m3'] / 1000.
    with np.errstate(over='raise', invalid='raise', divide='raise', under='raise'):
        normalizer = 1. / (volume * scale**2)
        alphas = prior['lengths_m']**2 * normalizer
        reference = prior['reference_kg_m3'] / 1000.
    if not np.isfinite(normalizer) or normalizer <= 0 or not np.isfinite(alphas).all() or np.any(alphas <= 0):
        raise ValueError('prior: finite positive physical regularization required')
    reg = regularization.WeightedLeastSquares(
        tensor, active_cells=mesh_spec['active'], mapping=maps.IdentityMap(nP=active_count),
        reference_model=reference, reference_model_in_smooth=True, alpha_s=normalizer,
        alpha_x=float(alphas[0]), alpha_y=float(alphas[1]), alpha_z=float(alphas[2]),
        alpha_xx=0., alpha_yy=0., alpha_zz=0.)
    return {'simulation': fitting, 'misfit': misfit, 'regularization': reg, 'geometry': geometry,
            'beta_engine': len(rows) * beta_candidate, 'beta_candidate': beta_candidate,
            'rows': survey._readonly(rows), 'background': survey._readonly(fixed_background),
            'reference_q': survey._readonly(reference),
            'alpha': (normalizer, float(alphas[0]), float(alphas[1]), float(alphas[2]))}
