"""Closed caller-control frames; these packets are not native extinction proof."""
import importlib.util
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts"))


def module():
    spec = importlib.util.spec_from_file_location("_m08_native_control_test",ROOT/"scripts/waveform_m08_linux.py")
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def test_fragmented_cancel_is_bounded_and_eof_never_becomes_commit_or_success():
    value = module()
    assert value.caller_frame(b"",b"CAN") == (b"CAN",None)
    assert value.caller_frame(b"CAN",b"CEL\n") == (b"CANCEL\n","cancelled")
    assert value.caller_frame(b"",b"") == (b"","caller_lost")
    assert value.caller_frame(b"CAN",b"") == (b"CAN","caller_lost")
    for part in (b"CANCEL\nextra",b"COMMIT\n",b"cancel\n",b"\0",b"\n"):
        with pytest.raises(value.ControlError):
            value.caller_frame(b"",part)


def test_partial_control_is_not_a_truthy_implied_cancellation():
    value = module()
    for prefix in (b"C",b"CA",b"CAN",b"CANC",b"CANCE",b"CANCEL"):
        assert value.caller_frame(b"",prefix) == (prefix,None)
    with pytest.raises(value.ControlError):
        value.caller_frame(b"CANCEL",b"\n\n")
