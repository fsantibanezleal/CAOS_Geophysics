# M04 forward test-first and independent validation

Protocol: tolerances fixed before candidate code. Independent execution of the
forward component reports 176 passing tests with no skips at source c3f9d73;
this does not establish survey inversion, field validity or online admission.
The exact ten named requirements map to tests/numerics/test_magnetic_forward.py.

## Independent physical controls

Use nonuniform multi-cell meshes with sparse activity and irregular receivers
above and laterally outside the source volume; include off-origin asymmetric
prisms. Separate direct Choclo0.3.2 evaluation uses its explicit six bounds and
mu0-consistent induced M, never candidate private helpers or candidate G.
Compare each ENU component and projected TMI at atol1e-7 nT, rtol2e-8.
Each unit-SI susceptibility Jacobian column uses a mathematical chi=1 in one
independently specified prism, zero in the others, with M=B0(T)/mu0 A/m.
Use Choclo0.3.2's actual VACUUM_MAGNETIC_PERMEABILITY for both the conversion
and its physical kernel; convert returned tesla to nT once and project with
the independently specified ENU field direction. Compare the candidate column
at the existing atol1e-7 nT per SI, rtol2e-8. This is a mathematical linear
derivative control, not an eligible chi=1 production input or a claim that
self-demagnetization is negligible there. Never substitute unscaled1 A/m or
submit chi=1 to the operator's0.1-limited request.

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
enough to avoid subtraction cancellation, atol1e-7 nT/rtol2e-8.

### Portable independent tiny-magnitude algebraic oracle

Use only stdlib Decimal in localcontext with prec=80 and ROUND_HALF_EVEN.
Convert every finite built-in binary64 float in F, B0 and b separately with
Decimal.from_float, not Decimal(str(value)) or a float norm cast afterward.
Compute s=sum((Decimal.from_float(B0[a])+Decimal.from_float(b[a]))**2 for
a in[0,1,2]); oracle=s.sqrt()-Decimal.from_float(F), entirely in that context.
Do not use the candidate's rationalized expression, helpers, direction
conversion or Windows longdouble. This independently validates scalar algebra;
it does not replace Choclo/volume quadrature as the physical component oracle.

Freeze F=50000.0 nT and exact cardinal B0=(0.0,50000.0,0.0) nT. The declared
tiny controls are b=(+1e-4,0.0,0.0),(-1e-4,0.0,0.0),(0.0,+1e-10,0.0),
(0.0,-1e-10,0.0) nT, plus b=(0.0,0.0,0.0). These are explicit algebraic
controls, not invented field readings or new Choclo kernel results. The exact
cardinal B0 also avoids a baseline error from rounding a noncardinal unit vector.
The two transverse references are equal and positive, approximately1e-13 nT;
the parallel references preserve their respective signs and the null is exactly0.
Calculate each actual reference independently at80 digits, rather than treating
the displayed approximation as truth. Compare the finite binary64 candidate
value converted with Decimal.from_float against that reference: for each
nonzero reference require its sign, candidate!=0 and
abs(candidate_decimal-oracle)<=Decimal('2e-8')*abs(oracle). This retains the
frozen relative tolerance and uses zero absolute allowance ONLY for these named
tiny controls, so an erroneous zero cannot pass under the ordinary1e-7 nT floor.
For the null control require candidate==0 and oracle==0 exactly. Ordinary
magnitude, Choclo component/Jacobian, quadrature, far-field and G@chi tolerances
above remain unchanged. There is no platform-dependent oracle skip or fallback.

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

The named test_geometry_order_and_immutability and test_runtime_output_and_scope gates
verify independently owned C-order snapshots, OWNDATA=true/base=None,
WRITEABLE=false at return, unchanged caller flags/bytes and no shared memory
between any numeric outputs or inputs. Ordinary indexed writes fail while the
flag is false. A separate isolated returned snapshot must demonstrate that its
owner can reenable WRITEABLE and mutate it without changing any input or sibling
array. That reversible flag is expected behavior, not an immutability failure.
No dictionary freezing, tamperproof array or durable storage is asserted by
these tests. Persisted bytes/hashes/contracts remain separate future gates.

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
