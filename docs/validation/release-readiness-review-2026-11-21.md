# Release-readiness review: 2026-11-21

## Scope and deployment rule

Reviewed the current geophysics task branch, the pinned CAOS App Shell and Product Template releases, the bilingual course and method wiki, both LaTeX manuscripts, current local data prerequisites, and the one configured ML-VPS origin. The approved deployment target remains `https://geophysics.ml.fasl-work.com/`; GitHub Pages is retired and is not a deployment target. No host files, release pointers, DNS, or services were changed in this review.

The current product pins Shell 0.26.2 and records Product Template 0.15.014. Both shared repositories were fetched; their local and remote `develop`/`main` trees match and their worktrees are clean. No newer shared-base tree delta was available to adopt.

## Implemented and checked in this review

- Notebook execution now always uses a disposable, release-shaped copy. Compressed M13 ONNX bytes are decompressed only there after byte-count and SHA-256 verification, for both `--check` and output regeneration. This fixes normal replay against the source tree, where the published ONNX exists only compressed.
- Notebook comparisons canonicalize both fresh and committed notebooks before checking, so Python version metadata and JSON source encoding do not produce false stale reports.
- The M13 lesson now calls the pipeline's shared SHA-bound CPU/WASM receipt validator rather than duplicating a long inline condition. The 24-record contract remains explicitly 23 QC-valid traces plus one excluded QC failure, with runtime parity distinguished from accuracy and release acceptance.
- ERT PNG raster drift is declared only for the two measured bilingual method-comparison lessons and the two measured bilingual inversion lessons. The observed maximum on the inversion pair was 0.000130718 changed-pixel fraction and 3.2778e-7 normalized MAE. Numerical, textual and scalar outputs remain exact; the guard caps each declared tolerance at 0.001.
- The source-to-content manifest now mirrors the seven current EN notebook citation inventories. Bilingual numeric parity accepts locale decimal commas while preserving numeric value and order.

## Current validation evidence

| Gate | Result | Boundary |
|---|---|---|
| Focused Python tests | 26 passed | Notebook runner, M13 receipt, and documentation numeric-parity controls. |
| Notebook structure and depth | 66/66 pass | EN/ES mirrors, ordering, metadata, reading bars, figures, equations and sources. |
| Fresh notebook execution | 66 executed | The first all-course run matched 64 notebooks exactly; the two M07 ERT images differed only by the measured raster drift above. Both M07 notebooks then passed fresh-kernel `--check` with the strict declared tolerance. No other notebook differed. |
| Documentation matrix | Pass | 13 method wiki entries and all 66 bilingual notebook pairs; implementation links, sources and EN/ES parity are bound. This is structural documentation evidence. |
| Manuscript depth | Pass | Technical report: 16,851 words, 32 equations, 10 figures, 9 tables, 32 references, 3 algorithms. Geometry-refinement manuscript: 8,718 words, 16 equations, 8 figures, 7 tables, 43 references, 1 algorithm. |
| Frontend production build | Pass | Current TypeScript and Vite build; Vite still warns that the Workbench and Three.js chunks exceed 500 kB minified. |
| Frontend unit suite with retained joint fixtures | 508 passed, 12 skipped, 2 failed files | The two setup failures need unavailable retained M04 selected-final and owned-custody browser controls. The fixture-bound joint subset separately passes 86 tests, with 4 explicit skips. |
| SDD checker and release ledger | Not accepted | `scripts/check_sdd.py` reports 97 structural requirement issues after M06/M07/M09/M12 requirement and adversarial-validation updates. The convergence ledger remains 1 failed, 15 unresolved and 3 passed; `--require-release` does not accept the candidate. |

`tests/run_validation.py` did not start its full scientific suite. Its fail-fast prerequisite check requires four exact retained originals that are not present at their configured paths: the M01 correction packet, M01 transform packet, profile-incomplete receipt, and M11 native database. No replacement or regenerated artifact was substituted. The method matrix reports all 13 structural gates present but `scientific_acceptance=false`.

## Manuscript assessment

The geometry-normalized travel-time paper is a bounded negative result on a fixed synthetic simulator. Its CNN loses to the regularized straight-ray reference under the stated held-out comparison. The paper discloses the generating/inversion operator mismatch and does not demonstrate novelty, superiority, field transfer, or improvement beyond the state of the art. Related work, including 2026 methods, is described by its distinct operators and protocols; those methods were not reproduced as matched baselines. The paper and technical report pass measured content/coverage checks, which are not peer review or product scientific acceptance.

## VPS verification and release decision

The read-only single-origin verifier compared the current local build with `https://geophysics.ml.fasl-work.com/` and returned `build_mismatch`. It therefore did not produce an acceptance receipt. The existing host is not a verified copy of this candidate. Deployment, promotion to `develop`/`main`, and release acceptance remain blocked by the unresolved scientific, source-custody, product-SDD, M04 actual-data, and hosted acceptance gates. No GitHub Pages deployment or second application origin was used.

The product branch is already based on current `origin/develop` (zero commits behind); no rebase is required. The current PR #151 remains draft. Only the scoped, validated changes from this review should be committed to that branch; the broader candidate should not be merged or deployed until its gates pass.

## M06 documentation follow-up

The measured MT feature requirements now use the current `AB-001` ID convention and have a requirement-by-requirement adversarial validation table. Six new tests cover pinned-source byte rejection, invalid variance, frame misalignment, full-period tensor gating, no-inverse behavior after a failed tensor screen, and rejection of an unreviewed station ID. The M06 feature gate no longer contributes SDD findings; its field conclusion remains negative for C15 and is not an MT inversion result. The course-wide SDD checker still reports 102 issues across other feature records.

## M07 ERT follow-up

The M07 Slagdump feature now has eight requirement-level adversarial checks. The ERT-08 gate is bound to a test that covers its convergence record, not to a documentation path presented as an executable gate. The pipeline now exposes `assumed_resistance_sigma`, the validated implementation of the declared `max(0.03*abs(R), 0.001 Ohm)` floor; invalid values fail before weighting. The M07 adversarial and existing parser/QC subset passed (12 passed); the separate M06 subset passed (11 passed, 3 skipped because ignored field bytes were unavailable in this checkout). This does not qualify the field inverse or host release.


## M09 travel-time follow-up

The M09 feature now has a requirement-by-requirement adversarial table for TT-01 through TT-10. A named `assumed_time_sigma` function validates the disclosed pick-weighting floor before use; the new controls exercise strict source identity, malformed SGT rows, absent precision, the homogeneous oracle, uncertainty inputs, whole-shot splits, failed predictive gates, documentation boundaries, immutable receipt bytes, and owner-source declarations. The focused M09 parser/adversarial suite passes 14 tests and Ruff passes. The SDD checker now reports 99 structural findings, with no M09 findings. This local contract improvement does not establish field predictive acceptance or change the convergence ledger's failed/unresolved release verdicts.

## Manuscript boundary recheck

The current manuscript-depth check reports 8,718 prose words, 16 display equations, 8 figures, 7 tables, 43 cited works and one algorithm for the BS-1 paper; the technical report measures 16,851 words, 32 equations, 10 figures, 9 tables, 32 references and three algorithms. Both pass the measured content floors, and the manuscript scientific-voice check is clean. The BS-1 experiment remains a negative fixed-simulator comparison with a Q/A operator mismatch; its literature discussion does not include reproduced matched state-of-the-art baselines. It is a substantive proposed-method study and a falsified hypothesis, but its current evidence does not establish novelty or performance beyond the state of the art. Do not describe the app as scientifically accepted or the proposed method as superior.

## Current shared-base review

The shell checkout is clean on `develop` at the release carrying `@fasl-work/caos-app-shell` 0.26.2; the template checkout is clean on `develop` at 0.15.014. The product pins shell 0.26.2 in its manifest, lockfile and exact-version gate and records template 0.15.014. The reviewed current release notes show no unadopted released delta. Product-specific shared-file adaptations remain local and were not overwritten. No shell or template edit is justified by this review.


## Online EDI and replay verification

A fresh current-source run of `tests/api/test_online_mt.py` in `.venv-api` passed all 17 tests in 254.40 s; one Starlette/httpx deprecation warning was emitted. The source-bound MT reconciliation suite passed all 9 tests in `.venv-pipeline` in 53.11 s. This is current local API and replay evidence. The local benchmark itself says actual ML-VPS admission is pending, so these tests do not open the worker feature flag or qualify live host capacity.


## M12 validation-contract follow-up

The learned velocity feature now has a seven-row adversarial validation map and its local requirements no longer embed a digest label that the SDD parser mistakes for a detached requirement ID. Existing tests are explicitly named as adversarial gates for split leakage, independent forward-operator checks, checkpoint tampering, same-input classical comparison, metric recomputation, negative-result retention, and fixture-only pipeline scope. The focused M12 inversion/comparison suite passes 7 tests; Ruff passes; the SDD checker reports no M12 feature findings and 97 findings overall. This changes contract traceability only: the frozen M12 learned method still fails its joint held-out comparison and does not establish beyond-SOTA performance or field validity.
