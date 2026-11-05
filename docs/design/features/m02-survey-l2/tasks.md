# L2 sub-SDD ownership and dependency backlog

Status: scoped local ordinary-L2 implementation and test gates have been executed.
The product owner authorized implementation of approved pending product work on
2026-10-25. Exact-head current-source replays on 2026-10-31 passed 186 core tests, 81 precision/control tests, 27 selection workflow tests and the complete 24-condition locked L2 matrix. The resource harness passed 20 cap plus 20 nominal runs with complete sampling; see the [core](evidence/core-replay-2026-10-31.md), [selection](evidence/selection-replay-2026-10-31.md), [resource](evidence/resource-replay-2026-10-31.md), [precision](evidence/precision-replay-2026-10-31.md) and [locked-matrix](evidence/locked24-replay-2026-10-31.md) receipts.
Historical diagnostics and failed controls remain preserved. The separate IRLS policy/serialization, corrected-control and original null-workflow replay passed 86 tests with the known non-null IR-C06 fixed-point case deliberately deselected; see the [IRLS controls replay](evidence/irls-controls-replay-2026-10-31.md). A fresh recurrence replay passed both native stage-oracle and scaled-weight derivative tests, confirming native inner-solve accuracy while reproducing the frozen final-transition failure; see the [recurrence replay](evidence/irls-recurrence-replay-2026-10-31.md). The distinct original-IRLS 24-case matrix failed in its first actual cell: all eight candidates were ineligible, the calibration reached its 1800-second cap, and no outer evaluation was produced; see the [first-case receipt](evidence/original24-irls-first-case-2026-10-31.md). These are local source-bound results, not independent acceptance. Independent pinned review, the non-null IRLS criterion, field-data eligibility and full product acceptance remain open. Base
`1b112bb258520a5679a865335cec30b6a97a1a0d`.

Parent references: [product SDD M02](../../SDD.md), [unchanged PR120 tasks](../m02-survey-inversion/tasks.md),
[accepted PR122 forward](../m02-prism-operator/tasks.md),
[BL-012/#44](https://github.com/fsantibanezleal/CAOS_Geophysics/issues/44),
[parent #32](https://github.com/fsantibanezleal/CAOS_Geophysics/issues/32).
Related M01 [BL-011/#43](https://github.com/fsantibanezleal/CAOS_Geophysics/issues/43)
and [strict JSON design #124](https://github.com/fsantibanezleal/CAOS_Geophysics/issues/124)
are NOT activated or closed by this native-array sub-SDD. No shared-owner edits.

## Review packet, implementation authority and acceptance boundary

- [x] Inspect actual current forward/legacy inverse/intake/M01 sources and parent
  plan, not infer completeness from names. Primary research and source findings
  persisted BEFORE contract/design: [dossier](../../../research/m02-survey-l2-2026-10-03.md),
  [source inspection receipt](../../../research/m02-survey-l2-evidence-2026-10-03.json).
- [x] Freeze separately reviewable exact native [contract](contract.md),
  [objective/optimizer/results/ownership](design.md), [16 EARS requirements](requirements.md)
  and [control/tolerance/seed matrix](validation.md).
- [x] MAIN authorized implementation of all approved pending product work on
  2026-10-25; this does not waive frozen scientific gates.
- [x] The scoped native admission and ordinary-L2 source/tests are implemented.
  A fresh exact-head core replay is recorded in
  [current-source evidence](evidence/core-replay-2026-10-31.md).
- [ ] Independent pinned review and source-bound replay of the complete numerical
  packet remain required; local implementation and tests do not provide them.

## Implemented local paths and remaining boundaries

| Owner | Paths | Boundary |
| --- | --- | --- |
| M02 sidecar | `data-pipeline/gravity_survey_l2.py`; `tests/data/test_gravity_survey_l2.py` | Native admission/hash/geometry-only split; no JSON/upload/I/O/provider corrections |
| M02 sidecar | `data-pipeline/gravity_l2.py`; `tests/numerics/test_gravity_l2.py`; `tests/numerics/test_gravity_l2_selection.py` | Core and selection workflow tests plus the complete 24-condition locked matrix passed locally; only four cells assert explicit model/WRMS efficacy limits; independent replay and field acceptance remain open |
| Evidence | This feature's dated evidence | Current 186-test core, 81-test precision, 27-test selection, 24-condition matrix and 40-run resource receipts; not independent or field acceptance |
| MAIN/M01/source owners | Future source/M01 normalized-survey proof, sealing custody, upload/JSON/storage/API/UI/replay integration | Separate explicit design/authority; not supplied by this module |
| MAIN independent review | Exact-source engine/objective/KKT/covariance/leakage/control/resource replay | Authored controls/self-review not independent acceptance |

All legacy sources, gravity_forward.py/tests, environments, requirements and
historical three forward receipts are protected. No broad scientific source or
app edits, runtime package installs or implicit builder scripts are authorized.

## Future task order and requirements

| Task | Depends on | Requirements | Actual gate status |
| --- | --- | --- | --- |
| L2-A, MAIN full read / exact authority | Packet persisted/pinned | All16 | Implementation authorized; independent review remains pending |
| L2-B, Native admission and geometry-only plan | L2-A | L2-01..04,08,13,15 | Current core replay passed; independent replay pending |
| L2-C, Official objective, symmetric covariance, independent tiny R/J oracle | L2-B | L2-04..07,12 | 186 core and 81 precision/control tests passed on current source; independent pinned replay remains pending |
| L2-D, Exact recorded stop/terminal/null/cap mapping | L2-C | L2-07,11,14,15 | 186 core and 81 precision/control tests passed on current source; independent pinned replay remains pending |
| L2-E, All candidate folds and immutable separate outer evaluation | L2-D | L2-08..10,13 | 27 selection workflow tests and all 24 locked matrix cases passed locally; independent review remains open |
| L2-F, Complete locked24L2 and resource/control receipts | L2-E | L2-12,14,16 | Local 24/24 matrix and 40/40 resource samples passed; resource upper proof and host acceptance remain false; independent replay pending |
| L2-G, MAIN pinned independent replay/full diff | L2-F | All16 | NOT RUN; required before code merge |

Finish each approved unit's code/tests/theory/evidence together; no partial-engine
selector or successful synthetic scalar is declared complete. A failed prospective
gate retains exact bytes/config/source and prompts review, not threshold/candidate/
seed edits to hide it. Measured operational cap must not be inferred from G bytes.

## Explicit remaining broad M02 backlog

The following parent work remains incomplete and unapproved by this narrowed
unit; none is silently removed from PR120's accepted plan:

- Actual original-byte uploaded data decoding/normalized derivative binding,
  provider/M01 correction/CRS/vertical/geometry-uncertainty adjudication; robust
  missing-geometry/repeat measurement/full-field covariance/source rights seam.
- Topography/surface coverage/refinement, depth/sensitivity-weighted priors and
  alternative-mesh source admissions beyond the accepted ordinary outside-box rule.
- IRLS/sparse objectives, epsilon floors/schedules/null/stopping and matched L2
  comparison; uncertainty refits/calibration/coverage and complete48/96controls.
- Typed portable bundles/other-data CLI/export/re-import, rights-aware original
  storage, independent source runtime epochs and actual cancel/crash resources.
- Eligible measured field evidence; retain Bartlett's current negative, no
  synthetic replacement or assumed-error claim of field geology.
- Shared API/jobs/auth/storage/UI/course/wiki, GPU/local-extension and actual-host
  admission; full product convergence, main/release/canonical/version/deploy.

No issue is closed by docs/static success. MAIN decides plan readiness and later
authority after complete read; this agent does not merge/deploy.

## Approved additive terminal-certificate work

| Work item | State | Evidence and remaining gate |
| --- | --- | --- |
| Exact fixed-point certificate design | Approved by user; dated amendment recorded | `terminal-certificate-amendment-2026-11-02.md` |
| Versioned CPU2 candidate implementation and independent-result validator | Present in dirty checkout; candidate only | `gravity_irls_corrected.py`; do not treat as merged/promoted |
| Focused positive and adversarial tests | 36 tests passed on current source with reviewed single-thread environment, including the seven input-identity tamper cases | [`terminal-certificate-validation-2026-11-02.md`](terminal-certificate-validation-2026-11-02.md); first unpinned invocation failed at workspace admission and is excluded from solver evidence |
| Implicated archived-fold audit and separate seeded positive | Seeded non-null positive terminal route and adversarial controls pass in the 36-test exact-source suite; research-only archived weight/KKT audit remains diagnostic | The archived 12-fold audit does not exercise this terminal route; independent reproduction from original request/native archive remains required |
| Complete current-source matrix and resource gates | All 24 actual nodes selected a candidate; 22 passed held-out evaluation, and two initially exceeded the unchanged 120 s per-fit cap by 2.656 s and 0.047 s. Both fresh-root replay cases now pass under the same limits. The earlier 20+20 resource children had a stale solver source pin; a fresh exact-current-source 20+20 replay now passes with complete sampling (see dated validation ledger). Local aggregate `resource_upper_proof` and `host_accepted` remain false. | First launcher had a node-ID ordering mismatch; its eight nonexistent selectors are harness errors, excluded from solver evidence. Preserve the 1,800 s aggregate and 120 s per-fit limits. See the dated validation ledger. |
| Current exact-source CPU2 terminal-certificate matrix — 2026-11-02 | All 24 family/condition nodes passed; all selected candidates completed outer evaluation. 600 fit records, max individual wall 118.234 s, max calibration wall 867.844 s. Independent computational audit checked 208 terminal certificates across 24 source-matched archives. | Exact JUnit, archive and audit receipt hashes are in `terminal-certificate-validation-2026-11-02.md`. This does not replace external owner review, allocation upper-bound proof, host admission, or full M02/product acceptance. |
| Independent certificate reproduction | Open | Reviewer must calculate from original request and native archive without importing producer terminal decision |

The user-approved design does not waive any open validation row. The terminal
route remains ineligible for scientific selection or VPS promotion until all
gates pass.
