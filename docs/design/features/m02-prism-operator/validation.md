# Ordinary prism operator exact planned gates

Status: planned. No operator code exists or numerical test has run in this
amendment. Docs/source-pin inspection only. Independent review pending.
Protocol: [design](design.md). Requirements: [requirements](requirements.md).

## Gate mapping, all NOT RUN

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

Current scientific gate count: zero executed. Documentation checks cannot
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
18 unresolved. No numerical/gate result changed. Actual operator/test files do
not exist. Main has not yet authorized code or independently accepted this amendment.
