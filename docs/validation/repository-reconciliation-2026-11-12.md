# Repository and release reconciliation

Review date: 2026-11-12. Scope: the geophysics product checkout, its pinned
CAOS App Shell and product template, the open product PR, the current M04
receipt, and the previously measured manuscript/UI/deployment gates.

## Shared foundation and Git state

- `CAOS_APP_SHELL`: local `main` and `origin/main` are clean at
  `d2b3351b672bfa43e6aceb5893afb672b1fc58d7` (tag `v0.26.000`). One checkout;
  no extra worktrees.
- `CAOS_PRODUCT_TEMPLATE`: local `main` and `origin/main` are clean at
  `7dce8c9db460fb094d26b3a024872dd6f036e215` (tag `v0.15.008`). One checkout;
  no extra worktrees.
- `CAOS_Geophysics`: one checkout on
  `task/geophysics-client-first-completion`, clean after the changes in this
  review. Its published head is `89453682c1bb41724b4f6f6f7d1d8e5c116f78a7`.
  `origin/develop` is an ancestor, so no rebase is required. The open PR #151
  targets `develop`, remains draft, and has no reported CI checks. Promotion to
  `develop` or `main` is not justified while the product gates below remain
  open.

The product already pins shell `0.26.0`; the current template's shared source
files were previously compared byte-for-byte with the product copies. The
template's `0.15.008` shell adoption is already present. The product stylesheet
uses shell tokens and does not replace the shared shell fonts or global theme.
No shell or template edit was needed in this reconciliation. The original
instantiation provenance in `.template-version` remains distinct from current
template equivalence. Full prior comparison and product-adoption detail are in
[`template-shell-review-2026-11-11.md`](template-shell-review-2026-11-11.md).

The external product scorecard deliberately reads GitHub `main`, not this local
task branch. Its 2026-11-12 public-main row reports shell `0.6.8`, no recognized
template version, `0/0` notebooks, 46 documentation pages (180 KB), no
beyond-method strategy section, no Zenodo report or proposed-method manuscript,
and `0/7` posts. That row describes the currently promoted public repository;
it does not contradict the shell/template pins in the unmerged task branch.
The scorecard's source was checked and reads the public `main` branch.

## Product and scientific gates

The source-exact same-beta M04 sparse fold 0 now completes all eight scheduled
epsilon stages under the unchanged per-fit limits. Its exact receipt, hashes,
KKT and objective values are recorded in
[`../design/features/m04-survey-inversion/validation.md`](../design/features/m04-survey-inversion/validation.md#2026-11-12-source-exact-same-beta-sparse-fold).
That is one synthetic development fold, not the candidate matrix, selection,
sealed evaluation, field validation or a method-acceptance result. The product
PR remains draft.

The local manuscript-depth checker still reports four findings: no LaTeX
identifiability manuscript, missing report and nullspace `coverage.json`, and
no declared technical report. The geometry-normalized travel-time manuscript
meets its structural floor as a draft. The technical report and nullspace
manuscript remain below depth. The independent notebook-depth checker reports
155 findings across 66 bilingual notebook entries, including notebooks with
no explanatory prose, display equations, figures or references and missing
contract coverage. The manuscript-voice checker is clean. These fresh local
results confirm the content gates remain open; no manuscript or notebook was
changed in this reconciliation.

The 2026-11-11 browser review recorded seven findings across 1,683 states, a
passing focused route/layout gate, and an unresolved automated G21 linked-panel
gate. These are historical measured results, not a new visual acceptance run.
The VPS remains the only intended deployment destination; GitHub Pages stays
retired. There is no deployment in this reconciliation because the full
scientific matrix, manuscript/content, all-route browser and VPS host-admission
acceptance gates are not complete. No duplicate deployment was created.

## Promotion, deployment and cleanup decision

The new solver and regression test were committed and pushed to the existing
task branch. No shared-repo or template changes were pending. Product promotion
and the single VPS deployment remain blocked by the measured acceptance gaps,
not by Git synchronization or rebase conflicts. No new worktree was created.
The profile receipts from this investigation are preserved under the configured
external data root as scientific failure/success evidence rather than disposable
scratch files. Earlier generated QA directories under the data
root were not removed because an automatic-action review rejected their
recursive cleanup; no further deletion attempt was made.
