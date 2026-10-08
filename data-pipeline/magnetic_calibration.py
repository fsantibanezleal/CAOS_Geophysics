"""Supplied-survey nested L2/IRLS fitting and one-time sealed evaluation.

Actual engines and public reviewed optimizer only. Failure/cap states remain
failures. This local driver does not admit an online worker or field geology.
"""

import hashlib
from time import monotonic, process_time

import numpy as np
from scipy.linalg import solve_triangular

from magnetic_inverse import build_operator, owned
from magnetic_likelihood import SealedLikelihood
from magnetic_optimizer_adapter import MagneticObjective, MagneticRegularizer, EPSILONS, solve_linear
from magnetic_survey_json import InputError, digest, fail


def descriptor(value):
    if type(value) is not np.ndarray or value.dtype not in (np.dtype('float64'), np.dtype('int64'), np.dtype('bool')):
        raise TypeError('result: native bounded numeric array required')
    return dict(dtype=str(value.dtype), shape=list(value.shape), data=value.ravel().tolist(),
                sha256=hashlib.sha256(value.astype(value.dtype.newbyteorder('<'), copy=False).tobytes()).hexdigest())


def _hash_model(q):
    return hashlib.sha256((.01*q).astype('<f8', copy=False).tobytes()).hexdigest()


def projected_gradient(q, gradient, lower, upper):
    tolerance = 32*np.finfo(float).eps*np.maximum.reduce([np.ones_like(q), abs(q), abs(lower), abs(upper)])
    result = gradient.copy()
    result[(q <= lower+tolerance)&(gradient > 0.)] = 0.
    result[(q >= upper-tolerance)&(gradient < 0.)] = 0.
    return float(np.linalg.norm(result, np.inf))


def nonlinear_projected_gradient(q, gradient, lower, upper):
    # Match the reviewed nonlinear seam's EXACT bounds, never the linear
    # near-bound numerical tolerance. Independent M04 threshold stays1e-7.
    result = gradient.copy()
    result[q == lower] = np.minimum(gradient[q == lower], 0.)
    result[q == upper] = np.maximum(gradient[q == upper], 0.)
    return float(np.linalg.norm(result, np.inf))


def mesh_from_metadata(meta):
    spec = meta['geometry']['mesh']
    result = {k: np.array(spec[source]['data'], dtype=np.float64) for k, source in (
        ('origin_m', 'origin_m'), ('hx_m', 'widths_x_m'), ('hy_m', 'widths_y_m'), ('hz_m', 'widths_z_m'))}
    result['active'] = np.array(spec['active']['data'], dtype=bool)
    return result


def metrics(prediction, observed, noise):
    try:
        with np.errstate(over='raise', divide='raise', invalid='raise'):
            residual = observed-prediction
            if noise['kind'] == 'full_covariance':
                wr = solve_triangular(np.linalg.cholesky(noise['values']), residual.ravel(), lower=True)
            else:
                wr = (residual/noise['values']).ravel()
            pd = float(wr@wr)
            rms = float(np.sqrt(np.mean(residual*residual)))
            normalized = float(np.sqrt(pd/observed.size))
    except (FloatingPointError, np.linalg.LinAlgError):
        fail('numerical', '$/metrics', 'Native likelihood metric is unrepresentable; no SD floor or score fallback')
    if not np.isfinite([pd, rms, normalized]).all():
        fail('numerical', '$/metrics', 'Native likelihood metric is unrepresentable; no SD floor or score fallback')
    return dict(n_rows=len(observed), n_components=observed.size, phi_d=pd,
                rms_nT=rms, normalized_rms=normalized)


def recorded_objective_terms(obj, trace, inner, *, nonlinear):
    """Retain native F and the SAME-state unweighted physical regularizer.

    The nonlinear public contract records the weighted penalty subtotal with
    beta_engine=1. M04 history instead explicitly records beta and bare phi_m.
    Re-evaluate the literal vendor operand, not weighted/beta (which can change
    a float64 bit). Never repair a mismatching engine trace or relax equality.
    """
    pd = float(trace['phi_d'][inner])
    pm = float(trace['phi_m'][inner])
    value = float(trace['phi_engine'][inner])
    if nonlinear:
        pm = float(obj.regularizer.vendor(trace['models_q'][inner]))
        if float(trace['phi_m'][inner]) != obj.beta*pm:
            fail('numerical', '$/history', 'Native weighted regularizer operand mismatch')
    if not np.isfinite([pd, pm, value]).all() or value != pd+obj.beta*pm:
        fail('numerical', '$/history', 'Actual objective terms mismatch')
    return dict(phi_d=pd, phi_regularizer=pm, objective=value)


def fit_partition(operator, mesh, prior, observed, noise, beta, penalty, *, binding,
                  deadline, admitted_bytes, allocation_sha256, source_inventory_sha256,
                  source_components=None, optimizer_audit=None):
    """Complete fixed-beta L2 and optionally eight-stage true-p1 continuation."""
    import physical_optimizer as core
    nonlinear = operator.quantity == 'exact_total_anomaly_nT'
    if nonlinear:
        import physical_nonlinear_optimizer as core
        from magnetic_nonlinear_adapter import MagneticNonlinearObjective, solve_nonlinear
    conditioned = type(binding).__module__ == 'physical_conditioned_optimizer'
    if conditioned:
        import physical_conditioned_optimizer as conditioned_core
        from magnetic_conditioned_adapter import MagneticConditionedObjective, solve_conditioned
    kkt_gradient = nonlinear_projected_gradient if nonlinear else projected_gradient
    reference = np.array(prior['reference_si']['data'], dtype=np.float64)/.01
    lower = np.array(prior['lower_si']['data'], dtype=np.float64)/.01
    upper = np.array(prior['upper_si']['data'], dtype=np.float64)/.01
    start = np.array(prior['start_si']['data'], dtype=np.float64)/.01
    lengths = np.array(prior['lengths_m']['data'], dtype=np.float64)
    deadline = min(deadline, monotonic()+120.)
    records, steps = [], 0

    def objective(q, sparse=False, epsilon=0., stage=0):
        reg = MagneticRegularizer(mesh, reference, lengths, 'sparse_smallness' if sparse else 'l2', epsilon, q)
        obj = MagneticObjective(operator, reg, observed, noise, lower, upper, float(beta),
                                source_inventory_sha256, allocation_sha256, stage)
        physical = MagneticNonlinearObjective(obj, q) if nonlinear else obj
        return MagneticConditionedObjective(physical, source_components) if conditioned else physical

    def append_trace(obj, solved, phase, outer, epsilon):
        for inner, q in enumerate(solved['trace']['models_q']):
            g = obj.evaluate(q, True, False)[1]
            records.append(dict(phase=phase, outer_iteration=outer, inner_iteration=inner,
                beta=float(beta), epsilon_q=epsilon,
                **recorded_objective_terms(obj, solved['trace'], inner, nonlinear=nonlinear),
                kkt_inf=kkt_gradient(q, g, lower, upper), model_sha256=_hash_model(q),
                status='converged' if inner == len(solved['trace']['models_q'])-1 and solved['status'] == 'converged' else
                       'failed' if inner == len(solved['trace']['models_q'])-1 and solved['status'] != 'converged' else 'iterating'))
            if len(records) > 4096:
                fail('resource', '$/history', 'Full untruncated history capacity exceeded')

    def solve(obj, q):
        nonlocal steps
        budget_type = conditioned_core.ConditionedBudget if conditioned else core.NonlinearBudget if nonlinear else core.OptimizerBudget
        budget = budget_type(deadline, 200-steps, 805306368, admitted_bytes, allocation_sha256)
        solver = solve_conditioned if conditioned else solve_nonlinear if nonlinear else solve_linear
        result = solver(obj, lower, upper, q, budget=budget, binding=binding)
        if conditioned and optimizer_audit is not None:
            optimizer_audit(result)
        steps += result['iterations']
        return result

    l2 = objective(start)
    solved = solve(l2, start)
    append_trace(l2, solved, 'l2', 0, 0.)
    if solved['status'] != 'converged':
        return dict(status='failed', reason=solved['reason'], q=solved['q'], kkt_inf=None, history=records, objective=l2)
    q = owned(solved['q'])
    initial_norm = max(1., float(np.linalg.norm(l2.evaluate(start, True, False)[1], np.inf)))
    kkt = kkt_gradient(q, l2.evaluate(q, True, False)[1], lower, upper)
    if kkt > 1e-7*initial_norm:
        return dict(status='failed', reason='independent_kkt', q=q, kkt_inf=kkt, history=records, objective=l2)
    if penalty == 'l2':
        return dict(status='converged', reason=None, q=q, kkt_inf=kkt, history=records, objective=l2)
    if penalty != 'sparse_smallness':
        fail('enum', '$/penalty', 'Frozen penalty required')
    final = l2
    for stage, epsilon in enumerate(EPSILONS):
        refreshed = objective(q, True, epsilon, stage)
        true_initial = refreshed.regularizer.true_value_gradient(q)[1]
        _, data_g = l2.evaluate(q, True, False)
        data_g = data_g-beta*l2.regularizer.vendor.deriv(q)
        initial_norm = max(1., float(np.linalg.norm(data_g+beta*true_initial, np.inf)))
        for outer in range(20):
            if monotonic() > deadline:
                return dict(status='failed', reason='wall_cap', q=q, kkt_inf=None, history=records, objective=refreshed)
            previous = q
            refreshed = objective(previous, True, epsilon, stage)
            before = refreshed.components(previous)['phi_d']+beta*refreshed.regularizer.true_value_gradient(previous)[0]
            solved = solve(refreshed, previous)
            append_trace(refreshed, solved, 'irls_surrogate', outer, epsilon)
            if solved['status'] != 'converged':
                return dict(status='failed', reason=solved['reason'], q=solved['q'], kkt_inf=None, history=records, objective=refreshed)
            q = owned(solved['q'])
            true_pm, true_g = refreshed.regularizer.true_value_gradient(q)
            pd = refreshed.components(q)['phi_d']
            after = pd+beta*true_pm
            if after-before > 64*np.finfo(float).eps*max(1., abs(before), abs(after)):
                return dict(status='failed', reason='irls_true_increase', q=q, kkt_inf=None, history=records, objective=refreshed)
            # Derive data gradient from this SAME actual likelihood, not an L2
            # cached surrogate or stale weight gradient.
            gradient = refreshed.evaluate(q, True, False)[1]-beta*refreshed.regularizer.vendor.deriv(q)+beta*true_g
            kkt = kkt_gradient(q, gradient, lower, upper)
            change = float(np.linalg.norm(q-previous, np.inf)/max(1., float(np.linalg.norm(q, np.inf))))
            records.append(dict(phase='irls_fixed', outer_iteration=outer, inner_iteration=solved['iterations'],
                beta=float(beta), epsilon_q=epsilon, phi_d=pd, phi_regularizer=true_pm, objective=after,
                kkt_inf=kkt, model_sha256=_hash_model(q),
                status='converged' if change <= 1e-5 and kkt <= 1e-7*initial_norm else 'iterating'))
            if len(records) > 4096:
                fail('resource', '$/history', 'Full untruncated history capacity exceeded')
            if change <= 1e-5 and kkt <= 1e-7*initial_norm:
                final = objective(q, True, epsilon, stage)
                break
        else:
            return dict(status='failed', reason='irls_outer_cap', q=q, kkt_inf=kkt, history=records, objective=refreshed)
    return dict(status='converged', reason=None, q=q, kkt_inf=kkt, history=records, objective=final)


def select_candidate(candidates):
    complete = [c for c in candidates if c['status'] == 'complete']
    if not complete:
        fail('convergence', '$/candidates', 'No complete candidate; no partial-average fallback')
    best = complete[0]
    for other in complete[1:]:
        tolerance = 64*np.finfo(float).eps*max(1., abs(best['score']), abs(other['score']))
        if other['score'] < best['score']-tolerance or (abs(other['score']-best['score']) <= tolerance and
                (other['penalty'] != 'l2', -other['beta'], other['id']) < (best['penalty'] != 'l2', -best['beta'], best['id'])):
            best = other
    return best


def calibrate(raw, *, binding, source_inventory_sha256, deadline, freeze_receipt=None, optimizer_audit=None):
    """Complete result or explicit retained numerical failure, never fallback."""
    state = {}
    try:
        return _calibrate(raw, binding=binding, source_inventory_sha256=source_inventory_sha256,
                          deadline=deadline, freeze_receipt=freeze_receipt, state=state, optimizer_audit=optimizer_audit)
    except InputError as error:
        if not state or error.code not in ('resource', 'numerical', 'convergence'):
            raise
        active_fold = state.get('active_fold')
        if active_fold is not None and active_fold >= 0:
            # A started but interrupted fit is not an unexecuted fold. Retain
            # its actual trace and failure reason; validation metrics unavailable.
            candidate = next(c for c in state['candidates'] if c['id'] == state['active_candidate'])
            metric = candidate['folds'][active_fold]
            if metric['reason'] == 'not_run':
                metric['reason'] = state.get('active_reason') or error.code
        return dict(schema='magnetic-survey-result-1', status='failed', identity=state['identity'],
            inventory=state['plan']['inventory'], partition=state['plan']['partition'], candidates=state['candidates'],
            selected=None, model=None, prediction=None, metrics=None, history=state['history'],
            diagnostics=dict(reason=error.code+': '+error.message, resolution_kind='none', resolution_arrays=None,
                             resources=None), claims=state['plan']['claims'])


def _calibrate(raw, *, binding, source_inventory_sha256, deadline, freeze_receipt, state, optimizer_audit):
    """Use actual supplied bytes; development fits cannot read outer values."""
    import physical_optimizer as core
    from magnetic_optimizer_adapter import certificate_source
    from pathlib import Path
    clock, cpu = monotonic(), process_time()
    reader = SealedLikelihood(raw)
    meta, plan = reader.metadata, reader.plan
    if not plan['eligibility']['local_processing']:
        fail('lineage', '$/processing', 'Local processing rights/lineage unresolved')
    requested = meta['policy']['optimizer_binding']
    nonlinear = meta['processing']['quantity'] == 'exact_total_anomaly_nT'
    binding_type = core.OptimizerBinding
    if nonlinear:
        import physical_nonlinear_optimizer as core
        binding_type = core.NonlinearBinding
    conditioned = type(binding).__module__ == 'physical_conditioned_optimizer'
    if conditioned:
        import physical_conditioned_optimizer as core
        import physical_owned_spd as spd
        binding_type = core.ConditionedBinding
    epoch = (core.NONLINEAR_EPOCH if nonlinear else core.LINEAR_EPOCH) if conditioned else core.RUNTIME_EPOCH
    if (type(binding) is not binding_type or requested != dict(accepted_source=binding.optimizer_source_sha256,
            accepted_export=binding.accepted_export, epoch=binding.runtime_epoch)
            or binding.optimizer_source_sha256 != core.SOURCE_SHA256 or binding.runtime_epoch != epoch
            or binding.policy != core.POLICY or binding.source_inventory_sha256 != source_inventory_sha256
            or (binding.vendor_source_sha256 != core.VENDOR_SOURCE_SHA256 if nonlinear and not conditioned else
                binding.certificate_source_sha256 != hashlib.sha256(Path(certificate_source()).read_bytes()).hexdigest())
            or (conditioned and (binding.metric_source_sha256 != spd.SOURCE_SHA256
                or binding.numeric_kernel_source_sha256 != spd.KERNEL_SHA256
                or binding.vendor_source_sha256 != core.VENDOR_SOURCE_SHA256
                or binding.accepted_export != 'physical_conditioned_optimizer.solve_bounded_'+('nonlinear' if nonlinear else 'linear')))):
        fail('dependency', '$/policy/optimizer_binding', 'Reviewed loaded binding required before kernel construction')
    if meta['policy']['resource_profile'] != 'local_bounded':
        fail('dependency', '$/policy/resource_profile', 'Online source/native admission is separate and closed')
    if type(deadline) is not float or not np.isfinite(deadline) or deadline > clock+7200.:
        fail('resource', '$/deadline', 'Explicit finite bounded whole-calibration deadline required')
    reader.validate_noise()
    mesh = mesh_from_metadata(meta)
    allocation_plan = plan['preflight']
    admitted_bytes = plan['preflight']['conservative_bytes']
    source_components = 3*plan['preflight']['rows']
    if conditioned:
        from magnetic_conditioned_adapter import allocation as phase_allocation
        fit_sizes = [len(f['fit_rows']['data']) for f in plan['partition']['folds']]+[len(plan['final_refit_rows']['data'])]
        try:
            phases = [phase_allocation(source_components, n*plan['preflight']['components'],
                plan['preflight']['active_cells'], meta['noise']['kind'] == 'full_covariance', admitted_bytes) for n in fit_sizes]
        except ValueError as error:
            fail('resource', '$/preflight', str(error))
        allocation_plan = dict(original_preflight=plan['preflight'], fit_refit_metric_phases=phases)
        admitted_bytes = max(p['admitted_bytes'] for p in phases)
    allocation = digest(allocation_plan)
    operators = {}
    history, candidates = [], []
    identity = dict(plan['identity'], engine_epoch=epoch, optimizer_source=binding.optimizer_source_sha256)
    for index, beta in enumerate(meta['policy']['betas']):
        for penalty in meta['policy']['penalties']:
            folds = [dict(fold=fold, status='failed', reason='not_run',
                n_rows=len(partition['validation_rows']['data']),
                n_components=len(partition['validation_rows']['data'])*meta['observations']['values']['shape'][1],
                phi_d=None, rms_nT=None, normalized_rms=None, kkt_inf=None, model_sha256=None)
                for fold, partition in enumerate(plan['partition']['folds'])]
            candidates.append(dict(id=f'b{index:02d}-'+('l2' if penalty == 'l2' else 'sparse'), beta=beta,
                                   penalty=penalty, folds=folds, status='failed', score=None))
    state.update(identity=identity, plan=plan, candidates=candidates, history=history)

    def check_time():
        if monotonic() > deadline or process_time()-cpu > 3600.:
            fail('resource', '$/calibration', 'Whole-calibration wall/CPU cap')

    def op(rows):
        check_time()
        if rows not in operators:
            operators[rows] = build_operator(raw, rows, deadline=deadline)
        return operators[rows]

    def fit(rows, role, fold, beta, penalty, cid):
        state.update(active_candidate=cid, active_fold=-1 if fold is None else fold, active_reason=None)
        observed, noise = reader.read(rows, role=role, fold=fold)
        result = fit_partition(op(rows), mesh, meta['prior'], observed, noise, beta, penalty, binding=binding,
            deadline=deadline, admitted_bytes=admitted_bytes, allocation_sha256=allocation,
            source_inventory_sha256=source_inventory_sha256, source_components=source_components,
            optimizer_audit=(lambda solved: optimizer_audit(cid, fold, solved)) if optimizer_audit is not None else None)
        state['active_reason'] = result['reason']
        for record in result['history']:
            if len(history) >= 4096:
                fail('resource', '$/history', 'Whole result history cap; no truncation')
            history.append(dict(candidate=cid, fold=-1 if fold is None else fold, **record))
        check_time()
        return result

    for index, beta in enumerate(meta['policy']['betas']):
        for penalty in meta['policy']['penalties']:
            cid = f'b{index:02d}-'+('l2' if penalty == 'l2' else 'sparse')
            candidate = candidates[2*index+(penalty != 'l2')]
            folds = candidate['folds']
            for fold, partition in enumerate(plan['partition']['folds']):
                rows = tuple(partition['fit_rows']['data'])
                result = fit(rows, 'fit', fold, beta, penalty, cid)
                validation = tuple(partition['validation_rows']['data'])
                if result['status'] == 'converged':
                    observed, noise = reader.read(validation, role='validation', fold=fold)
                    metric = metrics(op(validation).evaluate(result['q'])['prediction_nT'], observed, noise)
                    folds[fold] = dict(fold=fold, status='converged', reason=None, **metric,
                                      kkt_inf=result['kkt_inf'], model_sha256=_hash_model(result['q']))
                else:
                    folds[fold] = dict(fold=fold, status='failed', reason=result['reason'], n_rows=len(validation),
                        n_components=len(validation)*meta['observations']['values']['shape'][1],
                        phi_d=None, rms_nT=None, normalized_rms=None, kkt_inf=None, model_sha256=None)
            complete = all(f['status'] == 'converged' for f in folds)
            score = sum(f['phi_d'] for f in folds)/sum(f['n_components'] for f in folds) if complete else None
            candidate.update(status='complete' if complete else 'failed', score=score)
    selected = select_candidate(candidates)
    rows = tuple(plan['final_refit_rows']['data'])
    refit = fit(rows, 'refit', None, selected['beta'], selected['penalty'], selected['id'])
    if refit['status'] != 'converged':
        fail('convergence', '$/refit', 'Selected candidate refit failed: '+refit['reason'])
    baseline_id = 'b'+selected['id'][1:3]+'-l2'
    if selected['penalty'] != 'l2':
        baseline = fit(rows, 'refit', None, selected['beta'], 'l2', baseline_id)
        if baseline['status'] != 'converged':
            fail('convergence', '$/refit', 'Selected-beta L2 baseline failed: '+baseline['reason'])
    chi = owned(.01*refit['q'])
    model_hash = reader.freeze(selected['id'], chi, receipt=freeze_receipt)
    # No subsequent fit callback occurs after this immutable model identity.
    development_observed, development_noise = reader.read(rows, role='development')
    development = metrics(op(rows).evaluate(refit['q'])['prediction_nT'], development_observed, development_noise)
    outer_rows = tuple(plan['partition']['outer_rows']['data'])
    outer_observed, outer_noise = reader.read(outer_rows, role='outer')
    outer = metrics(op(outer_rows).evaluate(refit['q'])['prediction_nT'], outer_observed, outer_noise)
    usable = tuple(i for i, flag in enumerate(meta['geometry']['usable']['data']) if flag)
    prediction = op(usable).evaluate(refit['q'])['prediction_nT']
    # Export residuals for ALL original usable rows from already authorized
    # partitions; rows removed by final buffering remain valid display rows.
    from magnetic_likelihood import _selected_tokens
    c = prediction.shape[1]
    observed = np.array(_selected_tokens(reader._text, reader._observed,
        [i*c+j for i in usable for j in range(c)]), dtype=np.float64).reshape(len(usable), c)
    from magnetic_diagnostics import resolution
    diagnostics = resolution(refit['objective'], refit['q'], deadline=deadline)
    return dict(schema='magnetic-survey-result-1', status='complete', identity=identity,
        inventory=plan['inventory'], partition=plan['partition'], candidates=candidates, selected=selected['id'],
        model=dict(chi_si=descriptor(chi), active_indices=descriptor(np.flatnonzero(mesh['active']).astype(np.int64)),
                   mesh_sha256=digest(meta['geometry']['mesh']), sha256=model_hash),
        prediction=dict(quantity=meta['processing']['quantity'], components=['E', 'N', 'U'] if c == 3 else ['scalar'],
            rows=descriptor(np.array(usable, dtype=np.int64)), values_nT=descriptor(owned(prediction)),
            residual_nT=descriptor(owned(observed-prediction))),
        metrics=dict(development=development, outer=outer, l2_baseline=baseline_id,
            sparse_comparison=selected['id'] if selected['penalty'] == 'sparse_smallness' else None),
        history=history, diagnostics=dict(reason=None, resolution_kind='local_fixed_objective', resolution_arrays=diagnostics,
                                        resources=None), claims=plan['claims'])
