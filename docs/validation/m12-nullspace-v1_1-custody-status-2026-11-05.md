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
`receipt.json`, and `checkpoint.npz`. The hash-matching receipt is separately
present in the checkout at
`data/derived/v2/models/m12-nullspace-v1_1/receipt.json`; its SHA-256 matches
the historical value above. It contains 480 held-out `per_record` metric rows,
but those rows are not raw solver inputs. The source v3.1 checkpoint and
training receipt named by the receipt are absent from the checkout. This
establishes that the exact external run location was unavailable in the
current Windows environment. It does not establish whether another
independently managed copy exists elsewhere.

## Current interpretation

The successful 2026-10-31 historical replay remains documented evidence of a
past verification, and the hash-matching receipt with per-case metrics remains
available for inspection and metric reanalysis. It is not a current full
reproduction: the exact source checkpoint, training receipt, and raw generated
inputs are unavailable in the checked locations, so this audit did not rerun
the solver or recompute M12 metrics. The method remains unaccepted for M12 and
product release. Do not regenerate substitute files under the old run
identity or treat the receipt summary as a replacement for the missing
source-run artifacts.

To restore reproducibility, recover the original run files and verify the
receipt and checkpoint hashes above before invoking
`scripts/verify_m12_nullspace_v1_1_compat.py`. If those exact bytes cannot be
recovered, any new run must use a new immutable output identity and a separately
reviewed protocol; it cannot retroactively validate this receipt.
