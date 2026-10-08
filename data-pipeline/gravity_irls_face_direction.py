"""Closed native free-face canonical direction, not an enabled IRLS recipe.

Literal original physical owner, source-owned principal Joseph metric and
actual scipy CG; no caller gradient/mask/factor/action/solver or fit acceptance.
Production adoption awaits independent retained-state/trial/replay gates.
"""
import hashlib
import inspect
from fractions import Fraction
from pathlib import Path
from time import monotonic

import numpy as np
from scipy.sparse.linalg import LinearOperator, cg

import gravity_irls_face as face

SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
FACE_SOURCE_SHA256 = '2df98013d7291abe9f8d96a3274f62b4716b3c463cefb9ad9279eeb6f5762399'
CG_SOURCE_SHA256 = face.interior._SOURCES['scipy.cg']
RESEARCH_EPOCH = 'm02-canonical-native-free-face-direction-1'


def _source_check():
    if (hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != SOURCE_SHA256
            or face.SOURCE_SHA256 != FACE_SOURCE_SHA256
            or hashlib.sha256(Path(face.__file__).read_bytes()).hexdigest() != FACE_SOURCE_SHA256
            or hashlib.sha256(Path(inspect.getfile(cg)).read_bytes()).hexdigest() != CG_SOURCE_SHA256):
        raise ValueError('canonical direction: closed loaded/native source drift')


def _run_direction(owner, q, policy, index, initial, budget):
    """Internal source direction only; consumes and disposes its metric.

    The original shared budget counts every actual auxiliary CG; no separate
    deadline or accepted-step reset. No model is adopted by this function.
    Failure returns its genuine partial native CG record, never a rescue.
    """
    import gravity_irls_original as physical
    if type(owner) is not physical.GravityIRLSPartition or type(budget) is not face.interior._Budget:
        raise TypeError('canonical direction: closed physical owner/shared original budget')
    if type(index) is not int or not 0 <= index <= 20 or budget.deadline > owner.deadline:
        raise ValueError('canonical direction: original stage/uninterrupted lower clock')
    # Permanently lower the closed owner's cooperative construction/action
    # clock too. Never restore a wider deadline after a lower caller budget.
    owner.deadline = min(owner.deadline, budget.deadline)
    started = monotonic()
    derivative = None
    record = dict(research_epoch=RESEARCH_EPOCH, source_sha256=SOURCE_SHA256,
        derivative_source_sha256=FACE_SOURCE_SHA256, cg_source_sha256=CG_SOURCE_SHA256,
        stage=index, status='failed', reason=None, cg=[], direction=None,
        native_fit_accepted=False, recurrence_enabled=False, accepted_moves=0,
        disposed=False, seconds=0.)
    def check():
        budget.check(); _source_check()
        if derivative is not None:
            derivative.check()
        else:
            owner.check()
    try:
        check()
        if budget.steps >= 200:
            raise face.interior._Failure('iteration_cap')
        if budget.calls >= 126:
            raise face.interior._Failure('auxiliary_call_cap')
        stages = getattr(budget, '_face_stage_calls', {})
        if stages.get(index, 0) >= 3:
            raise face.interior._Failure('auxiliary_call_cap')
        stages[index] = stages.get(index, 0)+1
        budget._face_stage_calls = stages
        derivative = face._CanonicalFaceLinearization(owner, q, policy, index, initial)
        budget.evaluations += 1
        record.update(q=derivative.q.copy(), native_gradient=2*derivative.root,
            binding=derivative.face['binding'].copy(), free=derivative.face['free'].copy(),
            maxima=derivative.face['maxima'].copy(), branch=derivative.face['branch'],
            free_scale_gap=derivative.face['free_scale_gap'],
            source_state_sha256=derivative._state_sha256,
            stage_sha256=derivative.record['stage_sha256'])
        if not derivative.face['derivative_supported']:
            record.update(status='disabled', reason=derivative.face['branch'])
            return record
        free = derivative.face['free']
        root = derivative.root[free]
        if float(np.linalg.norm(2*root, np.inf)) <= 1e-12:
            record.update(status='stationary', reason='canonical_absolute_stationary')
            return record
        metric = derivative.metric()
        record.update(allocation=derivative.allocation.copy(),
            metric_operand_sha256=metric.operand_sha256, metric_face_sha256=metric.face_sha256)
        def call(rhs, kind):
            budget.begin_call()
            row = dict(kind=kind, rhs=rhs.copy(), solution=None, info=None,
                iterations=0, matvecs=0, metric_actions=0, seconds=0.,
                absolute_residual=None, relative_residual=None, status='aborted')
            record['cg'].append(row)
            call_started = monotonic()
            def action(v):
                check(); row['matvecs'] += 1
                value = derivative.action(v)
                check()
                return value
            def precondition(v):
                check(); row['metric_actions'] += 1
                value = metric.apply(v)
                check()
                return face.interior._finite(value)
            def observe(v):
                row['iterations'] += 1
                row['solution'] = v.copy()
                check()
            try:
                size = len(free)
                solution, info = cg(LinearOperator((size, size), matvec=action, dtype=np.float64),
                    rhs, M=LinearOperator((size, size), matvec=precondition, dtype=np.float64),
                    rtol=1e-6, atol=0., maxiter=200, callback=observe)
                row.update(solution=solution.copy(), info=int(info), status='returned')
                true = float(np.linalg.norm(action(solution)-rhs))
                norm = float(np.linalg.norm(rhs))
                relative = true/norm if norm else true
                row.update(absolute_residual=true, relative_residual=relative)
                if info != 0 or row['iterations'] > 200 or not np.isfinite(relative) or relative > 1e-6:
                    raise face.interior._Failure('auxiliary_cg_cap')
                return solution
            finally:
                row['seconds'] = float(monotonic()-call_started)
        a = call(-root, 'newton_rhs')
        if derivative.face['constant_scale']:
            p = a
            record.update(denominator=None, conditioning_ratio=None)
        else:
            c = call(derivative.u[free], 'rank_one_rhs')
            j = int(np.flatnonzero(free == derivative.face['maximum_index'])[0])
            denominator, ratio = face.interior._denominator(c, j)
            p = face.interior._finite(a-c*a[j]/denominator)
            record.update(denominator=denominator, conditioning_ratio=ratio)
        jp = derivative.action(p, full=True)
        slope = float(np.inner(root, jp))
        direction = np.zeros(len(q)); direction[free] = p
        record.update(direction=direction, merit_slope=slope,
            root_linear_residual=float(np.linalg.norm(jp+root)),
            root_relative_residual=float(np.linalg.norm(jp+root)/np.linalg.norm(root)))
        check()
        if not np.isfinite(slope) or slope >= 0. or not np.any(p):
            raise face.interior._Failure('merit_non_descent')
        record.update(status='direction', reason='source_native_free_direction')
        return record
    except (ValueError, RuntimeError, ArithmeticError) as error:
        record['reason'] = str(error)
        return record
    finally:
        if derivative is not None:
            derivative.close()
        record['disposed'] = True
        record['seconds'] = float(monotonic()-started)


def _native_direction(owner, q, policy, index, initial, budget):
    # The implementation's returned dictionary is finalized by its finally
    # before being copied/frozen. No stale disposed/time values are published.
    return face.interior._freeze(_run_direction(owner, q, policy, index, initial, budget))


def _feasible_scale(owner, q, p, budget):
    """Exact stored-real first contact; no projection or tolerance fudge."""
    owner.check(); budget.check(); _source_check()
    lower, upper = owner.prior['lower_kg_m3']/1000., owner.prior['upper_kg_m3']/1000.
    if (not face.interior.plain.optimizer._array(q, len(lower))
            or not face.interior.plain.optimizer._array(p, len(lower))
            or np.any(q < lower) or np.any(q > upper)):
        raise ValueError('canonical merit: literal original feasible source vectors')
    ratio = Fraction(1)
    for qi, pi, lo, hi in zip(q, p, lower, upper):
        budget.check()
        if pi:
            target = hi if pi > 0. else lo
            candidate = (Fraction(float(target))-Fraction(float(qi)))/Fraction(float(pi))
            ratio = min(ratio, candidate)
    value = float(ratio)
    if Fraction(value) > ratio:
        value = float(np.nextafter(value, 0.))
    owner.check(); budget.check(); _source_check()
    return dict(exact_ratio=str(ratio), alpha0=value, policy='exact_box_contact_floor_binary64')


def _validate_direction(owner, record, policy, initial):
    """Reconstruct a successful direction from original actions, NEVER CG.

    Research replay only. It does not upgrade a failed/archived native fit.
    Failed partial rows remain retained but cannot become proposal authority.
    """
    import gravity_irls_original as physical
    if type(owner) is not physical.GravityIRLSPartition or type(record) is not dict:
        raise TypeError('canonical direction replay: closed original owner/record')
    required = {'research_epoch', 'source_sha256', 'derivative_source_sha256', 'cg_source_sha256',
        'stage', 'status', 'reason', 'cg', 'direction', 'native_fit_accepted', 'recurrence_enabled',
        'accepted_moves', 'disposed', 'seconds', 'q', 'native_gradient', 'binding', 'free', 'maxima',
        'branch', 'free_scale_gap', 'source_state_sha256', 'stage_sha256', 'allocation',
        'metric_operand_sha256', 'metric_face_sha256', 'denominator', 'conditioning_ratio',
        'merit_slope', 'root_linear_residual', 'root_relative_residual'}
    if (set(record) != required or record['status'] != 'direction'
            or record['reason'] != 'source_native_free_direction'
            or record['research_epoch'] != RESEARCH_EPOCH
            or record['source_sha256'] != SOURCE_SHA256
            or record['derivative_source_sha256'] != FACE_SOURCE_SHA256
            or record['cg_source_sha256'] != CG_SOURCE_SHA256
            or record['native_fit_accepted'] is not False or record['recurrence_enabled'] is not False
            or type(record['accepted_moves']) is not int or record['accepted_moves'] != 0
            or record['disposed'] is not True or type(record['seconds']) is not float
            or not 0. <= record['seconds'] <= 120.):
        raise ValueError('canonical direction replay: prospective exact source/terminal/caps')
    _source_check(); owner.check()
    derivative = face._CanonicalFaceLinearization(owner, record['q'], policy, record['stage'], initial)
    try:
        if not derivative.face['derivative_supported']:
            raise ValueError('canonical direction replay: unsupported face before reconstruction')
        for name, value in (('native_gradient', 2*derivative.root),
                ('binding', derivative.face['binding']), ('free', derivative.face['free']),
                ('maxima', derivative.face['maxima'])):
            if not np.array_equal(record[name], value):
                raise ValueError('canonical direction replay: native model/gradient/free-face')
        for name, value in (('branch', derivative.face['branch']),
                ('free_scale_gap', derivative.face['free_scale_gap']),
                ('source_state_sha256', derivative._state_sha256),
                ('stage_sha256', derivative.record['stage_sha256']),
                ('allocation', derivative.allocation)):
            if record[name] != value:
                raise ValueError('canonical direction replay: original source/stage/allocation')
        metric = derivative.metric()
        if (record['metric_operand_sha256'], record['metric_face_sha256']) != (
                metric.operand_sha256, metric.face_sha256):
            raise ValueError('canonical direction replay: source-owned metric operand/face')
        free = derivative.face['free']; root = derivative.root[free]
        calls = record['cg']
        count = 1 if derivative.face['constant_scale'] else 2
        if type(calls) is not tuple or len(calls) != count:
            raise ValueError('canonical direction replay: literal source CG branch count')
        for number, row in enumerate(calls):
            rhs = -root if number == 0 else derivative.u[free]
            if (type(row) is not dict or set(row) != {'kind', 'rhs', 'solution', 'info',
                    'iterations', 'matvecs', 'metric_actions', 'seconds', 'absolute_residual',
                    'relative_residual', 'status'} or row['status'] != 'returned'
                    or row['kind'] != ('newton_rhs', 'rank_one_rhs')[number]
                    or type(row['info']) is not int or row['info'] != 0
                    or any(type(row[k]) is not int or row[k] < 0 for k in ('iterations', 'matvecs', 'metric_actions'))
                    or not 1 <= row['iterations'] <= 200
                    or row['matvecs'] != row['iterations']+1
                    or row['metric_actions'] != row['iterations'] or type(row['seconds']) is not float
                    or not 0. <= row['seconds'] <= record['seconds']
                    or not np.array_equal(row['rhs'], rhs)):
                raise ValueError('canonical direction replay: actual native CG counters/rhs/time')
            true = float(np.linalg.norm(derivative.action(row['solution'])-rhs))
            norm = float(np.linalg.norm(rhs)); relative = true/norm if norm else true
            if (true != row['absolute_residual'] or relative != row['relative_residual']
                    or not np.isfinite(relative) or relative > 1e-6):
                raise ValueError('canonical direction replay: original actual CG true residual')
        p = calls[0]['solution'].copy()
        denominator = ratio = None
        if count == 2:
            c = calls[1]['solution']; j = int(np.flatnonzero(free == derivative.face['maximum_index'])[0])
            denominator, ratio = face.interior._denominator(c, j)
            p -= c*p[j]/denominator
        if (record['denominator'], record['conditioning_ratio']) != (denominator, ratio):
            raise ValueError('canonical direction replay: safeguarded rank-one denominator')
        embedded = np.zeros(len(derivative.q)); embedded[free] = p
        jp = derivative.action(p, full=True)
        slope = float(np.inner(root, jp))
        if (not np.array_equal(record['direction'], embedded) or not np.any(p)
                or slope != record['merit_slope'] or not np.isfinite(slope) or slope >= 0.
                or float(np.linalg.norm(jp+root)) != record['root_linear_residual']
                or float(np.linalg.norm(jp+root)/np.linalg.norm(root)) != record['root_relative_residual']):
            raise ValueError('canonical direction replay: literal source direction/descent/residual')
        derivative.check(); _source_check()
        return record
    finally:
        derivative.close()


def _merit_candidate(owner, record, policy, initial, budget):
    """All original20 strict native merit trials on the SAME literal face.

    Returns a candidate for research, not an adopted model or native-fit PASS.
    The later enabled partition must count its adoption inside original200.
    No projection, face transition, failed-CG rescue or physical E rewrite.
    """
    import gravity_irls_original as physical
    if type(owner) is not physical.GravityIRLSPartition:
        raise TypeError('canonical merit: closed original physical owner')
    if type(budget) is not face.interior._Budget or budget.deadline > owner.deadline:
        raise ValueError('canonical merit: same uninterrupted original budget')
    owner.deadline = min(owner.deadline, budget.deadline)
    budget.check(); owner.check(); _source_check()
    if budget.steps >= 200:
        raise face.interior._Failure('iteration_cap')
    _validate_direction(owner, record, policy, initial)
    q, p = record['q'], record['direction']
    problem = owner.problem
    lower, upper = owner.prior['lower_kg_m3']/1000., owner.prior['upper_kg_m3']/1000.
    current_face = face._classify(q, problem['reference_q'], record['native_gradient'], lower, upper)
    root = record['native_gradient'][current_face['free']]/2.
    merit = float(np.inner(root, root)/2.)
    result = dict(research_epoch=RESEARCH_EPOCH, source_sha256=SOURCE_SHA256,
        stage=record['stage'], trials=[], q=None, status='failed', reason=None,
        native_fit_accepted=False, recurrence_enabled=False, accepted_moves=0,
        feasible_initialization=None)
    try:
        budget.check(); owner.check(); _source_check()
        if budget.steps >= 200:
            raise face.interior._Failure('iteration_cap')
        result['feasible_initialization'] = _feasible_scale(owner, q, p, budget)
        alpha0 = result['feasible_initialization']['alpha0']
        if alpha0 <= 0.:
            raise face.interior._Failure('merit_line_search_failed')
        for number in range(20):
            budget.check(); owner.check(); _source_check()
            alpha = float(alpha0*2.**(-number)); trial = q+alpha*p
            feasible = bool(np.isfinite(trial).all() and np.all(trial >= lower) and np.all(trial <= upper))
            nonzero = bool(np.any(trial != q))
            fixed = bool(np.array_equal(trial[current_face['binding']], q[current_face['binding']]))
            row = dict(trial=number, alpha=alpha, q=trial.copy(), feasible=feasible,
                nonzero=nonzero, binding_fixed=fixed, face_preserved=False,
                native_binding=None, native_gradient=None, stage_sha256=None,
                epsilon=None, disposed=True, merit_margin=None, accepted=False)
            result['trials'].append(row)
            if feasible and nonzero and fixed:
                stage = face.interior._stage(problem, trial, policy, record['stage'], initial)
                obj = face.interior._Objective(stage, record['stage'], lower, upper,
                    owner.allocation['allocation_plan_sha256'])
                row.update(stage_sha256=stage['objective_sha256'], epsilon=stage['epsilon'], disposed=False)
                try:
                    _, gradient = obj.evaluate(trial, True, False)
                    budget.evaluations += 1
                    row['native_gradient'] = gradient.copy()
                    row['native_binding'] = face._native_binding(trial, gradient, lower, upper)
                    same = face._same_face_trial(q, trial, gradient, problem['reference_q'],
                        lower, upper, current_face)
                    row['face_preserved'] = same
                    if same:
                        rt = gradient[current_face['free']]/2.
                        margin = float(np.inner(rt, rt)/2.-merit-1e-4*alpha*record['merit_slope'])
                        face.interior._finite(margin)
                        row.update(merit_margin=margin, accepted=bool(margin < 0.))
                    owner.check(); obj.identity(); _source_check(); budget.check()
                finally:
                    obj.release_state()
                    row['disposed'] = True
                    obj = stage = None
            if row['accepted']:
                result.update(q=trial.copy(), status='candidate', reason='strict_actual_merit_armijo')
                break
        else:
            raise face.interior._Failure('merit_line_search_failed')
    except (ValueError, RuntimeError, ArithmeticError) as error:
        result['reason'] = str(error)
    return face.interior._freeze(result)


def _validate_merit_candidate(owner, direction, result, policy, initial):
    """Reconstruct every stored trial/sign/margin; no CG or model adoption."""
    _validate_direction(owner, direction, policy, initial)
    required = {'research_epoch', 'source_sha256', 'stage', 'trials', 'q', 'status', 'reason',
        'native_fit_accepted', 'recurrence_enabled', 'accepted_moves', 'feasible_initialization'}
    if (type(result) is not dict or set(result) != required
            or result['research_epoch'] != RESEARCH_EPOCH or result['source_sha256'] != SOURCE_SHA256
            or result['stage'] != direction['stage'] or result['native_fit_accepted'] is not False
            or result['recurrence_enabled'] is not False or type(result['accepted_moves']) is not int
            or result['accepted_moves'] != 0 or type(result['trials']) is not tuple
            or not 1 <= len(result['trials']) <= 20 or result['status'] != 'candidate'
            or result['reason'] != 'strict_actual_merit_armijo'):
        raise ValueError('canonical merit replay: exact candidate-only source/caps/record')
    budget = face.interior._Budget(owner.deadline)
    q, p = direction['q'], direction['direction']
    initialization = _feasible_scale(owner, q, p, budget)
    if result['feasible_initialization'] != initialization or initialization['alpha0'] <= 0.:
        raise ValueError('canonical merit replay: original exact feasible initialization')
    problem = owner.problem
    lower, upper = owner.prior['lower_kg_m3']/1000., owner.prior['upper_kg_m3']/1000.
    native_face = face._classify(q, problem['reference_q'], direction['native_gradient'], lower, upper)
    root = direction['native_gradient'][native_face['free']]/2.
    merit = float(np.inner(root, root)/2.)
    for number, row in enumerate(result['trials']):
        budget.check(); owner.check(); _source_check()
        if type(row) is not dict or set(row) != {'trial', 'alpha', 'q', 'feasible', 'nonzero',
                'binding_fixed', 'face_preserved', 'native_binding', 'native_gradient',
                'stage_sha256', 'epsilon', 'disposed', 'merit_margin', 'accepted'}:
            raise ValueError('canonical merit replay: all actual trial fields')
        alpha = float(initialization['alpha0']*2.**(-number)); trial = q+alpha*p
        feasible = bool(np.isfinite(trial).all() and np.all(trial >= lower) and np.all(trial <= upper))
        nonzero = bool(np.any(trial != q))
        fixed = bool(np.array_equal(trial[native_face['binding']], q[native_face['binding']]))
        if (row['trial'] != number or row['alpha'] != alpha or not np.array_equal(row['q'], trial)
                or row['feasible'] is not feasible or row['nonzero'] is not nonzero
                or row['binding_fixed'] is not fixed):
            raise ValueError('canonical merit replay: actual chord/feasibility/fixed binding')
        preserved = False; margin = binding = gradient = stage_sha256 = epsilon = None
        if feasible and nonzero and fixed:
            stage = face.interior._stage(problem, trial, policy, direction['stage'], initial)
            obj = face.interior._Objective(stage, direction['stage'], lower, upper,
                owner.allocation['allocation_plan_sha256'])
            stage_sha256, epsilon = stage['objective_sha256'], stage['epsilon']
            try:
                _, gradient = obj.evaluate(trial, True, False)
                binding = face._native_binding(trial, gradient, lower, upper)
                preserved = face._same_face_trial(q, trial, gradient, problem['reference_q'],
                    lower, upper, native_face)
                if preserved:
                    rt = gradient[native_face['free']]/2.
                    margin = float(np.inner(rt, rt)/2.-merit-1e-4*alpha*direction['merit_slope'])
                owner.check(); obj.identity(); _source_check()
            finally:
                obj.release_state()
                obj = stage = None
        if (row['face_preserved'] is not preserved or row['merit_margin'] != margin
                or not np.array_equal(row['native_binding'], binding)
                or not np.array_equal(row['native_gradient'], gradient)
                or row['stage_sha256'] != stage_sha256 or row['epsilon'] != epsilon
                or row['disposed'] is not True
                or row['accepted'] is not bool(margin is not None and margin < 0.)
                or row['accepted'] is not (number == len(result['trials'])-1)):
            raise ValueError('canonical merit replay: native sign/branch/strict margin/all trials')
    if not np.array_equal(result['q'], result['trials'][-1]['q']):
        raise ValueError('canonical merit replay: actual terminal candidate')
    budget.check(); owner.check(); _source_check()
    return result
