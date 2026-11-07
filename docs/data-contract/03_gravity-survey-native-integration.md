# Gravity survey native integration manifest

This lists the executable numerical boundary and the mounting contract, not an
activated API. Keep protected profiles, queued M08 and MT in the controller's
existing registry. Do not replace shared Workbench or this branch's older API
files over the controller's current dispatcher.

| Operation | Existing product export | Exact native contract |
| --- | --- | --- |
| Geometry plan | `gravity_survey_l2.plan_gravity_l2` | `gravity-survey-l2-plan-request-1`; no measurements |
| L2 calibration | `gravity_l2.calibrate_gravity_l2` | `gravity-survey-l2-calibration-request-1`; epoch `m02-survey-l2-cpu-5` |
| IRLS calibration | `gravity_irls.calibrate_gravity_irls` | `gravity-survey-irls-calibration-request-1`; epoch `m02-survey-irls-cpu-1` |
| Original-noise corrected IRLS | `gravity_irls_original.calibrate`, `validate` | Original-calibration-request/result-1; epoch `m02-survey-irls-cpu-3`, distinct from old archives |
| Original-noise fixed partition | `gravity_irls_original.solve_partition`, `validate_partition` | Original physical request/observations/noise/prior/rows/beta/policy; no supplied operator or callback |
| Original-noise frozen outer | `gravity_irls_original.evaluate` | Original-evaluation-request/result-1, complete frozen request/result; no optimization |
| Calibration replay | `gravity_workflow_io.verify_calibration` | `gravity-calibration-archive-1`, complete original request/result |
| Frozen outer evaluation | `gravity_workflow_io.evaluate` | L2 evaluation-request-2 or IRLS evaluation-request-3, including original calibration request |
| Outer replay | `gravity_workflow_io.verify_evaluation` | `gravity-evaluation-archive-1`; no optimizer |
| Actual noise refits | `gravity_noise_refits.refit_gravity_noise(request, frozen)` | Successful original calibration request/result,32 actual fixed-recipe fits |
| Refit replay | `gravity_noise_refits.validate_noise_refits(result, request, frozen)` | Actual refit result and complete original calibration; no optimizer |
| Native transport | `gravity_workflow_io.archive_bytes`, `gravity_workflow_io.native_from_archive` | Stored-only bounded `.gza`, complete member/EOF/type/hash guard |
| External custody | `gravity_workflow_io.read_archive`, `gravity_workflow_io.publish_archive` | Explicit external data/temp roots, flat filename, no overwrite |

CLI: `scripts/run_gravity_survey.py`. Verifier:
`scripts/verify_gravity_survey.py`. The [practitioner recipe](../methods/gravity-survey-workflow.md)
and [calibration contract](../design/features/m02-survey-l2/contract.md) define
units, correction/source provenance, geometry, rows, noise, prior and policy.
No caller-supplied engine, simulation, default CRS or guessed errors are allowed.

The exact original-noise schemas, physical factor nesting, native cap accounting
and source-original terminal proof are specified in the
[closed quadratic/IRLS handbook](../methods/gravity-survey-original-quadratic.md).
This source contract is not permission to consume a new source, native binary,
online host, M11 compiled model or nonlinear objective. Runtime-source identities
are not interchangeable across these exports or their historical receipts.

## Controller mounting requirements

Reuse `install_processing_routes` and `/api/projects/{project_id}/jobs`
authorization, queue, cancellation, result and export. Review exact M02 method
IDs, normalized source dataset and child/result dispatch with the controller's
current schemas. Do not invent another queue/auth system or expose an unreviewed
method ID. A MAD outlier result is not a corrected gravity-anomaly dataset.

Admission binds owner/project/raw bytes, rights, correction/normalization/
transform identity, geometry/datum, row/group masks, explicit SD/SPD covariance,
signed bounds/reference/prior and frozen recipe. Outer measurements stay sealed
until successful frozen selection/refit. Execute a separate bounded worker child
using external per-job storage, one thread, original200/20/120 and1800 caps,
actual RSS/scratch controls and existing termination/recovery. A replayable file
does not make a scientifically failed fit successful. Integrity, authenticity,
source permission, convergence and host admission remain distinct.

Authorize owner before archive or cache access. Whole numerical replay belongs
in a bounded worker, not the FastAPI event loop. A verified cache binds whole
original/archive/member inventory, current defining product/vendor sources and
runtime, complete replay verdict and exact displayed fit/frame/stage/recipe.

The [inspection SDD](../design/features/m02-result-inspection/design.md) proposes
isolated typed contract/client/workbench/course/density leaf files. Supply one
reviewed import/dispatch mounting patch only after actual producer, two-owner,
EN/ES/light/dark and browser graph gates pass. Consume the governed shared base;
do not copy its newer components into this older foundation.

Original IR-C06 still fails. The distinct low-beta
[Armijo search-scale diagnosis](../design/features/m02-survey-l2/armijo-scale-cause.md)
also retains its unsuccessful feasible-scaling proposal. Source/M01 admission,
reviewed schema/mount, Linux qualification, bounded replay/cache and actual
mounted course/graphs remain factual gates. No SMTP, backup or Pages prerequisite
is introduced, and no public activation follows from this manifest.
