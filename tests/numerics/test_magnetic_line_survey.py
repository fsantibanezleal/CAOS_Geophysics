"""Independent algebra controls, NOT a survey/field predictive acceptance."""
from importlib import import_module
from pathlib import Path
import sys

import numpy as np
import pytest
from scipy.linalg import lstsq

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "data-pipeline"))


def module():
    return import_module("magnetic_line_survey")


def immutable(value):
    value = np.asarray(value, dtype=np.float64)
    value.flags.writeable = False
    return value


def geometry(case=0):
    # Noncentral, unequal axes, tilted XY with genuinely varying upward.
    # Exact geometry is constructed before the algebraic RHS below.
    t = np.arange(24 + 4 * case, dtype=np.float64)
    xyz = immutable(np.column_stack((134 + 17 * t,
                    -713 + 9 * (t % 5) + .13 * t,
                    110 + 13 * np.sin(t * .3))))
    k = np.arange(4 + case, dtype=np.float64)
    sources = immutable(np.column_stack((201 + 77 * k,
                        -730 + 24 * k, np.full(len(k), -200 - 30 * case))))
    return xyz, sources


def independent_dense(xyz, sources):
    return 1 / np.sqrt(np.sum((xyz[:, None, :] - sources[None, :, :])**2, axis=2))


@pytest.mark.parametrize("case", range(6))
@pytest.mark.parametrize("weighted", [False, True])
def test_global_dense_augmented_oracle(case, weighted):
    p = module()
    xyz, sources = geometry(case)
    # An algebraic RHS with no geological or field-truth claim.
    y = immutable(7 * np.sin(np.arange(len(xyz)) * .7) - 2.3)
    sigma = immutable(1 + np.arange(len(y)) % 7) if weighted else None
    model = p.global_operator(xyz, sources, sigma_nT=sigma,
                              chunk_rows=7, chunk_sources=3)
    jac = independent_dense(xyz, sources)
    scales = jac.std(axis=0, ddof=0)
    np.testing.assert_allclose(model.scales, scales, rtol=1e-12, atol=0)
    root = np.ones(len(y)) if sigma is None else 1 / sigma
    a = root[:, None] * jac / scales
    damping = .01
    c = lstsq(np.vstack((a, np.sqrt(damping) * np.eye(len(sources)))),
              np.r_[root * y, np.zeros(len(sources))], lapack_driver="gelsd")[0]
    fitted = p.solve_global(model, y, damping)
    predicted = jac @ fitted["coefficients"]
    oracle = a @ c / root
    assert np.max(np.abs(predicted - oracle)) <= 1e-7 * max(1, np.sqrt(np.mean(oracle**2)))
    objective = np.sum((a @ c - root * y)**2) + damping * np.sum(c**2)
    assert abs(fitted["objective"] - objective) / objective <= 1e-8
    assert fitted["stationarity_relative"] <= 1e-9
    assert fitted["coefficient_error_bound_nT"] + 1e-9 >= np.linalg.norm(fitted["scaled_coefficients"] - c)


def test_adjoint_dot_oracle():
    p = module()
    xyz, sources = geometry(3)
    op = p.global_operator(xyz, sources, chunk_rows=5, chunk_sources=2)
    v = np.linspace(-2, 3, len(sources))
    u = np.cos(np.arange(len(xyz)))
    a = independent_dense(xyz, sources) / independent_dense(xyz, sources).std(axis=0)
    av, atu = op.operator.matvec(v), op.operator.rmatvec(u)
    np.testing.assert_allclose(av, a @ v, rtol=1e-11, atol=1e-11)
    np.testing.assert_allclose(atu, a.T @ u, rtol=1e-11, atol=1e-11)
    lhs, rhs = av @ u, v @ atu
    denominator = max(abs(lhs), abs(rhs), np.linalg.norm(av) * np.linalg.norm(u),
                      np.linalg.norm(v) * np.linalg.norm(atu))
    assert abs(lhs - rhs) / denominator <= 1e-12


def test_chunk_order_and_sizes():
    p = module()
    xyz, sources = geometry(5)
    v = np.linspace(-2, 3, len(sources))
    baseline = p.global_operator(xyz, sources)
    for r, c in [(1, 1), (7, 3), (13, 4)]:
        op = p.global_operator(xyz, sources, chunk_rows=r, chunk_sources=c)
        np.testing.assert_allclose(op.scales, baseline.scales, rtol=1e-12)
        np.testing.assert_allclose(op.operator @ v, baseline.operator @ v, rtol=1e-11, atol=1e-11)
    # Reorder BOTH geometry and RHS, then restore output order: no implicit
    # data-dependent rows or independently fitted tile is permitted.
    order = np.arange(len(xyz))[::-1]
    reordered = p.global_operator(immutable(xyz[order]), sources, chunk_rows=7, chunk_sources=3)
    np.testing.assert_allclose((reordered.operator @ v)[order], baseline.operator @ v,
                               rtol=1e-11, atol=1e-11)


def test_raw_weight_lambda_scaling():
    p = module()
    xyz, sources = geometry()
    y = immutable(np.sin(np.arange(len(xyz))))
    sigma = immutable(1 + np.arange(len(xyz)) % 3)
    one = p.solve_global(p.global_operator(xyz, sources, sigma_nT=sigma), y, .01)
    factor = 25.
    two = p.solve_global(p.global_operator(xyz, sources, sigma_nT=immutable(sigma / np.sqrt(factor))),
                         y, .01 * factor)
    np.testing.assert_allclose(one["coefficients"], two["coefficients"], rtol=1e-7, atol=1e-7)
    assert abs(two["objective"] / one["objective"] - factor) < 1e-7


def test_lsmr_stop_and_stationarity():
    p = module()
    xyz, sources = geometry()
    op = p.global_operator(xyz, sources)
    zero = p.solve_global(op, immutable(np.zeros(len(xyz))), .01)
    assert zero["istop"] == 0 and zero["stationarity_relative"] == 0
    assert np.all(zero["coefficients"] == 0)
    for stop in [3, 6, 7]:
        with pytest.raises(p.SurveyError, match="nonconverged"):
            p.check_stationarity(op, immutable(np.zeros(len(xyz))), .01,
                                 immutable(np.zeros(len(sources))), stop, 1.)


def test_corrupt_coefficient_and_wrong_damp_refused():
    p = module()
    xyz, sources = geometry()
    op = p.global_operator(xyz, sources)
    y = immutable(np.sin(np.arange(len(xyz))))
    with pytest.raises(p.SurveyError, match="nonconverged"):
        p.check_stationarity(op, y, .01, immutable(np.ones(len(sources))), 2, 1.)
    a = independent_dense(xyz, sources) / op.scales
    # Incorrect mapping damp=lambda solves a DIFFERENT regularizer.
    wrong = lstsq(np.vstack((a, .01 * np.eye(len(sources)))),
                  np.r_[y, np.zeros(len(sources))])[0]
    with pytest.raises(p.SurveyError, match="nonconverged"):
        p.check_stationarity(op, y, .01, immutable(wrong), 2, 1.)


def test_unknown_sigma_refused():
    p = module()
    xyz, sources = geometry()
    for sigma in [immutable(np.zeros(len(xyz))), immutable(np.full(len(xyz), np.nan)),
                  immutable(np.full(len(xyz), 1e-300)), np.ones(len(xyz), dtype=bool)]:
        with pytest.raises(p.SurveyError):
            p.global_operator(xyz, sources, sigma_nT=sigma)


def test_geometry_dtype_mutability_and_collision_refused():
    p = module()
    xyz, sources = geometry()
    for bad in [xyz.copy(), immutable(xyz[:, :2]), xyz.astype(np.float32),
                immutable(np.full(xyz.shape, np.inf)), immutable(np.full(xyz.shape, 1e200))]:
        with pytest.raises(p.SurveyError):
            p.global_operator(bad, sources)
    collided = sources.copy()
    collided[0] = xyz[0]
    with pytest.raises(p.SurveyError):
        p.global_operator(xyz, immutable(collided))
    for r, c in [(True, 2), (4097, 2), (4, 129), (0, 2)]:
        with pytest.raises(p.SurveyError):
            p.global_operator(xyz, sources, chunk_rows=r, chunk_sources=c)


def test_engine_preloaded_shadow_and_version_refused(monkeypatch):
    from types import SimpleNamespace
    p = module()
    xyz, sources = geometry()
    name = "scipy.sparse.linalg._isolve.lsmr"
    monkeypatch.setitem(sys.modules, name, SimpleNamespace(__file__=__file__))
    with pytest.raises(p.SurveyError, match="custody_mismatch"):
        p.global_operator(xyz, sources)
    monkeypatch.undo()
    monkeypatch.setattr(p, "version", lambda name: "wrong")
    with pytest.raises(p.SurveyError, match="custody_mismatch"):
        p.global_operator(xyz, sources)


def test_operator_refuses_array_hooks_and_large_uncontained_shape():
    p = module()
    xyz, sources = geometry()
    op = p.global_operator(xyz, sources)
    class Hook:
        def __array__(self, *args, **kwargs):
            pytest.fail("Caller array hook must not execute")
    with pytest.raises(p.SurveyError):
        op._forward(Hook())
    with pytest.raises(p.SurveyError):
        op._adjoint(Hook())
    with pytest.raises(p.SurveyError, match="resource_refused"):
        p.global_operator(immutable(np.tile(xyz, (10, 1))), sources)


def test_constant_columns_and_unrepresentable_weights_refuse():
    p = module()
    xyz, sources = geometry()
    with pytest.raises(p.SurveyError, match="metadata_ineligible"):
        p.global_operator(immutable(np.tile(xyz[0], (24, 1))), sources)
    with pytest.raises(p.SurveyError, match="metadata_ineligible"):
        p.global_operator(xyz, sources, sigma_nT=immutable(np.full(len(xyz), 1e300)))


def test_nonzero_orthogonal_zero_solution_is_algebra_not_prediction():
    p = module()
    xyz = immutable([[0., 0., 100.], [0., 0., 100.],
                     [200., 10., 103.], [200., 10., 103.]])
    sources = immutable([[400., -20., -200.]])
    y = immutable([1., -1., 2., -2.])
    model = p.global_operator(xyz, sources, chunk_rows=2, chunk_sources=1)
    result = p.solve_global(model, y, .01)
    assert result["istop"] == 0
    assert result["stationarity_relative"] == 0
    assert np.all(result["coefficients"] == 0)
    assert result["data_term"] == 10.


def test_unrepresentable_penalty_is_not_silently_zero():
    p = module()
    xyz, sources = geometry()
    op = p.global_operator(xyz, sources, sigma_nT=immutable(np.full(len(xyz), 1e150)))
    # Finite weights do not guarantee representable objective components.
    # c^2 underflows, even when data term remains finite and stationarity small.
    with pytest.raises(p.SurveyError, match="nonconverged"):
        p.solve_global(op, immutable(np.sin(np.arange(len(xyz)))), .01)
