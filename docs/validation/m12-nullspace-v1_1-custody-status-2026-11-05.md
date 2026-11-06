# M12 null-space v1.1 current custody status

Audit date: 2026-11-05  
Checkout revision: `cdcec12658f90412af47855b665786cde2341090`

## Finding

The historical compatibility replay is documented in
[`m12-nullspace-v1_1-compatible-replay-2026-10-31.json`](m12-nullspace-v1_1-compatible-replay-2026-10-31.json).
That record binds receipt SHA-256
`30df0c2ad495bd850dda602b1c96725be8290dd086119fb3e8e75355fe9dea22`,
checkpoint SHA-256
`0f7a8fc43a078ab4cb16016774d44b356ccb70d9c60e0f197506fd3f7a53ea03`,
four replayed cohorts, and the bounded synthetic verdict. It explicitly keeps
`scientific_acceptance` false.

The record names this external run directory:

```text
E:\_worktrees\_runs\m12-nullspace-v1_1-full-20261027b
```

On the audit date, `Test-Path -LiteralPath` returned false for that directory,
`receipt.json`, and `checkpoint.npz`. This establishes that the exact recorded
location was unavailable in the current Windows environment. It does not
establish whether another independently managed copy exists elsewhere.

## Current interpretation

The successful 2026-10-31 historical replay remains documented evidence of a
past verification. It is not a current reproduction: the exact receipt,
checkpoint, and per-case arrays are not available at their recorded path, so
this audit did not rerun or recompute any M12 metric. The method remains
unaccepted for M12 and product release. Do not regenerate substitute files
under the old run identity or treat the committed summary JSON as a replacement
for the missing source-run artifacts.

To restore reproducibility, recover the original run files and verify the
receipt and checkpoint hashes above before invoking
`scripts/verify_m12_nullspace_v1_1_compat.py`. If those exact bytes cannot be
recovered, any new run must use a new immutable output identity and a separately
reviewed protocol; it cannot retroactively validate this receipt.
