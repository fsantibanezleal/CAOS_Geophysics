"""Bounded real-Git paired source builder; all writes are NEW temporary fixtures."""

import hashlib
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tarfile
import time
from types import SimpleNamespace
import zlib

import pytest

from scripts import ops_recovery as ops
from scripts import ops_source_bundle as bundle
from scripts import ops_source_pin as source


def git(root, *args, incoming=None):
    environment = bundle.clean_environment()
    environment.update({"GIT_AUTHOR_NAME": "Fixture Owner", "GIT_COMMITTER_NAME": "Fixture Owner",
        "GIT_AUTHOR_EMAIL": "fixture@example.invalid", "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
        "GIT_AUTHOR_DATE": "2026-10-03T00:00:00+00:00", "GIT_COMMITTER_DATE": "2026-10-03T00:00:00+00:00"})
    return subprocess.run([shutil.which("git"), *args], cwd=root, env=environment, input=incoming,
                          capture_output=True, check=True, timeout=30).stdout


def document(args, path, files=None):
    selected = {"schema": bundle.SELECTION_SCHEMA, "runtime_commit": args.runtime_commit, "ops_commit": args.ops_commit,
        "files": files or {scope: sorted(paths) for scope, paths in bundle.PATHS.items()}}
    path.write_bytes(ops.canonical(selected))
    args.selection, args.selection_sha256 = path, ops.sha_file(path, ops.JSON_CAP)
    return selected


@pytest.fixture(scope="module")
def pair(tmp_path_factory):
    root = tmp_path_factory.mktemp("paired-git")
    runtime, implementation = root / "runtime", root / "ops"
    for scope, repo in (("runtime", runtime), ("ops", implementation)):
        repo.mkdir()
        git(repo, "init", "-b", "fixture")
        for name in sorted(bundle.PATHS[scope]):
            path = repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"reviewed public fixture text\n" + name.encode() + b"\n")
        git(repo, "add", "--all")
        git(repo, "commit", "-m", "Fixture source")
    return SimpleNamespace(runtime_repo=runtime, ops_repo=implementation,
        runtime_commit=git(runtime, "rev-parse", "HEAD").decode().strip(),
        ops_commit=git(implementation, "rev-parse", "HEAD").decode().strip())


def arguments(pair, tmp_path):
    args = SimpleNamespace(**vars(pair), epoch=1790985600, new_output=tmp_path / "bundle")
    document(args, tmp_path / "selection.json")
    return args


@pytest.fixture(scope="module")
def built(pair, tmp_path_factory):
    root = tmp_path_factory.mktemp("built-pair")
    args = arguments(pair, root)
    receipt = bundle.build(args)
    return args, receipt


def test_committed_bytes_ignore_dirty_state(pair, tmp_path, built):
    args = arguments(pair, tmp_path)
    changed = pair.runtime_repo / "app/mt_contract.py"
    original = changed.read_bytes()
    sentinel = pair.runtime_repo / "never-include-identity.txt"
    sentinel.write_bytes(b"private fixture sentinel; not a real key")
    changed.write_bytes(b"uncommitted state must NEVER be bundled\n")
    absent = pair.runtime_repo / "app/mt_compute.py"
    original_absent = absent.read_bytes()
    absent.unlink()
    try:
        receipt = bundle.build(args)
        assert receipt["archive"] == built[1]["archive"]
        with tarfile.open(args.new_output / "selected-source.tar", "r:") as tar:
            assert tar.extractfile("runtime/app/mt_contract.py").read() == original
            assert tar.extractfile("runtime/app/mt_compute.py").read() == original_absent
            assert all("identity" not in item.name for item in tar)
        assert changed.read_bytes().startswith(b"uncommitted") and not absent.exists()
        assert sentinel.read_bytes() == b"private fixture sentinel; not a real key"
    finally:
        changed.write_bytes(original)
        absent.write_bytes(original_absent)


def test_deterministic_ustar(pair, tmp_path, built):
    args = arguments(pair, tmp_path)
    receipt = bundle.build(args)
    old = built[0].new_output
    assert (args.new_output / "selected-source.tar").read_bytes() == (old / "selected-source.tar").read_bytes()
    assert (args.new_output / "selected-source.json").read_bytes() == (old / "selected-source.json").read_bytes()
    assert receipt["source_only"] and not receipt["production_activated"] and not receipt["release_accepted"]
    with tarfile.open(args.new_output / "selected-source.tar", "r:") as tar:
        names = []
        for member in tar:
            names.append(member.name)
            assert member.type == tarfile.REGTYPE and not member.pax_headers and not member.linkname
            assert member.mode == 0o644 and member.uid == member.gid == 0 and member.mtime == args.epoch
            assert member.uname == member.gname == ""
        assert names == sorted(names) and len(names) == sum(len(paths) for paths in bundle.PATHS.values())


def test_paired_manifest_verifier_roundtrip(tmp_path, built):
    args, receipt = built
    manifest = ops.read_json(args.new_output / "selected-source.json")
    assert set(manifest) == {"schema", "runtime_commit", "ops_commit", "archive", "files"}
    runtime, implementation = tmp_path / "installed-runtime", tmp_path / "installed-ops"
    runtime.mkdir()
    implementation.mkdir()
    # Test-only install of validated fixed regular members into NEW fixtures; no utility extraction.
    with tarfile.open(args.new_output / "selected-source.tar", "r:") as tar:
        for member in tar:
            scope, name = member.name.split("/", 1)
            destination = (runtime if scope == "runtime" else implementation) / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("xb") as handle:
                handle.write(tar.extractfile(member).read())
    pinned = SimpleNamespace(source_manifest=args.new_output / "selected-source.json",
        source_manifest_sha256=receipt["manifest_sha256"], source_archive=args.new_output / "selected-source.tar", ops_commit=args.ops_commit)
    proof = source.verify(runtime, args.runtime_commit, pinned, implementation)
    assert proof["mode"] == "selected-archive"
    for scope, entries in receipt["files"].items():
        for name, entry in entries.items():
            assert entry["sha256"] == manifest["files"][scope][name]["sha256"]
            assert entry["tree_chain"][0]["tree_oid"] == receipt["commits"][scope]["tree"]
            assert entry["tree_chain"][-1]["oid"] == entry["oid"]
            raw = git(getattr(args, scope + "_repo"), "cat-file", "blob", entry["oid"])
            assert bundle.object_oid("blob", raw) == entry["oid"]


@pytest.mark.parametrize("case", ["schema", "field", "runtime_commit", "ops_commit", "hash", "missing", "extra",
    "unsorted", "duplicate", "case_alias", "traversal", "relative", "backslash", "native", "private", "raw", "edi_extra",
    "environment", "bytecode", "not_list", "non_string", "nonfinite", "duplicate_json", "count"])
def test_selection_policy(pair, tmp_path, monkeypatch, case):
    args = arguments(pair, tmp_path)
    selected = ops.read_json(args.selection)
    names = selected["files"]["runtime"]
    if case == "schema":
        selected["schema"] += "-unknown"
    elif case == "field":
        selected["override"] = True
    elif case in ("runtime_commit", "ops_commit"):
        selected[case] = "1" * 40
    elif case == "hash":
        args.selection_sha256 = "0" * 64
    elif case == "missing":
        names.pop()
    elif case == "extra":
        names.append("app/unreviewed.py")
    elif case == "unsorted":
        names.reverse()
    elif case == "duplicate":
        names.append(names[0])
    elif case == "case_alias":
        names.append(names[0].upper())
    elif case in ("traversal", "relative", "backslash", "native", "private", "raw", "edi_extra", "environment", "bytecode"):
        names.append({"traversal": "../private.key", "relative": "./app/auth.py", "backslash": "app\\auth.py",
            "native": "app/plugin.dll", "private": "app/recovery.key", "raw": "data/downloads/survey.edi",
            "edi_extra": "data/fixtures/edi/third-survey.edi", "environment": ".venv/python.exe", "bytecode": "app/__pycache__/auth.pyc"}[case])
        names.sort()
    elif case == "not_list":
        selected["files"]["runtime"] = {}
    elif case == "non_string":
        names[0] = True
    elif case == "count":
        monkeypatch.setattr(source, "COUNT_CAP", 2)
    encoded = ops.canonical(selected)
    if case == "nonfinite":
        encoded = encoded.replace(b'"files":', b'"invalid":NaN,"files":')
    elif case == "duplicate_json":
        encoded = encoded.replace(b'"schema":', b'"schema":"duplicate","schema":')
    args.selection.write_bytes(encoded)
    if case != "hash":
        args.selection_sha256 = ops.sha_file(args.selection, ops.JSON_CAP)
    with pytest.raises((ops.RecoveryError, ValueError)):
        bundle.build(args)
    assert not args.new_output.exists()


def selected_commit(args, path, mode=None, body=None):
    if body is not None:
        oid = git(args.runtime_repo, "hash-object", "-w", "--stdin", incoming=body).decode().strip()
    else:
        oid = args.runtime_commit
    git(args.runtime_repo, "update-index", "--cacheinfo", f"{mode or '100644'},{oid},{path}")
    git(args.runtime_repo, "commit", "-m", "Hostile temporary selected object")
    args.runtime_commit = git(args.runtime_repo, "rev-parse", "HEAD").decode().strip()


@pytest.mark.parametrize("case", ["symlink", "submodule", "missing_commit", "tag", "short_sha", "uppercase_sha",
    "missing_blob", "corrupt_blob", "hardlinked_blob", "partial", "promisor", "alternates", "subdirectory"])
def test_object_identity_guards(pair, tmp_path, case):
    args = arguments(pair, tmp_path)
    selected = "app/mt_contract.py"
    old_oid = git(pair.runtime_repo, "rev-parse", pair.runtime_commit + ":" + selected).decode().strip()
    restore = None
    try:
        if case == "symlink":
            selected_commit(args, selected, "120000", b"../unrelated")
        elif case == "submodule":
            selected_commit(args, selected, "160000")
        elif case == "missing_commit":
            args.runtime_commit = "0" * 40
        elif case == "tag":
            git(pair.runtime_repo, "tag", "-a", "fixture-tag", "-m", "Temporary tag", pair.runtime_commit)
            args.runtime_commit = git(pair.runtime_repo, "rev-parse", "fixture-tag").decode().strip()
        elif case == "short_sha":
            args.runtime_commit = args.runtime_commit[:7]
        elif case == "uppercase_sha":
            args.runtime_commit = args.runtime_commit.upper()
        elif case in ("missing_blob", "corrupt_blob"):
            loose = pair.runtime_repo / ".git/objects" / old_oid[:2] / old_oid[2:]
            original = loose.read_bytes()
            restore = (loose, original)
            loose.chmod(stat.S_IREAD | stat.S_IWRITE)  # ONLY a disposable external fixture Git object.
            loose.unlink() if case == "missing_blob" else loose.write_bytes(zlib.compress(b"blob 7\0altered"))
        elif case == "partial":
            git(pair.runtime_repo, "config", "extensions.partialclone", "never-fetch-fixture")
        elif case == "hardlinked_blob":
            loose = pair.runtime_repo / ".git/objects" / old_oid[:2] / old_oid[2:]
            os.link(loose, tmp_path / "fixture-object-alias")
        elif case == "promisor":
            (pair.runtime_repo / ".git/objects/pack/fixture.promisor").write_bytes(b"")
        elif case == "alternates":
            (pair.runtime_repo / ".git/objects/info/alternates").write_bytes(b"untrusted-alternate")
        elif case == "subdirectory":
            args.runtime_repo = pair.runtime_repo / "app"
        document(args, args.selection)
        with pytest.raises(ops.RecoveryError, match="hardlinked_path" if case == "hardlinked_blob" else None):
            bundle.build(args)
        assert not args.new_output.exists()
    finally:
        if restore:
            restore[0].write_bytes(restore[1])
        if case == "partial":
            git(pair.runtime_repo, "config", "--unset", "extensions.partialclone")
        if case == "hardlinked_blob":
            (tmp_path / "fixture-object-alias").unlink()
        if case == "promisor":
            (pair.runtime_repo / ".git/objects/pack/fixture.promisor").unlink()
        if case == "alternates":
            (pair.runtime_repo / ".git/objects/info/alternates").unlink()
        if case in ("symlink", "submodule"):
            git(pair.runtime_repo, "update-index", "--cacheinfo", f"100644,{old_oid},{selected}")
            git(pair.runtime_repo, "commit", "-m", "Restore temporary fixture index")


@pytest.mark.parametrize("body", [b"MZnative", b"\x7fELFnative", b"SQLite format 3\0", b"PK\x03\x04archive",
    b"version https://git-lfs.github.com/spec/v1\noid sha256:0000\n", b"AGE-SECRET-KEY-1" + b"X" * 58,
    b"-----BEGIN PRIVATE KEY-----\nnot a real key\n", b"text\0binary", b"\xffnot utf8"])
def test_forbidden_committed_content(pair, tmp_path, body):
    args = arguments(pair, tmp_path)
    selected = "app/mt_contract.py"
    old_oid = git(pair.runtime_repo, "rev-parse", pair.runtime_commit + ":" + selected).decode().strip()
    try:
        selected_commit(args, selected, body=body)
        document(args, args.selection)
        with pytest.raises((ops.RecoveryError, UnicodeError)):
            bundle.build(args)
        assert not args.new_output.exists()
    finally:
        git(pair.runtime_repo, "update-index", "--cacheinfo", f"100644,{old_oid},{selected}")
        git(pair.runtime_repo, "commit", "-m", "Restore public fixture object")


@pytest.mark.parametrize("case", ["existing", "linked", "overlap", "selection_inside_repo", "epoch_bool", "epoch_negative",
    "epoch_large", "file_cap", "total_cap", "archive_cap", "deadline", "receipt_failure"])
def test_output_and_resource_guards(pair, tmp_path, monkeypatch, case):
    args = arguments(pair, tmp_path)
    if case == "existing":
        args.new_output.mkdir()
        (args.new_output / "preserve").write_bytes(b"existing user fixture")
    elif case == "linked":
        destination = tmp_path / "destination"
        destination.mkdir()
        try:
            args.new_output.symlink_to(destination, target_is_directory=True)
        except OSError:
            pytest.skip("Ordinary symlink privilege unavailable")
    elif case == "overlap":
        args.new_output = pair.runtime_repo / "never-create"
    elif case == "selection_inside_repo":
        document(args, pair.runtime_repo / "never-selected.json")
    elif case.startswith("epoch"):
        args.epoch = {"epoch_bool": True, "epoch_negative": -1, "epoch_large": 2147483648}[case]
    elif case == "file_cap":
        monkeypatch.setattr(source, "FILE_CAP", 1)
    elif case == "total_cap":
        monkeypatch.setattr(source, "TOTAL_CAP", 1)
    elif case == "archive_cap":
        monkeypatch.setattr(source, "ARCHIVE_CAP", 1)
    elif case == "deadline":
        monkeypatch.setattr(bundle, "BUILD_SECONDS", 0)
    elif case == "receipt_failure":
        real_sync = ops.sync_dir
        def sync(path):
            if (path / "build-receipt.json").exists():
                raise OSError("controlled final directory flush failure")
            real_sync(path)
        monkeypatch.setattr(ops, "sync_dir", sync)
    with pytest.raises((ops.RecoveryError, OSError)):
        bundle.build(args)
    assert not (args.new_output / "build-receipt.json").exists()
    if case == "existing":
        assert (args.new_output / "preserve").read_bytes() == b"existing user fixture"
    elif case == "linked":
        assert args.new_output.is_symlink() and list(destination.iterdir()) == []
    elif case in ("archive_cap", "receipt_failure"):
        assert args.new_output.exists()  # Precisely NEW diagnostic output is retained, never swept.
    else:
        assert not args.new_output.exists()


@pytest.mark.parametrize("case", ["stdout", "stderr", "timeout", "success"])
def test_process_caps(tmp_path, monkeypatch, case):
    command = [sys.executable, "-B", "-c", "print('safe')"]
    if case in ("stdout", "stderr"):
        command[-1] = f"import sys; sys.{case}.write('x'*20000)"
    elif case == "timeout":
        command[-1] = "import time; time.sleep(2)"
        monkeypatch.setattr(bundle, "COMMAND_SECONDS", .05)
    if case == "success":
        assert bundle.bounded_command(command, cwd=tmp_path, cap=100, deadline=time.monotonic() + 10).strip() == b"safe"
    else:
        with pytest.raises(ops.RecoveryError, match="source_command_"):
            bundle.bounded_command(command, cwd=tmp_path, cap=100, deadline=time.monotonic() + 10)


def test_readonly_repositories(pair, tmp_path, monkeypatch, built):
    args = arguments(pair, tmp_path)
    snapshot = {path: path.read_bytes() for root in (pair.runtime_repo, pair.ops_repo)
                for path in root.rglob("*") if path.is_file()}
    original = bundle.bounded_command
    calls = []
    def observed(command, **kwargs):
        calls.append(command)
        return original(command, **kwargs)
    monkeypatch.setattr(bundle, "bounded_command", observed)
    for name, value in {"GIT_DIR": str(tmp_path / "wrong"), "GIT_WORK_TREE": str(tmp_path / "wrong"),
        "GIT_OBJECT_DIRECTORY": str(tmp_path / "wrong"), "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(tmp_path / "wrong"),
        "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "remote.fake.promisor", "GIT_CONFIG_VALUE_0": "true",
        "GIT_TRACE": str(tmp_path / "never-write-trace"), "GIT_REPLACE_REF_BASE": "refs/unknown"}.items():
        monkeypatch.setenv(name, value)
    receipt = bundle.build(args)
    assert receipt["archive"] == built[1]["archive"] and not (tmp_path / "never-write-trace").exists()
    assert all(path.read_bytes() == encoded for path, encoded in snapshot.items())
    assert all(not any(arg in {"fetch", "clone", "checkout", "reset", "archive", "--filters", "--textconv", "--global", "-w"}
                       for arg in command[1:]) for command in calls)
    assert all("--no-lazy-fetch" in command and "--no-replace-objects" in command for command in calls)


def test_replace_objects_disabled(pair, tmp_path, built):
    args = arguments(pair, tmp_path)
    original_oid = git(pair.runtime_repo, "rev-parse", pair.runtime_commit + ":app/mt_contract.py").decode().strip()
    replacement = git(pair.runtime_repo, "hash-object", "-w", "--stdin", incoming=b"must not replace selected source").decode().strip()
    git(pair.runtime_repo, "replace", original_oid, replacement)
    try:
        assert bundle.build(args)["archive"] == built[1]["archive"]
    finally:
        git(pair.runtime_repo, "replace", "-d", original_oid)


def test_installed_tool_hardlink_exception_is_not_source_admission(tmp_path, monkeypatch):
    binary = tmp_path / "installed-git"
    binary.write_bytes(b"trusted fixture executable metadata only")
    os.link(binary, tmp_path / "installed-tool-alias")
    monkeypatch.setattr(bundle.shutil, "which", lambda name: str(binary))
    assert bundle.trusted_git_tool() == (binary, hashlib.sha256(binary.read_bytes()).hexdigest(), 2)
    with pytest.raises(ops.RecoveryError, match="hardlinked_path"):
        ops.safe_path(binary, outside_repo=False)


def test_receipt_publication_never_overwrites_racing_file(tmp_path, monkeypatch):
    original = ops.safe_path
    final = tmp_path / "build-receipt.json"
    def guarded(path, **kwargs):
        result = original(path, **kwargs)
        if path == final:
            final.write_bytes(b"other writer sentinel")
        return result
    monkeypatch.setattr(ops, "safe_path", guarded)
    with pytest.raises(FileExistsError):
        bundle.completed_receipt(tmp_path, {"completed": True})
    assert final.read_bytes() == b"other writer sentinel"
    assert (tmp_path / "build-receipt.pending.json").exists()


def test_builder_guide():
    guide = (Path(__file__).parents[2] / "docs/operations/03_paired_source_bundle.md").read_text()
    for text in ("git-scm.com/docs/git-cat-file", "Git-blob", "--epoch", "--selection-sha256", "NOT RUN",
                 "30%", "no safe.directory", "source-only", "PAX", "two public EDI", "not production trust"):
        assert text.casefold() in guide.casefold()


def test_actual_committed_pair_api_fixture(tmp_path):
    """Opt-in real reviewed Git pair -> verifier -> actual API producer, never a host drill."""
    selected = os.environ.get("GEOPHYSICS_OPS_MT_CHECKOUT")
    if not selected:
        pytest.skip("Explicit pinned read-only MT checkout required")
    runtime_repo = Path(selected).resolve(strict=True)
    implementation = Path(__file__).parents[2]
    commits = SimpleNamespace(runtime_repo=runtime_repo, ops_repo=implementation,
        runtime_commit=git(runtime_repo, "rev-parse", "HEAD").decode().strip(), ops_commit="5bc20eb3253c88c0cd903ccf06fc42aeb2a26b77")
    args = arguments(commits, tmp_path)
    actual_app = set(git(runtime_repo, "ls-tree", "-r", "--name-only", args.runtime_commit, "--", "app").decode().splitlines())
    assert actual_app == {name for name in bundle.PATHS["runtime"] if name.startswith("app/")}
    receipt = bundle.build(args)
    manifest = ops.read_json(args.new_output / "selected-source.json")
    installed = {scope: tmp_path / ("installed-" + scope) for scope in bundle.PATHS}
    for root in installed.values():
        root.mkdir()
    with tarfile.open(args.new_output / "selected-source.tar", "r:") as tar:
        for member in tar:
            scope, name = member.name.split("/", 1)
            target = installed[scope] / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(tar.extractfile(member).read())
    pin_args = SimpleNamespace(source_manifest=args.new_output / "selected-source.json", source_manifest_sha256=receipt["manifest_sha256"],
        source_archive=args.new_output / "selected-source.tar", ops_commit=args.ops_commit)
    source.verify(installed["runtime"], args.runtime_commit, pin_args, installed["ops"])
    state = tmp_path / "state"
    environment = bundle.clean_environment()
    def call(mode):
        return subprocess.run([sys.executable, "-B", str(installed["ops"] / "tests/ops/mt_drill.py"), mode,
            "--runtime-commit", args.runtime_commit, *source.source_options(pin_args), str(installed["runtime"]), str(state)],
            cwd=installed["runtime"], env=environment, capture_output=True, timeout=300)
    prepared = call("--prepare-state")
    assert prepared.returncode == 0, prepared.stderr.decode(errors="replace")[-4000:]
    assert len(ops.read_json(state / "fixture-state.json")["files"]) == 11
    deleted = call("--delete-fixture-project")
    assert deleted.returncode == 0, deleted.stderr.decode(errors="replace")[-4000:]
    assert len(ops.read_json(state / "fixture-deletion.json")["files"]) == 7
    assert manifest["archive"] == receipt["archive"] and not list(state.rglob("*.age"))
