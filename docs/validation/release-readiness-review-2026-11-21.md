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
| SDD checker and release ledger | Not accepted | `scripts/check_sdd.py` reports 102 structural requirement issues after M06/M07 requirement and adversarial-validation documentation updates. The convergence ledger remains 1 failed, 15 unresolved and 3 passed; `--require-release` does not accept the candidate. |

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
