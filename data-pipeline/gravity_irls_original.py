"""Original-noise, source-owned IRLS partition with the approved corrector.

The public boundary accepts physical request DTOs only. Native construction,
fixed Sparse weights, original noise actions and lifetime are owned here.
This prospective cpu3 epoch does not upgrade historical plain/cpu2 results.
"""
import hashlib
from pathlib import Path
from time import monotonic

import numpy as np

import gravity_original_optimizer as original
import gravity_irls_corrected as corrected


RUNTIME_EPOCH = 'm02-survey-irls-cpu-3'
POLICY = 'safeguarded-irls-interior-threepair-original-noise-reduced-1'
SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
REQUEST_SCHEMA = 'gravity-survey-irls-original-calibration-request-1'
RESULT_SCHEMA = 'gravity-survey-irls-original-calibration-result-1'
EVALUATION_SCHEMA = 'gravity-survey-irls-original-evaluation-request-1'
EVALUATION_RESULT_SCHEMA = 'gravity-survey-irls-original-evaluation-result-1'


def source_inventory():
    import gravity_irls_pool
    sources = original.source_inventory()
    sources.update(corrected._SOURCES)
    sources['gravity_irls_pool'] = gravity_irls_pool.SOURCE_SHA256
    sources[Path(__file__).name] = SOURCE_SHA256
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError('original IRLS: loaded source changed')
    return sources


def allocation_plan(n, m, a, covariance):
    base = original.allocation_plan(n, m, a, covariance)
    extra = dict(retained_native_stages=21*sum(base['retained_audits'].values()),
        auxiliary_proposals=63*(20*(8*a+2048)+8*12*a+32768),
        sparse_stage_records=21*(8*8*a+32768))
    admitted = base['admitted_bytes']+sum(extra.values())
    if admitted > 2*1024**3:
        raise ValueError('original IRLS: simultaneous22 native ledgers exceed original2GiB')
    value = dict(base, admitted_bytes=admitted, irls_retained=extra,
        partition_epoch=RUNTIME_EPOCH, auxiliary_CG_calls=126, anchors=63)
    value.pop('allocation_plan_sha256')
    value['allocation_plan_sha256'] = original.physics.survey._digest(value)
    return value


class GravityIRLSPartition:
    """Closed original physical constructor; no caller native objects/actions."""
    def __init__(self, request, observations, noise, prior, rows, beta_candidate, *,
                 observation_rows=None, deadline):
        p = original.physics
        p.survey._native_metadata(dict(request=request, observations=observations,
            noise=noise, prior=prior, rows=rows, beta_candidate=beta_candidate,
            observation_rows=observation_rows))
        if type(deadline) is not float or not np.isfinite(deadline):
            raise ValueError('original IRLS: finite original absolute clock')
        self.started = monotonic()
        self.deadline = min(deadline, self.started+120.)
        p.metric._time(self.deadline)
        p.survey._keys(noise, ('kind', 'values'), 'original IRLS noise')
        p.survey._enum(noise['kind'], ('diagonal_sd', 'full_covariance'), 'noise.kind')
        self.allocation = allocation_plan(len(request['stations']['receivers_m']),
            len(rows), len(prior['start_kg_m3']), noise['kind'] == 'full_covariance')
        self.problem = p._build_problem(request, observations, noise, prior, rows,
            beta_candidate, observation_rows=observation_rows)
        self.prior = p.survey._snapshot(prior)
        self.noise = p.survey._snapshot(noise)
        self.positions = p.survey._readonly(rows if observation_rows is None else
            np.searchsorted(observation_rows, rows))
        self.inventory = source_inventory()
        self.base_hash = corrected._problem_hash(self.problem, self.prior, {})
        self.closed = False
        self.initial_evidence = None

    def check(self):
        if self.closed:
            raise ValueError('original IRLS: disposed partition')
        original.physics.metric._time(self.deadline)
        if (self.inventory != source_inventory() or self.base_hash !=
                corrected._problem_hash(self.problem, self.prior, {})):
            raise ValueError('original IRLS: source/physical base drift')

    def _adapter(self, problem, q, index, stage=None):
        self.check()
        prior = dict(self.prior, start_kg_m3=np.ascontiguousarray(q*1000.))
        adapter = original._Objective(problem, prior, self.noise, self.positions,
            self.inventory, self.allocation)
        # q is an actual retained native vector, not rho/1000 rounded again.
        # The physical output remains1000*q; native stage starts do not move
        # silently by one ULP without an accepted-step ledger entry.
        adapter.start = original.physics.survey._readonly(q.copy())
        adapter.identity_value['objective_sha256'] = original.owned.digest((
            adapter.identity_value['objective_sha256'], adapter.start))
        if stage is not None:
            # Native Sparse is never granted the ordinary-L2 zero-row allowance.
            if adapter.zero_row_terms:
                raise ValueError('unsupported_sparse_empty_face')
            adapter.identity_value['stage_index'] = index
            adapter.identity_value['objective_sha256'] = original.owned.digest((
                adapter.identity_value['objective_sha256'], stage['epsilon'],
                stage['objective_sha256'], stage['policy_sha256']))
        # Rebind after the exact native stage identity is installed.
        adapter.source_digest = original.accuracy._source_digest(adapter.quadratic_operands(q))
        return adapter

    def initialize(self):
        self.check()
        q = self.prior['start_kg_m3']/1000.
        adapter = self._adapter(self.problem, q, 0)
        started = monotonic()
        raw, _, _ = original._solve_adapter(adapter, self.deadline, 200)
        self.initial_evidence = raw
        trace = dict(raw['trace'])
        trace.pop('models_q')
        trace['models_kg_m3'] = original.physics.survey._readonly(raw['trace']['models_q']*1000.)
        prediction = None if raw['q'] is None else self.problem['simulation'].dpred(raw['q'])+self.problem['background']
        result = {k:raw[k] for k in ('status', 'reason', 'phi_d', 'phi_m',
            'phi_engine', 'kkt_normalized', 'iterations')}
        result.update(model_kg_m3=None if raw['q'] is None else raw['q']*1000.,
            beta_candidate=self.problem['beta_candidate'], beta_engine=float(self.problem['beta_engine']),
            fit_rows=self.problem['rows'], predicted_mgal=prediction,
            residual_observed_minus_predicted_mgal=None if prediction is None else self.problem['observations']-prediction,
            wrms=None if raw['phi_d'] is None else float(np.sqrt(raw['phi_d']/len(self.problem['rows']))),
            trace=trace, wall_seconds=monotonic()-started,
            failed_trial=None if raw['status'] == 'converged' else
                dict(iteration=raw['iterations'], reason=raw['reason']))
        return result

    def solve_stage(self, q, policy, index, initial, remaining_steps):
        self.check()
        stage = corrected._stage(self.problem, q, policy, index, initial)
        adapter = self._adapter(stage['problem'], q, index, stage)
        result, _, _ = original._solve_adapter(adapter, self.deadline, remaining_steps)
        return result

    def thresholds(self, policy, q):
        kernels = [child.f_m(q) for alpha, child in zip(
            self.problem['regularization'].multipliers, self.problem['regularization'].objfcts) if alpha > 0.]
        if len(kernels) != 4 or any(k.size == 0 for k in kernels):
            return None
        return tuple(max(f, float(np.max(np.abs(k)))) for f, k in zip(policy['epsilon_floor'], kernels))

    def replay_native(self, raw, problem, q, index, stage, thin, *, physical=False):
        """Actual H actions/source chords/strong bounds, never minimize or CG."""
        adapter = self._adapter(problem, q, index, stage)
        p = original.physics
        p.survey._keys(raw, ('status', 'reason', 'q', 'phi_d', 'phi_m', 'phi_engine',
            'kkt_normalized', 'iterations', 'trace', 'failed_trial', 'runtime_epoch', 'policy',
            'conditioning_attempts', 'terminal_audits', 'line_search_trials', 'source_binding',
            'ray_initializations'), 'complete source-native book')
        expected_sources = dict(optimizer=original.SOURCE_SHA256, metric=original.owned.SOURCE_SHA256,
            numeric_kernel=original.owned.KERNEL_SHA256, vendor=original.reduced.VENDOR_SOURCE_SHA256,
            original_linear=original.reduced.core.linear.SOURCE_SHA256,
            original_nonlinear=original.reduced.core.nonlinear.SOURCE_SHA256,
            conditioned_dependency=original.reduced.core.SOURCE_SHA256,
            original_arithmetic=original.source.SOURCE_SHA256, original_terminal=original.accuracy.SOURCE_SHA256,
            reduced_dependency=original.reduced.SOURCE_SHA256)
        if (raw['runtime_epoch'] != original.LINEAR_EPOCH or raw['policy'] != original.POLICY
            or raw['source_binding'] != expected_sources):
            raise ValueError('original replay: actual native source/epoch binding')
        models, trace = raw['trace']['models_q'], raw['trace']
        p.survey._keys(trace, ('models_q', 'phi_d', 'phi_m', 'phi_engine', 'kkt_normalized',
            'relative_changes', 'line_search_counts', 'cg_counts'), 'source-native trace')
        if (type(raw['iterations']) is not int or not 0 <= raw['iterations'] <= 200
            or len(models) != raw['iterations']+1 and len(models)
            or any(type(raw[key]) is not tuple or len(raw[key]) > limit for key, limit in (
                ('conditioning_attempts', 512), ('terminal_audits', 201), ('line_search_trials', 4000),
                ('ray_initializations', 201)))):
            raise ValueError('original replay: closed native book/cap')
        if (len(models) and (raw['q'] is None or not np.array_equal(raw['q'], models[-1]))
            or not len(models) and raw['q'] is not None):
            raise ValueError('original replay: actual native terminal model')
        for key in ('status', 'reason', 'phi_d', 'phi_m', 'phi_engine', 'kkt_normalized', 'iterations'):
            if raw[key] != thin[key]:
                raise ValueError('original replay: thin versus complete native evidence')
        thin_models = thin['trace']['models_kg_m3'] if physical else thin['trace']['models_q']
        if not np.array_equal(models*1000. if physical else models, thin_models):
            raise ValueError('original replay: actual native state identity')
        for key in trace.keys()-{'models_q'}:
            if not np.array_equal(trace[key], thin['trace'][key]):
                raise ValueError('original replay: actual native trace identity')
        if not len(models):
            if raw['status'] == 'converged':
                raise ValueError('original replay: empty success')
            return
        if not np.array_equal(models[0], adapter.start):
            raise ValueError('original replay: actual original native start')
        norm = max(1., float(np.linalg.norm(adapter.evaluate(models[0], True)[1], np.inf)))
        gradient_previous = None
        for i, state in enumerate(models):
            self.check()
            components = adapter.components(state)
            gradient = adapter.evaluate(state, True)[1]
            absolute = float(np.linalg.norm(p._kkt_gradient(state, gradient, adapter.lower, adapter.upper), np.inf))
            corrected.plain._close(tuple(components.values())+(absolute/norm,),
                tuple(trace[k][i] for k in ('phi_d', 'phi_m', 'phi_engine', 'kkt_normalized')),
                'original native phase metrics')
            if i:
                count = int(trace['line_search_counts'][i-1])
                if not 1 <= count <= 20 or not 0 <= int(trace['cg_counts'][i-1]) <= 200:
                    raise ValueError('original replay: original native method caps')
                proof = adapter.certify(models[i-1], state, gradient_previous,
                    float(trace['phi_engine'][i-1]), float(trace['phi_engine'][i]), i-1, count-1, self.deadline)
                if proof['decision'] != 'certified_accept':
                    raise ValueError('original replay: source-original Armijo')
            gradient_previous = gradient
        native = p.optimization.ProjectedGNCG(lower=adapter.lower, upper=adapter.upper,
            cg_maxiter=200, cg_rtol=1e-6, cg_atol=0.)
        iteration = -1
        counts = {}
        previous_direction = None
        previous_phase = -1
        for phase in raw['conditioning_attempts']:
            self.check()
            if (type(phase['iteration']) is not int or not 0 <= phase['iteration'] < len(models)
                or type(phase['phase']) is not int or not 0 <= phase['phase'] <= len(q)
                or type(phase['iterations']) is not int or not 0 <= phase['iterations'] <= 200):
                raise ValueError('original replay: exact phase/count identity')
            if phase['branch'] == 'admission_refusal':
                if raw['status'] == 'converged' or phase['failure'] is None or phase['iterations'] != 0:
                    raise ValueError('original replay: construction refusal cannot pass')
                continue
            if phase['iteration'] != iteration:
                iteration = phase['iteration']
                state = models[iteration]
                _, gradient, hessian = adapter.evaluate(state, True, True)
                native.g = gradient.copy()
                mask = native.bindingSet(state).copy()
                previous_phase, previous_direction = -1, None
                if (not np.array_equal(phase.get('q'), state)
                    or not np.array_equal(phase.get('gradient'), gradient) or phase['phase'] != 0):
                    raise ValueError('original replay: source-native phase state')
            delta = phase['frozen_delta']
            expected_delta = (np.empty(0, dtype=np.int64) if previous_direction is None else
                np.flatnonzero(((state == adapter.lower) & (previous_direction < 0.))
                    | ((state == adapter.upper) & (previous_direction > 0.))).astype(np.int64))
            if (phase['phase'] != previous_phase+1 or delta.dtype != np.int64 or not np.array_equal(delta, expected_delta)
                or previous_phase >= 0 and not len(expected_delta)):
                raise ValueError('original replay: actual outward-face refinement')
            previous_phase = phase['phase']
            mask[delta] = True
            if original.owned.digest(mask) != phase['working_mask_sha256']:
                raise ValueError('original replay: native/free-face mask drift')
            if phase['failure'] is not None:
                if raw['status'] == 'converged':
                    raise ValueError('original replay: failed native phase relabelled')
                continue
            direction = phase['direction']
            residual = (~mask)*(-gradient-hessian@direction)
            rhs = float(np.linalg.norm((~mask)*gradient))
            relative = float(np.linalg.norm(residual))/rhs if rhs else float(np.linalg.norm(residual))
            if type(phase['true_relative_residual']) is not float or relative != phase['true_relative_residual']:
                raise ValueError('original replay: exact actual native-H residual')
            if relative > 1e-6 or np.any(direction[mask] != 0.):
                raise ValueError('original replay: original true residual/free face')
            counts[iteration] = counts.get(iteration, 0)+phase['iterations']
            if (counts[iteration] > 200 or phase['cumulative_CG'] != counts[iteration]
                or phase['cg_remaining'] != 200-counts[iteration]):
                raise ValueError('original replay: summed original CG200')
            previous_direction = direction
        for i, count in enumerate(trace['cg_counts']):
            if counts.get(i, 0) != count:
                raise ValueError('original replay: phase/accepted CG count agreement')
        if raw['status'] == 'converged':
            if raw['reason'] == 'absolute_stationary':
                if absolute > 1e-12:
                    raise ValueError('original replay: original absolute stopping')
            elif (raw['reason'] != 'kkt_stable' or len(models) < 4 or absolute/norm > 1e-5
                  or np.any(trace['relative_changes'][-3:] > 1e-6)):
                raise ValueError('original replay: original stable stopping')
            stored = raw['terminal_audits'][-1]['check']
            if not stored or stored['passed'] is not True or stored['disposed'] is not True:
                raise ValueError('original replay: absent actual stronger terminal')
            state = models[-1]
            terminal_owner = original.accuracy.OwnedOriginalTerminal(adapter.metric_operands(state),
                adapter.quadratic_operands(state), adapter.identity(), state,
                adapter.evaluate(state, True)[1], norm, deadline=self.deadline,
                resource_limit_bytes=2*1024**3, admitted_bytes=self.allocation['admitted_bytes'])
            try:
                fresh = terminal_owner.certify(original.owned.TerminalPolicy(1e-7, 1e-8, 1e-8, 1e-6))
            finally:
                terminal_owner.close()
            for key in ('passed', 'bounds', 'kappa_upper', 'eta_upper', 'factor_sha256',
                        'face_sha256', 'source_sha256', 'active_sign_pass', 'inside_original_bounds', 'proof_basis'):
                if fresh[key] != stored[key]:
                    raise ValueError('original replay: recomputed stronger terminal differs')
        adapter.release_state()

    def close(self):
        self.closed = True
        self.initial_evidence = None
        self.problem = self.prior = self.noise = self.positions = self.inventory = None


def solve_partition(request, observations, noise, prior, rows, beta_candidate, *,
                    policy, observation_rows=None, deadline):
    """One original partition, same200 accepted/201states/120s, no hooks."""
    owner = GravityIRLSPartition(request, observations, noise, prior, rows,
        beta_candidate, observation_rows=observation_rows, deadline=deadline)
    try:
        return corrected._solve_partition(owner.problem, owner.prior, policy,
            owner.deadline, original_owner=owner)
    finally:
        owner.close()


def validate_partition(result, request, observations, noise, prior, rows, beta_candidate, *,
                       policy, observation_rows=None):
    """Closed original physics replay, no optimizer, no reclassification."""
    original.physics._result_native_metadata(dict(result=result, prior=prior, policy=policy))
    owner = GravityIRLSPartition(request, observations, noise, prior, rows, beta_candidate,
        observation_rows=observation_rows, deadline=monotonic()+120.)
    try:
        return corrected._validate_partition(result, owner.problem, owner.prior,
            policy, original_owner=owner)
    finally:
        owner.close()


def admit(request):
    from gravity_irls_corrected_workflow import _Workflow
    return _Workflow('cpu3').admit(request)


def calibrate(request):
    from gravity_irls_corrected_workflow import _Workflow
    return _Workflow('cpu3').calibrate(request)


def validate(result, request):
    from gravity_irls_corrected_workflow import _Workflow
    return _Workflow('cpu3').validate(result, request)


def evaluate(request):
    from gravity_irls_corrected_workflow import _Workflow
    return _Workflow('cpu3').evaluate(request)
