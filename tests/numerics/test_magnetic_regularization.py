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
