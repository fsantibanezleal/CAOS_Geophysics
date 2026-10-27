# Approved product and release status: 2026-10-27

This snapshot reconciles the approved product SDD, its 2026-10-03 operating
amendment, current product-branch evidence and the open implementation gates.
It supersedes the 2026-10-03 plan-status document only for current policy and
status. Historical receipts in that document remain historical evidence.

## Governing product and deployment decisions

- Product implementation follows the approved [SDD](SDD.md): the full M01–M13
  research and data workflow, public read-only exploration, authenticated
  multi-user/multi-project persistence and protected VPS jobs.
- Serve exactly one application from the existing ML VPS origin. GitHub remains
  the public source repository. GitHub Pages must remain withdrawn; no second
  application deployment or new hostname is part of this release.
- Retain the current release and two qualified rollback releases. A code
  rollback must preserve private project data and writes.
- SMTP, external email identity/reset, off-host backups and production-scale
  account administration are deferred. They are not release blockers for this
  owner-tested stage.
- VPS admission must be measured against this release, its three retained
  releases, current project data, configured job scratch and worker memory.
  The former whole-host 30% free-space threshold is superseded.
- Small initial projects constrain the measured workload; they do not reduce
  the required product functionality.

These decisions are also explicit in backlog issues #32, #61, #80 and #150.
The older plan-status text that lists SMTP, off-host recovery or a 30% host-wide
threshold as pending owner decisions must not be used to plan or block work.

## Current branch evidence

The isolated implementation branch is `task/geophysics-client-first-completion`
at `d7b5f0eb6eaad0094b98037cc31805bac4c94a51` as of 2026-10-27. It descends
from the M11 candidate workspace recovery work. Its
M11 work includes a source-bound gravity/magnetic joint inverse, independent
single-modality baselines, sealed selection/evaluation, a 24-control synthetic
matrix, resource controls and a strict local bundle importer. The actual local
M11 receipts are documented in
[`joint-survey-inversion/integration-status-20261025.md`](features/joint-survey-inversion/integration-status-20261025.md).

That evidence does not close M11 online execution. The current worktree adds
owner/project-scoped job, cancellation, result and export routes to the explicit
physical API assembly, plus a dedicated candidate worker that runs the pinned
Linux workflow CLI. Isolated candidate-schema API tests exercise admission,
cancellation, failed-result export, owner boundaries, terminal-result project
deletion, and a source-only delete against production descriptor-relative POSIX
storage. The exact 0006 migration remains outside the default serving chain, so
ordinary deployment databases fail closed at M11 admission. No M11 worker
service is installed. Request-time quota race qualification, process memory and
scratch enforcement, result-bearing restart/crash recovery, the full browser
contract and actual-host admission remain open. The workbench cannot yet offer a
released online solve. Do not label this vertical online-ready or scientifically
accepted.

The focused Linux M11 regression suite on this branch passed 488 tests with 3
skips on CPython 3.12.10 x86_64. A subsequent full 24-control Linux workflow
attempt did not complete and produced no qualifying matrix receipt; the earlier
complete Windows-hosted 24-control receipt remains the only full matrix result.
Do not infer Linux full-matrix acceptance from the focused suite or partial
attempt.

This review also verified a fresh production build, 318 frontend unit tests
with 11 skips, 3 Playwright workbench checks, and the CAOS browser gate across
142 measured states. The visual regression uses recorded station coordinates
to render non-overlapping survey glyphs and confirms distinct gravity and
magnetic model canvases. These are bounded UI/retention checks and do not close
the whole-product or ML-VPS gates.

## Current ML-VPS observation: 2026-10-25

Read-only SSH inspection of the deployment host (`89.167.4.175`) measured an
80,290,492,416-byte root filesystem with 34,615,701,504 bytes available (56%
used), and 5,253,431,296 bytes of available RAM. The canonical HTTPS origin
returned 200 and still served the `20260926235216` static release through
`current`; Nginx was active. No persistent `fasl-geophysics` systemd API
service is active, and the current Nginx product block serves the static root.
The just-built frontend `dist` contains 846,490,406 bytes (807.3 MiB); this is
only the static bundle size, not a qualified estimate for an API environment,
private project storage or solver scratch. Three unactivated `qual` release
directories each measure about 1.3 GiB. These observations establish present
disk and memory headroom, not worker, concurrency, crash-recovery or project
data capacity. No host files, services or release pointers were changed.

## Remaining release gates

1. **Full data-to-result verticals:** implement and independently qualify each
   promised method, input contract, provenance, processing/inversion, result
   inspection and export. Keep methods unavailable when required input, source
   rights, solver, resource or scientific gates are absent.
2. **Persisted M11 service path:** integrate its native member and dataset
   contracts with owner/project authorization, bounded worker submission,
   cancellation, source custody, quotas, result publication, deletion and
   export. Pass real API and browser tests using authentic solver outputs.
3. **Data and science acceptance:** complete rights-aware acquisition and
   reproducible processing for the advertised cases; retain ineligible cases
   and failures. Update the method matrix only from exact executed receipts.
4. **Product UI and documentation:** complete the six approved routes, CAOS
   shell and ADR styles, responsive scientific views, method-specific
   interactions, bilingual wiki/course coverage and real user-data workflows.
5. **Actual-host qualification:** measure the integrated release on the ML VPS:
   authenticated ownership, CPU/memory/scratch/time bounds, cancellation and
   crash recovery, concurrent public-read responsiveness, TLS/API/browser
   behavior, adequate disk for three releases and applicable project/runtime
   storage, with code rollback preserving project writes.
6. **Single-origin cutover:** promote through the repository's approved branch
   flow only after scientific, UI, data and actual-host gates pass; deploy one
   VPS release, verify its exact source/release/live receipts, retain the two
   qualified rollback releases, and verify the retired Pages publication stays
   absent.

The convergence ledger remains the authority for per-requirement verdicts. A
clean build, local synthetic matrix, HTTP 200, or successful VPS health check
does not by itself complete the replacement release.

## Sequential worker workspace regression: 2026-10-26

The candidate worker previously rejected any non-empty shared workspace root,
so one preserved interrupted job could permanently prevent later jobs from
running. The root now permits up to 127 retained entries, preserves them
without adoption or deletion, and refuses new work after that bound. The
focused regression passes on the Linux candidate environment. This does not
qualify scratch enforcement, crash recovery, service integration or VPS use.

The candidate worker now applies one shared 1,800-second deadline across its
runtime verifier, solve, validation, result instrument and instrument replay;
previously each child received a fresh 1,810-second allowance. The focused
Linux subprocess test verifies process-group termination at the shared
deadline. This is a job wall-time bound, not actual-host admission evidence.

The physical worker loop now checks the exact candidate schema under both
existing worker locks, dispatches one M11 job only on canonical
`0006_joint_artifacts`, and excludes M11 from the legacy claimant on that
schema. The 0005 no-dispatch, candidate dispatch, and legacy-claim exclusion
tests pass on the Linux candidate runtime. The normal service still has no
production operator binding that supplies the required `PhysicalAssembly`,
and no M11 unit is installed on the VPS; this is not online availability.

## Public origin recheck: 2026-10-26

Read-only HTTPS inspection returned HTTP 200, HTML title `Inverse Earth Studio |
Geophysics`, and `Last-Modified: Sat, 26 Sep 2026 23:46:49 GMT`. The existing
legacy frontend remains live; this branch has not been deployed or cut over.

## Operator-bound API and worker assembly: 2026-10-26

The candidate now contains a read-only operator-binding loader. It validates a
strict registry digest, its exact installed `release.json` digest, the
pre-existing private root/database and both fixed lock identities. It neither
creates or repairs files nor changes a schema or account. API and worker
entrypoints select the physical assembly only when both
`GEOPHYSICS_PHYSICAL_BINDING_PATH` and
`GEOPHYSICS_PHYSICAL_BINDING_SHA256` are supplied; partial configuration
fails closed. The API and worker release their retained descriptors on
shutdown. This makes the route/worker integration executable for a properly
provisioned candidate, but does not create the binding or qualify any method.
Linux operator-binding and physical-assembly lifecycle tests pass 16/16; Ruff
and whitespace checks pass. Windows cannot execute the POSIX lock qualification.

No production binding file, reviewed source-policy registry, initialized
physical locks, compatible service database, M11 systemd unit, or actual-host
admission receipt has been installed. Existing bootstrap and activation
contracts do not yet provision or admit this binding. The active VPS remains
the legacy static release described above. No deployment or cutover occurred.

## Supplied ERT profile result view: 2026-10-27

The branch adds a method-specific view for locally admitted Slagdump M07
results. It draws the supplied electrode elevations and selected original
ABMN quadrupole, plots observed and frozen-predicted transfer resistance with
the declared assumed sigma, identifies held-out observations, and shows
signed residuals and retained QC flags. The interface explicitly withholds
apparent resistivity, geometric factors and instrumental errors that are not
present in the input/result contract. Plot-card sizing follows the existing
CAOS scientific-plot module, including the phone note/QC spacing fix.

Evidence on the current build: the ERT result-view and supplied-profile tests
pass 17 with 2 fixture-gated skips; the production frontend build succeeds;
the local browser suite passes all 3 groups against actual Slagdump and
Koenigsee results. Its English/light desktop and Spanish/dark phone captures
cover ERT and travel-time mesh/residual views. The browser run records no page
errors, API writes, physics replay or changes to the pinned local result files.
The implementation is committed as `d7b5f0e` and pushed to PR #151; GitHub
reports no checks for that PR. The approved SDD remains much broader than this
one local-result view.

The convergence script still reports 1 failed and 18 unresolved requirements.
No current release passes, no host deployment occurred, and the origin
`https://geophysics.ml.fasl-work.com/` still returns the legacy static release
(HTTP 200; `Last-Modified: 2026-09-26 23:46:49 GMT`). No Pages publication or
second deployment was created.
