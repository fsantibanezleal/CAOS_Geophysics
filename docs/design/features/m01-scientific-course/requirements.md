# M01 scientific course requirements

Status: planned; FULL MAIN read and explicit approval pending. Parent [product SDD](../../SDD.md) remains approved and unchanged. Research was persisted first in `6ba07cb`; read the [physics dossier](../../../research/m01-course-research-2026-10-03.md) and [sources](../../../research/m01-course-sources-2026-10-03.md). This submission authorizes no lesson/frontend/solver/test implementation.

Each future named test below is a falsifiable gate, NOT an existing test or PASS claim. The proposed tests/test_m01_scientific_course.py file must stay absent until separately approved. Browser and recipe execution require their own actual receipts; content tests alone cannot certify them.

R-MC01 THE feature SHALL remain an M01 correction/transform course with no new solver, density inversion, source interpretation, private bytes, API/storage/worker activation, acceptance waiver or M13 change.
Gate: tests/test_m01_scientific_course.py::test_scope_and_acceptance_boundaries; MAIN full path/source/claim review.

R-MC02 WHEN teaching normal gravity, THE course SHALL derive surface Somigliana with explicit units and distinguish the actual closed-form gamma(phi,h), co-located disturbance and classical free-air anomaly without applying elevation twice.
Gate: tests/test_m01_scientific_course.py::test_reference_height_formula_and_no_double_correction; real existing formula tolerance checks, unchanged.

R-MC03 WHEN teaching height and topography, THE course SHALL distinguish compatible h=H+N, receiver clearance, surface plate thickness and a supplied signed T=B-A_topo from external DEM/curvature/ocean/isostatic calculations not implemented here.
Gate: tests/test_m01_scientific_course.py::test_datum_plate_and_supplied_terrain_contract.

R-MC04 THE course SHALL distinguish primitive SD, covariance, first-order propagated SD and the conservative marginal upper bound, including shared geoid/density errors and missing-error rejection, without inferring Gaussian confidence or geological uncertainty.
Gate: tests/test_m01_scientific_course.py::test_covariance_and_marginal_bound_definitions.

R-MC05 THE course SHALL derive the actual scalar 1/r layer, column-scaled L2 objective and conditional transfer covariance without interpreting coefficients or mathematical depth as recovered 3D mass/density.
Gate: tests/test_m01_scientific_course.py::test_scalar_kernel_regularization_and_nonuniqueness.

R-MC06 WHEN comparing depth/damping/height, THE course SHALL preserve the existing geometry-frozen outer split and training-only inner selection, show support counts/failures, and never select parameters or masks using outer holdout values.
Gate: tests/test_m01_scientific_course.py::test_blocked_training_only_selection; unchanged independent gravity-transform tests at the approved scientific source pin.

R-MC07 THE course SHALL teach source-free continuation, absolute height semantics, no downward continuation, conditional precision, null unsupported cells, original masks and sampling-versus-resolution limits with explicit prediction-minus-observation residual labels.
Gate: tests/test_m01_scientific_course.py::test_continuation_support_height_and_residual_sign.

R-MC08 WHERE controls calculate in the browser, THE course SHALL label them explanatory scalar calculators and expose exactly the bounded models in scenarios.md, not claim a core solve, authenticated origin, owned job or real-data admission.
Gate: tests/test_m01_scientific_course.py::test_explanatory_controls_not_physical_jobs; rendered EN/ES interaction audit.

R-MC09 WHERE a scenario shows recorded numerical results, THE course SHALL bind request/result/config/split/source/runtime and artifact hashes from an actual local run, distinguish view changes from new requests, and fail closed on stale or missing bindings.
Gate: tests/test_m01_scientific_course.py::test_recorded_scenario_identity_and_stale_negatives; independent retained execution/receipt audit, not mocked output.

R-MC10 THE course SHALL give runnable existing local Python and paired-script workflows for a user's own explicit eligible JSON, preserve full parent objects and integer serialization, and describe bounded transform replay limitations without repairing hashes or inventing physical metadata.
Gate: tests/test_m01_scientific_course.py::test_user_file_workflow_and_parent_identity; actual fresh local recipe execution after approval.

R-MC11 THE course SHALL provide six substantive question-led EN/ES lessons, literal definitions, dimensioned equations with captions, prediction/reasoning exercises and six distinct physical SVG explanations, rather than generic method summaries or decorative flowcharts.
Gate: tests/test_m01_scientific_course.py::test_bilingual_questions_equations_and_physical_figures; full human content review.

R-MC12 WHEN rendering, THE course SHALL inherit shell 0.6.8 language/theme/typography/navigation/reference primitives and demonstrate keyboard, mobile, dark/light and direct-route behaviour without modifying large routes/styles or the MT course under this unit's authority.
Gate: tests/test_m01_scientific_course.py::test_shared_shell_and_scoped_mount; actual screenshot/keyboard/mobile/direct-route receipt. A separately assigned MAIN mount is a dependency, not implicitly authorized.

R-MC13 WHEN demonstrating failure, THE course SHALL include actual wrong-unit/high-noise/missing-coordinate/downward-height/stale-parent and source-ineligible controls, keeping field eligibility closed for unresolved datum/SD/lineage and preserving scientific tolerances.
Gate: tests/test_m01_scientific_course.py::test_negative_controls_and_field_gate; real negative execution after explicit approval, private field test only when MAIN supplies a rights-aware path.

R-MC14 THE feature SHALL stop at each explicit approval boundary and keep documentation, local scientific execution, course content, browser QA, source eligibility, host admission and full M01 acceptance as separate verdicts.
Gate: tasks.md convergence review; tests/test_m01_scientific_course.py::test_stage_authorization_and_nonclaims.
