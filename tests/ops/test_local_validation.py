"""Authored orchestration controls plus actual local process-custody negatives."""

import ctypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_local.py"
spec = importlib.util.spec_from_file_location("local_validation", SCRIPT)
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)


@pytest.fixture
def case(tmp_path):
    root = tmp_path.resolve()
    scratch = root / "scratch"
    scratch.mkdir()
    source = root / "command.py"
    source.write_text("import os\nfrom pathlib import Path\np=Path(os.environ['COUNTER'])\np.write_text(p.read_text()+'x' if p.exists() else 'x')\nraise SystemExit(int(os.environ.get('EXIT','0')))\n")
    data = root / "input.txt"
    data.write_text("original input")
    env = {"TMP": str(scratch), "TEMP": str(scratch), "TMPDIR": str(scratch),
           "COUNTER": str(root / "counter.txt"), "PYTHONDONTWRITEBYTECODE": "1"}
    for key in ("SystemRoot", "PATH", "LANG"):
        if key in os.environ:
            env[key] = os.environ[key]
    if os.name == "nt":
        env["SystemDrive"] = Path(env["SystemRoot"]).drive
        env["windir"] = env["SystemRoot"]
    for key in ("HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "ProgramData"):
        env[key] = str(scratch)
    node = {"id": "first", "argv": [str(Path(sys.executable).resolve()), "-B", str(source)], "cwd": str(root),
            "sources": [str(source)], "inputs": [str(data)], "env": env,
            "timeout_s": 10, "log_bytes": 65536, "needs": []}
    return root, node


def config(case, nodes=None):
    root, node = case
    path = root / "dag.json"
    path.write_text(json.dumps({"schema": 1, "nodes": nodes or [node]}))
    return path


def run(case, nodes=None):
    root, _ = case
    return harness.run(str(config(case, nodes)), str(root), str(root / "cache"), str(root / "reports"))


def test_unchanged_failure_runs_once(case):
    root, node = case
    node["env"]["EXIT"] = "7"
    first, second = run(case), run(case)
    assert first["nodes"][0]["status"] == second["nodes"][0]["status"] == "FAIL"
    assert first["nodes"][0]["action"] == "started"
    assert second["nodes"][0]["action"] == "reused"
    assert first["nodes"][0]["evidence"] == second["nodes"][0]["evidence"]
    assert (root / "counter.txt").read_text() == "x"


@pytest.mark.parametrize("change", ["source", "input", "executable", "env", "directory_member", "dispatcher_image"])
def test_exact_binding_changes_invalidate(case, change, monkeypatch):
    root, node = case
    if change == "directory_member":
        closure = root / "closure"
        closure.mkdir()
        (closure / "one.txt").write_text("one")
        node["inputs"] = [str(closure)]
    if change == "executable":
        original = Path(os.environ["VALIDATION_COPYABLE_PYTHON"]) if os.name == "nt" else Path(sys.executable).resolve()
        copied = root / ("copied-python.exe" if os.name == "nt" else "copied-python")
        shutil.copyfile(original.resolve(), copied)
        copied.chmod(0o755)
        node["argv"][0] = str(copied)
        python_home = original.parent if os.name == "nt" else Path(sys.base_prefix)
        node["env"]["PYTHONHOME"] = str(python_home)
        node["env"]["PATH"] = str(python_home) + os.pathsep + node["env"].get("PATH", "")
    if change == "dispatcher_image":
        # Actual image bytes, separately bound from the sys.executable redirector.
        original_image = harness.dispatcher_image()
        copied_image = root / "base-image.exe"
        shutil.copyfile(original_image, copied_image)
        monkeypatch.setattr(harness, "dispatcher_image", lambda: copied_image)
        original_execute = harness.execute
        def execute_with_original_image(n, e, c):
            # Native mutation test separately executes a changed executable;
            # this regression isolates fingerprint selection without replacing
            # the bootstrap's stdlib or importing an unrelated interpreter.
            with monkeypatch.context() as active:
                active.setattr(harness, "dispatcher_image", lambda: original_image)
                return original_execute(n, e, c)
        monkeypatch.setattr(harness, "execute", execute_with_original_image)
    first = run(case)
    assert first["nodes"][0]["status"] == "PASS"
    if change in {"source", "input"}:
        with Path(node["sources" if change == "source" else "inputs"][0]).open("a") as stream:
            stream.write("\n# changed" if change == "source" else " changed")
    elif change == "env":
        node["env"]["EXPLICIT_BINDING"] = "changed"
    elif change == "directory_member":
        (closure / "two.txt").write_text("two")
    elif change == "executable":
        with copied.open("ab") as stream:
            stream.write(b"changed executable trailer")
    else:
        with copied_image.open("ab") as stream:
            stream.write(b"changed actual base runtime image")
    second = run(case)
    assert second["nodes"][0]["status"] == "PASS"
    assert second["nodes"][0]["action"] == "started"
    assert first["nodes"][0]["fingerprint"] != second["nodes"][0]["fingerprint"]
    assert (root / "counter.txt").read_text() == "xx"


def test_blocked_descendants_independent_continue(case):
    root, first = case
    first["env"]["EXIT"] = "1"
    child = {**first, "id": "child", "needs": ["first"], "env": {**first["env"], "EXIT": "0", "COUNTER": str(root / "child.txt")}}
    independent = {**child, "id": "independent", "needs": [], "env": {**child["env"], "COUNTER": str(root / "other.txt")}}
    result = run(case, [first, child, independent])["nodes"]
    assert [r["status"] for r in result] == ["FAIL", "BLOCKED", "PASS"]
    assert not (root / "child.txt").exists()
    assert (root / "other.txt").read_text() == "x"


def test_cached_pass_does_not_materialize_outputs(case):
    root, node = case
    first = run(case)
    artifact = root / "counter.txt"
    artifact.unlink()
    reused = run(case)
    assert first["nodes"][0]["status"] == reused["nodes"][0]["status"] == "PASS"
    assert reused["nodes"][0]["action"] == "reused"
    assert not artifact.exists()
    consumer = {**node, "id": "consumer", "needs": ["first"], "inputs": [str(artifact)]}
    with pytest.raises(harness.Refusal, match="missing path"):
        run(case, [node, consumer])
    assert not artifact.exists()


def test_predecessor_evidence_in_fingerprint(case):
    root, first = case
    child = {**first, "id": "child", "needs": ["first"], "env": {**first["env"], "COUNTER": str(root / "child.txt")}}
    initial = run(case, [first, child])
    first["env"]["CHANGED"] = "1"
    later = run(case, [first, child])
    assert all(row["action"] == "started" for row in later["nodes"])
    assert initial["nodes"][1]["fingerprint"] != later["nodes"][1]["fingerprint"]
    assert (root / "child.txt").read_text() == "xx"


@pytest.mark.parametrize("bad", ["cycle", "missing", "late_source", "duplicate", "unknown_field", "nonfinite", "shell"])
def test_all_preflight_before_any_spawn(case, bad):
    root, first = case
    second = {**first, "id": "second"}
    if bad == "cycle":
        first["needs"], second["needs"] = ["second"], ["first"]
    elif bad == "missing":
        second["needs"] = ["absent"]
    elif bad == "late_source":
        second["sources"] = [str(root / "absent.py")]
    elif bad == "duplicate":
        second["id"] = "first"
    elif bad == "unknown_field":
        second["shell"] = False
    elif bad == "nonfinite":
        second["timeout_s"] = float("inf")
    else:
        shell = root / "unsafe.cmd"
        shell.write_text("echo unsafe")
        second["argv"] = [str(shell)]
    with pytest.raises(harness.Refusal):
        run(case, [first, second])
    assert not (root / "counter.txt").exists()
    assert not (root / "cache").exists()


@pytest.mark.parametrize("field", ["sources", "inputs"])
def test_later_missing_declaration_refuses_before_hashing(case, field, monkeypatch):
    root, first = case
    second = {**first, "id": "second", field: [str(root / "absent.txt")]}

    def unexpected_snapshot(_):
        raise AssertionError("structural refusal must precede expensive hashing")

    monkeypatch.setattr(harness, "snapshot", unexpected_snapshot)
    with pytest.raises(harness.Refusal, match="missing path"):
        run(case, [first, second])
    assert not (root / "counter.txt").exists()
    assert not (root / "cache").exists()


@pytest.mark.parametrize("bad", ["stdout", "receipt", "seal", "missing_receipt", "unknown_file"])
def test_changed_or_incomplete_cache_refused(case, bad):
    root, _ = case
    original = run(case)
    entry = Path(original["nodes"][0]["receipt"]).parent
    if bad == "missing_receipt":
        (entry / "receipt.json").unlink()
    elif bad == "unknown_file":
        (entry / "extra.txt").write_text("unknown")
    else:
        path = entry / {"stdout": "stdout.bin", "receipt": "receipt.json", "seal": "seal.json"}[bad]
        path.write_bytes(b"changed")
    result = run(case)
    assert result["nodes"][0]["status"] == "REFUSED"
    assert (root / "counter.txt").read_text() == "x"


def test_interruption_plan_cannot_become_success(case):
    root, node = case
    plan = {"base": harness.snapshot(node), "predecessors": {}}
    entry = root / "cache" / harness.digest(harness.canonical(plan))
    entry.mkdir(parents=True)
    (entry / "plan.json").write_bytes(harness.canonical(plan))
    result = run(case)
    assert result["nodes"][0]["status"] == "REFUSED"
    assert not (root / "counter.txt").exists()


def test_unknown_live_lock_refuses(case):
    root, _ = case
    (root / "cache").mkdir()
    lock = root / "cache" / "dispatcher.lock"
    lock.write_text("unknown owner")
    with pytest.raises(harness.Refusal, match="lock"):
        run(case)
    assert lock.read_text() == "unknown owner"
    assert not (root / "counter.txt").exists()


def test_live_lock_refuses_before_expensive_inventory(case, monkeypatch):
    root, _ = case
    (root / "cache").mkdir()
    lock = root / "cache" / "dispatcher.lock"
    lock.write_text("unknown owner")
    monkeypatch.setattr(harness, "inventory", lambda _: pytest.fail("live owner must precede hashing"))
    with pytest.raises(harness.Refusal, match="lock"):
        run(case)
    assert lock.read_text() == "unknown owner"
    assert not (root / "counter.txt").exists()


def test_identical_preflight_inventories_are_shared_but_every_later_snapshot_is_fresh(case, monkeypatch):
    root, node = case
    second = json.loads(harness.canonical(node))
    second["id"] = "second"
    second["needs"] = ["first"]
    calls = []
    original = harness.inventory

    def counted(paths):
        calls.append(tuple(paths))
        return original(paths)

    monkeypatch.setattr(harness, "inventory", counted)
    indexed, order, bases = harness.declaration({"schema": 1, "nodes": [node, second]}, root)
    assert order == ["first", "second"]
    assert calls == [tuple(node["sources"]), tuple(node["inputs"])]
    assert bases["first"]["sources"] == bases["second"]["sources"]
    assert bases["first"]["inputs"] == bases["second"]["inputs"]
    assert bases["first"]["sources"] is not bases["second"]["sources"]
    assert bases["first"]["inputs"] is not bases["second"]["inputs"]
    source = Path(node["sources"][0])
    source.write_text(source.read_text() + "\n# independent later change\n")
    fresh = harness.snapshot(indexed["first"])
    assert len(calls) == 4
    assert fresh["sources"] != bases["first"]["sources"]
    harness.snapshot(indexed["second"])
    assert len(calls) == 6
    _, _, next_bases = harness.declaration({"schema": 1, "nodes": [node, second]}, root)
    assert len(calls) == 8
    assert next_bases["first"]["sources"] == fresh["sources"]


def test_preflight_refusal_releases_only_its_own_dispatcher_lock(case, monkeypatch):
    root, _ = case
    def refused(_):
        raise harness.Refusal("authored inventory refusal")
    monkeypatch.setattr(harness, "inventory", refused)
    with pytest.raises(harness.Refusal, match="authored inventory refusal"):
        run(case)
    assert (root / "cache").exists()
    assert not (root / "cache" / "dispatcher.lock").exists()
    assert not (root / "counter.txt").exists()


def test_report_allocation_failure_releases_owned_lock(case, monkeypatch):
    root, _ = case
    original = Path.mkdir
    def failing_mkdir(path, *args, **kwargs):
        if path.parent == root / "reports":
            raise OSError("authored report allocation failure")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "mkdir", failing_mkdir)
    with pytest.raises(OSError, match="allocation"):
        run(case)
    assert not (root / "cache" / "dispatcher.lock").exists()
    assert not (root / "counter.txt").exists()


@pytest.mark.parametrize("bad", ["repository", "outside_device", "relative", "system_temp"])
def test_external_paths_checked(case, bad):
    root, node = case
    if bad == "repository":
        (root / ".git").write_text("gitdir: nowhere")
    elif bad == "outside_device":
        node["env"]["TMP"] = str(root.parent)
    elif bad == "relative":
        node["env"]["TMPDIR"] = "relative"
    else:
        node["env"]["TEMP"] = os.environ.get("LOCALAPPDATA", "") + "/Temp" if os.name == "nt" else "/tmp"
    with pytest.raises(harness.Refusal):
        run(case)


def test_log_overflow_failed_and_reused(case):
    root, node = case
    Path(node["sources"][0]).write_text("import os\nwhile True: os.write(1,b'x'*8192)\n")
    node["log_bytes"] = 1024
    first, second = run(case), run(case)
    row = first["nodes"][0]
    assert row["status"] == "FAIL" and row["reason"] == "log_limit"
    assert second["nodes"][0]["action"] == "reused"
    entry = Path(row["receipt"]).parent
    assert sum((entry / n).stat().st_size for n in ("stdout.bin", "stderr.bin")) == 1024


def descendants(case):
    root, node = case
    source = Path(node["sources"][0])
    source.write_text("import os,sys,time,subprocess\nfrom pathlib import Path\nlevel=int(sys.argv[1]) if len(sys.argv)>1 else 0\nPath(os.environ['PIDS']+str(level)).write_text(str(os.getpid()))\nif level<2: subprocess.Popen([sys.executable,'-B',__file__,str(level+1)])\nwhile True: time.sleep(.1)\n")
    node["env"]["PIDS"] = str(root / "pid-")
    node["timeout_s"] = 3
    return root, node


def alive(pid):
    if os.name == "nt":
        api = ctypes.WinDLL("kernel32", use_last_error=True)
        api.OpenProcess.argtypes, api.OpenProcess.restype = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32], ctypes.c_void_p
        api.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        api.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = api.OpenProcess(0x100000, False, pid)
        if not handle:
            return False
        try:
            return api.WaitForSingleObject(handle, 0) == 258
        finally:
            api.CloseHandle(handle)
    path = Path(f"/proc/{pid}/stat")
    if path.exists():
        return path.read_text().rsplit(")", 1)[1].split()[0] != "Z"
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def assert_extinct(root):
    paths = [root / f"pid-{i}" for i in range(3)]
    assert all(p.exists() for p in paths), "actual command, child and grandchild must all have started"
    pids = [int(p.read_text()) for p in paths]
    deadline = time.monotonic() + 8
    while any(alive(pid) for pid in pids) and time.monotonic() < deadline:
        time.sleep(.02)
    assert not any(alive(pid) for pid in pids)


def test_actual_child_grandchild_timeout(case):
    root, _ = descendants(case)
    result = run(case)
    assert result["nodes"][0]["status"] == "FAIL"
    assert result["nodes"][0]["reason"] == "timeout"
    assert_extinct(root)


@pytest.mark.parametrize("action", ["parent_death", "cancel"])
def test_actual_parent_death_and_cancel(case, action, monkeypatch):
    root, node = descendants(case)
    node["timeout_s"] = 30
    if action == "cancel" and os.name == "nt":
        original = harness.execute
        cancelled = threading.Event()

        def cancel_when_descendants_started():
            deadline = time.monotonic() + 10
            while not (root / "pid-2").exists() and time.monotonic() < deadline:
                time.sleep(.02)
            cancelled.set()

        thread = threading.Thread(target=cancel_when_descendants_started)
        thread.start()
        monkeypatch.setattr(harness, "execute", lambda n, e, _: original(n, e, cancelled))
        result = run(case)
        thread.join(timeout=12)
        assert result["nodes"][0]["status"] == "FAIL"
        assert result["nodes"][0]["reason"] == "cancelled"
        assert_extinct(root)
        assert run(case)["nodes"][0]["action"] == "reused"
        return
    env = {**node["env"]}
    proc = subprocess.Popen([sys.executable, "-B", str(SCRIPT), "--config", str(config(case)),
                             "--device-root", str(root), "--cache-root", str(root / "cache"),
                             "--report-root", str(root / "reports")], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 10
        while not (root / "pid-2").exists() and time.monotonic() < deadline:
            time.sleep(.02)
        assert (root / "pid-2").exists()
        if action == "cancel" and os.name != "nt":
            proc.send_signal(__import__("signal").SIGTERM)
        else:
            # Kill the ACTUAL dispatcher, not a venv/Store launcher proxy PID.
            dispatcher = json.loads((root / "cache" / "dispatcher.lock").read_text())["pid"]
            os.kill(dispatcher, __import__("signal").SIGTERM if os.name == "nt" else __import__("signal").SIGKILL)
        proc.communicate(timeout=15)
        assert_extinct(root)
        if action == "parent_death":
            with pytest.raises(harness.Refusal, match="lock"):
                run(case)
        else:
            assert run(case)["nodes"][0]["status"] == "FAIL"
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.communicate(timeout=15)


@pytest.mark.skipif(os.name != "nt", reason="Windows native assignment gate")
def test_windows_assignment_failure_cannot_execute(case, monkeypatch):
    root, _ = case
    monkeypatch.setattr(harness.WindowsJob, "assign", lambda *_: harness.require(False, "test assignment refusal"))
    result = run(case)
    assert result["nodes"][0]["status"] == "REFUSED"
    assert not (root / "counter.txt").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows activation selector boundary")
def test_windows_activation_selector_refused_before_spawn(case):
    root, node = case
    copied = root / "python.exe"
    shutil.copyfile(node["argv"][0], copied)
    (root / "pyvenv.cfg").write_text("home = " + str(root / "WindowsApps" / "activation") + "\n")
    node["argv"][0] = str(copied)
    with pytest.raises(harness.Refusal, match="activation"):
        run(case)
    assert not (root / "counter.txt").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows native venv base selector")
def test_windows_redirector_base_image_hash_changes(case):
    root, _ = case
    scripts, base = root / "venv" / "Scripts", root / "base"
    scripts.mkdir(parents=True)
    base.mkdir()
    image = base / "python.exe"
    shutil.copyfile(harness.dispatcher_image(), image)
    (scripts.parent / "pyvenv.cfg").write_text("home = " + str(base) + "\n")
    # Pure selector regression, not a claim that these authored venv bytes ran.
    first = harness.runtime_selector(scripts / "python.exe")
    with image.open("ab") as stream:
        stream.write(b"changed base interpreter")
    later = harness.runtime_selector(scripts / "python.exe")
    assert first["configuration"] == later["configuration"]
    assert first["base_image"]["sha256"] != later["base_image"]["sha256"]


def test_closed_schema_rejects_boolean(case):
    root, node = case
    path = root / "boolean-schema.json"
    path.write_text(json.dumps({"schema": True, "nodes": [node]}))
    with pytest.raises(harness.Refusal, match="schema"):
        harness.run(str(path), str(root), str(root / "cache"), str(root / "reports"))
    assert not (root / "counter.txt").exists()


def test_directory_inventory_exact_bytes_without_per_file_resolution(case, monkeypatch):
    root, _ = case
    closure = root / "many-files"
    closure.mkdir()
    (closure / "empty").mkdir()
    for index in range(128):
        directory = closure / str(index % 8)
        directory.mkdir(exist_ok=True)
        (directory / f"{index}.txt").write_bytes(str(index).encode())
    expected, byte_count = {}, 0
    for path in closure.rglob("*"):
        if path.is_dir():
            expected[path.relative_to(closure).as_posix()] = None
        else:
            body = path.read_bytes()
            expected[path.relative_to(closure).as_posix()] = {
                "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}
            byte_count += len(body)
    calls, original = [], harness.absolute

    def observed(value, exists=True):
        calls.append(value)
        return original(value, exists)

    monkeypatch.setattr(harness, "absolute", observed)
    inventory = harness.inventory([str(closure)])
    assert calls == [str(closure)]
    assert inventory[str(closure)] == {
        "inventory_sha256": hashlib.sha256(harness.canonical(expected)).hexdigest(),
        "member_count": len(expected), "bytes": byte_count}


def test_directory_membership_change_during_hash_refused(case, monkeypatch):
    root, _ = case
    closure = root / "changing"
    closure.mkdir()
    (closure / "first.txt").write_bytes(b"first")
    original = harness.file_record
    changed = False

    def mutate(path):
        nonlocal changed
        record = original(path)
        if not changed:
            (closure / "late.txt").write_bytes(b"late member")
            changed = True
        return record

    monkeypatch.setattr(harness, "file_record", mutate)
    with pytest.raises(harness.Refusal, match="directory changed during hash"):
        harness.inventory([str(closure)])


def test_recursive_reparse_directory_refused(case, monkeypatch):
    root, _ = case
    closure = root / "parent"
    nested = closure / "linked"
    nested.mkdir(parents=True)
    original = Path.lstat

    def reparse(path):
        info = original(path)
        if path == nested:
            return SimpleNamespace(st_mode=info.st_mode, st_file_attributes=0x400)
        return info

    monkeypatch.setattr(Path, "lstat", reparse)
    with pytest.raises(harness.Refusal, match="linked path"):
        harness.inventory([str(closure)])
