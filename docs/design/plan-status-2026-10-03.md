# Replacement plan and scoped repository state

Assessment: 2026-10-03. Product SDD: [approved design](SDD.md). This is an implementation-state review, not final scientific convergence or a deployment receipt.

## Revisions and preservation

After fetching the product remote, `origin/develop` is `dce92a1d8693afd60a33ff429dfff59cad4de64d`. Its [CI run 36403768573](https://github.com/fsantibanezleal/CAOS_Geophysics/actions/runs/36403768573) completed successfully. `origin/main` is `39813230478ed53bf5eb29cc21f07ed568767c64`: legacy 0.04.001. No rebuild release has been promoted or deployed. The public tracker contains 49 open issues, including parent #32 and 48 implementation/acceptance children. Approval is already recorded; their old "blocked until plan validation" prose is stale, not a renewed approval requirement.

| Worktree purpose | Branch state at review | Action and boundary |
| --- | --- | --- |
| Browser M13/API foundation | PR #95 merged; local branch fast-forwarded to current develop | Trained-model export and browser integration preserved. New lifecycle jobs work uses a separate task branch. |
| Phase pipeline | PR #84 merged; tracked work clean | Private waveform/checkpoint/oracle data remain ignored. No retraining or sealed-test resampling. |
| Wiki foundation | PR #96 merged; pre-existing untracked browser test output | Protect unrelated test output; merged source-to-result documentation is retained. |
| FWI regression | Pushed WIP `f2bb280` plus five edited files and one untracked numerical receipt | Resume isolated numerical investigation. Do not discard dirty edits, weaken recovery gates or call WIP releasable. |
| Online EDI/MT | Branch based on `d1afb17`, with edited backend/parser files and new contracts/tests/docs | Resume isolated bounded MT implementation; protect test scratch and originals. Integrate newer develop only after accounting for partial edits. |
| Product checkout | Historical evidence branch `3f5de5b`, tracked clean | Do not repurpose its historical branch or overwrite its local data. New convergence work is isolated. |
| Older EDI/architecture audits | Clean, non-ancestor commits, but `git cherry` reports their patches already integrated | No duplicate cherry-pick or blind promotion. Preserve their branches and reference evidence. |

Local `develop` and `main` references were fast-forward fetched to their matching remote revisions without checking out or pushing the promotion-only branch. Historical task branches retain their identities; synchronizing the project is not rewriting every old feature branch to develop.

Historical feature task lists describe their own narrower units. In particular [the old rebuild checklist](features/rebuild/tasks.md) is not an acceptance checklist for this SDD. Completed local units do not close whole-product requirements, field rights, host tests, or visual acceptance.

## Method status against the current promise

| ID | Retained executable/evidence | Remaining acceptance work |
| --- | --- | --- |
| M01 | Flag-only station outlier worker with immutable inputs and threshold effect | Physical correction/reference/transform chain, compatible field stations, complete lineage, online instrument and independent oracle. Robust flags are not corrected gravity. |
| M02 | Original synthetic 3D prism/weighted spatial inverse | Strict submitted-survey workflow, gravity field case, independent holdouts and host admission. |
| M03 | Raw magnetic envelope and local source ledger | Real flight/tie line processing, height/correction QC, blocked gridding validation and field case. |
| M04 | Original induced-field synthetic forward/inverse | Uploaded field-vector/geometry contract, remanence controls, field workflow and bounded online admission. |
| M05 | Full EDI parser and measured Clear Lake/AusLAMP tensor screens | Online typed EDI lineage/QC, rotation/masks/error cross-checks, multistation instruments and actual-host gate. |
| M06 | Layered synthetic inverses and retained negative field screening | Eligible uploaded-EDI inverse, independent complex-impedance oracle, multistart/holdout/parameter sensitivity and server admission. cl061 is QC-only; no substituted field geology. |
| M07 | Local topographic Slagdump adapter, parser, homogeneous/topography and heldout tests | Rights-controlled field release, full uploaded-electrode workflow, linked instrument and measured host limits. |
| M08 | Matched classical comparator on locked STEAD traces | MiniSEED/StationXML response/epoch chain, catalogue arrivals and meaningful per-waveform user-data analysis. A weak baseline remains visible, not reclassified as successful. |
| M09 | Local Koenigsee tomography, pinned CGLS controls and independent repeats | Rights-controlled field release, uploaded survey UI/worker, source/receiver/ray/residual/coverage views and host admission. |
| M10 | Acoustic/adjoint and original CUDA replay evidence | Resolve fresh-process optimizer regression, revalidate independent numerics, complete local FWI inputs/results/course and actual physical playback. |
| M11 | Matched independent and coupled original synthetic inverses | Accepted uploaded co-registration/weights/coupling contract and field study, disjoint-source controls and deep scientific interface. |
| M12 | Actual trained checkpoint and complete negative family/acquisition benchmark | Learned seismic inversion remains unaccepted: the retained checkpoint loses to the matched classical model. A new predeclared protocol requires new untouched holdouts. |
| M13 | Frozen real STEAD training/test, event/station separation, 23 valid browser records, one retained flat rejection and Chromium probability parity | Complete release integration, named end-to-end gates, full visual matrix and public one-origin deployment. Scores are uncalibrated and evidence is within STEAD, not cross-dataset field validation. |

M13 local browser maximum probability error is `4.41e-6` with no sample shift, from the [merged export verification](features/m13-browser/design.md). This does not change the negative M12 finding or fill other method cells. Every scientifically failed, ineligible or not-run case is retained separately.

## Requirements and release blocker

[convergence.json](convergence.json) records all 19 current requirements, bound to the exact SDD digest and assessed source revision. Its initial verdict is 18 unresolved and R-008 failed because complete M01-M13 acceptance is absent and M12 failed its efficacy gate. Unresolved does not mean no code exists: it means the entire requirement's stated oracle has not passed. The structural checker accepts an honest incomplete ledger; `--require-release` must reject it.

Read-only VPS inspection at 2026-10-03 05:47:51 UTC found nginx active, current immutable release `20260926235216`, 7,751 MiB total/4,962 MiB available RAM, 624 MiB used swap and about 23 GiB free root disk. This is a host snapshot, not performance/admission evidence or external TLS/browser verification. GitHub's Pages API still identifies the legacy application URL. No API service was publicly activated and no second replacement site was created.

Next dependency sequence: recover and validate isolated numerical/backend edits; connect real authenticated processing/results; finish the scientific verticals, data acquisition and deep course; run complete numerical and visual case matrices; benchmark admitted jobs on the actual VPS; verify backup/restore and secure operations; select the final owner-approved identity; promote the accepted replacement, verify one VPS origin, then withdraw Pages. The public release is not ready while any of these accepted gates remain open.

## Use the acceptance checker

```powershell
python tests/test_sdd_convergence.py
python scripts/check_sdd_convergence.py
python scripts/check_sdd_convergence.py --require-release
```

The final command deliberately exits nonzero today. A gate receipt must identify the exact requirement, executable gate source hash, assessed source revision, real invocation and hashed measured outputs. Documentation notes, file presence or a build result cannot manufacture one. The checker validates identity/coverage/integrity; domain numerics, resource tests and rendered user experience still require their independent oracles.
