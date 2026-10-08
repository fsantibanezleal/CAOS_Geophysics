"""Authored client classification contracts, never installed/native queue proof."""
from copy import deepcopy
import sys

import pytest

from app.errors import ApiError
from app.waveform_linux_worker import _capture, failure_code


@pytest.mark.parametrize("reason",["user_cancelled","account_quota_exceeded","waveform_storage_unavailable"])
def test_proved_measured_publication_failure_retains_exact_typed_reason(reason):
    terminal = {"outcome":{"reason":"measured"},"lifecycle":{"caller":{"reason":None}}}
    assert failure_code(ApiError(409,reason,"authored"),None,terminal,True) == reason
    assert failure_code(ApiError(409,reason,"authored"),None,terminal,False) == "waveform_execution_unproved"


def test_cancel_needs_proved_matching_terminal_not_requested_flag_alone():
    terminal = {"outcome":{"reason":"cancelled"},"lifecycle":{"caller":{"reason":"cancelled"}}}
    assert failure_code(ValueError(),"user_cancelled",terminal,True) == "user_cancelled"
    assert failure_code(ValueError(),"user_cancelled",terminal,False) == "waveform_execution_unproved"
    other = deepcopy(terminal)
    other["lifecycle"]["caller"]["reason"] = "caller_lost"
    assert failure_code(ValueError(),"user_cancelled",other,True) == "waveform_execution_unproved"


def test_proved_scientific_failure_is_not_good_rss_success_or_unknown_cancel():
    terminal = {"outcome":{"reason":"engine_unavailable"},"lifecycle":{"caller":{"reason":None}}}
    assert failure_code(ApiError(409,"waveform_processing_failed","authored"),None,terminal,True) == "waveform_processing_failed"


def test_full_source_map_and_no_linux_generic_observer_command():
    from app.waveform_contract import IMPLEMENTATION_FILES
    from scripts.waveform_m08_installation import SOURCE_FILES
    from app.waveform_worker import command
    assert IMPLEMENTATION_FILES == SOURCE_FILES and len(set(SOURCE_FILES)) == 23
    with pytest.raises(ApiError):
        command({"platform":"linux","python":"/usr/bin/python3"},{})


def test_linux_absent_fixed_installation_refuses_without_legacy_context(monkeypatch):
    from app.waveform_contract import context_available
    import app.waveform_linux_worker as client
    monkeypatch.setattr(sys,"platform","linux")
    def absent(_):
        raise OSError("authored absent installation")
    monkeypatch.setattr(client,"installed_snapshot",absent)
    assert context_available(object()) is False


def test_bounded_terminal_capture_exact_canonical_first_frame_and_cleanup_suffix():
    import asyncio
    from scripts.waveform_m08_installation import canonical
    async def run():
        first = asyncio.get_running_loop().create_future()
        stream = asyncio.StreamReader()
        stream.feed_data(canonical({"authored":"frame control only"})+b"\nCLEAN\n")
        stream.feed_eof()
        body = await _capture(stream,65544,first)
        assert first.result() == {"authored":"frame control only"}
        assert body.endswith(b"\nCLEAN\n")
    asyncio.run(run())


@pytest.mark.parametrize("raw",[b'{"a":1, "b":2}\n',b'{"a":1,"a":2}\n',b'x'*65545],
                         ids=["noncanonical","duplicate-key","over-cap"])
def test_invalid_or_excess_terminal_capture_refuses(raw):
    import asyncio
    async def run():
        first = asyncio.get_running_loop().create_future()
        stream = asyncio.StreamReader()
        stream.feed_data(raw)
        stream.feed_eof()
        with pytest.raises(ValueError):
            await _capture(stream,65544,first)
        assert first.done() and isinstance(first.exception(),ValueError)
    asyncio.run(run())
