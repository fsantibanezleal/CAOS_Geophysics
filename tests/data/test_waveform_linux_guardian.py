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


@pytest.mark.skipif(sys.platform != "linux", reason="anonymous Linux caller descriptor contract")
def test_caller_guard_accepts_only_held_anonymous_pipe_read_end(tmp_path):
    from waveform_m08_guardian import caller_pipe
    import socket
    reader,writer = os.pipe()
    try:
        caller_pipe(reader)
        with pytest.raises(ValueError):
            caller_pipe(writer)
        with open(tmp_path/"regular","xb") as regular:
            with pytest.raises(ValueError):
                caller_pipe(regular.fileno())
        with socket.socket(socket.AF_UNIX) as sock:
            with pytest.raises(ValueError):
                caller_pipe(sock.fileno())
        fifo = tmp_path/"named-fifo"
        os.mkfifo(fifo)
        fd = os.open(fifo,os.O_RDONLY|os.O_NONBLOCK)
        try:
            with pytest.raises(ValueError):
                caller_pipe(fd)
        finally:
            os.close(fd)
    finally:
        os.close(reader)
        os.close(writer)


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
    # Own fresh POSIX qualification ancestry must permit the science UID's
    # CHDIR. No original/plan custody exists in these lifecycle negatives.
    tmp_path.chmod(0o755)
    tmp_path.parent.chmod(0o755)
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

@pytest.mark.skipif(sys.platform != "linux" or os.environ.get("M08_RUN_LINUX_NATIVE") != "1",
                    reason="actual independent manager guardian / paused observer control")
@pytest.mark.parametrize("control",["eof","pending_cancel"])
def test_actual_worker_pipe_loss_drains_even_with_root_observer_paused(tmp_path,control):
    from waveform_m08_guardian import Guardian,manager
    from waveform_m08_linux import _slice,_launch,image_sha
    tmp_path.chmod(0o755)
    tmp_path.parent.chmod(0o755)
    run = os.urandom(16).hex()
    service,accounting,scope = guardian_names(run)
    work = tmp_path/"work"
    work.mkdir()
    library = Path("/usr/lib/x86_64-linux-gnu/libsystemd.so.0").resolve(strict=True)
    library_record = dict(path=str(library),sha256=image_sha(library))
    admission = dict(uid=65534,gid=65534,python=str(Path(sys._base_executable).resolve()))
    caller,writer = os.pipe()
    ready,notify = os.pipe()
    observer = os.fork()
    if observer == 0:
        os.close(writer)
        os.close(ready)
        try:
            guardian = Guardian(run,library_record,caller_fd=caller)
            _slice(accounting)
            _launch(admission,service,accounting,work,run,scope)
            manager(["/usr/bin/systemctl","kill","--signal=SIGSTOP","--kill-whom=all",service])
            os.write(notify,json.dumps(guardian.receipt).encode()+b"\n")
            while True:
                time.sleep(1)
        except BaseException:
            os._exit(4)
    os.close(caller)
    os.close(notify)
    observer_fd = os.pidfd_open(observer)
    science_fd = None
    try:
        assert select.select([ready,observer_fd],[],[],15)[0] == [ready]
        receipt = json.loads(os.read(ready,4096))
        assert receipt["identity_transport"] == "PIDFDs/ah"
        pid = int(manager(["/usr/bin/systemctl","show",service,"--property=MainPID","--value"]))
        science_fd = os.pidfd_open(pid)
        assert not select.select([science_fd],[],[],0)[0]
        assert re.search(r"^State:\s+T",Path(f"/proc/{pid}/status").read_text(),re.M)
        signal.pidfd_send_signal(observer_fd,signal.SIGSTOP)
        deadline = time.monotonic()+2
        while not re.search(r"^State:\s+T",Path(f"/proc/{observer}/status").read_text(),re.M):
            assert time.monotonic() < deadline
            time.sleep(.005)
        began = time.monotonic_ns()
        if control == "eof":
            os.close(writer)
            writer = None
        else:
            assert os.write(writer,b"CANCEL\n") == 7
        group = Path("/sys/fs/cgroup")/accounting
        deadline = began+2000000000
        while group.exists() and b"populated 1" in (group/"cgroup.events").read_bytes().splitlines():
            assert time.monotonic_ns() <= deadline
            time.sleep(.005)
        quiescent = time.monotonic_ns()
        assert quiescent-began <= 2000000000 and select.select([science_fd],[],[],0)[0]
        # The observer is STILL stopped/alive: it could not parse or kill science.
        assert not select.select([observer_fd],[],[],0)[0]
        assert re.search(r"^State:\s+T",Path(f"/proc/{observer}/status").read_text(),re.M)
        guard_group = Path("/sys/fs/cgroup/system.slice")/scope
        deadline = time.monotonic()+22
        while guard_group.exists():
            assert time.monotonic() < deadline
            time.sleep(.05)
        assert not group.exists() and not (work/"final").exists()
        (tmp_path/"actual-caller-guard.json").write_text(json.dumps(dict(run_id=run,control=control,
            held_anonymous_pipe=True,observer_stopped=True,observer_alive_at_quiescence=True,
            guardian=receipt,quiescence_ns=quiescent-began,science_scope_removed=True,
            guardian_scope_removed=True,scientific_ack=False,production_api_proved=False)))
    finally:
        if writer is not None:
            os.close(writer)
        signal.pidfd_send_signal(observer_fd,signal.SIGKILL)
        os.waitpid(observer,0)
        os.close(observer_fd)
        if science_fd is not None:
            os.close(science_fd)
        os.close(ready)
