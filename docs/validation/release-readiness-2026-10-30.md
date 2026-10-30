# Replacement release readiness, 2026-10-30

Assessed product branch: `task/geophysics-client-first-completion`, pushed through `4d6e0bc`; PR #151 remains a draft. The working tree also contains extensive uncommitted implementation. The browser report records that dirty-tree state explicitly and does not treat it as release-commit acceptance.

## Checks that pass

| Check | Result | Boundary |
|---|---|---|
| CAOS Product SDD structure | `check_sdd.py`: 538 live requirements have executable gates; 27 planned requirements/gates remain unbuilt | Structural completeness does not prove the science or service works. |
| Method matrix | 13/13 structural method gates are present | `scientific_acceptance=false`. |
| Notebook structure | 60 English/Spanish notebooks are mirrored, ordered, annotated, and clean | A fresh-kernel replay executed all 60 without execution errors; three stale figures were refreshed and their focused replays passed. |
| Shell adoption | Exact shell 0.19.9 pin, production build, six route tests, and 1,442-state browser gate pass | 157 captures, no waivers or failures; shared-shell integration only. |
| Case and condition rendering | Full local browser sweep covers 20 case families × 6 experiment conditions; all 20 families expose six distinct metric views and no browser/layout failures; [full measured report](case-condition-viewport-2026-10-30.json) | 18 physical/joint families render six distinct visual states each; learned families render four distinct reconstructions and six distinct metric views. The report records that it was measured from a dirty working tree. This validates rendering/data selection, not scientific accuracy or a release commit. |
| API suite | 1,196 tests, 0 failures/errors, 138 skips; exit 0 in 460.631s; [JUnit and run details](api-tests-2026-10-30.md) | Local API/service tests only; retained platform/host controls are skipped and no ML-VPS acceptance is implied. |
| M02 locked controls | Retained Windows CPU matrix records 24/24 locked cases passing; its report validator passes 4/4 tests, and the current forward identity test passed | The only current gravity-L2 source delta is a corrected `FORWARD_SOURCE` hash matching the unchanged forward implementation; the matrix report remains historical evidence from 2026-10-29. |
| VPS service unit controls | `test_service_release.py`, `test_service_runtime.py`, `test_service_bootstrap.py`, `test_isolated_api.py`, and `test_single_vps_service_adversarial.py` pass locally (exit 0) | Platform-specific Linux controls are skipped on this Windows host; no live host qualification or service activation occurred. |
| API suite | 1,196 tests, 0 failures/errors, 138 skips; exit 0 in 460.631s; [JUnit and run details](api-tests-2026-10-30.md) | Local API/service tests only; retained platform/host controls are skipped and no ML-VPS acceptance is implied. |
| Deployment-origin source guard | `check_single_origin.py`: pass | Source/build policy only; not live deployment acceptance. |
| Local accounting/service controls | `test_protocol.py` and the single-VPS adversarial suite pass, with one skip | These do not establish native Windows/Linux containment or actual-host admission. |

## Release blockers

1. The fixture-backed frontend suite reports 429 passed and 12 skipped. Two magnetic suites fail during setup because the original selected-final extraction control and owned-custody browser-control file are unavailable at their recorded paths. No substitute was created.
2. The retained 24-case joint output records `scientific_precision_accepted=false`, `field_eligible=false`, and `public_activation=false`. The method matrix therefore remains structural only.
3. `check_sdd_convergence.py` currently fails on a stale hash for `docs/wiki/methods/m07-m13.es.md`; this checkout has extensive additional dirty changes, so the full ledger cannot be called reconciled. Its assessment revision `43f4f9b` predates product commits `e36a31d` and `4d6e0bc` and recorded 18 unresolved requirements and one failed requirement (`R-008`, scientific acceptance). `--require-release` remains unmet.
4. `check_manuscripts.py` fails: `product.json` has no technical-report declaration. The 12-page technical-report draft and a separate five-page M12 working manuscript now compile; the M12 manuscript's complete references fit on page five after a typography adjustment and were visually inspected. Neither has a verified Zenodo record or DOI, and no publication is claimed.
5. The live VPS is still serving `0.04.001`; Nginx is active and the geophysics API/worker are inactive. The 2026-10-30 measured free disk is 902,692,864 bytes, below the runtime stager's 4 GiB precondition. See [the read-only host receipt](actual-host-capacity-readonly-2026-10-30.md).
6. Full actual-host API/worker isolation, user-data workflows, capacity/job admission, and post-deployment verification have not passed. Current plus two rollback releases remain intact.

## Release decision

Do not stage or activate a replacement while these gates are open. The single canonical origin is `https://geophysics.ml.fasl-work.com/`; GitHub Pages is disabled. SMTP and off-host backup are not release prerequisites. Resume candidate admission only after the exact source and convergence ledger are reconciled, scientific and custody findings are resolved, the technical report has a verified real record, actual host capacity meets the measured runtime requirements, and the complete API/worker/browser/rollback acceptance passes.

## M12 evidence correction, 2026-10-30

The v1.1 residual-refinement receipt was replayed with its original verifier through a compatibility wrapper that tolerates only floating-point roundoff in candidate score maps; selected lambda, source and artifact hashes, splits, calibration selection, all four held-out cohorts, and the final bounded-synthetic verdict remain checked. The original scorer used an infinite threshold, so its saved zero-exceedance fields are not a threshold assessment. A deterministic paired case-ID bootstrap now regenerates the ratio-of-mean-RMSE intervals from the immutable receipt (20,000 PCG64 draws, seed 6122026); the corrected joint-OOD intervals are 0.9661–0.9737 for velocity and 0.9950–0.9983 for independent travel time. Seven focused bootstrap and compatibility tests pass. A separate working manuscript reviews established null-space and current learned-tomography approaches and explicitly states the missing same-cohort raw-network comparison. Its five-page PDF compiles and passes the CAOS scientific-voice check; the complete references now fit on page five after a typography adjustment and visual inspection. Its DOI fields state that none is assigned. These results remain bounded to fixed synthetic cohorts, do not validate field transfer, and do not change M12 or product scientific acceptance.
