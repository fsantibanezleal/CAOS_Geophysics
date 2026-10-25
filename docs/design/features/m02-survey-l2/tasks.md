# L2 sub-SDD ownership and dependency backlog

Status: local implementation gates executed 2026-10-25. The scoped supporting suite
passed 213 tests without skips; all 24 locked external-control conditions passed.
See [validation](validation.md) and the immutable [execution receipt](evidence/local-matrix-execution-20261025.json).
Independent pinned review and broader product/field acceptance remain pending.
Base `1b112bb258520a5679a865335cec30b6a97a1a0d`.

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
  and [control/tolerance/seed matrix](validation.md). The thresholds remain frozen;
  execution evidence is recorded separately from policy.
- [x] The owner explicitly instructed implementation and validation of all pending
  approved product work on 2026-10-25. This authorizes work within the product
  scope; it does not waive any frozen scientific gate or independent review.
- [ ] Independent reviewer verifies the exact packet/source diff, source/frame/
  error declarations, covariance, split, candidate grid, stopping policy and
  output contract against the fresh receipts before this unit is accepted.

## Implemented local ordinary-L2 paths and boundaries

| Owner | Proposed new paths | Boundary |
| --- | --- | --- |
| Local M02 ordinary-L2 | data-pipeline/gravity_survey_l2.py; tests/data/test_gravity_survey_l2.py | Exact native admission/hash/geometry-only split; excludes JSON/upload/I/O/provider corrections |
| Local M02 ordinary-L2 | data-pipeline/gravity_l2.py; tests/numerics/test_gravity_l2.py; tests/numerics/test_gravity_l2_selection.py | Official fixed L2/calibration/evaluation and private recorded stop mapping; excludes IRLS/API/hooks/export |
| Evidence | This feature's dated execution receipt | Source/input/outcome/JUnit/log identities; no canonical artifact or release mutation |
| Remaining product scope | Source/M01 normalized-survey proof, sealing custody, upload/JSON/storage/API/UI/replay | Outside this local numerical unit; must be implemented and separately accepted |
| Independent review | Exact-source engine/objective/KKT/covariance/leakage/control/resource replay | Still pending; local authored tests are not independent acceptance |

All legacy sources, gravity_forward.py/tests, environments, requirements and
historical three forward receipts remain protected. This local unit does not edit
those sources, install runtimes or invoke implicit artifact builders.

## Future task order and requirements

| Task | Depends on | Requirements | Actual gate status |
| --- | --- | --- | --- |
| L2-A, MAIN full read / owner authority | Packet persisted/pinned | All16 | Owner authorized the scoped work; independent review remains pending |
| L2-B, Native admission and geometry-only plan | L2-A | L2-01..04,08,13,15 | Local named controls passed in the 213-test receipt |
| L2-C, Official objective, symmetric covariance, independent tiny R/J oracle | L2-B | L2-04..07,12 | Local named controls passed in the 213-test receipt |
| L2-D, Exact recorded stop/terminal/null/cap mapping | L2-C | L2-07,11,14,15 | Local named controls passed in the 213-test receipt; operational p95 not established |
| L2-E, All candidate folds and immutable separate outer evaluation | L2-D | L2-08..10,13 | Local named controls passed in the 213-test receipt |
| L2-F, Complete locked24L2 and resource/control receipts | L2-E | L2-12,14,16 | 24/24 local synthetic outcomes passed; per-case outcomes and hashes retained; no field claim |
| L2-G, MAIN pinned independent replay/full diff | L2-F | All16 | NOT RUN; required before code merge |

Finish each approved unit's code/tests/theory/evidence together; no partial-engine
selector or successful synthetic scalar is declared complete. A failed prospective
gate retains exact bytes/config/source and prompts review, not threshold/candidate/
seed edits to hide it. Measured operational cap must not be inferred from G bytes.

## Explicit remaining broad M02 backlog

The following broader parent work remains incomplete outside this local ordinary
L2 unit; none is silently removed from PR120's accepted plan:

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

No parent issue or product requirement is closed by this local pass. Independent
review and remaining product gates are required before release or deployment.
