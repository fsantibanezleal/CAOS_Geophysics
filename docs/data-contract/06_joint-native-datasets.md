# Structurally indexed native joint datasets

The protected joint upload endpoint retains ordinary original bytes. A native
dataset binds an exact development/sealed role pair, not a ZIP, a machine path,
a remote URL, executable code or an optimizer selector. Structural indexing does
not fit, decode held-out values or assert scientific accuracy.

POST `/api/projects/{project_id}/joint-datasets` takes a bounded JSON object with
exactly `development` and `sealed` maps. Each literal native basename maps to its
owned uploaded asset UUID. The request is at most65536bytes and40members, with
unique asset IDs. Each role's original request/sealed manifest closes its member
inventory, shapes, original file/data digests and provided raw/correction files.
No missing/extra member, mixed project/owner or substituted role is accepted.

Before scanning any original, the complete declared member sum must fit the
unchanged256MiB input bound. The API holds each original while independently
checking its exact file/data hash and bounded NPY1 header. It reads only bounded
JSON metadata and opaque binary bytes, never numerical/sealed observation values.
The closed development/sealed plan identity and sealed manifest count/noise/file/
row digest declarations agree. Full physical/partition/covariance QC remains the
original numerical intake's responsibility in the fixed scientific child.

The immutable index at the canonical dataset key has schema
`geophysics.joint-native-dataset/v1`, parser `m11-native-members/v1`, complete
original metadata and all per-member asset/source/version/rights/hash/byte/
descriptor bindings. `scientific_values_decoded` and `scientific_accepted` are
false; `qc_verdict` is `structural_native_members_only`. Its source-observation
dimension is the true scalar sum of both modality receiver counts, not an extra
factor of two. A duplicate primary development request/parser rejects.

Every member has a `joint_dataset_sources` row. This additive table belongs to
allocated `0006_joint_artifacts`, directly after `0005_physical_forest`; the
successor body refuses older/unknown predecessors before creating anything.
Legacy `joint_schema.py` is not this successor and must not be mounted. The parent owns the real
Alembic revision/head and canonical validator/reconciliation/route unions. Existing
M08 tables and source rows are preserved, not copied into this leaf or overwritten.

GET `/api/projects/{project_id}/joint-datasets/{dataset_id}` rechecks the index,
complete dependency table, owner/project/source versions/rights, original file/
data digests and manifests; it is private and no-store. Parent startup, worker,
publication and export invoke the same dependency validator, in addition to the
canonical file/quota inventory. Neither an index-only check nor a port is custody.

The fixed worker materializes exclusive copies of every original beneath its
external job stage. It preserves bytes and exact role inventories, rechecks source
rows before/after copying and refuses to reuse a previous stage. A failure keeps
its evidence for exact recovery; no recursive cleanup of unknown bytes. Copying
inputs neither starts an inverse nor grants interpreter/platform/host admission.

Index publication is exclusive and fsynced, charged to the existing derived
quota, with source rows in one transaction. An uncertain commit keeps the index
and originals. Committed indexes are reconciled; orphan indexes require recovery.
Deleting the indexed dataset cascades only its explicit dependency rows before
the canonical raw-source deletion. No backup/SMTP/Pages prerequisite is added.

Gates: actual canonical authenticated API with the committed read-only M08
predecessor, complete native role pair, exact materialization, duplicate/inventory/
ownership/source/file tampering, predecessor refusal, uncertain commit outcomes,
startup/deletion/quota and original stat-identity drift controls. This contract is
not acceptance of coupled scientific precision or the still-separate online
worker/result/sidebar integration.
