# Potential-field source intake requirements

Date: 2026-10-03. Parent SDD: R-001, R-002, R-003 and the Bartlett Springs acquisition scope. This unit does not replace the promised field case or accept a solver.

| ID | EARS requirement | Named failing gate |
|---|---|---|
| PFI-001 | THE source ledger SHALL distinguish the actually retrieved USGS metadata from the author-processed Clear Lake archive, with exact immutable hashes, versions and source-specific rights. | `tests/data/test_potential_sources.py::test_adversarial_pinned_source_identity_and_rights` |
| PFI-002 | WHEN a reviewed ZIP is imported, THE extractor SHALL validate its complete bounded inventory and extract only named, byte/hash-pinned observation members without replacing existing bytes. | `tests/data/test_potential_sources.py::test_adversarial_selected_members_immutable` |
| PFI-003 | IF an archive contains traversal, symlink, duplicate, unbounded expansion or unexpected selected bytes, THEN THE extractor SHALL reject it before publishing extracted members. | `tests/data/test_potential_sources.py::test_adversarial_archive_negative_controls` |
| PFI-004 | WHEN a principal-fact CSV is profiled, THE result SHALL preserve every named physical channel, correction-state distinction, coordinate/height ambiguity, missing/error flags and source lineage without creating predictions or geological truth. | `tests/data/test_potential_sources.py::test_adversarial_profile_preserves_correction_and_missingness` |
| PFI-005 | THE local guide SHALL provide reproducible acquisition/profile commands, primary citations, rights/format/uncertainty semantics and explicit unresolved modelling limits. | `tests/data/test_potential_sources.py::test_adversarial_profile_guide_and_real_source` |
