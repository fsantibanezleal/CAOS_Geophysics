"""Post-freeze independent S2 model integration and retained adverse verdicts.

Uses authored evaluator bodies only AFTER result freeze. No evaluator values
enter a request, model fitting, candidate choice, field datum or uncertainties.
"""

import math

import numpy as np


def integrated_truth(mesh, bodies):
    """Exact rectangular body/cell overlap, not truth sampled at inverse centers."""
    widths = [np.array(mesh[k]['data'], dtype=np.float64) for k in ('widths_x_m', 'widths_y_m', 'widths_z_m')]
    origin = np.array(mesh['origin_m']['data'], dtype=np.float64)
    active = np.array(mesh['active']['data'], dtype=bool)
    if any(not np.isfinite(w).all() or np.any(w <= 0.) for w in widths) or active.size != math.prod(map(len, widths)):
        raise ValueError('Exact finite nonuniform evaluation mesh required')
    edges = [o+np.r_[0., np.cumsum(w)] for o, w in zip(origin, widths)]
    ids = np.flatnonzero(active)
    index = np.unravel_index(ids, tuple(map(len, widths)), order='F')
    lo = np.column_stack([edge[i] for edge, i in zip(edges, index)])
    hi = np.column_stack([edge[i+1] for edge, i in zip(edges, index)])
    volumes = np.prod(hi-lo, axis=1)
    moments, first = np.zeros(len(ids)), np.zeros((len(ids), 3))
    for body in bodies:
        bounds = np.array(body['bounds_m'], dtype=np.float64).reshape(3, 2)
        chi = body['chi_si']
        if (not np.isfinite(bounds).all() or np.any(bounds[:, 1] <= bounds[:, 0])
                or type(chi) not in (int, float) or not math.isfinite(chi) or chi < 0.):
            raise ValueError('Declared finite independent rectangle and SI susceptibility required')
        left, right = np.maximum(lo, bounds[:, 0]), np.minimum(hi, bounds[:, 1])
        overlap = np.prod(np.maximum(0., right-left), axis=1)
        mass = chi*overlap
        moments += mass
        first += mass[:, None]*(left+right)/2.
    total = float(moments.sum())
    return dict(active_indices=ids, volumes_m3=volumes, centers_m=(lo+hi)/2.,
        cell_chi_si=moments/volumes, susceptibility_integral_si_m3=total,
        centroid_m=None if total == 0. else first.sum(axis=0)/total)


def evaluate_model(mesh, bodies, chi_si):
    truth = integrated_truth(mesh, bodies)
    chi = np.asarray(chi_si, dtype=np.float64)
    if chi.shape != truth['cell_chi_si'].shape or not np.isfinite(chi).all() or np.any(chi < 0.):
        raise ValueError('Complete finite nonnegative frozen active-cell model required')
    weight = chi*truth['volumes_m3']
    integral = float(weight.sum())
    center = None if integral == 0. else np.sum(weight[:, None]*truth['centers_m'], axis=0)/integral
    actual_centroid = None if center is None else center.tolist()
    true_centroid = None if truth['centroid_m'] is None else truth['centroid_m'].tolist()
    discrepancy = None if center is None or true_centroid is None else float(np.linalg.norm(center-truth['centroid_m']))
    concentration = None if integral == 0. else float(np.sum(weight**2)/integral**2)
    return dict(kind='authored_synthetic_model_evaluation_only', truth_integration='exact_rectangle_cell_overlap',
        susceptibility_integral_unit='SI*m^3_not_kg', truth_integral_si_m3=truth['susceptibility_integral_si_m3'],
        fitted_integral_si_m3=integral, integral_error_si_m3=integral-truth['susceptibility_integral_si_m3'],
        truth_centroid_m=true_centroid, fitted_centroid_m=actual_centroid, centroid_error_m=discrepancy,
        volume_weighted_chi_rms_si=float(np.sqrt(np.dot(truth['volumes_m3'], (chi-truth['cell_chi_si'])**2)/truth['volumes_m3'].sum())),
        cell_weight_concentration=concentration, field_model_truth=None, geological_truth_claimed=False)


def adverse_verdict(adverse, matched_a):
    """Unchanged >=20% raw-RMS degradation gate, never a remanence classifier."""
    if adverse is None or matched_a is None:
        return dict(verdict='unresolved_unable_to_evaluate', rms_degradation_fraction=None,
                    reason='No complete frozen adverse and matched-A result; no partial-metric substitute')
    if matched_a <= 0. or not all(math.isfinite(x) and x >= 0. for x in (adverse, matched_a)):
        return dict(verdict='unresolved_unable_to_discriminate', rms_degradation_fraction=None,
                    reason='Finite positive matched-A RMS required; no zero division or new threshold')
    degradation = adverse/matched_a-1.
    return dict(verdict='adverse_degradation_demonstrated' if degradation >= .2 else 'unresolved_unable_to_discriminate',
                rms_degradation_fraction=degradation, reason='Fixed incorrect hypothesis; not a remanence/field-direction classifier')
