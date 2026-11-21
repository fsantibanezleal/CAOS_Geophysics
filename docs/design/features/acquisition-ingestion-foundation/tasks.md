# Acquisition and ingestion foundation tasks

Dependency order; requirement IDs refer to [requirements.md](requirements.md).

1. [x] Review approved product SDD, ADR-0075/0057/0069, current source ledger, `ingest.py`, EDI QC and provider references. Map rights and current tar-as-EDI regression. AIF-001, AIF-004, AIF-006, AIF-007.
2. [x] Version and validate the source ledger; pin exact provider objects and rights decisions. AIF-001, AIF-006, AIF-007.
3. [x] Implement selected-source acquisition, immutable raw assets, receipts, size/hash and network/path bounds. AIF-002, AIF-003, AIF-008.
4. [x] Dispatch tar/EDI/unsupported formats, preserve observation semantics and keep `--external` restricted to fetchable archives. AIF-004, AIF-005, AIF-006, AIF-008.
5. [x] Add hermetic tests for the source inventory, malicious/failure cases, dispatch regression and ignored raw boundary. AIF-001 through AIF-008.
6. [x] Write data contract and source guide with exact commands and limitations; update local fetch scripts. AIF-009.
7. [x] Run named gates, record per-requirement convergence and source review, then commit and push the task branch after tests. AIF-001 through AIF-009. See [convergence.md](convergence.md) for the pre-commit evidence; branch push is the final handoff action, not a scientific-release gate.
