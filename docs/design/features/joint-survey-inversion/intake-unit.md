# Exact proposed local serialized intake and source binding

Oct8 governance amendment: input directories must also be outside repositories.
During ordinary-ancestor admission, reject any ancestor containing a .git file
or directory before directory inventory, JSON reads or array work. This admits
explicit external data only, does not infer a path from sources.ROOT and does
not modify MAIN acquisition/ERT/traveltime/ingest behavior. Paired test:
test_repository_intake_rejected_before_read, for both ordinary and worktree Git
markers. Existing caller path/type/reparse/resource/precision gates remain exact.

Pre-code protocol for joint_survey_intake.py and its paired numerical tests.
This is a local filesystem adapter, separate from the no-I/O planner/objective.
It does not optimize, select candidates, publish data or infer field eligibility.
Its eventual complete solve/export CLI remains subject to the algorithm and
export contract reviews; this document does not implement a partial solve CLI.

## Entry points and ownership

`load_joint_development(directory: str) -> dict`:exact builtin nonempty absolute
directory string resolved by the local caller, not a URL/import/callback. Reject
symlinks/junctions/reparse points at the selected directory and every consumed
child. Input is read-only. Never create/delete/move/repair an input, canonical
directory or sibling path. The directory is untrusted scientific content, not
instructions. No import-path extension or object construction from serialized
strings. A read/hash/load is not a distributed filesystem snapshot:mutation
detected by size/header/content hashes fails closed; no concurrent-writer lock
or attacker-proof kernel-level confinement is claimed.

`load_joint_sealed(directory: str, frozen: dict) -> dict` is a separate evaluation
entry point. `frozen` must later bind the reviewed selection result identity and
its plan; exact selection grammar remains to be reviewed before this function is
implemented. Calibration has no sealed argument, path or loaded observations.
The first implementation is only complete development intake, not sealed solve.

## Six-key request.json

Maximum262144 original UTF-8 bytes, strict decoding, no BOM. JSON object duplicate
keys, NaN/Infinity/nonfinite numeric literals and unsupported nesting reject.
Exactly `schema=joint-survey-intake-1`, `survey`, `development`, `arrays`,
`sealed_manifest`, `raw_access`. No policy/engine/kernel/callback/truth/selection
injection. The eventual native descriptor's separate256KiB/32768scalar/depth8/
96MiB caps remain unchanged; passing the serialized byte bound does not waive
those native bounds. All JSON metadata and all array header/shape/size metadata
precede ANY array values, copies, physics or optional raw-file scan.

`survey` is the exact seven-key native planner request with array locations
replaced by single-key objects `{"array":"ID"}`. ONLY the explicitly array-typed
native fields permit these objects. Its frame.axes list is the sole designated
list-to-tuple conversion; missing_reasons lists become tuples at their designated
fields. All other keys/types/enums retain contracts.md. Require floating-point
JSON literals for exact builtin float fields, not silent int-to-float promotion.
Integer fields are exact ints, excluding bool. No inferred CRS/unit/error model.

`development` is exactly plan_sha256/gravity/magnetic from objective-unit.md,
with the three array fields in each modality using designated array references.
It binds exact train-then-validation rows and corrected physical observations/
noise; no sealed row is admitted. There are no model/direction/weight keys here:
intake cannot set the frozen candidate policy or integrate an optimizer.

`arrays` is an exact dictionary with22 survey IDs and6 development IDs:

    mesh_origin,mesh_hx,mesh_hy,mesh_hz,mesh_active,prior_lengths,
    gravity_receivers,gravity_mask,gravity_groups,gravity_partition,
    magnetic_receivers,magnetic_mask,magnetic_groups,magnetic_partition,
    density_lower,density_upper,density_start,density_reference,
    susceptibility_lower,susceptibility_upper,susceptibility_start,susceptibility_reference,
    gravity_development_rows,gravity_development_observed,gravity_development_noise,
    magnetic_development_rows,magnetic_development_observed,magnetic_development_noise.

Each ID is bound to its corresponding single field, used exactly once; no alias,
unknown/omitted ID or external path. Each descriptor exactly `dtype`, `shape`,
`file_bytes`, `file_sha256`, `data_sha256`. dtype is exactly `<f8`, `<i8` or `|b1`
as specified by the native field; shape is a nonempty builtin integer list of
the required rank and admitted bounds. SHA fields are64 lowercase hex. File name
is solely `ID.npy`, not caller-supplied. Every file must be an ordinary file,
exactly its declared size and no alternate stream/link/extension. No extra file,
directory, duplicate/case-variant name, ZIP/executable/pickle/object dtype or
compressed input is accepted. Hard links are not a lock:pre/post hashes still
must match and no writes to input storage occur.

NPY v1.0 only, header<=4096bytes. Parse literal header with bounded AST grammar
for its exact descr/fortran_order/shape keys, no eval/pickle. Require native dtype,
fortran_order=false, exact shape and file length equal prefix+header+logical data
bytes; reject trailing/truncated bytes and misleading header allocation counts.
Sum all28 logical array sizes<=96MiB before reading values. Only after complete
metadata admission:verify full-file SHA, load with allow_pickle=False, owned native
C-array snapshot, compare C-data SHA and repeat file identity/hash after loading.
No mmap/lazy view whose bytes can drift during a fit. Then run genuine native
planner and development admission, never return a blindly relabelled JSON object.

## Sealed metadata and raw access

`sealed_manifest` exactly `schema=joint-survey-sealed-manifest-1`, gravity,
magnetic. Each modality exactly `rows_sha256`, `observations_file_sha256`,
`noise_file_sha256`, `count` integer1..2048, `noise_kind` matching its native
declaration. This first directory contains NO sealed arrays or truth files.
Each count must equal the admitted plan's sealed row count; rows_sha256 must
equal SHA256 of those exact native int64 row IDs' C-order bytes. Observation and
noise file commitments are not reinterpreted as bare-array value hashes.
These are caller commitments only, not verified file/data hashes. Changes here
may alter intake/source envelope identity, but must not alter native plan,
development identity, calibration/selected scientific identities or weights.
The later separate sealed adapter must verify actual rows/noise/source bytes
against frozen selection and these commitments without allowing a refit.

`raw_access` exactly gravity/magnetic, each exactly `availability`,
`raw_present`, `correction_present`. availability is `provided` or
`provider_reference_only`; the two booleans are exact. For provided, both must
be true and ordinary fixed files `gravity.raw`/`magnetic.raw` plus
`gravity.corrections.json`/`magnetic.corrections.json` must exist. For
provider_reference_only both are false and those files MUST be absent. No fetch
or external filename is accepted. Provided raw file length/hash must equal the
native source raw_bytes/raw_sha256; correction file<=256KiB, full bytes SHA must
equal correction_sha256. Correction receipt exact schema is not interpreted in
this epoch:its hash verifies supplied bytes, NOT that geological preprocessing,
rights, datum or uncertainty propagation were scientifically correct.

Total development directory bytes, including optional raw/correction files,
<=268435456 before any raw/array-value scan. This is an additional local adapter
I/O admission cap, NOT a change to native per-source1GiB declarations, array/
kernel/export limits or future solver resources. Large source declarations may
be referenced without copying bytes; they remain explicitly unverified.
Provided files never become public export permission. private_use and
provider_link_only data/coordinates/derived observations remain private; only
an explicitly separately reviewed redistributable export can be public. The
loader itself does not copy/export any raw or corrected data.

## Exact proposed result and paired gates

Result exactly `schema=joint-survey-development-intake-1`, `survey_request`,
`plan`, `development`, `sealed_manifest`, `bindings`, `diagnostics`. bindings
exactly `request_file_sha256`, `directory_content_sha256`, `development_sha256`,
`raw_sha256`, `correction_sha256`; the latter two are modality maps with64hex
or null for unverified absent files. Directory content identity binds every
consumed file's exact bytes and the sealed commitments. Development identity
binds native plan and development descriptors ONLY, never sealed commitments.
No callable, injected engine or filesystem path is returned as executable input.

diagnostics exactly rights_verified=false, source_bytes_verified (two actual
raw-match booleans), correction_bytes_verified (two actual match booleans),
correction_science_verified=false, field_eligible=false, inverse_completed=false,
sealed_values_loaded=false, concurrent_snapshot_guaranteed=false. Output arrays
are owned/read-only; integrity claims remain distinct from rights/science.

Prospective paired test_joint_survey_intake.py gates:exact key/type/ID/dtype and
duplicate JSON rejection; every shape/count/byte cap before scans/hash/load/engine;
NPY header/trailing/object/pickle/path/case/link negatives; actual original raw/
correction/file/data SHA positive and drift failures; descriptor and array native
agreement; provider-reference missing-byte flags; separate sealed-commitment
mutation leaves native/development identities unchanged; input bytes unchanged;
Linux/Windows attributable link support without declaring an unavailable test
passed. Full export/CLI/selection grammar remains pending, not numerical PASS.
