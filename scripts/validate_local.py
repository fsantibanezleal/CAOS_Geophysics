"""Local serial validation DAG. This is command custody, not scientific admission."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import re
import select
import signal
import stat
import subprocess
import sys
import threading
import time
import uuid

SELF = Path(__file__).resolve()
MAX_JSON = 4 * 1024 * 1024
MAX_FILES = 100000
NAME = re.compile(r"[a-zA-Z][a-zA-Z0-9_-]{0,63}\Z")


class Refusal(Exception):
    """Invalid declaration or untrusted/incomplete evidence; never retry it."""


def require(condition, message):
    if not condition:
        raise Refusal(message)


def canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def read_json(path):
    require(path.stat().st_size <= MAX_JSON, "JSON exceeds bound")
    return json.loads(path.read_bytes(), object_pairs_hook=pairs, parse_constant=lambda _: require(False, "nonfinite JSON"))


def regular(path):
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and not path.is_symlink(), f"not a regular file: {path}")
    require(not getattr(info, "st_file_attributes", 0) & 0x400, f"reparse file: {path}")
    return info


def file_record(path):
    before = regular(path)
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(chunk)
        held = os.fstat(stream.fileno())
    after = regular(path)
    # Windows Python path stat exposes birth time as ctime, while CRT fstat can
    # expose modification time there. Compare like-for-like held identity.
    identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
    require(identity(before) == identity(held) == identity(after), f"file changed during hash: {path}")
    require(before.st_ctime_ns == after.st_ctime_ns, f"path metadata changed during hash: {path}")
    return {"path": str(path), "bytes": after.st_size, "sha256": sha.hexdigest()}


def absolute(value, exists=True):
    require(type(value) is str and 0 < len(value) <= 8192 and "\0" not in value, "invalid path")
    path = Path(value)
    require(path.is_absolute(), f"absolute path required: {value}")
    for parent in (path, *path.parents):
        if parent.exists():
            info = parent.lstat()
            require(not parent.is_symlink() and not getattr(info, "st_file_attributes", 0) & 0x400,
                    f"linked path: {parent}")
    if exists:
        require(path.exists(), f"missing path: {path}")
    return path.resolve(strict=exists)


def external(value, root=None, exists=True):
    path = absolute(value, exists)
    forbidden = [Path("/tmp"), Path("/var/tmp"), Path("/run")] if os.name != "nt" else []
    if os.name == "nt":
        windir = Path(os.environ.get("SystemRoot", "C:/Windows"))
        forbidden += [windir, Path(os.environ.get("LOCALAPPDATA", str(windir))) / "Temp"]
    for parent in (path, *path.parents):
        require(not (parent / ".git").exists(), f"working data inside repository: {path}")
    require(not any(path == p or p in path.parents for p in forbidden), f"system temporary path: {path}")
    require(path != Path(path.anchor), "device root cannot be filesystem root")
    if root is not None:
        require(path != root and root in path.parents, f"working path outside device root: {path}")
    return path


def runtime_selector(exe):
    """Bind Python redirector configuration; Store activation is not local custody."""
    if os.name != "nt" or not exe.stem.lower().startswith("python"):
        return None
    require("windowsapps" not in str(exe).lower(), "Windows Store activation is outside local Job custody")
    for parent in (exe.parent, exe.parent.parent):
        cfg = parent / "pyvenv.cfg"
        if cfg.exists():
            absolute(str(cfg))
            require(regular(cfg).st_size <= 65536, "Python runtime selector exceeds bound")
            text = cfg.read_text(encoding="utf-8")
            require(not re.search(r"(?im)^home\s*=.*windowsapps", text),
                    "Windows Store venv activation is outside local Job custody; use explicit native image/environment")
            homes = re.findall(r"(?im)^home\s*=\s*(.+?)\s*$", text)
            require(len(homes) == 1, "one explicit Python venv home required")
            image = absolute(str(Path(homes[0]) / "python.exe"))
            return {"configuration": file_record(cfg), "base_image": file_record(image)}
    return None


def inventory(paths):
    records = {}
    count = 0
    for value in paths:
        base = absolute(value)
        if base.is_file():
            row = file_record(base)
            records[str(base)] = {k: row[k] for k in ("bytes", "sha256")}
            count += 1
        else:
            members, byte_count = {}, 0
            for path in base.rglob("*"):
                count += 1
                require(count <= MAX_FILES, "complete inventory exceeds bound")
                absolute(str(path))
                name = path.relative_to(base).as_posix()
                if path.is_dir():
                    members[name] = None
                else:
                    row = file_record(path)
                    members[name] = {k: row[k] for k in ("bytes", "sha256")}
                    byte_count += row["bytes"]
            # Hash EVERY exact member name/type/byte count/content hash, including
            # empty directories. Only representation is compacted, never inputs.
            records[str(base)] = {"inventory_sha256": digest(canonical(members)),
                                  "member_count": len(members), "bytes": byte_count}
        require(count <= MAX_FILES, "complete inventory exceeds bound")
    return records


def declaration(config, device_root):
    require(type(config) is dict and set(config) == {"schema", "nodes"} and
            type(config["schema"]) is int and config["schema"] == 1,
            "closed DAG schema 1 required")
    nodes = config["nodes"]
    require(type(nodes) is list and 1 <= len(nodes) <= 64, "DAG must contain 1..64 nodes")
    indexed = {}
    for node in nodes:
        require(type(node) is dict and set(node) == {
            "id", "argv", "cwd", "sources", "inputs", "env", "timeout_s", "log_bytes", "needs"
        }, "closed node fields required")
        name = node["id"]
        require(type(name) is str and NAME.fullmatch(name) and name not in indexed, "invalid/duplicate node id")
        argv = node["argv"]
        require(type(argv) is list and 1 <= len(argv) <= 256 and all(
            type(s) is str and 0 < len(s) <= 8192 and "\0" not in s for s in argv), "invalid argv")
        exe = absolute(argv[0])
        regular(exe)
        runtime_selector(exe)
        require(exe.suffix.lower() not in {".bat", ".cmd", ".ps1", ".sh"} and exe.stem.lower() not in {
            "cmd", "powershell", "pwsh", "sh", "bash", "dash", "zsh", "fish"
        }, "explicit executable, no shell")
        require(os.name == "nt" or os.access(exe, os.X_OK), "executable is not executable")
        require(absolute(node["cwd"]).is_dir(), "cwd must be a directory")
        for key in ("sources", "inputs", "needs"):
            require(type(node[key]) is list and len(node[key]) <= MAX_FILES and
                    all(type(s) is str for s in node[key]) and len(set(node[key])) == len(node[key]), f"invalid {key}")
        require(node["sources"], "explicit complete source declaration required")
        env = node["env"]
        require(type(env) is dict and len(env) <= 128 and all(
            type(k) is str and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", k) and
            type(v) is str and len(v) <= 8192 and "\0" not in v for k, v in env.items()), "invalid explicit environment")
        require(len({k.upper() for k in env}) == len(env), "case-ambiguous environment")
        for key in ("TMP", "TEMP", "TMPDIR"):
            require(key in env, f"explicit external {key} required")
            require(external(env[key], device_root).is_dir(), f"{key} is not a directory")
        if os.name == "nt":
            require("SystemRoot" in env and Path(env["SystemRoot"]).is_dir(), "explicit SystemRoot required")
        require(type(node["timeout_s"]) in (int, float) and math.isfinite(node["timeout_s"]) and
                0.1 <= node["timeout_s"] <= 86400, "invalid operational timeout")
        require(type(node["log_bytes"]) is int and 1 <= node["log_bytes"] <= 64 * 1024 * 1024, "invalid log bound")
        indexed[name] = node
    order, visiting = [], set()

    def visit(name):
        require(name in indexed, f"missing dependency: {name}")
        require(name not in visiting, f"cycle at {name}")
        if name in order:
            return
        visiting.add(name)
        for dep in indexed[name]["needs"]:
            visit(dep)
        visiting.remove(name)
        order.append(name)

    for name in indexed:
        visit(name)
    # Hash every complete declaration before ANY spawn, including independent branches.
    base = {name: snapshot(indexed[name]) for name in order}
    require(all(len(canonical(value)) < MAX_JSON - 20000 for value in base.values()), "complete node plan exceeds bound")
    return indexed, order, base


def snapshot(node):
    return {"node": json.loads(canonical(node)), "sources": inventory(node["sources"]), "inputs": inventory(node["inputs"]),
            "executable": file_record(Path(node["argv"][0])), "harness": file_record(SELF),
            "dispatcher": file_record(Path(sys.executable).resolve()), "python": sys.version,
            "dispatcher_image": file_record(dispatcher_image()),
            "runtime_selector": runtime_selector(Path(node["argv"][0])),
            "platform": sys.platform, "machine": os.uname().machine if os.name != "nt" else os.environ.get("PROCESSOR_ARCHITECTURE")}


def exclusive(path, data):
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def dispatcher_image():
    if os.name == "nt":
        api = ctypes.WinDLL("kernel32", use_last_error=True)
        api.GetModuleFileNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint32]
        api.GetModuleFileNameW.restype = ctypes.c_uint32
        buffer = ctypes.create_unicode_buffer(32768)
        length = api.GetModuleFileNameW(None, buffer, len(buffer))
        require(0 < length < len(buffer), "actual dispatcher image unavailable")
        return absolute(buffer.value)
    return Path(sys.executable).resolve(strict=True)


class WindowsJob:
    """Only kill-on-close. No scientific CPU, memory or process admission limits."""

    def __init__(self):
        from ctypes import wintypes as W

        class Basic(ctypes.Structure):
            _fields_ = [("per_process", ctypes.c_int64), ("per_job", ctypes.c_int64), ("flags", W.DWORD),
                        ("min_ws", ctypes.c_size_t), ("max_ws", ctypes.c_size_t), ("active", W.DWORD),
                        ("affinity", ctypes.c_size_t), ("priority", W.DWORD), ("scheduling", W.DWORD)]

        class IO(ctypes.Structure):
            _fields_ = [(n, ctypes.c_uint64) for n in ("read", "write", "other", "rb", "wb", "ob")]

        class Extended(ctypes.Structure):
            _fields_ = [("basic", Basic), ("io", IO), ("pm", ctypes.c_size_t), ("jm", ctypes.c_size_t),
                        ("pp", ctypes.c_size_t), ("pj", ctypes.c_size_t)]

        class Accounting(ctypes.Structure):
            _fields_ = [(n, ctypes.c_int64) for n in ("user", "kernel", "pu", "pk")] + [
                (n, W.DWORD) for n in ("faults", "total", "active", "terminated")]

        self.Accounting = Accounting
        self.api = ctypes.WinDLL("kernel32", use_last_error=True)
        self.name = "Local\\validation-" + uuid.uuid4().hex
        for name, args, result in (
            ("CreateJobObjectW", [ctypes.c_void_p, W.LPCWSTR], ctypes.c_void_p),
            ("SetInformationJobObject", [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, W.DWORD], W.BOOL),
            ("AssignProcessToJobObject", [ctypes.c_void_p, ctypes.c_void_p], W.BOOL),
            ("QueryInformationJobObject", [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, W.DWORD, ctypes.c_void_p], W.BOOL),
            ("TerminateJobObject", [ctypes.c_void_p, W.UINT], W.BOOL),
            ("CloseHandle", [ctypes.c_void_p], W.BOOL),
        ):
            fn = getattr(self.api, name)
            fn.argtypes, fn.restype = args, result
        self.handle = self.api.CreateJobObjectW(None, self.name)  # NULL security: non-inheritable.
        require(self.handle, "CreateJobObject failed")
        limits = Extended()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE; no breakaway.
        try:
            self.check(self.api.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)))
        except BaseException:
            self.api.CloseHandle(self.handle)
            raise

    def check(self, success):
        require(success, f"Job Object API failed: {ctypes.get_last_error()}")

    def assign(self, process):
        from ctypes import wintypes as W
        self.api.IsProcessInJob.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(W.BOOL)]
        self.api.IsProcessInJob.restype = W.BOOL
        assigned = W.BOOL()
        self.check(self.api.IsProcessInJob(process._handle, self.handle, ctypes.byref(assigned)))
        require(assigned.value, "atomic Job List assignment absent")

    def drain(self):
        self.check(self.api.TerminateJobObject(self.handle, 1))
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            row = self.Accounting()
            self.check(self.api.QueryInformationJobObject(self.handle, 1, ctypes.byref(row), ctypes.sizeof(row), None))
            if row.active == 0:
                return
            time.sleep(0.01)
        raise Refusal("Job Object extinction unresolved")

    def close(self):
        self.check(self.api.CloseHandle(self.handle))


class WindowsProcess:
    """Atomic job enrollment at birth, including venv/Store redirector children."""

    def __init__(self, argv, cwd, env, job):
        from ctypes import wintypes as W
        import msvcrt

        class Startup(ctypes.Structure):
            _fields_ = [("cb", W.DWORD), ("reserved", W.LPWSTR), ("desktop", W.LPWSTR), ("title", W.LPWSTR)] + [
                (name, W.DWORD) for name in ("x", "y", "xs", "ys", "xc", "yc", "fill", "flags")] + [
                ("show", W.WORD), ("reserved2bytes", W.WORD), ("reserved2", ctypes.c_void_p),
                ("stdin", W.HANDLE), ("stdout", W.HANDLE), ("stderr", W.HANDLE)]

        class ExtendedStartup(ctypes.Structure):
            _fields_ = [("startup", Startup), ("attributes", ctypes.c_void_p)]

        class Information(ctypes.Structure):
            _fields_ = [("process", W.HANDLE), ("thread", W.HANDLE), ("pid", W.DWORD), ("tid", W.DWORD)]

        self.api = job.api
        for name, args, result in (
            ("InitializeProcThreadAttributeList", [ctypes.c_void_p, W.DWORD, W.DWORD, ctypes.POINTER(ctypes.c_size_t)], W.BOOL),
            ("UpdateProcThreadAttribute", [ctypes.c_void_p, W.DWORD, ctypes.c_size_t, ctypes.c_void_p,
                                           ctypes.c_size_t, ctypes.c_void_p, ctypes.c_void_p], W.BOOL),
            ("DeleteProcThreadAttributeList", [ctypes.c_void_p], None),
            ("CreateProcessW", [W.LPCWSTR, W.LPWSTR, ctypes.c_void_p, ctypes.c_void_p, W.BOOL, W.DWORD,
                                ctypes.c_void_p, W.LPCWSTR, ctypes.c_void_p, ctypes.c_void_p], W.BOOL),
            ("WaitForSingleObject", [W.HANDLE, W.DWORD], W.DWORD),
            ("GetExitCodeProcess", [W.HANDLE, ctypes.POINTER(W.DWORD)], W.BOOL),
        ):
            fn = getattr(self.api, name)
            fn.argtypes, fn.restype = args, result
        pipe_fds = []
        attributes = None
        initialized = False
        created = False
        try:
            ir, iw = os.pipe()
            pipe_fds.extend((ir, iw))
            outr, outw = os.pipe()
            pipe_fds.extend((outr, outw))
            errr, errw = os.pipe()
            pipe_fds.extend((errr, errw))
            for fd in (ir, outw, errw):
                os.set_inheritable(fd, True)
            handles = (W.HANDLE * 3)(*(msvcrt.get_osfhandle(fd) for fd in (ir, outw, errw)))
            jobs = (W.HANDLE * 1)(job.handle)
            size = ctypes.c_size_t()
            self.api.InitializeProcThreadAttributeList(None, 2, 0, ctypes.byref(size))
            require(size.value > 0, "Job List attribute size unavailable")
            attributes = ctypes.create_string_buffer(size.value)
            job.check(self.api.InitializeProcThreadAttributeList(attributes, 2, 0, ctypes.byref(size)))
            initialized = True
            job.check(self.api.UpdateProcThreadAttribute(attributes, 0, 0x20002, handles, ctypes.sizeof(handles), None, None))
            job.check(self.api.UpdateProcThreadAttribute(attributes, 0, 0x2000D, jobs, ctypes.sizeof(jobs), None, None))
            startup = ExtendedStartup()
            startup.startup.cb = ctypes.sizeof(startup)
            startup.startup.flags = 0x100  # STARTF_USESTDHANDLES
            startup.startup.stdin, startup.startup.stdout, startup.startup.stderr = handles
            startup.attributes = ctypes.cast(attributes, ctypes.c_void_p)
            information = Information()
            command = ctypes.create_unicode_buffer(subprocess.list2cmdline(argv))
            environment = ctypes.create_unicode_buffer("\0".join(f"{k}={v}" for k, v in sorted(env.items(), key=lambda x: x[0].upper())) + "\0\0")
            # JOB_LIST is assigned by CreateProcess before any thread or redirector runs.
            job.check(self.api.CreateProcessW(argv[0], command, None, None, True,
                      0x80000 | 0x400 | 0x8000000, environment, cwd, ctypes.byref(startup), ctypes.byref(information)))
            self._handle, self.pid = information.process, information.pid
            self.api.CloseHandle(information.thread)
            created = True
            for fd in (ir, outw, errw):
                os.close(fd)
                pipe_fds.remove(fd)
            self.stdin = os.fdopen(iw, "wb", buffering=0)
            pipe_fds.remove(iw)
            self.stdout = os.fdopen(outr, "rb", buffering=0)
            pipe_fds.remove(outr)
            self.stderr = os.fdopen(errr, "rb", buffering=0)
            pipe_fds.remove(errr)
            self.returncode = None
        except BaseException:
            if created:
                job.drain()
                self.api.CloseHandle(self._handle)
            raise
        finally:
            if initialized:
                self.api.DeleteProcThreadAttributeList(attributes)
            for fd in pipe_fds:
                os.close(fd)

    def poll(self):
        wait = self.api.WaitForSingleObject(self._handle, 0)
        require(wait in (0, 258), "process wait failed")
        if wait == 0 and self.returncode is None:
            from ctypes import wintypes as W
            code = W.DWORD()
            require(self.api.GetExitCodeProcess(self._handle, ctypes.byref(code)), "exit code unavailable")
            self.returncode = code.value
        return self.returncode

    def wait(self, timeout):
        require(self.api.WaitForSingleObject(self._handle, int(timeout * 1000)) == 0, "owned process did not drain")
        return self.poll()

    def close(self):
        self.api.CloseHandle(self._handle)


def owner(plan_path, job_name=None):
    """Trusted gate/guardian bootstrap. Request-selected command cannot run before GO."""
    require(sys.stdin.buffer.read(3) == b"GO\n", "command gate closed")
    node = read_json(Path(plan_path))["base"]["node"]
    if os.name == "nt":
        # Independently check the actual interpreter, not a launcher proxy.
        # Query-only handle is closed BEFORE command creation; no inherited job
        # handle can keep the kill-on-close owner alive after dispatcher death.
        from ctypes import wintypes as W
        api = ctypes.WinDLL("kernel32", use_last_error=True)
        api.OpenJobObjectW.argtypes, api.OpenJobObjectW.restype = [W.DWORD, W.BOOL, W.LPCWSTR], W.HANDLE
        api.GetCurrentProcess.restype = W.HANDLE
        api.IsProcessInJob.argtypes, api.IsProcessInJob.restype = [W.HANDLE, W.HANDLE, ctypes.POINTER(W.BOOL)], W.BOOL
        api.CloseHandle.argtypes = [W.HANDLE]
        handle = api.OpenJobObjectW(4, False, job_name)
        require(handle, "local job query unavailable")
        try:
            member = W.BOOL()
            require(api.IsProcessInJob(api.GetCurrentProcess(), handle, ctypes.byref(member)) and member.value,
                    "actual bootstrap outside local job (activation redirector unsupported)")
        finally:
            api.CloseHandle(handle)
        # Already assigned to dispatcher-owned non-inheritable kill-on-close job.
        return subprocess.call(node["argv"], cwd=node["cwd"], env=node["env"], stdin=subprocess.DEVNULL,
                               shell=False, close_fds=True)
    require(hasattr(os, "waitid") and hasattr(os, "WNOWAIT"), "POSIX retained-leader wait unavailable")
    command = subprocess.Popen(node["argv"], cwd=node["cwd"], env=node["env"], stdin=subprocess.DEVNULL,
                               shell=False, close_fds=True, start_new_session=True)
    reason, result = None, None
    deadline = time.monotonic() + node["timeout_s"]
    try:
        while True:
            row = os.waitid(os.P_PID, command.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
            if row is not None:
                result = row.si_status if row.si_code == os.CLD_EXITED else 128 + row.si_status
                break
            if select.select([sys.stdin.buffer], [], [], 0.02)[0]:
                reason = "caller_lost_or_cancelled"
                break
            if time.monotonic() >= deadline:
                reason = "timeout"
                break
    finally:
        # Leader is UNREAPED, so its PGID cannot be reused before killpg.
        try:
            os.killpg(command.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        command.wait()
    return result if reason is None else 124


def execute(node, entry, cancelled):
    job = WindowsJob() if os.name == "nt" else None
    process = None
    threads, streams = [], []
    overflow, read_error = threading.Event(), threading.Event()
    lock, used = threading.Lock(), [0]
    started = time.monotonic()
    reason = "exit"

    def capture(pipe, path):
        try:
            with path.open("xb") as output:
                while chunk := pipe.read(4096):
                    with lock:
                        allowed = min(len(chunk), max(0, node["log_bytes"] - used[0]))
                        output.write(chunk[:allowed])
                        used[0] += allowed
                        if allowed != len(chunk):
                            overflow.set()
                output.flush()
                os.fsync(output.fileno())
        except BaseException:
            read_error.set()
        finally:
            pipe.close()

    try:
        # Bootstrap imports only stdlib; stdin gate is its first execution boundary.
        argv = [str(dispatcher_image()), "-I", "-B", str(SELF), "--owner", str(entry / "plan.json")]
        if job is not None:
            argv.append(job.name)
        process = WindowsProcess(argv, node["cwd"], node["env"], job) if job is not None else subprocess.Popen(
            argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=node["cwd"], env=node["env"], close_fds=True)
        if job is not None:
            job.assign(process)  # No GO, and thus no command, if assignment fails.
        for pipe, name in ((process.stdout, "stdout.bin"), (process.stderr, "stderr.bin")):
            streams.append(pipe)
            thread = threading.Thread(target=capture, args=(pipe, entry / name), daemon=True)
            thread.start()
            threads.append(thread)
        process.stdin.write(b"GO\n")
        process.stdin.flush()
        while process.poll() is None:
            if cancelled.is_set() or overflow.is_set() or read_error.is_set() or time.monotonic() - started > node["timeout_s"]:
                reason = "cancelled" if cancelled.is_set() else "log_limit" if overflow.is_set() else "log_io" if read_error.is_set() else "timeout"
                break
            time.sleep(0.02)
        process.stdin.close()  # POSIX independent guardian sees EOF, kills group and reaps retained leader.
        if job is not None:
            job.drain()
        process.wait(timeout=12)
        for thread in threads:
            thread.join(timeout=12)
        require(not any(t.is_alive() for t in threads), "output descendants did not drain")
        require(not read_error.is_set(), "log IO incomplete")
        if overflow.is_set():
            reason = "log_limit"
        return {"status": "PASS" if reason == "exit" and process.returncode == 0 else "FAIL",
                "reason": reason, "returncode": process.returncode,
                "elapsed_s": round(time.monotonic() - started, 6), "captured_bytes": used[0]}
    finally:
        if process is not None:
            if not process.stdin.closed:
                process.stdin.close()
            if job is not None:
                try:
                    job.drain()
                finally:
                    job.close()
            # Never signal root/science PIDs. This is only the harness's local bootstrap.
            process.wait(timeout=12)
            if isinstance(process, WindowsProcess):
                process.close()
        elif job is not None:
            job.close()


def reuse(entry, plan, fingerprint):
    require(set(p.name for p in entry.iterdir()) == {"plan.json", "stdout.bin", "stderr.bin", "receipt.json", "seal.json"},
            f"incomplete/unknown cache: {entry}")
    actual_plan, receipt, seal = (read_json(entry / n) for n in ("plan.json", "receipt.json", "seal.json"))
    require(actual_plan == plan, "cached declaration mismatch")
    require(type(seal) is dict and set(seal) == {"plan.json", "stdout.bin", "stderr.bin", "receipt.json"}, "invalid seal")
    for name, record in seal.items():
        require(record == file_record(entry / name), f"changed cached evidence: {entry / name}")
    require(type(receipt) is dict and set(receipt) == {
        "schema", "fingerprint", "status", "reason", "returncode", "elapsed_s", "captured_bytes"
    } and receipt["schema"] == 1 and receipt["fingerprint"] == fingerprint and receipt["status"] in {"PASS", "FAIL"},
        "invalid receipt")
    require(receipt["status"] != "PASS" or (receipt["reason"] == "exit" and receipt["returncode"] == 0), "invalid PASS")
    return receipt, digest(canonical(seal))


def run(config_path, device_root, cache_root, report_root):
    root = external(device_root)
    require(root.is_dir(), "device root must exist")
    config_path = external(config_path, root)
    cache = external(cache_root, root, exists=False)
    reports = external(report_root, root, exists=False)
    require(cache != reports and cache not in reports.parents and reports not in cache.parents, "cache/report overlap")
    config = read_json(config_path)
    nodes, order, base = declaration(config, root)
    cache.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    lock_path = cache / "dispatcher.lock"
    token = canonical({"pid": os.getpid(), "token": uuid.uuid4().hex})
    try:
        exclusive(lock_path, token)
    except FileExistsError as error:
        raise Refusal("live/unknown dispatcher lock; no automatic takeover") from error
    old_signals = {}
    try:
        cancelled = threading.Event()
        if threading.current_thread() is threading.main_thread():
            for sig in (signal.SIGINT, signal.SIGTERM):
                old_signals[sig] = signal.signal(sig, lambda *_: cancelled.set())
        summary = {"schema": 1, "config_sha256": file_record(config_path)["sha256"], "nodes": []}
        run_dir = reports / uuid.uuid4().hex
        run_dir.mkdir()
        outcomes = {}
        with (run_dir / "progress.jsonl").open("xb") as journal:
            for name in order:
                node = nodes[name]
                predecessors = {dep: {key: outcomes[dep][key] for key in ("fingerprint", "evidence", "status")}
                                for dep in node["needs"]}
                plan = {"base": base[name], "predecessors": predecessors}
                fingerprint = digest(canonical(plan))
                result = {"id": name, "fingerprint": fingerprint, "evidence": None, "status": "BLOCKED", "action": "blocked"}
                failed = [dep for dep in node["needs"] if outcomes[dep]["status"] != "PASS"]
                try:
                    if failed or cancelled.is_set():
                        result["reason"] = "prerequisites: " + ",".join(failed) if failed else "dispatcher cancelled"
                    else:
                        require(snapshot(node) == base[name], "source/input/runtime changed since preflight")
                        entry = cache / fingerprint
                        if entry.exists():
                            receipt, evidence = reuse(entry, plan, fingerprint)
                            result["action"] = "reused"
                        else:
                            entry.mkdir()
                            exclusive(entry / "plan.json", canonical(plan))
                            receipt = {"schema": 1, "fingerprint": fingerprint, **execute(node, entry, cancelled)}
                            if snapshot(node) != base[name]:
                                receipt.update(status="FAIL", reason="source_input_runtime_changed")
                            exclusive(entry / "receipt.json", canonical(receipt))
                            seal = {n: file_record(entry / n) for n in ("plan.json", "stdout.bin", "stderr.bin", "receipt.json")}
                            exclusive(entry / "seal.json", canonical(seal))
                            evidence = digest(canonical(seal))
                            result["action"] = "started"
                        result.update(status=receipt["status"], reason=receipt["reason"], returncode=receipt["returncode"],
                                      evidence=evidence, receipt=str(entry / "receipt.json"))
                except (Refusal, OSError, ValueError, subprocess.SubprocessError) as error:
                    result.update(status="REFUSED", action="refused", reason=str(error)[:1000])
                outcomes[name] = result
                summary["nodes"].append(result)
                journal.write(canonical(result) + b"\n")
                journal.flush()
                os.fsync(journal.fileno())
        summary["report"] = str(run_dir / "report.json")
        exclusive(run_dir / "report.json", canonical(summary))
        return summary
    finally:
        for sig, handler in old_signals.items():
            signal.signal(sig, handler)
        # Remove only our own exact lock, never adopt a stale one.
        if lock_path.read_bytes() == token:
            lock_path.unlink()


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) in (2, 3) and argv[0] == "--owner":
        return owner(argv[1], argv[2] if len(argv) == 3 else None)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--device-root", required=True)
    parser.add_argument("--cache-root", required=True)
    parser.add_argument("--report-root", required=True)
    args = parser.parse_args(argv)
    try:
        summary = run(args.config, args.device_root, args.cache_root, args.report_root)
    except (Refusal, OSError, ValueError) as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 2
    for row in summary["nodes"]:
        print(f"{row['id']}: {row['action']} {row['status']} ({row['reason']})")
    print(f"Report: {summary['report']}")
    return 0 if all(row["status"] == "PASS" for row in summary["nodes"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
