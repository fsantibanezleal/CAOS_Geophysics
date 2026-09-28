"""Hermetic archive and EDI dispatch, with no provider download or raw publication."""
import hashlib
import io
import json
import tarfile
import types
import sys

import numpy as np
import pytest

import ingest
from sources import load_ledger


def _ledger(tmp_path, payload: bytes, *, source_id="sample", fmt="simpeg-obs-tar-gz"):
    original = load_ledger()["simpeg-gravity" if fmt == "simpeg-obs-tar-gz" else "pygimli-slagdump"]
    record = dict(original)
    record.update(source_id=source_id, acquisition="manual", format=fmt,
                  expected_bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest(),
                  raw_path=f"data/downloads/{source_id}{'.tar.gz' if fmt == 'simpeg-obs-tar-gz' else '.ohm'}")
    ledger = tmp_path / "ledger.json"
    ledger.write_text(json.dumps({"schema": "inverse-earth.sources/v2", "sources": [record]}), encoding="utf-8")
    local = tmp_path / "incoming"
    local.write_bytes(payload)
    return ledger, local, record


def _archive(rows=b"0 0 1 2\n1 0 1 3\n0 1 1 4\n1 1 1 5\n", *, name="case_data.obs"):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as archive:
        member = tarfile.TarInfo(name)
        member.size = len(rows)
        archive.addfile(member, io.BytesIO(rows))
    return output.getvalue()


def _duplicate_archive():
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as archive:
        for name in ("first_data.obs", "second_data.obs"):
            rows = b"0 0 1 2\n1 0 1 3\n0 1 1 4\n1 1 1 5\n"
            member = tarfile.TarInfo(name)
            member.size = len(rows)
            archive.addfile(member, io.BytesIO(rows))
    return output.getvalue()


def test_external_edi_never_opened_as_tar(tmp_path, monkeypatch):
    records = [dict(load_ledger()[source_id]) for source_id in
               ("simpeg-gravity", "simpeg-magnetics", "clear-lake-cl061", "pygimli-slagdump")]
    ledger = tmp_path / "ledger.json"
    ledger.write_text(json.dumps({"schema": "inverse-earth.sources/v2", "sources": records}), encoding="utf-8")
    visited = []
    monkeypatch.setattr(ingest, "ingest_source", lambda source_id, **_: visited.append(source_id) or {"source_id": source_id})
    result = ingest.external(root=tmp_path, ledger_path=ledger)
    assert visited == ["simpeg-gravity", "simpeg-magnetics"]
    assert [entry["source_id"] for entry in result] == visited


def test_selected_edi_dispatch(tmp_path, monkeypatch):
    raw = tmp_path / "station.edi"
    raw.write_bytes(b">HEAD\n DATAID=cl061\n>END\n")
    record = dict(load_ledger()["clear-lake-cl061"])
    record["sha256"] = hashlib.sha256(raw.read_bytes()).hexdigest()
    monkeypatch.setattr(ingest, "acquire_source", lambda *_, **__: (record, raw, {"storage_key": "data/downloads/station.edi"}))
    monkeypatch.setattr(tarfile, "open", lambda *_, **__: pytest.fail("EDI was routed to tarfile"))
    called = {}

    def screen(path, **kwargs):
        called.update(path=path, options=kwargs)
        return {"provenance": {"source_sha256": record["sha256"]}, "id": "cl061",
                "frequencies_hz": list(range(42)), "one_d_inversion_eligible": False,
                "inversion_performed": False}

    monkeypatch.setitem(sys.modules, "edi", types.SimpleNamespace(screen_edi=screen))
    result = ingest.ingest_source("clear-lake-cl061", root=tmp_path)
    assert called == {"path": raw, "options": {"units": "mt", "variance_convention": "complex", "rotation": "preserve"}}
    assert result["frequencies"] == 42 and result["one_d_inversion_eligible"] is False
    assert result["inversion_performed"] is False
    assert not list(tmp_path.glob("**/*screen.json"))


def test_archive_member_bounds_and_observation_contract(tmp_path):
    ledger, local, record = _ledger(tmp_path, _archive())
    report = ingest.ingest_source("sample", local_file=local, root=tmp_path, ledger_path=ledger)
    assert report["source_sha256"] == record["sha256"]
    assert report["rows"] == 4 and report["value_unit"] == "mGal"
    assert report["uncertainty_policy"].startswith("3% observation SD")
    processed = tmp_path / report["preprocessed_path"]
    with np.load(processed) as arrays:
        assert arrays["locations_xyz_m"].shape == (4, 3)
        assert arrays["observed"].tolist() == [2, 3, 4, 5]
        assert (arrays["sigma_assumed"] > 0).all()
        assert not arrays["outlier_flag"].any()
    assert hashlib.sha256(processed.read_bytes()).hexdigest() == report["preprocessed_sha256"]
    assert ingest.ingest_source("sample", root=tmp_path, ledger_path=ledger) == report
    assert not (tmp_path / "data/derived").exists()

    for index, payload in enumerate((_archive(name="../escape_data.obs"),
                                     _archive(rows=b"0 0 1 nan\n1 0 1 3\n0 1 1 4\n1 1 1 5\n"),
                                     _archive(name="not_observations.txt"),
                                     _duplicate_archive(),
                                     _archive(rows=b"0" * 10_000_001))):
        case_root = tmp_path / f"bad-{index}"
        case_root.mkdir()
        case_ledger, case_local, _ = _ledger(case_root, payload)
        with pytest.raises(ingest.IngestError, match="unsafe archive|non-finite|exactly one|oversized"):
            ingest.ingest_source("sample", local_file=case_local, root=case_root, ledger_path=case_ledger)
        assert not (case_root / "data/raw/processed").exists()


def test_unsupported_adapter_is_explicit(tmp_path):
    ledger, local, record = _ledger(tmp_path, b"example ERT resistance", fmt="pygimli-ert-ohm")
    with pytest.raises(ingest.IngestError, match="verified raw asset.*no validated observation adapter.*Provider"):
        ingest.ingest_source("sample", local_file=local, root=tmp_path, ledger_path=ledger)
    assert (tmp_path / record["raw_path"]).read_bytes() == local.read_bytes()
    assert not (tmp_path / "data/derived").exists()
