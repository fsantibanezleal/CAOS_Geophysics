"""Adversarial acceptance entry points for the pinned online-MT tests.

The older test module is hash-bound by the M05/M06 source-reconciliation
receipt. Keep those historical test names intact and expose their live,
fail-capable cases under the adversarial names required by the current SDD.
"""

import pytest

import test_online_mt as mt


def test_adversarial_source_identity_and_m05_screen(make_harness):
    mt.test_source_identity_and_m05_screen(make_harness)


def test_adversarial_inverse_parameter_effect_and_independent_oracle(make_harness):
    mt.test_inverse_parameter_effect_and_independent_oracle(make_harness)


def test_adversarial_malformed_and_clear_lake_exclusion(make_harness, tmp_path):
    mt.test_malformed_and_clear_lake_exclusion(make_harness, tmp_path)


@pytest.mark.parametrize(
    "field,value",
    [
        ("measurement_unit", "ohm"),
        ("sign_convention", "-"),
        ("variance_convention", "per-real-component"),
        ("rotation_degrees", 90),
    ],
)
def test_adversarial_declared_physics_mismatch_fails_m05(make_harness, field, value):
    mt.test_declared_physics_mismatch_fails_m05(make_harness, field, value)


def test_adversarial_bundle_roundtrip_and_wrong_principal(make_harness):
    mt.test_bundle_roundtrip_and_wrong_principal(make_harness)


def test_adversarial_verified_snapshot_survives_source_drift(make_harness, tmp_path):
    mt.test_verified_snapshot_survives_source_drift(make_harness, tmp_path)


def test_adversarial_worker_gate_refuses_queued_mt(make_harness, monkeypatch):
    mt.test_worker_gate_refuses_queued_mt(make_harness, monkeypatch)


def test_adversarial_host_gate_defaults_closed(make_harness):
    mt.test_host_gate_defaults_closed(make_harness)


def test_adversarial_raw_receipt_tamper_blocks_m05(make_harness):
    mt.test_raw_receipt_tamper_blocks_m05(make_harness)


def test_adversarial_preflight_cancel_timeout_and_memory(make_harness, monkeypatch, tmp_path):
    mt.test_preflight_cancel_timeout_and_memory(make_harness, monkeypatch, tmp_path)
