# Replacement plan and scoped repository state

Assessment: 2026-10-03. Product SDD: [approved design](SDD.md). This is an implementation-state review, not final scientific convergence or a deployment receipt.

## Revisions and preservation

After fetching the product remote at 07:08 UTC, `origin/develop` is `afac8ab7b0be2df474406d1b17f0a165be9e0599`. Its [CI run 37104931366](https://github.com/fsantibanezleal/CAOS_Geophysics/actions/runs/37104931366) completed successfully. Scoped PRs #98 (ledger), #99 (station corrections), #103 (real project gravity-QC workbench) and #104 (pinned source intake) are merged. `origin/main` is `39813230478ed53bf5eb29cc21f07ed568767c64`: legacy 0.04.001. No rebuild release has been promoted or deployed. The public tracker contains 49 open issues, including parent #32 and 48 implementation/acceptance children. Approval is already recorded; their old "blocked until plan validation" prose is stale, not a renewed approval requirement.

| Worktree purpose | Branch state at review | Action and boundary |
| --- | --- | --- |
| Browser M13/API foundation | PR #95 and #103 merged; new isolated MT scientific-workbench task | Trained-model export, owner processing and browser evidence preserved. M05/M06 scientific controls are being added separately. |
| Phase pipeline | PR #84 merged; tracked work clean | Private waveform/checkpoint/oracle data remain ignored. No retraining or sealed-test resampling. |
| Wiki foundation | PR #96 merged; pre-existing untracked browser test output | Protect unrelated test output; merged source-to-result documentation is retained. |
| FWI regression | Pushed draft PR #97, `f97a971`; candidate assembler resumed | Optimizer/replay fixes and independently tested 24-case candidate preserved. Combine fresh MT outputs with all 120 cases before canonical import. |
| Online EDI/MT | Pushed draft PR #100, `0970a09`; actual 24-case source reconciliation preserved | Default admission remains closed. Main review and combined artifact regression precede integration; no stale source-hash relabelling. |
| Actual-host admission | Pushed draft PR #101, `6d291f4` | Restricted private Linux runs measured and preserved. Six controls pass; forty-job nominal distribution fails unchanged disk gate. No listener or production mutation. |
| Backup/restore | Pushed PR #102, `02378f1`; explicit MT adapter continuation | Strict gravity-only local unit preserved. M05/M06 restore compatibility and actual-host drill remain pending; unknown variants stay rejected. |
| Station corrections and source intake | PRs #99/#104 merged | 29 correction tests and 79 data checks independently rerun. Author field bytes remain physically ineligible; new gridding/continuation work uses a separate task. |
| Product checkout | Historical evidence branch `3f5de5b`, tracked clean | Do not repurpose its historical branch or overwrite its local data. New convergence work is isolated. |
| Older EDI/architecture audits | Clean, non-ancestor commits, but `git cherry` reports their patches already integrated | No duplicate cherry-pick or blind promotion. Preserve their branches and reference evidence. |

Local `develop` and `main` references were fast-forward fetched to their matching remote revisions without checking out or pushing the promotion-only branch. Historical task branches retain their identities; synchronizing the project is not rewriting every old feature branch to develop.

Historical feature task lists describe their own narrower units. In particular [the old rebuild checklist](features/rebuild/tasks.md) is not an acceptance checklist for this SDD. Completed local units do not close whole-product requirements, field rights, host tests, or visual acceptance.

## Method status against the current promise

| ID | Retained executable/evidence | Remaining acceptance work |
| --- | --- | --- |
| M01 | Flag-only owner worker/UI; merged explicit normal/plate/terrain/reference/uncertainty station controls; pinned 2,929-row author-source profile | Equivalent-source/continuation chain, compatible field heights/errors, complete API lineage and independently validated maps. Missing values and duplicate diagnostics remain; no fabricated field eligibility. |
| M02 | Original synthetic 3D prism/weighted spatial inverse | Strict submitted-survey workflow, gravity field case, independent holdouts and host admission. |
| M03 | Raw magnetic envelope and local source ledger | Real flight/tie line processing, height/correction QC, blocked gridding validation and field case. |
| M04 | Original induced-field synthetic forward/inverse | Uploaded field-vector/geometry contract, remanence controls, field workflow and bounded online admission. |
| M05 | Full EDI parser/screens; draft owned immutable QC worker and fresh synthetic source reconciliation | Reviewed canonical candidate, online typed tensor instrument, multistation analysis and complete actual-host gate. Default admission is closed. |
| M06 | Draft bounded multistart inverse with frozen holdouts/halfspace controls, conditional bootstrap and actual-host job samples | Combined candidate acceptance, full scientific UI/export, passing host headroom and operational restore. cl061 is freshly screened QC-only; no substituted field geology. |
| M07 | Local topographic Slagdump adapter, parser, homogeneous/topography and heldout tests | Rights-controlled field release, full uploaded-electrode workflow, linked instrument and measured host limits. |
| M08 | Matched classical comparator on locked STEAD traces | MiniSEED/StationXML response/epoch chain, catalogue arrivals and meaningful per-waveform user-data analysis. A weak baseline remains visible, not reclassified as successful. |
| M09 | Local Koenigsee tomography, pinned CGLS controls and independent repeats | Rights-controlled field release, uploaded survey UI/worker, source/receiver/ray/residual/coverage views and host admission. |
| M10 | Draft explicit LBFGS evaluation budget/deterministic replay fix, fresh 24-case bake and 48 CUDA replay controls | Combined 120-case acceptance, complete local FWI inputs/results/course and actual physical playback. Failed/unresolved salt controls remain visible. |
| M11 | Matched independent and coupled original synthetic inverses | Accepted uploaded co-registration/weights/coupling contract and field study, disjoint-source controls and deep scientific interface. |
| M12 | Actual trained checkpoint and complete negative family/acquisition benchmark | Learned seismic inversion remains unaccepted: the retained checkpoint loses to the matched classical model. A new predeclared protocol requires new untouched holdouts. |
| M13 | Frozen real STEAD training/test, event/station separation, 23 valid browser records, one retained flat rejection and Chromium probability parity | Complete release integration, named end-to-end gates, full visual matrix and public one-origin deployment. Scores are uncalibrated and evidence is within STEAD, not cross-dataset field validation. |

M13 local browser maximum probability error is `4.41e-6` with no sample shift, from the [merged export verification](features/m13-browser/design.md). This does not change the negative M12 finding or fill other method cells. Every scientifically failed, ineligible or not-run case is retained separately.

## Requirements and release blocker

[convergence.json](convergence.json) records all 19 current requirements, bound to the exact SDD digest and assessed source revision. Its initial verdict is 18 unresolved and R-008 failed because complete M01-M13 acceptance is absent and M12 failed its efficacy gate. Unresolved does not mean no code exists: it means the entire requirement's stated oracle has not passed. The structural checker accepts an honest incomplete ledger; `--require-release` must reject it.

Read-only VPS inspection at 2026-10-03 05:47:51 UTC found nginx active, current immutable release `20260926235216`, 7,751 MiB total/4,962 MiB available RAM, 624 MiB used swap and about 23 GiB free root disk. This is a host snapshot, not performance/admission evidence or external TLS/browser verification. GitHub's Pages API still identifies the legacy application URL. No API service was publicly activated and no second replacement site was created.

Actual-host isolated MT admission subsequently ran under DynamicUser, private state/network, one-library-thread and explicit cgroup/process/file limits. All 40 nominal jobs completed: M05 p95 wall 8,651 ms/RSS 245,182,464 bytes; M06 p95 wall 8,511 ms/RSS 247,214,080 bytes. These calculations do not pass the overall gate: minimum free disk was 23,622,492,160 / 80,290,492,416 bytes (29.42%), below the unchanged 30% requirement. A separate six-test run passed upper-bound, malformed input, cancellation, limit and actual worker-kill/recovery controls in 114.75 s. The measured concurrent reads are private TestClient traffic, not public HTTP/TLS validation. [Draft PR #101](https://github.com/fsantibanezleal/CAOS_Geophysics/pull/101) preserves commands, source pins, hashes and honest non-claims. No old releases or private admission outputs were deleted.

Owner questions remain open for final identity, lossless compression of obsolete geophysics-only releases (active plus two latest rollback releases preserved), and an approved mail provider/sender. Pending choices do not stop isolated method work, but no preselected option is authorization and no cutover can bypass these dependencies.

Next dependency sequence: recover and validate isolated numerical/backend edits; connect real authenticated processing/results; finish the scientific verticals, data acquisition and deep course; run complete numerical and visual case matrices; benchmark admitted jobs on the actual VPS; verify backup/restore and secure operations; select the final owner-approved identity; promote the accepted replacement, verify one VPS origin, then withdraw Pages. The public release is not ready while any of these accepted gates remain open.

## Use the acceptance checker

```powershell
python tests/test_sdd_convergence.py
python scripts/check_sdd_convergence.py
python scripts/check_sdd_convergence.py --require-release
```

The final command deliberately exits nonzero today. A gate receipt must identify the exact requirement, executable gate source hash, assessed source revision, real invocation and hashed measured outputs. Documentation notes, file presence or a build result cannot manufacture one. The checker validates identity/coverage/integrity; domain numerics, resource tests and rendered user experience still require their independent oracles.
