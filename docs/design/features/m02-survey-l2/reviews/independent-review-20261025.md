# Independent evidence review: ordinary gravity L2

Date: 2026-10-25. Review mode: read-only source and execution-receipt audit.

## Reviewed scope

The reviewer checked the hashed numerical source and test files, the 213-case
supporting JUnit receipt, all 24 per-condition JUnit/log receipts, and the
recorded outputs against their hashes, sizes, case counts and outcomes. The
review confirmed 213 supporting passes and 24/24 locked matrix passes with no
failures, errors or skips. The numerical files named by the receipt matched
their recorded hashes.

This is independent inspection of the local execution evidence. It is not an
independent numerical reimplementation or a field-data, API, UI, GPU, VPS,
release or whole-product acceptance.

## Findings and disposition

1. **Status text contradicted the run receipt.** The requirements, contract and
   design still described the implemented controls as prospective or not run.
   Their status statements were updated to match the dated receipt and preserve
   the explicit distinction from product acceptance.
2. **Executed orchestration script bytes are unavailable.** The matrix runner
   was edited after launch. The exact pre-edit script bytes and hash were not
   retained. Per-case JUnit/log files and numerical source hashes were verified,
   but the orchestration edit limits exact procedural replay. This remains an
   evidence limitation; no hash was inferred or reconstructed.
3. **Optimizer naming requires scope.** The bounded solver is a tested hybrid
   built on SimPEG `ProjectedGNCG`; it must not be described as unmodified
   SimPEG GPCG convergence. The implementation's stated limitation remains.

No hash mismatch or direct numerical-source contradiction was found in the
reviewed scope. The result is accepted only as a local synthetic/native control
pass. Broader product gates remain open.
