# Public original-source phase allocation consumer

## Requirements

R-485 WHEN planning an original linear magnetic fit, THE M04 adapter SHALL call
the public `magnetic_original_optimizer.allocation_plan` with the actual whole
source, likelihood and parameter counts, original noise kind, original preflight
bytes and observation components. It SHALL retain the returned closed source
plan without subtracting bytes or calling private phase helpers. The actual
native DTO, factory and terminal owner still verify simultaneous allocations.
Gate: `tests/data/test_magnetic_public_phase_allocation.py::test_exact_public_plan_is_delegated_without_local_arithmetic`.

R-486 IF the public plan has an unknown schema/member, changed literal identity,
quota, source binding, epoch or policy, THEN THE adapter SHALL refuse before
kernel construction or fitting. Old source epochs and receipts SHALL remain
distinct; no historical refusal is promoted to the new epoch.
Gate: `tests/data/test_magnetic_public_phase_allocation.py::test_changed_public_contract_refuses_before_fit`
and `tests/data/test_magnetic_public_phase_allocation.py::test_old_epoch_receipt_is_not_upgraded`.

R-487 BEFORE a new frozen workflow launch, THE allocation prerequisite SHALL
check every inner/final geometry-only fit size through this same public seam,
including the original 216-row/648-component final refit. Original limits remain
805306368 bytes, uninterrupted fit wall120s, accepted200, CG200 and LS20. A
source/allocation-only pass SHALL not imply fitted accuracy or native admission.
Gate: `tests/data/test_magnetic_public_phase_allocation.py::test_original_frozen_request_all_phases_without_kernel_or_child`
and `scripts/check_magnetic_original_workflow_allocation.py`.

## Design

The prospective dependency is the original-only public source at commit
`97cf928412609ed7437fe24d22a3b7639137b34c`. It replaces three original-source
modules within the existing thirteen-library closure. The public allocation
schema is `magnetic-original-allocation-2`, including `owned_source_phases`.
The consumer binds the complete returned dictionary, including its public
source hashes and current original epoch/policy, to the existing objective and
budget digests. It neither copies the phase formula nor infers permission from
RSS. The original source owner retains operand/backing/alias validation and
fresh terminal face/factor/witness/audit checks before allocation.

The public original planner separates its actually executed certificate phase
from the generic certificate workspace. The native reserve and setup/action
dictionaries remain unchanged. This consumer makes no independent claim that
those phases are disjoint; it consumes the public owner's versioned contract.
Native H/g, original SD or stored covariance, regularization, beta, bounds,
starts, proof arithmetic and independent precision thresholds are unchanged.

Reuse the corrected seven-module observation dependency without replacing
current observation source bytes with old reference copies. Prospective CLI
selection recognizes only the current public original epoch, while historical
records remain readable evidence rather than fit authority. No nonlinear,
coupled, field, Linux host, API mount or release eligibility is introduced.

## Tasks

1. Persist this precode before implementation (R-485 through R-487).
2. Colocate the exact three public replacements for reproducible qualification;
   integration uses their owner pin, never an edited numerical substitute.
3. Delegate allocation and reject contract/identity/source drift (R-485/R-486).
4. Test actual frozen geometry counts with no kernel, solver or child (R-487),
   including invalid types, covariance512 and oversize refusal controls.
5. Only after changed public exact-arithmetic controls and the shared timed
   lane are qualified, execute the original complete final fit and independent
   precision prerequisite. Only its pass permits a new frozen full matrix.
   Source-only controls are not that numerical or native proof.

## Consumer qualification boundary

The closed consumer protocol has 79 passing, zero-skipped controls, including
the complete retained frozen geometry's 144-row inner folds and 216-row final
refit, source/plan drift and historical-epoch refusal. Five additional literal
quota controls pass without building a kernel. The actual CLI planner returns
690057120 bytes for 432 likelihood components and 723407520 for 648, with the
same full native reserve 633176064 and admitted ceiling 805306368.

The prospective request changes only `policy.optimizer_binding`; the old
request and every datum remain unchanged. Original-byte verification, fitting,
independent precision, native process containment, field science, complete
matrix and mounted protected result acceptance are not established by this
geometry-only receipt. Independent original source arithmetic and actual final
fit gates remain mandatory before downstream execution.
