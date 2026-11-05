# M02 native result inspection requirements

Status: proposed; review required before implementation. This is a consumer of
the existing native L2/IRLS workflow, not another solver, queue or upload decoder.
Parent: [product SDD](../../SDD.md). Scientific contracts:
[local workflow](../m02-survey-l2/full-workflow.md) and
[original IRLS cause](../m02-survey-l2/irls-positive-cause.md).

MV-01 WHEN an archive is inspected, THE projector SHALL verify its complete
native request/result and every actual fit before producing any JSON arrays.
Gate: proposed tests/numerics/test_gravity_survey_view.py::test_replay_before_projection

MV-02 WHEN a view is requested, THE projector SHALL return one identified fit
and one actual recorded accepted frame, physical active-cell bounds and signed
density, development station identity/geometry and observed-minus-predicted
residuals; it SHALL NOT invent an accepted state or observation.
Gate: proposed tests/numerics/test_gravity_survey_view.py::test_actual_frame_and_physical_units

MV-03 IF selection or an IRLS fit fails, THEN THE consumer SHALL retain its
literal reason, all eight candidates and all 24 fold verdicts; unavailable
models, scores and predictions SHALL remain null, not zero or a success badge.
Gate: proposed tests/numerics/test_gravity_survey_view.py::test_failed_selection_is_literal

MV-04 WHILE outer observations are sealed, THE inspection packet SHALL contain
no outer observed values or residuals; inspection SHALL neither select nor refit.
Gate: proposed tests/numerics/test_gravity_survey_view.py::test_outer_observations_are_not_disclosed

MV-05 THE Python and TypeScript wire parsers SHALL enforce exact schema, keys,
finite numbers, units, dimensions, indices, literal nonclaims and a bounded
single-frame packet, explicit residual convention and immutable fit/frame/recipe
hashes; overflow SHALL reject rather than truncate scientific data.
Gate: proposed tests/data/test_gravity_survey_view_contract.py::test_python_typescript_wire_parity
Gate: proposed frontend/src/api/gravity-survey-contracts.test.ts::rejects_wire_drift

MV-06 WHEN a private result is obtained, THE mounted consumer SHALL reuse the
existing owner-scoped project/job authorization and same-origin ApiClient;
neither archive paths nor owner identifiers SHALL be client-controlled storage keys.
Gate: proposed tests/api/test_gravity_survey_results.py::test_other_owner_cannot_read_result
Gate: proposed frontend/src/api/gravity-survey-client.test.ts::uses_owned_relative_api

MV-07 WHEN a run is submitted, THE service SHALL use the existing bounded
separate worker and exact normalized-input admission, preserve original bytes
and correction lineage, and reject unqualified host/source inputs before queuing.
Gate: proposed tests/api/test_gravity_survey_jobs.py::test_admission_and_existing_queue

MV-08 THE isolated workbench SHALL provide linked station/prediction/residual
plots, physical density slices, candidate and fixed-stage histories, keyboard
inspection and underlying data tables in EN/ES and both themes; view controls
SHALL alter inspection only, not imply browser-side inversion.
Gate: proposed frontend/src/components/GravitySurveyWorkbench.test.tsx::actual_packet_views
Gate: proposed scripts/validate_gravity_survey_browser.mjs

MV-09 WHERE a 3D density view is included, THE view SHALL encode the independent
x/y/z physical cell coordinates, with orbit/slice selection and signed density
readouts, not relief obtained by lifting a two-dimensional residual plot.
Gate: proposed scripts/validate_gravity_survey_browser.mjs

MV-10 WHEN refit evidence is displayed, THE consumer SHALL verify every actual
conditional noisy-data refit, preserve all failures, and state fixed-recipe,
geometry and noise assumptions without claiming posterior or field coverage.
Gate: proposed tests/numerics/test_gravity_survey_view.py::test_actual_noise_refits_and_failures

MV-11 THE methods handbook SHALL connect the exact practitioner-input recipe,
physical objective, buffered selection, frozen evaluation, scaled IRLS recurrence
and graph readouts to primary citations and the executed gates.
Gate: proposed tests/data/test_gravity_survey_view_contract.py::test_handbook_and_graph_contract

MV-12 THE integration SHALL consist of isolated leaf files and a reviewed
mounting change; it SHALL NOT replace the shared Workbench, raw-source admission,
ingest CLI, authentication, queue or other method implementation.
Gate: proposed scripts/check_gravity_survey_mount.py

MV-13 WHEN a mounted view needs replay or a verified cache, THE service SHALL
perform numerical replay outside the request event loop within a measured bound,
bind the whole original/source/runtime inventory and complete verdict, authorize
the owner before cache access and invalidate changed inputs without resetting
the original solve budget.
Gate: proposed tests/api/test_gravity_survey_results.py::test_bounded_replay_cache_identity

The proposed gates above do not yet exist or pass. Their names are acceptance
criteria, not an implementation receipt. Review covers design.md and tasks.md
before code; a parser-only or mock-only UI does not satisfy these requirements.
