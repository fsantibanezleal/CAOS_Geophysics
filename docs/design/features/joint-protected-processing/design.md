# Additive source/worker/result contract

Read-only canonical reference: MAIN cdb0eb291505dcc4a09f25601693acb6fb01b6ef,
app/processing.py, worker.py, processing_contract.py, processing_storage.py,
models.py, config.py, schemas.py, formats.py, database.py and M08 leaves.
This is precode, not a claim those files contain M11. Parent may advance them.

Owned files will be app/joint_{contract,processing,worker,result,models}.py,
scripts/joint_processing_child.py and owned API/frontend tests. Parent receives
an explicit additive union/mount patch, not replacement canonical files. New
dependency/artifact tables follow current0004_waveform_artifacts; migration
head and reconciliation must union M08, never revert its source rows/members.

## Source custody and transport

The existing generic upload archive ban remains. Add an authenticated ordinary
native-member endpoint under the existing project, using existing RawAsset,
SourceRecord, AccountUsage and owned-project checks. No ZIP input, arbitrary
filesystem path or remote fetch. Metadata declares role development/sealed,
literal basename and exact native format; physical geometry comes from the
closed request, not a mixed-unit guess in the generic CSV schema. Headers and
request JSON are bounded before decode. Strict NPY1 little-endian f8/i8/b1,
C-order, exact file/data hashes and closed directory inventories retain the
original intake limits. Raw and correction files remain original bytes.

Exact endpoint: POST /api/projects/{project_id}/joint-members. It inherits the
canonical same-origin/CSRF/authentication protections. The owned leaf admits
at most80 native-member requests per authenticated owner/hour using existing
persistent RateWindow rows, before body streaming. One complete role pair has
at most40 members; a complete upload must not be blocked by the unrelated
generic20-assets/hour rule. Generic upload limits are unchanged. Metadata is
closed role/name/source/descriptor JSON under16KiB. Ordinary bytes and source
attestation are required; no multipart archive, executable or remote fetch.
NPY descriptor dimensions/byte caps precede streaming; original file/data
digests and bounded literal header are checked without importing numerical code.
Canonical raw download/export/deletion/startup accounting already includes these
RawAsset rows. Dataset/job result members require the separate additive unions.

Dataset creation binds an exact role/name -> asset/source/version/hash/bytes
map with a unique development request member as primary raw asset. Validation
compares held source bytes with descriptors and original schema using the
existing stdlib intake scanner before native imports. Structural indexing is
not inversion/physical QC. Sealed membership/hashes may be admitted, but sealed
observation values are not decoded during selection. Source rows are rechecked
at request, worker, publication, startup audit and export; no hidden dependencies.

## Actual execution and failure state

Use one existing ProcessingJob and singleton dispatch to the owned leaf for
method joint.gravity-magnetic-native/v1. Frozen parameters bind the scientific
request/inventory/source identities and implementation hashes; no arbitrary
optimizer options. The child materializes exact originals exclusively beneath
the external job root, then invokes solve_joint_workflow and strict original
replay before state_instrument_workflow. Final freeze/selection never changes
during export. A rejected/failed solve remains failed with real accepted-state
artifacts; it cannot publish a completed inverse or manufactured coupling.

The supervisor owns one fixed child tree, explicit interpreter/source digest,
external caches and disjoint stage inputs/outputs/scratch. Real cancellation,
elapsed time, sampled RSS and total stage bytes are enforced independently of
the scientific resource receipts; sampled RSS is not OS reservation. Existing
lower configured limits bind; no increase to default600s to force passage.
Three stages (actual solve, original validation, supplement) consume one job
deadline, not three reset jobs. Supplement's own1800s cap cannot extend it.
Publication only follows child completion, offline replay, stable source/input
hashes, exact member inventory and true total-byte/quota checks.

## Protected publication and shell

Publish at derived/{owner}/{project}/joint/{job}/{fixed-relative-native-member}
with a canonical result index at the existing result_key. Nested member names
are exactly the existing calibration/frozen/models/result/instrument inventory;
never user-supplied paths. Exclusive files, fsync, final independent validation,
transactional source/artifact rows and uncertain-commit preservation mirror the
existing private custody semantics. Reconciliation, quota reservations, project
export/deletion and downloads must include every member, failed stage and source
dependency; unknown bytes require operator recovery, not recursive cleanup.

The shell's single processing sidebar submits a real job only after eligible
structural indexing and admitted native context; denial explains a factual gate
and offers the already executable offline workflow, without pretending an online
method ran. Completed result members feed the SAME bounded joint-result client
and native instrument. Private archive/native JSON exports retain actual array
values, source/version/hash identities, original selection/holdout states and
explicit false scientific/authenticity/public-activation claims. One existing
citations provider and ADR CSS only. Parent owns final integrated render.

## Conditioning applicability

M02 physical_conditioned_optimizer is prospective until committed public source
is read. Linear CG200 and nonlinear CG512 are distinct unchanged limits.
Independent single-property quadratic factors need source-derived smallness and
directed original-unit accuracy bounds; an arbitrary mu/pass callback is banned.
Two-property exact face-averaged quartic CrossGradient requires its own closed
Jacobian/CSR graph and peak-allocation proof, not automatic first-order7a/4a
admission. GN PSD is not a global curvature/model/prediction error certificate.
Old384 oracle failures remain immutable; only a new full actual fit matrix can
establish corrective acceptance with all original scientific predicates intact.
