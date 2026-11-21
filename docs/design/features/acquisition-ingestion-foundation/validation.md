# Acquisition and ingestion foundation validation

This table maps the current requirement IDs to executable adversarial entry points. Run outcomes and dated source/provider qualifications remain in [convergence.md](convergence.md). A present test name does not imply current product, field, or host acceptance.

| Requirement | Adversarial check | Gate |
| --- | --- | --- |
| AIF-001 | Assert stable ledger IDs, explicit rights and the unverified metadata-only boundary. | `tests/adversarial/test_acquisition_ingestion_adversarial.py::test_adversarial_aif_001_source_ledger_contract` |
| AIF-002 | Exercise immutable byte/receipt verification and refusal to overwrite tampered records. | `tests/adversarial/test_acquisition_ingestion_adversarial.py::test_adversarial_aif_002_immutable_asset_and_receipt` |
| AIF-003 | Exercise source allowlisting, URL/redirect constraints and provider-link-only behavior. | `tests/adversarial/test_acquisition_ingestion_adversarial.py::test_adversarial_aif_003_allowlist_and_link_only` |
| AIF-004 | Prove the external archive path does not open EDI as tar and explicit EDI selection is dispatched to QC. | `tests/adversarial/test_acquisition_ingestion_adversarial.py::test_adversarial_aif_004_format_dispatch` |
| AIF-005 | Exercise unsafe, oversized, duplicate, missing and malformed observation members before derivative publication. | `tests/adversarial/test_acquisition_ingestion_adversarial.py::test_adversarial_aif_005_archive_bounds_and_observations` |
| AIF-006 | Check the exact Clear Lake pin and current QC-only dispatch; this does not assert a layered-earth inversion. | `tests/adversarial/test_acquisition_ingestion_adversarial.py::test_adversarial_aif_006_clear_lake_qc_only` |
| AIF-007 | Check pinned provider records, STEAD's unverified metadata status and the no-raw-mirror boundary. | `tests/adversarial/test_acquisition_ingestion_adversarial.py::test_adversarial_aif_007_provider_rights_and_no_raw_mirror` |
| AIF-008 | Exercise actionable acquisition failures and explicit unsupported-format handling. | `tests/adversarial/test_acquisition_ingestion_adversarial.py::test_adversarial_aif_008_actionable_failures` |
| AIF-009 | Assert that source inventory documentation contains its required fields and commands; this is a presence check, not a destructive mutation test. | `tests/adversarial/test_acquisition_ingestion_adversarial.py::test_adversarial_aif_009_source_inventory_documentation` |
