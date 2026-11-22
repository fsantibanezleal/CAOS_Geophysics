"""Independent recurrence/oracle controls; never replace the original IR-C06.

These test actual native stage accuracy and literal scaled-p1 semantics, not
IRLS scientific acceptance. No production optimizer/oracle fallback is added.
"""
from time import monotonic

import numpy as np

import gravity_irls as irls
from test_gravity_irls import native_problem, policy


def equations(problem):
    """Derive four positive WLS terms, excluding zero second-order terms."""
    reg = problem['regularization']
    components = [(alpha, c) for alpha, c in zip(reg.multipliers, reg.objfcts) if alpha > 0.]
    assert len(components) == 4 and not np.any(problem['reference_q'])
    a = np.asarray(problem['misfit'].W @ problem['simulation'].G)
    d = np.asarray(problem['misfit'].W @ problem['misfit'].data.dobs)
    h0 = a.T @ a
    for alpha, component in components[1:]:
        b = (np.sqrt(problem['beta_engine'] * alpha) * component.W @
             component.f_m_deriv(problem['reference_q'])).toarray()
        h0 += b.T @ b
    alpha, smallness = components[0]
    np.testing.assert_array_equal(smallness.f_m_deriv(problem['reference_q']).toarray(), np.eye(12))
    v = problem['beta_engine'] * alpha * smallness.W.diagonal() ** 2
    return h0, a.T @ d, v, components


def scaled_weights(q, eps):
    maximum = np.max(np.abs(q))
    scale = np.sqrt(maximum ** 2 + eps ** 2) if maximum != 0. else 1.
    return scale / np.sqrt(q ** 2 + eps ** 2)


def test_actual_original21_native_states_match_independent_recursive_optima(record_property):
    problem, prior = native_problem(null=False)
    parts = []
    actual = irls._solve_partition(problem, prior, policy(), monotonic() + 120., _stage_solutions=parts)
    assert len(parts) == 21 and all(p['status'] == 'converged' for p in parts)
    assert actual['iterations'] <= 200
    h0, rhs, v, components = equations(problem)
    previous = actual['l2_initialization']['model_kg_m3'] / 1000.
    initial = tuple(max(f, float(np.max(np.abs(c.f_m(previous)))))
                    for f, (_, c) in zip(policy()['epsilon_floor'], components))
    prior_weights = None
    changes = []
    errors = []
    for k in range(21):
        eps = irls._epsilon(initial[0], policy()['epsilon_floor'][0], k)
        w = scaled_weights(previous, eps)
        h = h0 + np.diag(v * w)
        q = np.linalg.solve(h, rhs)
        assert np.all(q > prior['lower_kg_m3'] / 1000.)
        assert np.all(q < prior['upper_kg_m3'] / 1000.)
        # Positive smallness is a lower eigenvalue bound, hence each oracle
        # interior optimum is unique. This is not a global IRLS guarantee.
        assert np.min(v * w) > 0.
        assert np.linalg.eigvalsh(h)[0] >= .999999 * np.min(v * w)
        np.testing.assert_allclose(parts[k]['q'], q, rtol=0., atol=2e-12)
        np.testing.assert_allclose(actual['stages'][k]['smallness_weights'], w, rtol=2e-10, atol=2e-12)
        errors.append(float(np.max(np.abs(parts[k]['q'] - q))))
        if k:
            changes.append({'model_relative': float(np.max(np.abs(q - previous)) / max(1., np.max(np.abs(previous)))),
                            'weights_relative': float(np.max(np.abs(w - prior_weights)) / max(1., np.max(np.abs(prior_weights))))})
        previous, prior_weights = q, w
    for computed, observed in zip(changes, actual['irls_terminal']['stage_changes']):
        for key in computed:
            np.testing.assert_allclose(computed[key], observed[key], rtol=0., atol=2e-10)
    record_property('scope', 'native per-stage accuracy and prescribed recurrence only; original IR-C06 unchanged')
    record_property('max_native_q_error_inf', max(errors))
    record_property('independent_final_changes', repr(changes[-3:]))


def test_actual_floor_weight_map_derivative_matches_independent_finite_difference():
    # Nonnull original physical fixture, strictly unique maximum branch, fixed
    # approved floor. This evaluates weights, not additional optimization stages.
    problem, _ = native_problem(null=False)
    q = np.linspace(-.013, .011, 12)
    eps = policy()['epsilon_floor'][0]
    maximum, ell = np.max(np.abs(q)), int(np.argmax(np.abs(q)))
    assert np.sum(np.abs(q) == maximum) == 1
    scale = np.sqrt(maximum ** 2 + eps ** 2)
    denom = np.sqrt(q ** 2 + eps ** 2)
    jacobian = np.diag(-scale * q / denom ** 3)
    jacobian[:, ell] += q[ell] / scale / denom
    initial = (.013, .001, .001, .001)
    for j in range(12):
        perturbation = np.eye(12)[j] * 1e-8
        plus = irls._build_stage(problem, q + perturbation, policy(), 17, initial)['weights'][0]
        minus = irls._build_stage(problem, q - perturbation, policy(), 17, initial)['weights'][0]
        np.testing.assert_allclose((plus - minus) / 2e-8, jacobian[:, j], rtol=2e-7, atol=2e-6)
