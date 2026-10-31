# Additional wide-start negative, no policy change

Date2026-10-03. This is producer execution/diagnosis, NOT MAIN independent review
or a proposed approved optimizer change. The AS-B source is2662dece5964fb4652c510dfcb89df99bf1b0344fe7aa9b9071f0c55c5e274df.
Read the [complete new actual trace](evidence/additional-wide-start-negative-20261003.json)
and [run chronology](evidence/approved-release-execution-20261003.json).
All prior receipts and MAIN's d7 reports remain original bytes.

## Specimen and measured negative

The already declared six-cell nonuniform signed control uses direct Choclo G,
explicit both-active pairwise R and separate triangular Cholesky whitening for
its BVLS reference. Bounds are1500kg/m3, diagonal SD.005mGal, same prior/reference,
candidate.01 and background. Start lower_reference means alternating supplied
lower bound/reference; no start perturbation, warm start or solver option changes.
The supplemental gate covers all six modes at both75/1500 and both noise modes:
23 PASS/1 FAIL. This is NOT the separate24-family/condition matrix.

The failed case hits the unchanged120s cooperative deadline. A separate actual
diagnostic returns nonconverged/wall_cap after51 accepted native directions,
52 states and120.25s; caps are not hard preemption promises. Retained actual
normalized density L2 error versus BVLS1.1286665317147966, unhalved objective
relative error0.05268513341523953 and prediction absolute error
0.000286669295700677mGal all fail their frozen comparison gates. Low residual
or positive inner-CG diagnostics cannot establish a constrained optimum.

At accepted state4, cell0 is at the lower bound-1500 with independent q-gradient
-0.08871593992245919, pointing inward. The other five free q-gradients are
nonzero, approximately4.3e-12 through2.4e-11. Independent normalized KKT is
0.0001297087805779684; the native-objective KKT is0.00012970878056745429.
The final state retains the same nonstationary bound and essentially unchanged
objective0.09650667178910109. All recorded direction kinds are0=native_CG.
No exceptional release, dense oracle fallback or alternate bounds were used.

## Installed source and exact boundary

Read-only inspection of the trusted installed SimPEG0.25.2 optimization.py
lines1630..1705 confirms its exact active/binding handling. For an active inward
coordinate the native method adds a gradient scaled by
`active_set_grad_scale * max_abs_free_CG_step / max_abs_inward_gradient`.
When the free-coordinate solve has nearly stationary gradient, that scale can
leave the inward bound effectively unmoved in floating point. This diagnosis
is supported by the actual independent gradients/model/trace, not a hypothetical
geometry or centre bug. Installed file SHA remains
0ac858cc310b32bb9aa59c78aaaa9c79b5f28438db52fb06ec73d976b63196a4.

The approved AS-B trigger requires ELEMENTWISE EXACT zero free residual, not a
small norm, a relative epsilon or a rounded accepted-step test. This specimen
does not qualify. Broadening to near-zero, replacing an ordinary direction or
retrying after native CG/LS would change the explicitly approved policy. None
is implemented. In particular, increasing wall/iteration caps, tolerances or
changing the fixture/start would conceal rather than resolve this negative.

## Hold and bounded continuation

The optimum assertion stays failing, not xfailed/skipped/excluded. Code/tests
are frozen for a scoped incomplete milestone and MAIN detached review. This
negative blocks whole bounded-quality acceptance even if MAIN's distinct16
start controls later pass. Exact-zero AS-B comparisons are not relabelled as
global finite-precision convergence proof. New algorithm work requires a separate
evidence-backed complete amendment and explicit MAIN read/approval before code.
Original sealed selection, all24 outcomes and projected/measured resources remain
pending under their unchanged rules; no partial PASS closes those requirements.
No installed/planner/forward/runtime/legacy/API/field/IRLS/GPU/host/canonical,
main, merge or deployment change is authorized by this diagnostic.
