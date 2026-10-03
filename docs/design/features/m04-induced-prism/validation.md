# M04 forward test-first and independent validation

Status: all proposed gates NOT_RUN. Tolerances fixed before candidate code.
The exact ten named requirements map to tests/numerics/test_magnetic_forward.py.

## Independent physical controls

Use nonuniform multi-cell meshes with sparse activity and irregular receivers
above and laterally outside the source volume; include off-origin asymmetric
prisms. Separate direct Choclo0.3.2 evaluation uses its explicit six bounds and
mu0-consistent induced M, never candidate private helpers or candidate G.
Compare each ENU component and projected TMI at atol1e-7 nT, rtol2e-8.
Unit susceptibility Jacobian columns use independent physical unit-M oracle;
they do not submit chi=1 to the operator's0.1-limited request.

Independent tensor-product Gauss-Legendre volume dipole integration uses16,24,
32 nodes per axis on smooth distant exterior controls (distance from centre at
least1.5 times largest cell diagonal). Require24-versus32 convergence first at
atol1e-8 nT, rtol2e-8; compare analytic result at atol1e-7 nT, rtol2e-8.
Do not loosen quadrature tolerance, move a failed receiver or count a nonconverged
quadrature as an oracle. A separate far-field dipole uses receiver distance>=20
largest cell dimension, relative discrepancy<=0.003 where signal is nonzero.

Null chi, scaling chi within0..0.1, field amplitude scaling, cardinal/noncardinal
angles, asymmetric sign lobes, active permutation and receiver permutation
controls verify actual physics/order. G@chi versus actual dpred: atol1e-10 nT,
rtol1e-12. Exact magnitude uses independent direct vector norm for cases large
enough to avoid subtraction cancellation, atol1e-7 nT/rtol2e-8; tiny cases use
long-double arithmetic oracle where independently supported, not a cast claimed
more accurate on Windows when its longdouble equalsfloat64.

Construct a fixed remanent prism M not parallel to f via direct Choclo and
retain its difference from the induced prediction. A wrong-field orientation
likewise changes the modeled data. No inverse optimization/field classification
is claimed by these counterexamples. A physical inverse negative remains a later
parent M04 gate, explicitly pending.

## Contracts, failure and scope

All cap/+1, exact dict/key/type/enum, float32/array-subclass/bool/int field,
nonfinite, width/edge/volume-collapse, source-interior/face/edge/inactive/zero-chi,
runtime, malformed kernel shape/dtype/nonfinite and output ownership negatives
must fail literally. A patched engine call is only a deterministic negative;
positive physics uses actual unmodified engines. Oversize metadata rejection
must precede finite scans/snapshots/engine constructor, observed by trap tests.

Source/runtime audit compares installed files to research pins externally, with
the additional actually used Geoana/discretize/SimPEG base and source-map pins
from the accepted M02 runtime audit. Keep framework attribution separate from
new execution. AST scope prohibits CLI/application I/O/optimizer/vendor edits;
ordinary errors are not advertised as safe HTTP payloads.

## Execution and review

Persist source/tests before each real execution; use the existing read-only
pipeline interpreter, -B, explicit candidate PYTHONPATH, one-thread environment
and new private cache/JUnit/output roots. Retain first RED, all scientific
failures and full exact commands/versions/pins/resource metrics. No existing
receipt/log/output overwrite or environment install. MAIN independent candidate
review/replay and peer exact-head read precede PR promotion. No skipped oracle
becomes PASS, no method matrix count replaces these actual gate outcomes.

Cold/warm nominal and upper allocation tests are separate prospective measurements,
not dangerous uncontained controls authorized by this SDD. Native Job/cgroup,
memory floor, CPU/timeout/crash/resource admission and VPS deployment remain
CLOSED until their own concrete reviewed mechanisms and actual-host gates pass.
