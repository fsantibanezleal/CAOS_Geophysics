"""Fixed manager-born M08 Linux lane; no scientific fallback or request hooks."""
from __future__ import annotations

import array
from contextlib import ExitStack
import ctypes
import hashlib
import os
from pathlib import Path
import re
import select
import socket
import stat
import struct
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data-pipeline"))
sys.path.insert(0, str(ROOT / "scripts"))
from waveform_input import WaveformInputError, sha
from waveform_m08_files import external_work_path, validate_path, open_input, open_output, create_output, OwnedDirectory, _info
from waveform_m08_windows import B, S, POLL, GAP, MEMORY, SCRATCH, ControlError, require, integer, canonical, terminal, prepare_engine, decode_control
from waveform_m08_windows import exit_status as exit_status

ADMISSION = "caos.m08-linux-admission.v1"
RESOURCE = "caos.m08-linux-resources.v1"
RELEASE = "caos.m08-linux-release.v1"
CODE_FILES = (
    "scripts/waveform_m08_linux.py", "scripts/waveform_m08_windows.py",
    "scripts/waveform_m08_files.py", "scripts/waveform_m08_export.py",
    "scripts/waveform_m08_child.py", "scripts/process_waveform_m08.py",
    "data-pipeline/waveform_input.py", "data-pipeline/waveform_processing.py",
    "data-pipeline/waveform_evaluation.py", "app/waveform_contract.py",
    "app/waveform_processing.py", "app/waveform_result.py", "app/waveform_worker.py",
    "app/waveform_linux_exec.py", "scripts/qualify_waveform_m08_linux.py",
)
TOOLS = {"run": "/usr/bin/systemd-run", "ctl": "/usr/bin/systemctl", "bus": "/usr/bin/busctl"}


def image_sha(path):
    """Pinned code/runtime images may be hardlinks; originals never may."""
    path = validate_path(str(path))
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= 1073741824, "closure_mismatch")
        value, used = hashlib.sha256(), 0
        while block := os.read(fd, 65536):
            used += len(block)
            require(used <= before.st_size, "closure_mismatch")
            value.update(block)
        after = os.fstat(fd)
        require(used == before.st_size and (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), "closure_mismatch")
        return value.hexdigest()
    finally:
        os.close(fd)


def parse_cpu(raw):
    require(type(raw) is bytes and 0 < len(raw) <= 4096, "counter_invalid")
    result = {}
    for line in raw.splitlines():
        parts = line.split()
        require(len(parts) == 2 and re.fullmatch(rb"[a-z_]+", parts[0]) and
                re.fullmatch(rb"[0-9]{1,20}", parts[1]) and parts[0] not in result, "counter_invalid")
        result[parts[0]] = int(parts[1])
    require({b"usage_usec", b"user_usec", b"system_usec"} <= set(result), "counter_invalid")
    values = tuple(integer(result[k], (2**63 - 1) // 1000) * 1000 for k in (b"usage_usec", b"user_usec", b"system_usec"))
    # Kernel independently rounds these counters. Do not manufacture equality.
    require(values[1] <= values[0] and values[2] <= values[0], "counter_invalid")
    return values


class LinuxLifetime:
    def __init__(self):
        self.last = self.started = self.drain = self.stable = None
        self.samples = self.max_gap_ns = 0
        self.final_cpu_ns = None
        self.final_ready = False
        self.failure = None

    def drained(self, stamp):
        integer(stamp)
        require(self.drain is None and self.last is not None and
                self.started <= stamp <= self.last[0] + GAP, "drain_invalid")
        self.drain = stamp

    def sample(self, stamp, usage, user, system, tasks, peak):
        try:
            row = tuple(integer(v) for v in (stamp, usage, user, system, tasks, peak))
            require(tasks <= 2 and peak <= MEMORY, "resource_exceeded")
            if self.last is not None:
                require(stamp >= self.last[0] and all(row[k] >= self.last[k] for k in (1, 2, 3, 5)), "counter_invalid")
                self.max_gap_ns = max(self.max_gap_ns, stamp - self.last[0])
                require(self.max_gap_ns <= GAP, "sample_gap")
                if self.stable is not None:
                    require(row[1:] == self.stable[1:], "drain_invalid")
            require(usage <= B, "resource_exceeded")
            require(usage < S, "resource_stop")
            if self.started is None:
                self.started = stamp
            if self.drain is not None and stamp >= self.drain + POLL and tasks == 0:
                if self.stable is None:
                    self.stable = row
                elif stamp >= self.stable[0] + POLL and self.failure is None:
                    self.final_ready, self.final_cpu_ns = True, usage
            self.last = row
            self.samples += 1
        except ControlError as error:
            if self.failure is None or error.reason == "resource_exceeded":
                self.failure = error.reason
            self.final_ready = False


def packet(run, sequence, phase, payload):
    require(type(run) is str and re.fullmatch("[a-f0-9]{32}", run) and type(sequence) is int and
            1 <= sequence <= 2 and phase in {"hello", "ack", "drained", "error"} and type(payload) is dict, "wire_invalid")
    return canonical({"schema": "caos.m08-linux-wire.v1", "run_id": run,
                      "sequence": sequence, "phase": phase, "payload": payload})


def read_packet(raw, run, sequence, phase):
    try:
        # Native stat/clock domains are uint64, not the scientific JSON's JS-safe
        # integer domain. Use the existing reviewed bounded native grammar.
        value = decode_control(raw)
        require(type(value) is dict and set(value) == {"schema", "run_id", "sequence", "phase", "payload"}
                and value["schema"] == "caos.m08-linux-wire.v1" and value["run_id"] == run
                and type(value["sequence"]) is int and value["sequence"] == sequence
                and value["phase"] == phase and type(value["payload"]) is dict and canonical(value) == raw, "wire_invalid")
        return value["payload"]
    except (ControlError, WaveformInputError, TypeError, ValueError):
        raise ControlError("wire_invalid") from None


def code_hashes():
    return {name: image_sha(ROOT / name) for name in CODE_FILES}


def loaded_images():
    result = {}
    with open("/proc/self/maps", "rb") as stream:
        for line in stream:
            parts = line.split(maxsplit=5)
            if len(parts) == 6 and parts[5].startswith(b"/"):
                path = parts[5].rstrip(b"\n").decode("utf-8", "strict")
                require(not path.endswith(" (deleted)") and "\\" not in path, "closure_mismatch")
                path = str(Path(path).resolve())
                if path not in result:
                    require(len(result) < 256, "closure_mismatch")
                    result[path] = image_sha(path)
    require(bool(result), "closure_mismatch")
    return result


def closure(admission):
    expected = {item["path"]: item["sha256"] for item in admission["runtime"]}
    require(all(expected.get(path) == digest for path, digest in loaded_images().items()), "closure_mismatch")


def read_admission(path, python):
    require(sys.platform == "linux", "platform_unavailable")
    with open_input(external_work_path(path), 65536) as source:
        raw = source.read_bytes()
    value = decode_control(raw)
    require(type(value) is dict and set(value) == set("schema platform source_revision observer_uid uid gid python python_sha256 site_packages parent code runtime supervisor".split()))
    require(value["schema"] == ADMISSION and value["platform"] == "linux" and
            type(value["source_revision"]) is str and re.fullmatch("[a-f0-9]{40}", value["source_revision"]))
    require(type(value["uid"]) is int and 1 <= value["uid"] < 2**32 and
            type(value["gid"]) is int and 1 <= value["gid"] < 2**32 and
            type(value["observer_uid"]) is int and value["observer_uid"] == os.geteuid())
    require(value["python"] == str(validate_path(str(python))) and image_sha(python) == value["python_sha256"], "closure_mismatch")
    require(type(value["code"]) is dict and value["code"] == code_hashes(), "closure_mismatch")
    require(type(value["supervisor"]) is dict and set(value["supervisor"]) == set(TOOLS) and
            all(value["supervisor"][role] == image_sha(path) for role, path in TOOLS.items()), "closure_mismatch")
    runtime = value["runtime"]
    require(type(runtime) is list and 1 <= len(runtime) <= 256, "closure_mismatch")
    names = []
    for row in runtime:
        require(type(row) is dict and set(row) == {"path", "sha256"}, "closure_mismatch")
        image, digest = row["path"], row["sha256"]
        require(type(digest) is str and re.fullmatch("[a-f0-9]{64}", digest)
                and image_sha(image) == digest, "closure_mismatch")
        names.append(image)
    require(names == sorted(set(names)), "closure_mismatch")
    site = validate_path(value["site_packages"])
    with open_output(site):
        pass
    parent = value["parent"]
    require(type(parent) is dict and set(parent) == {"path", "identity", "context_receipt_sha256"})
    with open_output(external_work_path(parent["path"])) as directory:
        require(list(directory.identity) == parent["identity"], "parent_mismatch")
    require(type(parent["context_receipt_sha256"]) is str and re.fullmatch("[a-f0-9]{64}", parent["context_receipt_sha256"]))
    return value, sha(raw)


def _command(argv, *, timeout=2):
    try:
        result = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, close_fds=True, timeout=timeout,
                                env={"PATH": "/usr/bin:/bin", "LC_ALL": "C", "SYSTEMD_PAGER": "cat"})
        require(len(result.stdout) <= 65536 and len(result.stderr) <= 65536 and result.returncode == 0, "native_unavailable")
        return result.stdout.decode("ascii", "strict").strip()
    except (subprocess.TimeoutExpired, OSError, UnicodeError):
        raise ControlError("native_unavailable") from None


def _show(unit, key):
    return _command([TOOLS["ctl"], "show", unit, "--property=" + key, "--value"])


def _released_unit(unit):
    # A stopped transient unit may already have been garbage collected by the
    # manager. Accept ONLY its explicit inactive/not-found readback, not any
    # command failure or missing output. This is called after retained empty-
    # scope samples, never as a substitute for CPU/quiescence measurement.
    try:
        result = subprocess.run([TOOLS["ctl"], "show", unit, "--property=LoadState", "--property=ActiveState"],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True,
            timeout=2, env={"PATH": "/usr/bin:/bin", "LC_ALL": "C", "SYSTEMD_PAGER": "cat"})
        require(len(result.stdout) <= 4096 and len(result.stderr) <= 4096, "termination_unresolved")
        lines = result.stdout.decode("ascii", "strict").splitlines()
        require(len(lines) == 2 and all(line.count("=") == 1 for line in lines), "termination_unresolved")
        values = dict(line.split("=", 1) for line in lines)
        require(set(values) == {"LoadState", "ActiveState"} and values["ActiveState"] == "inactive"
                and ((result.returncode == 0 and values["LoadState"] == "loaded")
                     or (result.returncode in (0, 1) and values["LoadState"] == "not-found")), "termination_unresolved")
    except (subprocess.TimeoutExpired, OSError, UnicodeError):
        raise ControlError("termination_unresolved") from None


def _slice(unit):
    props = ["CPUAccounting", "b", "true", "MemoryAccounting", "b", "true", "TasksAccounting", "b", "true",
             "MemoryMax", "t", str(MEMORY), "MemorySwapMax", "t", "0", "TasksMax", "t", "2"]
    _command([TOOLS["bus"], "call", "org.freedesktop.systemd1", "/org/freedesktop/systemd1",
              "org.freedesktop.systemd1.Manager", "StartTransientUnit", "ssa(sv)a(sa(sv))", unit, "fail", "6", *props, "0"])


def _cgroup_path(unit):
    value = _show(unit, "ControlGroup")
    require(re.fullmatch(r"/(?:[a-zA-Z0-9_.-]+/)*[a-zA-Z0-9_.-]+", value) is not None, "membership")
    path = Path("/sys/fs/cgroup" + value)
    require(path.is_dir() and not path.is_symlink(), "membership")
    return path


def _read_at(fd, name, cap=4096):
    item = os.open(name, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=fd)
    try:
        raw = os.read(item, cap + 1)
        require(0 < len(raw) <= cap, "counter_invalid")
        return raw
    finally:
        os.close(item)


def _decimal(raw):
    require(re.fullmatch(rb"[0-9]{1,20}\n?", raw) is not None, "counter_invalid")
    return integer(int(raw))


class Monitor:
    def __init__(self, fd):
        self.fd, self.life = fd, LinuxLifetime()
        self.lock, self.stop = threading.Lock(), threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def sample(self):
        values = parse_cpu(_read_at(self.fd, "cpu.stat"))
        tasks = _decimal(_read_at(self.fd, "pids.current"))
        peak = _decimal(_read_at(self.fd, "memory.peak"))
        events = _read_at(self.fd, "memory.events")
        require(all(line.split()[1] == b"0" for line in events.splitlines()
                    if line.split()[0] in (b"max", b"oom", b"oom_kill", b"oom_group_kill")), "resource_exceeded")
        with self.lock:
            self.life.sample(time.monotonic_ns(), *values, tasks, peak)

    def _run(self):
        while not self.stop.is_set():
            try:
                self.sample()
            except (ControlError, OSError) as error:
                with self.lock:
                    self.life.failure = error.reason if type(error) is ControlError else "counter_invalid"
                    self.life.final_ready = False
            self.stop.wait(POLL / 1e9)

    def check(self):
        with self.lock:
            require(self.life.failure is None, self.life.failure or "counter_invalid")

    def close(self):
        self.stop.set()
        self.thread.join(timeout=1)
        require(not self.thread.is_alive(), "termination_unresolved")


class LinuxHeldDirectory(OwnedDirectory):
    """Readonly openat lease from a verified live tmpfs mount, not a proc path."""
    def __init__(self, fd):
        super().__init__(Path("/"), [os.dup(fd)], readonly=True)

    def check_identity(self):
        require(not self.closed and _info(self.fd)[0] == self.identity, "export_invalid")

    def names(self, cap):
        self.check_identity()
        require(type(cap) is int and 0 < cap <= 55, "export_invalid")
        result = []
        with os.scandir(self.fd) as entries:
            for entry in entries:
                require(len(result) < cap and entry.is_file(follow_symlinks=False)
                        and not entry.is_symlink() and entry.stat(follow_symlinks=False).st_nlink == 1, "export_invalid")
                result.append(entry.name)
        return sorted(result)

    def _regular(self, name, create):
        from waveform_m08_export import _name
        _name(name)
        require(create is False, "export_invalid")
        self.check_identity()
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=self.fd)
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            os.close(fd)
            raise ControlError("export_invalid")
        return os.fdopen(fd, "rb", buffering=0)


def _tmpfs(fd):
    # fstatfs: Linux native long/pointer-sized layout, field storage deliberately
    # larger than the ABI; only documented f_type is read. fstatvfs gives capacity.
    libc = ctypes.CDLL(None, use_errno=True)
    libc.fstatfs.argtypes, libc.fstatfs.restype = [ctypes.c_int, ctypes.c_void_p], ctypes.c_int
    buffer = ctypes.create_string_buffer(256)
    require(libc.fstatfs(fd, buffer) == 0 and ctypes.c_long.from_buffer(buffer).value == 0x01021994, "native_contract")
    fs = os.fstatvfs(fd)
    require(fs.f_blocks * fs.f_frsize == SCRATCH, "native_contract")


def _tree_bytes(fd, depth=0, count=None):
    """Bounded no-follow accounting on the retained, quiescent private tmpfs."""
    count = [0] if count is None else count
    require(depth <= 8, "resource_exceeded")
    total = 0
    with os.scandir(fd) as entries:
        for entry in entries:
            count[0] += 1
            require(count[0] <= 1024 and not entry.is_symlink(), "export_invalid")
            info = entry.stat(follow_symlinks=False)
            if stat.S_ISDIR(info.st_mode):
                child = os.open(entry.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
                try:
                    held = os.fstat(child)
                    require((held.st_dev, held.st_ino) == (info.st_dev, info.st_ino), "export_invalid")
                    total += _tree_bytes(child, depth + 1, count)
                finally:
                    os.close(child)
            else:
                require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, "export_invalid")
                total += integer(info.st_size)
            require(total <= SCRATCH, "resource_exceeded")
    return total


def _kill(fd, service):
    started = time.monotonic_ns()
    target = os.open("cgroup.kill", os.O_WRONLY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=fd)
    try:
        require(os.write(target, b"1") == 1, "termination_unresolved")
    finally:
        os.close(target)
    while _decimal(_read_at(fd, "pids.current")):
        require(time.monotonic_ns() - started <= 2000000000, "termination_unresolved")
        time.sleep(0.005)
    _command([TOOLS["ctl"], "stop", service])


def _namespace_listener(pid, run):
    """Bind only in this manager-born child's netns, never move observer main."""
    require(type(pid) is int and pid > 1 and re.fullmatch("[a-f0-9]{32}", run), "membership")
    pidfd = os.pidfd_open(pid)
    namespace = os.open(f"/proc/{pid}/ns/net", os.O_RDONLY | os.O_CLOEXEC)
    identity = os.fstat(namespace)
    result = []

    def bind():
        channel = None
        try:
            os.setns(namespace, os.CLONE_NEWNET)
            actual = os.stat("/proc/thread-self/ns/net")
            require((actual.st_dev, actual.st_ino) == (identity.st_dev, identity.st_ino), "membership")
            channel = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
            channel.bind("\0caos-m08-" + run)
            channel.listen(1)
            channel.settimeout(0.05)
            result.append(channel)
        except (ControlError, OSError) as error:
            if channel is not None:
                channel.close()
            result.append(error)

    try:
        thread = threading.Thread(target=bind, daemon=True)
        thread.start()
        thread.join(timeout=2)
        require(not thread.is_alive() and len(result) == 1 and type(result[0]) is socket.socket, "native_contract")
        return result[0], pidfd
    except BaseException:
        os.close(pidfd)
        if result and type(result[0]) is socket.socket:
            result[0].close()
        raise
    finally:
        os.close(namespace)


def _launch(admission, service, scope, work, run, observer):
    uid, gid = admission["uid"], admission["gid"]
    properties = ["Slice=" + scope, "User=" + str(uid), "Group=" + str(gid), "SupplementaryGroups=",
        "Type=exec", "RemainAfterExit=yes", "KillMode=control-group", "TimeoutStopSec=2", "RuntimeMaxSec=60", "SendSIGKILL=yes",
        "NoNewPrivileges=yes", "CapabilityBoundingSet=", "AmbientCapabilities=",
        "ProtectSystem=strict", "ProtectHome=yes", "ProtectControlGroups=yes", "PrivateDevices=yes",
        "PrivateNetwork=yes", "RestrictAddressFamilies=AF_UNIX", "RestrictNamespaces=yes", "RestrictRealtime=yes",
        "ReadOnlyPaths=/", "InaccessiblePaths=/tmp /var/tmp", "UMask=0077",
        "MemoryMax=" + str(MEMORY), "MemorySwapMax=0", "TasksMax=2", "CPUAccounting=yes", "MemoryAccounting=yes", "TasksAccounting=yes",
        "CPUQuota=100%", "WorkingDirectory=" + str(work), "StandardOutput=null", "StandardError=null",
        "TemporaryFileSystem=" + str(work) + f":rw,size={SCRATCH},mode=0700,uid={uid},gid={gid}",
        "Environment=PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1",
        "Environment=HOME=" + str(work / "environment") + " TMPDIR=" + str(work / "environment") +
        " TMP=" + str(work / "environment") + " TEMP=" + str(work / "environment") +
        " MPLCONFIGDIR=" + str(work / "environment/matplotlib") + " XDG_CACHE_HOME=" + str(work / "environment/cache")]
    _command([TOOLS["run"], "--quiet", "--unit=" + service, *["--property=" + item for item in properties],
              "--", admission["python"], "-I", "-B", str(Path(__file__).resolve()), "--science",
              "caos-m08-" + run, run, str(observer)], timeout=10)


def run_cli(paths, reference, admission_path):
    """Actual scope+sealed science, not a fixture or unit-test launch adapter."""
    stage = None
    fd = work_fd = None
    monitor = None
    service = scope = None
    began = time.monotonic_ns()
    checkpoint = "admission"
    try:
        admission, admission_sha = read_admission(admission_path, paths["python"])
        parent = external_work_path(admission["parent"]["path"])
        require(paths["out"].parent == parent and not paths["out"].exists(), "parent_mismatch")
        run = os.urandom(16).hex()
        service, scope = "m08-" + run + ".service", "m08" + run + ".slice"
        stage = parent / (paths["out"].name + ".a4-" + run)
        stage.mkdir(mode=0o700)
        work = stage / "work"
        work.mkdir(mode=0o700)
        with ExitStack() as stack:
            inputs = [stack.enter_context(open_input(external_work_path(paths[name]), cap))
                      for name, cap in (("mseed", 16777216), ("stationxml", 2097152), ("request", 65536))]
            if reference is not None:
                inputs.append(stack.enter_context(open_input(external_work_path(reference), 1048576)))
            checkpoint = "slice"
            _slice(scope)
            group = _cgroup_path(scope)
            fd = os.open(group, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
            require(_decimal(_read_at(fd, "memory.max")) == MEMORY and _decimal(_read_at(fd, "memory.swap.max")) == 0
                    and _decimal(_read_at(fd, "pids.max")) == 2, "native_contract")
            require(parse_cpu(_read_at(fd, "cpu.stat")) == (0, 0, 0) and _decimal(_read_at(fd, "pids.current")) == 0
                    and _decimal(_read_at(fd, "memory.peak")) == 0, "counter_invalid")
            monitor = Monitor(fd)
            monitor.sample()
            monitor.thread.start()
            checkpoint = "launch"
            _launch(admission, service, scope, work, run, os.getpid())
            pid = _decimal(_show(service, "MainPID").encode())
            leaf = _cgroup_path(service)
            leaf_fd = os.open(leaf, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
            try:
                require(leaf.parent == group and _read_at(leaf_fd, "cgroup.procs") == (str(pid) + "\n").encode(), "membership")
            finally:
                os.close(leaf_fd)
            listener, pidfd = _namespace_listener(pid, run)
            stack.callback(os.close, pidfd)
            stack.enter_context(listener)
            while True:
                monitor.check()
                require(time.monotonic_ns() - began < 120000000000, "timeout")
                try:
                    connection, _ = listener.accept()
                    break
                except TimeoutError:
                    require(_show(service, "ActiveState") in {"activating", "active"}, "child_failed")
            with connection:
                connection.settimeout(0.05)
                checkpoint = "hello"
                hello = read_packet(connection.recv(65537), run, 1, "hello")
                require(set(hello) == {"pid"} and type(hello["pid"]) is int, "wire_invalid")
                pid, uid, gid = struct.unpack("3i", connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
                require((uid, gid) == (admission["uid"], admission["gid"]) and hello["pid"] == pid
                        and _show(service, "MainPID") == str(pid), "membership")
                checkpoint = "membership"
                leaf = _cgroup_path(service)
                leaf_fd = os.open(leaf, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
                try:
                    require(leaf.parent == group and _read_at(leaf_fd, "cgroup.procs") == (str(pid) + "\n").encode(), "membership")
                finally:
                    os.close(leaf_fd)
                for key, expected in {"NoNewPrivileges": "yes", "CapabilityBoundingSet": "", "AmbientCapabilities": "",
                                      "ProtectControlGroups": "yes", "PrivateNetwork": "yes", "TasksMax": "2",
                                      "MemoryMax": str(MEMORY), "MemorySwapMax": "0"}.items():
                    require(_show(service, key) == expected, "native_contract")
                status = Path(f"/proc/{pid}/status").read_text()
                require("NoNewPrivs:\t1\n" in status and "CapEff:\t0000000000000000\n" in status, "membership")
                work_fd = os.open(f"/proc/{pid}/cwd", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
                _tmpfs(work_fd)
                control = {"site_packages": admission["site_packages"], "runtime": admission["runtime"], "code": admission["code"],
                           "inputs": [{"initial": [list(item.initial[0]), *item.initial[1:]], "cap": item.cap} for item in inputs]}
                checkpoint = "ack"
                rights = array.array("i", [item.fd for item in inputs])
                require(connection.sendmsg([packet(run, 1, "ack", control)], [(socket.SOL_SOCKET, socket.SCM_RIGHTS, rights)]) > 0, "wire_invalid")
                while True:
                    monitor.check()
                    require(time.monotonic_ns() - began < 120000000000, "timeout")
                    try:
                        raw = connection.recv(65537)
                        break
                    except TimeoutError:
                        pass
                checkpoint = "drain"
                value = decode_control(raw)
                if value.get("phase") == "error":
                    error = read_packet(raw, run, 2, "error")
                    require(set(error) == {"reason"} and type(error["reason"]) is str, "wire_invalid")
                    raise ControlError(error["reason"])
                drained = read_packet(raw, run, 2, "drained")
                require(set(drained) == {"stamp", "pid", "status", "calculation_sha256"} and drained["pid"] == pid
                        and drained["status"] in {"computed", "qc_only"}, "drain_invalid")
                with monitor.lock:
                    monitor.life.drained(drained["stamp"])
                until = time.monotonic_ns() + 5000000000
                while not monitor.life.final_ready:
                    monitor.check()
                    require(time.monotonic_ns() < until, "timeout")
                    time.sleep(0.005)
                require(_show(service, "ExecMainStatus") == "0" and _show(service, "Result") == "success", "child_failed")
            for item in inputs:
                require(_info(item.fd) == item.initial, "closure_mismatch")
                with open_input(item.path, item.cap) as fresh:
                    require(fresh.initial == item.initial, "closure_mismatch")
            checkpoint = "reopen"
            final_fd = os.open("final", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=work_fd)
            from waveform_m08_export import verify_export, CHUNK
            stack.callback(os.close, final_fd)
            with LinuxHeldDirectory(final_fd) as source:
                sealed = verify_export(source)
                require(sealed.calculation_sha256 == drained["calculation_sha256"], "export_invalid")
                names = source.names(55)
                total = 0
                for name in names:
                    with source.open_regular(name) as member:
                        total += source.file_size(member)
                require(_tree_bytes(work_fd) + total + sum(item.initial[1] for item in inputs) + 196608 <= SCRATCH,
                        "resource_exceeded")
                with create_output(paths["out"], trusted_parent=parent) as target:
                    for name in names:
                        with source.open_regular(name) as src, target.create_regular(name) as dst:
                            while chunk := src.read(CHUNK):
                                require(dst.write(chunk) == len(chunk), "export_invalid")
                            target.flush_file(dst)
                    require(verify_export(target).calculation_sha256 == sealed.calculation_sha256, "export_invalid")
            monitor.close()
            life = monitor.life
            receipt = {"schema": RESOURCE, "run_id": run, "status": "measured", "cpu_ns": life.final_cpu_ns,
                "user_cpu_ns": life.last[2], "system_cpu_ns": life.last[3], "budget_ns": B, "stop_ns": S,
                "sample_count": life.samples, "max_sample_gap_ns": life.max_gap_ns,
                "peak_charge_bytes": life.last[-1], "active_processes": 0,
                "drained_ns": life.drain, "stable_final_ns": life.last[0], "admission_sha256": admission_sha,
                "memory_kind": "linux_cgroup_charge", "runtime_authorized": False, "method_accepted": False, "host_admitted": False}
            os.close(work_fd)
            work_fd = None
            checkpoint = "release"
            _command([TOOLS["ctl"], "stop", service, scope])
            os.close(fd)
            fd = None
            monitor = None
            require(not group.exists(), "termination_unresolved")
            _released_unit(service)
            _released_unit(scope)
            release = {"schema": RELEASE, "run_id": run, "receipt_sha256": sha(canonical(receipt)),
                       "all_native_owned_handles_closed": True, "scope_removed": True, "runtime_authorized": False}
            # All held original/socket handles close before release is persisted.
        work.rmdir()
        for name, body in (("eligibility.json", receipt), ("release.json", release)):
            with (stage / name).open("xb") as stream:
                stream.write(canonical(body))
                stream.flush()
                os.fsync(stream.fileno())
        return {"status": drained["status"], "reason": "measured", "run_id": run,
                "receipt_sha256": sha(canonical(receipt)), "release_sha256": sha(canonical(release)), "runtime_authorized": False}
    except (ControlError, WaveformInputError, OSError, ValueError, TypeError, KeyError) as error:
        print("M08_LINUX_BOOTSTRAP:" + checkpoint + ":" + (error.reason if type(error) is ControlError else type(error).__name__) +
              (":" + str(error.errno) if type(error) is OSError else ""), file=sys.stderr, flush=True)
        return terminal(error.reason if type(error) is ControlError else "native_contract")
    finally:
        if fd is not None:
            cleanup_failed = False
            try:
                if group.exists():
                    _kill(fd, service)
                else:
                    _released_unit(service)
            except (ControlError, OSError):
                cleanup_failed = True
            finally:
                try:
                    if monitor is not None:
                        monitor.close()
                    os.close(fd)
                    if group.exists():
                        _command([TOOLS["ctl"], "stop", scope])
                    _released_unit(scope)
                except (ControlError, OSError):
                    cleanup_failed = True
            if cleanup_failed:
                return terminal("termination_unresolved")
        if work_fd is not None:
            os.close(work_fd)


def _watch_observer(pid, ready):
    try:
        fd = os.pidfd_open(pid)
        poller = select.poll()
        poller.register(fd, select.POLLIN | select.POLLHUP | select.POLLERR)
        ready.set()
        poller.poll()
    finally:
        os._exit(99)


def _read_original(fd, item):
    require(type(item) is dict and set(item) == {"initial", "cap"} and
            type(item["cap"]) is int and 0 < item["cap"] <= 16777216 and
            type(item["initial"]) is list and len(item["initial"]) == 5, "closure_mismatch")
    initial = (tuple(item["initial"][0]), *item["initial"][1:])
    require(_info(fd) == initial and initial[1] <= item["cap"], "closure_mismatch")
    chunks, size = [], 0
    while block := os.read(fd, 65536):
        size += len(block)
        require(size <= initial[1] and size <= item["cap"], "closure_mismatch")
        chunks.append(block)
    require(size == initial[1] and _info(fd) == initial, "closure_mismatch")
    return b"".join(chunks)


def _science(wire, run, observer):
    """Fixed bootstrap: no scientific import/original body read before ACK."""
    require(os.geteuid() != 0 and type(observer) is int and observer > 0, "membership")
    ready = threading.Event()
    threading.Thread(target=_watch_observer, args=(observer, ready), daemon=True).start()
    require(ready.wait(2), "membership")
    with socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET) as connection:
        require(wire == "caos-m08-" + run, "wire_invalid")
        until = time.monotonic_ns() + 2000000000
        while True:
            try:
                connection.connect("\0" + wire)
                break
            except ConnectionRefusedError:
                require(time.monotonic_ns() < until, "wire_invalid")
                time.sleep(0.005)
        connection.settimeout(60)
        connection.sendall(packet(run, 1, "hello", {"pid": os.getpid()}))
        fds = []
        try:
            raw, auxiliary, flags, _ = connection.recvmsg(65537, socket.CMSG_SPACE(4 * array.array("i").itemsize), socket.MSG_CMSG_CLOEXEC)
            require(flags & ~socket.MSG_CMSG_CLOEXEC == 0 and len(auxiliary) == 1 and
                    auxiliary[0][:2] == (socket.SOL_SOCKET, socket.SCM_RIGHTS), "wire_invalid")
            held = array.array("i")
            held.frombytes(auxiliary[0][2])
            fds = list(held)
            control = read_packet(raw, run, 1, "ack")
            require(set(control) == {"site_packages", "runtime", "code", "inputs"} and len(fds) == len(control["inputs"])
                    and len(fds) in {3, 4}, "wire_invalid")
            require(control["code"] == code_hashes(), "closure_mismatch")
            site = validate_path(control["site_packages"])
            sys.path.insert(0, str(site))
            # Scope membership and exact namespace readbacks have now been ACKed.
            environment = Path.cwd() / "environment"
            environment.mkdir(mode=0o700)
            prepare_engine()
            closure(control)
            sources = []
            for fd, item in zip(fds[:3], control["inputs"][:3], strict=True):
                require(set(item) == {"initial", "cap"} and list(_info(fd)) == [tuple(item["initial"][0]), *item["initial"][1:]], "closure_mismatch")
                body = _read_original(fd, item)
                require(len(body) == item["initial"][1] and len(body) <= item["cap"], "closure_mismatch")
                sources.append(body)
            from waveform_m08_child import calculate_bytes
            from waveform_m08_export import plan_export, write_export, verify_export
            from waveform_evaluation import evaluate_waveform_candidates
            result, sealed = calculate_bytes(*sources)
            evaluation = None
            if len(fds) == 4:
                # Exact reference acquisition follows sealing, never decoder tuning.
                fd, item = fds[3], control["inputs"][3]
                reference = _read_original(fd, item)
                require(len(reference) == item["initial"][1] and len(reference) <= item["cap"], "closure_mismatch")
                evaluation = canonical(evaluate_waveform_candidates(sealed, reference), 2097152)
            final = Path.cwd() / "final"
            with create_output(final, trusted_parent=Path.cwd()) as target:
                write_export(plan_export(result, sealed, evaluation=evaluation), target)
                require(verify_export(target).calculation_sha256 == sealed.calculation_sha256, "export_invalid")
            for fd, item in zip(fds, control["inputs"], strict=True):
                os.lseek(fd, 0, os.SEEK_SET)
                body = _read_original(fd, item)
                require(len(body) == item["initial"][1] and _info(fd) == (tuple(item["initial"][0]), *item["initial"][1:]), "closure_mismatch")
                if fd in fds[:3]:
                    require(sha(body) == sha(sources[fds.index(fd)]), "closure_mismatch")
                else:
                    require(sha(body) == sha(reference), "closure_mismatch")
            closure(control)
            require(control["code"] == code_hashes(), "closure_mismatch")
            connection.sendall(packet(run, 2, "drained", {"stamp": time.monotonic_ns(), "pid": os.getpid(),
                               "status": result.metadata["status"], "calculation_sha256": sealed.calculation_sha256}))
            return 0
        except (ControlError, WaveformInputError, OSError, ValueError, TypeError, KeyError) as error:
            reason = error.reason if type(error) is ControlError else "science_failed"
            connection.sendall(packet(run, 2, "error", {"reason": reason}))
            return 3
        finally:
            for fd in fds:
                os.close(fd)


if __name__ == "__main__":
    try:
        require(len(sys.argv) == 5 and sys.argv[1] == "--science" and re.fullmatch("[0-9]{1,10}", sys.argv[4]) is not None)
        raise SystemExit(_science(sys.argv[2], sys.argv[3], int(sys.argv[4])))
    except (ControlError, OSError, ValueError):
        raise SystemExit(3) from None
