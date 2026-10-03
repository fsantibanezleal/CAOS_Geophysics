"""Source-pinned ordinary weighted L2 primitives; no public API/field claim.

The private problem constructor is for admitted native requests and independent
small mathematical controls. No user-prepared engine/kernel objects are accepted.
"""

from time import monotonic

import numpy as np
import scipy.linalg as la
import scipy.sparse as sp
from simpeg import data, data_misfit, inverse_problem, inversion, maps, optimization, regularization

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
    if np.any(indices < 0) or np.any(indices >= n) or np.any(indices[1:] <= indices[:-1]):
        raise ValueError('noise.rows: unique strictly ascending aligned rows required')
    if not np.isfinite(values).all():
        raise ValueError('noise: nonfinite values')
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
            'observations': survey._readonly(observations[rows]),
            'reference_q': survey._readonly(reference),
            'alpha': (normalizer, float(alphas[0]), float(alphas[1]), float(alphas[2]))}


class _SolveFailure(RuntimeError):
    """Private deterministic observer failure, not an alternative solver."""


def _kkt_gradient(q, gradient, lower, upper):
    tolerance = 32*np.finfo(np.float64).eps*np.maximum.reduce(
        [np.ones_like(q), np.abs(q), np.abs(lower), np.abs(upper)])
    projected = gradient.copy()
    projected[(q <= lower+tolerance) & (gradient > 0)] = 0.
    projected[(q >= upper-tolerance) & (gradient < 0)] = 0.
    return projected


class _RecordedProjectedGNCG(optimization.ProjectedGNCG):
    """Observe official directions/LS and replace ONLY ordinary stop semantics.

    No public hook, changed search/projection or native-source monkeypatch.
    Line-search wrapper delegates unchanged; only failed diagnostics abort.
    """

    def __init__(self, problem, prior, deadline):
        super().__init__(lower=prior['lower_kg_m3']/1000., upper=prior['upper_kg_m3']/1000.,
                         maxIter=200, maxIterLS=20, cg_maxiter=200, cg_rtol=1e-6, cg_atol=0.,
                         step_active_set=True, active_set_grad_scale=.01, LSreduction=1e-4,
                         LSshorten=.5, use_WolfeCurvature=False, require_decrease=True, maxStep=np.inf)
        self._problem, self._deadline = problem, deadline
        self._states, self._cg_counts, self._ls_counts = [], [], []
        self._reason, self._initial_norm = None, None
        self._trials = []

    def _fail(self, reason):
        self._reason = reason
        raise _SolveFailure(reason)

    def _record(self):
        # The parent is the genuine BaseInvProblem, not a substituted objective.
        phi, gradient = self.parent.evalFunction(self.xc, return_g=True, return_H=False)
        pd, pm = float(self.parent.phi_d), float(self.parent.phi_m)
        if (not np.isfinite(phi) or not np.isfinite(pd) or not np.isfinite(pm)
                or not np.isfinite(gradient).all() or not np.isfinite(self.xc).all()):
            self._fail('nonfinite')
        if np.any(self.xc < self.lower) or np.any(self.xc > self.upper): self._fail('state_mismatch')
        if self._initial_norm is None:
            self._initial_norm = max(1., float(np.linalg.norm(gradient, ord=np.inf)))
        projected = _kkt_gradient(self.xc, gradient, self.lower, self.upper)
        absolute = float(np.linalg.norm(projected, ord=np.inf))
        kkt = absolute/self._initial_norm
        if len(self._states) != self.iter:
            self._fail('state_mismatch')
        self._states.append((self.xc.copy(), pd, pm, float(phi), kkt))
        if len(self._states) > 201: self._fail('state_mismatch')
        self.f, self.g = phi, gradient
        return absolute, kkt

    def stoppingCriteria(self, inLS=False):
        if inLS:
            if not np.isfinite(self._LS_ft) or not np.isfinite(self._LS_xt).all(): self._fail('nonfinite')
            self._trials.append((self.iter, self.iterLS, float(self._LS_ft)))
            if monotonic() > self._deadline: self._fail('wall_cap')
            return super().stoppingCriteria(inLS=True)
        absolute, kkt = self._record()
        if monotonic() > self._deadline:
            self._reason = 'wall_cap'
            return True
        if absolute <= 1e-12:
            self._reason = 'absolute_stationary'
            return True
        if len(self._states) >= 4:
            phi = np.array([state[3] for state in self._states[-4:]])
            changes = np.abs(np.diff(phi))/np.maximum(1., np.abs(phi[:-1]))
            if kkt <= 1e-5 and np.all(changes <= 1e-6):
                self._reason = 'kkt_stable'
                return True
        if self.iter >= 200:
            self._reason = 'iteration_cap'
            return True
        free = ~self.activeSet(self.xc)
        self._initial_free_residual = float(np.linalg.norm(free*self.g))
        if self._initial_free_residual == 0.:
            self._reason = 'zero_free_direction'
            return True
        return False

    def modifySearchDirection(self, p):
        # Official findSearchDirection already ran. Do not replace its step.
        if (not np.isfinite(p).all() or not np.isfinite(self.cg_abs_resid)
                or not np.isfinite(self.cg_rel_resid)):
            self._fail('nonfinite')
        if self.cg_count > 200 or self.cg_abs_resid > max(self.cg_rtol*self._initial_free_residual, self.cg_atol):
            self._fail('cg_cap')
        if not np.any(p): self._fail('zero_free_direction')
        trial, accepted = super().modifySearchDirection(p)
        if not accepted: self._reason = 'line_search_failed'
        return trial, accepted

    def doEndIteration(self, xt):
        previous = float(self.f)
        if self._LS_ft - previous > 1e-12*max(1., abs(previous)): self._fail('state_mismatch')
        self._cg_counts.append(int(self.cg_count))
        self._ls_counts.append(int(self.iterLS)+1)
        super().doEndIteration(xt)


def _solve_partition(problem, prior, deadline=None):
    """Return truthful official bounded solve/accepted trace under frozen stops."""
    started = monotonic()
    stop_time = min(started+120., deadline) if deadline is not None else started+120.
    opt = _RecordedProjectedGNCG(problem, prior, stop_time)
    misfit, reg, beta = problem['misfit'], problem['regularization'], problem['beta_engine']
    # Positive diagonal of the genuine, fixed Hessian; no floor or dense solve.
    weighted = misfit.W @ problem['simulation'].G
    diagonal = 2*np.sum(weighted*weighted, axis=0) + beta*reg.deriv2(prior['start_kg_m3']/1000.).diagonal()
    if not np.isfinite(diagonal).all() or np.any(diagonal <= 0):
        raise ValueError('optimizer: finite positive actual Hessian diagonal required')
    try:
        with np.errstate(over='raise', divide='raise', invalid='raise'):
            inverse_diagonal = 1./diagonal
    except ArithmeticError as exc:
        raise ValueError('optimizer: finite positive preconditioner required, no floor') from exc
    if not np.isfinite(inverse_diagonal).all() or np.any(inverse_diagonal <= 0):
        raise ValueError('optimizer: finite positive preconditioner required, no floor')
    opt.bfgsH0 = sp.diags(inverse_diagonal, format='csr')
    # The documented public preconditioner setter fixes the diagonal action;
    # no BFGS low-rank updates are silently substituted for the declared action.
    opt.approxHinv = opt.bfgsH0
    inv = inverse_problem.BaseInvProblem(misfit, reg, opt, beta=beta, init_bfgs=False, print_version=False)
    runner = inversion.BaseInversion(inv, directiveList=[])
    terminal = None
    try:
        terminal = runner.run(prior['start_kg_m3']/1000.)
    except _SolveFailure:
        terminal = getattr(opt, 'xc', None)
    except (FloatingPointError, ArithmeticError):
        opt._reason = 'nonfinite'
    except (RuntimeError, ValueError):
        opt._reason = 'engine_error'
    states = opt._states
    reason = opt._reason or 'state_mismatch'
    if terminal is not None and states:
        if not np.array_equal(terminal, states[-1][0]): reason = 'state_mismatch'
        # Reset genuine parent state after the last trial and independently replay.
        try:
            replay_phi, replay_g = inv.evalFunction(states[-1][0], return_g=True, return_H=False)
            pd, pm = float(inv.phi_d), float(inv.phi_m)
            if not np.isfinite(replay_g).all() or not np.allclose(
                    [pd, pm, replay_phi], states[-1][1:4], rtol=1e-10, atol=1e-12):
                reason = 'state_mismatch'
        except ArithmeticError:
            if reason != 'state_mismatch': reason = 'nonfinite'
        except (RuntimeError, ValueError):
            if reason not in ('nonfinite', 'state_mismatch'): reason = 'engine_error'
    k = len(states)
    model = survey._readonly(states[-1][0]*1000.) if k else None
    pd, pm, phi, kkt = states[-1][1:] if k else (None, None, None, None)
    predicted = None
    if k:
        try:
            predicted = problem['simulation'].dpred(states[-1][0]) + problem['background']
        except ArithmeticError:
            reason = 'nonfinite'
        except (RuntimeError, ValueError):
            if reason not in ('nonfinite', 'state_mismatch'): reason = 'engine_error'
    # Never reconstruct original d by reversing the engine's d-b subtraction:
    # floating-point cancellation could change its serialized residual identity.
    observed = problem['observations']
    if predicted is not None and not np.isfinite(predicted).all():
        predicted, reason = None, 'nonfinite'
    phi_trace = np.array([s[3] for s in states])
    trace = {
        'models_kg_m3': survey._readonly(np.array([s[0]*1000. for s in states]).reshape(k, len(diagonal))),
        'phi_d': survey._readonly(np.array([s[1] for s in states])),
        'phi_m': survey._readonly(np.array([s[2] for s in states])), 'phi_engine': survey._readonly(phi_trace),
        'kkt_normalized': survey._readonly(np.array([s[4] for s in states])),
        'relative_changes': survey._readonly(np.abs(np.diff(phi_trace))/np.maximum(1., np.abs(phi_trace[:-1]))),
        'line_search_counts': survey._readonly(np.array(opt._ls_counts[:max(k-1, 0)], dtype=np.int64)),
        'cg_counts': survey._readonly(np.array(opt._cg_counts[:max(k-1, 0)], dtype=np.int64))}
    if monotonic() > stop_time and reason not in ('nonfinite', 'engine_error', 'state_mismatch', 'line_search_failed'):
        reason = 'wall_cap'
    # Private bounded evidence for external trusted controls, not extra public
    # solve-record keys or a caller-selectable hook/output destination.
    problem['optimizer_evidence'] = {
        'trial_objectives': survey._readonly(np.array(opt._trials, dtype=np.float64).reshape(-1, 3)),
        'last_cg_count': int(getattr(opt, 'cg_count', 0)),
        'last_cg_absolute_residual': float(opt.cg_abs_resid) if hasattr(opt, 'cg_abs_resid') else None,
        'last_cg_relative_residual': float(opt.cg_rel_resid) if hasattr(opt, 'cg_rel_resid') else None}
    converged = reason in ('kkt_stable', 'absolute_stationary')
    return {'status': 'converged' if converged else ('failed' if reason in ('engine_error', 'nonfinite', 'state_mismatch')
                                                  else 'nonconverged'),
            'reason': reason, 'model_kg_m3': model, 'beta_candidate': problem['beta_candidate'], 'beta_engine': beta,
            'fit_rows': problem['rows'], 'predicted_mgal': survey._readonly(predicted) if predicted is not None else None,
            'residual_observed_minus_predicted_mgal': survey._readonly(observed-predicted) if predicted is not None else None,
            'phi_d': pd, 'phi_m': pm, 'phi_engine': phi, 'wrms': float(np.sqrt(pd/len(observed))) if pd is not None else None,
            'kkt_normalized': kkt, 'trace': trace, 'iterations': max(0, k-1), 'wall_seconds': float(monotonic()-started),
            'failed_trial': None if converged else {'iteration': int(getattr(opt, 'iter', 0)), 'reason': reason}}
