"""Exact private Linux qualification recipe/transport and retained evidence.

Nothing executes on import. No build during tests, dependency install, public
broker, automatic retry/reset/cleanup, or app activation. CLI has separate recipe
and controls operations; execution requires the independently reviewed artifacts
and root-owned manifest. This does not implement deployment or API authentication.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import selectors
import signal
import stat
import struct
import subprocess
import time

from scripts.prepare_linux_cpu_context import ContextError, encode_context, identity, unit_arguments

FRAME = struct.Struct("<4sHHIIQQ16s16s")
SOURCE_NAMES = (
    "controller.h", "controller.c", "linux_controller.h", "linux_controller.c",
    "linux_main.c", "linux_probe.c", "linux_fixture.c",
)
BUILD_SOURCE_FILES = frozenset("scripts/native_physical_cpu/" + name for name in SOURCE_NAMES) | {
    "scripts/prepare_linux_cpu_context.py", "scripts/run_linux_cpu_controls.py",
    "tests/worker_accounting/native/test_linux_context.py",
    "tests/worker_accounting/native/test_linux_source.py",
    "tests/worker_accounting/native/test_linux_controller.py"}
BUILD_TOOLS = frozenset({"/usr/bin/cc", "/usr/bin/as", "/usr/bin/ld", "/usr/bin/readelf",
    "/usr/libexec/gcc/x86_64-linux-gnu/13/cc1", "/usr/libexec/gcc/x86_64-linux-gnu/13/collect2",
    "/usr/bin/systemd-run", "/usr/bin/systemctl"})
BUILD_ARTIFACT_NAMES = frozenset(target + extension
    for target in ("core", "platform", "main", "probe", "fixture")
    for extension in (".o", ".d")) | {"controller", "probe", "fixture"}
COMMON_FLAGS = ["-std=c17", "-Wall", "-Wextra", "-Werror", "-Wconversion", "-Wshadow",
                "-fstack-protector-strong", "-D_FORTIFY_SOURCE=2", "-O2", "-fPIE"]
CASES = {
    "nominal": ("--nominal", 1), "system_cpu": ("--system-cpu", 1), "threads": ("--threads", 1),
    "exited": ("--exited", 1), "grandchild": ("--grandchild", 1),
    "escape": ("--escape", 1), "upper60": ("--upper", 1), "upper240": ("--upper", 2),
    "cancel": ("--cancel", 1), "eof": ("--cancel", 1),
    "heartbeat_loss": ("--cancel", 1), "output": ("--output", 1), "oom": ("--oom", 1),
    "wrong_attempt": ("--nominal", 1), "wrong_object": ("--nominal", 1),
    "malformed_frame": ("--nominal", 1), "bad_ack": ("--nominal", 1),
    "no_ack": ("--nominal", 1), "parent_crash": ("--cancel", 1),
    "controller_crash": ("--cancel", 1), "simultaneous_crash": ("--cancel", 1),
    "backpressure": ("--cancel", 1),
    "clone_denied": ("--nominal", 1), "setup_denied": ("--nominal", 1),
    "early_ack": ("--nominal", 1), "delayed_observer": ("--cancel", 1),
    "over_budget": ("--upper", 1),
}


class ControlError(ValueError):
    pass


def reject():
    raise ControlError("linux_qualification_invalid")


def build_recipe(source_root, output_root, cc="/usr/bin/cc"):
    if cc != "/usr/bin/cc":
        reject()
    source_root, output_root = Path(source_root), Path(output_root)
    commands = []
    for name, target in (("controller.c", "core"), ("linux_controller.c", "platform"),
                         ("linux_main.c", "main"), ("linux_probe.c", "probe"),
                         ("linux_fixture.c", "fixture")):
        commands.append([cc, *COMMON_FLAGS, *( ["-pthread"] if target == "fixture" else []),
                         "-MD", "-MF", str(output_root / (target + ".d")), "-c",
                         str(source_root / name), "-o", str(output_root / (target + ".o"))])
    for objects, executable, extra in ((["core", "platform", "main"], "controller", []),
                                      (["core", "platform", "probe"], "probe", []),
                                      (["core", "platform", "fixture"], "fixture", ["-pthread"])):
        commands.append([cc, "-pie", "-Wl,-z,relro,-z,now", *extra,
                         *(str(output_root / (name + ".o")) for name in objects),
                         "-o", str(output_root / executable)])
    return commands


def file_digest(path, cap=64 * 1024**2):
    path = Path(path)
    status = path.stat()
    if not stat.S_ISREG(status.st_mode) or status.st_size > cap:
        reject()
    value = hashlib.sha256()
    count = 0
    with path.open("rb") as stream:
        while chunk := stream.read(65536):
            count += len(chunk)
            if count > cap:
                reject()
            value.update(chunk)
    if count != status.st_size:
        reject()
    return value.hexdigest()


def bounded_read(path, cap):
    if Path(path).stat().st_size > cap:
        reject()
    with Path(path).open("rb") as stream:
        raw = stream.read(cap + 1)
    if len(raw) > cap:
        reject()
    return raw


def validate_build_fields(value):
    """No filesystem or execution: reject unknown identity/shape before preflight."""
    if type(value) is not dict or set(value) != {"schema", "source_commit_claim", "authority_sha256",
            "attempt", "source", "output", "scratch", "outcome", "source_hashes", "tool_hashes",
            "header_hashes", "library_hashes", "execute_build"}:
        reject()
    if value["schema"] != "linux-native-build-1" or value["execute_build"] is not True:
        reject()
    for key, width in (("source_commit_claim", 40), ("authority_sha256", 64)):
        if type(value[key]) is not str or not re.fullmatch("[0-9a-f]{" + str(width) + "}", value[key]):
            reject()
    try:
        identity(value["attempt"])
    except ContextError:
        reject()
    for label in ("source", "output", "scratch", "outcome"):
        name = value[label]
        if (type(name) is not str or not name.startswith("/") or len(name.encode("utf-8")) > 1024 or
                "\0" in name or str(PurePosixPath(name)) != name or ".." in PurePosixPath(name).parts):
            reject()
    roots = [PurePosixPath(value[key]) for key in ("source", "output", "scratch", "outcome")]
    if any(a == b or a.is_relative_to(b) or b.is_relative_to(a)
           for i, a in enumerate(roots) for b in roots[i + 1:]):
        reject()
    if type(value["source_hashes"]) is not dict or set(value["source_hashes"]) != BUILD_SOURCE_FILES:
        reject()
    if type(value["tool_hashes"]) is not dict or set(value["tool_hashes"]) != BUILD_TOOLS:
        reject()
    for kind in ("source_hashes", "tool_hashes", "header_hashes", "library_hashes"):
        mapping = value[kind]
        if type(mapping) is not dict or not mapping or len(mapping) > 256:
            reject()
        for name, digest in mapping.items():
            if type(name) is not str or type(digest) is not str or not re.fullmatch("[0-9a-f]{64}", digest):
                reject()
            if kind != "source_hashes" and (not name.startswith("/") or
                    str(PurePosixPath(name)) != name or ".." in PurePosixPath(name).parts or "\0" in name):
                reject()


def build_manifest(path, expected):
    if type(expected) is not str or not re.fullmatch("[0-9a-f]{64}", expected):
        reject()
    selected = safe_path(path)
    info = selected.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_mode & 0o777 != 0o600:
        reject()
    raw = bounded_read(selected, 65536)
    if hashlib.sha256(raw).hexdigest() != expected:
        reject()
    value = json.loads(raw, object_pairs_hook=duplicate_pairs, parse_constant=lambda unused: reject())
    validate_build_fields(value)
    for label in ("source", "output", "scratch", "outcome"):
        safe_path(value[label], label == "source")
    for kind in ("source_hashes", "tool_hashes", "header_hashes", "library_hashes"):
        for name, digest in value[kind].items():
            selected_path = Path(value["source"]) / name if kind == "source_hashes" else Path(name)
            if kind == "source_hashes":
                safe_path(selected_path)
            # Ordinary installed tool/library aliases are observed, not rejected
            # as output links and not replaced by guessed alternate versions.
            if file_digest(selected_path) != digest:
                reject()
    if file_digest(Path(__file__).resolve()) != value["source_hashes"]["scripts/run_linux_cpu_controls.py"]:
        reject()
    return value


def observe_inventory(output, scratch, *, linker=False):
    """Build custody observation, not a science scratch quota/RSS controller."""
    if type(linker) is not bool:
        reject()
    entries = []
    total = 0
    invalid = False
    linker_leaves = 0
    resolution_leaves = 0
    vanished_scratch = []
    for kind, root in (("output", Path(output)), ("scratch", Path(scratch))):
        for entry in root.iterdir():
            if len(entries) >= 128:
                return dict(bytes=total, leaves=len(entries), entries=entries, invalid=True, truncated=True)
            try:
                status = entry.lstat()
            except FileNotFoundError:
                # GCC may unlink its exact temporary leaf between readdir and
                # lstat. Only a reviewed scratch name can disappear harmlessly;
                # artifact loss or an unknown transient remains a failed build.
                ordinary = re.fullmatch(r"cc[A-Za-z0-9]{6}\.(s|o)", entry.name)
                transient_linker = linker and re.fullmatch(
                    r"cc[A-Za-z0-9]{6}\.(cdtor\.(c|o)|res)", entry.name)
                if kind != "scratch" or not (ordinary or transient_linker):
                    raise
                vanished_scratch.append(entry.name)
                if len(vanished_scratch) > 128:
                    reject()
                continue
            if not stat.S_ISREG(status.st_mode) or status.st_nlink != 1 or status.st_uid != 0:
                invalid = True
            total += status.st_size
            if total > 32 * 1024**2:
                invalid = True
            if kind == "output" and entry.name not in BUILD_ARTIFACT_NAMES:
                invalid = True
            if kind == "scratch":
                ordinary = re.fullmatch(r"cc[A-Za-z0-9]{6}\.(s|o)", entry.name)
                ctor = re.fullmatch(r"cc[A-Za-z0-9]{6}\.cdtor\.(c|o)", entry.name)
                resolution = re.fullmatch(r"cc[A-Za-z0-9]{6}\.res", entry.name)
                if ctor:
                    linker_leaves += 1
                if resolution:
                    resolution_leaves += 1
                known_linker = linker and ((ctor and linker_leaves <= 2) or
                    (resolution and resolution_leaves <= 1 and status.st_size <= 65536))
                if not ordinary and not known_linker:
                    invalid = True
            entries.append(dict(kind=kind, name=entry.name, bytes=status.st_size,
                                mode=stat.S_IFMT(status.st_mode), uid=status.st_uid, nlink=status.st_nlink))
    return dict(bytes=total, leaves=len(entries), entries=entries, invalid=invalid,
                truncated=False, vanished_scratch=vanished_scratch)


def inventory(output, scratch, *, linker=False):
    observed = observe_inventory(output, scratch, linker=linker)
    if observed["invalid"]:
        reject()
    return observed


def build_capture(argv, output, scratch, deadline, *, linker=False):
    """Bounded selected-tool capture; PID1 owns the separate build unit teardown."""
    if type(linker) is not bool:
        reject()
    child = subprocess.Popen(argv, shell=False, stdin=subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
    selector = selectors.DefaultSelector()
    out, err = bytearray(), bytearray()
    for stream, target in ((child.stdout, out), (child.stderr, err)):
        os.set_blocking(stream.fileno(), False)
        selector.register(stream, selectors.EVENT_READ, target)
    begun = time.monotonic_ns()
    held = None
    first_invalid = None
    peak = dict(bytes=0, leaves=0)
    try:
        while selector.get_map():
            if time.monotonic_ns() > deadline or time.monotonic_ns()-begun > 30_000_000_000:
                raise ControlError("build_timeout")
            observed = observe_inventory(output, scratch, linker=linker)
            if observed["invalid"]:
                first_invalid = observed
                reject()
            peak["bytes"] = max(peak["bytes"], observed["bytes"])
            peak["leaves"] = max(peak["leaves"], observed["leaves"])
            for key, unused in selector.select(0.005):
                chunk = os.read(key.fileobj.fileno(), 4096)
                if not chunk:
                    selector.unregister(key.fileobj)
                elif len(key.data) + len(chunk) > 1024**2:
                    raise ControlError("build_stream_cap")
                else:
                    key.data.extend(chunk)
        code = child.wait(timeout=1)
    except (ControlError, OSError, subprocess.TimeoutExpired) as error:
        held = str(error) if type(error) is ControlError else type(error).__name__
        code = None
    finally:
        selector.close()
        if child.poll() is None:
            child.kill()  # Capturing systemd-run only; not a worker accounting claim.
            child.wait(timeout=4)
        child.stdout.close()
        child.stderr.close()
    return dict(returncode=code, held=held, wall_ns=time.monotonic_ns()-begun,
                peak_observed=peak, first_invalid_inventory=first_invalid), bytes(out), bytes(err)


def run_build(path, expected):
    if os.name != "posix" or os.geteuid() != 0:
        reject()
    m = build_manifest(path, expected)
    output, scratch, outcome = (Path(m[name]) for name in ("output", "scratch", "outcome"))
    # External outcome first. Partial roots/unknown files are retained on failure.
    # If its creation itself fails, caller retains original manager/CLI failure.
    outcome.mkdir(mode=0o700)
    stages, held, artifacts, dependency_closure = [], None, None, {}
    start = time.monotonic_ns()
    deadline = start + 120_000_000_000
    try:
        output.mkdir(mode=0o700)
        scratch.mkdir(mode=0o700)
        commands = build_recipe(Path(m["source"]) / "scripts/native_physical_cpu", output)
        for index, command in enumerate(commands):
            unit = "geophysics-cpu-build-" + m["attempt"] + "-" + str(index + 1) + ".service"
            state = manager(["/usr/bin/systemctl", "show", unit, "--property=LoadState", "--value"])
            if state.stdout.strip() != b"not-found":
                reject()
            wrapper = ["/usr/bin/systemd-run", "--quiet", "--pipe", "--wait", "--unit=" + unit,
                       "--property=Type=exec", "--property=KillMode=control-group", "--property=Restart=no",
                       "--property=RuntimeMaxSec=30s", "--property=TimeoutStopSec=1s", "--property=MemoryMax=256M",
                       "--property=TasksMax=32", "--property=NoNewPrivileges=yes", "--property=CapabilityBoundingSet=",
                       "--property=PrivateNetwork=yes", "--property=PrivateDevices=yes", "--property=ProtectHome=yes",
                       "--property=ProtectSystem=strict", "--property=ProtectControlGroups=yes",
                       "--property=ReadOnlyPaths=" + m["source"],
                       "--property=ReadWritePaths=" + str(output) + " " + str(scratch),
                       "--setenv=TMPDIR=" + str(scratch), "--setenv=PATH=/usr/bin:/bin", "--setenv=LC_ALL=C", *command]
            stage, out, err = build_capture(wrapper, output, scratch, deadline, linker=index >= 5)
            stages.append(dict(index=index + 1, command=command, **stage))
            exclusive(outcome / (str(index + 1) + ".stdout"), out)
            exclusive(outcome / (str(index + 1) + ".stderr"), err)
            if stage["held"] or stage["returncode"] != 0:
                manager(["/usr/bin/systemctl", "stop", unit])
                raise ControlError("build_stage_failed")
            inventory(output, scratch, linker=index >= 5)
        if {entry.name for entry in output.iterdir()} != BUILD_ARTIFACT_NAMES:
            reject()
        # Emitted selected header closure is retained and hashed before any load.
        for target in ("core", "platform", "main", "probe", "fixture"):
            raw = bounded_read(output / (target + ".d"), 65536)
            if b"\\ " in raw:
                reject()
            text = raw.decode("utf-8").replace("\\\n", " ")
            paths = text.split(":", 1)[1].split()
            if len(paths) > 256:
                reject()
            for name in paths:
                selected = Path(name)
                if not selected.is_absolute() or ".." in selected.parts:
                    reject()
                dependency_closure[name] = file_digest(selected)
        artifacts = {entry.name: dict(bytes=entry.stat().st_size, sha256=file_digest(entry))
                     for entry in output.iterdir()}
    except (ControlError, OSError, ValueError) as error:
        held = str(error) if type(error) is ControlError else type(error).__name__
    try:
        retained = observe_inventory(output, scratch)
    except OSError as error:
        retained = dict(unavailable=type(error).__name__)
    receipt = dict(schema="linux-native-build-outcome-1", manifest_sha256=expected,
                   source_commit_claim=m["source_commit_claim"], authority_sha256=m["authority_sha256"],
                   stages=stages, held=held, artifact_success=held is None, artifacts=artifacts if held is None else None,
                   dependency_closure=dependency_closure, retained_inventory=retained,
                   wall_ns=time.monotonic_ns()-start,
                   abi_execution="NOT_RUN", controller_execution="NOT_RUN", runtime_admission=False)
    exclusive(outcome / "build.json", (json.dumps(receipt, sort_keys=True, separators=(",", ":"))+"\n").encode("ascii"))
    return receipt


def frame(kind, seq, attempt, obj, payload=b""):
    if (type(kind) is not int or kind not in (1, 2, 3, 4, 5) or
            type(seq) is not int or not 1 <= seq < 2**64 or type(payload) is not bytes or
            len(payload) != {1: 0, 2: 0, 3: 0, 4: 64, 5: 32}[kind]):
        reject()
    return FRAME.pack(b"LCP1", 1, kind, len(payload), 0, seq, time.monotonic_ns(),
                      identity(attempt), identity(obj)) + payload


class Transcript:
    """Fixed-sized frame buffer, incremental digest, retained summary not full trace."""
    def __init__(self, attempt, obj):
        self.attempt, self.obj = identity(attempt), identity(obj)
        self.pending = bytearray()
        self.digest = hashlib.sha256()
        self.sequence = self.samples = 0
        self.last = self.final = self.native_digest = None
        self.release = None
        self.bytes = 0
        self.max_gap = self.max_query = 0

    def feed(self, raw):
        if type(raw) is not bytes or len(raw) > 4160 or self.bytes + len(raw) > 16 * 1024**2:
            reject()
        self.bytes += len(raw)
        # One incomplete frame retained, never a whole-input accumulation.
        for byte in raw:
            self.pending.append(byte)
            if len(self.pending) < 64:
                continue
            magic, version, kind, size, flags, seq, clock, attempt, obj = FRAME.unpack_from(self.pending)
            if (magic != b"LCP1" or version != 1 or flags or attempt != self.attempt or obj != self.obj or
                    seq != self.sequence + 1 or size != {256: 96, 257: 184, 258: 32, 259: 8}.get(kind)):
                reject()
            if len(self.pending) < 64 + size:
                continue
            packet = bytes(self.pending)
            body = packet[64:]
            if kind == 256:
                if self.final is not None or self.samples >= 65536:
                    reject()
                values = struct.unpack("<12Q", body)
                start, end, usage, user, system, charge, populated, root, adopted, gap, query, error = values
                if end < start or charge != max(usage, user + system) * 1000 or populated > 1 or root > 1:
                    reject()
                if self.last and (start < self.last[1] or any(values[i] < self.last[i] for i in (2, 3, 4, 7, 8))):
                    reject()
                self.samples += 1
                self.last = values
                self.max_gap, self.max_query = max(self.max_gap, gap), max(self.max_query, query)
                self.digest.update(packet)
            elif kind == 257:
                if self.final is not None:
                    reject()
                values = struct.unpack("<23Q", body)
                if values[15] not in (0, 1):
                    reject()
                if self.last is None:
                    # Explicit unavailable sentinel, not an observed zero CPU.
                    if (any(values[:11]) or not 1 <= values[11] <= 23 or values[12] or
                            not values[13] or values[14] < values[13] or values[15] or
                            any(values[16:22]) or not 1 <= values[22] < 2**32):
                        reject()
                elif values[:11] != self.last[:11]:
                    reject()
                self.final = values
                self.digest.update(packet)
            elif kind == 258:
                if self.final is None or self.native_digest is not None or body != self.digest.digest():
                    reject()
                self.native_digest = body
            else:
                if self.native_digest is None or self.release is not None or self.final[15] != 1:
                    reject()
                self.release = struct.unpack("<Q", body)[0]
            self.sequence = seq
            self.pending.clear()


def safe_path(path, leaf_exists=True):
    """Linux output custody only: no links, root ownership, shared writable ancestry."""
    original = str(path)
    if not original or len(original.encode("utf-8")) > 1024 or "\0" in original:
        reject()
    path = Path(path)
    if str(path) != original:
        reject()
    if not path.is_absolute() or any(p in (".", "..") for p in path.parts):
        reject()
    for index, part in enumerate(reversed((path, *path.parents))):
        if part == path and not leaf_exists:
            if part.exists() or part.is_symlink():
                reject()
            continue
        info = part.lstat()
        if stat.S_ISLNK(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            reject()
        if part != path and not stat.S_ISDIR(info.st_mode):
            reject()
    return path


def exclusive(path, raw):
    safe_path(path, False)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        # Retain partial output, never overwrite/retry/delete it.
        raise


def duplicate_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            reject()
        result[key] = value
    return result


def load_manifest(path, expected_sha256):
    if type(expected_sha256) is not str or not re.fullmatch("[0-9a-f]{64}", expected_sha256):
        reject()
    selected = safe_path(path)
    info = selected.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_mode & 0o777 != 0o600 or info.st_size > 32768:
        reject()
    raw = selected.read_bytes()
    if len(raw) > 32768 or hashlib.sha256(raw).hexdigest() != expected_sha256:
        reject()
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=duplicate_pairs,
                       parse_constant=lambda unused: reject())
    required = {"controller", "fixture", "controller_sha256", "fixture_sha256", "source_commit",
                "uid", "gid", "root", "case", "attempt", "object", "authority_sha256"}
    if type(value) is not dict or set(value) != required:
        reject()
    for key in ("controller_sha256", "fixture_sha256", "authority_sha256"):
        if type(value[key]) is not str or not re.fullmatch("[0-9a-f]{64}", value[key]):
            reject()
    if type(value["source_commit"]) is not str or not re.fullmatch("[0-9a-f]{40}", value["source_commit"]):
        reject()
    if (type(value["case"]) is not str or value["case"] not in CASES or
            any(type(value[k]) is not int or not 1 <= value[k] < 2**32 - 1 for k in ("uid", "gid"))):
        reject()
    identity(value["attempt"])
    identity(value["object"])
    for key in ("controller", "fixture"):
        artifact = safe_path(value[key])
        status = artifact.stat()
        if (not stat.S_ISREG(status.st_mode) or status.st_nlink != 1 or not status.st_mode & 0o111 or
                status.st_size > 8 * 1024**2 or hashlib.sha256(artifact.read_bytes()).hexdigest() != value[key + "_sha256"]):
            reject()
    safe_path(value["root"], False)
    return value, hashlib.sha256(raw).hexdigest()


def manager(argv):
    process = subprocess.Popen(argv, shell=False, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
    selector = selectors.DefaultSelector()
    output, errors = bytearray(), bytearray()
    for stream, target in ((process.stdout, output), (process.stderr, errors)):
        os.set_blocking(stream.fileno(), False)
        selector.register(stream, selectors.EVENT_READ, target)
    deadline = time.monotonic_ns() + 5_000_000_000
    try:
        while selector.get_map():
            if time.monotonic_ns() >= deadline:
                raise ControlError("linux_manager_timeout")
            for key, unused in selector.select(0.005):
                packet = os.read(key.fileobj.fileno(), 4096)
                if not packet:
                    selector.unregister(key.fileobj)
                elif len(key.data) + len(packet) > 65536:
                    reject()
                else:
                    key.data.extend(packet)
        code = process.wait(timeout=max(0.001, (deadline-time.monotonic_ns())/10**9))
        return subprocess.CompletedProcess(argv, code, bytes(output), bytes(errors))
    finally:
        selector.close()
        if process.poll() is None:
            process.kill()
            process.wait(timeout=1)
        process.stdout.close()
        process.stderr.close()


def show(unit):
    output = manager(["/usr/bin/systemctl", "show", unit, "--no-pager",
                      "--property=MainPID,ActiveState,SubState,ControlGroup,CPUUsageNSec,Result"])
    if output.returncode:
        reject()
    return dict(line.split("=", 1) for line in output.stdout.decode("ascii").splitlines())


def owned_pidfd(unit, attempt):
    values = show(unit)
    pid = int(values["MainPID"])
    if pid <= 1:
        reject()
    handle = os.pidfd_open(pid)
    expected = "/system.slice/" + unit + ("/observer" if "-qual-" in unit else "")
    if Path("/proc/" + str(pid) + "/cgroup").read_text("ascii") != "0::" + expected + "\n":
        os.close(handle)
        reject()
    if attempt not in unit:
        os.close(handle)
        reject()
    return handle


def run_control(manifest_path, expected_sha256):
    if os.name != "posix" or os.geteuid() != 0:
        reject()
    m, manifest_hash = load_manifest(manifest_path, expected_sha256)
    root = Path(m["root"])
    root.mkdir(mode=0o700)
    manifest_raw = bounded_read(manifest_path, 32768)
    if hashlib.sha256(manifest_raw).hexdigest() != manifest_hash:
        reject()
    exclusive(root / "manifest.json", manifest_raw)
    cwd = root / "science"
    cwd.mkdir(mode=0o700)
    os.chown(cwd, m["uid"], m["gid"])
    mode, cls = CASES[m["case"]]
    context = encode_context(budget_class=cls, uid=m["uid"], gid=m["gid"], attempt=m["attempt"],
                             object_id=m["object"], executable=m["fixture"], argv0=m["fixture"],
                             cwd=str(cwd), arguments=[mode], environment=["LANG=C"])
    context_path = root / "context.bin"
    exclusive(context_path, context)
    parent = "geophysics-cpu-parent-" + m["attempt"] + ".service"
    unit = "geophysics-cpu-qual-" + m["attempt"] + ".service"
    for name in (parent, unit):
        # LoadState=not-found only; no adopting an existing/failed unit.
        state = manager(["/usr/bin/systemctl", "show", name, "--property=LoadState", "--value"])
        if state.stdout.strip() != b"not-found":
            reject()
    parent_start = manager(["/usr/bin/systemd-run", "--quiet", "--unit=" + parent,
                            "--property=Type=exec", "--property=KillMode=control-group",
                            "--property=RuntimeMaxSec=600s", "--property=Restart=no",
                            m["fixture"], "--parent"])
    if parent_start.returncode:
        exclusive(root / "parent-start.stderr", parent_start.stderr)
        reject()
    if show(parent)["ActiveState"] != "active":
        reject()
    command = unit_arguments("/usr/bin/systemd-run", m["controller"], str(context_path),
                             m["attempt"], parent, cls)
    if m["case"] == "clone_denied":
        command[-2:-2] = ["--property=SystemCallFilter=~clone3", "--property=SystemCallErrorNumber=EPERM"]
    elif m["case"] == "setup_denied":
        command = ["--property=CapabilityBoundingSet=CAP_SETUID CAP_SETPCAP"
                   if item == "--property=CapabilityBoundingSet=CAP_SETUID CAP_SETGID CAP_SETPCAP"
                   else item for item in command]
    attempt, obj = m["attempt"], m["object"]
    trace = Transcript(attempt, obj)
    raw_path = root / "native.frames"
    raw_fd = os.open(raw_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    process = subprocess.Popen(command, shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, bufsize=0, close_fds=True)
    for stream in (process.stdin, process.stdout, process.stderr):
        os.set_blocking(stream.fileno(), False)
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, "out")
    selector.register(process.stderr, selectors.EVENT_READ, "err")
    begun = time.monotonic_ns()
    seq = 0
    pending = bytearray()
    last_heartbeat = 0
    intervention = custody = False
    stderr = bytearray()
    failure = None
    sent = []
    def send(kind, payload=b"", selected_attempt=attempt, selected_obj=obj):
        nonlocal seq
        seq += 1
        packet = frame(kind, seq, selected_attempt, selected_obj, payload)
        if len(pending) + len(packet) > 4160:
            reject()
        pending.extend(packet)
        sent.append((seq, kind, hashlib.sha256(packet).hexdigest()))
    case = m["case"]
    if case == "wrong_attempt":
        send(1, selected_attempt="ff" * 16 if attempt != "ff" * 16 else "ee" * 16)
    elif case == "wrong_object":
        send(1, selected_obj="ff" * 16 if obj != "ff" * 16 else "ee" * 16)
    else:
        send(1)
        if case == "malformed_frame":
            pending[0] = 0
        if case == "early_ack":
            send(5, b"\0" * 32)
    try:
        while True:
            now = time.monotonic_ns()
            elapsed = now - begun
            if elapsed > (310 if cls == 2 else 130) * 10**9:
                raise ControlError("linux_qualification_timeout")
            if elapsed > 300_000_000 and not intervention and case != "over_budget":
                intervention = True
                if case == "cancel":
                    send(3)
                elif case == "eof":
                    process.stdin.close()
                elif case in ("parent_crash", "controller_crash", "simultaneous_crash"):
                    names = [parent, unit] if case == "simultaneous_crash" else [parent if case == "parent_crash" else unit]
                    handles = [owned_pidfd(name, attempt) for name in names]
                    try:
                        for handle in handles:
                            signal.pidfd_send_signal(handle, signal.SIGKILL)
                    finally:
                        for handle in handles:
                            os.close(handle)
                elif case == "delayed_observer":
                    handle = owned_pidfd(unit, attempt)
                    try:
                        signal.pidfd_send_signal(handle, signal.SIGSTOP)
                        time.sleep(0.150)
                        signal.pidfd_send_signal(handle, signal.SIGCONT)
                    finally:
                        os.close(handle)
            if case == "over_budget" and not intervention and trace.last and trace.last[5] >= 56_000_000_000:
                intervention = True
                handle = owned_pidfd(unit, attempt)
                try:
                    signal.pidfd_send_signal(handle, signal.SIGSTOP)
                    time.sleep(4.500)
                    signal.pidfd_send_signal(handle, signal.SIGCONT)
                finally:
                    os.close(handle)
            if (now - last_heartbeat >= 100_000_000 and not process.stdin.closed and
                    case not in ("heartbeat_loss", "wrong_attempt", "wrong_object", "malformed_frame")):
                send(2)
                last_heartbeat = now
            if pending and not process.stdin.closed:
                try:
                    count = os.write(process.stdin.fileno(), pending)
                    del pending[:count]
                except BlockingIOError:
                    pass
                except BrokenPipeError:
                    pending.clear()
                    process.stdin.close()
            for key, mask in selector.select(0.005):
                if key.data == "out" and case == "backpressure" and 300_000_000 < elapsed < 3_000_000_000:
                    continue
                packet = os.read(key.fileobj.fileno(), 4160)
                if not packet:
                    selector.unregister(key.fileobj)
                elif key.data == "err":
                    if len(stderr) + len(packet) > 65536:
                        reject()
                    stderr.extend(packet)
                else:
                    if trace.bytes + len(packet) > 16 * 1024**2:
                        reject()
                    count = os.write(raw_fd, packet)
                    if count != len(packet):
                        reject()
                    trace.feed(packet)
            if trace.native_digest is not None and not custody:
                os.fsync(raw_fd)
                # Exact transcript receipt sealed before BIND; no DB durability claim.
                receipt = dict(schema="linux-cpu-transcript-1", manifest_sha256=manifest_hash,
                               source_commit_claim=m["source_commit"], controller_sha256=m["controller_sha256"],
                               context_sha256=hashlib.sha256(context).hexdigest(),
                               transcript_sha256=trace.native_digest.hex(), samples=trace.samples,
                               final=list(trace.final), authority_sha256=m["authority_sha256"])
                receipt_bytes = (json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")
                exclusive(root / "transcript-receipt.json", receipt_bytes)
                receipt_hash = hashlib.sha256(receipt_bytes).digest()
                if trace.final[15] == 1 and case != "no_ack":
                    send(4, trace.native_digest + receipt_hash)
                    send(5, (b"\0" * 32 if case == "bad_ack" else receipt_hash))
                custody = True
            if process.poll() is not None and not selector.get_map():
                break
    except BaseException as error:
        failure = type(error).__name__
        # Emergency stop of exactly this owned fresh attempt, never PID-tree kill.
        manager(["/usr/bin/systemctl", "stop", unit])
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=4)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=4)
    finally:
        os.fsync(raw_fd)
        os.close(raw_fd)
        selector.close()
    # Separate manager diagnostic; controller final does not replace it or full API tails.
    unit_final = show(unit)
    cgroup_path = Path("/sys/fs/cgroup/system.slice") / unit
    extinct = False
    extinction_deadline = time.monotonic_ns() + 4_000_000_000
    while time.monotonic_ns() < extinction_deadline:
        if not cgroup_path.exists():
            extinct = True
            break
        events = (cgroup_path / "cgroup.events").read_bytes()
        if len(events) <= 4096 and b"populated 0\n" in events:
            extinct = True
            break
        time.sleep(0.005)
    manager(["/usr/bin/systemctl", "stop", parent])
    exclusive(root / "controller.stderr", bytes(stderr))
    result = dict(schema="linux-cpu-control-1", case=case, manifest_sha256=manifest_hash,
                  source_commit_claim=m["source_commit"], controller_sha256=m["controller_sha256"],
                  fixture_sha256=m["fixture_sha256"], returncode=process.returncode,
                  wall_ns=time.monotonic_ns() - begun, failure=failure,
                  samples=trace.samples, final=list(trace.final) if trace.final else None,
                  digest=trace.native_digest.hex() if trace.native_digest else None,
                  release=trace.release, max_gap_ns=trace.max_gap, max_query_ns=trace.max_query,
                  raw_sha256=hashlib.sha256(raw_path.read_bytes()).hexdigest(),
                  unit=unit_final, group_extinct=extinct,
                  birth_marker=(cwd / "birth.marker").exists(),
                  escape_denied=(cwd / "escape.denied").exists(),
                  scientific_admission=False, runtime_admission=False, sent=sent)
    exclusive(root / "result.json", (json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii"))
    return result


def pytest_addoption(parser):
    parser.addoption("--linux-cpu-results", action="store", default=None,
                     help="Exact private completed host-matrix directory; absent is NOT_RUN/error, not skip")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="operation", required=True)
    recipe = sub.add_parser("recipe")
    recipe.add_argument("source_root")
    recipe.add_argument("output_root")
    controls = sub.add_parser("controls")
    controls.add_argument("manifest")
    controls.add_argument("manifest_sha256")
    build = sub.add_parser("build")
    build.add_argument("manifest")
    build.add_argument("manifest_sha256")
    args = parser.parse_args()
    if args.operation == "recipe":
        print(json.dumps(build_recipe(args.source_root, args.output_root), indent=2))
    elif args.operation == "build":
        result = run_build(args.manifest, args.manifest_sha256)
        print(json.dumps({"artifact_success": result["artifact_success"], "held": result["held"],
                          "abi_execution": "NOT_RUN", "runtime_admission": False}, sort_keys=True))
        if result["artifact_success"] is not True:
            raise SystemExit(1)
    else:
        # Private output file, not an API safe-error surface.
        result = run_control(args.manifest, args.manifest_sha256)
        print(json.dumps({"case": result["case"], "failure": result["failure"],
                          "runtime_admission": False}, sort_keys=True))


if __name__ == "__main__":
    main()
