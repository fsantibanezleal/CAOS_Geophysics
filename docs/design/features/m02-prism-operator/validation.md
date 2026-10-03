# Ordinary prism operator exact planned gates

Status: local ordinary-operator controls executed; independent pinned code/test
review pending. The original gate policy below was frozen before implementation.
Actual receipts and literal scope limits are in the implementation section.
Protocol: [design](design.md). Requirements: [requirements](requirements.md).

## Frozen gate mapping

| Requirement | Planned test in `tests/numerics/test_gravity_forward.py` | Locked evidence/negative |
| --- | --- | --- |
| P02-01 | `test_exact_protocol_and_types` | Six/nested exact keys; ndarray subclass/float32/complex/list/object, invalid tuple/enums, missing/extra fields reject before engine |
| P02-02 | `test_geometry_counts_and_frame` | n=1/2048 admitted, n=0/2049 reject; N=4096 cap and >cap reject; all-inactive, collapsed/nonfinite edges, zero/negative widths/volume and wrong frame reject |
| P02-03 | `test_receiver_outside_volume_policy` | Interior/face/edge/corner rejects, zero density/inactive air does not exempt; above/below/lateral strictly outside accepted; no numerical receiver shift |
| P02-04 | `test_xfast_activity_and_input_immutability` | Nonuniform 2x3x2 cells, distinct signed values and sparse activity; explicit six-bound Choclo columns; C/F inputs unchanged, no memory alias |
| P02-05 | `test_actual_required_engine_and_precision` | Observe actual official fields/G call, Geoana selected, dtype64 at construction, RAM/no multiprocess; injected wrong dtype does not pass by cast |
| P02-06 | `test_sign_units_linearity_and_jacobian` | kg/m3-to-g/cc, J/1000, +/negative/zero rho, doubling, adjoint and finite-difference derivative in physical units |
| P02-07 | `test_independent_choclo_prisms`; `test_volume_quadrature_and_physical_limits` | Separate prism and numerical volume integration; sphere, point-mass sign/amplitude/r-distance; no engine-own-oracle |
| P02-08 | `test_output_protocol_and_engine_failures` | Six exact output/nested keys, dtype/shapes/finite readonly copies; fake/failed/nonfinite engine rejected; p=Jrho state identity |
| P02-09 | `test_runtime_epoch_and_external_source_pins` | Required loaded versions and external manifest SHA audit; wrong version/hash/binary epoch blocks acceptance, no fabricated operator source SHA |
| P02-10 | `test_no_io_hooks_or_inverse_behavior` | No callable/hook/path/backend args, optimizer/CLI/API imports or application I/O; RAM official path with disk/file/network writes denied in test harness |
| P02-11 | `test_negative_controls_and_literal_scope` | Exact field/unit/sign/factor-source failures and null result; absence of residual/WRMS/eligibility/inverse-convergence outputs |

Planned tests are distinct from main's approved physics principles. Tests may
instrument engine calls/errors as ordinary test isolation; production has no
callback or injection hook. Dependency pin auditing is external read-only
review/harness work, not added application I/O. It must report its actual audit
tool/command, source revisions and manifest hash rather than copy old receipts.

## Fixed deterministic ordinary cases

No RNG, training, inverse seeds, candidate beta or epsilon in this unit.
First single prism: origin (-50,-50,-100) m; widths (100),(100),(100) m;
active true; density +1000 kg/m3. Receivers (0,0,100), (100,50,120),
(-170,30,220) m. Repeat at -1000, zero and +2000 densities.
Verify upward-negative response above the positive body and J independent of rho.

Nonuniform mapping case: origin (-140,-180,-260) m; hx=(40,70), hy=(30,50,90),
hz=(60,110) m; active full indices (0,2,3,7,11); density
(400,-600,900,-300,1200) kg/m3 in that order. Receivers
(0,0,100), (230,-50,40), (-400,60,-350), (70,260,-150) m.
Compute oracle bounds from x-fast index, never recover them from production G.
Other production sign/unit/state comparisons use these fixed cases, not synthetic
geology scores. Cap tests use repeated receivers and bounded widths/density;
receipt distinguishes pure geometry admission from allocated/engine execution.

## Frozen proposed forward tolerances

- Geoana versus independent Choclo: rtol 1e-7, atol 1e-10 mGal, all ordinary
  case receivers strictly outside source box. Retain unexpected near-boundary
  failures, no implicit exclusion beyond the declared geometry policy.
- Scaling/unit/prediction-versus-Jrho: rtol 1e-10, atol 1e-12 mGal;
  density finite-difference derivative relative 1e-6 across several nonzero
  perturbation sizes, plus adjoint dot identity relative 1e-10.
- Three-level independent volume quadrature refinement away from source:
  relative 1e-5; point mass at >=100 largest body dimensions relative 1e-3
  with inverse-square ratio. Independently test the volume integrator on an
  analytic sphere in spherical coordinates to relative 1e-5, then use rectangular
  cell integration as the actual operator oracle. Do not demand equality of
  a coarse voxelized sphere to a continuous sphere or treat it as a new supported
  production geometry.
- SI Newtonian G=6.67430e-11 m3/(kg*s2) must agree with pinned SciPy/Choclo
  constants before amplitude acceptance. No refit of G to make engines agree.
- Output geometry/unit/shape/active mapping/immutable pin identity is exact,
  not waived under prediction tolerance. Boundary errors have no tolerance that
  moves a receiver across the source volume.

No threshold change after a failure, hidden float32 path, substituted engine,
seed replacement, field badge or canonical rewrite. All negatives are named
rejection tests, not reconstructed models. Float64 forward success is neither
optimizer validation nor proof of density identifiability.

## Execution/independent review sequence

1. Main fully reads exact protocol, shape/cap/boundary, source/runtime and
   no-I/O ownership scope before authorizing code.
2. Implement only the two named new paths after that authorization; metadata
   source checks remain external. No legacy hooks or new install/CLI scripts.
3. Run exact-source fast tests and required engine/oracle cases locally; record
   command, operator/test/tool revision hashes, runtime/pin manifest identity,
   actual outputs/dtypes and every rejected/error condition.
4. Main independently reviews actual code and reproduces ordinary cases/source
   checks. Broader survey/inverse/field gates remain pending and unclaimed.

At the docs-only design milestone the scientific gate count was zero executed.
Documentation checks cannot
close P02 requirements or mark M02 accepted. Full product convergence ledger,
historical negative fixtures and original private FWI backup/candidates/receipts
remain unchanged.

## Executed docs/source audit only, 2026-10-03

On base `bc0c573daa511ba897dd0b21e315b8c1eef67413`, five new feature files staged:

```text
python scripts/check_content_standards.py
python scripts/check_template_residue.py
python scripts/check_ci_budget.py
python scripts/check_sdd_convergence.py
git diff --cached --check
```

All commands exited zero. Stdlib inline read-only self-audit checked
all eight recorded package versions and 20 targeted installed module/binary
digests; valid pin JSON; five-path new-folder-only scope; all six merged PR120
docs unchanged; 11 EARS requirements / 12 distinct planned nonexistent gates;
13 existing relative links; no banned scoped content. Pin manifest SHA256:
`a5aa08c23a80e15024e6499fab6805315d52dee185c5de1010b5f46e5c9f5819`.
These are source inspection, not numerical results or a full environment audit.

Private backup presence remains 137 files / zero tracked; backup and experiments
remain ignored and untouched. Product ledger structure still reports one failure,
18 unresolved. No numerical/gate result changed. Actual operator/test files
did not exist at the docs-only audit. Subsequent main approval is recorded in
tasks at design head `361b66f`; independent code acceptance is still pending.

## Historical ordinary implementation before geometry correction

The following 66/104/164 results and hashes belong to the earlier source,
not the corrected final implementation. Preserve this receipt byte-for-byte.

Local machine receipt: [evidence/local-execution.json](evidence/local-execution.json).
Only two new scientific/test paths are implemented. No threshold, cap, engine,
source epoch or approved fixture was changed. Errors/cause chains remain private
caller context, not safe HTTP payloads. No full inverse/M02/field/host/GPU claim.

Operator SHA256:
`94c2bd2a8ea626b55b0e7954c48eedecf09f2d5becbb4793fb969ea865173d30`.
Test SHA256:
`897c99a395c4f9c14fe28019abf2732910cb2e5ec7a44ba85bfcd1c83c44ad91`.
Reviewed runtime-pin manifest remains byte-identical at
`a5aa08c23a80e15024e6499fab6805315d52dee185c5de1010b5f46e5c9f5819`.
Later documentation/receipt edits must not be confused with changed code bytes.

Exact existing interpreter, READ-ONLY, no creation/upgrade:
`D:\_Repos\_Web_Projects\CAOS_Geophysics\.venv-pipeline\Scripts\python.exe`.
Set process-only `PYTHONDONTWRITEBYTECODE=1`, `OPENBLAS_NUM_THREADS=1`,
`OMP_NUM_THREADS=1`; main can use a new private scratch outside protected backups
for pytest temporary outputs. The standalone new unit does not publish files.

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
& 'D:\_Repos\_Web_Projects\CAOS_Geophysics\.venv-pipeline\Scripts\python.exe' -m pytest tests/numerics/test_gravity_forward.py -o addopts= -q -p no:cacheprovider
```

All **66** new controls pass. In particular seven metadata-preallocation
negatives use real modest oversized arrays (including 5,000-element arrays and
2,049 receivers), forbid np.isfinite/np.array/np.count_nonzero and engine calls,
and prove rejection before ANY scans/copies. Only after all arrays' exact metadata
and caps pass is bounded active population traversed to verify density alignment.
Custom scalar/frame/nested values and array/dict/string subclasses reject before
equality/NumPy conversion. Runtime versions use already-loaded official modules,
not filesystem metadata scans in the pure callable.

Actual max combined 2,048-by-4,096 engine execution returns a float64 physical J
of exactly 64 MiB and meets p=Jrho identity. This is not a measured RSS/latency or
host envelope. Separate Choclo single-prism maximum difference is
`1.3322676295501878e-15 mGal`; signed/nonuniform active case is
`5.7667629352331495e-15 mGal`. Independent volume quadrature maximum errors at
orders 4/8/16 are `4.174748420460173e-6`, `2.2928547949163658e-11` and
`3.1433189384699745e-15 mGal`. Null/sign, Jacobian 0.001, finite-difference,
adjoint, sphere-integrator, far-field, output/state, actual engine and no-I/O
controls pass the original thresholds. These are authored ordinary controls,
not measured surveys or geological truths.

Scoped pipeline regression command (exact in receipt) includes this test module,
source intake and four existing legacy prism/inverse/CSV gates:
**104 passed, 2 existing skips, 11 deselected**. Initial broader collection
failed with three missing-Boule/Harmonica errors in this unchanged pipeline
environment. Preserve that negative; no installation or fallback was made.
Existing isolated M01 interpreter
`D:\_worktrees\geophysics-m01-corrections\.venv-m01\Scripts\python.exe`
ran its processing/transforms/station-adapter regression files separately:
**164 passed, 1 existing skip**. This is not an M02 environment or new install.

The unchanged artifact guard reports PASS **20 truths / 120 experiments / 348
method results**, with all SHA256/sizes matching. Ordinary unit source/runtime
audit verifies the 20 targeted installed source/binary pins; no native binaries
staged. Full product ledger and all prior scientific negatives stay independent.
Main's exact-source independent rerun/review is required before merge; hold this
code/test handoff stable once ready.

## Resolved geometry implementation and ready handoff, 2026-10-03

Final source SHA256:
`46d205a453147cc18697464e4a6deda2920d0d88307e366b6fd336d9a1ac07d5`.
Final test SHA256:
`c50158f083cba3ad096ff7b17eccdcbeb0a31f6e8293d13ffdccb3f6d78624c1`.
Read the [fresh quantitative receipt](evidence/final-geometry-execution.json)
and [final test addendum](evidence/ready-execution.json) together. The first
contains the actual 76/114/164 run and test hash `e5456f...`; the addendum binds
the final additional controls and does NOT relabel that earlier test run.
Both use the same unchanged operator source above. Original historical receipt
SHA256 remains `3b2d8e59338e8d678a9e97a9bb35e4868c34c58164b8cb1a2dd2e71a2c4d714e`;
reviewed runtime manifest remains `a5aa08c23a80e15024e6499fab6805315d52dee185c5de1010b5f46e5c9f5819`.

Final standalone controls: **80 passed, no skips**. Final scoped pipeline
command as printed above/in the receipts: **118 passed, 2 existing skips,
11 deselected**. The three existing M01 files passed **164 / 1 existing skip**
in their separate unchanged interpreter; the final test-only additions do not
affect those files. Full artifact guard passes **20/120/348**, all hashes/sizes
match. No scientific fixture or canonical/source guard was changed.

Full geometry tightening relative to the historical implementation:

- Reject nonrepresentable nominal and actual interior centres across ALL cells,
  including inactive cells, before prism construction/evaluation.
- Verify actual cumulative TensorMesh axis nodes and interval widths, cell
  bounds, all eight ordered node corners, centres and physical volumes. Nominal
  agreement is cell-scaled **1e-10 geometry fidelity**, NOT exact equality of
  decimal arithmetic and NOT a changed prediction/oracle tolerance.
- Return actual verified engine geometry, check full actual-node closed-box
  receiver exclusion, and verify SimPEG active prism-node identity before fields.
- Reject large origin 1e16 / width 3 rounding to node width 4 and physical-volume
  mismatch; admit width 4 with interior centres and exact TensorMesh volume.
  Admit ordinary decimal roundoff. Injected cumulative node disagreement,
  invalid bounds/centres/corners/volumes all reject before prism evaluation.

The final added controls explicitly isolate a representable active cell beside
an invalid inactive cell. Seven original pre-scan negatives still forbid finite
scans/copies/mask traversal/engine for invalid metadata/caps. Counts, exact types,
runtime pins, no-I/O scope and frozen physics tolerances remain unchanged.

Fresh measured Choclo residual maxima remain **1.3322676295501878e-15** and
**5.7667629352331495e-15 mGal**. Volume quadrature errors at orders 4/8/16:
**4.174748420460173e-6 / 2.2928547949163658e-11 / 3.1433189384699745e-15 mGal**.
Actual simultaneous 2048-observation/4096-cell control executes the official
engine and returns a 64 MiB Jacobian; not a total-RSS or host-admission claim.

Evidence separation: Curie's user-reported static WIP review of `d8cf3...` is
STATIC, not execution. Main's user-reported diagnostic of source `46d205...`
rejects hx2/hx3 and admits hx4 with volume 40000 m3, but is WIP, NOT independent
final acceptance. Our direct-engine investigation agrees with Choclo even when
centres collapse: the engine uses actual nodes. No centre-caused G collapse was
reproduced or claimed. The retained intermediate negative (1 failed/73 passed)
was an injected duplicate-corner escape, corrected by ordered-corner validation.
Here and in the unchanged dated JSON receipts, "user-reported" means MAIN-agent
coordination, not Felipe-supplied scientific execution or owner approval.

Use the exact existing READ-ONLY pipeline interpreter and process controls above;
no environment creation/upgrades. For main's rerun select new private scratch,
for example `--basetemp <new-private-path>`, never a protected backup/candidate.
M01 interpreter is separate and listed above. Windows source epoch only;
20 trusted installed source pins pass. No native binaries are staged.
An attempted PowerShell `Get-Date -AsUTC` display failed because this host lacks
that parameter, after the 80-test run had passed; the addendum timestamp uses
the independent UTC clock instead. This does not turn the test into a failure.

Self-review: exactly two additive code/test paths and this feature folder; all
six PR120 plan files, legacy physics, dependency/environment, API/UI and canonical
bytes are unchanged. Private 137-file backup and ignored candidates/receipts
remain unstaged/untouched. Independent final FULL code/policy/diff review and
exact-source rerun by main are still pending. Keep the ready pin stable; this
milestone is not inverse, survey, full M02, field, GPU, host or deployment acceptance.

Final staged static checks pass: content standards, template residue, CI budget,
SDD structure and `git diff --cached --check`. Read-only receipt self-audit verifies
strict JSON/no duplicate keys, all source/test/receipt/manifest SHA bindings,
12 requirement gate functions present, nine staged paths confined to the approved
scope, six PR120 files unchanged, and private backup count 137 / zero tracked.
The structural ledger reports 1 fail / 18 unresolved on this branch; this does
not imply scientific or release acceptance and has not been edited here.
