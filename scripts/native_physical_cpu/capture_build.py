"""Operator-only I01 build capture. Import never launches or writes anything.

This is NOT a scientific supervisor or a descendant containment mechanism.
Only compile/link the reviewed four-stage recipe; never load/run its outputs.
Execution needs independent review and an explicit private approval manifest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import threading
import time

STREAM_CAP = 2 * 1024 * 1024
OUTPUT_CAP = 64 * 1024 * 1024
FILE_CAP = 32
ENTRY_CAP = 128
DEPTH_CAP = 8
NAME_CAP = 1024
RECEIPT_CAP = 128 * 1024
INVENTORY_CAP = 64 * 1024
ROOT_KEYS = ("source", "output", "scratch", "outcome", "vc", "sdk", "system")
SOURCE_FILES = (
    "scripts/native_physical_cpu/controller.h",
    "scripts/native_physical_cpu/controller.c",
    "scripts/native_physical_cpu/abi_probe.c",
    "scripts/native_physical_cpu/capture_build.py",
    "tests/worker_accounting/native/test_contract.py",
    "tests/worker_accounting/native/test_bounds.py",
    "tests/worker_accounting/native/test_scope.py",
    "tests/worker_accounting/native/test_capture_build.py",
)
PINNED = {
    "bin/Hostx64/x64/cl.exe": "9beec04038c74406e4c055593edc07ddda7b166272d77cbf85507d5a6be29ff0",
    "bin/Hostx64/x64/link.exe": "dfdc692e2837fc67f0da929f1b3330a55ed723b009157a6a604da643a824ccd1",
    "lib/x64/libcmt.lib": "2f85dcc9697707be63ce7842cfa4ad0dbc1fddabfcd1c4e6c0afcb372fdff83c",
    "lib/x64/libvcruntime.lib": "e8060e3d69ea5303431e92cdbdff68b73f3a3739526db27f52b2e61897bf7b2e",
    "lib/x64/oldnames.lib": "533735074def7e97179650450c79a7e5e9433e0e593cabbd55f802a7d09bc00f",
}
SDK_PINNED = {
    "Lib/10.0.22621.0/ucrt/x64/libucrt.lib":
        "742bf3739ddb2e3fcd94bd7a1618aea1c832a08d1304f0a70fc59f5ae13307b9",
    "Lib/10.0.22621.0/um/x64/kernel32.lib":
        "25346e02cffca92abff07000d54e1830fe0d8861c31a114eda472547fe9f2f00",
}
PYTHON_PIN = "0b471133e110cfb53a061cad528ce8e517d7b9ac41a0a396c39ad795a487fc14"
TREE_COUNTS = (90, 361, 66, 303, 2214)
TREE_BYTES = (88183442, 16162316, 1055527, 11723353, 126821714)
SHA = re.compile(r"[0-9a-f]{64}\Z")


class BuildHeld(Exception):
    """Fixed private outcome only; no exceptions/raw paths in a public payload."""


def safe_path(path: Path, *, missing_leaf: bool = False) -> None:
    if not path.is_absolute() or ".." in path.parts:
        raise BuildHeld("build_path_invalid")
    for index, item in enumerate((path, *path.parents)):
        try:
            info = item.lstat()
        except FileNotFoundError:
            if index == 0 and missing_leaf:
                continue
            raise
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise BuildHeld("build_path_invalid")
        if stat.S_ISREG(info.st_mode) and info.st_nlink != 1:
            raise BuildHeld("build_path_invalid")


def identity(info) -> tuple:
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
            info.st_nlink, stat.S_IFMT(info.st_mode))


def same_metadata(before, after) -> bool:
    # Compare ctime only within the same path/handle API, not across Windows APIs.
    return identity(before) == identity(after) and before.st_ctime_ns == after.st_ctime_ns


def file_hash(path: Path) -> str:
    safe_path(path)
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > OUTPUT_CAP:
        raise BuildHeld("build_file_invalid")
    h = hashlib.sha256()
    with path.open("rb") as stream:
        before_handle = os.fstat(stream.fileno())
        if identity(before_handle) != identity(info):
            raise BuildHeld("build_file_changed")
        count = 0
        while chunk := stream.read(65536):
            count += len(chunk)
            if count > OUTPUT_CAP:
                raise BuildHeld("build_file_invalid")
            h.update(chunk)
        after_handle = os.fstat(stream.fileno())
    safe_path(path)
    if (count != info.st_size or not same_metadata(before_handle, after_handle) or
            not same_metadata(info, path.stat())):
        raise BuildHeld("build_file_changed")
    return h.hexdigest()


def unique_pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise BuildHeld("build_approval_invalid")
        result[key] = value
    return result


def approval(path: Path, expected: str) -> dict:
    if not SHA.fullmatch(expected):
        raise BuildHeld("build_approval_invalid")
    safe_path(path)
    if path.stat().st_size > STREAM_CAP:
        raise BuildHeld("build_approval_invalid")
    with path.open("rb") as stream:
        raw = stream.read(STREAM_CAP + 1)
    if len(raw) > STREAM_CAP or hashlib.sha256(raw).hexdigest() != expected:
        raise BuildHeld("build_approval_invalid")
    # This is an operator-reviewed, hash-pinned private manifest, not user JSON.
    value = json.loads(raw, object_pairs_hook=unique_pairs)
    if type(value) is not dict or set(value) != {
        "schema", "source_commit", "source_hashes", "tree_files", "execute_i01_build", "roots"
    }:
        raise BuildHeld("build_approval_invalid")
    if value["schema"] != "i01-build-approval-2" or value["execute_i01_build"] is not True:
        raise BuildHeld("build_approval_invalid")
    if type(value["source_commit"]) is not str or not re.fullmatch("[0-9a-f]{40}", value["source_commit"]):
        raise BuildHeld("build_approval_invalid")
    roots = value["roots"]
    if type(roots) is not dict or set(roots) != set(ROOT_KEYS):
        raise BuildHeld("build_approval_invalid")
    if any(type(p) is not str or len(p) > 1024 or not p for p in roots.values()):
        raise BuildHeld("build_approval_invalid")
    if any(path.is_relative_to(Path(roots[key])) for key in ("output", "scratch", "outcome")):
        raise BuildHeld("build_approval_invalid")
    hashes = value["source_hashes"]
    if type(hashes) is not dict or set(hashes) != set(SOURCE_FILES):
        raise BuildHeld("build_approval_invalid")
    if any(type(h) is not str or not SHA.fullmatch(h) for h in hashes.values()):
        raise BuildHeld("build_approval_invalid")
    trees = value["tree_files"]
    if type(trees) is not list or len(trees) != 5:
        raise BuildHeld("build_approval_invalid")
    for tree, count in zip(trees, TREE_COUNTS, strict=True):
        if type(tree) is not dict or len(tree) != count:
            raise BuildHeld("build_approval_invalid")
        for name, h in tree.items():
            rel = Path(name)
            if (type(name) is not str or not name or len(name) > 1024 or
                    rel.anchor or ".." in rel.parts or "\\" in name or ":" in name or
                    type(h) is not str or not SHA.fullmatch(h)):
                raise BuildHeld("build_approval_invalid")
    return value


def include_roots(vc: Path, sdk: Path) -> tuple[Path, ...]:
    return (vc / "include", sdk / "Include/10.0.22621.0/ucrt",
            sdk / "Include/10.0.22621.0/shared", sdk / "Include/10.0.22621.0/um")


def verify_inputs(source: Path, vc: Path, sdk: Path, binding: dict) -> None:
    for root in (source, vc, sdk):
        safe_path(root)
        if not root.is_dir():
            raise BuildHeld("build_path_invalid")
    if file_hash(Path(sys.executable)) != PYTHON_PIN:
        raise BuildHeld("build_python_changed")
    for name, h in binding["source_hashes"].items():
        if file_hash(source / name) != h:
            raise BuildHeld("build_source_changed")
    if file_hash(Path(__file__).absolute()) != binding["source_hashes"][SOURCE_FILES[3]]:
        raise BuildHeld("build_source_changed")
    for root, pinned in ((vc, PINNED), (sdk, SDK_PINNED)):
        for name, h in pinned.items():
            if file_hash(root / name) != h:
                raise BuildHeld("build_tool_changed")
    roots = (vc / "bin/Hostx64/x64", *include_roots(vc, sdk))
    for root, tree, expected_bytes in zip(roots, binding["tree_files"], TREE_BYTES, strict=True):
        safe_path(root)
        found = set()
        total = 0
        for directory, dirs, files in os.walk(root, followlinks=False):
            safe_path(Path(directory))
            for name in dirs:
                safe_path(Path(directory) / name)
            for name in files:
                path = Path(directory) / name
                rel = path.relative_to(root).as_posix()
                if rel not in tree or len(found) >= len(tree) or file_hash(path) != tree[rel]:
                    raise BuildHeld("build_tree_changed")
                found.add(rel)
                total += path.stat().st_size
        if found != set(tree) or total != expected_bytes:
            raise BuildHeld("build_tree_changed")


def recipe(source: Path, output: Path, vc: Path, sdk: Path) -> tuple[tuple[str, ...], ...]:
    common = ("/nologo", "/c", "/TC", "/std:c17", "/MT", "/Zl", "/X",
              "/W4", "/WX", "/sdl", "/GS", "/guard:cf", "/O2", "/showIncludes",
              "/DUNICODE", "/D_UNICODE", "/D_WIN32_WINNT=0x0A00")
    common += tuple("/I" + str(p) for p in include_roots(vc, sdk))
    link = ("/NOLOGO", "/MACHINE:X64", "/NODEFAULTLIB", "/Brepro", "/DYNAMICBASE",
            "/NXCOMPAT", "/HIGHENTROPYVA", "/guard:cf", "/INCREMENTAL:NO",
            "/OPT:REF", "/OPT:ICF", "/MANIFEST:NO")
    libs = (str(vc / "lib/x64/libcmt.lib"), str(vc / "lib/x64/libvcruntime.lib"),
            str(sdk / "Lib/10.0.22621.0/ucrt/x64/libucrt.lib"),
            str(vc / "lib/x64/oldnames.lib"), str(sdk / "Lib/10.0.22621.0/um/x64/kernel32.lib"))
    cl, linker = str(vc / "bin/Hostx64/x64/cl.exe"), str(vc / "bin/Hostx64/x64/link.exe")
    return (
        (cl, *common, "/Fo" + str(output / "core.obj"), str(source / SOURCE_FILES[1])),
        (linker, *link, "/DLL", "/OUT:" + str(output / "core.dll"),
         "/IMPLIB:" + str(output / "core.lib"), str(output / "core.obj"), *libs),
        (cl, *common, "/Fo" + str(output / "abi.obj"), str(source / SOURCE_FILES[2])),
        (linker, *link, "/SUBSYSTEM:CONSOLE", "/OUT:" + str(output / "abi.exe"),
         str(output / "abi.obj"), *libs),
    )


ALLOW = {"core.obj", "core.dll", "core.lib", "core.exp", "abi.obj", "abi.exe"}
ALLOW |= {f"stage{i}.{kind}" for i in range(1, 5) for kind in ("stdout", "stderr")}


def output_size(root: Path) -> int:
    safe_path(root)
    total = 0
    for count, path in enumerate(root.iterdir(), 1):
        safe_path(path)
        if count > FILE_CAP or path.name not in ALLOW or not path.is_file():
            raise BuildHeld("build_output_invalid")
        total += path.stat().st_size
        if total > OUTPUT_CAP:
            raise BuildHeld("build_output_exceeded")
    return total


def observe_workspace(output: Path, scratch: Path) -> dict:
    """Bounded metadata observation, never open unknown files or follow links.

    Partial observations are lower counts, not complete quota/drain evidence.
    Scratch names are quarantined metadata, never artifact identities.
    """
    report = {"held": None, "complete": False, "files": 0, "directories": 0,
              "file_bytes": 0, "entries": []}
    telemetry_leaves = 0
    inventory_bytes = 0

    def walk(root, directory, lane):
        nonlocal telemetry_leaves, inventory_bytes
        safe_path(directory)
        with os.scandir(directory) as iterator:
            for entry in iterator:
                path = Path(entry.path)
                rel = path.relative_to(root)
                name = rel.as_posix()
                if (len(report["entries"]) >= ENTRY_CAP or len(rel.parts) > DEPTH_CAP or
                        len(name) > NAME_CAP):
                    raise BuildHeld("build_observation_exceeded")
                safe_path(path)
                info = path.lstat()
                is_dir = stat.S_ISDIR(info.st_mode)
                if not is_dir and not stat.S_ISREG(info.st_mode):
                    raise BuildHeld("build_path_invalid")
                item = {"lane": lane, "name": name, "kind": "directory" if is_dir else "file",
                        "bytes": 0 if is_dir else info.st_size}
                amount = len(json.dumps(item, ensure_ascii=True, separators=(",", ":")).encode("ascii"))
                if inventory_bytes + amount > INVENTORY_CAP:
                    raise BuildHeld("build_observation_exceeded")
                inventory_bytes += amount
                report["entries"].append(item)
                report["directories" if is_dir else "files"] += 1
                report["file_bytes"] += item["bytes"]
                if report["files"] > FILE_CAP or report["file_bytes"] > OUTPUT_CAP:
                    raise BuildHeld("build_output_exceeded")
                if lane == "output":
                    valid = not is_dir and len(rel.parts) == 1 and name in ALLOW
                else:
                    dynamic = re.fullmatch(r"Microsoft/VSApplicationInsights/vstel[0-9a-f]{32}", name)
                    if dynamic and is_dir:
                        telemetry_leaves += 1
                    valid = is_dir and (name in {"Microsoft", "Microsoft/VSApplicationInsights"} or
                                        bool(dynamic)) and telemetry_leaves <= 1
                if not valid and report["held"] is None:
                    report["held"] = "build_output_invalid" if lane == "output" else "build_scratch_invalid"
                if is_dir:
                    yield from walk(root, path, lane)
                yield None

    try:
        for root, lane in ((output, "output"), (scratch, "scratch")):
            for _ in walk(root, root, lane):
                pass
        report["complete"] = True
    except BuildHeld as error:
        report["held"] = error.args[0]
    except OSError:
        report["held"] = "build_observation_unavailable"
    return report


def check_workspace(output: Path, scratch: Path) -> int:
    report = observe_workspace(output, scratch)
    if report["held"]:
        raise BuildHeld(report["held"])
    return report["file_bytes"]


def drain(stream, buffer: bytearray, stopped: threading.Event, failed: threading.Event,
          lock: threading.Lock) -> None:
    try:
        while not stopped.is_set():
            chunk = stream.read(65536)
            if not chunk:
                return
            with lock:
                if stopped.is_set():
                    return
                room = STREAM_CAP - len(buffer)
                if len(chunk) > room:
                    buffer.extend(chunk[:room])
                    failed.set()
                    return
                buffer.extend(chunk)
    except OSError:
        failed.set()
    finally:
        stream.close()


def capture(args: tuple[str, ...], output: Path, environment: dict, *, scratch: Path) -> dict:
    stopped, failed = threading.Event(), threading.Event()
    lock = threading.Lock()
    buffers = (bytearray(), bytearray())
    started = time.monotonic()
    # argv[0] is a rechecked absolute compiler/linker, never a shell or a probe.
    proc = subprocess.Popen(args, cwd=output, env=environment, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False,
                            close_fds=True, bufsize=0, creationflags=subprocess.CREATE_NO_WINDOW)
    readers = tuple(threading.Thread(target=drain, args=(stream, data, stopped, failed, lock), daemon=True)
                    for stream, data in zip((proc.stdout, proc.stderr), buffers, strict=True))
    for thread in readers:
        thread.start()
    held = None
    try:
        while proc.poll() is None:
            check_workspace(output, scratch)
            if failed.is_set():
                raise BuildHeld("build_stream_exceeded_or_unavailable")
            if time.monotonic() - started > 90:
                raise BuildHeld("build_deadline")
            stopped.wait(0.02)
        for thread in readers:
            thread.join(timeout=1)
        if any(t.is_alive() for t in readers) or failed.is_set():
            raise BuildHeld("build_stream_exceeded_or_unavailable")
        check_workspace(output, scratch)
        if proc.returncode != 0:
            held = "build_tool_failed"
    except BuildHeld as error:
        held = error.args[0]
    except OSError:
        held = "build_io_unavailable"
    finally:
        with lock:
            stopped.set()
        if proc.poll() is None:
            # Exact owned Popen handle only. NOT a descendant kill/drain proof.
            try:
                proc.kill()
                proc.wait(timeout=2)
            except (OSError, subprocess.TimeoutExpired):
                held = "build_root_termination_uncertain"
        for thread in readers:
            thread.join(timeout=1)
        if any(t.is_alive() for t in readers):
            held = "build_pipe_custody_uncertain"
    with lock:
        frozen = tuple(bytes(b) for b in buffers)
    return {"returncode": proc.returncode, "wall_ms": (time.monotonic() - started) * 1000,
            "held": held, "streams": frozen, "descendant_drain_proven": False}


def write_new(root: Path, name: str, data: bytes, *, scratch: Path | None = None) -> None:
    size = output_size(root) if scratch is None else check_workspace(root, scratch)
    if name not in ALLOW or len(data) > STREAM_CAP or size + len(data) > OUTPUT_CAP:
        raise BuildHeld("build_output_exceeded")
    with (root / name).open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def run(source: Path, output: Path, vc: Path, sdk: Path, system: Path, binding: dict,
        *, scratch: Path, outcome: Path) -> int:
    if os.name != "nt":
        raise BuildHeld("build_platform_closed")
    actual_roots = dict(zip(ROOT_KEYS, (source, output, scratch, outcome, vc, sdk, system), strict=True))
    if any(path != Path(binding["roots"][key]) for key, path in actual_roots.items()):
        raise BuildHeld("build_path_invalid")
    safe_path(system)
    # A full independent approval supplied this SystemRoot; no PATH discovery.
    if system.name.casefold() != "windows" or not (system / "System32").is_dir():
        raise BuildHeld("build_platform_closed")
    writable = (output, scratch, outcome)
    for root in writable:
        if (root.exists() or any(root.is_relative_to(p) or p.is_relative_to(root)
                                 for p in (source, vc, sdk, system)) or
                any(root != p and (root.is_relative_to(p) or p.is_relative_to(root)) for p in writable) or
                len(set(writable)) != 3):
            raise BuildHeld("build_output_invalid")
        safe_path(root, missing_leaf=True)
    outcome.mkdir()  # all three leaves are absent; no cleanup on partial failure
    # Reserve independent custody before tool launch. No output scan gates this write.
    with (outcome / "build.json").open("xb") as destination:
        reserved_handle = os.fstat(destination.fileno())
        reserved_path = (outcome / "build.json").stat()
        if identity(reserved_handle) != identity(reserved_path):
            raise BuildHeld("build_receipt_custody_uncertain")
        receipt = {"schema": "i01-build-capture-2", "source_commit": binding["source_commit"],
                   "source_hashes": binding["source_hashes"], "stages": [], "held": None,
                   "compiled_tests": "NOT_RUN", "abi_execution": "NOT_RUN",
                   "loaded_dependency_closure": "NOT_RUN", "runtime_authorized": False,
                   "artifact_success": False, "recipe_completed": False, "artifacts": None,
                   "artifact_snapshot_status": "NOT_AVAILABLE", "workspace": None}
        try:
            output.mkdir()
            scratch.mkdir()
            execute_recipe(source, output, scratch, vc, sdk, system, binding, receipt)
        except BuildHeld as error:
            receipt["held"] = error.args[0]
        except (OSError, ValueError, TypeError):
            receipt["held"] = "build_io_unavailable"
        receipt["workspace"] = observe_workspace(output, scratch)
        if receipt["workspace"]["held"] and receipt["held"] is None:
            receipt["held"] = receipt["workspace"]["held"]
        if receipt["held"]:
            receipt["artifacts"] = None
            receipt["recipe_completed"] = False
            receipt["artifact_snapshot_status"] = "NOT_AVAILABLE"
        raw = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode("ascii")
        if len(raw) > RECEIPT_CAP:
            # Never replace a held outcome with success. No raw exception/paths.
            raw = b'{"schema":"i01-build-capture-2","held":"build_receipt_exceeded","artifact_success":false,"runtime_authorized":false}'
            receipt["held"] = "build_receipt_exceeded"
        # Detect observable outcome replacement/modification before the single write.
        safe_path(outcome / "build.json")
        if (not same_metadata(reserved_path, (outcome / "build.json").stat()) or
                not same_metadata(reserved_handle, os.fstat(destination.fileno()))):
            raise BuildHeld("build_receipt_custody_uncertain")
        if os.fstat(destination.fileno()).st_size != 0:
            raise BuildHeld("build_receipt_custody_uncertain")
        destination.write(raw)
        destination.flush()
        os.fsync(destination.fileno())
    return 1 if receipt["held"] else 0


def execute_recipe(source, output, scratch, vc, sdk, system, binding, receipt):
    environment = {"SystemRoot": str(system), "TEMP": str(scratch), "TMP": str(scratch),
                   "PATH": str(vc / "bin/Hostx64/x64") + os.pathsep + str(system / "System32")}
    for index, args in enumerate(recipe(source, output, vc, sdk), 1):
        verify_inputs(source, vc, sdk, binding)
        targets = (("core.obj",), ("core.dll", "core.lib", "core.exp"), ("abi.obj",), ("abi.exe",))
        if any((output / name).exists() for name in targets[index - 1]):
            raise BuildHeld("build_artifact_exists")
        result = capture(args, output, environment, scratch=scratch)
        streams = result.pop("streams")
        result["stream_bytes"] = [len(b) for b in streams]
        result["stream_sha256"] = [hashlib.sha256(b).hexdigest() for b in streams]
        result["stream_hash_scope"] = "captured_prefix_if_held"
        receipt["stages"].append(result)
        if result["held"]:
            receipt["held"] = result["held"]
            return  # no writes/hash reads into rejected or potentially live tool roots
        check_workspace(output, scratch)
        for kind, data in zip(("stdout", "stderr"), streams, strict=True):
            write_new(output, f"stage{index}.{kind}", bytes(data), scratch=scratch)
    # Do not hash potentially still-mutating compiler output on any held stage.
    check_workspace(output, scratch)
    expected_artifacts = {"core.obj", "core.dll", "core.lib", "core.exp", "abi.obj", "abi.exe"}
    if not all(
            (output / name).is_file() for name in expected_artifacts):
        raise BuildHeld("build_artifacts_unavailable")
    artifacts = {}
    for name in sorted(expected_artifacts):
        path = output / name
        before = path.stat()
        digest = file_hash(path)
        if not same_metadata(before, path.stat()):
            raise BuildHeld("build_file_changed")
        artifacts[name] = {"bytes": before.st_size, "sha256": digest}
    receipt["artifacts"] = artifacts
    check_workspace(output, scratch)
    receipt["artifact_snapshot_status"] = "OBSERVED_NOT_DRAIN_PROVEN"
    receipt["recipe_completed"] = True  # NOT trusted artifact/native execution acceptance


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (*ROOT_KEYS, "approval", "approval-sha256"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    try:
        binding = approval(Path(args.approval), args.approval_sha256)
        return run(*(Path(getattr(args, name)) for name in ("source", "output", "vc", "sdk", "system")), binding,
                   scratch=Path(args.scratch), outcome=Path(args.outcome))
    except (BuildHeld, OSError, ValueError, TypeError, RecursionError):
        print("I01 build held; retain private output and request review", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
