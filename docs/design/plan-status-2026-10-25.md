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
at `76ee160b5f0d7c3efd47b76c282cbdd7a1312871` at the start of this review. Its
M11 work includes a source-bound gravity/magnetic joint inverse, independent
single-modality baselines, sealed selection/evaluation, a 24-control synthetic
matrix, resource controls and a strict local bundle importer. The actual local
M11 receipts are documented in
[`joint-survey-inversion/integration-status-20261025.md`](features/joint-survey-inversion/integration-status-20261025.md).

That evidence does not close M11 online execution. The current FastAPI app does
not register the M11 member, dataset, job, cancellation, custody-history or
export routes expected by the project workbench. Its existing retention schema
refuses nonempty joint extension tables until complete custody, accounting and
deletion adapters are wired. The workbench therefore cannot yet take a user's
gravity and magnetic survey through an online solve. Do not label this vertical
online-ready or scientifically accepted.

The M11 local suite is being rerun on this branch during this review. Its result
will be recorded only after process completion; prior receipts are not a
substitute for this run.

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
