"""Source-pinned ordinary weighted L2 primitives; no public API/field claim.

The private problem constructor is for admitted native requests and independent
small mathematical controls. No user-prepared engine/kernel objects are accepted.
"""

from time import monotonic
import json

import numpy as np
import scipy.linalg as la
import scipy.sparse as sp
from simpeg import data, data_misfit, inverse_problem, inversion, maps, optimization, regularization

import gravity_forward as forward
import gravity_survey_l2 as survey
import gravity_l2_precision as precision


RUNTIME_EPOCH = 'm02-survey-l2-cpu-4'
OPTIMIZER_POLICY = 'projected-gncg-binding-release-certified-delta-1'
FORWARD_SOURCE = '46d205a453147cc18697464e4a6deda2920d0d88307e366b6fd336d9a1ac07d5'
BETA_CANDIDATES = (.0001, .001, .01, .1, 1., 10., 100., 1000.)


def _calibration_metadata(request):
    """All supplied shapes/types/counts before scans, hash, copy or engine.

    Private admission stage only; projected-resource and SPD/workflow gates
    remain required before this becomes the complete native calibration entry.
    """
    survey._native_metadata(request)
    survey._keys(request, ('schema', 'plan', 'observations', 'noise', 'prior', 'policy', 'runtime_epoch'), 'calibration')
    survey._enum(request['schema'], ('gravity-survey-l2-calibration-request-1',), 'schema')
    survey._enum(request['runtime_epoch'], (RUNTIME_EPOCH,), 'runtime_epoch')
    survey._plan_result_metadata(request['plan'])
    m = len(request['plan']['development_rows'])
    a = len(request['plan']['geometry']['active_cell_indices'])
    if not 1 <= m <= 2048: raise ValueError('observations: compact row count outside ordinary cap')
    observed = request['observations']
    survey._keys(observed, ('rows', 'gz_up_mgal', 'values_sha256', 'acceleration_unit', 'vertical_positive'),
                 'observations')
    survey._array(observed['rows'], (m,), 'observations.rows', np.int64)
    survey._array(observed['gz_up_mgal'], (m,), 'observations.gz_up_mgal')
    survey._enum(observed['acceleration_unit'], ('mGal',), 'observations.acceleration_unit')
    survey._enum(observed['vertical_positive'], ('up',), 'observations.vertical_positive')
    survey._sha(observed['values_sha256'], 'observations.values_sha256')
    noise = request['noise']
    survey._keys(noise, ('kind', 'values', 'unit', 'basis', 'citation', 'values_sha256',
                        'cross_partition_dependence'), 'noise')
    survey._enum(noise['kind'], ('diagonal_sd', 'full_covariance'), 'noise.kind')
    covariance = noise['kind'] == 'full_covariance'
    survey._array(noise['values'], (m, m) if covariance else (m,), 'noise.values')
    survey._enum(noise['unit'], ('mGal^2' if covariance else 'mGal',), 'noise.unit')
    survey._enum(noise['basis'], ('measured_gaussian', 'propagated_independent_gaussian',
                                'explicit_conditional_gaussian'), 'noise.basis')
    survey._enum(noise['cross_partition_dependence'], ('declared_absent', 'possible_not_removed'),
                 'noise.cross_partition_dependence')
    survey._text(noise['citation'], 'noise.citation')
    survey._sha(noise['values_sha256'], 'noise.values_sha256')
    prior = request['prior']
    survey._keys(prior, ('lower_kg_m3', 'upper_kg_m3', 'start_kg_m3', 'reference_kg_m3', 'density_scale_kg_m3',
                        'lengths_m', 'basis', 'reference_in_smooth', 'spatial_weights', 'geometry_sha256'), 'prior')
    for key in ('lower_kg_m3', 'upper_kg_m3', 'start_kg_m3', 'reference_kg_m3'):
        survey._array(prior[key], (a,), 'prior.'+key)
    survey._array(prior['lengths_m'], (3,), 'prior.lengths_m')
    survey._float(prior['density_scale_kg_m3'], 'prior.density_scale_kg_m3', positive=True)
    survey._text(prior['basis'], 'prior.basis')
    if type(prior['reference_in_smooth']) is not bool or prior['reference_in_smooth'] is not True:
        raise ValueError('prior.reference_in_smooth: exact True required')
    survey._enum(prior['spatial_weights'], ('none',), 'prior.spatial_weights')
    survey._sha(prior['geometry_sha256'], 'prior.geometry_sha256')
    policy = request['policy']
    survey._keys(policy, ('name', 'beta_candidates', 'optimizer', 'training'), 'policy')
    survey._enum(policy['name'], ('ordinary-l2-beta-grid-1',), 'policy.name')
    survey._enum(policy['optimizer'], (OPTIMIZER_POLICY,), 'policy.optimizer')
    survey._enum(policy['training'], ('not_applicable_classical',), 'policy.training')
    if (type(policy['beta_candidates']) is not tuple or len(policy['beta_candidates']) != 8
            or any(type(beta) is not float for beta in policy['beta_candidates'])
            or policy['beta_candidates'] != BETA_CANDIDATES):
        raise ValueError('policy.beta_candidates: exact eight frozen floats required')


def _admit_calibration(request):
    """Private compact identity/prior stage, NOT a complete inverse or SPD gate."""
    _calibration_metadata(request)
    survey._finite(request)
    observed, noise, prior, plan = (request[key] for key in ('observations', 'noise', 'prior', 'plan'))
    if not np.array_equal(observed['rows'], plan['development_rows']):
        raise ValueError('observations.rows: exact compact development identities required')
    body = {key: value for key, value in observed.items() if key != 'values_sha256'}
    if survey._digest(body) != observed['values_sha256']: raise ValueError('observations: content hash mismatch')
    body = {key: noise[key] for key in ('kind', 'unit', 'values')} | {'rows': observed['rows']}
    if survey._digest(body) != noise['values_sha256']: raise ValueError('noise: content hash mismatch')
    if survey._digest(plan['geometry']) != prior['geometry_sha256']: raise ValueError('prior: geometry hash mismatch')
    lower, upper = prior['lower_kg_m3'], prior['upper_kg_m3']
    if np.any(lower >= upper): raise ValueError('prior: strict lower<upper required')
    for key in ('start_kg_m3', 'reference_kg_m3'):
        if np.any(prior[key] < lower) or np.any(prior[key] > upper):
            raise ValueError('prior: start/reference outside supplied bounds, no clipping')
    if np.any(prior['lengths_m'] <= 0): raise ValueError('prior: positive physical lengths required')
    if noise['kind'] == 'diagonal_sd':
        if np.any(noise['values'] <= 0): raise ValueError('noise: positive SD required, no floor')
    elif not np.array_equal(noise['values'], noise['values'].T):
        raise ValueError('noise: exact declared covariance symmetry required')
    admitted = survey._snapshot(request)
    admitted['plan'] = survey._validate_plan(admitted['plan'])
    return admitted


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


def _build_problem(request, observations, noise, prior, rows, beta_candidate, observation_rows=None):
    """Real fitting simulation; compact declared rows never impute sealed values.

    Legacy private tiny controls omit observation_rows. Production calibration
    must supply its compact development identities, not a full-n data vector.
    """
    forward._runtime()
    survey._array(rows, (None,), 'fit_rows', np.int64)
    n = len(request['stations']['receivers_m'])
    survey._array(observations, (n,) if observation_rows is None else (None,), 'observations')
    if observation_rows is not None:
        survey._array(observation_rows, (len(observations),), 'observation_rows', np.int64)
    if not 1 <= len(observations) <= 2048 or not 1 <= len(rows) <= 2048:
        raise ValueError('fit: row count outside ordinary cap')
    if np.any(rows < 0) or np.any(rows >= n) or np.any(rows[1:] <= rows[:-1]):
        raise ValueError('fit: row count/identity invalid')
    selected = rows
    if observation_rows is not None:
        if (np.any(observation_rows < 0) or np.any(observation_rows >= n)
                or np.any(observation_rows[1:] <= observation_rows[:-1])):
            raise ValueError('fit: compact unique ascending observation identities required')
        selected = np.searchsorted(observation_rows, rows)
        if np.any(selected >= len(observation_rows)) or not np.array_equal(observation_rows[selected], rows):
            raise ValueError('fit: requested identity absent from compact observations')
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
    weights = _weights(noise, selected)
    fixed_background = request['background_mgal'][rows]
    # Official simulation predicts Gq. Move independently fixed b to the data;
    # its residual is still Gq+b-d. No intercept/background fit is introduced.
    engine_data = data.Data(fitting.survey, dobs=observations[selected] - fixed_background)
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
            'observations': survey._readonly(observations[selected]),
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
    """Reviewed binding-set hybrid with native reduced-face CG and Armijo.

    An exact active nonbinding coordinate selects the fixed-diagonal feasible
    chord BEFORE CG. Never a fallback after native CG/LS failure.
    No public hook, installed-source patch or claim of full GPCG convergence.
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
        self._release_next = False
        self._direction_kinds, self._last_direction_kind = [], 'not_run'
        self._direction_decisions, self._trial_checks = [], []
        self._last_trial_check = None
        self._precision, self._precision_trials = None, []
        self.cg_count, self.cg_abs_resid, self.cg_rel_resid = 0, None, None

    def _fail(self, reason):
        self._reason = reason
        raise _SolveFailure(reason)

    def _trial_fail(self, reason):
        self._last_trial_check['decision'] = 'failure'
        self._last_trial_check['cause'] = reason
        if self._precision_trials:
            r = self._precision_trials[-1]
            r.update(decision='not_run',cause='zero_displacement' if reason=='zero_free_direction' else
                     'wall_cap' if reason=='wall_cap' else 'native_failure',passes=0,precision_digits=None,
                     slope_interval=None,delta_interval=None,armijo_margin_interval=None)
        self._fail(reason)

    def _certify_trial(self):
        if self._precision is None:
            # Native SimPEG descriptors represent a one-cell bound as a scalar.
            # Broadcast that exact native value, without changing the box.
            lower = np.broadcast_to(np.asarray(self.lower,dtype=np.float64),self.xc.shape)
            upper = np.broadcast_to(np.asarray(self.upper,dtype=np.float64),self.xc.shape)
            self._precision = precision._CertifiedDelta(self._problem,lower,upper,self._deadline)
        self._precision.deadline = self._deadline
        return self._precision.evaluate(self.xc,self._LS_xt,self.g,int(self.iter),int(self.iterLS),float(self.f),float(self._LS_ft))

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
            # Native terminal diagnostic printers require this initial scalar.
            # Their tolF/tolX shortcuts are never called as our convergence rule.
            self.f0 = phi
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
            if len(self._precision_trials)>=4000: self._fail('state_mismatch')
            self._precision_trials.append(precision._record(int(self.iter),int(self.iterLS),self.f,self._LS_ft))
            self._last_trial_check = {
                'iteration': int(self.iter), 'trial': int(self.iterLS), 't': float(self._LS_t),
                'phi_trial': float(self._LS_ft) if np.isfinite(self._LS_ft) else None,
                'slope': None, 'decision': 'shorten', 'cause': None}
            if (not np.isfinite(self._LS_ft) or not np.isfinite(self._LS_xt).all()
                    or not np.isfinite(self._LS_t)):
                self._trial_fail('nonfinite')
            self._trials.append((self.iter, self.iterLS, float(self._LS_ft)))
            try:
                with np.errstate(over='raise', invalid='raise'):
                    displacement = self._LS_xt-self.xc
                    slope = float(np.inner(self.g, displacement))
            except ArithmeticError:
                self._trial_fail('nonfinite')
            if not np.isfinite(displacement).all() or not np.isfinite(slope):
                self._trial_fail('nonfinite')
            self._last_trial_check['slope'] = slope
            self._precision_trials[-1]['displacement_inf_q'] = float(np.max(np.abs(displacement)))
            if not np.any(displacement): self._trial_fail('zero_free_direction')
            if monotonic() > self._deadline: self._trial_fail('wall_cap')
            # Projection can turn a native descent direction into ascent.
            # Shorten that SAME direction; never rerun CG or use a fallback.
            if slope<0.:
                try:
                    certificate = self._certify_trial()
                except (ValueError,KeyError,TypeError):
                    certificate = self._precision_trials[-1]
                    certificate.update(cause='range_unsupported')
                self._precision_trials[-1] = precision._validate_record(certificate)
                if certificate['cause']=='wall_cap': self._trial_fail('wall_cap')
                accepted = certificate['decision']=='certified_accept'
            else:
                self._precision_trials[-1].update(cause='non_descent')
                accepted = False
            self._trial_checks.append((self.iter, self.iterLS, self._LS_t, slope, int(accepted)))
            if accepted: self._last_trial_check['decision'] = 'accepted'
            return accepted
        self._release_next = False
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
        active = self.activeSet(self.xc)
        residual = (~active)*(-self.g)
        self._initial_free_residual = float(np.linalg.norm(residual))
        # Exact official sets, NOT the diagnostic KKT bound tolerance or a
        # free-gradient magnitude heuristic. The free norm never selects PG.
        self._release_next = bool(np.any(active & ~self.bindingSet(self.xc)))
        if self._initial_free_residual == 0. and not self._release_next:
            self._reason = 'zero_free_direction'
            return True
        return False

    def findSearchDirection(self):
        self.cg_count, self.cg_abs_resid, self.cg_rel_resid = 0, None, None
        self._last_direction_kind = 'binding_release' if self._release_next else 'native_CG'
        active = self.activeSet(self.xc)
        inward = active & ~self.bindingSet(self.xc)
        decision = {'state_index': int(self.iter), 'kind': self._last_direction_kind,
                    'active_count': int(np.count_nonzero(active)),
                    'inward_active_count': int(np.count_nonzero(inward)),
                    'free_residual_inf': float(np.max(np.abs((~active)*self.g))),
                    'candidate_slope': None, 'pg_metric_norm_squared': None,
                    'cg_executed': not self._release_next}
        self._direction_decisions.append(decision)
        if not self._release_next:
            if not np.isfinite(self._initial_free_residual): self._fail('nonfinite')
            direction = super().findSearchDirection()
            try:
                with np.errstate(over='raise', invalid='raise'):
                    slope = float(np.inner(self.g, direction))
            except ArithmeticError:
                self._fail('nonfinite')
            if not np.isfinite(direction).all() or not np.isfinite(slope): self._fail('nonfinite')
            decision['candidate_slope'] = slope
            if not np.any(direction) or slope >= 0.: self._fail('zero_free_direction')
            return direction
        try:
            with np.errstate(over='raise', invalid='raise', divide='raise'):
                unprojected = self.xc-self.approxHinv*self.g
                if not np.isfinite(unprojected).all(): self._fail('nonfinite')
                direction = self.projection(unprojected)-self.xc
                slope = float(np.inner(self.g, direction))
                inverse_diagonal = self.approxHinv.diagonal()
                if not np.isfinite(inverse_diagonal).all() or np.any(inverse_diagonal <= 0.):
                    self._fail('nonfinite')
                metric = float(np.sum(direction**2/inverse_diagonal))
        except ArithmeticError:
            self._fail('nonfinite')
        if not np.isfinite(direction).all() or not np.isfinite(slope) or not np.isfinite(metric):
            self._fail('nonfinite')
        decision['candidate_slope'] = slope
        if not np.any(direction) or slope >= 0. or metric <= 0.: self._fail('zero_free_direction')
        decision['pg_metric_norm_squared'] = metric
        return direction

    def modifySearchDirection(self, p):
        if not np.isfinite(p).all(): self._fail('nonfinite')
        if self._last_direction_kind != 'binding_release':
            if not np.isfinite(self.cg_abs_resid) or not np.isfinite(self.cg_rel_resid): self._fail('nonfinite')
            if self.cg_count > 200 or self.cg_abs_resid > max(self.cg_rtol*self._initial_free_residual, self.cg_atol):
                self._fail('cg_cap')
        if not np.any(p): self._fail('zero_free_direction')
        trial, accepted = super().modifySearchDirection(p)
        if not accepted:
            self._reason = 'line_search_failed'
            if self._last_trial_check is not None:
                self._last_trial_check.update(decision='failure', cause='line_search_failed')
        return trial, accepted

    def doEndIteration(self, xt):
        previous = float(self.f)
        if self._LS_ft - previous > 1e-12*max(1., abs(previous)): self._fail('state_mismatch')
        self._cg_counts.append(int(self.cg_count))
        self._ls_counts.append(int(self.iterLS)+1)
        self._direction_kinds.append(1 if self._last_direction_kind == 'binding_release' else 0)
        super().doEndIteration(xt)


def _solve_partition(problem, prior, deadline=None):
    """Return reviewed local hybrid solve/accepted trace under frozen stops."""
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
    cg_absolute, cg_relative = opt.cg_abs_resid, opt.cg_rel_resid
    cg_status = ('not_run' if opt._last_direction_kind != 'native_CG' else
                 'unavailable' if cg_absolute is None or cg_relative is None else
                 'finite' if np.isfinite(cg_absolute) and np.isfinite(cg_relative) else 'nonfinite')
    problem['optimizer_evidence'] = {
        'trial_objectives': survey._readonly(np.array(opt._trials, dtype=np.float64).reshape(-1, 3)),
        'direction_kinds': survey._readonly(np.array(opt._direction_kinds[:max(k-1, 0)], dtype=np.int64)),
        'last_direction_kind': opt._last_direction_kind,
        'last_cg_count': int(getattr(opt, 'cg_count', 0)),
        'last_cg_absolute_residual': float(cg_absolute) if cg_absolute is not None and np.isfinite(cg_absolute) else None,
        'last_cg_relative_residual': float(cg_relative) if cg_relative is not None and np.isfinite(cg_relative) else None,
        'last_cg_residual_status': cg_status,
        'direction_decisions': tuple(dict(item) for item in opt._direction_decisions),
        'trial_checks': survey._readonly(np.array(opt._trial_checks, dtype=np.float64).reshape(-1, 5)),
        'last_trial_check': dict(opt._last_trial_check) if opt._last_trial_check is not None else None,
        'precision_trials': tuple(dict(precision._validate_record(item)) for item in opt._precision_trials)}
    converged = reason in ('kkt_stable', 'absolute_stationary')
    return {'status': 'converged' if converged else ('failed' if reason in ('engine_error', 'nonfinite', 'state_mismatch')
                                                  else 'nonconverged'),
            'reason': reason, 'model_kg_m3': model, 'beta_candidate': problem['beta_candidate'], 'beta_engine': beta,
            'fit_rows': problem['rows'], 'predicted_mgal': survey._readonly(predicted) if predicted is not None else None,
            'residual_observed_minus_predicted_mgal': survey._readonly(observed-predicted) if predicted is not None else None,
            'phi_d': pd, 'phi_m': pm, 'phi_engine': phi, 'wrms': float(np.sqrt(pd/len(observed))) if pd is not None else None,
            'kkt_normalized': kkt, 'trace': trace, 'iterations': max(0, k-1), 'wall_seconds': float(monotonic()-started),
            'failed_trial': None if converged else {'iteration': int(getattr(opt, 'iter', 0)), 'reason': reason}}


_WARNINGS = ('admitted_fixed_geometry','rank_deficient','zero_sensitivity_columns',
             'validation_outside_fit_hull','error_assumed_conditional',
             'geometry_uncertainty_not_propagated','cross_partition_dependence')
_REASONS = ('kkt_stable','absolute_stationary','iteration_cap','cg_cap','line_search_failed','wall_cap',
            'zero_free_direction','nonfinite','engine_error','state_mismatch')


def _preflight_calibration(request):
    """Conservative native + interval storage admission, not a measured RSS claim."""
    _calibration_metadata(request)
    plan = request['plan']
    n,m = len(plan['request']['stations']['receivers_m']),len(plan['development_rows'])
    # Charge actual submitted mask population, not a potentially inconsistent
    # redundant geometry record that has not yet been recomputed.
    a = int(np.count_nonzero(plan['request']['mesh']['active']))
    sensitivity = 8*n*a
    covariance = 8*m*m if request['noise']['kind']=='full_covariance' else 0
    # <=a smallness rows plus <=3a BOTH-active first-order face rows.
    intervals = 4096*(12*a+12*m+32*a)
    projected = 8*sensitivity+12*covariance+intervals+(256+256+64)*1024**2
    if sensitivity>64*1024**2 or covariance>32*1024**2 or projected>2*1024**3:
        raise ValueError('calibration: projected native/interval workspace exceeds existing budget')
    return projected


def _marginal_metrics(prediction, observed, noise, indices):
    weights = _weights(noise,indices)
    residual = observed-prediction
    with np.errstate(over='raise',invalid='raise'):
        whitened = weights@residual
        phi = float(whitened@whitened)
        wrms,rmse = float(np.sqrt(phi/len(indices))),float(np.sqrt(np.mean(residual**2)))
    if not np.isfinite([phi,wrms,rmse]).all() or not np.isfinite(whitened).all():
        raise ValueError('evaluation: nonfinite marginal metrics')
    return phi,wrms,rmse,residual,whitened


def _physical_prediction(request,model):
    return forward.forward_gravity({'schema':'gravity-prism-forward-request-1','frame':request['frame'],
        'mesh':request['mesh'],'receivers_m':request['stations']['receivers_m'],
        'density_kg_m3':model,'engine':request['engine']})['gz_up_mgal']+request['background_mgal']


def _bounded_prediction(request,model,deadline):
    if monotonic()>deadline: raise _SolveFailure('wall_cap')
    prediction=_physical_prediction(request,model)
    survey._array(prediction,request['background_mgal'].shape,'prediction')
    if not np.isfinite(prediction).all(): raise ArithmeticError('nonfinite prediction')
    if monotonic()>deadline: raise _SolveFailure('wall_cap')
    return prediction


def _selected_index(candidates):
    eligible = [c for c in candidates if c['eligible']]
    if len(eligible)<2: return None
    best = min(c['score_q'] for c in eligible)
    ties = [c for c in eligible if abs(c['score_q']-best)<=1e-12*max(1.,abs(best))]
    return min(ties,key=lambda c:(-c['beta_candidate'],c['index']))['index']


def _unstarted_solve(rows,prior,beta,reason):
    a = len(prior['start_kg_m3'])
    empty = {key:survey._readonly(np.empty(0,dtype=np.int64 if key in ('cg_counts','line_search_counts') else np.float64))
             for key in ('phi_d','phi_m','phi_engine','kkt_normalized','relative_changes','cg_counts','line_search_counts')}
    empty['models_kg_m3'] = survey._readonly(np.empty((0,a)))
    return {'status':'nonconverged' if reason=='wall_cap' else 'failed','reason':reason,'model_kg_m3':None,
        'beta_candidate':beta,'beta_engine':len(rows)*beta,'fit_rows':survey._readonly(rows),'predicted_mgal':None,
        'residual_observed_minus_predicted_mgal':None,'phi_d':None,'phi_m':None,'phi_engine':None,'wrms':None,
        'kkt_normalized':None,'trace':empty,'iterations':0,'wall_seconds':0.,'failed_trial':{'iteration':0,'reason':reason}}


def _run_fit(request,observed,noise,prior,rows,beta,observation_rows,deadline):
    if monotonic()>deadline: return _unstarted_solve(rows,prior,beta,'wall_cap')
    started = monotonic()
    try:
        problem = _build_problem(request,observed,noise,prior,rows,beta,observation_rows=observation_rows)
        return _solve_partition(problem,prior,deadline)
    except ArithmeticError:
        result = _unstarted_solve(rows,prior,beta,'nonfinite')
    except (ValueError,RuntimeError):
        result = _unstarted_solve(rows,prior,beta,'engine_error')
    result['wall_seconds'] = float(monotonic()-started)
    return result


def _fit_diagnostics(request,noise,observed,prior,plan):
    rows = plan['development_rows']
    problem = _build_problem(request,observed,noise,prior,rows,BETA_CANDIDATES[0],observation_rows=rows)
    weighted = problem['misfit'].W@problem['simulation'].G
    with np.errstate(over='raise',invalid='raise'):
        sensitivity = np.sum((weighted/1000.)**2,axis=0)
        singular = la.svdvals(weighted,check_finite=True)
        threshold = float(max(weighted.shape)*np.finfo(np.float64).eps*singular[0])
    rank = int(np.count_nonzero(singular>threshold))
    if rank==0 or not np.isfinite(sensitivity).all() or not np.isfinite(singular).all():
        raise ValueError('diagnostics: rank-zero/nonfinite data sensitivity')
    warnings = ['admitted_fixed_geometry']
    if rank<weighted.shape[1]: warnings.append('rank_deficient')
    if np.any(sensitivity==0.): warnings.append('zero_sensitivity_columns')
    from scipy.spatial import Delaunay
    points = request['stations']['receivers_m'][:,:2]
    if any(np.any(Delaunay(points[f['fit_rows']]).find_simplex(points[f['validation_rows']])<0) for f in plan['folds']):
        warnings.append('validation_outside_fit_hull')
    return {'fit_rows':survey._readonly(rows),'sensitivity_diagonal':survey._readonly(sensitivity),
        'sensitivity_unit':'(kg/m3)^-2','singular_values':survey._readonly(singular),
        'numeric_rank':rank,'numeric_nullity':weighted.shape[1]-rank,'rank_threshold':threshold,
        'warnings':tuple(warnings)}


def calibrate_gravity_l2(request):
    """Actual serial8x3 fits + one selected refit; compact development only.

    No I/O, user callback, warm start, failed-fold average or second selected
    candidate on refit failure. Source verification/sealing remain external.
    """
    started = monotonic()
    _preflight_calibration(request)
    admitted = _admit_calibration(request)
    plan,prior = admitted['plan'],admitted['prior']
    req,rows = plan['request'],plan['development_rows']
    observed = admitted['observations']['gz_up_mgal']
    noise = {k:admitted['noise'][k] for k in ('kind','values')}
    # Validate the complete declared covariance, not just selected subblocks.
    _weights(noise,np.arange(len(rows),dtype=np.int64))
    diagnostics = _fit_diagnostics(req,noise,observed,prior,plan)
    warnings = list(diagnostics['warnings'])
    if admitted['noise']['basis']=='explicit_conditional_gaussian': warnings.append('error_assumed_conditional')
    warnings.append('geometry_uncertainty_not_propagated')
    if admitted['noise']['cross_partition_dependence']=='possible_not_removed': warnings.append('cross_partition_dependence')
    diagnostics['warnings'] = tuple(warnings)
    deadline,candidates = started+1800.,[]
    for index,beta in enumerate(BETA_CANDIDATES):
        folds = []
        for fold in plan['folds']:
            solved = _run_fit(req,observed,noise,prior,fold['fit_rows'],beta,rows,deadline)
            pd,wrms,rmse = None,None,None
            if solved['status']=='converged' and monotonic()<=deadline:
                try:
                    prediction = _bounded_prediction(req,solved['model_kg_m3'],deadline)
                    positions = np.searchsorted(rows,fold['validation_rows'])
                    scored_values = _marginal_metrics(prediction[fold['validation_rows']],observed[positions],noise,positions)
                    if monotonic()<=deadline: pd,wrms,rmse = scored_values[:3]
                except (ArithmeticError,ValueError,RuntimeError):
                    pass  # Literal unavailable score, never average successful folds only.
            folds.append({'fold':fold['fold'],'solve':solved,'validation_rows':survey._readonly(fold['validation_rows']),
                          'validation_phi_d':pd,'validation_wrms':wrms,'validation_rmse_mgal':rmse})
        valid = all(f['solve']['status']=='converged' for f in folds)
        scored = valid and all(f['validation_phi_d'] is not None for f in folds)
        score = float(sum(f['validation_phi_d'] for f in folds)/sum(len(f['validation_rows']) for f in folds)) if scored else None
        if score is not None and not np.isfinite(score): scored,score = False,None
        candidates.append({'index':index,'beta_candidate':beta,'eligible':bool(scored),'folds':tuple(folds),
                           'score_q':score,'reason':'eligible' if scored else 'invalid_score' if valid else 'fold_failure'})
    selected = _selected_index(candidates)
    final,prediction,status = None,None,'insufficient_candidates'
    if selected is not None:
        final = _run_fit(req,observed,noise,prior,rows,BETA_CANDIDATES[selected],rows,deadline)
        status = 'selected' if final['status']=='converged' else 'final_nonconverged'
        if final['model_kg_m3'] is not None:
            prediction_reason=None
            try: prediction = _bounded_prediction(req,final['model_kg_m3'],deadline)
            except _SolveFailure: prediction_reason='wall_cap'
            except ArithmeticError: prediction_reason='nonfinite'
            except (ValueError,RuntimeError): prediction_reason='engine_error'
            if prediction_reason is not None and final['status']=='converged':
                final.update(status='nonconverged' if prediction_reason=='wall_cap' else 'failed',
                             reason=prediction_reason,
                             failed_trial={'iteration':final['iterations'],'reason':prediction_reason})
                status='final_nonconverged'
    result = {'schema':'gravity-survey-l2-calibration-result-1','plan':plan,
        'provenance':{'source':survey._snapshot(req['source']),'plan_sha256':plan['plan_sha256'],
            'normalized_values_sha256':admitted['observations']['values_sha256'],'noise_sha256':admitted['noise']['values_sha256'],
            'prior_sha256':survey._digest(prior),'policy_sha256':survey._digest(admitted['policy']),
            'forward_source_sha256':FORWARD_SOURCE,'runtime_epoch':RUNTIME_EPOCH,
            'runtime_versions':forward._runtime(),'source_verification':'external_required_not_performed_by_solver'},
        'candidates':tuple(candidates),'selected_index':selected,'selection_status':status,'final_solve':final,
        'predictions':{'rows':survey._readonly(np.arange(len(req['background_mgal']),dtype=np.int64)),
                       'gz_up_mgal':survey._readonly(prediction) if prediction is not None else None},
        'diagnostics':diagnostics,'scope':{'training':'not_applicable_classical','inverse':'weighted_bounded_l2',
            'field_eligible':False,'full_M02_accepted':False,'API_accepted':False,'GPU_accepted':False,
            'host_accepted':False,'geometry_error':'not_propagated'}}
    result['result_sha256'] = survey._digest(result)
    return result


def _result_native_metadata(value):
    """Result histories have the frozen256MiB allowance, not request96MiB.

    Never changes planner/request caps. Charge the complete evaluation wrapper,
    including repeated logical occurrences, before any numeric traversal/hash.
    """
    totals = [0,0,0]
    def charge(size):
        totals[1] += size
        if totals[0]>256*1024**2 or totals[1]>survey.MAX_METADATA_BYTES or totals[2]>survey.MAX_SCALARS:
            raise ValueError('result: complete native storage/metadata/scalar cap')
    def size(item):
        return len(json.dumps(item,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode('utf-8'))
    def visit(item,depth):
        if depth>8: raise ValueError('result: eight container levels')
        kind = type(item)
        if kind is np.ndarray:
            if item.dtype not in (np.dtype('float64'),np.dtype('int64'),np.dtype('bool')):
                raise TypeError('result: exact native arrays required')
            if item.ndim not in (1,2) or any(n>4096 for n in item.shape): raise ValueError('result: bounded dimensions')
            totals[0] += item.nbytes
            charge(size({'dtype':{'f':'<f8','i':'<i8','b':'|b1'}[item.dtype.kind],'shape':list(item.shape),'sha256':'0'*64}))
        elif kind is dict:
            if len(item)>survey.MAX_SCALARS: raise ValueError('result: dictionary count')
            charge(2+max(0,len(item)-1)+len(item))
            for key,child in item.items():
                if type(key) is not str: raise TypeError('result: exact string keys')
                visit(key,depth+1)
                visit(child,depth+1)
        elif kind is tuple:
            if len(item)>survey.MAX_SCALARS: raise ValueError('result: tuple count')
            charge(2+max(0,len(item)-1))
            for child in item: visit(child,depth+1)
        elif kind in (str,int,float,bool,type(None)):
            totals[2] += 1
            if kind is str and len(item)>1024: raise ValueError('result: text cap')
            if kind is int and item.bit_length()>64: raise ValueError('result: integer cap')
            charge(size(0. if kind is float and item==0 else item))
        else: raise TypeError('result: hooks/subclasses/foreign values forbidden')
    visit(value,0)


def _int(value,maximum,field):
    if type(value) is not int or not 0<=value<=maximum: raise ValueError(field+': exact bounded integer')


def _solve_metadata(value,a,rows,beta):
    survey._keys(value,('status','reason','model_kg_m3','beta_candidate','beta_engine','fit_rows','predicted_mgal',
        'residual_observed_minus_predicted_mgal','phi_d','phi_m','phi_engine','wrms','kkt_normalized','trace',
        'iterations','wall_seconds','failed_trial'),'solve')
    survey._enum(value['status'],('converged','nonconverged','failed'),'solve.status')
    survey._enum(value['reason'],_REASONS,'solve.reason')
    for key in ('beta_candidate','beta_engine','wall_seconds'): survey._float(value[key],key)
    if value['beta_candidate']!=beta or value['beta_engine']!=len(rows)*beta or value['wall_seconds']<0:
        raise ValueError('solve: fixed beta/timing identity')
    survey._array(value['fit_rows'],rows.shape,'solve.fit_rows',np.int64)
    for key in ('predicted_mgal','residual_observed_minus_predicted_mgal'):
        if value[key] is not None: survey._array(value[key],rows.shape,key)
    if value['model_kg_m3'] is not None: survey._array(value['model_kg_m3'],(a,),'model_kg_m3')
    for key in ('phi_d','phi_m','phi_engine','wrms','kkt_normalized'):
        if value[key] is not None:
            survey._float(value[key],key)
            if value[key]<0: raise ValueError('solve: nonnegative metric')
    _int(value['iterations'],200,'solve.iterations')
    trace = value['trace']
    survey._keys(trace,('models_kg_m3','phi_d','phi_m','phi_engine','kkt_normalized','relative_changes',
                       'line_search_counts','cg_counts'),'trace')
    survey._array(trace['models_kg_m3'],(None,a),'trace.models')
    k = len(trace['models_kg_m3'])
    if k>201: raise ValueError('trace:201states cap')
    for key in ('phi_d','phi_m','phi_engine','kkt_normalized'): survey._array(trace[key],(k,),'trace.'+key)
    survey._array(trace['relative_changes'],(max(0,k-1),),'trace.relative_changes')
    for key in ('line_search_counts','cg_counts'): survey._array(trace[key],(max(0,k-1),),'trace.'+key,np.int64)
    failed = value['failed_trial']
    if failed is not None:
        survey._keys(failed,('iteration','reason'),'failed_trial')
        _int(failed['iteration'],200,'failed_trial.iteration')
        survey._enum(failed['reason'],_REASONS,'failed_trial.reason')


def _calibration_result_metadata(result):
    survey._keys(result,('schema','plan','provenance','candidates','selected_index','selection_status',
        'final_solve','predictions','diagnostics','scope','result_sha256'),'calibration_result')
    survey._enum(result['schema'],('gravity-survey-l2-calibration-result-1',),'schema')
    survey._sha(result['result_sha256'],'result_sha256')
    survey._plan_result_metadata(result['plan'])
    plan = result['plan']
    a,n,m = len(plan['geometry']['active_cell_indices']),len(plan['request']['background_mgal']),len(plan['development_rows'])
    provenance = result['provenance']
    survey._keys(provenance,('source','plan_sha256','normalized_values_sha256','noise_sha256','prior_sha256',
        'policy_sha256','forward_source_sha256','runtime_epoch','runtime_versions','source_verification'),'provenance')
    survey._keys(provenance['source'],survey.SOURCE_KEYS,'provenance.source')
    for key in ('plan_sha256','normalized_values_sha256','noise_sha256','prior_sha256','policy_sha256','forward_source_sha256'):
        survey._sha(provenance[key],key)
    survey._enum(provenance['forward_source_sha256'],(FORWARD_SOURCE,),'forward_source_sha256')
    survey._enum(provenance['runtime_epoch'],(RUNTIME_EPOCH,),'runtime_epoch')
    survey._enum(provenance['source_verification'],('external_required_not_performed_by_solver',),'source_verification')
    survey._keys(provenance['runtime_versions'],forward.VERSIONS,'runtime_versions')
    for key,version in forward.VERSIONS.items(): survey._enum(provenance['runtime_versions'][key],(version,),key)
    candidates = result['candidates']
    if type(candidates) is not tuple or len(candidates)!=8: raise ValueError('candidates: exact8')
    for index,candidate in enumerate(candidates):
        survey._keys(candidate,('index','beta_candidate','eligible','folds','score_q','reason'),'candidate')
        _int(candidate['index'],7,'candidate.index')
        survey._float(candidate['beta_candidate'],'candidate.beta')
        if candidate['index']!=index or candidate['beta_candidate']!=BETA_CANDIDATES[index]:
            raise ValueError('candidate: exact grid/order')
        if type(candidate['eligible']) is not bool: raise TypeError('candidate: exact eligibility bool')
        if candidate['score_q'] is not None: survey._float(candidate['score_q'],'candidate.score_q')
        survey._enum(candidate['reason'],('eligible','fold_failure','invalid_score'),'candidate.reason')
        if type(candidate['folds']) is not tuple or len(candidate['folds'])!=3: raise ValueError('candidate: exact3folds')
        for fold_index,fold in enumerate(candidate['folds']):
            survey._keys(fold,('fold','solve','validation_rows','validation_phi_d','validation_wrms','validation_rmse_mgal'),'fold')
            _int(fold['fold'],2,'fold.index')
            if fold['fold']!=fold_index: raise ValueError('fold: exact order')
            expected = plan['folds'][fold_index]
            survey._array(fold['validation_rows'],expected['validation_rows'].shape,'validation_rows',np.int64)
            for key in ('validation_phi_d','validation_wrms','validation_rmse_mgal'):
                if fold[key] is not None:
                    survey._float(fold[key],key)
                    if fold[key]<0: raise ValueError('validation: negative metric')
            _solve_metadata(fold['solve'],a,expected['fit_rows'],BETA_CANDIDATES[index])
    selected = result['selected_index']
    if selected is not None: _int(selected,7,'selected_index')
    survey._enum(result['selection_status'],('selected','insufficient_candidates','final_nonconverged'),'selection_status')
    if result['final_solve'] is not None:
        if selected is None: raise ValueError('final: absent selected identity')
        _solve_metadata(result['final_solve'],a,plan['development_rows'],BETA_CANDIDATES[selected])
    prediction = result['predictions']
    survey._keys(prediction,('rows','gz_up_mgal'),'predictions')
    survey._array(prediction['rows'],(n,),'predictions.rows',np.int64)
    if prediction['gz_up_mgal'] is not None: survey._array(prediction['gz_up_mgal'],(n,),'predictions.gz')
    diagnostics = result['diagnostics']
    survey._keys(diagnostics,('fit_rows','sensitivity_diagonal','sensitivity_unit','singular_values','numeric_rank',
        'numeric_nullity','rank_threshold','warnings'),'diagnostics')
    survey._array(diagnostics['fit_rows'],(m,),'diagnostics.fit_rows',np.int64)
    survey._enum(diagnostics['sensitivity_unit'],('(kg/m3)^-2',),'sensitivity_unit')
    for key,shape in [('sensitivity_diagonal',(a,)),('singular_values',(min(m,a),))]:
        if diagnostics[key] is not None: survey._array(diagnostics[key],shape,'diagnostics.'+key)
    for key,maximum in [('numeric_rank',min(m,a)),('numeric_nullity',a)]:
        if diagnostics[key] is not None: _int(diagnostics[key],maximum,'diagnostics.'+key)
    if diagnostics['rank_threshold'] is not None: survey._float(diagnostics['rank_threshold'],'rank_threshold')
    if type(diagnostics['warnings']) is not tuple or len(diagnostics['warnings'])>7: raise ValueError('diagnostics: bounded warnings tuple')
    for warning in diagnostics['warnings']: survey._enum(warning,_WARNINGS,'warning')
    scope = result['scope']
    survey._keys(scope,('training','inverse','field_eligible','full_M02_accepted','API_accepted','GPU_accepted',
                       'host_accepted','geometry_error'),'scope')
    for key,value in [('training','not_applicable_classical'),('inverse','weighted_bounded_l2'),('geometry_error','not_propagated')]:
        survey._enum(scope[key],(value,),key)
    for key in ('field_eligible','full_M02_accepted','API_accepted','GPU_accepted','host_accepted'):
        if type(scope[key]) is not bool or scope[key] is not False: raise ValueError('scope: exact False nonclaim')


def _validate_solve_state(solve,rows):
    if not np.array_equal(solve['fit_rows'],rows): raise ValueError('solve: row binding')
    trace,k = solve['trace'],len(solve['trace']['models_kg_m3'])
    if solve['iterations']!=max(0,k-1): raise ValueError('solve: accepted history count')
    if any(np.any(trace[key]<0) for key in ('phi_d','phi_m','phi_engine','kkt_normalized','relative_changes')):
        raise ValueError('trace: negative metrics')
    if np.any(trace['line_search_counts']<1) or np.any(trace['line_search_counts']>20) or np.any(trace['cg_counts']<0) or np.any(trace['cg_counts']>200):
        raise ValueError('trace: original trial/CG caps')
    if not np.array_equal(trace['relative_changes'],np.abs(np.diff(trace['phi_engine']))/np.maximum(1.,np.abs(trace['phi_engine'][:-1]))):
        raise ValueError('trace: native relative change binding')
    if not np.allclose(trace['phi_engine'],trace['phi_d']+solve['beta_engine']*trace['phi_m'],rtol=1e-10,atol=1e-12):
        raise ValueError('trace: fixed objective binding')
    if k:
        if solve['model_kg_m3'] is None or not np.array_equal(solve['model_kg_m3'],trace['models_kg_m3'][-1]):
            raise ValueError('solve: exact accepted terminal model')
        for key in ('phi_d','phi_m','phi_engine','kkt_normalized'):
            if solve[key]!=float(trace[key][-1]): raise ValueError('solve: terminal metric binding')
        if solve['wrms']!=float(np.sqrt(solve['phi_d']/len(rows))): raise ValueError('solve: WRMS binding')
    elif solve['model_kg_m3'] is not None or any(solve[key] is not None for key in ('phi_d','phi_m','phi_engine','wrms','kkt_normalized')):
        raise ValueError('solve: unavailable metrics must be None')
    success = solve['status']=='converged'
    if success!=(solve['reason'] in ('kkt_stable','absolute_stationary')): raise ValueError('solve: status/reason binding')
    if success and (not k or solve['failed_trial'] is not None or solve['predicted_mgal'] is None or solve['residual_observed_minus_predicted_mgal'] is None):
        raise ValueError('solve: incomplete success')
    if not success and (solve['failed_trial'] is None or solve['failed_trial']['reason']!=solve['reason']):
        raise ValueError('solve: retained failure identity')
    if solve['reason']=='kkt_stable' and (k<4 or solve['kkt_normalized']>1e-5 or np.any(trace['relative_changes'][-3:]>1e-6)):
        raise ValueError('solve: frozen three-change criterion')
    if solve['reason']=='absolute_stationary' and solve['kkt_normalized']>1e-12:
        raise ValueError('solve: necessary native normalized stationarity bound')


def _validate_frozen(result):
    if survey._digest({k:v for k,v in result.items() if k!='result_sha256'})!=result['result_sha256']:
        raise ValueError('frozen: content hash mismatch')
    plan,provenance = result['plan'],result['provenance']
    if provenance['plan_sha256']!=plan['plan_sha256'] or survey._digest(provenance['source'])!=survey._digest(plan['request']['source']):
        raise ValueError('frozen: source/plan binding')
    expected_policy = {'name':'ordinary-l2-beta-grid-1','beta_candidates':BETA_CANDIDATES,
                       'optimizer':OPTIMIZER_POLICY,'training':'not_applicable_classical'}
    if provenance['policy_sha256']!=survey._digest(expected_policy): raise ValueError('frozen: current exact policy binding')
    if result['selection_status']!='selected' or result['final_solve'] is None: raise ValueError('frozen: nonconverged/unselected result')
    for candidate in result['candidates']:
        for fold,expected in zip(candidate['folds'],plan['folds']):
            if not np.array_equal(fold['validation_rows'],expected['validation_rows']): raise ValueError('fold: row binding')
            _validate_solve_state(fold['solve'],expected['fit_rows'])
            if fold['validation_phi_d'] is not None and fold['validation_wrms']!=float(np.sqrt(fold['validation_phi_d']/len(fold['validation_rows']))):
                raise ValueError('fold: WRMS binding')
        eligible = all(f['solve']['status']=='converged' and all(f[k] is not None for k in ('validation_phi_d','validation_wrms','validation_rmse_mgal')) for f in candidate['folds'])
        if candidate['eligible']!=eligible: raise ValueError('candidate: no missing-fold eligibility')
        expected_score = float(sum(f['validation_phi_d'] for f in candidate['folds'])/sum(len(f['validation_rows']) for f in candidate['folds'])) if eligible else None
        if candidate['score_q']!=expected_score: raise ValueError('candidate: exact complete score')
    if result['selected_index']!=_selected_index(result['candidates']): raise ValueError('selection: fixed tie/eligibility binding')
    final = result['final_solve']
    _validate_solve_state(final,plan['development_rows'])
    if final['status']!='converged': raise ValueError('frozen: unsuccessful selected refit')
    if not np.array_equal(result['predictions']['rows'],np.arange(len(plan['request']['background_mgal']),dtype=np.int64)):
        raise ValueError('predictions: complete original row identity')
    if result['predictions']['gz_up_mgal'] is None: raise ValueError('frozen: unavailable predictions')
    # Recompute geometry/plan AFTER complete wrapper metadata/hash admission.
    survey._validate_plan(plan)
    prediction = _physical_prediction(plan['request'],final['model_kg_m3'])
    if not np.allclose(prediction,result['predictions']['gz_up_mgal'],rtol=1e-10,atol=1e-12):
        raise ValueError('frozen: independent physical prediction binding')
    if not np.allclose(prediction[final['fit_rows']],final['predicted_mgal'],rtol=1e-10,atol=1e-12):
        raise ValueError('frozen: fit prediction binding')


def evaluate_gravity_l2(request):
    """Separate sealed marginal score; NO optimization, correction or refit."""
    _result_native_metadata(request)
    survey._keys(request,('schema','frozen_calibration','observations','noise'),'evaluation')
    survey._enum(request['schema'],('gravity-survey-l2-evaluation-request-1',),'schema')
    frozen = request['frozen_calibration']
    _calibration_result_metadata(frozen)
    rows = frozen['plan']['outer_rows']
    observed,noise = request['observations'],request['noise']
    survey._keys(observed,('rows','gz_up_mgal','values_sha256','acceleration_unit','vertical_positive'),'observations')
    survey._array(observed['rows'],rows.shape,'observations.rows',np.int64)
    survey._array(observed['gz_up_mgal'],rows.shape,'observations.values')
    survey._sha(observed['values_sha256'],'values_sha256')
    survey._enum(observed['acceleration_unit'],('mGal',),'acceleration_unit')
    survey._enum(observed['vertical_positive'],('up',),'vertical_positive')
    survey._keys(noise,('kind','values','unit','basis','citation','values_sha256','cross_partition_dependence'),'noise')
    survey._enum(noise['kind'],('diagonal_sd','full_covariance'),'noise.kind')
    covariance = noise['kind']=='full_covariance'
    survey._array(noise['values'],(len(rows),len(rows)) if covariance else rows.shape,'noise.values')
    survey._enum(noise['unit'],('mGal^2' if covariance else 'mGal',),'noise.unit')
    survey._enum(noise['basis'],('measured_gaussian','propagated_independent_gaussian','explicit_conditional_gaussian'),'noise.basis')
    survey._enum(noise['cross_partition_dependence'],('declared_absent','possible_not_removed'),'dependence')
    survey._text(noise['citation'],'noise.citation')
    survey._sha(noise['values_sha256'],'noise.values_sha256')
    survey._finite(request)
    if not np.array_equal(observed['rows'],rows): raise ValueError('evaluation: exact outer row binding')
    if survey._digest({k:v for k,v in observed.items() if k!='values_sha256'})!=observed['values_sha256']:
        raise ValueError('evaluation: observation hash mismatch')
    if survey._digest({k:noise[k] for k in ('kind','unit','values')}|{'rows':rows})!=noise['values_sha256']:
        raise ValueError('evaluation: noise hash mismatch')
    _validate_frozen(frozen)
    observed = survey._snapshot(observed)
    prediction = survey._readonly(frozen['predictions']['gz_up_mgal'][rows])
    phi,wrms,rmse,residual,whitened = _marginal_metrics(prediction,observed['gz_up_mgal'],
        {k:noise[k] for k in ('kind','values')},np.arange(len(rows),dtype=np.int64))
    result = {'schema':'gravity-survey-l2-evaluation-result-1','calibration_sha256':frozen['result_sha256'],
        'observations':observed,'noise_sha256':noise['values_sha256'],'rows':survey._readonly(rows),'predicted_mgal':prediction,
        'residual_observed_minus_predicted_mgal':survey._readonly(residual),'whitened_residual':survey._readonly(whitened),
        'phi_d':phi,'wrms':wrms,'rmse_mgal':rmse,
        'prediction_quality':'within_declared_noise' if wrms<=2. else 'poor_under_declared_noise',
        'dependence':noise['cross_partition_dependence'],'geometry_conditioning':'fixed_not_propagated',
        'field_truth':None,'model_accuracy':None,'field_eligible':False,'full_M02_accepted':False}
    result['result_sha256'] = survey._digest(result)
    return result
