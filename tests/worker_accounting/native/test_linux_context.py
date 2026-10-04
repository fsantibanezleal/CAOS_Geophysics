"""Test-first bounded launch bytes; these do not execute Linux operations."""
import importlib.util
from pathlib import Path
import struct

import pytest

ROOT = Path(__file__).resolve().parents[3]


def module():
    spec = importlib.util.spec_from_file_location(
        "linux_context", ROOT / "scripts/prepare_linux_cpu_context.py")
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def valid():
    return dict(budget_class=1, uid=61001, gid=61001,
                attempt="01" * 16, object_id="02" * 16,
                executable="/usr/bin/python3.12", argv0="/owned/venv/bin/python",
                cwd="/owned/work", arguments=["-I", "script.py"],
                environment=["OMP_NUM_THREADS=1", "LANG=C.UTF-8"])


def test_exact_header_native_payload_and_roundtrip():
    m = module()
    value = valid()
    raw = m.encode_context(**value)
    assert type(raw) is bytes and raw[:4] == b"LCX1"
    assert struct.unpack_from("<HHIIIIII", raw, 4) == (
        1, 1, 61001, 61001, 2, 2, len(raw) - 64, 0)
    assert raw[32:48] == bytes.fromhex(value["attempt"])
    assert raw[48:64] == bytes.fromhex(value["object_id"])
    assert m.decode_context(raw) == value


@pytest.mark.parametrize("field,bad", [
    ("budget_class", True), ("budget_class", 3), ("uid", 0),
    ("uid", 1.0), ("gid", -1), ("uid", 2**32), ("uid", 2**32 - 1), ("gid", 2**32 - 1),
    ("attempt", "00" * 16), ("attempt", "AA" * 16),
    ("object_id", "z" * 32), ("executable", "relative"),
    ("executable", "/usr/../bin/python"), ("cwd", "/a//b"),
    ("argv0", "/a\x00b"), ("arguments", []),
    ("arguments", ["x"] * 33), ("arguments", ["x" * 1025]),
    ("arguments", ["x" * 1024] * 17), ("arguments", [False]),
    ("environment", ["A=x", "A=y"]), ("environment", ["=x"]),
    ("environment", ["A=x\x00y"]), ("environment", ["A=\ud800"]),
    ("environment", ["LD_PRELOAD=/tmp/evil"]),
    ("environment", ["PYTHONPATH=/tmp/evil"]),
    ("environment", ["TOKEN=private"]),
])
def test_caps_before_copy(field, bad):
    m = module()
    value = valid()
    value[field] = bad
    with pytest.raises(m.ContextError) as raised:
        m.encode_context(**value)
    assert str(raised.value) == "linux_context_invalid"
    assert raised.value.__cause__ is None
    assert raised.value.__context__ is None


@pytest.mark.parametrize("mutation", [
    lambda b: b + b"x", lambda b: b[:63],
    lambda b: b"bad!" + b[4:],
    lambda b: b[:28] + b"\x01\x00\x00\x00" + b[32:],
    lambda b: b[:64] + b"\xff\xff\xff\xff" + b[68:],
    lambda b: b[:68] + b"\xff" + b[69:],
])
def test_raw_context_rejects_before_native_launch(mutation):
    m = module()
    with pytest.raises(m.ContextError):
        m.decode_context(mutation(m.encode_context(**valid())))


def test_exact_bytes_only_and_maximum_before_scan():
    m = module()
    for bad in (bytearray(64), "LCX1", b"x" * 32769):
        with pytest.raises(m.ContextError):
            m.decode_context(bad)


def test_utf8_byte_limit_not_unicode_length():
    m = module()
    value = valid()
    value["arguments"] = ["\U0001d11e" * 256]
    assert m.decode_context(m.encode_context(**value)) == value
    value["arguments"] = ["\U0001d11e" * 257]
    with pytest.raises(m.ContextError):
        m.encode_context(**value)


def test_system_manager_recipe_is_attempt_specific_and_not_activation():
    m = module()
    command = m.unit_arguments("/usr/bin/systemd-run", "/owned/controller",
                               "/owned/context", "01" * 16,
                               "geophysics-cpu-parent-" + "01" * 16 + ".service", 1)
    assert command[0] == "/usr/bin/systemd-run"
    assert "--unit=geophysics-cpu-qual-" + "01" * 16 + ".service" in command
    assert "--property=Delegate=cpu memory pids" in command
    assert "--property=DelegateSubgroup=observer" in command
    assert "--property=KillMode=control-group" in command
    assert "--property=CapabilityBoundingSet=CAP_SETUID CAP_SETGID CAP_SETPCAP" in command
    # v255 blocks clone3 under RestrictNamespaces, before native birth. Science
    # receives its own post-birth filter instead; preserve the actual syscall.
    assert not any("RestrictNamespaces" in item for item in command)
    assert "--property=BindsTo=geophysics-cpu-parent-" + "01" * 16 + ".service" in command
    assert "--user" not in command and "--scope" not in command
    assert "--collect" not in command
    assert command[-2:] == ["/owned/controller", "/owned/context"]
