"""Exact independently pinned selected source; all mutations are temporary fixtures."""

import io
import tarfile
from types import SimpleNamespace

import pytest

from scripts import ops_recovery as ops
from scripts import ops_source_pin as source


def seal_bundle(root, runtime, implementation, *, members=None):
    files = {}
    for scope, tree in (("runtime", runtime), ("ops", implementation)):
        files[scope] = {path.relative_to(tree).as_posix(): {"bytes": path.stat().st_size,
            "sha256": ops.sha_file(path, source.FILE_CAP)} for path in tree.rglob("*") if path.is_file()}
    archive = root / "selected.tar"
    with tarfile.open(archive, "w", format=tarfile.USTAR_FORMAT) as output:
        for scope, tree in (("runtime", runtime), ("ops", implementation)):
            for name, item in files[scope].items():
                header = tarfile.TarInfo(scope + "/" + name)
                header.size = item["bytes"]
                output.addfile(header, io.BytesIO((tree / name).read_bytes()))
        for header, body in members or []:
            output.addfile(header, io.BytesIO(body))
    manifest = {"schema": source.SCHEMA, "runtime_commit": "1" * 40, "ops_commit": "2" * 40,
        "archive": {"bytes": archive.stat().st_size, "sha256": ops.sha_file(archive, source.ARCHIVE_CAP)}, "files": files}
    path = root / "source.json"
    path.write_bytes(ops.canonical(manifest))
    return SimpleNamespace(source_manifest=path, source_manifest_sha256=ops.sha_file(path, ops.JSON_CAP),
                           source_archive=archive, ops_commit="2" * 40), manifest


@pytest.fixture
def bundle(tmp_path):
    runtime, implementation = tmp_path / "runtime", tmp_path / "ops"
    for tree, required in ((runtime, source.REQUIRED_RUNTIME), (implementation, source.REQUIRED_OPS)):
        tree.mkdir()
        for relative in required:
            path = tree / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"reviewed fixture bytes " + relative.encode())
    args, manifest = seal_bundle(tmp_path, runtime, implementation)
    return tmp_path, runtime, implementation, args, manifest


def test_selected_source_exact_inventory_no_git(bundle, monkeypatch):
    _root, runtime, implementation, args, manifest = bundle
    monkeypatch.setattr(source.subprocess, "run", lambda *a, **kw: pytest.fail("archive route must not invoke Git"))
    before = {path: path.read_bytes() for tree in (runtime, implementation) for path in tree.rglob("*") if path.is_file()}
    receipt = source.verify(runtime, "1" * 40, args, implementation)
    assert receipt["mode"] == "selected-archive" and receipt["manifest_sha256"] == args.source_manifest_sha256
    assert receipt["file_count"] == sum(len(files) for files in manifest["files"].values())
    assert all(path.read_bytes() == encoded for path, encoded in before.items())


@pytest.mark.parametrize("variant", ["manifest_hash", "schema", "field", "runtime_commit", "ops_commit", "required",
    "unknown_file", "unknown_dir", "changed_runtime", "changed_ops", "missing", "archive_hash", "archive_size",
    "traversal", "absolute", "backslash", "device", "case_alias", "boolean_bytes", "file_limit", "total_limit",
    "partial", "git_metadata", "hardlink", "bytecode", "environment"])
def test_selected_source_refusals(bundle, variant):
    root, runtime, implementation, args, manifest = bundle
    files = manifest["files"]["runtime"]
    chosen = sorted(files)[0]
    entry = dict(files[chosen])
    reseal = True
    if variant == "manifest_hash":
        args.source_manifest_sha256 = "0" * 64
        reseal = False
    elif variant == "schema":
        manifest["schema"] += "-unknown"
    elif variant == "field":
        manifest["unknown"] = True
    elif variant in ("runtime_commit", "ops_commit"):
        manifest[variant] = "3" * 40
    elif variant == "required":
        del files[chosen]
    elif variant == "unknown_file":
        (runtime / "unreviewed.py").write_bytes(b"unreviewed")
    elif variant == "unknown_dir":
        (runtime / "extra-empty").mkdir()
    elif variant in ("changed_runtime", "changed_ops"):
        path = runtime / chosen if variant == "changed_runtime" else implementation / sorted(manifest["files"]["ops"])[0]
        path.write_bytes(b"changed")
    elif variant == "missing":
        (runtime / chosen).unlink()
    elif variant == "archive_hash":
        args.source_archive.write_bytes(args.source_archive.read_bytes() + b"changed")
    elif variant == "archive_size":
        manifest["archive"]["bytes"] = source.ARCHIVE_CAP + 1
    elif variant in ("traversal", "absolute", "backslash", "device", "case_alias"):
        illegal = {"traversal": "../app.py", "absolute": "/app.py", "backslash": "app\\x.py",
                   "device": "app/CON.py", "case_alias": chosen.upper()}[variant]
        files[illegal] = entry
    elif variant == "boolean_bytes":
        files[chosen]["bytes"] = True
    elif variant == "file_limit":
        files[chosen]["bytes"] = source.FILE_CAP + 1
    elif variant == "total_limit":
        for index in range(9):
            files[f"extra{index}"] = {"bytes": source.FILE_CAP, "sha256": "0" * 64}
    elif variant == "partial":
        args.source_archive = None
    elif variant == "git_metadata":
        (runtime / ".git").mkdir()
    elif variant == "hardlink":
        import os
        os.link(runtime / chosen, root / "second-link")
    elif variant in ("bytecode", "environment"):
        files["app/__pycache__/config.pyc" if variant == "bytecode" else ".venv/config.py"] = entry
    if reseal:
        args.source_manifest.write_bytes(ops.canonical(manifest))
        args.source_manifest_sha256 = ops.sha_file(args.source_manifest, ops.JSON_CAP)
    with pytest.raises(ops.RecoveryError):
        source.verify(runtime, "1" * 40, args, implementation)


@pytest.mark.parametrize("variant", ["link", "hardlink", "pax", "gnu", "traversal", "directory", "duplicate", "trailing", "hash", "padding"])
def test_selected_archive_raw_header_guards(bundle, variant):
    root, runtime, implementation, args, _manifest = bundle
    header = tarfile.TarInfo("unexpected")
    body = b""
    if variant in ("link", "hardlink", "pax", "gnu"):
        header.type = {"link": tarfile.SYMTYPE, "hardlink": tarfile.LNKTYPE, "pax": tarfile.XHDTYPE,
                       "gnu": tarfile.GNUTYPE_LONGNAME}[variant]
        header.linkname = "runtime/app/config.py" if variant in ("link", "hardlink") else ""
    elif variant == "traversal":
        header.name = "../escape"
    elif variant == "directory":
        header.type = tarfile.DIRTYPE
    elif variant == "duplicate":
        header.name = "runtime/app/config.py"
        body = (runtime / "app/config.py").read_bytes()
        header.size = len(body)
    args, manifest = seal_bundle(root, runtime, implementation, members=[(header, body)] if variant not in ("trailing", "hash", "padding") else [])
    if variant in ("trailing", "hash", "padding"):
        encoded = bytearray(args.source_archive.read_bytes())
        if variant == "trailing":
            encoded += b"not-zero"
        elif variant == "hash":
            encoded[512] ^= 1
        else:
            first = tarfile.TarInfo.frombuf(bytes(encoded[:512]), "utf-8", "strict")
            encoded[512 + first.size] = 1
        args.source_archive.write_bytes(encoded)
        manifest["archive"] = {"bytes": len(encoded), "sha256": ops.sha_file(args.source_archive, source.ARCHIVE_CAP)}
        args.source_manifest.write_bytes(ops.canonical(manifest))
        args.source_manifest_sha256 = ops.sha_file(args.source_manifest, ops.JSON_CAP)
    with pytest.raises(ops.RecoveryError):
        source.verify(runtime, "1" * 40, args, implementation)


def test_clean_git_route_never_sets_trust(tmp_path, monkeypatch):
    args = SimpleNamespace()
    calls = []
    def git(command, **kwargs):
        calls.append(command)
        output = str(tmp_path).encode() if command[1:] == ["rev-parse", "--show-toplevel"] else b"1" * 40 if command[1:] == ["rev-parse", "HEAD"] else b""
        return SimpleNamespace(returncode=0, stdout=output)
    monkeypatch.setattr(source.subprocess, "run", git)
    assert source.verify(tmp_path, "1" * 40, args, tmp_path)["mode"] == "clean-git"
    assert all(command[1] != "config" for command in calls)
    monkeypatch.setattr(source.subprocess, "run", lambda *a, **kw: SimpleNamespace(returncode=128, stdout=b""))
    with pytest.raises(ops.RecoveryError, match="clean_git_source_unavailable"):
        source.verify(tmp_path, "1" * 40, args, tmp_path)
