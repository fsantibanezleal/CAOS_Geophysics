"""Closed guardian controls; authored packets are not native containment proof."""
import sys
import json
import os
import re
from pathlib import Path
import select
import signal
import time

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from waveform_m08_guardian import guardian_names, completion_frame


def test_constructor_names_are_one_owned_run_not_arbitrary_units():
    assert guardian_names("a" * 32) == ("m08-" + "a" * 32 + ".service",
        "m08" + "a" * 32 + ".slice", "m08guard-" + "a" * 32 + ".scope")
    for bad in ("", "../other", "A" * 32, "a" * 31, True, 123):
        with pytest.raises(ValueError):
            guardian_names(bad)


def test_fragmented_completion_is_not_eof_or_implicit_success():
    assert completion_frame(b"", b"DO") == (b"DO", None)
    assert completion_frame(b"DO", b"NE\n") == (b"DONE\n", "complete")
    assert completion_frame(b"DO", b"") == (b"DO", "caller_dead")
    for bad in (b"DONE\nextra", b"COMPLETE\n", b"done\n", b"\0"):
        with pytest.raises(ValueError):
            completion_frame(b"", bad)


@pytest.mark.skipif(sys.platform != "linux" or os.environ.get("M08_RUN_LINUX_NATIVE") != "1",
    reason="Actual installed manager/guardian controls require explicit opt-in")
@pytest.mark.parametrize("checkpoint", ["before_submit", "before_ack", "paused_before_ack"])
def test_actual_parent_death_before_bootstrap_or_ack(tmp_path, checkpoint):
    """Real manager-born M08 bootstrap, no original/scientific import ACK.

    Own observer is held unreaped; actual guardian enrollment transfers UNIX_FD.
    This is a lifecycle negative, never a substitute positive calculation.
    """
    from waveform_m08_guardian import Guardian, manager
    from waveform_m08_linux import _slice, _launch, image_sha
    from waveform_m08_windows import ControlError
    from waveform_m08_files import external_work_path
    external_work_path(tmp_path)
    run = os.urandom(16).hex()
    service, accounting, scope = guardian_names(run)
    work = tmp_path / "work"
    work.mkdir()
    library = Path("/usr/lib/x86_64-linux-gnu/libsystemd.so.0").resolve(strict=True)
    library_record = dict(path=str(library), sha256=image_sha(library))
    admission = dict(uid=65534, gid=65534, python=str(Path(sys._base_executable).resolve()))
    ready_read, ready_write = os.pipe()
    observer = os.fork()
    if observer == 0:
        os.close(ready_read)
        try:
            guardian = Guardian(run, library_record)
            if checkpoint != "before_submit":
                _slice(accounting)
                _launch(admission, service, accounting, work, run, scope)
                if checkpoint == "paused_before_ack":
                    manager(["/usr/bin/systemctl", "kill", "--signal=SIGSTOP", "--kill-whom=all", service])
            os.write(ready_write, json.dumps(guardian.receipt).encode() + b"\n")
            while True:
                time.sleep(1)
        except BaseException:
            os._exit(4)
    os.close(ready_write)
    observer_fd = os.pidfd_open(observer)
    science_fd = None
    try:
        assert select.select([ready_read, observer_fd], [], [], 15)[0] == [ready_read]
        record = json.loads(os.read(ready_read, 4096))
        assert record["identity_transport"] == "PIDFDs/ah" and record["scope"] == scope
        assert record["group"] == "/system.slice/" + scope
        if checkpoint != "before_submit":
            pid = int(manager(["/usr/bin/systemctl", "show", service, "--property=MainPID", "--value"]))
            assert pid > 1
            science_fd = os.pidfd_open(pid)
            assert manager(["/usr/bin/systemctl", "show", service, "--property=MainPID", "--value"]) == str(pid)
            assert not select.select([science_fd], [], [], 0)[0]
            assert b"--science" in Path(f"/proc/{pid}/cmdline").read_bytes()
            assert scope in manager(["/usr/bin/systemctl", "show", service, "--property=BindsTo", "--value"]).split()
            assert scope in manager(["/usr/bin/systemctl", "show", service, "--property=After", "--value"]).split()
            if checkpoint == "paused_before_ack":
                assert re.search(r"^State:\s+T", Path(f"/proc/{pid}/status").read_text(), re.M)
        before = time.monotonic_ns()
        signal.pidfd_send_signal(observer_fd, signal.SIGKILL)
        assert select.select([observer_fd], [], [], 2)[0]
        os.waitpid(observer, 0)
        observer = None
        if checkpoint == "before_submit":
            # The client submits after the original observer is already dead.
            # No held original/ACK exists; guardian must stop this late child.
            _slice(accounting)
            try:
                _launch(admission, service, accounting, work, run, scope)
            except ControlError as error:
                assert error.reason == "native_unavailable"
                pass
        deadline = before + 2000000000
        group = Path("/sys/fs/cgroup") / accounting
        while group.exists() and b"populated 1" in (group / "cgroup.events").read_bytes().splitlines():
            assert time.monotonic_ns() <= deadline
            time.sleep(.01)
        quiescent = time.monotonic_ns()
        assert quiescent - before <= 2000000000
        if science_fd is not None:
            assert select.select([science_fd], [], [], 0)[0]
        guardian_deadline = time.monotonic() + 22
        guard_group = Path("/sys/fs/cgroup/system.slice") / scope
        while guard_group.exists():
            assert time.monotonic() < guardian_deadline
            time.sleep(.05)
        assert not group.exists() and not (work / "final").exists()
        (tmp_path / "actual-guard.json").write_text(json.dumps(dict(run_id=run, checkpoint=checkpoint,
            observer_pidfd_held_before_death=True, scope_transport=record, quiescence_ns=quiescent-before,
            science_scope_removed=True, guardian_scope_removed=True, scientific_ack=False)))
    finally:
        if observer is not None:
            signal.pidfd_send_signal(observer_fd, signal.SIGKILL)
            os.waitpid(observer, 0)
        os.close(observer_fd)
        if science_fd is not None:
            os.close(science_fd)
        os.close(ready_read)
