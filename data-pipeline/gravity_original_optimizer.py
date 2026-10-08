"""Closed original gravity L2 bridge, with native reduced-face CG and accuracy.

Actual SimPEG construction and original noise/reference/beta/background only.
No uploaded objective, private CG, oracle, mask, SPD/action or terminal hook.
This trusted numerical ABI does not confer source, host or online authority.
"""
from dataclasses import asdict
import hashlib
import inspect
from pathlib import Path
from time import monotonic

import numpy as np
from scipy.sparse.linalg import LinearOperator

import gravity_l2 as physics
import physical_original_quadratic as source
import physical_original_terminal as accuracy
import physical_reduced_optimizer as reduced
import physical_owned_spd as owned


SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
LINEAR_EPOCH = 'physical-gncg-gravity-original-reduced-joseph-candidate-7'
POLICY = 'closed-gravity-original-reduced-joseph-free-face-accuracy-1'
ConditionedBudget = reduced.ConditionedBudget


def allocation_plan(source_count, fit_count, parameters, covariance):
    """Literal worst simultaneous phases, before native/source construction.

    No caller allowance. Operand8MiB is the source validator's HARD backing
    ceiling, not an unproved replacement for its endpoint/factor dictionary.
    Original physical native workspace closure remains independently required.
    """
    a, n, m = parameters, source_count, fit_count
    kernel = owned.kernel.allocation(n, m, a, covariance)
    arithmetic = dict(operand_and_sparse_copy_bytes=2*source.RESERVE_BYTES,
        endpoint_bytes=source.ENDPOINT_PAIR_BYTES*(14*a+6*n),
        native_row_scratch_bytes=128*(3*a+n), metadata_bytes=32768)
    retained = dict(native_states_bytes=201*(8*a+128),
        reduced_phase_audits_bytes=reduced.PHASE_LIMIT*(reduced.PHASE_METADATA_BYTES+40*a),
        native_line_search_bytes=4000*2048, original_chord_certificates_bytes=4000*2048,
        terminal_audits_bytes=201*(32768+1024*a))
    terminal = dict(free_endpoint_bytes=source.ENDPOINT_PAIR_BYTES*12*a,
        factor_and_transpose_bytes=16*m*a+16*7*a+64*a+4*(a+1),
        native_workspace_bytes=source.RESERVE_BYTES, metadata_bytes=32768)
    maximum = kernel['maximum']+sum(arithmetic.values())+sum(retained.values())+sum(terminal.values())
    if maximum > 2*1024**3:
        raise ValueError('gravity original: complete simultaneous dictionary exceeds original2GiB')
    result = dict(original_native=kernel, source_arithmetic=arithmetic,
        retained_audits=retained, terminal=terminal, original_limit_bytes=2*1024**3,
        admitted_bytes=maximum, source_components=n, fit_components=m,
        parameters=a, covariance=covariance, runtime_epoch=LINEAR_EPOCH,
        CG=200, accepted=200, states=201, LS=20, seconds=120.)
    result['allocation_plan_sha256'] = physics.survey._digest(result)
    return result


def source_inventory():
    modules = (physics, physics.forward, source, accuracy, reduced, reduced.core,
        owned, owned.kernel, owned.intervals, reduced.core.linear)
    result = {Path(m.__file__).name: hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()
        for m in modules}
    result[Path(__file__).name] = SOURCE_SHA256
    for cls in (physics.regularization.WeightedLeastSquares,
        physics.data_misfit.L2DataMisfit, physics.forward.gravity.simulation.Simulation3DIntegral,
        physics.optimization.ProjectedGNCG):
        path = Path(inspect.getfile(cls))
        result[cls.__name__] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


class _Objective:
    """Owned construction only; original native evaluations are not replaced."""
    def __init__(self, problem, prior, noise, positions, inventory, allocation):
        self.problem, self.allocation = problem, allocation
        self.lower = prior['lower_kg_m3']/1000.
        self.upper = prior['upper_kg_m3']/1000.
        self.reference = problem['reference_q']
        self.start = prior['start_kg_m3']/1000.
        self.diagonal = None
        self.source_components = problem['metric_profile'][0]
        self.covariance = noise['kind'] == 'full_covariance'
        if self.covariance:
            values = np.ascontiguousarray(noise['values'][np.ix_(positions, positions)])
            self.noise = source.OriginalWhitening('stored_symmetric_precision_root',
                problem['misfit'].W.toarray(), values)
        else:
            self.noise = source.OriginalWhitening('diagonal_sd',
                np.ascontiguousarray(noise['values'][positions]))
        reg = problem['regularization']
        terms, empty = [], []
        for index, (alpha, child) in enumerate(zip(reg.multipliers, reg.objfcts)):
            if alpha == 0.:
                continue
            derivative = child.f_m_deriv(self.reference).tocsr()
            weights = child.W.tocsr()
            if derivative.shape[0] == 0:
                # Ordinary L2 genuinely has an empty orientation on some
                # active meshes. Its native 0-row quadratic is exactly zero,
                # not a Sparse/IRLS empty-face exemption or dropped coupling.
                if weights.shape != (0, 0) or index == 0:
                    raise ValueError('gravity original: exact native zero-row L2 term')
                empty.append((index, float(alpha), derivative.shape))
                continue
            terms.append(owned.QuadraticTerm(float(alpha), weights, derivative))
        self.terms, self.zero_row_terms = tuple(terms), tuple(empty)
        self.identity_value = dict(mode='fixed_linear_quadratic', runtime_epoch=LINEAR_EPOCH,
            objective_sha256=owned.digest((problem['simulation'].G,
                problem['misfit'].W, problem['misfit'].data.dobs, self.reference,
                self.lower, self.upper, self.start, problem['background'],
                float(problem['beta_engine']), tuple((t.alpha, t.weights, t.derivative) for t in self.terms),
                self.zero_row_terms)),
            source_inventory_sha256=physics.survey._digest(inventory), q_unit='g/cc',
            physical_unit='kg/m3', physical_scale=1000., parameter_count=len(self.lower),
            observation_rows=len(problem['rows']), observation_components=1,
            beta_engine=float(problem['beta_engine']), stage_index=0,
            allocation_plan_sha256=allocation['allocation_plan_sha256'])
        self.source_digest = accuracy._source_digest(self.quadratic_operands(self.start))

    def identity(self):
        return self.identity_value.copy()

    def components(self, q):
        p = self.problem
        pd, pm = float(p['misfit'](q)), float(p['regularization'](q))
        return dict(phi_d=pd, phi_m=pm, phi_engine=float(pd+p['beta_engine']*pm))

    def evaluate(self, q, return_g=False, return_H=False):
        p = self.problem
        values = [self.components(q)['phi_engine']]
        if return_g:
            values.append(p['misfit'].deriv(q)+p['beta_engine']*p['regularization'].deriv(q))
        if return_H:
            values.append(LinearOperator((len(q), len(q)), dtype=np.float64,
                matvec=lambda v: p['misfit'].deriv2(q, v)+p['beta_engine']*p['regularization'].deriv2(q, v)))
        return tuple(values) if return_g or return_H else values[0]

    def binding_diagonal(self, q):
        if self.diagonal is None:
            j = self.problem['misfit'].W@self.problem['simulation'].G
            self.diagonal = 2*np.sum(j*j, axis=0)+self.problem['beta_engine']*self.problem['regularization'].deriv2(q).diagonal()
        return self.diagonal.copy()

    def metric_operands(self, q):
        p = self.problem
        return owned.MetricOperands(owned.binding_for(self.identity(), q), self.source_components,
            len(p['rows']), len(q), self.covariance,
            (p['beta_engine']*p['regularization'].deriv2(q)).tocsr().sorted_indices(),
            np.ascontiguousarray(p['misfit'].W@p['simulation'].G))

    def quadratic_operands(self, q):
        p = self.problem
        value = source.OriginalQuadraticOperands(owned.binding_for(self.identity(), q),
            self.source_components, p['simulation'].G, None, self.noise,
            p['misfit'].data.dobs, self.reference, self.lower, self.upper,
            1., float(p['beta_engine']), self.terms, p['simulation'].G, None)
        if hasattr(self, 'source_digest') and accuracy._source_digest(value) != self.source_digest:
            raise ValueError('gravity original: frozen source operand drift')
        return value

    def certify(self, q, qt, gradient, phi, phit, iteration, trial, deadline):
        return source.certify_chord(self.quadratic_operands(q), self.identity(), q, qt,
            gradient, phi, phit, iteration, trial, deadline=deadline,
            resource_limit_bytes=2*1024**3, admitted_bytes=self.allocation['admitted_bytes'])

    def release_state(self):
        self.diagonal = None


class _Linear(reduced._Linear):
    def stronger_terminal(self):
        self.check()
        self.dispose_metric()
        started = monotonic()
        row = dict(iteration=int(self.iter), q=self.xc.copy(), seconds=0., check=None, failure=None)
        self.terminal_audits.append(row)
        owner = None
        try:
            q = reduced.core.linear._owned(self.xc)
            audits = self._audit_bytes+sum(s[0].nbytes+128 for s in self.states)
            audits += 2048*len(self.line_search_trials)+(32768+1024*len(q))*len(self.terminal_audits)
            owner = accuracy.OwnedOriginalTerminal(self.objective.metric_operands(q),
                self.objective.quadratic_operands(q), self.identity_value, q, self.g,
                float(self.initial_norm), deadline=self.budget.deadline,
                resource_limit_bytes=self.budget.resource_limit_bytes,
                admitted_bytes=self.budget.admitted_bytes, retained_audit_bytes=audits)
            row['check'] = owner.certify(self.terminal_policy)
            self.check()
            return row['check']['passed']
        except source.intervals._Expired:
            row['failure'] = 'wall_cap'
            self.fail('wall_cap')
        except (ValueError, TypeError, KeyError, ArithmeticError, RuntimeError) as error:
            row['failure'] = type(error).__name__+':'+str(error)[:160]
            self.fail('terminal_operands_failed')
        finally:
            if owner is not None:
                owner.close()
            row['seconds'] = monotonic()-started


def solve_bounded_linear(request, observations, noise, prior, rows, beta_candidate, *,
        observation_rows=None, deadline, remaining_steps=200):
    """Construct and solve one original supplied partition, no injection hooks.

    All construction and terminal arithmetic consume the same original120s.
    Original covariance marginal/root and beta_engine=nfit*beta are preserved.
    Stronger sufficient gates supplement, never replace, independent assertions.
    """
    if (type(deadline) is not float or not np.isfinite(deadline)
        or type(remaining_steps) is not int or not 0 <= remaining_steps <= 200):
        raise ValueError('gravity original: original absolute clock/accepted allowance')
    started = monotonic()
    deadline = min(deadline, started+120.)
    # Original native metadata/value/noise/geometry checks precede construction.
    physics.survey._native_metadata(dict(request=request, observations=observations,
        noise=noise, prior=prior, rows=rows, observation_rows=observation_rows,
        beta_candidate=beta_candidate))
    physics.metric._time(deadline)
    if type(noise) is not dict or set(noise) != {'kind', 'values'}:
        raise ValueError('gravity original: exact original declared noise')
    physics.survey._enum(noise['kind'], ('diagonal_sd', 'full_covariance'), 'noise.kind')
    source_count = len(request['stations']['receivers_m'])
    a = len(prior['start_kg_m3'])
    allocation = allocation_plan(source_count, len(rows), a, noise['kind'] == 'full_covariance')
    problem = physics._build_problem(request, observations, noise, prior, rows,
        beta_candidate, observation_rows=observation_rows)
    positions = rows if observation_rows is None else np.searchsorted(observation_rows, rows)
    inventory = source_inventory()
    adapter = _Objective(problem, prior, noise, positions, inventory, allocation)
    identity = adapter.identity()
    budget = ConditionedBudget(deadline, remaining_steps, 2*1024**3,
        allocation['admitted_bytes'], allocation['allocation_plan_sha256'])
    binding = reduced.ConditionedBinding('gravity_original_optimizer.solve_bounded_linear',
        SOURCE_SHA256, owned.SOURCE_SHA256, owned.KERNEL_SHA256, reduced.VENDOR_SOURCE_SHA256,
        source.SOURCE_SHA256, identity['source_inventory_sha256'], LINEAR_EPOCH, POLICY)
    terminal = owned.TerminalPolicy(1e-7, model_error_limit=1e-8,
        objective_gap_limit=1e-8, physical_prediction_error_limit=1e-6)
    value = adapter.quadratic_operands(adapter.start)
    source.validate(value, identity, adapter.start, deadline=deadline,
        resource_limit_bytes=2*1024**3, admitted_bytes=allocation['admitted_bytes'])
    value = None
    result = reduced.core._solve(adapter, adapter.lower, adapter.upper, adapter.start,
        budget=budget, binding=binding, terminal=terminal, mode='fixed_linear_quadratic',
        optimizer_class=_Linear, source_epoch=('gravity_original_optimizer', SOURCE_SHA256, POLICY, LINEAR_EPOCH))
    result['source_binding'].update(original_arithmetic=source.SOURCE_SHA256,
        original_terminal=accuracy.SOURCE_SHA256, reduced_dependency=reduced.SOURCE_SHA256)
    prediction = (None if result['q'] is None else
        problem['simulation'].dpred(result['q'])+problem['background'])
    if monotonic() > deadline and result['status'] == 'converged':
        result.update(status='nonconverged', reason='wall_cap')
    return dict(schema='gravity-original-partition-1', identity=identity,
        source_inventory=inventory, allocation_plan=allocation, optimizer_binding=asdict(binding),
        terminal_policy=asdict(terminal), result=result, wall_seconds=monotonic()-started,
        fit_rows=problem['rows'], beta_candidate=beta_candidate,
        model_kg_m3=None if result['q'] is None else result['q']*1000.,
        predicted_mgal=prediction,
        source_authority_verified=False, host_accepted=False, full_M02_accepted=False,
        public_activation=False)
