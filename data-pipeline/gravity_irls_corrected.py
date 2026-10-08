"""Source-action safeguarded scaled IRLS, explicit cpu2 policy.

Actual native fixed quadratics and pinned library auxiliary CG, not a new
physical objective, copied optimizer, dense inverse or source admission registry.
The original cpu1/plain assertion and archive reader remain unchanged.
"""
import hashlib
import inspect
from pathlib import Path
from time import monotonic

import numpy as np
from scipy.sparse.linalg import LinearOperator, cg

import gravity_irls as plain


POLICY = 'safeguarded-irls-interior-threepair-log17-stage-1'
RUNTIME_EPOCH = 'm02-survey-irls-cpu-2'
SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
_SOURCES = dict(plain._SOURCES)
_SOURCES[Path(__file__).name] = SOURCE_SHA256
_SOURCES['scipy.cg'] = hashlib.sha256(Path(inspect.getfile(cg)).read_bytes()).hexdigest()
_INVENTORY = plain.survey._digest(_SOURCES)
_REASONS = ('iteration_cap', 'wall_cap', 'auxiliary_call_cap', 'auxiliary_cg_cap',
            'rank_one_denominator', 'rank_one_conditioning', 'merit_non_descent',
            'merit_line_search_failed', 'nonfinite', 'state_mismatch', 'engine_error')


class _Failure(RuntimeError):
    pass


class _Budget:
    def __init__(self, deadline):
        if type(deadline) is not float or not np.isfinite(deadline):
            raise ValueError('corrected IRLS: finite absolute deadline')
        self.deadline = min(deadline, monotonic()+120.)
        self.steps = self.calls = self.evaluations = 0

    def check(self):
        if monotonic() > self.deadline:
            raise _Failure('wall_cap')
        if self.steps > 200:
            raise _Failure('iteration_cap')

    def adopt(self):
        self.check()
        if self.steps >= 200:
            raise _Failure('iteration_cap')
        self.steps += 1

    def begin_call(self):
        self.check()
        if self.calls >= 126:
            raise _Failure('auxiliary_call_cap')
        self.calls += 1


def _finite(value):
    if not np.isfinite(value).all():
        raise _Failure('nonfinite')
    return value


def _freeze(value):
    if type(value) is np.ndarray:
        return plain.survey._readonly(value)
    if type(value) in (list, tuple):
        return tuple(_freeze(v) for v in value)
    if type(value) is dict:
        return {k: _freeze(v) for k, v in value.items()}
    return value


def _problem_hash(problem, prior, policy):
    reg = problem['regularization']
    return plain.survey._digest(dict(G=problem['simulation'].G,
        W=plain._sparse_snapshot(problem['misfit'].W), dobs=problem['misfit'].data.dobs,
        background=problem['background'], reference=problem['reference_q'],
        alpha=problem['alpha'], beta=float(problem['beta_engine']), prior=prior, policy=policy,
        regularizer=tuple(dict(alpha=float(alpha), W=plain._sparse_snapshot(child.W),
            D=plain._sparse_snapshot(child.f_m_deriv(problem['reference_q'])),
            reference=child.reference_model) for alpha, child in zip(reg.multipliers, reg.objfcts))))


def _stage(problem, q, policy, index, initial):
    stage = plain._build_stage(problem, q, policy, index, initial)
    stage['policy_sha256'] = plain.survey._digest(dict(name=POLICY, irls=policy))
    stage['objective_sha256'] = plain._seal(stage['problem'], stage['epsilon'], stage['policy_sha256'])
    return stage


class _Objective(plain._StageObjective):
    def identity(self):
        value = super().identity()
        value['source_inventory_sha256'] = _INVENTORY
        return value


def _branch(q, reference, lower, upper):
    x = q-reference
    if not np.any(x):
        return 'disabled_null', None
    maximum = np.max(np.abs(x))
    indices = np.flatnonzero(np.abs(x) == maximum)
    if len(indices) != 1:
        return 'disabled_tied_max', None
    j = int(indices[0])
    active = (q == lower) | (q == upper)
    if np.any(active):
        return 'disabled_bound_face_active_max' if active[j] else 'disabled_bound_face_free_max', j
    return 'interior_unique_nonzero_max', j


def _denominator(c, j):
    _finite(c)
    delta = float(1.+c[j])
    ratio = delta/(1.+float(np.linalg.norm(c, np.inf)))
    if not np.isfinite(delta) or delta <= 0.:
        raise _Failure('rank_one_denominator')
    if not np.isfinite(ratio) or ratio < np.sqrt(np.finfo(np.float64).eps):
        raise _Failure('rank_one_conditioning')
    return delta, ratio


def _linearization(problem, stage, objective, q, deadline):
    """Native likelihood/directional actions, no dense H or smallness subtraction."""
    x = q-problem['reference_q']
    j = int(np.argmax(abs(x)))
    eps = stage['epsilon'][0]
    reg = stage['problem']['regularization']
    beta = problem['beta_engine']
    v = beta*problem['regularization'].multipliers[0]*problem['regularization'].objfcts[0].W.diagonal()**2
    with np.errstate(over='raise', invalid='raise', divide='raise', under='ignore'):
        d = _finite(np.sqrt(x*x+eps*eps))
        scale = float(np.sqrt(x[j]*x[j]+eps*eps))
        correction = _finite(v*scale*eps**2/d**3)
        u = _finite(v*x*x[j]/(d*scale))
    if np.any(v <= 0.) or np.any(correction <= 0.):
        raise _Failure('nonfinite')
    def check():
        if monotonic() > deadline:
            raise _Failure('wall_cap')
    def action(vector):
        check()
        _finite(vector)
        value = problem['misfit'].deriv2(q, vector)/2.
        for alpha, child in zip(reg.multipliers[1:], reg.objfcts[1:]):
            value += beta*alpha*child.deriv2(q, vector)/2.
        value += correction*vector
        check()
        return _finite(value)
    check()
    wg = problem['misfit'].W@problem['simulation'].G
    diagonal = np.sum(wg*wg, axis=0)
    for alpha, child in zip(reg.multipliers[1:], reg.objfcts[1:]):
        diagonal += beta*alpha*child.deriv2(q).diagonal()/2.
    diagonal += correction
    _finite(diagonal)
    if np.any(diagonal <= 0.):
        raise _Failure('nonfinite')
    check()
    return LinearOperator((len(q), len(q)), matvec=action, dtype=np.float64), u, j, diagonal


def _canonical(problem, q, policy, index, initial, lower, upper, allocation, budget):
    budget.check()
    stage = _stage(problem, q, policy, index, initial)
    obj = _Objective(stage, index, lower, upper, allocation)
    obj.identity()
    phi, gradient = obj.evaluate(q, True, False)
    _finite(gradient)
    _finite(phi)
    budget.evaluations += 1
    budget.check()
    return stage, obj, gradient/2.


def _cg(operator, diagonal, rhs, kind, budget, record):
    budget.begin_call()
    started = monotonic()
    row = dict(kind=kind, rhs=rhs.copy(), solution=None, info=None, iterations=0,
               matvecs=0, metric_actions=0, absolute_residual=None,
               relative_residual=None, seconds=0., status='aborted')
    record.append(row)
    def action(v):
        budget.check()
        row['matvecs'] += 1
        result = operator@v
        budget.check()
        return _finite(result)
    def metric(v):
        budget.check()
        row['metric_actions'] += 1
        result = v/diagonal
        budget.check()
        return _finite(result)
    def observe(value):
        row['iterations'] += 1
        row['solution'] = value.copy()
        budget.check()
    native_operator = LinearOperator(operator.shape, matvec=action, dtype=np.float64)
    native_metric = LinearOperator(operator.shape, matvec=metric, dtype=np.float64)
    try:
        solution, info = cg(native_operator, rhs, M=native_metric, rtol=1e-6,
                            atol=0., maxiter=200, callback=observe)
        row.update(solution=solution.copy(), info=int(info), status='returned')
        true = float(np.linalg.norm(action(solution)-rhs))
        norm = float(np.linalg.norm(rhs))
        relative = true/norm if norm else true
        row.update(absolute_residual=true, relative_residual=relative)
        if info != 0 or row['iterations'] > 200 or not np.isfinite(relative) or relative > 1e-6:
            raise _Failure('auxiliary_cg_cap')
        return solution
    finally:
        row['seconds'] = float(monotonic()-started)


def solve_partition(problem, prior, policy, deadline):
    """One trusted native partition; explicit separate epoch, no caller hooks/I/O."""
    return _solve_partition(problem, prior, policy, deadline)


def _solve_partition(problem, prior, policy, deadline, *, original_owner=None):
    """Shared approved orchestration; only the closed physical owner is allowed."""
    if original_owner is not None:
        import gravity_irls_original as prospective
        if (type(original_owner) is not prospective.GravityIRLSPartition
            or original_owner.problem is not problem
            or plain.survey._digest(prior) != plain.survey._digest(original_owner.prior)):
            raise ValueError('corrected IRLS: exact original physical owner required')
        original_owner.check()
    started = monotonic()
    policy = plain._validate_policy(policy)
    budget = _Budget(deadline)
    lower, upper = prior['lower_kg_m3']/1000., prior['upper_kg_m3']/1000.
    initialization = (plain.l2._solve_partition(problem, prior, budget.deadline)
        if original_owner is None else original_owner.initialize())
    budget.steps = initialization['iterations']
    a = len(lower)
    models = [row/1000. for row in initialization['trace']['models_kg_m3']]
    kinds, labels = [0]*len(models), [-1]*len(models)
    attempts, stages, changes = [], [], []
    native_evidence = []
    q = initialization['model_kg_m3']/1000. if initialization['model_kg_m3'] is not None else None
    initial = plain._initial_thresholds(problem, initialization, policy)
    previous_weights = None
    status, reason = initialization['status'], initialization['reason']
    n = problem['simulation'].G.shape[0]
    admitted = 8*(8*n*a)+12*(8*n*n)+4096*(44*a+12*n)+576*1024**2
    allocation = plain.survey._digest(dict(n=n, a=a, bytes=admitted,
        rule='original_full_covariance_upper_plus_matrixfree_threepair_1'))
    if original_owner is not None:
        admitted = original_owner.allocation['admitted_bytes']
        allocation = original_owner.allocation['allocation_plan_sha256']
    # Auxiliary retained vectors are output; temporary M actions are sparse/
    # vector-only inside the existing native/trace reserve, not a dense inverse.
    if admitted > 2*1024**3:
        raise ValueError('corrected IRLS: unchanged2GiB admission')
    try:
        if initialization['status'] == 'converged':
            if initial is None:
                raise ValueError('unsupported_sparse_empty_face')
            for index in range(21):
                budget.check()
                previous = q.copy()
                stage_start, attempt_start = len(models)-1, len(attempts)
                for correction in range(3):
                    budget.check()
                    branch, j = _branch(q, problem['reference_q'], lower, upper)
                    row = dict(stage=index, correction=correction, model_row=len(models)-1,
                               branch=branch, maximum_index=j, outcome='disabled', cg=[], trials=[])
                    attempts.append(row)
                    if branch != 'interior_unique_nonzero_max':
                        break
                    stage, obj, r = _canonical(problem, q, policy, index, initial,
                                                lower, upper, allocation, budget)
                    row['canonical_gradient'] = 2*r
                    if float(np.linalg.norm(2*r, np.inf)) <= 1e-12:
                        row['outcome'] = 'canonical_absolute_stationary'
                        break
                    if budget.steps >= 200:
                        raise _Failure('iteration_cap')
                    m, u, j, diagonal = _linearization(problem, stage, obj, q, budget.deadline)
                    aa = _cg(m, diagonal, -r, 'newton_rhs', budget, row['cg'])
                    cc = _cg(m, diagonal, u, 'rank_one_rhs', budget, row['cg'])
                    obj.identity()
                    delta, ratio = _denominator(cc, j)
                    p = _finite(aa-cc*aa[j]/delta)
                    jp = _finite(m@p+u*p[j])
                    slope = float(np.inner(r, jp))
                    row.update(denominator=delta, conditioning_ratio=ratio, direction=p.copy(),
                               merit_slope=slope, root_linear_residual=float(np.linalg.norm(jp+r)),
                               root_relative_residual=float(np.linalg.norm(jp+r)/np.linalg.norm(r)))
                    if not np.isfinite(slope) or slope >= 0. or not np.any(p):
                        raise _Failure('merit_non_descent')
                    psi = float(np.inner(r, r)/2.)
                    for trial in range(20):
                        budget.check()
                        alpha = float(2.**(-trial))
                        qt = _finite(q+alpha*p)
                        interior = bool(np.all(qt > lower) and np.all(qt < upper))
                        nonzero = bool(np.any(qt != q))
                        trial_row = dict(trial=trial, alpha=alpha, q=qt.copy(), interior=interior,
                                         nonzero=nonzero, merit_margin=None, accepted=False)
                        row['trials'].append(trial_row)
                        if interior and nonzero:
                            _, _, rt = _canonical(problem, qt, policy, index, initial,
                                                    lower, upper, allocation, budget)
                            margin = float(np.inner(rt, rt)/2.-psi-1e-4*alpha*slope)
                            _finite(margin)
                            trial_row.update(merit_margin=margin, accepted=bool(margin < 0.))
                        if trial_row['accepted']:
                            budget.adopt()
                            q = qt.copy()
                            models.append(q.copy())
                            kinds.append(1)
                            labels.append(index)
                            row['outcome'] = 'adopted'
                            break
                    else:
                        raise _Failure('merit_line_search_failed')
                stage, obj, r = _canonical(problem, q, policy, index, initial,
                                            lower, upper, allocation, budget)
                adopted = len(models)-1
                weights = stage['weights'][0]
                binding = plain.optimizer.OptimizerBinding('physical_optimizer.solve_bounded_physical',
                    plain.optimizer.SOURCE_SHA256, plain._SOURCES[Path(plain.precision.__file__).name],
                    _INVENTORY, plain.optimizer.RUNTIME_EPOCH, plain.optimizer.POLICY)
                native_budget = plain.optimizer.OptimizerBudget(budget.deadline, 200-budget.steps,
                    2*1024**3, admitted, allocation)
                norm = max(1., float(np.linalg.norm(2*r, np.inf)))
                inner = (plain.optimizer.solve_bounded_physical(obj, lower, upper, q.copy(),
                    budget=native_budget, binding=binding) if original_owner is None else
                    original_owner.solve_stage(q.copy(), policy, index, initial, 200-budget.steps))
                if original_owner is not None:
                    # Lossless separately bounded books, not a deeper logical
                    # tree or a relaxed original eight-container transport cap.
                    import gravity_irls_pool as pool
                    native_evidence.append(pool.encode(_freeze(inner)))
                    inner = {k:inner[k] for k in ('status', 'reason', 'q', 'phi_d', 'phi_m',
                        'phi_engine', 'kkt_normalized', 'iterations', 'trace', 'failed_trial')}
                budget.steps += inner['iterations']
                for value in inner['trace']['models_q'][1:]:
                    models.append(value.copy())
                    kinds.append(2)
                    labels.append(index)
                if inner['q'] is not None:
                    q = inner['q'].copy()
                native_row = dict(index=index, epsilon=stage['epsilon'], weight_sha256=stage['weight_sha256'],
                    operator_sha256=stage['operator_sha256'], adopted_weights=weights.copy(),
                    start_row=stage_start, adopted_row=adopted, stop_row=len(models)-1,
                    attempt_span=(attempt_start, len(attempts)), remaining_steps=native_budget.remaining_steps,
                    inner=inner, canonical_gradient=None, canonical_absolute_kkt=None,
                    canonical_normalized_kkt=None, canonical_weight_mismatch=None, initial_gradient_norm=norm)
                stages.append(native_row)
                canonical_stage, _, canonical_r = _canonical(problem, q, policy, index, initial,
                                                             lower, upper, allocation, budget)
                canonical_g = 2*canonical_r
                absolute = float(np.linalg.norm(plain.l2._kkt_gradient(q, canonical_g, lower, upper), np.inf))
                mismatch = float(np.linalg.norm(canonical_stage['weights'][0]-weights, np.inf)
                                 /max(1., float(np.linalg.norm(weights, np.inf))))
                native_row.update(canonical_gradient=canonical_g, canonical_absolute_kkt=absolute,
                                  canonical_normalized_kkt=absolute/norm, canonical_weight_mismatch=mismatch)
                if previous_weights is not None:
                    changes.append(dict(model_relative=float(np.linalg.norm(q-previous, np.inf)
                        /max(1., float(np.linalg.norm(previous, np.inf)))),
                        weights_relative=float(np.linalg.norm(weights-previous_weights, np.inf)
                        /max(1., float(np.linalg.norm(previous_weights, np.inf))))))
                previous_weights = weights.copy()
                if inner['status'] != 'converged':
                    status, reason = inner['status'], inner['reason']
                    break
                if index == 20:
                    success = plain._fixed_point(index, stage['epsilon'] == policy['epsilon_floor'], tuple(changes))
                    success = success and mismatch <= 1e-6 and (absolute <= 1e-12 or absolute/norm <= 1e-5)
                    null = not np.any(q-problem['reference_q']) and not np.any(canonical_g)
                    status = 'converged' if success else 'nonconverged'
                    reason = ('irls_stationary_null' if null else 'irls_fixed_point') if success else 'irls_iteration_cap'
            budget.check()
    except _Failure as error:
        reason = str(error)
        status = 'failed' if reason in ('nonfinite', 'state_mismatch', 'engine_error') else 'nonconverged'
        if attempts and attempts[-1]['outcome'] not in ('adopted', 'disabled', 'canonical_absolute_stationary'):
            attempts[-1]['outcome'] = reason
        elif attempts and attempts[-1]['branch'] == 'interior_unique_nonzero_max' and attempts[-1]['outcome'] == 'disabled':
            attempts[-1]['outcome'] = reason
    except ArithmeticError:
        reason, status = 'nonfinite', 'failed'
    except (ValueError, RuntimeError, TypeError, KeyError):
        reason, status = 'engine_error', 'failed'
    result = _freeze(dict(schema='gravity-irls-corrected-partition-1', runtime_epoch=RUNTIME_EPOCH,
        policy=POLICY, source_inventory=_SOURCES, problem_sha256=_problem_hash(problem, prior, policy),
        initialization=initialization, initial_epsilon=initial, stages=stages, attempts=attempts,
        models_q=np.array(models, dtype=np.float64).reshape(-1, a),
        event_kinds=np.array(kinds, dtype=np.int64), event_stages=np.array(labels, dtype=np.int64),
        iterations=budget.steps, auxiliary_calls=budget.calls, residual_evaluations=budget.evaluations,
        model_kg_m3=q*1000. if q is not None else None, wall_seconds=float(monotonic()-started),
        terminal=dict(status=status, reason=reason, weight_updates=max(0, len(stages)-1),
                      epsilon_saturated=bool(stages and stages[-1]['epsilon'] == policy['epsilon_floor']),
                      stage_changes=changes)))
    if original_owner is not None:
        result.update(schema='gravity-irls-original-partition-1',
            runtime_epoch=prospective.RUNTIME_EPOCH, policy=prospective.POLICY,
            source_inventory=original_owner.inventory,
            initialization_evidence=pool.encode(_freeze(original_owner.initial_evidence)),
            native_evidence=tuple(native_evidence),
            allocation_plan=original_owner.allocation,
            wall_seconds=float(monotonic()-original_owner.started))
    plain.l2._result_native_metadata(result)
    result['result_sha256'] = plain.survey._digest(result)
    plain.l2._result_native_metadata(result)
    return result


def validate_partition(result, problem, prior, policy):
    """Reconstruct physics/actions without CG/optimization; reject rehashed lies."""
    plain.l2._result_native_metadata(dict(result=result, prior=prior, policy=policy))
    plain.survey._keys(result, ('schema', 'runtime_epoch', 'policy', 'source_inventory', 'problem_sha256',
        'initialization', 'initial_epsilon', 'stages', 'attempts', 'models_q', 'event_kinds', 'event_stages',
        'iterations', 'auxiliary_calls', 'residual_evaluations', 'model_kg_m3', 'wall_seconds', 'terminal',
        'result_sha256'), 'corrected partition')
    policy = plain._validate_policy(policy)
    if (result['schema'] != 'gravity-irls-corrected-partition-1' or result['runtime_epoch'] != RUNTIME_EPOCH
        or result['policy'] != POLICY or result['source_inventory'] != _SOURCES
        or result['problem_sha256'] != _problem_hash(problem, prior, policy)
        or result['result_sha256'] != plain.survey._digest({k:v for k,v in result.items() if k != 'result_sha256'})):
        raise ValueError('corrected replay: exact source/epoch/input/result binding')
    plain.survey._finite(result)
    models, stages, attempts = result['models_q'], result['stages'], result['attempts']
    lower, upper = prior['lower_kg_m3']/1000., prior['upper_kg_m3']/1000.
    plain.survey._array(models, (None, len(lower)), 'combined actual models')
    steps = result['iterations']
    if (type(steps) is not int or not 0 <= steps <= 200 or len(models) != (steps+1 if len(models) else 0)
        or (not len(models) and steps) or type(result['wall_seconds']) is not float or result['wall_seconds'] < 0.):
        raise ValueError('corrected replay: combined accepted ledger')
    if np.any(models < lower) or np.any(models > upper):
        raise ValueError('corrected replay: original box')
    init = result['initialization']
    plain.l2._validate_solve_state(init, init['fit_rows'])
    prefix = init['trace']['models_kg_m3']/1000.
    if not np.array_equal(models[:len(prefix)], prefix):
        raise ValueError('corrected replay: actual native initialization prefix')
    if result['initial_epsilon'] != plain._initial_thresholds(problem, init, policy):
        raise ValueError('corrected replay: original thresholds')
    deadline = monotonic()+1800.
    _replay_native(init, problem, lower, upper, deadline, physical_initialization=True)
    if len(models):
        if result['model_kg_m3'] is None or not np.array_equal(result['model_kg_m3'], models[-1]*1000.):
            raise ValueError('corrected replay: actual physical terminal')
    elif result['model_kg_m3'] is not None:
        raise ValueError('corrected replay: unavailable initial state')
    expected_kinds, expected_labels = [0]*len(prefix), [-1]*len(prefix)
    calls = anchors = native_steps = 0
    previous_weights = None
    changes = []
    terminal = result['terminal']
    plain.survey._keys(terminal, ('status', 'reason', 'weight_updates', 'epsilon_saturated', 'stage_changes'), 'actual corrected terminal')
    failed = terminal['status'] in ('failed', 'nonconverged')
    if terminal['status'] not in ('failed', 'nonconverged', 'converged'):
        raise ValueError('corrected replay: literal terminal status')
    for attempt in attempts:
        base = {'stage', 'correction', 'model_row', 'branch', 'maximum_index', 'outcome', 'cg', 'trials'}
        optional = {'canonical_gradient', 'denominator', 'conditioning_ratio', 'direction', 'merit_slope',
                    'root_linear_residual', 'root_relative_residual'}
        if (type(attempt) is not dict or not base <= set(attempt) or set(attempt)-base-optional
            or type(attempt['cg']) is not tuple or len(attempt['cg']) > 2
            or type(attempt['trials']) is not tuple or len(attempt['trials']) > 20):
            raise ValueError('corrected replay: closed bounded attempt')
        if (type(attempt['stage']) is not int or not 0 <= attempt['stage'] <= 20
            or type(attempt['correction']) is not int or not 0 <= attempt['correction'] <= 2
            or type(attempt['model_row']) is not int or not 0 <= attempt['model_row'] < len(models)):
            raise ValueError('corrected replay: actual bounded proposal identity')
        q = models[attempt['model_row']]
        branch, j = _branch(q, problem['reference_q'], lower, upper)
        if (attempt['branch'], attempt['maximum_index']) != (branch, j):
            raise ValueError('corrected replay: derivative branch')
        if branch != 'interior_unique_nonzero_max':
            if attempt['cg'] or attempt['trials'] or attempt['outcome'] != 'disabled':
                raise ValueError('corrected replay: disabled derivative constructed proposal')
            continue
        stage = _stage(problem, q, policy, attempt['stage'], result['initial_epsilon'])
        obj = _Objective(stage, attempt['stage'], lower, upper, 'b'*64)
        r = obj.evaluate(q, True, False)[1]/2.
        if 'canonical_gradient' not in attempt:
            if (not failed or terminal['reason'] != 'wall_cap' or attempt is not attempts[-1]
                or attempt['cg'] or attempt['trials'] or 'direction' in attempt
                or attempt['outcome'] != 'wall_cap'):
                raise ValueError('corrected replay: unavailable failed canonical action')
            continue
        if not np.array_equal(attempt['canonical_gradient'], 2*r):
            raise ValueError('corrected replay: canonical residual')
        if attempt['outcome'] == 'canonical_absolute_stationary':
            if np.linalg.norm(2*r, np.inf) > 1e-12 or attempt['cg'] or attempt['trials']:
                raise ValueError('corrected replay: manufactured stationary anchor')
            continue
        m, u, j, diagonal = _linearization(problem, stage, obj, q, deadline)
        for ordinal, (call, rhs) in enumerate(zip(attempt['cg'], (-r, u))):
            calls += 1
            plain.survey._keys(call, ('kind', 'rhs', 'solution', 'info', 'iterations', 'matvecs',
                'metric_actions', 'absolute_residual', 'relative_residual', 'seconds', 'status'), 'actual auxiliary CG')
            if (type(call['seconds']) is not float or not 0. <= call['seconds'] <= result['wall_seconds']
                or any(type(call[k]) is not int or call[k] < 0 for k in ('iterations', 'matvecs', 'metric_actions'))
                or call['iterations'] > 200 or call['kind'] != ('newton_rhs', 'rank_one_rhs')[ordinal]
                or call['status'] not in ('returned', 'aborted')
                or not np.array_equal(call['rhs'], rhs)):
                raise ValueError('corrected replay: actual CG timing/count/rhs')
            if call['solution'] is not None:
                plain.survey._array(call['solution'], (len(lower),), 'actual auxiliary solution')
            if call['status'] == 'returned' and (type(call['info']) is not int or call['solution'] is None):
                raise ValueError('corrected replay: actual returned CG info/solution')
            if call['absolute_residual'] is not None:
                true = float(np.linalg.norm(m@call['solution']-rhs))
                relative = true/float(np.linalg.norm(rhs)) if np.any(rhs) else true
                if (true, relative) != (call['absolute_residual'], call['relative_residual']):
                    raise ValueError('corrected replay: actual CG true residual')
                if attempt['outcome'] == 'adopted' and (call['info'] != 0 or relative > 1e-6):
                    raise ValueError('corrected replay: failed CG anchor')
        if 'direction' not in attempt:
            if attempt['outcome'] == 'adopted' or attempt['trials']:
                raise ValueError('corrected replay: unavailable direction adopted/tested')
            continue
        if len(attempt['cg']) != 2:
            raise ValueError('corrected replay: actual pair')
        aa, cc = [c['solution'] for c in attempt['cg']]
        delta, ratio = _denominator(cc, j)
        p = aa-cc*aa[j]/delta
        jp = m@p+u*p[j]
        slope = float(np.inner(r, jp))
        if (delta != attempt['denominator'] or ratio != attempt['conditioning_ratio']
            or slope != attempt['merit_slope'] or not np.array_equal(p, attempt['direction'])
            or float(np.linalg.norm(jp+r)) != attempt['root_linear_residual']
            or float(np.linalg.norm(jp+r)/np.linalg.norm(r)) != attempt['root_relative_residual']):
            raise ValueError('corrected replay: rank-one/descent/linear residual')
        if slope >= 0. or not np.any(p):
            if (not failed or attempt['outcome'] != 'merit_non_descent' or attempt['trials']
                or terminal['reason'] != 'merit_non_descent' or attempt is not attempts[-1]):
                raise ValueError('corrected replay: failed actual merit descent')
            continue
        if attempt['outcome'] == 'adopted' and not attempt['trials']:
            raise ValueError('corrected replay: original trial cap')
        for index, trial in enumerate(attempt['trials']):
            plain.survey._keys(trial, ('trial', 'alpha', 'q', 'interior', 'nonzero', 'merit_margin', 'accepted'), 'actual merit trial')
            qt = q+float(2.**(-index))*p
            interior = bool(np.all(qt > lower) and np.all(qt < upper))
            nonzero = bool(np.any(qt != q))
            if (trial['trial'] != index or trial['alpha'] != float(2.**(-index))
                or not np.array_equal(qt, trial['q']) or trial['interior'] != interior or trial['nonzero'] != nonzero):
                raise ValueError('corrected replay: actual trial/chord')
            margin = None
            if interior and nonzero:
                trial_stage = _stage(problem, qt, policy, attempt['stage'], result['initial_epsilon'])
                trial_obj = _Objective(trial_stage, attempt['stage'], lower, upper, 'b'*64)
                rt = trial_obj.evaluate(qt, True, False)[1]/2.
                margin = float(np.inner(rt, rt)/2.-np.inner(r, r)/2.-1e-4*trial['alpha']*slope)
            if trial['merit_margin'] != margin or trial['accepted'] != (margin is not None and margin < 0.):
                raise ValueError('corrected replay: strict actual merit Armijo')
            if trial['accepted'] != (attempt['outcome'] == 'adopted' and index == len(attempt['trials'])-1):
                raise ValueError('corrected replay: no post-acceptance trials')
        if attempt['outcome'] != 'adopted':
            continue
        if not np.array_equal(models[attempt['model_row']+1], attempt['trials'][-1]['q']):
            raise ValueError('corrected replay: actual adopted anchor')
        anchors += 1
    for index, row in enumerate(stages):
        plain.survey._keys(row, ('index', 'epsilon', 'weight_sha256', 'operator_sha256', 'adopted_weights',
            'start_row', 'adopted_row', 'stop_row', 'attempt_span', 'remaining_steps', 'inner', 'canonical_gradient',
            'canonical_absolute_kkt', 'canonical_normalized_kkt', 'canonical_weight_mismatch', 'initial_gradient_norm'), 'actual native stage')
        if row['index'] != index or row['epsilon'] != tuple(plain._epsilon(x, f, index)
            for x, f in zip(result['initial_epsilon'], policy['epsilon_floor'])):
            raise ValueError('corrected replay: original schedule')
        q = models[row['adopted_row']]
        stage = _stage(problem, q, policy, index, result['initial_epsilon'])
        if (stage['weight_sha256'] != row['weight_sha256'] or stage['operator_sha256'] != row['operator_sha256']
            or not np.array_equal(stage['weights'][0], row['adopted_weights'])):
            raise ValueError('corrected replay: adopted native weights/operators')
        inner = row['inner']
        if (row['remaining_steps'] != 200-row['adopted_row'] or row['stop_row']-row['adopted_row'] != inner['iterations']
            or not 0 <= row['start_row'] <= row['adopted_row'] <= row['stop_row'] < len(models)
            or tuple(a['stage'] for a in attempts[slice(*row['attempt_span'])]) != (index,)*(row['attempt_span'][1]-row['attempt_span'][0])):
            raise ValueError('corrected replay: original shared remaining/native spans')
        if row['start_row'] != len(expected_kinds)-1:
            raise ValueError('corrected replay: no skipped combined states')
        expected_kinds.extend([1]*(row['adopted_row']-row['start_row']))
        expected_kinds.extend([2]*inner['iterations'])
        expected_labels.extend([index]*(row['stop_row']-row['start_row']))
        native_steps += inner['iterations']
        segment = models[row['adopted_row']:row['stop_row']+1]
        if not np.array_equal(segment, inner['trace']['models_q']) and not (
            not len(inner['trace']['models_q']) and inner['status'] != 'converged' and inner['iterations'] == 0):
            raise ValueError('corrected replay: native versus auxiliary model lineage')
        _replay_native(inner, stage['problem'], lower, upper, deadline)
        native_initial = stage['problem']['misfit'].deriv(q)+problem['beta_engine']*stage['problem']['regularization'].deriv(q)
        if row['initial_gradient_norm'] != max(1., float(np.linalg.norm(native_initial, np.inf))):
            raise ValueError('corrected replay: native gradient normalization')
        final_q = segment[-1]
        audit_fields = ('canonical_gradient', 'canonical_absolute_kkt', 'canonical_normalized_kkt', 'canonical_weight_mismatch')
        if any(row[k] is None for k in audit_fields):
            if (not failed or index != len(stages)-1
                or terminal['reason'] not in ('wall_cap', 'nonfinite', 'engine_error')
                or not all(row[k] is None for k in audit_fields)):
                raise ValueError('corrected replay: unavailable last failed canonical audit')
            # Actual native inner/weights/state were replayed above. Do not
            # fabricate an audit or transition absent from the expired run.
            continue
        canonical = _stage(problem, final_q, policy, index, result['initial_epsilon'])
        obj = _Objective(canonical, index, lower, upper, 'b'*64)
        gradient = obj.evaluate(final_q, True, False)[1]
        absolute = float(np.linalg.norm(plain.l2._kkt_gradient(final_q, gradient, lower, upper), np.inf))
        mismatch = float(np.linalg.norm(canonical['weights'][0]-stage['weights'][0], np.inf)
            /max(1., float(np.linalg.norm(stage['weights'][0], np.inf))))
        if (not np.array_equal(gradient, row['canonical_gradient'])
            or absolute != row['canonical_absolute_kkt'] or mismatch != row['canonical_weight_mismatch']
            or absolute/row['initial_gradient_norm'] != row['canonical_normalized_kkt']):
            raise ValueError('corrected replay: canonical weights/KKT')
        if previous_weights is not None:
            previous_q = models[row['start_row']]
            changes.append(dict(model_relative=float(np.linalg.norm(final_q-previous_q, np.inf)
                /max(1., float(np.linalg.norm(previous_q, np.inf)))),
                weights_relative=float(np.linalg.norm(stage['weights'][0]-previous_weights, np.inf)
                /max(1., float(np.linalg.norm(previous_weights, np.inf))))))
        previous_weights = stage['weights'][0]
    if calls > 126 or anchors > 63 or steps != init['iterations']+native_steps+anchors or result['auxiliary_calls'] != calls:
        raise ValueError('corrected replay: actual combined/method caps')
    # A failed proposal phase may retain genuine auxiliary anchors before the
    # next official native stage exists. Replay this tail, not invented stages.
    for attempt in attempts:
        if attempt['outcome'] == 'adopted' and attempt['model_row'] >= len(expected_kinds)-1:
            if attempt['model_row'] != len(expected_kinds)-1 or not failed:
                raise ValueError('corrected replay: unavailable native-stage tail')
            expected_kinds.append(1)
            expected_labels.append(attempt['stage'])
    if (not np.array_equal(result['event_kinds'], np.array(expected_kinds, dtype=np.int64))
        or not np.array_equal(result['event_stages'], np.array(expected_labels, dtype=np.int64))):
        raise ValueError('corrected replay: exact failed/success phase ledger')
    if terminal['stage_changes'] != tuple(changes) or terminal['weight_updates'] != max(0, len(stages)-1):
        raise ValueError('corrected replay: actual transition/adoption ledger')
    if terminal['status'] == 'converged':
        if (len(stages) != 21 or not all(s['inner']['status'] == 'converged' for s in stages)
            or not plain._fixed_point(20, terminal['epsilon_saturated'], tuple(changes))
            or stages[-1]['canonical_weight_mismatch'] > 1e-6
            or not (stages[-1]['canonical_absolute_kkt'] <= 1e-12 or stages[-1]['canonical_normalized_kkt'] <= 1e-5)):
            raise ValueError('corrected replay: original positive scientific assertions')
        if (not np.array_equal(result['event_kinds'], np.array(expected_kinds, dtype=np.int64))
            or not np.array_equal(result['event_stages'], np.array(expected_labels, dtype=np.int64))
            or result['residual_evaluations'] != sum(a['branch'] == 'interior_unique_nonzero_max' for a in attempts)
                +sum(t['merit_margin'] is not None for a in attempts for t in a['trials'])+2*len(stages)):
            raise ValueError('corrected replay: phase/evaluation ledger')
    return result


def _replay_native(solved, problem, lower, upper, deadline, *, physical_initialization=False):
    """Original physical metrics/stopping/certificates, no optimizer invocation."""
    trace = solved['trace']
    models = trace['models_kg_m3']/1000. if physical_initialization else trace['models_q']
    if not len(models):
        if solved['status'] == 'converged':
            raise ValueError('corrected replay: empty native success')
        return
    misfit, reg, beta = problem['misfit'], problem['regularization'], problem['beta_engine']
    initial_gradient = misfit.deriv(models[0])+beta*reg.deriv(models[0])
    norm = max(1., float(np.linalg.norm(initial_gradient, np.inf)))
    certificate = plain.precision._CertifiedDelta(problem, lower, upper, deadline)
    previous_phi = previous_gradient = previous_q = None
    for i, q in enumerate(models):
        pd, pm = float(misfit(q)), float(reg(q))
        phi = float(pd+beta*pm)
        gradient = misfit.deriv(q)+beta*reg.deriv(q)
        absolute = float(np.linalg.norm(plain.l2._kkt_gradient(q, gradient, lower, upper), np.inf))
        plain._close((pd, pm, phi, absolute/norm), tuple(trace[name][i]
            for name in ('phi_d', 'phi_m', 'phi_engine', 'kkt_normalized')), 'original native stage metrics')
        if i:
            count, cg_count = int(trace['line_search_counts'][i-1]), int(trace['cg_counts'][i-1])
            if not 1 <= count <= 20 or not 0 <= cg_count <= 200:
                raise ValueError('corrected replay: original native LS/CG caps')
            proof = certificate.evaluate(previous_q, q, previous_gradient, i-1, count-1,
                                         previous_phi, phi)
            if proof['decision'] != 'certified_accept':
                raise ValueError('corrected replay: physical E Armijo proof')
            plain._close(abs(phi-previous_phi)/max(1., abs(previous_phi)),
                         trace['relative_changes'][i-1], 'original native objective change')
        previous_q, previous_phi, previous_gradient = q, phi, gradient
    if solved['status'] == 'converged':
        if solved['reason'] == 'absolute_stationary':
            if absolute > 1e-12:
                raise ValueError('corrected replay: original absolute native stopping')
        elif solved['reason'] != 'kkt_stable' or (len(models) < 4 or absolute/norm > 1e-5
            or np.any(trace['relative_changes'][-3:] > 1e-6)):
            raise ValueError('corrected replay: original stable native stopping')
