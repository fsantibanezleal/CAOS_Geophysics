# Surveyed input and owned local result design

The scientific protocol remains magnetic-survey-inversion-1. A new additive
adapter consumes an existing authenticated owned RawAsset and SourceRecord,
the original byte snapshot supplied by checked owner storage, and the exact
bounded physical-request UTF8. No inferred CSV columns, datum, uncertainty,
field direction, licence or correction is introduced. It preserves lexical
request bytes in the dataset and recomputes the original geometry seal on read.
Hash verification is not proof that a source's declared correction is physical.

Method mapping names executable existing functions: parse_request, plan_geometry,
magnetic_calibration.calibrate, frozen evaluation in run_magnetic_survey,
magnetic_result_bundle.read_bundle and magnetic_result_export.export_zip.
Online remains ineligible for this version, independent of caller strings.
Changed configuration produces a new immutable dataset; existing database parser
uniqueness by raw asset/version requires the owner union to version that parser
or the raw acquisition, never overwrite an existing dataset.

A local replay imports a genuinely complete, already fitted NPY generation.
Full read_bundle validation runs before identity matching. The request recovered
from the generation must equal the original dataset's converted closed request,
not merely its geometry/configuration hash. The generation cannot set ownership.
The owner stores one deterministic uncompressed numeric ZIP at
derived/<owner>/<project>/results/<job>.zip. Its stored SHA/count occupy existing
ProcessingJob.result_sha256/result_bytes, so result quotas count all retained
numeric bytes and no unaccounted sibling artifacts are introduced. Projection
JSON is derived on read, not an independently mutable successful pointer.

The job's closed request and preflight retain dataset SHA, physical request SHA,
generation SHA, configuration SHA, source ID and original SHA. Installation uses
exclusive private output, fsync, byte readback then an owned SQLite transaction.
On pre-commit refusal only exactly created bytes may be removed. An uncertain
commit retains its exact file for reconciliation; never delete a possibly
committed successful result. Cross-owner reads retain non-disclosing404.
Read/export verifies current source/raw/dataset/job and exact archive again.
Unpacking uses a fresh explicit external scratch generation; exact created
members are removed only after manifest/inventory and hash recheck. Unknown
files refuse cleanup. No generic raw-directory sweep or successful crash claim.

The additive functions are executable owner-union seams, not a second auth/server.
Existing protected dataset/job/result/export dispatchers mount them in the parent
assembly. Existing generic deletion and result validators require explicit
magnetic ZIP dispatch before mounting; this unit supplies exact inventory and
cleanup functions, not edits to the shared controller. No deployment activation.
The client uses the existing same-origin ApiClient and selected job binding.
Online submit remains unavailable, not a replay silently called computation.
