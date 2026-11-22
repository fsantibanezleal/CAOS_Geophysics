"""Adversarial source and physics gates for the measured M06 MT lane."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data-pipeline"))

import mt_field_qc  # noqa: E402
from mt_field_qc import MTFieldQCError, inspect_edi, tensor_gate  # noqa: E402
from sources import LEDGER, SourceError, acquire_source, load_ledger  # noqa: E402

FIXTURE = ROOT / "data/fixtures/edi/halfspace-100-native.edi"


def _change_first_value(text: str, block: str, value: str) -> str:
    start = text.index(">" + block)
    first_line_end = text.index("\n", start)
    next_block = text.index("\n>", first_line_end)
    body = text[first_line_end:next_block]
    old = body.split()[0]
    return text[:first_line_end] + body.replace(old, value, 1) + text[next_block:]


def test_wrong_c15_bytes_never_enter_the_raw_store(tmp_path):
    source = load_ledger()["auslamp-nsw-c15"]
    wrong = tmp_path / "C15.edi"
    wrong.write_bytes(b"wrong bytes with no source identity")
    with pytest.raises(SourceError, match="byte/hash mismatch"):
        acquire_source("auslamp-nsw-c15", local_file=wrong, root=tmp_path, ledger_path=LEDGER)
    assert not (tmp_path / source["raw_path"]).exists()
    assert not (tmp_path / "data/raw/acquisition/auslamp-nsw-c15.json").exists()


def test_zero_variance_is_rejected_before_scoring(tmp_path):
    text = FIXTURE.read_text(encoding="utf-8")
    malformed = tmp_path / "zero-variance.edi"
    malformed.write_text(_change_first_value(text, "ZXX.VAR", "0"), encoding="utf-8")
    with pytest.raises(MTFieldQCError, match="strictly positive"):
        inspect_edi(malformed)


def test_misaligned_dipole_frame_is_rejected(tmp_path):
    text = FIXTURE.read_text(encoding="utf-8")
    malformed = tmp_path / "misaligned-ey.edi"
    malformed.write_text(
        text.replace("CHTYPE=EY X=0 Y=0 X2=0 Y2=100", "CHTYPE=EY X=0 Y=0 X2=100 Y2=0"),
        encoding="utf-8",
    )
    with pytest.raises(MTFieldQCError, match="orthogonal"):
        inspect_edi(malformed)


def test_last_period_violation_is_not_dropped_from_the_1d_gate():
    frequency = np.geomspace(0.01, 100, 24)
    amplitude = (1 + 1j) * np.sqrt(frequency)
    tensor = np.zeros((len(frequency), 2, 2), dtype=complex)
    tensor[:, 0, 1], tensor[:, 1, 0] = amplitude, -amplitude
    variance = np.broadcast_to((0.02 * abs(amplitude))[:, None, None] ** 2, tensor.shape).copy()
    tensor[-1, 0, 0] = 2 * amplitude[-1]
    result = tensor_gate(tensor, variance)
    assert result["all_supplied_periods_used"] is True
    assert len(result["per_period_normalized"]["xx"]) == 24
    assert result["per_period_normalized"]["xx"][-1] > result["threshold"]
    assert result["passes"] is False


def test_failed_tensor_gate_cannot_publish_an_inverse(tmp_path, monkeypatch):
    source = load_ledger()["auslamp-nsw-c15"]
    acquired = {"schema": "test-receipt", "source_id": source["source_id"]}
    inspected = inspect_edi(FIXTURE)
    inspected.update(id="C15", source_sha256=source["sha256"], unresolved_for_absolute_inverse=[])
    inspected["tensor_1d"]["passes"] = False
    monkeypatch.setattr(mt_field_qc, "acquire_source", lambda *args, **kwargs: (source, FIXTURE, acquired))
    monkeypatch.setattr(mt_field_qc, "inspect_edi", lambda _: inspected)
    monkeypatch.setattr(mt_field_qc, "_provider_screen", lambda *args: {"not_an_inverse_admission": True})

    result = mt_field_qc.run(root=tmp_path)
    assert result["status"] == "ineligible"
    assert result["inversion_performed"] is False
    assert result["methods"] == {}
    assert result["predicted"] is None and result["heldout_metrics"] is None and result["truth"] is None
    receipt = tmp_path / "data/raw/mt/auslamp-nsw-c15-m06-admission.json"
    payload = receipt.read_bytes()
    sidecar = receipt.with_suffix(receipt.suffix + ".sha256").read_text(encoding="ascii")
    assert sidecar.startswith(hashlib.sha256(payload).hexdigest() + "  ")


def test_unreviewed_station_cannot_enter_the_m06_inverse_lane(tmp_path):
    with pytest.raises(SourceError, match="Unknown source_id"):
        acquire_source("unreviewed-mt-station", local_file=FIXTURE, root=tmp_path, ledger_path=LEDGER)
    assert not (tmp_path / "data").exists()
