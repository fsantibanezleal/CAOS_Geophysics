"""Read-only ZIP census on retained real bytes; no fit or extraction admission."""
import copy
import io
import json
import warnings
import zipfile

import pytest

from app.magnetic_contract import science
from tests.api.test_magnetic_owned_custody import actual_generation as retained_generation


@pytest.fixture(scope="module")
def actual_archive(tmp_path_factory):
    science()
    from magnetic_result_export import export_zip
    generation, _, imported, _ = retained_generation.__wrapped__()
    destination = tmp_path_factory.mktemp("retained-zip") / "numeric.zip"
    export_zip(generation, destination)
    return destination.read_bytes(), imported


def test_readonly_actual_manifest_and_member_hashes(actual_archive):
    from magnetic_result_export import inspect_zip_bytes
    raw, imported = actual_archive
    manifest = inspect_zip_bytes(raw)
    assert manifest["generation_sha256"] == imported["generation_sha256"]
    assert manifest["original"]["included"] is False
    assert not any(manifest["result"]["claims"].values())


@pytest.mark.parametrize("attack", ["traversal", "extra", "duplicate", "link", "compression",
                                    "member_hash", "manifest_hash", "missing"])
def test_closed_readonly_inventory_refuses_retained_zip_mutations(actual_archive, attack):
    from magnetic_result_export import inspect_zip_bytes
    from magnetic_survey_json import InputError, canonical
    raw, _ = actual_archive
    with zipfile.ZipFile(io.BytesIO(raw)) as original:
        records = [(copy.copy(info), original.read(info)) for info in original.infolist()]
    numeric = next(i for i, (info, _) in enumerate(records) if info.filename.endswith(".npy"))
    if attack == "traversal": records[numeric][0].filename = "../outside.npy"
    if attack == "link": records[numeric][0].external_attr = 0o120600 << 16
    if attack == "compression": records[numeric][0].compress_type = zipfile.ZIP_DEFLATED
    if attack == "member_hash":
        info, body = records[numeric]
        records[numeric] = info, body[:-1] + bytes([body[-1] ^ 1])
    if attack == "manifest_hash":
        index = next(i for i, (info, _) in enumerate(records) if info.filename == "manifest.json")
        info, body = records[index]
        manifest = json.loads(body)
        manifest["generation_sha256"] = "0" * 64
        records[index] = info, canonical(manifest)
    if attack == "missing": records.pop(numeric)
    if attack == "duplicate": records.append(copy.deepcopy(records[numeric]))
    if attack == "extra":
        info = zipfile.ZipInfo("unknown.npy")
        info.create_system, info.external_attr = 3, 0o100600 << 16
        records.append((info, b"unknown numeric sibling"))
    output = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)  # deliberately authored duplicate
        with zipfile.ZipFile(output, "w") as writer:
            for info, body in records:
                writer.writestr(info, body)
    with pytest.raises(InputError):
        inspect_zip_bytes(output.getvalue())
