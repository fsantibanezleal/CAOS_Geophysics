# L2 sub-SDD ownership and dependency backlog

Status: planned. This task authorizes ONLY new feature docs plus primary research.
MAIN complete review and explicit code/test authority still pending; no numerical
gate executed. Base `1b112bb258520a5679a865335cec30b6a97a1a0d`.

Parent references: [product SDD M02](../../SDD.md), [unchanged PR120 tasks](../m02-survey-inversion/tasks.md),
[accepted PR122 forward](../m02-prism-operator/tasks.md),
[BL-012/#44](https://github.com/fsantibanezleal/CAOS_Geophysics/issues/44),
[parent #32](https://github.com/fsantibanezleal/CAOS_Geophysics/issues/32).
Related M01 [BL-011/#43](https://github.com/fsantibanezleal/CAOS_Geophysics/issues/43)
and [strict JSON design #124](https://github.com/fsantibanezleal/CAOS_Geophysics/issues/124)
are NOT activated or closed by this native-array sub-SDD. No shared-owner edits.

## Review packet and mandatory hold

- [x] Inspect actual current forward/legacy inverse/intake/M01 sources and parent
  plan, not infer completeness from names. Primary research and source findings
  persisted BEFORE contract/design: [dossier](../../../research/m02-survey-l2-2026-10-03.md),
  [source inspection receipt](../../../research/m02-survey-l2-evidence-2026-10-03.json).
- [x] Freeze separately reviewable exact native [contract](contract.md),
  [objective/optimizer/results/ownership](design.md), [16 EARS requirements](requirements.md)
  and [prospective control/tolerance/seed matrix](validation.md). These are authored
  documents, NOT approved numerical policy or executed gates.
- [ ] MAIN fully reads ALL packet files and exact diff; approves source/frame/
  error declaration boundary, covariance symmetric-root policy, normalization,
  split minima/algorithm, beta grid/seeds, KKT/native stop mapping, caps/outputs.
- [ ] MAIN explicitly authorizes exact prospective code/test paths and independent
  acceptance responsibilities. No code/test starts before this separate authority.

## Prospective bounded implementation paths, unapproved

| Owner | Proposed new paths | Boundary |
| --- | --- | --- |
| M02 sidecar | data-pipeline/gravity_survey_l2.py; tests/data/test_gravity_survey_l2.py | Exact native admission/hash/geometry-only split, no JSON/upload/I/O/provider corrections |
| M02 sidecar | data-pipeline/gravity_l2.py; tests/numerics/test_gravity_l2.py; tests/numerics/test_gravity_l2_selection.py | Official fixed L2/calibration/evaluation, private recorded stop mapping; no IRLS/API/hook/export |
| M02 sidecar | This feature docs and later own dated evidence | Preserve parent/accepted forward/receipts, no ledger/version/canonical mutation |
| MAIN/M01/source owners | Future source/M01 normalized-survey proof, sealing custody, upload/JSON/storage/API/UI/replay integration | Separate explicit design/authority; not supplied by this module |
| MAIN independent review | Exact-source engine/objective/KKT/covariance/leakage/control/resource replay | Authored controls/self-review not independent acceptance |

All legacy sources, gravity_forward.py/tests, environments, requirements and
historical three forward receipts are protected. No broad scientific source or
app edits, runtime package installs or implicit builder scripts are authorized.

## Future task order and requirements

| Task | Depends on | Requirements | Actual gate status |
| --- | --- | --- | --- |
| L2-A, MAIN full read / exact authority | Packet persisted/pinned | All16 | Awaiting review, no numerical PASS |
| L2-B, Native admission and geometry-only plan | L2-A | L2-01..04,08,13,15 | NOT RUN; no new code/tests |
| L2-C, Official objective, symmetric covariance, independent tiny R/J oracle | L2-B | L2-04..07,12 | NOT RUN |
| L2-D, Exact recorded stop/terminal/null/cap mapping | L2-C | L2-07,11,14,15 | NOT RUN |
| L2-E, All candidate folds and immutable separate outer evaluation | L2-D | L2-08..10,13 | NOT RUN |
| L2-F, Complete locked24L2 and resource/control receipts | L2-E | L2-12,14,16 | NOT RUN; negatives retained |
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
