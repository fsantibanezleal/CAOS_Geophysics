"""Genuine science/API/ZIP with authored root receipt; NOT installed queue proof."""
import sys

import pytest

from tests.api.test_waveform_service import _publication_roundtrip


@pytest.mark.skipif(sys.platform != "linux",reason="actual POSIX held publication")
def test_genuine_science_held_adoption_api_zip_reconcile_delete(harness,tmp_path,monkeypatch):
    _publication_roundtrip(harness,tmp_path,monkeypatch,held_linux=True)
