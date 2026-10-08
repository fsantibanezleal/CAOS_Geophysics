# Bounded same-operand objective enclosure reuse

This amendment precedes implementation. It changes no objective, optimizer,
physical operand, precision ladder, sign predicate, tolerance, deadline or cap.
Existing running source inventories and historical receipts remain unchanged.
Reuse belongs to one already frozen MagneticCertificate instance, never a
global cache, returned kernel snapshot, external model oracle or Decimal matrix.

## Requirements

R-E01 WHEN an objective is recomputed at the bit-identical native model with
the same explicit precision inside one frozen certificate, THE certificate
SHALL reuse only its completed directed scalar objective endpoints. Gate:
tests/numerics/test_magnetic_enclosure_reuse.py::test_bit_identical_scalar_reuse.

R-E02 THE cache SHALL retain at most two owned readonly model vectors and three
precision entries per vector, with its conservative memory charge admitted
before operand snapshots. Gate:
tests/numerics/test_magnetic_enclosure_reuse.py::test_two_model_bound_and_charge.

R-E03 IF a clock/domain failure occurs during objective construction, THEN THE
cache SHALL not retain that partial objective and the certificate SHALL preserve
its existing cleared refusal. Hits SHALL still check the original deadline.
Gate: tests/numerics/test_magnetic_enclosure_reuse.py::test_expiration_and_partial_refusal.

R-E04 WHEN caller arrays, returned snapshots, a trial model or another fixed
surrogate differ, THE cache SHALL not adopt another model's endpoints. Gate:
tests/numerics/test_magnetic_enclosure_reuse.py::test_mutation_and_instance_isolation.

R-E05 THE cached and independently uncached certificates SHALL return identical
complete records, including all34/50/80 passes, strict projected slope/Armijo
and unresolved cases. Gate:
tests/numerics/test_magnetic_enclosure_reuse.py::test_uncached_record_parity,
tests/numerics/test_magnetic_inverse_precision.py and
scripts/run_magnetic_frozen_matrix.py original full288row/528cell receipts.

## Design and soundness

The frozen instance already owns the stored binary64 kernel/background/noise
chain/reference/bounds/beta/vendor fixed-surrogate derivative and weights.
Its explicit-context objective is deterministic for model bits and precision.
Therefore an already completed interval at that identical pair encloses the
same real objective as reevaluation; no rounded normal matrix or approximate
float value replaces the interval. Slope/chord/margin are still computed fresh
for every invocation, including changed gradients/counters/native diagnostics.
Each sparse surrogate constructs a separate instance; no cross-surrogate reuse.

Use two least-recently-used model slots. Each key is an owned C-order float64
copy, matched through its uint64 bit view (signed zero cannot alias). Values
are immutable lower/upper Decimal scalar pairs keyed only by explicit precision
34/50/80. Validate bounded finite ordered endpoints and check the clock before
publishing an entry. A cache hit checks the clock again, without refreshing it.
Failed partial computation never creates an entry. Previously completed scalar
entries are not acceptance proofs and cannot bypass the fresh certificate.

Charge16*a bytes for two native vectors plus24576bytes conservative Python
container/at-most12 bounded scalar Decimal endpoints. At original a<=2048 this
is at most57344bytes, not a new dense matrix. Add that charge to the existing
certificate preallocation estimate before any owned snapshot. The overall
805306368byte rejection limit and existing wrapper reservation remain fixed;
do not subtract estimated savings, increase scratch/audit limits or relabel
native memory observations as allocation admission.

## Tasks and non-goals

1. Add named bit-key/bounded/expiry/independent uncached parity controls (R-E01..05).
2. Implement two-slot scalar memoization with explicit preallocation (R-E01..04).
3. Preserve independent Decimal160 and rational full-objective checks (R-E05).
4. Measure fresh full original fits/matrix and native lifetime receipts (R-E05).

No private/copied CG, public M02 change, contact nonlinear invention, field datum
inference, proof truncation, higher deadline/accepted-step/CG/LS cap or scientific
tolerance weakening. A faster certificate can still leave the full fit failed.
API/UI/mount/Linux/public promotion/deployment gates remain separate.
