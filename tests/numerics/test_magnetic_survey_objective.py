"""Tiny physical likelihood/regularizer oracles, not fitted-survey acceptance."""

import math
from decimal import Decimal, ROUND_HALF_EVEN, localcontext

import choclo
from choclo.constants import VACUUM_MAGNETIC_PERMEABILITY as MU0
from discretize import TensorMesh
import numpy as np
import pytest
from scipy.linalg import solve_triangular
from scipy.sparse.linalg import LinearOperator
from simpeg import data, data_misfit, maps, regularization
from simpeg.potential_fields import magnetics
from simpeg.simulation import LinearSimulation


WIDTHS = ([40., 70.], [30., 50., 90.], [60., 110.])
ORIGIN = [-140., -180., -260.]
ACTIVE = [0, 1, 2, 3, 6, 7, 11]
LENGTHS = [400., 1200., 600.]
QREF = np.array([.2, .4, .1, .7, .3, .6, .5])
Q = np.array([1.2, .8, 2.1, .9, 1.7, 2.4, 1.1])
V = np.array([.3, -.2, .5, -.4, .1, .7, -.6])
SUBSET = np.array([0, 2, 3, 5, 7, 9, 12, 14, 17, 21, 24, 29])


def cell_oracle():
    """Independent x-fast cell bounds/volumes and active interior topology."""
    edges = [o + np.r_[0., np.cumsum(h)] for o, h in zip(ORIGIN, WIDTHS)]
    cells = [(i, j, k) for k in range(2) for j in range(3) for i in range(2)]
    bounds, volumes = [], []
    for index in ACTIVE:
        ijk = cells[index]
        bounds.append([edge[coord+offset] for edge, coord in zip(edges, ijk) for offset in (0, 1)])
        volumes.append(math.prod(WIDTHS[axis][coord] for axis, coord in enumerate(ijk)))
    volumes = np.array(volumes)
    gradients, averages = [], []
    for axis in range(3):
        grad, avg = [], []
        # Sorting is not vendor face order; explicit row matching checks topology.
        for left, index in enumerate(ACTIVE):
            ijk = cells[index]
            nxt = tuple(coord+(j == axis) for j, coord in enumerate(ijk))
            if nxt not in cells or cells.index(nxt) not in ACTIVE:
                continue
            right = ACTIVE.index(cells.index(nxt))
            distance = .5*(WIDTHS[axis][ijk[axis]] + WIDTHS[axis][nxt[axis]])
            row = np.zeros(7)
            row[left], row[right] = -1./distance, 1./distance
            grad.append(row)
            row = np.zeros(7)
            row[[left, right]] = .5
            avg.append(row)
        gradients.append(np.array(grad))
        averages.append(np.array(avg))
    r = [np.diag(np.sqrt(volumes/volumes.sum()))]
    for ell, grad, avg in zip(LENGTHS, gradients, averages):
        r.append(ell*np.sqrt((avg @ volumes)/volumes.sum())[:, None]*grad)
    return np.array(bounds), volumes, gradients, averages, np.vstack(r)


@pytest.fixture(scope="module")
def physical():
    # No observations, noise or truth choose this literal geometry.
    mesh = TensorMesh(WIDTHS, x0=ORIGIN)
    mask = np.zeros(12, dtype=bool)
    mask[ACTIVE] = True
    xyz = np.array([[-260.+90*s, -350.+220*l, 100.+17*((l+s)%3)]
                    for l in range(3) for s in range(10)])
    i, d = math.radians(37.), math.radians(-73.)
    direction = np.array([math.cos(i)*math.sin(d), math.cos(i)*math.cos(d), -math.sin(i)])
    receivers = magnetics.receivers.Point(xyz, components=["bx", "by", "bz"])
    field = magnetics.sources.UniformBackgroundField(
        receiver_list=[receivers], amplitude=50000., inclination=37., declination=-73.)
    sim = magnetics.simulation.Simulation3DIntegral(
        mesh, survey=magnetics.survey.Survey(field), active_cells=mask,
        chiMap=maps.IdentityMap(nP=7), model_type="scalar", engine="geoana",
        store_sensitivities="ram", sensitivity_dtype=np.float64,
        n_processes=1, is_amplitude_data=False)
    g = sim.G
    bounds, volumes, grad, avg, r = cell_oracle()
    # chi=1 defines physical derivative nT/SI; it is NOT a production input.
    m_unit = 50000.*direction*1e-9/MU0
    independent = np.array([
        [[fun(*receiver, *prism, *m_unit) * 1e9
          for prism in bounds]
         for fun in (choclo.prism.magnetic_e, choclo.prism.magnetic_n, choclo.prism.magnetic_u)]
        for receiver in xyz]).reshape(90, 7)
    reg = regularization.WeightedLeastSquares(
        mesh, active_cells=mask, mapping=maps.IdentityMap(nP=7),
        reference_model=QREF.copy(), reference_model_in_smooth=True,
        alpha_s=1., alpha_x=LENGTHS[0]**2, alpha_y=LENGTHS[1]**2,
        alpha_z=LENGTHS[2]**2, alpha_xx=0., alpha_yy=0., alpha_zz=0.,
        weights={"total_volume": np.full(7, 1./volumes.sum())})
    return sim, g, independent, direction, reg, grad, avg, r, volumes


def whitening(c):
    """Actual solve operator; never explicitly form C^-1 or L^-1."""
    lower = np.linalg.cholesky(c)
    def forward(value):
        return solve_triangular(lower, value, lower=True)
    def transpose(value):
        return solve_triangular(lower.T, value, lower=False)
    return LinearOperator(c.shape, matvec=forward, rmatvec=transpose,
                          matmat=forward, rmatmat=transpose, dtype=np.float64)


def test_physical_unit_si_and_q_ordering(physical):
    sim, g, independent, _, _, _, _, _, _ = physical
    assert g.shape == (90, 7) and g.dtype == np.float64
    np.testing.assert_allclose(g, independent, rtol=2e-8, atol=1e-7)
    np.testing.assert_array_equal(sim.getJ(.01*Q), g)
    np.testing.assert_allclose(sim.dpred(.01*Q), (.01*g) @ Q, rtol=1e-12, atol=1e-10)
    np.testing.assert_allclose(sim.dpred(.01*Q), independent @ (.01*Q), rtol=2e-8, atol=1e-7)
    # Explicit negative: treating q as physical chi changes the model 100-fold.
    assert np.linalg.norm(g @ Q - sim.dpred(.01*Q)) > 100.


@pytest.mark.parametrize("axis", range(3))
def test_actual_active_face_gradients_and_averages(physical, axis):
    _, _, _, _, reg, gradients, averages, _, _ = physical
    rm = reg.regularization_mesh
    name = "xyz"[axis]
    actual = getattr(rm, "cell_gradient_"+name).toarray()
    avg = getattr(rm, "aveCC2F"+name).toarray()
    oracle = gradients[axis]
    assert actual.shape == oracle.shape
    assert len(oracle) > 0
    matched = []
    for row, mean in zip(actual, avg):
        candidates = [k for k, expected in enumerate(oracle)
                      if np.allclose(row, expected, rtol=1e-12, atol=1e-14)]
        assert len(candidates) == 1
        matched.append(candidates[0])
        np.testing.assert_array_equal(mean, averages[axis][candidates[0]])
    assert sorted(matched) == list(range(len(oracle)))


@pytest.mark.parametrize("model", [Q, QREF, np.zeros(7)])
def test_nonuniform_regularizer_value_gradient_hessian(physical, model):
    _, _, _, _, reg, _, _, r, _ = physical
    delta = model-QREF
    np.testing.assert_allclose(reg(model), np.linalg.norm(r @ delta)**2, rtol=1e-10, atol=1e-10)
    np.testing.assert_allclose(reg.deriv(model), 2*r.T @ (r @ delta), rtol=1e-10, atol=1e-8)
    np.testing.assert_allclose(reg.deriv2(model, V), 2*r.T @ (r @ V), rtol=1e-10, atol=1e-8)
    assert reg.reference_model_in_smooth


@pytest.mark.parametrize("quantity", ["secondary_enu_nT", "linear_tmi_nT"])
@pytest.mark.parametrize("noise", ["sd", "covariance"])
@pytest.mark.parametrize("subset", [False, True])
@pytest.mark.parametrize("beta", [.3, 3.])
def test_vendor_objective_against_independent_physical_covariance_stencil(physical, quantity, noise, subset, beta):
    _, g, independent, direction, reg, _, _, r, _ = physical
    components = 3 if quantity == "secondary_enu_nT" else 1
    if components == 1:
        g = np.einsum("c,nca->na", direction, g.reshape(30, 3, 7))
        independent = np.einsum("c,nca->na", direction, independent.reshape(30, 3, 7))
    j, j_oracle = .01*g, .01*independent
    d_full = j_oracle @ np.array([1., .4, 2., 1.5, .8, 2.2, 1.3]) + .07*np.sin(np.arange(30*components))
    indices = np.arange(30*components)
    if subset:
        indices = (SUBSET[:, None]*components + np.arange(components)).ravel()
    size = 30*components
    sigma = .5 + .002*np.arange(size)
    c_full = (.22**np.abs(np.arange(size)[:, None]-np.arange(size))) * sigma[:, None]*sigma[None, :]
    if noise == "sd":
        c_full = np.eye(size)*.5**2
    c = c_full[np.ix_(indices, indices)]
    j, j_oracle, d = j[indices], j_oracle[indices], d_full[indices]
    w = whitening(c)
    linear = LinearSimulation(G=j, model_map=maps.IdentityMap(nP=7))
    misfit = data_misfit.L2DataMisfit(simulation=linear, data=data.Data(linear.survey, dobs=d))
    misfit.W = w
    residual = j_oracle @ Q-d
    solved = np.linalg.solve(c, residual)
    phi_d = residual @ solved
    phi_m = np.linalg.norm(r @ (Q-QREF))**2
    gradient = 2*j_oracle.T @ solved + 2*beta*r.T @ (r @ (Q-QREF))
    hv = 2*j_oracle.T @ np.linalg.solve(c, j_oracle @ V) + 2*beta*r.T @ (r @ V)
    np.testing.assert_allclose(misfit(Q)+beta*reg(Q), phi_d+beta*phi_m, rtol=1e-10, atol=1e-10)
    np.testing.assert_allclose(misfit.deriv(Q)+beta*reg.deriv(Q), gradient, rtol=1e-10, atol=1e-8)
    # Pinned vendor deriv2 uses W*W, valid for diagonal SD but not triangular W.
    # Compose public physical J actions and the actual transpose; no vendor patch.
    action = 2*linear.Jtvec(Q, w.T @ (w @ linear.Jvec(Q, V))) + beta*reg.deriv2(Q, V)
    np.testing.assert_allclose(action, hv, rtol=1e-10, atol=1e-8)
    vendor_action = misfit.deriv2(Q, V)+beta*reg.deriv2(Q, V)
    if noise == "sd":
        np.testing.assert_allclose(vendor_action, hv, rtol=1e-10, atol=1e-8)
    else:
        assert not np.allclose(vendor_action, hv, rtol=1e-5, atol=1e-8)
    weighted = w @ j
    exact_diag = np.diag(j.T @ np.linalg.solve(c, j))
    np.testing.assert_allclose(np.sum(weighted**2, axis=0), exact_diag, rtol=1e-12, atol=1e-10)
    native_residual = j @ Q-d
    np.testing.assert_allclose(np.linalg.norm(w @ native_residual)**2,
                               native_residual @ np.linalg.solve(c, native_residual), rtol=1e-12, atol=1e-10)
    if noise == "covariance":
        diagonal_shortcut = np.sum((j/np.sqrt(np.diag(c))[:, None])**2, axis=0)
        assert not np.allclose(diagonal_shortcut, exact_diag, rtol=1e-3, atol=1e-10)
        if subset:
            wrong = solve_triangular(np.linalg.cholesky(c_full), np.eye(size), lower=True)[np.ix_(indices, indices)]
            assert not np.allclose(w @ native_residual, wrong @ native_residual, rtol=1e-5, atol=1e-10)


def test_oracles_detect_wrong_reference_length_and_volume(physical):
    _, _, _, _, reg, _, _, r, volumes = physical
    delta = Q-QREF
    correct = reg(Q)
    assert not np.isclose(correct, np.linalg.norm(r @ Q)**2, rtol=1e-5)
    assert not np.isclose(correct, np.linalg.norm(r @ delta)**2*volumes.sum(), rtol=1e-5)
    assert not np.isclose(correct, np.dot(delta, delta), rtol=1e-5)


@pytest.mark.parametrize("epsilon", [.1, .05, .025, .0125, .00625, .003125, .0015625, .001])
@pytest.mark.parametrize("model", [Q, QREF, np.zeros(7)])
def test_actual_sparse_weights_true_gradient_and_surrogate_distinction(physical, epsilon, model):
    sim, _, _, _, _, _, _, r, volumes = physical
    sparse = regularization.Sparse(
        sim.mesh, active_cells=sim.active_cells, mapping=maps.IdentityMap(nP=7),
        reference_model=QREF.copy(), reference_model_in_smooth=True,
        alpha_s=1., alpha_x=LENGTHS[0]**2, alpha_y=LENGTHS[1]**2,
        alpha_z=LENGTHS[2]**2, alpha_xx=0., alpha_yy=0., alpha_zz=0.,
        weights={"total_volume": np.full(7, 1./volumes.sum())},
        norms=[1., 2., 2., 2.], gradient_type="components", irls_scaled=False,
        irls_threshold=epsilon)
    for child, ell in zip(sparse.objfcts[1:], LENGTHS):
        child.irls_threshold = epsilon/ell
    sparse.update_weights(model)
    delta = model-QREF
    fraction = volumes/volumes.sum()
    weights = 1./np.sqrt(delta**2+epsilon**2)
    np.testing.assert_allclose(sparse.objfcts[0].get_weights("irls"), weights, rtol=1e-12, atol=1e-10)
    for child, ell in zip(sparse.objfcts[1:], LENGTHS):
        assert child.irls_scaled is False and child.irls_threshold == epsilon/ell
        np.testing.assert_array_equal(child.get_weights("irls"), np.ones(child.f_m(model).shape))
    smooth = r[7:]
    true_smallness = 2*np.sum(fraction*delta**2/(np.sqrt(delta**2+epsilon**2)+epsilon))
    true_value = true_smallness + np.linalg.norm(smooth @ delta)**2
    true_gradient = 2*fraction*delta/np.sqrt(delta**2+epsilon**2)+2*smooth.T @ (smooth @ delta)
    surrogate = np.sum(fraction*weights*delta**2)+np.linalg.norm(smooth @ delta)**2
    surrogate_hv = 2*fraction*weights*V+2*smooth.T @ (smooth @ V)
    np.testing.assert_allclose(sparse(model), surrogate, rtol=1e-10, atol=1e-10)
    np.testing.assert_allclose(sparse.deriv(model), true_gradient, rtol=1e-10, atol=1e-8)
    np.testing.assert_allclose(sparse.deriv2(model, V), surrogate_hv, rtol=1e-10, atol=1e-8)
    if np.array_equal(model, QREF):
        assert true_value == surrogate == 0.
        np.testing.assert_array_equal(weights, np.full(7, 1./epsilon))
    else:
        assert true_value > surrogate > 0.
        # Equality of refreshed gradients does not make frozen-surrogate H the true H.
        true_hv = 2*fraction*epsilon**2*V/(delta**2+epsilon**2)**1.5 + 2*smooth.T @ (smooth @ V)
        assert not np.allclose(surrogate_hv, true_hv, rtol=1e-5, atol=1e-8)


@pytest.mark.parametrize("delta", [-1e-10, 0., 1e-10])
def test_tiny_true_sparse_smallness_has_no_absolute_floor(delta):
    epsilon = .1
    actual = 2*delta**2/(math.sqrt(delta**2+epsilon**2)+epsilon)
    with localcontext() as context:
        context.prec = 80
        context.rounding = ROUND_HALF_EVEN
        d, e = Decimal.from_float(delta), Decimal.from_float(epsilon)
        oracle = float(2*((d*d+e*e).sqrt()-e))
    if delta == 0.:
        assert actual == oracle == 0.
    else:
        assert actual > 0. and oracle > 0.
        assert abs(actual/oracle-1.) <= 2e-8
