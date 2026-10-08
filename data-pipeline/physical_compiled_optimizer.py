"""Closed stored-A/d half-quadratic baseline, not nonlinear/global admission.

Canonical native beta_engine=1 and tuple scale are not rewritten. A separately
bound proof-coordinate view supplies actual scientific beta and physical J.
"""
from dataclasses import dataclass, replace
from decimal import Decimal
import hashlib
from pathlib import Path
from time import monotonic

import numpy as np
import scipy.sparse as sp

import physical_original_quadratic as source
import physical_original_terminal as original_terminal
import physical_original_residual_terminal as residual
import physical_reduced_optimizer as reduced


SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
LINEAR_EPOCH = 'physical-gncg-compiled-original-residual-candidate-1'
POLICY = 'closed-compiled-identity-half-native-free-face-residual-accuracy-1'
RESIDUAL_SHA256 = 'a9bf32a6c4e932d7d4efa1f38540778e2993f74982adb9f29985d921ecb5ddf7'
PRECISION_SHA256 = '57727cac9ab6550eab902d20d6c43e662be8f9fac406896c6797d1e29b3e7c1a'
_LOADED_PRECISION_SHA256 = hashlib.sha256(Path(source.owned.intervals.__file__).read_bytes()).hexdigest()
BETAS = (.0001, .001, .01, .1, 1., 10., 100., 1000.)
ConditionedBudget = reduced.ConditionedBudget
ConditionedBinding = reduced.ConditionedBinding
VENDOR_SOURCE_SHA256 = reduced.VENDOR_SOURCE_SHA256


@dataclass(frozen=True)
class CompiledQuadraticOperands:
    binding: source.owned.OperandBinding
    sensitivity: np.ndarray
    observations: np.ndarray
    prior: sp.csr_matrix
    reference: np.ndarray
    lower: np.ndarray
    upper: np.ndarray
    scientific_beta: float
    physical_sensitivity: np.ndarray
    active_full_indices: np.ndarray
    mesh_shape: tuple


@dataclass(frozen=True)
class RetainedCompiledProblem:
    full_kernels: tuple
    development_arrays: tuple


def _check_source():
    if residual.SOURCE_SHA256 != RESIDUAL_SHA256:
        raise ValueError('compiled original: literal residual source drift')
    for module in (source, original_terminal, original_terminal.exact_rows, residual, reduced, reduced.core,
                   source.owned, source.owned.kernel):
        if hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest() != module.SOURCE_SHA256:
            raise ValueError('compiled original: loaded/on-disk public source drift')
    if (_LOADED_PRECISION_SHA256 != PRECISION_SHA256
        or hashlib.sha256(Path(source.owned.intervals.__file__).read_bytes()).hexdigest() != PRECISION_SHA256):
        raise ValueError('compiled original: literal loaded/on-disk precision source drift')
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError('compiled original: loaded bridge source drift')


def _identity_hash(identity):
    return source.owned.digest(tuple((key, identity[key]) for key in sorted(identity)))


def _metadata(o, identity, q):
    if (type(identity) is not dict or set(identity) != reduced.core.linear._IDENTITY_KEYS
        or type(o) is not CompiledQuadraticOperands
        or type(o.binding) is not source.owned.OperandBinding):
        raise ValueError('compiled original: closed DTO and original13 native identity')
    a, m = identity['parameter_count'], identity['observation_rows']
    if (type(a) is not int or not 1 <= a <= 4096 or type(m) is not int or not 1 <= m <= 2048
        or identity['mode'] != 'fixed_linear_quadratic' or identity['runtime_epoch'] != LINEAR_EPOCH
        or identity['observation_components'] != 1 or type(identity['observation_components']) is not int
        or type(identity['beta_engine']) is not float or identity['beta_engine'] != 1.
        or type(identity['physical_scale']) is not tuple or len(identity['physical_scale']) != 1
        or not reduced.core.linear._finite(identity['physical_scale'][0], positive=True)
        or identity['q_unit'] != 'normalized_property_block' or identity['physical_unit'] not in ('kg_m3', 'si')
        or type(identity['stage_index']) is not int or not 0 <= identity['stage_index'] <= 25
        or any(not source.owned._hash(identity[key]) for key in
            ('objective_sha256', 'source_inventory_sha256', 'allocation_plan_sha256'))
        or type(o.scientific_beta) is not float or o.scientific_beta not in BETAS
        or type(o.physical_sensitivity) is not np.ndarray or o.physical_sensitivity.ndim != 2):
        raise ValueError('compiled original: original native scale/beta/counts and actual coefficient')
    n = o.physical_sensitivity.shape[0]
    if (not m <= n <= 2048 or not source.owned._matrix(o.sensitivity, m, a)
        or not source.owned._matrix(o.physical_sensitivity, n, a)
        or any(not source._vector(v, a) for v in (q, o.reference, o.lower, o.upper))
        or not source._vector(o.observations, m)
        or type(o.mesh_shape) is not tuple or len(o.mesh_shape) != 3
        or any(type(v) is not int or not 1 <= v <= 4096 for v in o.mesh_shape)
        or np.prod(o.mesh_shape, dtype=np.int64) > 4096
        or type(o.active_full_indices) is not np.ndarray or o.active_full_indices.dtype != np.int64
        or o.active_full_indices.shape != (a,) or not o.active_full_indices.flags.c_contiguous
        or type(o.prior) is not sp.csr_matrix or o.prior.shape[1] != a
        or not a <= o.prior.shape[0] <= 4*a):
        raise ValueError('compiled original: bounded stored A/d/R/fullJ/mesh metadata')
    source._csr_metadata(o.prior, o.prior.shape[0], a, 7*a)
    arrays = (o.sensitivity, o.physical_sensitivity, o.observations, o.reference,
              o.lower, o.upper, o.active_full_indices, o.prior.data, o.prior.indices, o.prior.indptr)
    payload = sum(source._backing_bytes(v) for v in arrays)
    if (source._backing_bytes(o.sensitivity) > 8*m*a
        or source._backing_bytes(o.physical_sensitivity) > 8*n*a
        or any(source._backing_bytes(v) > 16*a for v in (q, o.reference, o.lower, o.upper))
        or source._backing_bytes(o.active_full_indices) > 8*a
        or payload > source.RESERVE_BYTES):
        raise ValueError('compiled original: actual compiled ultimate source payload exceeds qualified backing')
    return a, m, n, payload


def _terms(o, a):
    source.owned._csr(o.prior, o.prior.shape[0], a, 7*a)
    indices = o.active_full_indices
    if (np.any(indices < 0) or np.any(indices >= np.prod(o.mesh_shape, dtype=np.int64))
        or np.any(np.diff(indices) <= 0)):
        raise ValueError('compiled original: literal original increasing active mesh indices')
    small = o.prior[:a].tocsr()
    if (not np.array_equal(small.indptr, np.arange(a+1, dtype=np.int32))
        or not np.array_equal(small.indices, np.arange(a, dtype=np.int32)) or np.any(small.data <= 0.)):
        raise ValueError('compiled original: actual positive scientific smallness')
    groups = [[], [], []]
    nx, ny, nz = o.mesh_shape
    stride = (1, nx, nx*ny)
    for row in range(a, o.prior.shape[0]):
        left, right = o.prior.indptr[row:row+2]
        columns, values = o.prior.indices[left:right], o.prior.data[left:right]
        if (len(columns) != 2 or not columns[0] < columns[1]
            or not values[0] < 0. or values[1] != -values[0]):
            raise ValueError('compiled original: exact original signed neighboring R row')
        lo, hi = map(int, indices[columns])
        xyz = (lo % nx, (lo//nx) % ny, lo//(nx*ny))
        axes = [axis for axis in range(3) if hi-lo == stride[axis]
                and xyz[axis]+1 < o.mesh_shape[axis]]
        if len(axes) != 1:
            raise ValueError('compiled original: genuine mesh neighbor, no wrapped graph edge')
        groups[axes[0]].append(row)
    terms = [source.owned.QuadraticTerm(.5, small, sp.eye(a, format='csr'))]
    for group in groups:
        if group:
            block = o.prior[group].tocsr()
            derivative = block.copy()
            derivative.data[::2] = -1.
            derivative.data[1::2] = 1.
            weights = sp.diags(block.data[1::2].copy(), format='csr')
            if (weights@derivative-block).nnz:
                raise ValueError('compiled original: exact original R factors changed')
            terms.append(source.owned.QuadraticTerm(.5, weights, derivative))
    return tuple(terms)


def _normalization(o, identity, q):
    a, m, n, payload = _metadata(o, identity, q)
    if (o.binding != source.owned.binding_for(identity, q)
        or any(not np.isfinite(v).all() for v in (o.sensitivity, o.observations,
            o.physical_sensitivity, o.reference, o.lower, o.upper, q))
        or np.any(o.lower >= o.upper) or np.any(q < o.lower) or np.any(q > o.upper)):
        raise ValueError('compiled original: finite exact bound original source/model binding')
    terms = _terms(o, a)
    source_sha = source.owned.digest((o.sensitivity, o.observations, o.prior, o.reference,
        o.lower, o.upper, o.scientific_beta, o.physical_sensitivity, o.active_full_indices, o.mesh_shape))
    native_sha = _identity_hash(identity)
    proof = dict(identity, runtime_epoch='compiled-original-proof-coordinate-1',
        objective_sha256=source.owned.digest((native_sha, source_sha, 'identity-half-physical-scale-1')),
        beta_engine=o.scientific_beta, physical_scale=identity['physical_scale'][0], stage_index=0)
    # This is an explicit proof-coordinate view, never returned as native identity.
    original = source.OriginalQuadraticOperands(source.owned.binding_for(proof, q), n,
        o.sensitivity, None, source.OriginalWhitening('diagonal_sd', np.ones(m)),
        o.observations, o.reference, o.lower, o.upper, .5, o.scientific_beta, terms,
        o.physical_sensitivity, None)
    mapping = dict(native_identity=identity.copy(), native_identity_sha256=native_sha,
        proof_identity=proof, source_sha256=source_sha, scientific_beta=o.scientific_beta,
        likelihood_scale=.5, physical_scale=identity['physical_scale'],
        runtime_whitening='identity_compiled_A_d', actual_source_payload_bytes=payload)
    mapping['mapping_sha256'] = source.owned.digest((native_sha, source_sha,
        _identity_hash(proof), o.scientific_beta, .5, identity['physical_scale']))
    return original, mapping


def allocation_plan(o, identity, q, retained):
    """SUM whole retained Problem and prospective proof phases, never caller bytes."""
    a, m, n, payload = _metadata(o, identity, q)
    if (type(retained) is not RetainedCompiledProblem or type(retained.full_kernels) is not tuple
        or len(retained.full_kernels) != 2 or type(retained.development_arrays) is not tuple
        or not 1 <= len(retained.development_arrays) <= 32):
        raise ValueError('compiled original: BOTH full kernels and complete original development envelope')
    kernel_bytes = 0
    for matrix in retained.full_kernels:
        if (type(matrix) is not np.ndarray or matrix.ndim != 2 or matrix.shape[1] != a
            or not 1 <= matrix.shape[0] <= 2048 or not source.owned._matrix(matrix, matrix.shape[0], a)
            or source._backing_bytes(matrix) > 8*matrix.shape[0]*a):
            raise ValueError('compiled original: bounded original full retained kernels')
        kernel_bytes += source._backing_bytes(matrix)
    if not any(matrix is o.physical_sensitivity for matrix in retained.full_kernels):
        raise ValueError('compiled original: physical J must belong to retained full Problem')
    development_bytes = 0
    for array in retained.development_arrays:
        if (type(array) is not np.ndarray or array.dtype not in (np.dtype('float64'), np.dtype('int64'))
            or array.ndim not in (1, 2) or not array.flags.c_contiguous
            or array.size > 2048**2 or source._backing_bytes(array) > 32*1024**2):
            raise ValueError('compiled original: bounded actual complete development arrays')
        development_bytes += source._backing_bytes(array)
    old = 4*kernel_bytes+4*development_bytes+36*251*a*8+512*(2*a)*8+64*1024**2
    native = source.owned.kernel.allocation(n, m, a, False)
    source_phase = dict(operand_and_sparse_copy_bytes=2*source.RESERVE_BYTES,
        endpoint_bytes=source.ENDPOINT_PAIR_BYTES*(14*a+6*n),
        native_row_scratch_bytes=128*(3*a+n), metadata_bytes=32768)
    retained_phase = dict(native_states_bytes=201*(8*a+128),
        reduced_phase_audits_bytes=reduced.PHASE_LIMIT*(reduced.PHASE_METADATA_BYTES+40*a),
        native_line_search_bytes=4000*2048, compiled_chord_mapping_bytes=4000*2048,
        terminal_audits_bytes=201*(32768+1024*a))
    terminal = dict(free_endpoint_bytes=source.ENDPOINT_PAIR_BYTES*12*a,
        factor_and_transpose_bytes=16*m*a+16*7*a+64*a+4*(a+1),
        native_workspace_bytes=source.RESERVE_BYTES, witness_bytes=128*a, mapping_bytes=65536)
    total = old+native['maximum']+sum(source_phase.values())+sum(retained_phase.values())+sum(terminal.values())
    if total > 2*1024**3:
        raise ValueError('compiled original: complete simultaneous original2GiB resource cap')
    value = dict(original_retained_problem_bytes=old, full_kernel_bytes=kernel_bytes,
        development_bytes=development_bytes, original_native=native, source_phase=source_phase,
        retained_audits=retained_phase, terminal=terminal, admitted_bytes=total,
        source_components=n, fit_components=m, parameters=a, source_payload_bytes=payload,
        resource_limit_bytes=2*1024**3, CG=200, accepted=200, states=201, LS=20, seconds=120.)
    value['allocation_plan_sha256'] = source.owned.digest((old, kernel_bytes, development_bytes,
        tuple(sorted(native.items())), tuple(sorted(source_phase.items())),
        tuple(sorted(retained_phase.items())), tuple(sorted(terminal.items())), n, m, a, payload, total))
    return value


class _CompiledResidualTerminal(residual.OwnedOriginalResidualTerminal):
    def __init__(self, o, identity, q, gradient, initial_norm, allocation, *, deadline, retained_audit_bytes):
        _check_source()
        original, self.mapping = _normalization(o, identity, q)
        regularizer = (o.scientific_beta*(o.prior.T@o.prior)).tocsr()
        regularizer.sort_indices()
        metric = source.owned.MetricOperands(original.binding, original.source_components,
            len(o.observations), len(q), False, regularizer, o.sensitivity, .5)
        super().__init__(metric, original, self.mapping['proof_identity'], q, gradient,
            initial_norm, deadline=deadline, resource_limit_bytes=2*1024**3,
            admitted_bytes=allocation['admitted_bytes'], retained_audit_bytes=retained_audit_bytes+
                allocation['original_retained_problem_bytes']+allocation['terminal']['mapping_bytes'])

    def certify(self, policy):
        started = monotonic()
        try:
            source.owned.validate_terminal(policy)
            # Unscaled J is NOT the physical-unit predicate. All other exact
            # original gates are unchanged and this view cannot accept a fit.
            record = super().certify(replace(policy, physical_prediction_error_limit=None))
            ar = original_terminal.original_row_arithmetic(34, self.deadline)
            unscaled = Decimal(record['bounds']['physical_prediction_error_upper'])
            physical = ar.hi.multiply(unscaled, Decimal.from_float(self.mapping['physical_scale'][0]))
            record['unscaled_prediction_error_upper'] = str(unscaled)
            record['bounds']['physical_prediction_error_upper'] = str(physical)
            record['compiled_mapping'] = self.mapping
            record['domain'] = 'compiled-original-residual-half-physical-prediction-1'
            record['original_physical_prediction_limit'] = policy.physical_prediction_error_limit
            record['passed'] = bool(record['passed'] and (policy.physical_prediction_error_limit is None
                or physical <= Decimal.from_float(policy.physical_prediction_error_limit)))
            record['reason'] = 'original_accuracy_certified' if record['passed'] else 'original_accuracy_not_certified'
            _check_source()
            ar.check()
            return record
        finally:
            self.close()
            if 'record' in locals():
                record.update(seconds=monotonic()-started, disposed=self.live_payload_bytes == 0)


class _CompiledObjective:
    """Delegate unchanged native H/g/evaluation; own all numerical proof actions."""
    def __init__(self, native, budget, start):
        self.native, self.budget = native, budget
        for name in ('identity', 'evaluate', 'components', 'binding_diagonal',
                     'release_state', 'compiled_operands', 'retained_compiled_problem'):
            if not callable(getattr(native, name, None)):
                raise ValueError('compiled original: complete trusted native/source DTO adapter')
        self.canonical_identity = reduced.core._identity(native, 'fixed_linear_quadratic', LINEAR_EPOCH)
        self.retained = native.retained_compiled_problem()
        o = native.compiled_operands(start)
        self.allocation = allocation_plan(o, self.canonical_identity, start, self.retained)
        if (budget.resource_limit_bytes != self.allocation['resource_limit_bytes']
            or budget.admitted_bytes != self.allocation['admitted_bytes']
            or budget.allocation_plan_sha256 != self.allocation['allocation_plan_sha256']
            or self.canonical_identity['allocation_plan_sha256'] != budget.allocation_plan_sha256):
            raise ValueError('compiled original: exact owner-derived whole-Problem allocation')
        self.source_digest = None
        self.mapping_records = []
        self.original(start)

    def __getattr__(self, name):
        return getattr(self.native, name)

    def evaluate(self, *args, **kwargs):
        if monotonic() > self.budget.deadline:
            raise source.intervals._Expired
        _check_source()
        if self.native.identity() != self.canonical_identity:
            raise ValueError('compiled original: canonical native identity drift')
        # No reconstructed potential/gradient/Hessian here: actual native
        # outputs and action objects are returned literally unchanged.
        return self.native.evaluate(*args, **kwargs)

    def original(self, q):
        if monotonic() > self.budget.deadline:
            raise source.intervals._Expired
        _check_source()
        identity = self.native.identity()
        if identity != self.canonical_identity:
            raise ValueError('compiled original: canonical native identity drift')
        o = self.native.compiled_operands(q)
        original, mapping = _normalization(o, identity, q)
        # The source digest excludes the actual model, but includes every
        # literal A/d/R/reference/box/J/mesh/coefficient. No changed epoch reuse.
        if self.source_digest is None:
            self.source_digest = mapping['source_sha256']
        elif self.source_digest != mapping['source_sha256']:
            raise ValueError('compiled original: frozen physical source operand drift')
        source.validate(original, mapping['proof_identity'], q, deadline=self.budget.deadline,
            resource_limit_bytes=self.budget.resource_limit_bytes, admitted_bytes=self.budget.admitted_bytes)
        return o, original, mapping

    def metric_operands(self, q):
        o, _, _ = self.original(q)
        regularizer = (o.scientific_beta*(o.prior.T@o.prior)).tocsr()
        regularizer.sort_indices()
        return source.owned.MetricOperands(o.binding, o.physical_sensitivity.shape[0],
            len(o.observations), len(q), False, regularizer, o.sensitivity, .5)

    def quadratic_operands(self, q):
        return self.original(q)[1]

    def certify(self, q, qt, gradient, phi, phit, iteration, trial, deadline):
        _, original, mapping = self.original(q)
        record = source.certify_chord(original, mapping['proof_identity'], q, qt,
            gradient, phi, phit, iteration, trial, deadline=min(deadline, self.budget.deadline),
            resource_limit_bytes=self.budget.resource_limit_bytes, admitted_bytes=self.budget.admitted_bytes)
        # Keep the original strict14-key certificate unchanged. Mapping proof
        # belongs to a separate bounded replay record, not extra callback keys.
        self.mapping_records.append(dict(iteration=iteration, trial=trial,
            mapping_sha256=mapping['mapping_sha256'], native_identity_sha256=mapping['native_identity_sha256'],
            source_sha256=mapping['source_sha256'], q_sha256=source.owned.digest(q),
            trial_q_sha256=source.owned.digest(qt)))
        if len(self.mapping_records) > 4000:
            raise ValueError('compiled original: original accepted/LS mapping record cap')
        _check_source()
        return record


class _Linear(reduced._Linear):
    def evaluate(self, *args, **kwargs):
        try:
            return super().evaluate(*args, **kwargs)
        except source.intervals._Expired:
            self.fail('wall_cap')

    def stoppingCriteria(self, inLS=False):
        try:
            return super().stoppingCriteria(inLS)
        except source.intervals._Expired:
            self.fail('wall_cap')

    def prepare_owned(self, terminal, mode, source_epoch=None):
        super().prepare_owned(terminal, mode, source_epoch)
        self._kernel_base_bytes = 0

    def _admit_phase(self, phase):
        # Parent computes kernel and prospective history BEFORE factory setup.
        # Add, never MAX away, the coexisting complete original joint Problem.
        self._base_bytes = self._kernel_base_bytes
        try:
            count = super()._admit_phase(phase)
        except source.intervals._Expired:
            self.fail('wall_cap')
        self._kernel_base_bytes = self._base_bytes
        self._base_bytes += self.objective.allocation['original_retained_problem_bytes']
        prospective = (self._base_bytes+reduced.WORKSPACE_BYTES+self._audit_bytes+count
            +8*self.identity_value['parameter_count']+2048*len(self.objective.mapping_records))
        if prospective > min(self.budget.admitted_bytes, self.budget.resource_limit_bytes):
            self.fail('resource_cap')
        self._resource_peak = max(self._resource_peak, prospective)
        return count

    def stronger_terminal(self):
        self.check()
        _check_source()
        self.dispose_metric()
        started = monotonic()
        row = dict(iteration=int(self.iter), q=self.xc.copy(), seconds=0., check=None, failure=None)
        self.terminal_audits.append(row)
        owner = None
        try:
            q = reduced.core.linear._owned(self.xc)
            o, _, mapping = self.objective.original(q)
            audits = self._audit_bytes+sum(s[0].nbytes+128 for s in self.states)
            audits += 2048*(len(self.line_search_trials)+len(self.objective.mapping_records))
            audits += (32768+1024*len(q))*len(self.terminal_audits)
            owner = _CompiledResidualTerminal(o, self.identity_value, q, self.g,
                float(self.initial_norm), self.objective.allocation, deadline=self.budget.deadline,
                retained_audit_bytes=audits)
            if owner.mapping['mapping_sha256'] != mapping['mapping_sha256']:
                raise ValueError('compiled original: owner normalization mapping drift')
            row['check'] = owner.certify(self.terminal_policy)
            _check_source()
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


def solve_bounded_linear(objective, lower_q, upper_q, start_q, *, budget, binding, terminal):
    """Closed compiled physical DTO bridge; unchanged actual native solver ABI."""
    started = monotonic()
    if (type(budget) is not ConditionedBudget or not reduced.core.linear._finite(budget.deadline)
        or type(budget.remaining_steps) is not int or not 0 <= budget.remaining_steps <= 200):
        raise ValueError('compiled original: original absolute clock/accepted allowance')
    budget = replace(budget, deadline=min(budget.deadline, started+120.))
    if monotonic() > budget.deadline:
        raise source.intervals._Expired
    _check_source()
    if (type(binding) is not ConditionedBinding
        or binding.certificate_source_sha256 != source.SOURCE_SHA256):
        raise ValueError('compiled original: exact original chord certificate source')
    proxy = _CompiledObjective(objective, budget, start_q)
    o, _, mapping = proxy.original(start_q)
    if not np.array_equal(o.lower, lower_q) or not np.array_equal(o.upper, upper_q):
        raise ValueError('compiled original: exact original source/native bounds')
    o = None
    result = reduced.core._solve(proxy, lower_q, upper_q, start_q, budget=budget,
        binding=binding, terminal=terminal, mode='fixed_linear_quadratic', optimizer_class=_Linear,
        source_epoch=('physical_compiled_optimizer', SOURCE_SHA256, POLICY, LINEAR_EPOCH))
    result['compiled_mapping'] = mapping
    result['compiled_chord_mappings'] = tuple(proxy.mapping_records)
    result['allocation_plan'] = proxy.allocation
    result['source_binding'].update(original_arithmetic=source.SOURCE_SHA256,
        original_terminal=original_terminal.SOURCE_SHA256, original_residual_terminal=RESIDUAL_SHA256,
        original_rows=original_terminal.exact_rows.SOURCE_SHA256, reduced_dependency=reduced.SOURCE_SHA256)
    return result
