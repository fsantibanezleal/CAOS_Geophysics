# Linked local velocity JSON adapter

## Boundary and exact producer

The actual producer is data-pipeline/velocity_user_data.py, geophysics.velocity-
result/v1 with geophysics.velocity-bundle/v1 manifest. Its user-data contract
and later physics-v2 checkpoint protocol are authoritative. A caller runs the
existing local command first; this adapter only inspects those returned files.
No API/account/session/provider dependency, raw-input upload, browser solve,
checkpoint execution/training, GPU, field eligibility or server activation.
The curated app remains unchanged. A local-result launcher and instrument=velocity-
local query choose a separate local workbench; returning removes only that query.
A simultaneous project query does not dispatch local bytes to that project.

## Admission

Before byte reads require integer file sizes: result1..4194304 bytes, manifest
1..4096 bytes. Reject malformed UTF8, JSON depth>12, nodes>160000 (manifest40000),
duplicate decoded object keys, nonfinite values, unknown keys and false schema.
The bounded lexical pass precedes JSON.parse and does not invoke user hooks.
SHA256 is WebCrypto over ORIGINAL result bytes; result_bytes is exact length.
Manifest source/engine must agree with result source/engine. Source SHA/bytes are
DECLARED original-request identity: that raw request is not present for byte
reverification. A matching manifest is neither signature nor source authenticity.

Closed request: schema,id,source,frame,units,ray_ids,rays_m,times_s,sigma_s,lambda.
Frame local-x-z-down and units m/s/m/s are not inferred/converted.8..2048 unique
ASCII IDs; finite endpoint4-tuples in[0,800]m, length>=0.001m; times(0,100]s,
sigma(0,10]s,lambda[1e-6,1e6]. Citation nonempty<=2048characters; approved rights/
scope enums. Axes exactly25+50i m,16cells; order depth,distance. Coverage16x16
finite nonnegative metres. Velocity16x16 finite positive; classical1400..4000
m/s. Four per-ray arrays lengthN: predicted_s,residual_s,normalized_residual,
bilinear_predicted_s. Observed-minus-predicted, residual/sigma, data chi square,
WRMS and cell/bilinear RMSE must match within the producer's frozen scalar
rtol1e-12/atol1e-12. This is scalar consistency, NOT independent ray reforward.
Regularizer finite nonnegative, clipping integer0..256, bounded optimum false.

Engine keys: numpy,scipy,user_tool_sha256,velocity_operator_sha256,
checkpoint_sha256,checkpoint_protocol,refinement_code_sha256. Versions are
bounded strings; hashes lowercase64hex. Classical-only has null checkpoint,
protocol/refinement and learned_domain. Learned has a real hash and original or
physics-v2 protocol; refinement hash only for physics-v2. Learned-domain keys
training_geometry,training_noise,field_validated,heldout_advantage are boolean,
last two false. Claims field_truth_known,field_validated,heldout_advantage,
online_admitted must ALL be literal false. No fallback or ignored invalid field.
Warnings are bounded plain text rendered as React text, never HTML or links.
Only validated parsed native JSON is retained; no external path execution.

## Linked views and semantics

Existing Heatmap renders returned velocity or path-length coverage, no new
renderer or interpolated resolution. Existing Plot renders all ray times with
sigma, signed residuals or residual/sigma. Shared selected-ray index links those
charts, a native ID select and exact endpoint/time/prediction/sigma readout.
Geometry view shows the selected supplied straight segment using the same Plot;
its vertical display coordinate is -depth(m), explicitly labelled up, while
all original JSON/readouts remain positive-down. Coverage displays the selected
source/receiver markers at their actual coordinates, not invented ray trajectories.
No bent rays, FWI, geology surfaces, unseen solver frames or known truth.

Native x/z cell selects provide keyboard/exact value alternatives for map picks;
cell centre/depth, velocity and coverage share one selected cell. Native colour
min/max controls affect display only, no mutation/normalization of returned arrays.
Model choice is classical or actual learned, only when returned. Both retain
warnings. Always show classical solver as unconstrained Cholesky plus explicit
slowness clipping, not certified bounded optimum. Learned badge is NEGATIVE
matched benchmark for BOTH original and physics-v2, never a green pass.

Export is a geophysics.velocity-inspection/v1 JSON sidecar with full admitted
result, original result/manifest hashes and current ray/cell/model/view selection.
Native finite JSON retains exact numbers apart from JSON negative-zero semantics;
it is not the original producer-byte bundle. Local file read/export never writes
the API. Epoch/unmount cancellation prevents stale reads; failures leave an
explicitly labelled last admitted view. No filename/paths rendered as authority.

## Prospective gates and resources

Test-first malformed admission and missing-interface reds, then exact unit
roundtrip/scalar controls. Actual producer generations run from trusted immutable
source with existing readonly runtime, in fresh private scratch. Exercise real
classical-only, original CNN and physics-v2 CNN, with variable errors/nonuniform
times. Independent producer verify_generation must pass before UI admission;
record its scope separately. No successful data interception or fabricated
fixture replaces these generations. Original files, producer source/checkpoints,
owner database and failed receipts remain unchanged. Existing installed packages
are never changed. New outputs/builds use private non-source-drive scratch.
Browser gates run all views in both languages/themes/four viewports, inspect
pointer ray/cell selection, keyboard alternatives, colour display-only changes,
model choice, rejected files, byte identity and exact downloaded selection.
Full current gravity/MT tests remain regressions, not velocity physics proof.
