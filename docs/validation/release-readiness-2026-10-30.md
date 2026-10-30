# Replacement release readiness, 2026-10-30

Assessed product branch: `task/geophysics-client-first-completion`, pushed through `43f4f9b`. PR #151 remains a draft. The working tree also contains extensive uncommitted implementation; this assessment does not treat those files as part of the pushed source.

## Checks that pass

| Check | Result | Boundary |
|---|---|---|
| CAOS Product SDD structure | `check_sdd.py`: 538 live requirements have executable gates; 27 planned requirements/gates remain unbuilt | Structural completeness does not prove the science or service works. |
| Method matrix | 13/13 structural method gates are present | `scientific_acceptance=false`. |
| Notebook structure | 60 English/Spanish notebooks are mirrored, ordered, annotated, and clean | A fresh-kernel replay executed all 60 without execution errors; three stale figures were refreshed and their focused replays passed. |
| Shell adoption | Exact shell 0.19.9 pin, production build, six route tests, and 1,442-state browser gate pass | 157 captures, no waivers or failures; shared-shell integration only. |
| Case and condition rendering | Full local browser sweep covers 20 case families × 6 experiment conditions; all 20 families expose six distinct metric views and no browser/layout failures; [full measured report](case-condition-viewport-2026-10-30.json) | 18 physical/joint families render six distinct visual states each; learned families render four distinct reconstructions and six distinct metric views. The report records that it was measured from a dirty working tree. This validates rendering/data selection, not scientific accuracy or a release commit. |
| M02 locked controls | Retained Windows CPU matrix records 24/24 locked cases passing; its report validator passes 4/4 tests, and the current forward identity test passed | The only current gravity-L2 source delta is a corrected `FORWARD_SOURCE` hash matching the unchanged forward implementation; the matrix report remains historical evidence from 2026-10-29. |
| Deployment-origin source guard | `check_single_origin.py`: pass | Source/build policy only; not live deployment acceptance. |
| Local accounting/service controls | `test_protocol.py` and the single-VPS adversarial suite pass, with one skip | These do not establish native Windows/Linux containment or actual-host admission. |

## Release blockers

1. The fixture-backed frontend suite reports 429 passed and 12 skipped. Two magnetic suites fail during setup because the original selected-final extraction control and owned-custody browser-control file are unavailable at their recorded paths. No substitute was created.
2. The retained 24-case joint output records `scientific_precision_accepted=false`, `field_eligible=false`, and `public_activation=false`. The method matrix therefore remains structural only.
3. The convergence ledger now validates structurally against the current SDD and evidence hashes. It still records 18 unresolved requirements and one failed requirement (`R-008`, scientific acceptance); `--require-release` therefore fails correctly until those outcomes are accepted. The ledger assessment revision is `43f4f9bc68699bd1090406688b50ffd1a73a87a9` (2026-10-30).
4. `check_manuscripts.py` fails: `product.json` has no technical-report declaration. A report draft is being prepared; no Zenodo DOI or publication is claimed.
5. The live VPS is still serving `0.04.001`; Nginx is active and the geophysics API/worker are inactive. The 2026-10-30 measured free disk is 902,692,864 bytes, below the runtime stager's 4 GiB precondition. See [the read-only host receipt](actual-host-capacity-readonly-2026-10-30.md).
6. Full actual-host API/worker isolation, user-data workflows, capacity/job admission, and post-deployment verification have not passed. Current plus two rollback releases remain intact.

## Release decision

Do not stage or activate a replacement while these gates are open. The single canonical origin is `https://geophysics.ml.fasl-work.com/`; GitHub Pages is disabled. SMTP and off-host backup are not release prerequisites. Resume candidate admission only after the exact source and convergence ledger are reconciled, scientific and custody findings are resolved, the technical report has a verified real record, actual host capacity meets the measured runtime requirements, and the complete API/worker/browser/rollback acceptance passes.
