"""Adversarial entry points for the acquisition/ingestion feature gates."""

from tests.adversarial._existing_pytest_gate import run_existing


def test_adversarial_aif_001_source_ledger_contract():
    run_existing(
        "tests/data/test_sources.py::test_ledger_contract_and_rights",
        "tests/data/test_sources.py::test_stead_is_unverified_provider_metadata_only",
    )


def test_adversarial_aif_002_immutable_asset_and_receipt():
    run_existing("tests/data/test_sources.py::test_immutable_raw_asset_and_receipt")


def test_adversarial_aif_003_allowlist_and_link_only():
    run_existing(
        "tests/data/test_sources.py::test_source_allowlist_and_link_only",
        "tests/data/test_sources.py::test_stead_is_unverified_provider_metadata_only",
    )


def test_adversarial_aif_004_format_dispatch():
    run_existing(
        "tests/data/test_ingest_dispatch.py::test_external_edi_never_opened_as_tar",
        "tests/data/test_ingest_dispatch.py::test_selected_edi_dispatch",
    )


def test_adversarial_aif_005_archive_bounds_and_observations():
    run_existing("tests/data/test_ingest_dispatch.py::test_archive_member_bounds_and_observation_contract")


def test_adversarial_aif_006_clear_lake_qc_only():
    run_existing(
        "tests/data/test_sources.py::test_clear_lake_source_pin",
        "tests/data/test_ingest_dispatch.py::test_selected_edi_dispatch",
    )


def test_adversarial_aif_007_provider_rights_and_no_raw_mirror():
    run_existing(
        "tests/data/test_sources.py::test_pygimli_provider_links_and_pins",
        "tests/data/test_sources.py::test_stead_is_unverified_provider_metadata_only",
        "tests/data/test_sources.py::test_no_external_raw_tracked",
    )


def test_adversarial_aif_008_actionable_failures():
    run_existing(
        "tests/data/test_sources.py::test_actionable_acquisition_errors",
        "tests/data/test_ingest_dispatch.py::test_unsupported_adapter_is_explicit",
    )


def test_adversarial_aif_009_source_inventory_documentation():
    run_existing("tests/data/test_sources.py::test_documented_source_inventory")
