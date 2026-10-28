from decimal import Decimal, localcontext

import numpy as np
import pytest
from discretize import TensorMesh

from magnetic_regularization import MagneticRegularizer


def _regularizer():
    mesh = TensorMesh(
        [[1., 2., 3.], [1.5, 2.5], [2., 3.]], origin=[-4., 8., -20.]
    )
    active = np.ones(mesh.nC, dtype=np.bool_)
    active[[2, 8]] = False
    reference = np.linspace(.1, .8, int(active.sum()), dtype=np.float64)
    lengths = np.array([4., 9., 16.], dtype=np.float64)
    return MagneticRegularizer(mesh, active, reference, lengths), active


def test_simpeg_regularizer_matches_independent_nonuniform_active_face_quadratic():
    regularizer, _ = _regularizer()
    q = np.array([.1, .24, .19, .55, .37, .41, .8, .22, .47, .9], dtype=np.float64)
    result = regularizer.evaluate(q)
    np.testing.assert_allclose(result["phi"], result["independent_phi"], rtol=2e-13, atol=2e-14)
    np.testing.assert_allclose(result["gradient_q"], result["independent_gradient_q"], rtol=3e-13, atol=2e-14)
    np.testing.assert_allclose(result["hessian_action"](np.ones_like(q)),
                               result["independent_hessian"] @ np.ones_like(q),
                               rtol=3e-13, atol=2e-14)
    assert result["active_face_count_by_axis"] == (6, 4, 5)
    assert result["unit"] == "dimensionless"
    assert np.linalg.eigvalsh(result["independent_hessian"])[0] > 0.


def test_inactive_cells_and_exterior_faces_are_not_regularized_across():
    regularizer, active = _regularizer()
    expected_counts = [0, 0, 0]
    shape = regularizer.mesh.shape_cells
    strides = (1, shape[0], shape[0] * shape[1])
    for axis, stride in enumerate(strides):
        for left in range(regularizer.mesh.nC):
            coords = np.unravel_index(left, shape, order="F")
            if coords[axis] + 1 < shape[axis] and active[left] and active[left + stride]:
                expected_counts[axis] += 1
    assert regularizer.evaluate(np.full(regularizer.parameter_count, .4, dtype=np.float64))["active_face_count_by_axis"] == tuple(expected_counts)


def test_metadata_limits_precede_numeric_finite_scans(monkeypatch):
    regularizer, _ = _regularizer()
    oversized_reference = np.zeros(regularizer.parameter_count + 1, dtype=np.float64)
    original_isfinite = np.isfinite

    def guarded_isfinite(value, *args, **kwargs):
        if value is oversized_reference:
            raise AssertionError("shape failure scanned reference before metadata admission")
        return original_isfinite(value, *args, **kwargs)

    monkeypatch.setattr(np, "isfinite", guarded_isfinite)
    with pytest.raises(TypeError, match="reference_q"):
        MagneticRegularizer(regularizer.mesh, regularizer.active_cells,
                            oversized_reference, regularizer.lengths_m)


@pytest.mark.parametrize("epsilon", [.1, .05, .025, .0125, .00625, .003125, .0015625, .001])
def test_sparse_refresh_uses_actual_simpeg_weights_and_true_fixed_epsilon_gradient(epsilon):
    regularizer, _ = _regularizer()
    q = np.array([.3, .24, .19, .55, .37, .41, .8, .22, .47, .9], dtype=np.float64)
    result = regularizer.evaluate_sparse(q, epsilon)
    delta = q - regularizer.reference_q
    root = np.hypot(delta, epsilon)
    expected_smallness = float(2. * np.dot(
        regularizer.volumes / regularizer.total_volume,
        delta**2 / (root + epsilon),
    ))
    expected_gradient = (
        2. * (regularizer.volumes / regularizer.total_volume) * delta / root
        + 2. * regularizer._smooth_quadratic @ delta
    )
    np.testing.assert_allclose(result["true_smallness"], expected_smallness, rtol=2e-15, atol=0.)
    np.testing.assert_allclose(result["true_gradient_q"], expected_gradient, rtol=2e-14, atol=2e-15)
    np.testing.assert_allclose(result["simpeg_surrogate_gradient_q"], expected_gradient,
                               rtol=3e-13, atol=2e-14)
    np.testing.assert_allclose(result["smallness_irls_weights"], 1. / root, rtol=3e-16, atol=0.)
    direction = np.linspace(-.4, .5, len(q), dtype=np.float64)
    step = 1e-6
    plus = regularizer.evaluate_sparse(q + step * direction, epsilon)["true_fixed_epsilon_psi"]
    minus = regularizer.evaluate_sparse(q - step * direction, epsilon)["true_fixed_epsilon_psi"]
    finite_difference = (plus - minus) / (2. * step)
    np.testing.assert_allclose(finite_difference, expected_gradient @ direction,
                               rtol=2e-7, atol=2e-9)
    assert result["norms"] == (1., 2., 2., 2.)
    assert result["gradient_type"] == "components"
    assert result["irls_scaled"] is False
    assert result["smoothness_epsilon_per_m"] == tuple(epsilon / ell for ell in (4., 9., 16.))


@pytest.mark.parametrize("change", [1e-10, -1e-10, 0.])
def test_sparse_smallness_preserves_tiny_positive_values_against_decimal80(change):
    regularizer, _ = _regularizer()
    q = regularizer.reference_q.copy()
    q[0] += change
    epsilon = .1
    result = regularizer.evaluate_sparse(q, epsilon)
    delta = float(q[0] - regularizer.reference_q[0])
    with localcontext() as context:
        context.prec = 80
        exact_delta = Decimal.from_float(delta)
        exact_epsilon = Decimal.from_float(epsilon)
        expected = (Decimal(2) * Decimal.from_float(
            float(regularizer.volumes[0] / regularizer.total_volume)
        ) * exact_delta**2 / ((exact_delta**2 + exact_epsilon**2).sqrt() + exact_epsilon))
        observed = Decimal.from_float(float(result["true_smallness"]))
        if delta == 0.:
            assert observed == 0 and expected == 0
        else:
            assert observed > 0 and expected > 0
            assert abs(observed - expected) <= Decimal("2e-8") * abs(expected)


def test_sparse_calls_simpeg_update_weights_at_each_recorded_model(monkeypatch):
    regularizer, _ = _regularizer()
    calls = []
    original = regularizer.sparse.update_weights

    def recording(model):
        calls.append(model.copy())
        return original(model)

    monkeypatch.setattr(regularizer.sparse, "update_weights", recording)
    q = regularizer.reference_q.copy()
    regularizer.evaluate_sparse(q, .05)
    assert len(calls) == 1
    np.testing.assert_array_equal(calls[0], q)
