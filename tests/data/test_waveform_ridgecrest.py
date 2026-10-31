"""Original negative seal plus admitted format replay; physical execution held."""

import hashlib
import json
import os
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data-pipeline"))
from waveform_input import (
    WaveformInputError,
    validate_request,
    scan_miniseed,
    scientific_identity,
    scan_stationxml,
    resolve_channel,
    utc_us,
)
import waveform_processing as processing
from waveform_evaluation import references_from_stp, references_from_scedc_cloud_stp

PRIVATE_ORIGINAL = Path(os.environ["CAOS_M08_ORIGINAL_ROOT"]) if os.environ.get("CAOS_M08_ORIGINAL_ROOT") else None
PINS = {
    "miniseed.raw": (32768, "425a7184012a5403e0431e5ed5161e0bd16115d6eab5132a51d27b66c3830ef6"),
    "stationxml.raw": (9388, "cd14c82f6e188975cc7b5cff2720e318ac6140f2550c50999ef4100f0fd71382"),
}


def original_request():
    seal_raw = (
        ROOT / "docs/design/features/m08-waveform-user-data/evidence/ridgecrest-selection-seal.json"
    ).read_bytes()
    assert hashlib.sha256(seal_raw).hexdigest() == "6c5356cb1ac3b3255de3aeab069d4fb90ca028a709410cae795d7b7800d36709"
    seal = json.loads(seal_raw)
    request = {
        k: seal[k]
        for k in (
            "channels",
            "conditioning_start_utc",
            "conditioning_end_utc",
            "analysis_start_utc",
            "analysis_end_utc",
            "representation",
            "adc_rails",
            "processing",
        )
    }
    request.update(
        schema="caos.local-waveform-request.v1",
        source={
            "kind": "provider",
            "citation": "SCEDC 10.7909/C3WD3xH1; CI 10.7914/SN/CI",
            "provider_url": seal["queries"]["miniseed"]["url"],
            "declared_sha256": PINS["miniseed.raw"][1],
            "rights": "private-use-attested",
            "processing_statement": "Exact privately acquired original counts; no response removal, resampling or rotation",
        },
    )
    return validate_request(request)


def bounded_original(name):
    assert PRIVATE_ORIGINAL is not None and PRIVATE_ORIGINAL.is_absolute(), "Select CAOS_M08_ORIGINAL_ROOT outside the repository"
    assert not PRIVATE_ORIGINAL.resolve().is_relative_to(ROOT)
    path = PRIVATE_ORIGINAL / name
    # Explicit fixed private source; no links/reparse points, traversal or discovery.
    for ancestor in (path, *path.parents):
        assert not ancestor.is_symlink()
        assert not getattr(ancestor, "is_junction", lambda: False)()
    expected_length, expected_hash = PINS[name]
    with path.open("rb") as handle:
        raw = handle.read(expected_length + 1)
    assert len(raw) == expected_length and hashlib.sha256(raw).hexdigest() == expected_hash
    return raw


def original_outcome():
    """Reopen historical rejection; never pretend current parser returned it."""
    request = original_request()
    raw, xml = bounded_original("miniseed.raw"), bounded_original("stationxml.raw")
    records = scan_miniseed(raw, request)
    receipt = ROOT / "docs/design/features/m08-waveform-user-data/evidence/ridgecrest-terminal-20261003.json"
    body = receipt.read_bytes()
    assert hashlib.sha256(body).hexdigest() == "6e340817230a8096c5f9eefda4b138e8fb985e7b9982dfb50a93535bacb1af2d"
    outcome = json.loads(body)
    assert outcome["request"] == request and outcome["scientific_sha256"] == scientific_identity(request)
    assert outcome["record_count"] == len(records)
    assert outcome["sample_count"] == sum(row["npts"] for row in records)
    assert outcome["safe_error"]["code"] == "waveform_format"
    for name, value in (("miniseed", raw), ("stationxml", xml)):
        assert outcome["sources"][name] == {"bytes": len(value), "sha256": hashlib.sha256(value).hexdigest()}
    return outcome


def test_original_rejection_seal_and_current_format_admission_only(monkeypatch):
    if os.environ.get("CAOS_M08_ORIGINAL") != "1":
        pytest.skip("Explicit private exact-original opt-in required; no automatic acquisition")
    calls = []
    monkeypatch.setattr(processing, "_engine_modules", lambda: calls.append("engine"))
    monkeypatch.setattr(processing, "_decode_record", lambda *a: calls.append("decode"))
    monkeypatch.setattr(processing, "_read_inventory", lambda *a: calls.append("inventory"))
    outcome = original_outcome()
    assert calls == []
    assert outcome["status"] == "input_rejected" and outcome["safe_error"]["field"] == "document"
    assert outcome["physical_arrays_emitted"] is False
    dto = scan_stationxml(bounded_original("stationxml.raw"))
    req = original_request()
    selected, reasons = resolve_channel(
        dto, ("CI", "GSC", "", "HNZ"), utc_us(req["conditioning_start_utc"]), utc_us(req["conditioning_end_utc"]), 100
    )
    assert reasons == []
    assert selected["native_unit"] == "m/s2"
    assert selected["response_unit_ledger"][1]["original_input_unit"] is None
    assert selected["response_unit_ledger"][1]["effective_input_unit"] == "V"
    assert calls == []  # No physical engine execution, even after successful preflight.
    # Raw hashes and source bytes are rechecked, not repaired for a positive case.
    for name in PINS:
        assert hashlib.sha256(bounded_original(name)).hexdigest() == PINS[name][1]


def test_original_catalogue_retains_unsupported_after_terminal_seal():
    if os.environ.get("CAOS_M08_ORIGINAL") != "1":
        pytest.skip("Explicit private exact-original opt-in required")
    receipt = ROOT / "docs/design/features/m08-waveform-user-data/evidence/ridgecrest-terminal-20261003.json"
    assert (
        hashlib.sha256(receipt.read_bytes()).hexdigest()
        == "6e340817230a8096c5f9eefda4b138e8fb985e7b9982dfb50a93535bacb1af2d"
    )
    # No implicit source discovery/download; absent exact path is a failure,
    # not an omitted field case. Catalogue access follows the committed seal.
    phase_path = os.environ.get("CAOS_M08_PHASE")
    assert phase_path is not None and Path(phase_path).is_absolute()
    path = Path(phase_path)
    for ancestor in (path, *path.parents):
        assert not ancestor.is_symlink()
        assert not getattr(ancestor, "is_junction", lambda: False)()
    with path.open("rb") as handle:
        raw = handle.read(7209)
    assert len(raw) == 7208
    assert hashlib.sha256(raw).hexdigest() == "f16a0f2994f12590aae981e08758118672e962d1a9665bf133634c8e2add3b89"
    with pytest.raises(WaveformInputError) as info:
        references_from_stp(raw, "38457511", ("CI", "GSC", "", "HNZ"))
    assert info.value.code == "waveform_format" and info.value.field == "document"
    assert info.value.__cause__ is None and info.value.__context__ is None
    cloud = references_from_scedc_cloud_stp(raw, "38457511", ("CI", "GSC", "", "HNZ"))
    assert cloud["source_format"] == "scedc-cloud-stp-10/v1"
    assert cloud["rows"] == [] and cloud["unsupported_or_ambiguous_rows"] == []
