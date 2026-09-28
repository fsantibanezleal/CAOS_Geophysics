# Acquisition and ingestion foundation tasks

Dependency order; requirement IDs refer to [requirements.md](requirements.md).

1. [x] Review approved product SDD, ADR-0075/0057/0069, current source ledger, `ingest.py`, EDI QC and provider references. Map rights and current tar-as-EDI regression. AIF-01, AIF-04, AIF-06, AIF-07.
2. [x] Version and validate the source ledger; pin exact provider objects and rights decisions. AIF-01, AIF-06, AIF-07.
3. [x] Implement selected-source acquisition, immutable raw assets, receipts, size/hash and network/path bounds. AIF-02, AIF-03, AIF-08.
4. [x] Dispatch tar/EDI/unsupported formats, preserve observation semantics and keep `--external` restricted to fetchable archives. AIF-04, AIF-05, AIF-06, AIF-08.
5. [x] Add hermetic tests for the source inventory, malicious/failure cases, dispatch regression and ignored raw boundary. AIF-01 through AIF-08.
6. [x] Write data contract and source guide with exact commands and limitations; update local fetch scripts. AIF-09.
7. [x] Run named gates, record per-requirement convergence and source review, then commit and push the task branch after tests. AIF-01 through AIF-09. See [convergence.md](convergence.md) for the pre-commit evidence; branch push is the final handoff action, not a scientific-release gate.
