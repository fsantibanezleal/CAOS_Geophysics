# Owned physical catalog and original-byte identity

The physical catalog projects saved dataset receipts and complete selected
ancestry. It does not run corrections, transforms or scientific admission.
Operator installation, authenticated ownership and the caller's actual writer
lease remain separate from navigation. The legacy dataset representation stays
the default; a catalog implementation or source hash does not activate workers.

## Navigation and bounded metadata

The explicit list representation uses
`schema=geophysics.physical-dataset-list/v2`, `limit=1..32` and an optional opaque
`cursor`. Its closed wrapper contains `schema`, `project_id`, `items` and
`next_cursor`. Every item is the nineteen-key compact receipt in
`app/physical_catalog.py`. A receipt contains stored byte counts and hashes,
root/parent identities, native station count, declared state and actual producing
record, not station vectors or private storage paths. A page is at most 256 KiB;
one receipt is at most 4096 bytes. Overflow is refused, not partially projected.

The first page fixes a SQL row-birth cutoff and its actual anchor. Later births
remain outside that traversal, even if their creation timestamp sorts earlier.
Saved creation time and dataset UUID determine keyset ordering. The signed
cursor retains the literal SQL timestamp: either historical suffix-free UTC or
native publication's `+00:00`, with at most six fractional digits. It does not
normalize the comparison key. Receipt `created_at` uses a UTC wire timestamp.
Non-UTC offsets, excessive precision, unknown cursor versions and wrong
owner/project contexts are refused. A missing or changed cutoff anchor cannot
silently restart pagination. Cursor bytes are at most 256; clients send them
unchanged and discard pages when the selected context changes. The signing key
is operator configuration and never belongs in a response or client request.

The `geophysics.physical-lineage/v2` detail representation contains the selected
root-to-current chain, not every branch. Its closed seven-key wrapper has at
most five nodes and four edges/productions. Each node retains eleven identities
and each production fourteen saved input/result/module/verdict fields. A root
has one node and no producer. Every saved producing edge and original input is
audited before projection; a signed navigation token cannot replace that audit.
Transform non-pass and null adapter identities remain explicit, not scientific
success. Unknown or duplicate query fields are not representation aliases.

## Original bytes and digest domains

Read an entire dataset separately when its physical values are needed. The
original-byte reader checks complete producer ancestry and returns the actual
saved JSON bytes. Whitespace, Unicode, numeric spelling and ordering are part
of that file SHA-256; neither object serialization nor the separate scientific
canonical digest can recreate it. Private responses use `Cache-Control:
no-store`. Foreign ownership is refused before disclosing saved data.

Catalog operations execute on the API session's existing native SQLite snapshot.
They do not create another ledger, commit writes or transfer authority to a
child task. Cancellation drains the actual queued native operation before
caller-held lifetime guards can release. Database ownership, immutable byte
identity and full scientific producer checks remain necessary even for a
read-only projection. Browser EOF/type/member verification and actual native
execution/resource evidence are separate from metadata navigation.
