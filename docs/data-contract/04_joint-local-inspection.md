# Supplied joint output to local scientific instrument

## Product path manifest

The independent client entry is `frontend/src/api/joint-result.ts` and the
instrument is `frontend/src/components/JointResultWorkbench.tsx`. Unit gates
are `frontend/src/test/joint-result.test.ts` and
`frontend/src/test/joint-result-component.test.ts`; actual browser gates are
`frontend/e2e/joint-result-inspection.spec.ts`. The pre-code design, requirements
and convergence tasks are under `docs/design/features/joint-result-inspection/`.
The instrument composes existing ScientificPlots, the shell language store and
existing widget classes. No new shell, CSS/font, server endpoint, scientific
array, engine parameter or physical-method approximation is introduced.

Offline sources are the complete local processing workflow and its native
calibration/freeze/result/physical-model writers, not the cached synthetic joint
example. These writer hashes identify the inspected transport contracts:

| Defining writer path | SHA-256 |
|---|---|
| data-pipeline/joint_survey_files.py | af034287f89e78fe666397f4bf8a13c8841813a8c1b83ce2df087b9c78a40abe |
| data-pipeline/joint_survey_calibration_io.py | 824be4adeca732d4cc15c4e44c95c2d497964ea39b19ebd8967173f1686973fb |
| data-pipeline/joint_survey_evaluation.py | f0121b1562b50ab37ec1c93adbf4507b67456e955b8d24c227c9cc4314ed5db9 |
| data-pipeline/joint_survey_model_export.py | 51fe2b4eba9becb611c7dad22ada2ed5556697053aca12547a8ee5b844219421 |

Optimizer declarations must match epoch `physical-gncg-nonlinear-candidate-2`,
policy `exact-bound-native-gncg-actual-armijo-1`, source
`772c4de0b7747bbc9075b6fbf1357b04de752bfd900f88c9a5ddead2a91931fd`
and vendor
`0ac858cc310b32bb9aa59c78aaaa9c79b5f28438db52fb06ec73d976b63196a4`.
Pins identify an inspected ABI, not parent scientific acceptance, provenance
authentication or execution on the browsing device.

## Import, inspect and export

Select the **complete workflow output directory**. Do not select its parent data
root or mix in development/sealed inputs. Admission permits completed solve,
completed supplied-model evaluation, failed independent-baseline selection and
aborted workflows. Native manifests and exactly their fixed NPY members must be
present. At most1100file occurrences (including separately retained failure
ledgers) charge the256MiB cap before reads; every
JSON record is at most256KiB/depth8 and every NPY1 header is bounded/literal,
native little-endian float64/int64 or boolean and non-executable. All headers are
checked before value decoding/hashing. Unknown filenames/keys, duplicate JSON
keys, ambiguous path prefixes, unsupported epochs, malformed shapes, nonfinite
values and altered file/data hashes reject. There is no arbitrary ZIP extraction,
URL fetch, pickle, executable object, browser storage or upload.

The response view links original row IDs, observed/frozen-predicted response,
signed prediction-minus-observation residual and principal-marginal whitened
coordinate. Original row number is not distance. Whitening with covariance is
not pointwise residual/SD. Partition metrics remain separate for both modalities;
there is no combined accuracy score. The physical view draws orthographic
sections of exact nonuniform active prism bounds, x-fast indices, density kg/m3
and SI susceptibility. Inactive cells stay blank. Coordinates use the original
declared ENU frame, not an invented datum transformation or geological label.

Calibration inspection retains all16 independent fits and10 joint positive
strength/two-start attempts. Accepted states, actual terminal reasons, physical
blocks and exported five scalar terms bind their own stage/identity/weights.
Earlier states do not inherit terminal validation metrics or nonexistent
historical prediction arrays. The exported scalar coupling is not replaced by a
CrossGradient vector-factor or approximate local coupling map. Failed workflows
override any earlier durable result files; unreplayed last attempts remain
explicitly unreplayed, and no sealed result is exposed as complete.

Original archive export preserves every admitted member byte-for-byte under its
original relative name. It includes private observations; it is **not** a public
redistribution bundle. Hashes are checked again before export. Numeric inspection
JSON is a derived sidecar, not the native artifact or a scientific certificate.
Browser flags for scientific replay, executed inverse, scientific acceptance,
field eligibility, authentication and redistribution remain false. Scientific
replay still uses the original development/sealed inputs, pinned offline runtime
and strict validate command in the [local workflow guide](../guides/22_local_joint_survey.md).

## Gate usage and qualification limits

Actual fixtures are explicit external environment configuration:
`GEOPHYSICS_JOINT_OUTPUT_FIXTURE`, `GEOPHYSICS_JOINT_EVALUATION_FIXTURE`,
`GEOPHYSICS_JOINT_ABORT_FIXTURE`, `GEOPHYSICS_JOINT_DURABLE_ABORT_FIXTURE`,
`GEOPHYSICS_JOINT_MATRIX_FIXTURE` and
`GEOPHYSICS_JOINT_MAX_OUTPUT_FIXTURE`. Missing fixtures are explicit skips, not
browser acceptance. Browser gates additionally require the actual component URL
`GEOPHYSICS_JOINT_INSPECTION_URL` and external `GEOPHYSICS_BROWSER_EVIDENCE_ROOT`.
Run locally with an external test/cache/trace directory; no artifacts belong in
the repository or system temp. The browser test covers both languages/themes,
desktop/phone, each response partition, three property planes, retained candidate
failure/state controls, private archive and sidecar exports, maximum-count output
and aborted-state boundaries. Composition into the app and its actual shell
navigation/render gate are distinct from isolated component gates.

Native byte/count admission is not a whole-browser memory proof. Actual maximum
**count** output contains a zero-property resource control and short histories;
it does not qualify the maximum251-state history, mobile memory upper bounds,
geological recovery, coupled benefit, Linux or GPU execution. Inspection metric
arithmetic uses a1e-12 relative floating-point roundoff consistency check; it is
not the independent scientific oracle and changes no offline scientific precision
predicate or tolerance.
