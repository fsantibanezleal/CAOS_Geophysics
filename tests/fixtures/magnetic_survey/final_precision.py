"""TEST ONLY independent final surrogate/true-p1 observer, never production CG."""
import numpy as np
from scipy.linalg import solve_triangular
from scipy.optimize import lsq_linear


def independent_kernel(doc, rows):
    import choclo
    from choclo.constants import VACUUM_MAGNETIC_PERMEABILITY
    geometry, field = doc['geometry'], doc['inducing_field']
    mesh = geometry['mesh']
    widths = [np.array(mesh[k]['data'], dtype=float) for k in ('widths_x_m', 'widths_y_m', 'widths_z_m')]
    mask = np.array(mesh['active']['data'], dtype=bool)
    edges = [origin + np.r_[0., np.cumsum(h)] for origin, h in zip(mesh['origin_m']['data'], widths)]
    indices = np.unravel_index(np.flatnonzero(mask), tuple(map(len, widths)), order='F')
    bounds = np.column_stack([edge[index+j] for edge, index in zip(edges, indices) for j in (0, 1)])
    volumes = np.prod(np.column_stack([h[index] for h, index in zip(widths, indices)]), axis=1)
    fractions = volumes / volumes.sum()
    inclination, declination = np.deg2rad([field['I_deg'], field['D_deg']])
    direction = np.array([np.cos(inclination)*np.sin(declination),
        np.cos(inclination)*np.cos(declination), -np.sin(inclination)])
    magnetization = float(field['F_nT'])*1e-9/VACUUM_MAGNETIC_PERMEABILITY*direction
    receivers = np.array(geometry['receivers_m']['data'], dtype=float).reshape(-1, 3)[list(rows)]
    vector = np.array([[[fun(*receiver, *cell, *magnetization)*1e9
        for cell in bounds] for fun in (choclo.prism.magnetic_e, choclo.prism.magnetic_n,
                                      choclo.prism.magnetic_u)] for receiver in receivers])*.01
    quantity = doc['processing']['quantity']
    if quantity == 'secondary_enu_nT':
        kernel = vector.reshape(-1, len(bounds))
    elif quantity == 'linear_tmi_nT':
        kernel = np.einsum('rck,c->rk', vector, direction)
    else:
        raise ValueError('Independent original precision is LINEAR only')
    return kernel, fractions


def compare_final(kernel, observed, noise, terms, fractions, reference, lower, upper,
                  q, stage_entry, beta, epsilon):
    """Frozen final weights: optimum comparison is NOT a true-p1 global proof."""
    if epsilon <= 0 or beta <= 0 or np.any(fractions <= 0) or not np.isclose(fractions.sum(), 1., rtol=0., atol=1e-14):
        raise ValueError('Original positive epsilon/beta/active volume fractions')
    if noise['kind'] == 'diagonal_sd':
        sd = noise['values'].ravel()
        whiten = lambda value: value/sd[:, None] if value.ndim == 2 else value/sd
        adjoint = lambda value: value/sd
    elif noise['kind'] == 'full_covariance':
        factor = np.linalg.cholesky(noise['values'])
        whiten = lambda value: solve_triangular(factor, value, lower=True)
        adjoint = lambda value: solve_triangular(factor.T, value, lower=False)
    else:
        raise ValueError('Original SD or stored covariance only')
    physical_terms = [np.sqrt(beta*t['alpha'])*t['weights'][:, None]*t['derivative'].toarray() for t in terms]
    matrix = np.vstack([whiten(kernel), *physical_terms])
    rhs = np.r_[whiten(observed.ravel()), *(t@reference for t in physical_terms)]
    oracle = lsq_linear(matrix, rhs, bounds=(lower, upper), method='bvls', tol=1e-12, max_iter=10000)
    if not oracle.success:
        raise AssertionError('Independent TEST ONLY BVLS did not converge')
    optimum = float(np.linalg.norm(matrix@oracle.x-rhs)**2)
    candidate = float(np.linalg.norm(matrix@q-rhs)**2)

    def true_gradient(model):
        delta = model-reference
        gradient = 2*kernel.T@adjoint(whiten(kernel@model-observed.ravel()))
        gradient += beta*2*fractions*delta/np.sqrt(delta*delta+epsilon*epsilon)
        for term in terms[1:]:
            derivative, weights = term['derivative'], term['weights']
            gradient += beta*2*term['alpha']*(derivative.T@(weights*weights*(derivative@delta)))
        return gradient

    initial = max(1., float(np.linalg.norm(true_gradient(stage_entry), np.inf)))
    projected = true_gradient(q)
    projected[q == lower] = np.minimum(projected[q == lower], 0.)
    projected[q == upper] = np.maximum(projected[q == upper], 0.)
    result = dict(model_inf_q=float(np.max(abs(q-oracle.x))),
        objective_relative=abs(candidate-optimum)/max(1., optimum),
        prediction_rms_nT=float(np.sqrt(np.mean((kernel@(q-oracle.x))**2))),
        normalized_kkt_inf=float(np.linalg.norm(projected, np.inf)/initial))
    if not np.isfinite(list(result.values())).all():
        raise AssertionError('Nonfinite independent precision is not acceptance')
    return result
