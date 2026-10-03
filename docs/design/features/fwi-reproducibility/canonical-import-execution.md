# Owner-executed canonical container import

Date: 2026-10-03. Main executed the exact reviewed run3 import at `8285517`
using the plan-bound approval token. The implementation remains `bb8e601`.
This worker did not execute the importer; it verifies and persists the owner's
published canonical files and a separate execution receipt. Historical
[rehearsal evidence](../../../validation/fwi-container-migration-20261003.json)
and [review snapshot](version-import-review.md) remain unchanged, including
their accurate pre-execution `canonical_import_executed: false` statements.

## Actual execution and scoped bytes

The [portable execution proof](../../../validation/fwi-canonical-import-20261003.json)
copies the exact main attempt/success receipt values with original byte hashes,
and binds the published 139-file inventory to the reviewed stage. It records
every changed canonical path: 53 modified and two new files (`migration.json`
and `mt-replay.json`). There is no solver/tool/app-version change.

| Evidence | SHA-256 |
| --- | --- |
| Reviewed plan | `8ee0c2caf9470b320816417fa083a51ebf2e5010388a275a9edfd577e9941ad9` |
| Reviewed stage receipt | `e695f7bb7f6fc8abf4542c4b4b4e57c0fc9d087d7c41fafaf4d583141f275eeb` |
| Original private 137-file backup | `7dfc0fc18a0a45988f501a7aaedbda12abca3628cfa403b19696bda618aba266` |
| Published 139-file canonical tree | `2e19fadf4f5500295e9bf5a90f15634086247d1bdc66ea2082aef547906332a8` |

The backup is `data/raw/canonical-backups/pre-004002-20261003-run3`.
Its inventory exactly equals the frozen original plan; `git ls-files` is empty
and `git check-ignore` succeeds. Retain this original forever private, ignored
and unstaged: do not publish, delete or replace it. Only hashes/counts and its
retention policy appear in the portable proof, not its original file contents.
The ignored original combined candidate and all 133 producer/auxiliary bytes
remain identical. The stage was renamed into canonical, not erased.

0.04.002 is the new corrected container header. Original 0.04.000/0.04.001
producer versions and all version-specific current source fingerprints remain
intact. The reviewed guard epoch exception is explicit and unchanged; old
tool hashes in independent receipts are not replaced. Full scientific coverage
is 20 cases /120 conditions /348 methods, with 122 recovered, 184 unresolved,
six failed and 36 negative controls retained. Main reports the post-import
full artifact guard passed; this worker independently rechecks it.

## Integration and post-import regression

The source-scoped canonical milestone is persisted before a normal merge of
reviewed develop `54277f95b836a302ab02ccb4af1fdd4d822a7eb2`. Its source-ledger
metadata-verification unit is separate from FWI/MT physics and changes no frozen
scientific producer/importer/guard module. Preserve both documentation nav lists
if the merge requires resolving them. Post-integration regression receipts will
be recorded here and in the new portable execution proof, not in old rehearsals.

This canonical milestone is not app-version promotion, host admission, release,
merge to main or deployment. R008 remains failed and 18 requirements unresolved;
main's disk 29.42% is below the unchanged 30% gate. Original independent FWI
48-model and MT 4,038-state/3,072-refit receipts remain separately source-pinned.
Synthetic recovery is not geological truth. The offline race/no distributed
lock limitations remain as originally reviewed.
