"""Local bundle envelope integrity and atomic pointer controls."""

import copy

import pytest

import magnetic_survey_bundle as bundle
from magnetic_survey_json import InputError, digest
from magnetic_bundle_support import make_manifest


def test_validates_generation_identity_and_history_inventory():
    manifest, payloads = make_manifest()
    report = bundle.validate_bundle_container(manifest, payloads)
    assert report["generation_sha256"] == manifest["generation_sha256"]
    assert report["members"] == len(manifest["members"])
    tampered = copy.deepcopy(manifest)
    tampered["result"]["status"] = "complete"
    with pytest.raises(InputError):
        bundle.validate_bundle_container(tampered, payloads)


def test_container_cannot_publish_a_success_without_scientific_result_validation():
    manifest, payloads = make_manifest(status="complete")
    with pytest.raises(InputError, match="full scientific schema validation"):
        bundle.validate_bundle_container(manifest, payloads)


@pytest.mark.parametrize("mutation", ["original", "claims", "reference", "member_name", "unit", "request_semantics"])
def test_container_rejects_identity_claim_and_member_inventory_changes(mutation):
    manifest, payloads = make_manifest()
    changed = copy.deepcopy(manifest)
    if mutation == "original":
        changed["original"]["sha256"] = "b"*64
    elif mutation == "claims":
        changed["result"]["claims"]["online_admitted"] = True
    elif mutation == "reference":
        changed["result"]["history"]["index"]["member"] = "missing.npy"
    elif mutation == "member_name":
        changed["members"][0]["name"] = "../unsafe.npy"
    elif mutation == "unit":
        ref = changed["request_metadata"]["geometry"]["receivers_m"]["member"]
        next(member for member in changed["members"] if member["name"] == ref)["unit"] = "SI"
    else:
        changed["request_metadata"]["frame"]["vertical_positive"] = "down"
    unsigned = dict(changed)
    unsigned.pop("generation_sha256")
    changed["generation_sha256"] = digest(unsigned)
    with pytest.raises(InputError):
        bundle.validate_bundle_container(changed, payloads)


def test_pointer_swap_keeps_prior_generation_when_replacement_fails(tmp_path, monkeypatch):
    first, first_payloads = make_manifest("local_calibrate", "failed")
    first_written = bundle.write_bundle_generation(tmp_path / "bundles", first, first_payloads)
    current_before, _ = bundle.read_bundle_generation(tmp_path / "bundles")
    assert current_before["generation_sha256"] == first["generation_sha256"]

    second, second_payloads = make_manifest("local_evaluate", "ineligible")
    def reject_pointer_replace(*_args, **_kwargs):
        raise OSError("injected pointer interruption")
    monkeypatch.setattr(bundle.os, "replace", reject_pointer_replace)
    with pytest.raises(OSError, match="injected pointer interruption"):
        bundle.write_bundle_generation(tmp_path / "bundles", second, second_payloads)

    current_after, _ = bundle.read_bundle_generation(tmp_path / "bundles")
    assert current_after["generation_sha256"] == first["generation_sha256"]
    assert current_after["generation_sha256"] != second["generation_sha256"]
    assert (tmp_path / "bundles" / "generations" / first_written["generation"]).is_dir()


def test_partial_generation_write_keeps_prior_pointer(tmp_path, monkeypatch):
    first, first_payloads = make_manifest("local_calibrate", "failed")
    bundle.write_bundle_generation(tmp_path / "bundles", first, first_payloads)
    second, second_payloads = make_manifest("local_evaluate", "ineligible")

    def fail_fsync(_fd):
        raise OSError("injected storage failure")
    monkeypatch.setattr(bundle.os, "fsync", fail_fsync)
    with pytest.raises(OSError, match="injected storage failure"):
        bundle.write_bundle_generation(tmp_path / "bundles", second, second_payloads)
    current, _ = bundle.read_bundle_generation(tmp_path / "bundles")
    assert current["generation_sha256"] == first["generation_sha256"]


def test_read_rejects_member_corruption_and_unlisted_files(tmp_path):
    manifest, payloads = make_manifest()
    written = bundle.write_bundle_generation(tmp_path / "bundles", manifest, payloads)
    directory = tmp_path / "bundles" / "generations" / written["generation"]
    target = directory / manifest["members"][0]["name"]
    raw = target.read_bytes()
    target.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
    with pytest.raises(InputError):
        bundle.read_bundle_generation(tmp_path / "bundles")

    target.write_bytes(raw)
    (directory / "unexpected.bin").write_bytes(b"not in manifest")
    with pytest.raises(InputError):
        bundle.read_bundle_generation(tmp_path / "bundles")
