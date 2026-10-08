"""Prospective canonical IRLS face guards, not an enabled fit policy.

Native binding signs distinguish binding from inward-released literal bounds.
No arbitrary caller mask, tie perturbation or historical branch replacement.
"""
import hashlib
from pathlib import Path

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import LinearOperator

import gravity_irls_corrected as interior


SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
RESEARCH_EPOCH = 'm02-canonical-native-free-face-guards-1'
VENDOR_SHA256 = '0ac858cc310b32bb9aa59c78aaaa9c79b5f28438db52fb06ec73d976b63196a4'


def _native_binding(q, gradient, lower, upper):
    """Internal original-source arithmetic helper; never upload admission."""
    native_module = interior.plain.l2.optimization
    if hashlib.sha256(Path(native_module.__file__).read_bytes()).hexdigest() != VENDOR_SHA256:
        raise ValueError('canonical face: native binding source drift')
    if type(q) is not np.ndarray or q.ndim != 1 or not 1 <= len(q) <= 4096:
        raise ValueError('canonical face: original native bounded model')
    if any(not interior.plain.optimizer._array(v, len(q)) for v in (q, gradient, lower, upper)):
        raise ValueError('canonical face: finite original native vectors')
    if np.any(lower >= upper) or np.any(q < lower) or np.any(q > upper):
        raise ValueError('canonical face: exact original feasible box')
    native = native_module.ProjectedGNCG(lower=lower, upper=upper, maxIter=200,
        maxIterLS=20, cg_maxiter=200, cg_rtol=1e-6, cg_atol=0.)
    native.g = gradient.copy()
    return native.bindingSet(q).copy()


def _classify(q, reference, gradient, lower, upper):
    binding = _native_binding(q, gradient, lower, upper)
    if not interior.plain.optimizer._array(reference, len(q)):
        raise ValueError('canonical face: original reference vector')
    x = q-reference
    if not np.isfinite(x).all():
        raise ValueError('canonical face: finite actual normalized displacement')
    free = np.flatnonzero(~binding).astype(np.int64)
    maxima = np.flatnonzero(np.abs(x) == np.max(np.abs(x))).astype(np.int64)
    maximum = float(np.max(np.abs(x)))
    branch = 'disabled_null' if not maximum else 'disabled_empty_free_face' if not len(free) else None
    constant = bool(maximum and len(free) and np.all(binding[maxima]))
    gap = maximum-float(np.max(np.abs(x[free]))) if len(free) else None
    if branch is None:
        if constant and gap > 0.:
            branch = 'native_binding_max_constant_scale'
        elif len(maxima) == 1:
            branch = 'native_free_unique_max_rank_one'
        else:
            branch = 'disabled_free_tied_max'
    value = dict(branch=branch, binding=interior.plain.survey._readonly(binding),
        free=interior.plain.survey._readonly(free),
        maxima=interior.plain.survey._readonly(maxima), maximum=maximum,
        maximum_index=int(maxima[0]) if len(maxima) == 1 else None,
        free_scale_gap=gap, constant_scale=constant and gap is not None and gap > 0.,
        derivative_supported=branch in ('native_binding_max_constant_scale', 'native_free_unique_max_rank_one'))
    return value


def _same_face_trial(center, trial, gradient, reference, lower, upper, face):
    """Guard only, before a proposal can be adopted; no projection/fallback."""
    if (not interior.plain.optimizer._array(trial, len(center))
        or np.any(trial < lower) or np.any(trial > upper)
        or not np.any(trial != center)
        or not np.array_equal(trial[face['binding']], center[face['binding']])):
        return False
    current = _classify(trial, reference, gradient, lower, upper)
    if not np.array_equal(current['binding'], face['binding']) or current['branch'] != face['branch']:
        return False
    if face['constant_scale']:
        return (current['constant_scale'] and current['maximum'] == face['maximum']
            and np.array_equal(current['maxima'], face['maxima']))
    return current['maximum_index'] == face['maximum_index']


def _derivative_allocation(original):
    """Private closed constructor accounting, not caller allowance admission."""
    import gravity_irls_original as physical
    a, n, m, covariance = (original[k] for k in ('parameters', 'source_components', 'fit_components', 'covariance'))
    if original != physical.allocation_plan(n, m, a, covariance):
        raise ValueError('canonical face: exact original retained partition dictionary')
    value = dict(original_partition_bytes=original['admitted_bytes'],
        derivative_kernel_bytes=physical.original.owned.kernel.allocation(n, m, a, covariance)['maximum'],
        derivative_source_jacobian_bytes=16*m*a,
        derivative_source_parameter_workspace_bytes=256*a,
        derivative_source_likelihood_workspace_bytes=256*m,
        derivative_source_metadata_bytes=65536,
        derivative_sparse_bytes=16*7*a+4*(a+1), metadata_bytes=65536)
    value['maximum'] = sum(value.values())
    if value['maximum'] > 2*1024**3:
        raise ValueError('canonical face: simultaneous original partition/derivative metric2GiB')
    return value


class _CanonicalFaceLinearization:
    """Closed physical source derivative owner, not an enabled fit recurrence.

    A native partition owns source construction; this object has no public
    model-acceptance method, caller gradient/Hessian/mask/SPD or CG fallback.
    Unsupported faces disable BEFORE derivative or metric construction.
    """
    def __init__(self, owner, q, policy, index, initial):
        import gravity_irls_original as physical
        if type(owner) is not physical.GravityIRLSPartition:
            raise TypeError('canonical face: exact closed original physical owner')
        if type(index) is not int or not 0 <= index <= 20:
            raise ValueError('canonical face: original stage index')
        self.owner = owner
        self._closed = False
        self._metric = self._operator = self._objective = None
        self.q = self.root = self.u = self.diagonal = self._regularizer = self._jacobian = None
        self.record = dict(research_epoch=RESEARCH_EPOCH, source_sha256=SOURCE_SHA256,
            stage=index, derivative_constructed=False, metric_constructed=False,
            native_fit_accepted=False, recurrence_enabled=False, disposed=False)
        try:
            owner.check()
            self._source_check()
            if not interior.plain.optimizer._array(q, len(owner.prior['start_kg_m3'])):
                raise ValueError('canonical face: actual bounded finite physical model')
            self.q = interior.plain.survey._readonly(q.copy())
            stage = interior._stage(owner.problem, self.q, policy, index, initial)
            lo = owner.prior['lower_kg_m3']/1000.
            hi = owner.prior['upper_kg_m3']/1000.
            self._objective = interior._Objective(stage, index, lo, hi,
                owner.allocation['allocation_plan_sha256'])
            _, gradient = self._objective.evaluate(self.q, True, False)
            self.root = interior.plain.survey._readonly(gradient/2.)
            self.face = _classify(self.q, owner.problem['reference_q'], gradient, lo, hi)
            self.record.update(branch=self.face['branch'], native_gradient=gradient.copy(),
                native_binding=self.face['binding'].copy(), free=self.face['free'].copy(),
                maxima=self.face['maxima'].copy(), free_scale_gap=self.face['free_scale_gap'],
                stage_sha256=stage['objective_sha256'], epsilon=stage['epsilon'])
            if not self.face['derivative_supported']:
                self._state_sha256 = self._state_seal()
                return
            # The original retained native books coexist with this prospective
            # derivative source and metric. SUM a complete extra native phase,
            # not a caller allowance or subtraction of presumed unused memory.
            self.allocation = _derivative_allocation(owner.allocation)
            self.record['allocation'] = self.allocation.copy()
            self._operator, u, _, diagonal = interior._linearization(owner.problem, stage,
                self._objective, self.q, owner.deadline)
            # Native actions remain literal full source actions with zero
            # embedding on binding coordinates, not a full solve-and-clip.
            self.u = interior.plain.survey._readonly(u.copy())
            self.diagonal = interior.plain.survey._readonly(diagonal.copy())
            self.record['derivative_constructed'] = True
            self._stage = stage
            self._state_sha256 = self._state_seal()
            self.record['source_state_sha256'] = self._state_sha256
            self.check()
        except BaseException:
            self.close()
            raise

    def _source_check(self):
        if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != SOURCE_SHA256:
            raise ValueError('canonical face: loaded derivative source drift')

    def _state_seal(self):
        return interior.plain.survey._digest(dict(q=self.q, root=self.root,
            u=self.u, diagonal=self.diagonal, binding=self.face['binding'],
            free=self.face['free'], maxima=self.face['maxima'], branch=self.face['branch']))

    def check(self):
        if self._closed:
            raise ValueError('canonical face: disposed derivative owner')
        try:
            self.owner.check()
            self._source_check()
            self._objective.identity()
            if self._state_seal() != self._state_sha256:
                raise ValueError('canonical face: frozen source/model/branch drift')
        except BaseException:
            self.close()
            raise

    def action(self, value, *, full=False):
        """Literal M_FF or J_FF; binding max removes rank-one EXACTLY."""
        self.check()
        if not self.face['derivative_supported']:
            raise ValueError('canonical face: derivative disabled before proposal construction')
        free = self.face['free']
        if not interior.plain.optimizer._array(value, len(free)):
            raise ValueError('canonical face: actual finite free derivative vector')
        embedded = np.zeros(len(self.q))
        embedded[free] = value
        result = self._operator@embedded
        if full and not self.face['constant_scale']:
            result += self.u*embedded[self.face['maximum_index']]
        self.check()
        return interior._finite(result[free])

    def metric(self):
        """Own prospective principal Joseph construction from literal source."""
        self.check()
        if not self.face['derivative_supported']:
            raise ValueError('canonical face: derivative disabled before metric construction')
        if self._metric is not None:
            return self._metric
        try:
            return self._construct_metric()
        except BaseException:
            self.close()
            raise

    def _construct_metric(self):
        import physical_owned_spd as owned
        problem, stage = self.owner.problem, self._stage
        x = self.q-problem['reference_q']
        eps = stage['epsilon'][0]
        small = problem['regularization'].objfcts[0]
        v = problem['beta_engine']*problem['regularization'].multipliers[0]*small.W.diagonal()**2
        scale = np.sqrt(self.face['maximum']**2+eps**2)
        correction = v*scale*eps**2/(x*x+eps*eps)**1.5
        if not np.isfinite(correction).all() or np.any(correction <= 0.):
            raise ValueError('canonical face: actual positive scientific derivative diagonal')
        prior = sp.diags(correction, format='csr')
        for alpha, child in zip(stage['problem']['regularization'].multipliers[1:],
                stage['problem']['regularization'].objfcts[1:]):
            prior += problem['beta_engine']*alpha*child.deriv2(self.q)/2.
        prior = prior.tocsr(); prior.sort_indices()
        jacobian = np.ascontiguousarray(problem['misfit'].W@problem['simulation'].G)
        identity = self._objective.identity()
        identity.update(runtime_epoch=RESEARCH_EPOCH,
            objective_sha256=owned.digest((identity['objective_sha256'], self.face['binding'],
                self.face['maxima'], prior, jacobian)),
            source_inventory_sha256=interior.plain.survey._digest(dict(self.owner.inventory,
                canonical_face_source=SOURCE_SHA256)))
        operands = owned.MetricOperands(owned.binding_for(identity, self.q),
            self.owner.allocation['source_components'], len(jacobian), len(self.q),
            self.owner.allocation['covariance'], prior, jacobian, .5)
        # M is the half native gradient's derivative: physical data H/2.
        # Factory coefficient .5 corresponds to A.T A in the shared ABI.
        try:
            self._metric = owned.OwnedMetric(operands, identity, self.q,
                self.face['free'], self.owner.deadline, 2*1024**3)
            self._regularizer, self._jacobian = prior, jacobian
            self.record.update(metric_constructed=True, metric_source_sha256=owned.SOURCE_SHA256,
                metric_operand_sha256=self._metric.operand_sha256,
                metric_face_sha256=self._metric.face_sha256, metric_identity=identity.copy())
            self.check()
            return self._metric
        except BaseException:
            self.close()
            raise

    @property
    def live_payload_bytes(self):
        own = sum(v.nbytes for v in (self.q, self.root, self.u, self.diagonal, self._jacobian)
            if type(v) is np.ndarray)
        if self._regularizer is not None:
            own += sum(v.nbytes for v in (self._regularizer.data, self._regularizer.indices, self._regularizer.indptr))
        return own+(0 if self._metric is None else self._metric.live_payload_bytes)

    def close(self):
        if self._metric is not None:
            self._metric.close()
        self._metric = self._operator = self._objective = self._regularizer = self._jacobian = None
        self.q = self.root = self.u = self.diagonal = None
        self._closed = True
        self.record['disposed'] = True
