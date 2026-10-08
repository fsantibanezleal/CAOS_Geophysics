"""Fixed root guardian identity transport. No science, database or public IPC.

Uses the reviewed systemd255 PIDFDs/ah enrollment, not numeric PID adoption.
Only installation/qualification callers with existing manager authority may use
this helper. It does not authorize a production root API/worker.
"""
from __future__ import annotations

import ctypes as c
import hashlib
import os
from pathlib import Path
import re
import select
import signal
import stat
import subprocess
import time


def require(value):
    if not value:
        raise ValueError("waveform_guardian_unresolved")


def guardian_names(run):
    require(type(run) is str and re.fullmatch("[a-f0-9]{32}", run))
    return "m08-" + run + ".service", "m08" + run + ".slice", "m08guard-" + run + ".scope"


def completion_frame(buffer, part):
    require(type(buffer) is bytes and type(part) is bytes)
    if not part:
        return buffer, "caller_dead"
    buffer += part
    require(len(buffer) <= 5 and b"DONE\n".startswith(buffer))
    return buffer, "complete" if buffer == b"DONE\n" else None


def root_library(path, digest):
    path = Path(path)
    require(path.is_absolute() and str(path).startswith("/usr/lib/") and
            path.name.startswith("libsystemd.so.") and type(digest) is str and
            re.fullmatch("[a-f0-9]{64}", digest))
    for member in (path, *path.parents):
        info = member.lstat()
        require(info.st_uid == 0 and not info.st_mode & 0o022 and not stat.S_ISLNK(info.st_mode))
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= 8 * 1024**2)
        value, size = hashlib.sha256(), 0
        while block := os.read(fd, 65536):
            size += len(block)
            require(size <= before.st_size)
            value.update(block)
        after = os.fstat(fd)
        require(size == before.st_size and value.hexdigest() == digest and
                (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns))
    finally:
        os.close(fd)
    return str(path)


def manager(arguments):
    reply = subprocess.run(arguments, stdin=subprocess.DEVNULL, capture_output=True,
        timeout=3, env={"PATH": "/usr/bin:/bin", "LC_ALL": "C", "SYSTEMD_PAGER": "cat"})
    require(reply.returncode == 0 and len(reply.stdout) <= 4096 and len(reply.stderr) <= 4096)
    return reply.stdout.decode("ascii", "strict").strip()


def scope_transport(scope, pidfd, library):
    require(type(scope) is str and re.fullmatch(r"m08guard-[a-f0-9]{32}\.scope", scope) and
            type(pidfd) is int and pidfd >= 3 and type(library) is dict and
            set(library) == {"path", "sha256"})
    native = c.CDLL(root_library(library["path"], library["sha256"]))
    pointer = c.c_void_p
    signatures = {
        "sd_bus_open_system": ([c.POINTER(pointer)], c.c_int),
        "sd_bus_message_new_method_call": ([pointer, c.POINTER(pointer), c.c_char_p, c.c_char_p, c.c_char_p, c.c_char_p], c.c_int),
        "sd_bus_message_append_basic": ([pointer, c.c_char, pointer], c.c_int),
        "sd_bus_message_open_container": ([pointer, c.c_char, c.c_char_p], c.c_int),
        "sd_bus_message_close_container": ([pointer], c.c_int),
        "sd_bus_call": ([pointer, pointer, c.c_uint64, pointer, c.POINTER(pointer)], c.c_int),
        "sd_bus_message_read_basic": ([pointer, c.c_char, pointer], c.c_int),
        "sd_bus_message_unref": ([pointer], pointer), "sd_bus_close": ([pointer], None),
        "sd_bus_unref": ([pointer], pointer),
    }
    for name, (arguments, result) in signatures.items():
        function = getattr(native, name)
        function.argtypes, function.restype = arguments, result
    bus, message, reply = pointer(), pointer(), pointer()

    def checked(name, *arguments):
        result = getattr(native, name)(*arguments)
        require(result >= 0)
        return result

    def basic(kind, value):
        if kind == b"s":
            item = c.c_char_p(value.encode("ascii"))
            address = c.cast(item, pointer)
        else:
            item = c.c_int(value) if kind == b"h" else c.c_uint64(value)
            address = c.cast(c.byref(item), pointer)
        checked("sd_bus_message_append_basic", message, kind, address)

    def opened(kind, signature):
        checked("sd_bus_message_open_container", message, kind, signature)

    def closed():
        checked("sd_bus_message_close_container", message)

    try:
        checked("sd_bus_open_system", c.byref(bus))
        checked("sd_bus_message_new_method_call", bus, c.byref(message), b"org.freedesktop.systemd1",
            b"/org/freedesktop/systemd1", b"org.freedesktop.systemd1.Manager", b"StartTransientUnit")
        basic(b"s", scope)
        basic(b"s", "fail")
        opened(b"a", b"(sv)")
        for name, kind, value in (("PIDFDs", b"ah", pidfd), ("MemoryMax", b"t", 128*1024**2),
                ("TasksMax", b"t", 16), ("RuntimeMaxUSec", b"t", 150000000), ("Slice", b"s", "system.slice")):
            opened(b"r", b"sv")
            basic(b"s", name)
            opened(b"v", kind)
            if kind == b"ah":
                opened(b"a", b"h")
                basic(b"h", value)
                closed()
            else:
                basic(kind, value)
            closed()
            closed()
        closed()
        opened(b"a", b"(sa(sv))")
        closed()
        checked("sd_bus_call", bus, message, 5000000, None, c.byref(reply))
        result = c.c_char_p()
        require(checked("sd_bus_message_read_basic", reply, b"o", c.byref(result)) > 0 and
                result.value is not None and re.fullmatch(rb"/org/freedesktop/systemd1/job/[0-9]{1,20}", result.value))
        return result.value.decode("ascii")
    finally:
        for value in (reply, message):
            if value:
                native.sd_bus_message_unref(value)
        if bus:
            native.sd_bus_close(bus)
            native.sd_bus_unref(bus)


def drain(run):
    service, accounting, _scope = guardian_names(run)
    for unit in (service, accounting):
        state = subprocess.run(["/usr/bin/systemctl", "show", unit, "--property=LoadState", "--value"],
            capture_output=True, timeout=3)
        require(len(state.stdout) <= 256 and state.stdout.strip() in (b"loaded", b"not-found"))
        if state.stdout.strip() == b"loaded":
            manager(["/usr/bin/systemctl", "stop", unit])
    # Manager MainPID zero alone is insufficient. Observe exact constructor-owned
    # cgroups independently, never a caller-provided path or a numeric root PID.
    deadline = time.monotonic() + 2
    group = Path("/sys/fs/cgroup") / accounting
    while group.exists():
        require(not group.is_symlink())
        try:
            require((group / "cgroup.events").read_bytes().splitlines().count(b"populated 0") == 1)
        except FileNotFoundError:
            require(not group.exists())
        require(time.monotonic() < deadline)
        time.sleep(.01)


def _child(run, parent_fd, control, ready):
    for name in os.listdir("/proc/self/fd"):
        fd = int(name)
        if fd not in (parent_fd, control, ready):
            try:
                os.close(fd)
            except OSError:
                pass
    normal = False
    try:
        os.write(ready, b"READY\n")
        os.close(ready)
        buffer = b""
        while True:
            readable, _, _ = select.select([parent_fd, control], [], [], 1)
            if parent_fd in readable:
                break
            if control in readable:
                buffer, outcome = completion_frame(buffer, os.read(control, 1024))
                if outcome:
                    normal = outcome == "complete"
                    break
        if normal:
            drain(run)
            os._exit(0)
    except BaseException:
        normal = False
    # Cover interrupted and late manager acceptance as well as a live child.
    # Science is independently BindsTo/After this exact scope. Its later exit
    # also prevents a deferred submission from becoming scientific execution.
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        try:
            drain(run)
        except BaseException:
            pass
        time.sleep(.05)
    os._exit(2)


class Guardian:
    """Held pre-fork parent identity and own unreaped guardian, outside caller."""
    def __init__(self, run, library):
        require(os.geteuid() == 0)
        self.run, self.pid, self.pidfd, self.control = run, None, None, None
        _service, _accounting, self.scope = guardian_names(run)
        descriptors = {}
        try:
            # Capture our live kernel identity BEFORE fork and manager submission.
            descriptors["parent"] = os.pidfd_open(os.getpid())
            descriptors["read"], descriptors["write"] = os.pipe()
            descriptors["ready"], descriptors["notify"] = os.pipe()
            self.pid = os.fork()
            if self.pid == 0:
                try:
                    _child(run, descriptors["parent"], descriptors["read"], descriptors["notify"])
                finally:
                    os._exit(2)
            for name in ("parent", "read", "notify"):
                os.close(descriptors.pop(name))
            descriptors["child"] = os.pidfd_open(self.pid)  # Own child remains unreaped.
            readable, _, _ = select.select([descriptors["ready"], descriptors["child"]], [], [], 3)
            require(descriptors["ready"] in readable and descriptors["child"] not in readable and
                    os.read(descriptors["ready"], 7) == b"READY\n")
            require(manager(["/usr/bin/systemctl", "show", self.scope, "--property=LoadState", "--value"]) == "not-found")
            job = scope_transport(self.scope, descriptors["child"], library)
            deadline = time.monotonic() + 3
            while True:
                self.check(descriptors["child"])
                group = "/system.slice/" + self.scope
                if manager(["/usr/bin/systemctl", "show", self.scope, "--property=ActiveState", "--value"]) == "active" and Path(f"/proc/{self.pid}/cgroup").read_text() == "0::" + group + "\n":
                    require(manager(["/usr/bin/systemctl", "show", self.scope, "--property=ControlGroup", "--value"]) == group)
                    require(manager(["/usr/bin/systemctl", "show", self.scope, "--property=MemoryMax", "--value"]) == str(128*1024**2))
                    require(manager(["/usr/bin/systemctl", "show", self.scope, "--property=TasksMax", "--value"]) == "16")
                    object_path = "/org/freedesktop/systemd1/unit/" + "".join(
                        letter if letter.isalnum() else "_" + format(ord(letter), "02x") for letter in self.scope)
                    require(manager(["/usr/bin/busctl", "--timeout=3s", "get-property", "org.freedesktop.systemd1",
                        object_path, "org.freedesktop.systemd1.Scope", "RuntimeMaxUSec"]) == "t 150000000")
                    break
                require(time.monotonic() < deadline)
                time.sleep(.02)
            self.receipt = dict(scope=self.scope, group=group, identity_transport="PIDFDs/ah",
                memory_limit_bytes=128*1024**2, tasks_max=16, wall_limit_seconds=150, manager_job=job)
            self.pidfd, self.control = descriptors.pop("child"), descriptors.pop("write")
        except BaseException:
            if self.pid is not None and self.pid > 0:
                if "child" in descriptors:
                    try:
                        signal.pidfd_send_signal(descriptors["child"], signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                else:
                    os.kill(self.pid, signal.SIGKILL)  # Own unreaped fork, never adopted PID.
                os.waitpid(self.pid, 0)
                self.pid = None
            raise
        finally:
            for fd in descriptors.values():
                os.close(fd)

    def check(self, fd=None):
        require(not select.select([self.pidfd if fd is None else fd], [], [], 0)[0])

    def close(self, complete):
        require(type(complete) is bool)
        if self.control is not None:
            try:
                if complete:
                    os.write(self.control, b"DONE\n")
            finally:
                os.close(self.control)
                self.control = None
        try:
            require(select.select([self.pidfd], [], [], 20)[0])
            _pid, status = os.waitpid(self.pid, 0)
            self.pid = None
            if complete:
                require(os.waitstatus_to_exitcode(status) == 0)
            # Exact independent guardian scope must be inactive or absent after
            # its held child dies. Never claim success from a lost manager read.
            state = subprocess.run(["/usr/bin/systemctl", "show", self.scope,
                "--property=ActiveState", "--value"], capture_output=True, timeout=3)
            require(len(state.stdout) <= 256 and state.stdout.strip() == b"inactive")
            require(not (Path("/sys/fs/cgroup/system.slice") / self.scope).exists())
        finally:
            if self.pidfd is not None:
                os.close(self.pidfd)
                self.pidfd = None
