# Complete native accepted-state instrument

Status: planned

JI-01 THE offline exporter SHALL preserve every original workflow byte and emit
       a new exclusive external bundle, with original file hashes and actual
       loaded exporter/physical/operator source pins; no refit or policy change.
       Gate: tests/numerics/test_joint_survey_instrument.py::test_full_bundle_replay
JI-02 WHEN a completed durable selection is verified, THE exporter SHALL compute
       actual physical predictions, signed and marginal-whitened residuals and
       separate training/validation/sealed metrics for every accepted state of
       every candidate; single-property attempts SHALL expose only that property.
       Gate: tests/numerics/test_joint_survey_instrument.py::test_state_responses
JI-03 THE exporter SHALL expose signed per-active-cell face-averaged Gram
       contributions whose sum equals the actual optimized CrossGradient scalar,
       without vector-first averaging, clipping or normalized-factor substitution.
       Gate: tests/numerics/test_joint_survey_instrument.py::test_exact_face_gram
JI-04 IF whole projected arrays, native files or metadata exceed the existing
       256MiB transport or 256KiB JSON caps, THEN THE exporter SHALL reject before
       historical calculations or output creation, never truncate states.
       Gate: tests/numerics/test_joint_survey_instrument.py::test_precompute_cap
JI-05 THE browser SHALL bind every historical response/coupling frame to its
       original candidate/state, fixed strengths, freeze, inputs and file hashes,
       retaining literal failures and denying scientific execution/acceptance.
       Gate: frontend/src/test/joint-result.test.ts::accepted state instrument
JI-06 WHEN an accepted state is selected, THE instrument SHALL expose its actual
       models, response/residual/holdout metrics and exact coupling contributions
       through existing bilingual theme-aware widgets and unchanged shell CSS.
       Gate: frontend/e2e/joint-result-inspection.spec.ts::native accepted states
JI-07 THE instrument SHALL export selected exact native-state values and original
       private files, and link its wiki contract and executable local guide.
       Gate: frontend/src/test/joint-result-component.test.ts::state export links

These gates do not replace the original independent inverse precision, field,
integrated navigation/render, scientific resource or activation gates.
