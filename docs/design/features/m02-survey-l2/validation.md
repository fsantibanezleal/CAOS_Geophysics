# Prospective L2 gates, controls and evidence policy

Status: planned. New numerical gates executed: **0**. No code/test authorization.
MAIN must fully read [contract](contract.md), [design](design.md),
[requirements](requirements.md), [research](../../../research/m02-survey-l2-2026-10-03.md),
[source receipt](../../../research/m02-survey-l2-evidence-2026-10-03.json) and
[tasks](tasks.md) before authorizing prospective paths. Never label these gates
PASS from a source read, plan merge or documentation check.

## Frozen proposed tolerances and meanings

Existing accepted forward policy stays unchanged: Geoana versus Choclo rtol1e-7 /
atol1e-10 mGal; prediction/Jrho/state/units rtol1e-10 / atol1e-12 mGal; adjoint
relative1e-10; directional physical derivative relative1e-6; volume quadrature
relative1e-5, far-field relative1e-3. Mesh local fidelity1e-10 is separately
geometric metadata admission, NOT a prediction threshold. No modification of
accepted forward source, fixtures, scientific source gates or failed receipts.

New objective/gradient/Hessian-vector controls relative1e-6 over steps
1e-2,1e-3,1e-4 in normalized density directions; require at least two adjacent
steps meeting the gate, retain every step/error. Unhalved objective and model
volume/pairwise-stencil identity rtol1e-10 / atol1e-12 on tiny well-scaled controls.
Choclo finite-difference physical J factor .001 is independently checked.

Covariance precision/quadratic/Cholesky-versus-symmetric-root identities
rtol1e-10 / atol1e-12 on frozen condition<=1e4 controls. At the full admissible
condition<=1e8 envelope require normalized ||W C W.T-I||_inf <=1e-7 and
relative quadratic-versus-Cholesky <=1e-7, preserving original C and every
failure. These are distinct named conditioning gates, not dynamically widened
tolerances after failures. Covariance symmetry/row/unit/source bindings are exact;
eigenvalue sign/conditioning failure rejects without nugget/diagonal fallback.

Independent tiny bounded optimum: rho and predictions normalized errors <=1e-5
under the design's normalized KKT<=1e-5, plus bounds feasibility. BVLS half factor
and direct Choclo/pairwise R independently audited. Native termination alone
does not pass the optimizer gate. Tests include ill-conditioned/underdetermined
cases as literal diagnostics, not demand geological-model equality for all cases.

Trace decrease: allowed roundoff <=1e-12*max(1,abs(previous phi_engine)), measured
on the SAME fixed objective. Stop criteria are exactly design's normalized KKT,
three accepted relative changes, absolute-stationary exception, CG/LS/iteration/
wall caps. No success on returned vector, low WRMS, early line-search failure,
retuned beta, zero-jitter start or stale terminal model. Deadlines are cooperative,
not a hard preemption guarantee. Native source defaults are not our stop policy.

## Requirement-to-gate matrix, all NOT RUN

| Requirement | Named prospective control | Positive, negative and independent proof |
| --- | --- | --- |
| L2-01 | test_metadata_first_exact_contract | Real 5000-cell/2049-row arrays and oversized covariance reject with finite scans/copies/digests/count/engine denied; exact ndarray/native keys/scalar hooks reject before equality |
| L2-02 | test_source_frame_sign_and_processing | Upward-mGal/metre/kg/m3 accepted; wrong sign/unit, absent datum/correction and raw-absolute input reject; external raw declaration not false byte verification |
| L2-03 | test_masks_missingness_duplicates_and_order | Compact observations never masked/outer zero values; exclusions/reasons/permutation roundtrip; duplicate IDs/XYZ and unknown geometry reject without invented heights |
| L2-04 | test_real_engine_forward_and_geometry_identity | Genuine official fit engine observed; compare G/1000 to accepted forward J and independent Choclo; actual x-fast nodes/bounds/centres/volumes; width2/3 rejects including inactive, width4/decimal admits |
| L2-05 | test_covariance_whitening_hessian_and_marginals | Non-diagonal SPD and diagonal equivalence, off-diagonal Hessian-vector; nonsymmetric/indefinite/ill-conditioned/wrong squared-unit rejects; lower-triangular misfit Hessian mismatch retained as expected negative |
| L2-06 | test_objective_regularization_and_physical_derivatives | Independent nonuniform signed pairwise active-face R, constant/gradient reference and air gaps; objective factor2, physical gradient .001/Hessian .000001, explicit beta_engine=nfit*beta |
| L2-07 | test_bounded_l2_independent_bvls_and_kkt | Positive/negative/zero/reference starts; active bounds; independent Choclo G/pairwise R BVLS; infeasible/infinite/swap bounds reject; no production fallback |
| L2-08 | test_frozen_geometry_blocks_groups_buffers | Seed104729/group union/hash/ceil fifth/cyclic folds; buffers exclude near rows; order invariance; all-one group/infeasible mask/collinearity/oversized block indices reject |
| L2-09 | test_exact_candidates_scores_failures_and_refit | Eight candidates x3 real fits; no fold omission, tie chooses stronger beta, at least2 eligible; selected refit failure cannot choose another beta |
| L2-10 | test_sealed_outer_and_inner_value_leakage | Outer values/SD/truth absent from calibration; poison/permute outer leaves fit hashes; own-fold validation changes only score; evaluate forbids optimizer and recomputes model binding |
| L2-11 | test_pinned_stopping_null_and_terminal_state | Current cg_* names, fixed beta/alpha, actual official search/LS observed; stationary null beforeCG, nonstationary zero-free stall, cap/failedLS/nonfinite retained; terminal trace exact |
| L2-12 | test_rank_coverage_nullspace_and_nonclaims | Rank<a allowed with warning, rank0 rejection, fit-only physical sensitivity; separated depth/density near-null pair, regularized vs data uniqueness distinction, no field truth/posterior |
| L2-13 | test_native_result_identity_and_tamper | Exact keys/dtypes/None/private immutable arrays; source/model/units/masks/candidates/row/hash/trace tamper rejects; residual identity against independent validated stored prediction |
| L2-14 | test_preflight_caps_and_measured_local_envelope | Above-cap/projection rejects before allocation; serial CPU/thread/covariance/history limits; actual measured workflow plus wall failure retained, no host/GPU claim |
| L2-15 | test_no_io_hooks_runtime_or_legacy_mutation | File/network/subprocess writes denied after imports; no user callbacks/importpaths; loaded official version checks; external eight+existing20 hashes; accepted legacy/artifact bytes unchanged |
| L2-16 | test_complete_locked_l2_control_matrix | All 24 prospective source-disjoint ordinary controls including poor/null/model-sensitive outcomes; no erased errors/replaced seeds; prospective synthetic positives separate from field |

Full file paths are in requirements. These names do NOT exist yet. Small private
partition-solve unit tests may use tiny official objects without pretending that
they meet public calibration split minima or are eligible submitted surveys.
No testing-only public engine injection/bypass is proposed.

## Frozen small and ordinary authored control specifications

Tiny objective/bounds controls: nonuniform hx=(40,70), hy=(30,50,90), hz=(60,110),
origin(-140,-180,-260), sparse active full indices(0,2,3,7,11), rho
(400,-600,900,-300,1200) kg/m3; same four off-axis receivers as accepted prism
control. SD .01 mGal; correlated C=.0001*((.8 I)+.2 ones), explicit fixed background
(.002,-.003,0,.001) mGal. Bounds all[-1500,1500], start all0, reference
(10,-20,30,-40,50), density scale1000, lengths(80,90,70)m, beta candidates exactly
as contract. Separate tighter bounds[-250,250] exercise feasible active optimum.
These are small mathematical oracles, not heldout survey-quality cases.

Prospective external ordinary matrix: six families x four conditions = **24 L2
outcomes**, each retaining eight candidates x three folds plus selected refit when
eligible. No IRLS outcome count or claim that this replaces parent's future48/96.
Mesh fixed4x4x3, each width100m, origin(-200,-200,-300), all48cells active;
start/reference0, bounds[-1500,1500], density scale1000, lengths(100,100,100)m.
Receivers12x12: x/y=-550+100*i (i=0..11), z100; xfast station index i+12*j.
Partition group ID `line:j`; station ID `station:i:j`; block origin(-600,-600),
size(100,100), buffer25m, split seed104729. These geometry choices are authored
development controls, not a measured field correlation/CRS policy.

Continuous source prisms below are independent Choclo inputs, not inversion
cell vectors or saved production G. Bounds west,east,south,north,bottom,top;
densities kg/m3. Exact volume intersections produce volume-averaged synthetic
density truth only for separate evaluation, never a solver input.

| Family index | Prisms / physical purpose |
| --- | --- |
| 0 | (-85,45,-75,35,-135,-45), +450: off-grid off-axis compact positive |
| 1 | (-135,-25,-95,65,-155,-55), +400; (35,135,-45,105,-205,-95), -300: signed bipolar |
| 2 | (-155,165,-145,145,-220,-60), +125: diffuse body, no sparsity advantage claimed |
| 3 | (-175,185,-165,155,-285,-185), +300: deep broad body / weak depth information |
| 4 | No sources: exact null anomaly; separate noisy null and zero-gradient controls |
| 5 | (-125,-15,-125,-15,-105,-35), +250; (15,125,15,125,-275,-165), +500: two depth scales / model sensitivity |

Conditions: 0 credible diagonal noise SD=.005mGal; 1 correlated Gaussian noise
Cij=.005^2*(.8deltaij+.2 exp(-horizontal_distance/120m)); 2 same diagonal noise
with excluded index%7==0 and reason `control_gap`; 3 same diagonal noise plus
unmodelled background .00002*x mGal/m and +.05mGal at indices%29==0.
Background supplied to solver is zero with explicit synthetic convention. Condition3
is model/noise mismatch with all retained residuals, not silently cleaned or fitted.

Noise seeds: PCG64 seed=700001+100*family_index+condition_index for this locked
evaluation matrix; disjoint development controls use the same six explicitly
documented families but source bounds translated(+17,+13,0)m and seeds900001+100*f+c,
never reuse evaluation noise/values to choose the beta grid, prior or stops.
Generator version NumPy2.2.6, exact source specification and measured generated
array hashes must be recorded at first approved execution. No fixture/model/raw
array is generated by this docs task. PCG64 draws full source noise BEFORE masks/
splits so omitted data cannot change the remaining realization. Full covariance
generation via Cholesky uses declared C; calibration receives principal dev C.

Quality gates for conditions0/1 nominal families0/1: prospective outer WRMS<=2
and volume-weighted model RMSE ratio<1 versus zero/reference. Publish each score
and identity even if failing. No universal density-quality pass for diffuse/deep/
two-depth/null or mismatch family. Non-aligned source geometry prevents same-G
inverse crime; synthetic truth remains coarse volume-average, not field truth.
All 24 outcomes, rejected/nonconverged fits and prior/rank/mesh warnings count.
Independent numerical quadrature4/8/16 at separated receivers, sign/mass/far-field
and near-null/depth alternatives supplement separate prism implementations.

External geometry alternatives (diagnostics, not model selection): same source
observations under mesh8x8x6 widths50 and widened6x6x4 widths100 origin(-300,-300,-400),
same physical priors/bounds/lengths, chosen before opening sealed data. Report
prediction changes in original SD units, flag >.25SD, and retain model change;
do not replace frozen primary48-cell result with the nicer alternative. These
geometry counts fit the inherited4096cap but are not evidence of local resources.

## Resource/source/nonclaim gates and later execution receipt

Proposed resource measurements after code authority: small/nominal/combined-cap,
20 nominal repeat workflows for p95 and estimator check, observed peak RSS<=2GiB,
nominal p95 peak<=70%of2GiB, complete calibration<=1800s and per solve<=120s with
literal cooperative overrun reporting. No file scratch, native staging or package
install. CPU/device/threads/baseRSS/workspace/trace/elapsed receipts must be actual.
Failure preserves caps/thresholds and may require a separately reviewed scale
amendment; cannot silently alter geometry or loosen numerical stops.

External source audit reads trusted installed distributions ONLY, never request
paths; combine existing20pins with new8, avoiding duplicate-file double counting.
New source files require genuine SHA/version receipts at code acceptance. Current
inspection proves eight source bytes equal official tag, NOT inverse execution.
Private FWI137backup/candidates/historical forward receipts and canonical hashes
remain untouched. Existing full artifact guard/source gates are not weakened.

Full field admission remains blocked by current Bartlett datum/errors/lineage;
conditional Gaussian assumptions or field source_kind NEVER emit field_eligible.
Output truth/model accuracy absent for field/upload. Broader M02 IRLS, source/M01
normalization, uncertainty refits, bundle/export, shared API/UI/wiki, GPU/host and
full-method gates remain backlog. Local inverse convergence is not their proxy.

After implementation approval, each receipt must record exact input/spec/array,
plan/prior/policy/module/test/runtime/source SHA, command, seed/fold/row counts,
actual official engine calls, every candidate/model/state/score and all negatives.
Main independently replays exact-source objective/physical output/selection and
ownership seams before merge. Historical source/tests/receipts never relabelled.

## Docs-only checks

Only document/research inspection and static checks may execute before approval.
Recorded results will be separate from this prospective numerical ledger. Public
commands use `$ExistingPipelinePython` resolved from the trusted `$ProductCheckout`,
not a workstation absolute path or request-supplied executable. No installation,
CI fitting, source changes or missing-test PASS is permitted.

### Executed documentation/source checks, 2026-10-03

At 11:40 UTC the existing trusted Windows CPython3.12.10 interpreter ran with
PYTHONDONTWRITEBYTECODE=1. This is documentation/source review, NOT inverse
execution or implementation acceptance. No package creation/update/import or
scientific source change occurred in the source-byte audit.

| Command or read-only check | Actual result |
| --- | --- |
| `& $ExistingPipelinePython scripts/check_content_standards.py` | PASS, tracked packet included |
| `& $ExistingPipelinePython scripts/check_template_residue.py` | PASS, 860 tracked files |
| `& $ExistingPipelinePython scripts/check_ci_budget.py` | PASS |
| `& $ExistingPipelinePython scripts/check_sdd_convergence.py` | Structurally valid; 1 fail, 18 unresolved, 0 pass; NOT release acceptance |
| `& $ExistingPipelinePython scripts/check_artifacts.py` | PASS, unchanged 20 truths / 120 experiments / 348 methods, SHA/size verified; NOT L2 evidence |
| Existing CI base-integrity rules, read-only tracked paths and literal path grep | PASS; no machine-path leak, tracked environment/native/heavy/raw blobs |
| Strict JSON, scoped index, relative links, prospective gate absence | Exactly seven new docs; valid links; all16 unique gates absent, NOT RUN |
| Stdlib hashes/metadata against source receipt and prior runtime manifest | All18 protected repository hashes, accepted forward test and 28 distinct installed source pins unchanged; seven versions match |
| Private original backup tracking/ignore/presence check | Zero tracked paths, present and ignored; no backup digest recomputation or modifications |
| `git diff --cached --check` | PASS |

The eight previously retrieved official files remain byte-bound to their recorded
installed counterparts. This final source audit rechecks 20 inherited plus eight
new installed pins, not a new remote retrieval or a full environment certificate.
The complete packet and actual check counts are pinned by the handoff commit;
prospective source/test hashes remain null. MAIN's full read/explicit authority
and every new numerical gate remain pending.
