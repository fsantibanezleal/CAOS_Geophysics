# Result opening, exact inspection and recorded-state controls

## Scope and existing authority

The reviewed processing/MT workbenches already own authenticated dataset/job
selection, worker submission, actual result loading, linked charts and verified
ZIP download. Only three result kinds exist here: gravity statistical station
flags, M05 full-tensor QC and M06 conditional fixed-thickness TRF. The ledger's
unresolved modality and failed scientific gates are not closed by adding views.
No API/producer schema, physics, bounds, threshold, optimizer, source artifact,
environment or shared shell is changed. M01 course and curated widgets stay intact.

## Open a previously exported result

History's existing successful-job selection remains authoritative; opening has
its own compact control section, not an additional history-rail form. A local file
input opens only that job's saved ZIP, with the same17MiB limit and ZIP_STORED
member bounds already enforced by verifyProcessingBundle/verifyMtBundle. Check
File size before arrayBuffer. Do not weaken either verifier or infer a job from
untrusted file metadata. Existing parsers verify shape/units/scientific consistency;
digests bind original member bytes to the independently loaded job/dataset.

ResultBundleInput performs no HTTP/storage write. It invokes the modality-specific
existing verifier supplied by the authenticated parent and emits only verified
result data. An epoch/lifetime check discards completion after unmount or selection
replacement. Verification errors cannot replace the previous verified result;
the error explains that it remains the last verified view, not the rejected file.
Re-opening another job requires selecting that job first. This is not a free-form
offline producer importer or proof of field geology/authenticity from hashes alone.
Reselecting the same dataset/job is a no-op: it must not clear the current view
without a changed identity triggering the existing reload effect.

## Exact-value inspection snapshot

result-view-data builds a separate JSON inspection snapshot, schema
`geophysics.result-inspection/v1`, not a replacement processing-result or signed
producer bundle. Native JSON number serialization preserves finite returned
float64 values without display rounding, with native JSON semantics (negative
zero serializes as zero; no bit-pattern or original-byte identity claim).
Snapshot export is a local download,
never a server operation. It carries dataset/job/request/raw/engine identity,
source rights/physical metadata, units, literal arrays and the view selection.
Gravity retains all stations/declared sigma/false masks and optional returned
scores/flags. MT retains the full tensor and ancillary missingness, XY/-YX,
final predicted arrays, frozen training partition, literal conditional model
and diagnostics. M05 has null prediction/residual/model; no zero substitutes.
Signed complex residuals in the exact selected-frequency table are the same
observed-minus-final-predicted values already defined by mtResidual; marginal
standardization is a declared view transformation, not an inverse or QC change.

The export embeds the parsed result itself plus selected index/declared units,
so all omitted plot points and exact diagnostics remain available. It does not
claim original JSON member-byte identity; use the verified ZIP for that purpose.
No CSV formula injection, locale number conversion or arbitrary filename reuse:
download JSON under a constant prefix and validated UUID.

## Recorded-state inspection, not solver animation

RecordedMtStates operates only on M06 frames/history/states already validated by
the MT parser. A native labelled integer range and previous/next/reset/play/pause
controls share the objective-plot cursor. LayerColumn shows that recorded model
at imposed depth; the final model remains separately named and response panels
never switch to an unreturned historical response. State kind/step/objective are
literal receipts: residual evaluations include trial/Jacobian calls, not accepted
iterations, wall-clock or physical time. No interpolation or new forward solve.

Play is explicit, initially paused,500ms per stored frame, no looping; stops at
the last frame. Manual selection pauses. View unmount, document hidden or reduced
motion pauses and cleans timers/subscriptions. Reduced-motion users retain manual
scrub/step/export but cannot start automatic playback. The same selected-state
JSON has schema `geophysics.recorded-mt-state/v1`, source identities, imposed
thickness, units and the literal index/kind/step/model/objective, with
historical_prediction=null and evaluation_kind=residual-evaluation-record.

## Verification before any acceptance

Test-first negatives: oversize pre-read spy; tampered/foreign/non-success bundles;
null QC fields; exact signed nonuniform values; frame bounds; selected-state
roundtrip and unchanged source arrays. Browser verification uses actual backend
API and separate worker in a new private local database, existing trusted runtime,
random stdin credentials and unchanged source hashes. It uploads an independent
station CSV plus actual analytic EDI fixtures, executes flags/M05/M06, downloads
and reopens real ZIPs, compares snapshots/state exports against actual results,
and tests stale job switches and reduced motion. No successful API result is
intercepted. All new tests/builds write ignored output; no canonical bake.

The existing seven MT views and gravity instrument are revisited in EN/ES,
light/dark,1280x800/1600x900/2560x1440/390x844. Containment, labels, pointer/keyboard
selection and screenshots are measured. A browser pass is not a numerical
revalidation of the methods, host admission, scientific renderer-wide acceptance
or deployment authority. Existing negative/review receipts remain unchanged.

Ordinary repository-local Playwright against the owned local server is the
browser gate. Native window-controller availability is not a product prerequisite.
Exploratory native-visibility attempts and their failures remain separate historical
QA evidence; their removal from the ordinary matrix does not establish a native
visibility pass. Do not override document properties or intercept scientific data.
The source lifecycle still observes native visibility changes: hidden pauses,
visible restoration updates control eligibility but never restarts playback.
A pure admission predicate tests reduced-motion, visibility and frame-end states;
these unit controls are not an operating-system visibility execution claim.
QA storage/receipts use a caller-created private scratch parent when the source
drive is constrained. Require a new UUID child of that declared parent; no deletion,
installed changes or canonical writes. The ordinary matrix must run all five
data/result/export/render groups without exclusions.

Implementation grounding: [React effect cleanup](https://react.dev/reference/react/useEffect),
[media-query change subscription](https://developer.mozilla.org/en-US/docs/Web/API/Window/matchMedia),
and [asynchronous Blob reading](https://developer.mozilla.org/en-US/docs/Web/API/Blob/arrayBuffer).
These describe lifecycle/resource controls, not geophysical validity.
