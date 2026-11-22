# Replacement release readiness, 2026-10-30

This local assessment is against the direct product checkout at `221d031ca366410ca36066da37d302b9832008b1` (detached HEAD); the working tree currently has 99 changed paths. This is not a fresh remote synchronization or a release commit. No commit or deployment was made during this validation pass.

## Checks that pass

| Check | Result | Boundary |
|---|---|---|
| Convergence ledger | `check_sdd_convergence.py`: 19 requirement records are structurally valid; 1 pass, 1 fail, and 17 unresolved | The checker validates evidence bindings and status structure, not scientific or release acceptance. |
| Method matrix | 13/13 structural method gates are present | `scientific_acceptance=false`. |
| Notebook structure | 62 English/Spanish notebooks are mirrored, ordered, annotated, and clean | A fresh-kernel replay executed all 62 without execution errors; the current structural check also passes. |
| Shell adoption | Exact shell 0.19.9 pin, production build, six route tests, and a fresh 1,442-state browser gate pass with 157 captures; see [current gate receipt](shell-gate-current-2026-10-30.json). The measured checkout was `221d031ca366410ca36066da37d302b9832008b1`, with 96 changed paths. | Zero waivers/failures; a fresh post-gate production build produced the same `dist/index.html` hash. This is shared-shell integration only, not exact-commit release or owner acceptance. |
| Case and condition rendering | Full local browser sweep covers 20 case families × 6 experiment conditions; all 20 families expose six distinct metric views and no browser/layout failures; [full measured report](case-condition-viewport-2026-10-30.json) | 18 physical/joint families render six distinct visual states each; learned families render four distinct reconstructions and six distinct metric views. The report records that it was measured from a dirty working tree. This validates rendering/data selection, not scientific accuracy or a release commit. |
| M02 locked controls | Retained Windows CPU matrix records 24/24 locked cases passing; its report validator passes 4/4 tests, and the current forward identity test passed | The only current gravity-L2 source delta is a corrected `FORWARD_SOURCE` hash matching the unchanged forward implementation; the matrix report remains historical evidence from 2026-10-29. |
| VPS service unit controls | `test_service_release.py`, `test_service_runtime.py`, `test_service_bootstrap.py`, `test_isolated_api.py`, and `test_single_vps_service_adversarial.py` pass locally (exit 0) | Platform-specific Linux controls are skipped on this Windows host; no live host qualification or service activation occurred. |
| API suite | 1,196 tests, 0 failures/errors, 138 skips; exit 0 in 460.631s; [JUnit and run details](api-tests-2026-10-30.md) | Local API/service tests only; retained platform/host controls are skipped and no ML-VPS acceptance is implied. |
| Deployment-origin source guard | `check_single_origin.py`: pass | Source/build policy only; not live deployment acceptance. |
| Local accounting/service controls | `test_protocol.py` and the single-VPS adversarial suite pass, with one skip | These do not establish native Windows/Linux containment or actual-host admission. |

## Release blockers

1. Full frontend-suite acceptance remains open. The current retained-data checks passed 46 joint input/result tests with 5 fixture-gated skips; exact M04 selected-final and browser-control fixtures and other maximum-output/custody fixtures are unavailable. No substitute was created.
2. The fresh 24-case joint solver matrix replayed all 624 candidates, retaining 100 nonconverged candidates across 22 cases. `scientific_precision_accepted`, `field_eligible`, and `public_activation` are all false.
3. `check_sdd_convergence.py` reports a structurally valid ledger with 1 pass, 1 fail (`R-008`), and 17 unresolved requirements. The ledger's `assessed_revision` is `ad221c52a2e64a842ee77299b5c2f300c8d9296f`; the current direct checkout is detached at `221d031ca366410ca36066da37d302b9832008b1` and dirty, so the assessment is not re-anchored to this state. `--require-release` remains unmet.
4. R-019 remains unresolved: the current browser model has same-checkpoint CPU/WASM parity, but no current private PyTorch oracle receipt/checkpoint is available for independent parity, and the 23-trace display subset is not an accuracy population.
5. `product.json` still has no manuscript declaration, and no `check_manuscripts.py` exists in this checkout. The technical-report and M12 manuscript drafts have retained local compile evidence, but neither has a verified Zenodo record or DOI; no publication is claimed.
6. The retained 2026-10-30 read-only VPS receipt reports 902,692,864 bytes free, below the runtime stager's 4 GiB precondition; that receipt also reports the legacy `0.04.001` release and inactive API/worker. See [the read-only host receipt](actual-host-capacity-readonly-2026-10-30.md). This was not rechecked during the present local validation.
7. Full actual-host API/worker isolation, user-data workflows, capacity/job admission, and post-deployment verification have not passed. Preserve the current release and two rollback releases.

## Release decision

Do not stage or activate a replacement while these gates are open. The single canonical origin is `https://geophysics.ml.fasl-work.com/`; GitHub Pages is disabled. SMTP and off-host backup are not release prerequisites. Resume candidate admission only after the exact source and convergence ledger are reconciled, scientific and custody findings are resolved, the technical report has a verified real record, actual host capacity meets the measured runtime requirements, and the complete API/worker/browser/rollback acceptance passes.

## M12 evidence correction, 2026-10-30

The v1.1 residual-refinement receipt was replayed with its original verifier through a compatibility wrapper that tolerates only floating-point roundoff in candidate score maps; selected lambda, source and artifact hashes, splits, calibration selection, all four held-out cohorts, and the final bounded-synthetic verdict remain checked. The original scorer used an infinite threshold, so its saved zero-exceedance fields are not a threshold assessment. A deterministic paired case-ID bootstrap now regenerates the ratio-of-mean-RMSE intervals from the immutable receipt (20,000 PCG64 draws, seed 6122026); the corrected joint-OOD intervals are 0.9661–0.9737 for velocity and 0.9950–0.9983 for independent travel time. Seven focused bootstrap and compatibility tests pass. A separate working manuscript reviews established null-space and current learned-tomography approaches and explicitly states the missing same-cohort raw-network comparison. Its five-page PDF compiles and passes the CAOS scientific-voice check; the complete references now fit on page five after a typography adjustment and visual inspection. Its DOI fields state that none is assigned. These results remain bounded to fixed synthetic cohorts, do not validate field transfer, and do not change M12 or product scientific acceptance.

## User-data workflow validation, 2026-10-30

Current focused evidence is recorded in [the local science and user-data validation receipt](current-local-science-validation-2026-10-30.md). The 24-case joint solver matrix completed and replayed, but retains 100 nonconverged candidates across 22 cases and does not pass scientific precision acceptance. The complete `tests/run_validation.py` release matrix remains unrun because exact retained M01 source packets, the profile-incomplete receipt, and the M11 native database are unavailable; Linux-only controls and the two M04 browser custody controls remain unqualified. These local results do not establish host acceptance.
