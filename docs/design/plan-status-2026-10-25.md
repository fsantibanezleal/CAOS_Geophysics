# Approved product and release status — 2026-10-25

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
at `1d90428307c4b710c7cb165a849ae11fe790c089` at the start of this review. Its
M11 work includes a source-bound gravity/magnetic joint inverse, independent
single-modality baselines, sealed selection/evaluation, a 24-control synthetic
matrix, resource controls and a strict local bundle importer. The actual local
M11 receipts are documented in
[`joint-survey-inversion/integration-status-20261025.md`](features/joint-survey-inversion/integration-status-20261025.md).

That evidence does not close M11 online execution. The current FastAPI app does
not register the M11 member, dataset, job, cancellation, custody-history or
export routes expected by the project workbench. The current classifier now
audits exact M11 originals, datasets, result members and indices in one
snapshot and adds retained/active charges through that audit. Request-time
admission, startup reconciliation and M11-aware deletion receipts remain
unintegrated; deletion explicitly refuses projects containing M11 state. The
workbench therefore cannot yet take a user's gravity and magnetic survey
through an online solve. Do not label this vertical online-ready or
scientifically accepted.

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

## Current ML-VPS observation — 2026-10-25

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
