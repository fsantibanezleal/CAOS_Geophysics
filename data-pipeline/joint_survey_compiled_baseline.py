"""Source-bound original single-property baseline through the public compiler.

This independent adapter does not change the active26-fit worker, physical
potential/H/g, coupled objective, original assertions or scientific admission.
Its closed allocation is a declaration, not OS reservation or retained-framework
structural qualification. Original independent resource/accuracy gates remain.
"""
from dataclasses import asdict, dataclass, field
import hashlib
import inspect
import math
from pathlib import Path
from time import monotonic

import numpy as np

import joint_survey_optimizer as original
import joint_survey_plan as planner
import joint_survey_resources as resources
import physical_compiled_optimizer as public


PUBLIC_COMMIT = 'f3022ef999b79004faa45e54c33adb3fdc9e0441'
SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
_NATIVE_NAMES = ('joint_survey_optimizer', 'joint_survey_compiled', 'joint_survey_objective',
    'joint_survey_plan', 'joint_survey_structure', 'joint_survey_resources', 'gravity_forward', 'magnetic_forward')
_LOADED_NATIVE = {name+'.py': hashlib.sha256((Path(original.__file__).parent/(name+'.py')).read_bytes()).hexdigest()
    for name in _NATIVE_NAMES}
PINS = {
    'physical_compiled_optimizer.py': '1554320f49012062b523e7a2d6d02baf0cf54ca18ec5c47efaee48c39194e7ab',
    'physical_conditioned_optimizer.py': '1342ade648175f89ee5e2aeb802ab56dbe18e2272c6c3f0ff293a8aab4267b9c',
    'physical_nonlinear_optimizer.py': '772c4de0b7747bbc9075b6fbf1357b04de752bfd900f88c9a5ddead2a91931fd',
    'physical_optimizer.py': '4745d41ff8afb908260611601861db8303ce7bd612ff0ea614cceb201a20bc86',
    'physical_original_quadratic.py': '07c67519110d59758614516a3f3d98ed49713a969affcefb4711430b604186ce',
    'physical_original_residual_terminal.py': 'a9bf32a6c4e932d7d4efa1f38540778e2993f74982adb9f29985d921ecb5ddf7',
    'physical_original_rows.py': '8a18a0ae04bfd09336480e06d2e9526aecab79a232033e9ca5d0040b16e9f399',
    'physical_original_terminal.py': 'dd4b07defa6921a173d3e4d75dad28697fa36743a5dccef6f5db815ae6a73991',
    'physical_owned_spd.py': '5c54937bee748011b029653d138694de31a6b3123e05d29ceeddcf2e8f76d16e',
    'physical_reduced_optimizer.py': '22bf04a7e260b5f93c2e54430f54c3d3464150b3ce78d861c8236bc3d6b21aad',
    'gravity_l2_metric.py': 'd09a2b4630258d2c26a1a82ea92a3cd79b42143695d3e630d5252df5ba8dfe8b',
    'gravity_l2_precision.py': '57727cac9ab6550eab902d20d6c43e662be8f9fac406896c6797d1e29b3e7c1a',
}
_NATIVE_VENDOR_PINS = (
    (original.CrossGradient, '85ff1c1e39ec9e8973707a7debd83706db23027b13832298c4e468b052e3298c'),
    (original.RegularizationMesh, '942ac3fffded92f48c7a5294575082713ebde716918d0e8fbe117c084607ff8f'),
    (original.BaseSimilarityMeasure, 'aae7dbd3cb4887246f38c8ceba4fe8fbeeb5592110341635e06fdb70246a92b5'),
    (original.maps.Wires, '6bdd7455d17467ed547091526735df560a35c9b204ab2f4105dfab096ed6c90e'),
    (original.TensorMesh, '2e8a97a5449f490dbf4128c8696833a8770c896d260f5ecf087e2f622b3be65d'),
    (original.DiffOperators, 'f3c7ca3c54a50232202d08bf9768411273fcee7ce95eb5b110a79de6c42db70a'),
)


@dataclass(frozen=True, slots=True)
class _FitBudget:
    """Owned absolute120s view; never rewrites/restarts the workflow budget.

    Constructed by solve_original_baseline before inventory or allocation. It
    is not a caller proof, resource certificate or hard-realtime interruption.
    Every inherited native action uses this view's checkpoints; public proof
    receives the SAME absolute deadline, not a fresh clock after construction.
    """
    workflow: resources.JointResourceBudget
    workflow_started: float = field(init=False)
    workflow_deadline: float = field(init=False)
    started: float = field(init=False)
    deadline: float = field(init=False)

    def __post_init__(self):
        if type(self.workflow) is not resources.JointResourceBudget:
            raise TypeError('M11: actual original measured workflow budget required')
        started = monotonic()
        original_start, original_deadline = self.workflow.started, self.workflow.deadline
        if (type(original_start) is not float or type(original_deadline) is not float
            or not math.isfinite(original_start) or not math.isfinite(original_deadline)
            or original_start > started or resources.MAX_SECONDS != 1800.
            or original_deadline != original_start+1800.):
            raise ValueError('M11: original uninterrupted workflow clock required')
        object.__setattr__(self, 'workflow_started', original_start)
        object.__setattr__(self, 'workflow_deadline', original_deadline)
        object.__setattr__(self, 'started', started)
        object.__setattr__(self, 'deadline', min(original_deadline, started+120.))

    def _workflow_clock(self):
        if (self.workflow.started != self.workflow_started or self.workflow.deadline != self.workflow_deadline
            or type(self.workflow.started) is not float or type(self.workflow.deadline) is not float
            or resources.MAX_SECONDS != 1800.):
            raise RuntimeError('M11: original workflow clock changed during fit')

    def checkpoint(self):
        self._workflow_clock()
        if monotonic() > self.deadline:
            raise RuntimeError('M11: original baseline fit deadline')
        self.workflow.checkpoint()
        self._workflow_clock()
        # RSS/scratch sampling is actual work and cannot reset or escape120s.
        if monotonic() > self.deadline:
            raise RuntimeError('M11: original baseline fit deadline')


def _source_checkpoint(clock):
    if clock is not None:
        if type(clock) is not _FitBudget:
            raise TypeError('M11: owned original fit clock required')
        clock.checkpoint()


def _source_digest(path, clock):
    _source_checkpoint(clock)
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    _source_checkpoint(clock)
    return actual


def _check_native_sources(clock=None):
    if _source_digest(Path(__file__), clock) != SOURCE_SHA256 or any(
        _source_digest(Path(original.__file__).parent/name, clock) != pin
        for name, pin in _LOADED_NATIVE.items()
    ):
        raise RuntimeError('M11: loaded/disk native compiled source drift')


def source_inventory(clock=None):
    """Complete reviewed loaded/disk closure, not a branch-name grant."""
    _check_native_sources(clock)
    _source_checkpoint(clock)
    planner._runtime()
    _source_checkpoint(clock)
    # Same native closure as the legacy inventory, but EVERY defining-file
    # action is guarded. No callback/monkeypatch of the original routine.
    nonlinear = original.solver
    actual = _source_digest(Path(nonlinear.__file__), clock)
    vendor = _source_digest(Path(original.optimization.__file__), clock)
    if (actual != PINS['physical_nonlinear_optimizer.py'] or nonlinear.SOURCE_SHA256 != actual
        or vendor != '0ac858cc310b32bb9aa59c78aaaa9c79b5f28438db52fb06ec73d976b63196a4'
        or nonlinear.VENDOR_SOURCE_SHA256 != vendor
        or nonlinear.RUNTIME_EPOCH != 'physical-gncg-nonlinear-candidate-2'
        or nonlinear.POLICY != 'exact-bound-native-gncg-actual-armijo-1'):
        raise RuntimeError('M11: unreviewed native nonlinear source or policy')
    inventory = {'physical_nonlinear_optimizer.py': actual, 'simpeg.optimization': vendor}
    for target, expected in _NATIVE_VENDOR_PINS:
        _source_checkpoint(clock)
        actual = _source_digest(Path(inspect.getsourcefile(target)), clock)
        if actual != expected:
            raise RuntimeError('M11: defining structural source drift')
        inventory[target.__name__] = actual
    _source_checkpoint(clock)
    defining = Path(inspect.getsourcefile(original.RegularizationMesh.cell_gradient.fget))
    actual = _source_digest(defining, clock)
    if actual != '5283b4f854906aeb05c216ff1c83174c99a7c53fe6a3ce8227b8ea483e785f44':
        raise RuntimeError('M11: defining regularization mesh drift')
    inventory['RegularizationMesh.cell_gradient'] = actual
    inventory.update(_LOADED_NATIVE)
    modules = (public, public.source, public.original_terminal,
        public.original_terminal.exact_rows, public.residual, public.reduced,
        public.reduced.core, public.reduced.core.linear, public.reduced.core.nonlinear,
        public.source.owned, public.source.owned.kernel, public.source.owned.intervals)
    seen = set()
    for module in modules:
        path = Path(module.__file__)
        actual = _source_digest(path, clock)
        if PINS.get(path.name) != actual or getattr(module, 'SOURCE_SHA256', actual) != actual:
            raise RuntimeError('M11: unreviewed compiled public source')
        if path.name in seen:
            raise RuntimeError('M11: duplicate compiled dependency identity')
        seen.add(path.name)
        inventory[path.name] = actual
    if seen != set(PINS) or (
        public.LINEAR_EPOCH != 'physical-gncg-compiled-original-residual-candidate-1'
        or public.POLICY != 'closed-compiled-identity-half-native-free-face-residual-accuracy-1'
    ):
        raise RuntimeError('M11: incomplete compiled closure or changed policy')
    inventory[Path(__file__).name] = SOURCE_SHA256
    _source_checkpoint(clock)
    return inventory


class JointCompiledBaseline(original.JointOptimizerObjective):
    """Literal A/d/R/unscaled-J DTO; native evaluation and H/g are inherited."""
    def __init__(self, problem, modality, beta, stage, inventory, budget):
        budget.checkpoint()
        planner._enum(modality, ('gravity', 'magnetic'), 'compiled-baseline.modality')
        if type(beta) is not float or beta not in original.objective.BETAS:
            raise ValueError('M11: original frozen scientific beta required')
        if type(stage) is not int or not 0 <= stage <= 25:
            raise ValueError('M11: original stage index required')
        weights = {'beta_gravity': beta if modality == 'gravity' else .0001,
            'beta_magnetic': beta if modality == 'magnetic' else .0001, 'coupling': 0.}
        sl = slice(0, problem.n) if modality == 'gravity' else slice(problem.n, 2*problem.n)
        # Only the public count-derived allocation closes this placeholder.
        super().__init__(problem, weights, problem.start[sl], stage, inventory,
            {'allocation_plan_sha256': '0'*64}, budget, modality)
        budget.checkpoint()
        self._identity.update(mode='fixed_linear_quadratic', runtime_epoch=public.LINEAR_EPOCH)
        self.active_indices = np.flatnonzero(problem.plan['mesh']['active'])
        budget.checkpoint()
        self.mesh_shape = tuple(len(problem.plan['mesh'][key]) for key in ('hx_m', 'hy_m', 'hz_m'))
        retained = (*planner._arrays(problem.development), *problem.A.values(), *problem.d.values(),
            problem.scales, problem.lower, problem.upper, problem.start, problem.reference,
            problem.geometry['active_cell_bounds_m'], problem.geometry['active_cell_centres_m'],
            problem.geometry['active_cell_volumes_m3'], problem.R.data, self.active_indices)
        # Native int32/bool structural arrays are not coerced into this f64/i64 tuple.
        self.retained = public.RetainedCompiledProblem(
            (problem.J['gravity'], problem.J['magnetic']), tuple(retained))
        budget.checkpoint()
        self.allocation = public.allocation_plan(self.compiled_operands(self.start),
            self.identity(), self.start, self.retained)
        budget.checkpoint()
        self._identity['allocation_plan_sha256'] = self.allocation['allocation_plan_sha256']
        closed = public.allocation_plan(self.compiled_operands(self.start),
            self.identity(), self.start, self.retained)
        budget.checkpoint()
        if closed != self.allocation or self.identity()['allocation_plan_sha256'] == '0'*64:
            raise RuntimeError('M11: compiled allocation rebinding changed')

    def components(self, q):
        data, penalty, _, _ = self._state(q)
        return {'phi_d': data, 'phi_m': penalty, 'phi_engine': data+penalty}

    def compiled_operands(self, q):
        self.budget.checkpoint()
        _check_native_sources(self.budget if type(self.budget) is _FitBudget else None)
        planner._array(q, (self.n,), 'compiled-baseline.q')
        planner._finite(q)
        p = self.problem
        return public.CompiledQuadraticOperands(public.source.owned.binding_for(self.identity(), q),
            p.A[self.modality], p.d[self.modality], p.R, p.reference[self.slice],
            p.lower[self.slice], p.upper[self.slice], self.weights['beta_'+self.modality],
            p.J[self.modality], self.active_indices, self.mesh_shape)

    def retained_compiled_problem(self):
        self.budget.checkpoint()
        return self.retained


def solve_original_baseline(problem, modality, beta, stage, budget):
    """Actual native baseline; no oracle, refit, fallback or coupled admission.

The offline caller must first qualify the source-bound original compiler
structural/resource closure and independent case gates. This entry point does
not promote source controls into such acceptance or alter the existing worker.
"""
    if type(budget) is not resources.JointResourceBudget:
        raise TypeError('M11: actual original measured workflow budget required')
    clock = _FitBudget(budget)
    clock.checkpoint()
    inventory = source_inventory(clock)
    adapter = JointCompiledBaseline(problem, modality, beta, stage, inventory, clock)
    clock.checkpoint()
    identity = adapter.identity()
    spd = public.source.owned
    binding = public.ConditionedBinding('physical_compiled_optimizer.solve_bounded_linear',
        public.SOURCE_SHA256, spd.SOURCE_SHA256, spd.KERNEL_SHA256,
        public.VENDOR_SOURCE_SHA256, public.source.SOURCE_SHA256,
        identity['source_inventory_sha256'], public.LINEAR_EPOCH, public.POLICY)
    declared = public.ConditionedBudget(clock.deadline, 200,
        resources.MAX_RSS, adapter.allocation['admitted_bytes'], adapter.allocation['allocation_plan_sha256'])
    terminal = spd.TerminalPolicy(1e-5, model_error_limit=1e-5,
        objective_gap_limit=1e-10, physical_prediction_error_limit=1e-8)
    clock.checkpoint()
    result = public.solve_bounded_linear(adapter, problem.lower[adapter.slice], problem.upper[adapter.slice],
        problem.start[adapter.slice], budget=declared, binding=binding, terminal=terminal)
    clock.checkpoint()
    if source_inventory(clock) != inventory:
        raise RuntimeError('M11: original compiled source inventory changed during fit')
    clock.checkpoint()
    return {'schema': 'joint-compiled-baseline-1', 'stage': stage, 'modality': modality, 'beta': beta,
        'identity': identity, 'source_inventory': inventory, 'optimizer_binding': asdict(binding),
        'allocation_plan': adapter.allocation, 'terminal_policy': asdict(terminal), 'result': result,
        'retained_framework_resource_acceptance_verified': False,
        'coupled_inversion_performed': False, 'scientific_acceptance_verified': False, 'public_activation': False}
