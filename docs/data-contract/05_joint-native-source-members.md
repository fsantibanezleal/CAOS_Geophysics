# Owner-bound local joint source members

The native transport carries the existing [supplied-survey input](../methods/joint-survey-inversion/README.md)
without changing its scientific potential, frame, prior, calibration or sealed
selection. Browser import/inspection and an offline scientific run remain
different operations. A structural receipt is never an inverse, a correction
approval, field eligibility or provider permission verification.

## Ordinary transport and exact original custody

The parent API installs `app.joint_processing.install_joint_routes` with its
existing authentication/session dependencies. POST
`/api/projects/{project_id}/joint-members` accepts one ordinary byte stream
with Content-Type `application/octet-stream`, not a ZIP/multipart archive.
`X-Joint-Member-Metadata` is closed JSON under16KiB containing exactly
`role`, `name`, `source`, `descriptor`. Role is development or sealed; name is
one fixed existing native basename, never a path. NPY members require the
original five-field dtype/shape/file/data-hash descriptor. Other members have
descriptor null. Source is the existing attested SourceInput, with mandatory
positive exact byte count and lowercase original SHA256. Forbidden rights
cannot be stored. No executable, callback, factory or remote URL is accepted.

Each member becomes the existing immutable RawAsset and SourceRecord, bound to
one authenticated owner/project/version/hash. Existing raw receipt, download,
project archive, quota, deletion and startup auditing include these rows. The
detected format is `joint_native`; physical metadata explicitly reports
`scientific_values_decoded=false` and `scientific_accepted=false`. Native
geometry and mixed measurement units belong to the existing complete scientific
request, not a manufactured generic CSV projection.

Development contains its request,28 NPY members and optionally both raw originals
and both correction JSON originals. Sealed contains its request and six NPY
members. Admission does not decode sealed values during selection. Original
intake remains the authority for source/correction semantics and physical QC.
The dedicated persistent80-member/hour/owner limit admits two maximum40-member
role pairs; generic20-upload/hour limits are unchanged. All POST operations
retain the canonical same-origin, CSRF and authenticated owned-project checks.

## Structural checks and byte accounting

NPY1 is little-endian f8/i8 or b1, C-order, bounded literal header and exact file
length. Count/rank/shape/byte metadata is rejected before body streaming. File
SHA256 and data SHA256 are independent. Header syntax cannot execute Python.
JSON is bounded to256KiB, depth8, no duplicate keys, BOM or nonfinite numbers.
Archives remain forbidden, including renamed archives. Stream bytes never
exceed the declared original length, configured upload limit or256MiB cap.

Staging uses exclusive private files and fsync, then an exclusive same-volume
hard link at the new canonical raw storage key. Source/version/quota checks
are repeated under the existing SQLite immediate transaction. Before any
commit attempt, a failed publication can remove only its known new bytes.
Once commit is attempted, an unknown response/outcome retains the actual
original for reconciliation; it cannot delete a possibly committed asset.
Unknown raw bytes deliberately require operator recovery on startup.

## Scientific workflow boundary

Dataset/member dependency, fixed-child processing, frozen selection, native
result/artifact publication and worker dispatch are separate additive contracts.
This source endpoint does not mark them implemented or activate a host. The
[offline scientific workflow](../guides/22_local_joint_survey.md) already performs
the real sixteen separate and ten coupled attempts and durable freeze before
held-out evaluation. [Full native inspection](04_joint-local-inspection.md)
retains the original optimization/precision failures and exact private exports.
Parent owns the canonical source/method unions and final single-sidebar mount.
