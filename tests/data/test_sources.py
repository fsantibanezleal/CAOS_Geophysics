"""Source rights, exact object identity, local immutability and publication boundary."""
import hashlib
import json
from pathlib import Path
import subprocess
from urllib.request import Request

import pytest

from sources import SourceError, _NoRedirect, acquire_source, load_ledger


ROOT = Path(__file__).resolve().parents[2]


def _test_ledger(tmp_path, payload=b"verified local bytes", *, mode="manual"):
    record = dict(load_ledger()["simpeg-gravity"])
    record.update(source_id="test-source", acquisition=mode, format="simpeg-obs-tar-gz",
                  expected_bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest(),
                  raw_path="data/downloads/test-source.tar.gz")
    ledger = tmp_path / "ledger.json"
    ledger.write_text(json.dumps({"schema": "inverse-earth.sources/v2", "sources": [record]}), encoding="utf-8")
    local = tmp_path / "incoming.bin"
    local.write_bytes(payload)
    return ledger, local, record


def test_ledger_contract_and_rights():
    records = load_ledger()
    assert set(records) == {"simpeg-gravity", "simpeg-magnetics", "original-synthetic",
                            "clear-lake-cl061", "auslamp-nsw-c15", "pygimli-slagdump", "pygimli-koenigsee",
                            "stead-metadata"}
    assert {record["rights_decision"] for record in records.values()} <= {
        "mirror", "provider-link-only", "derivative-only", "forbidden"}
    assert all(record["raw_path"].startswith("data/downloads/") for record in records.values()
               if record["raw_path"])
    assert records["original-synthetic"]["acquisition"] == "generated"
    assert records["original-synthetic"]["sha256"] is None
    for source_id in ("simpeg-gravity", "simpeg-magnetics"):
        assert records[source_id]["acquisition"] == "fetch"
        assert records[source_id]["rights_decision"] == "provider-link-only"
        assert records[source_id]["expected_bytes"] > 0


def test_immutable_raw_asset_and_receipt(tmp_path):
    ledger, local, record = _test_ledger(tmp_path)
    _, target, first = acquire_source("test-source", local_file=local, root=tmp_path, ledger_path=ledger)
    assert target.read_bytes() == local.read_bytes()
    assert first["asset_id"] == f"sha256:{record['sha256']}"
    assert first["storage_key"] == record["raw_path"]
    assert first["rights_decision"] == "provider-link-only"
    receipt_path = tmp_path / "data/raw/acquisition/test-source.json"
    assert json.loads(receipt_path.read_text(encoding="utf-8")) == first
    _, same_target, second = acquire_source("test-source", root=tmp_path, ledger_path=ledger)
    assert same_target == target and second == first
    local.write_bytes(b"different supplied input")
    with pytest.raises(SourceError, match="test-source: byte/hash mismatch"):
        acquire_source("test-source", local_file=local, root=tmp_path, ledger_path=ledger)
    assert target.read_bytes() == b"verified local bytes"
    damaged = dict(first, rights_decision="mirror")
    receipt_path.write_text(json.dumps(damaged), encoding="utf-8")
    with pytest.raises(SourceError, match="immutable receipt drift in rights_decision"):
        acquire_source("test-source", root=tmp_path, ledger_path=ledger)
    receipt_path.write_text(json.dumps(dict(first, owner_scope="another-owner")), encoding="utf-8")
    with pytest.raises(SourceError, match="immutable receipt drift in owner_scope"):
        acquire_source("test-source", root=tmp_path, ledger_path=ledger)
    receipt_path.write_text(json.dumps(first), encoding="utf-8")
    target.write_bytes(b"changed bytes")
    with pytest.raises(SourceError, match="test-source: byte/hash mismatch"):
        acquire_source("test-source", root=tmp_path, ledger_path=ledger)
    assert target.read_bytes() == b"changed bytes"  # acquisition did not overwrite the disputed asset


def test_source_allowlist_and_link_only(tmp_path):
    ledger, local, record = _test_ledger(tmp_path)
    with pytest.raises(SourceError, match="Unknown source_id"):
        acquire_source("unknown", root=tmp_path, ledger_path=ledger)
    with pytest.raises(SourceError, match="automatic fetch is not approved.*--file"):
        acquire_source("test-source", root=tmp_path, ledger_path=ledger)
    with pytest.raises(SourceError, match="Unapproved redirect.*update the reviewed source ledger"):
        _NoRedirect().redirect_request(Request("https://storage.googleapis.com/approved"), None,
                                       302, "moved", {}, "https://evil.example/asset")
    for url in ("http://storage.googleapis.com/file.tar.gz", "https://127.0.0.1/file.tar.gz",
                "https://evil.example/file.tar.gz"):
        record.update(acquisition="fetch", object_url=url)
        ledger.write_text(json.dumps({"schema": "inverse-earth.sources/v2", "sources": [record]}),
                          encoding="utf-8")
        with pytest.raises(SourceError, match="HTTPS|allowlist"):
            load_ledger(ledger)
    record.update(acquisition="manual", object_url="https://raw.githubusercontent.com/provider/object")
    record["raw_path"] = "data/downloads/../escaped.tar.gz"
    ledger.write_text(json.dumps({"schema": "inverse-earth.sources/v2", "sources": [record]}),
                      encoding="utf-8")
    with pytest.raises(SourceError, match="storage key"):
        load_ledger(ledger)


def test_clear_lake_source_pin():
    station = load_ledger()["clear-lake-cl061"]
    assert station["format"] == "edi-transfer-function"
    assert station["acquisition"] == "fetch"
    assert station["object_url"] == (
        "https://data.earthscope.org/archive/seismology/products/emtf/surveys/2022/"
        "MT_TF_USGS-GMEG.2022.cl061/USGS-GMEG.2022.cl061.edi")
    assert station["expected_bytes"] == 16411
    assert station["sha256"] == "90c5c96cd69d6d29c866a768097cb3b38bc20e8b9c143e24bf10b2d253261e83"
    assert station["release_doi"] == "10.5066/P14KAQ3M"
    assert station["transfer_function_doi"] == "10.17611/DP/EMTF/GMEG/Clearlake"
    assert station["rights_decision"] == "derivative-only"
    assert station["public_derivative"] == "data/derived/v2/edi/clear-lake-cl061-screen.json"
    edi_root = ROOT / "data/derived/v2/edi"
    manifest = json.loads((edi_root / "manifest.json").read_text(encoding="utf-8"))
    field = next(item for item in manifest["field_screens"] if item["id"] == "cl061")
    screen_file = edi_root / field["artifact"]
    screen = json.loads(screen_file.read_text(encoding="utf-8"))
    assert field["source_sha256"] == station["sha256"]
    assert field["source_bytes"] == station["expected_bytes"]
    assert field["station_url"] == station["provider_url"]
    assert hashlib.sha256(screen_file.read_bytes()).hexdigest() == field["artifact_sha256"]
    assert screen["id"] == "cl061" and len(screen["frequencies_hz"]) == 42
    assert screen["one_d_inversion_eligible"] is False
    assert screen["inversion_performed"] is False and screen["methods"] == {} and screen["truth"] is None


def test_auslamp_c15_source_contract():
    station = load_ledger()["auslamp-nsw-c15"]
    assert station["acquisition"] == "manual"
    assert station["format"] == "edi-transfer-function"
    assert station["object_url"] == "https://ausmt.auscope.org.au/data/edi/auslamp-nsw-2016-21/C15.edi"
    assert station["expected_bytes"] == 23021
    assert station["sha256"] == "353953564964015c59eaaa0ce8f808ebec48af0d51c11759a14c21be00b20a8f"
    assert station["rights_decision"] == "mirror"
    assert "CC BY 4.0" in station["rights_statement"]
    assert station["station_record_sha256"] == "50b82ab1c9326414e1dabc418470fc1cb956b4ed039d63864c44571760560444"
    assert station["dimensionality_record_sha256"] == "412b267270b8f86f52233025fa0b4ccdba3f92b40d172a5d53697689c621e590"


def test_pygimli_provider_links_and_pins():
    records = load_ledger()
    expected = {"pygimli-slagdump": (5435, "c010a11b78ea4392cb926d675e847c74010b4cdec536aacaf8db6a644e886de2"),
                "pygimli-koenigsee": (9844, "cf8f6c8c79fd0f60984eefc61aff67b567b0c875f8f5c663fe904cdbf0d0414a")}
    for source_id, (size, digest) in expected.items():
        record = records[source_id]
        assert record["expected_bytes"] == size and record["sha256"] == digest
        assert record["acquisition"] == "manual" and record["rights_decision"] == "provider-link-only"
        assert "3bab9c6b96a606e2ca12cbdafc8c7da4f1b73c67" in record["object_url"]
        assert record["provider_url"].startswith("https://www.pygimli.org/")


def test_stead_is_unverified_provider_metadata_only(tmp_path):
    record = load_ledger()["stead-metadata"]
    assert record["acquisition"] == "provider-link"
    assert record["rights_decision"] == "provider-link-only"
    assert record["format"] == "stead-metadata-csv"
    assert record["verification_status"] == "user-reported-unverified"
    assert record["raw_path"] is None
    assert record["expected_bytes"] == 402560190
    assert record["sha256"] == "9b9007406ebfef8c182060c8bb4266d29bbc433985f91f7e2dc476c8aca08efe"
    assert record["object_url"] == "https://seisbench.gfz-potsdam.de/mirror/datasets/stead/metadata.csv"
    with pytest.raises(SourceError, match="stead-metadata: provider-link metadata is not a verified raw asset"):
        acquire_source("stead-metadata", root=tmp_path)
    assert not (tmp_path / "data").exists()


def test_actionable_acquisition_errors(tmp_path):
    ledger, local, record = _test_ledger(tmp_path)
    wrong = tmp_path / "wrong.bin"
    wrong.write_bytes(b"invalid")
    with pytest.raises(SourceError, match="test-source: byte/hash mismatch.*SHA-256"):
        acquire_source("test-source", local_file=wrong, root=tmp_path, ledger_path=ledger)
    assert not (tmp_path / record["raw_path"]).exists()
    with pytest.raises(SourceError, match="test-source.*https://"):
        acquire_source("test-source", root=tmp_path, ledger_path=ledger)


def test_no_external_raw_tracked():
    tracked = subprocess.run(["git", "ls-files", "data/downloads", "data/raw"], cwd=ROOT,
                             text=True, capture_output=True, check=True)
    assert tracked.stdout.strip() == ""


def test_documented_source_inventory():
    guide = (ROOT / "docs/guides/05_sources.md").read_text(encoding="utf-8")
    contract = (ROOT / "docs/data-contract/data-contract.md").read_text(encoding="utf-8")
    for source_id in load_ledger():
        assert source_id in guide
    for term in ("provider-link-only", "sha256", "data/downloads/", "data/raw/"):
        assert term in guide and term in contract
