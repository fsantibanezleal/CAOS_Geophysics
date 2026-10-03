"""Read-only selected-source provenance; never extracts or changes Git trust."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tarfile

try:
    from scripts import ops_recovery as ops
except ModuleNotFoundError:
    import ops_recovery as ops


SCHEMA = "geophysics.ops-selected-source/v1"
FILE_CAP = 8 * 1024**2
TOTAL_CAP = 64 * 1024**2
ARCHIVE_CAP = 80 * 1024**2
COUNT_CAP = 4096
REQUIRED_RUNTIME = set("app/__init__.py app/alembic.ini app/config.py app/database.py app/server.py app/worker.py "
    "app/mt_contract.py app/mt_compute.py app/mt_bundle.py app/compute.py app/bundle.py app/processing_contract.py "
    "app/processing_storage.py app/migrations/env.py app/migrations/versions/0001_api_foundation.py "
    "app/migrations/versions/0002_private_storage_permission.py app/migrations/versions/0003_processing_jobs.py "
    "data-pipeline/edi.py data-pipeline/electromagnetics.py data-pipeline/geology.py tests/api/conftest.py tests/api/test_online_mt.py "
    "data/fixtures/edi/halfspace-100-native.edi data/fixtures/edi/two-layer-noisy-rotated.edi".split())
REQUIRED_OPS = set("scripts/ops_source_pin.py scripts/ops_host_fixture.py scripts/ops_recovery.py tests/ops/mt_drill.py".split())


def add_arguments(parser):
    parser.add_argument("--source-manifest", type=Path)
    parser.add_argument("--source-manifest-sha256")
    parser.add_argument("--source-archive", type=Path)
    parser.add_argument("--ops-commit", help="Full independently reviewed ops commit for selected archive mode")


def source_options(args):
    values = [getattr(args, key, None) for key in ("source_manifest", "source_manifest_sha256", "source_archive", "ops_commit")]
    ops.require(not any(value is not None for value in values) or all(value is not None for value in values),
                "incomplete_selected_source_pin")
    if values[0] is None:
        return []
    return ["--source-manifest", str(values[0]), "--source-manifest-sha256", values[1],
            "--source-archive", str(values[2]), "--ops-commit", values[3]]


def commit(value):
    ops.require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value), "explicit_source_commit_required")
    return value


def name(value):
    ops.require(isinstance(value, str) and len(value) <= 240 and value
                and not value.startswith("/") and "\\" not in value and ":" not in value
                and all(part not in {"", ".", "..", ".git", "__pycache__", ".venv", "venv"} for part in value.split("/"))
                and not value.endswith((".pyc", ".pyo"))
                and all(32 <= ord(char) < 127 for char in value), "invalid_selected_source_path")
    # No trailing spaces/dots, device names or case-fold aliases on Windows.
    ops.require(all(not part.endswith((" ", ".")) and not re.fullmatch(
        r"(?i)(con|prn|aux|nul|com[0-9]|lpt[0-9])(?:\..*)?", part) for part in value.split("/")),
        "invalid_selected_source_path")
    return value


def parents(files):
    return {str(parent) for path in files for parent in PurePosixPath(path).parents if str(parent) != "."}


def verify_tree(root, files):
    """Exact selected tree, including necessary directories; bounded walk, no symlink following."""
    directories = parents(files)
    seen_files, seen_dirs = set(), set()
    for current, child_dirs, child_files in os.walk(root, followlinks=False):
        for leaf, directory in [(leaf, True) for leaf in child_dirs] + [(leaf, False) for leaf in child_files]:
            path = Path(current) / leaf
            relative = name(path.relative_to(root).as_posix())
            ops.require(relative in (directories if directory else files), "unknown_selected_source_entry")
            ops.safe_path(path, directory=directory, outside_repo=False)
            if directory:
                seen_dirs.add(relative)
            else:
                seen_files.add(relative)
                entry = files[relative]
                ops.require(path.stat().st_size == entry["bytes"] and ops.sha_file(path, FILE_CAP) == entry["sha256"],
                            "selected_source_hash_mismatch")
            ops.require(len(seen_files) <= COUNT_CAP and len(seen_dirs) <= COUNT_CAP * 16, "selected_source_count_limit")
    ops.require(seen_files == set(files) and seen_dirs == directories, "missing_selected_source_entry")


def verify_archive(path, expected):
    """Inspect raw USTAR headers and member hashes; no tarfile extraction or allocation by untrusted size."""
    seen, seen_dirs = set(), set()
    directories = parents(expected)
    with path.open("rb") as stream:
        while True:
            header = stream.read(512)
            ops.require(len(header) == 512, "truncated_selected_archive")
            if not any(header):
                ops.require(stream.read(512) == bytes(512), "selected_archive_end_marker")
                while block := stream.read(1024**2):
                    ops.require(not any(block), "selected_archive_trailing_data")
                break
            try:
                member = tarfile.TarInfo.frombuf(header, "utf-8", "strict")
            except (tarfile.HeaderError, UnicodeError, ValueError):
                ops.require(False, "invalid_selected_archive_header")
            ops.require(header[257:263] == b"ustar\0" and header[263:265] == b"00"
                        and member.type in {tarfile.REGTYPE, tarfile.DIRTYPE} and not member.linkname,
                        "unsupported_selected_archive_member")
            relative = name(member.name)
            ops.require(relative not in seen and relative not in seen_dirs, "duplicate_selected_archive_member")
            if member.type == tarfile.DIRTYPE:
                ops.require(relative in directories and member.size == 0, "unknown_selected_archive_directory")
                seen_dirs.add(relative)
                continue
            ops.require(relative in expected and member.size == expected[relative]["bytes"], "unknown_selected_archive_file")
            seen.add(relative)
            digest = hashlib.sha256()
            remaining = member.size
            while remaining:
                block = stream.read(min(remaining, 1024**2))
                ops.require(block, "truncated_selected_archive")
                remaining -= len(block)
                digest.update(block)
            ops.require(digest.hexdigest() == expected[relative]["sha256"], "selected_archive_hash_mismatch")
            padding = (-member.size) % 512
            ops.require(stream.read(padding) == bytes(padding), "invalid_selected_archive_padding")
            ops.require(len(seen) <= COUNT_CAP and len(seen_dirs) <= COUNT_CAP * 16, "selected_source_count_limit")
    ops.require(seen == set(expected), "missing_selected_archive_file")


def verify(checkout, expected_commit, args, ops_root):
    commit(expected_commit)
    options = source_options(args)
    if not options:
        environment = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}
        environment.pop("GIT_DIR", None)
        environment.pop("GIT_WORK_TREE", None)
        results = []
        for command in (["rev-parse", "--show-toplevel"], ["rev-parse", "HEAD"],
                        ["status", "--porcelain", "--untracked-files=all", "--ignored=matching"]):
            result = subprocess.run(["git", *command], cwd=checkout, env=environment,
                                    capture_output=True, timeout=10, check=False)
            ops.require(result.returncode == 0 and len(result.stdout) <= 1024**2, "clean_git_source_unavailable")
            results.append(result.stdout.decode("utf-8").strip())
        ops.require(Path(results[0]).resolve() == checkout and results[1] == expected_commit and not results[2],
                    "fixture_runtime_changed")
        return {"mode": "clean-git", "runtime_commit": expected_commit}
    commit(args.ops_commit)
    checkout = ops.safe_path(checkout, directory=True)
    ops_root = ops.safe_path(ops_root, directory=True)
    ops.separate(checkout, ops_root)
    manifest_path = ops.safe_path(args.source_manifest)
    archive_path = ops.safe_path(args.source_archive)
    for root in (checkout, ops_root):
        ops.separate(manifest_path, root)
        ops.separate(archive_path, root)
    ops.digest(args.source_manifest_sha256)
    ops.require(ops.sha_file(manifest_path, ops.JSON_CAP) == args.source_manifest_sha256, "selected_manifest_hash_mismatch")
    manifest = ops.read_json(manifest_path)
    ops.fields(manifest, "schema runtime_commit ops_commit archive files")
    ops.require(manifest["schema"] == SCHEMA and manifest["runtime_commit"] == expected_commit
                and manifest["ops_commit"] == args.ops_commit, "selected_source_commit_mismatch")
    ops.fields(manifest["archive"], "sha256 bytes")
    ops.digest(manifest["archive"]["sha256"])
    ops.require(type(manifest["archive"]["bytes"]) is int and 1024 <= manifest["archive"]["bytes"] <= ARCHIVE_CAP,
                "selected_archive_size_limit")
    ops.fields(manifest["files"], "runtime ops")
    total, count = 0, 0
    all_files = {}
    for scope, required in (("runtime", REQUIRED_RUNTIME), ("ops", REQUIRED_OPS)):
        files = manifest["files"][scope]
        ops.require(isinstance(files, dict) and required <= set(files), "required_selected_source_missing")
        folded = set()
        for relative, entry in files.items():
            name(relative)
            ops.require(relative.casefold() not in folded, "selected_source_case_alias")
            folded.add(relative.casefold())
            ops.fields(entry, "sha256 bytes")
            ops.digest(entry["sha256"])
            ops.require(type(entry["bytes"]) is int and 0 <= entry["bytes"] <= FILE_CAP, "selected_source_file_limit")
            total += entry["bytes"]
            count += 1
            ops.require(total <= TOTAL_CAP and count <= COUNT_CAP, "selected_source_count_or_byte_limit")
            all_files[scope + "/" + relative] = entry
    ops.require(archive_path.stat().st_size == manifest["archive"]["bytes"]
                and ops.sha_file(archive_path, ARCHIVE_CAP) == manifest["archive"]["sha256"], "selected_archive_digest_mismatch")
    verify_archive(archive_path, all_files)
    verify_tree(checkout, manifest["files"]["runtime"])
    verify_tree(ops_root, manifest["files"]["ops"])
    return {"mode": "selected-archive", "runtime_commit": expected_commit, "ops_commit": args.ops_commit,
            "manifest_sha256": args.source_manifest_sha256, "archive": manifest["archive"], "file_count": count,
            "file_bytes": total, "history_proof": "independently reviewed manifest; not server-derived Git history"}
