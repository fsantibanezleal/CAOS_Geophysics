"""Paired public Git-blob USTAR builder; no worktree content, fetch, install or keys."""

from __future__ import annotations

import argparse
import hashlib
import io
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import threading
import time

try:
    from scripts import ops_recovery as ops
    from scripts import ops_source_pin as source
except ModuleNotFoundError:
    import ops_recovery as ops
    import ops_source_pin as source


SELECTION_SCHEMA = "geophysics.ops-source-selection/v1"
RECEIPT_SCHEMA = "geophysics.ops-source-build/v1"
POLICY = "paired-public-code-and-two-edi-fixtures/v1"
RUNTIME_PATHS = source.REQUIRED_RUNTIME | set("app/auth.py app/errors.py app/formats.py app/main.py app/models.py "
    "app/processing.py app/projects.py app/schemas.py app/security.py app/views.py".split())
OPS_PATHS = frozenset(source.REQUIRED_OPS)
PATHS = {"runtime": frozenset(RUNTIME_PATHS), "ops": OPS_PATHS}
COMMAND_SECONDS = 30
BUILD_SECONDS = 300
META_CAP = 2 * 1024**2
META_TOTAL = 8 * 1024**2
STDERR_CAP = 16 * 1024
OID = re.compile(r"[0-9a-f]{40}")


def trusted_git_tool():
    """Installed Git may use regular hardlinks; this exception NEVER applies to source/output."""
    found = shutil.which("git")
    ops.require(found is not None, "git_tool_unavailable")
    path = Path(found)
    ops.safe_path(path.parent, directory=True, outside_repo=False)
    info = path.lstat()
    ops.require(stat.S_ISREG(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400
                and path.resolve(strict=True) == path and 0 < info.st_size <= 32 * 1024**2,
                "unsafe_git_tool")
    digest = hashlib.sha256()
    count = 0
    with path.open("rb") as handle:
        while block := handle.read(65536):
            count += len(block)
            ops.require(count <= 32 * 1024**2, "git_tool_size_limit")
            digest.update(block)
    ops.require(count == info.st_size, "git_tool_changed")
    return path, digest.hexdigest(), info.st_nlink


def clean_environment():
    environment = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
    environment.pop("PYTHONPATH", None)
    environment.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_SYSTEM": os.devnull,
        "GIT_CONFIG_GLOBAL": os.devnull, "GIT_OPTIONAL_LOCKS": "0", "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_NO_LAZY_FETCH": "1", "GIT_LITERAL_PATHSPECS": "1", "GIT_ALLOW_PROTOCOL": "",
        "GIT_TERMINAL_PROMPT": "0", "LC_ALL": "C", "PYTHONDONTWRITEBYTECODE": "1"})
    return environment


def bounded_command(command, *, cwd, cap, deadline, allowed=(0,)):
    """Read bounded stdout and discard bounded stderr; no private diagnostic logging."""
    timeout = min(COMMAND_SECONDS, deadline - time.monotonic())
    ops.require(timeout > 0, "source_build_timeout")
    process = subprocess.Popen([str(arg) for arg in command], cwd=cwd, env=clean_environment(),
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = bytearray()
    failed = threading.Event()
    def drain(stream, limit, retain):
        count = 0
        try:
            while block := stream.read(4096):
                count += len(block)
                if count > limit:
                    failed.set()
                    try:
                        process.kill()
                    except OSError:
                        pass
                    break
                if retain:
                    output.extend(block)
        except OSError:
            failed.set()
        finally:
            stream.close()
    readers = [threading.Thread(target=drain, args=(process.stdout, cap, True), daemon=True),
               threading.Thread(target=drain, args=(process.stderr, STDERR_CAP, False), daemon=True)]
    for reader in readers:
        reader.start()
    try:
        status = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        raise ops.RecoveryError("source_command_timeout") from None
    finally:
        for reader in readers:
            reader.join(timeout=1)
    ops.require(status in allowed and not failed.is_set() and not any(reader.is_alive() for reader in readers),
                "source_command_failed")
    ops.require(time.monotonic() < deadline, "source_build_timeout")
    return bytes(output)


def object_oid(kind, body):
    # Git SHA-1 content addressing, NOT encryption/authentication or a production trust proof.
    return hashlib.sha1(f"{kind} {len(body)}\0".encode() + body, usedforsecurity=False).hexdigest()


def parse_tree(body):
    entries, offset = {}, 0
    while offset < len(body):
        space, zero = body.find(b" ", offset), body.find(b"\0", offset)
        ops.require(offset < space < zero and zero + 21 <= len(body), "invalid_git_tree")
        mode, name = body[offset:space], body[space + 1:zero]
        ops.require(mode in {b"40000", b"100644", b"100755", b"120000", b"160000"}
                    and name and b"/" not in name and name not in entries, "invalid_git_tree")
        entries[name] = (mode.decode("ascii"), body[zero + 1:zero + 21].hex())
        offset = zero + 21
        ops.require(len(entries) <= 65536, "git_tree_count_limit")
    return entries


class Repository:
    def __init__(self, root, commit, binary, deadline):
        self.root = ops.safe_path(root, directory=True, outside_repo=False)
        self.commit = source.commit(commit)
        self.binary, self.deadline = binary, deadline
        self.tree_cache, self.meta_bytes = {}, 0
        top = self.git("rev-parse", "--show-toplevel", cap=4096).decode("utf-8").strip()
        ops.require(Path(top).resolve() == self.root, "explicit_git_root_required")
        ops.require(self.git("rev-parse", "--show-object-format", cap=100).strip() == b"sha1", "git_object_format_unsupported")
        self.common = ops.safe_path(Path(self.git("rev-parse", "--path-format=absolute", "--git-common-dir", cap=4096)
                                             .decode("utf-8").strip()), directory=True, outside_repo=False)
        config = self.git("config", "--get-regexp", r"^(extensions\.partialclone|remote\..*\.promisor)$", cap=16384, allowed=(0, 1))
        ops.require(not config, "partial_git_repository_forbidden")
        objects = self.objects = ops.safe_path(self.common / "objects", directory=True, outside_repo=False)
        if os.path.lexists(objects / "info"):
            ops.safe_path(objects / "info", directory=True, outside_repo=False)
        ops.require(not any(os.path.lexists(objects / "info" / leaf) for leaf in ("alternates", "http-alternates")),
                    "git_object_alternates_forbidden")
        pack = objects / "pack"
        if pack.exists():
            ops.safe_path(pack, directory=True, outside_repo=False)
            for count, path in enumerate(pack.iterdir()):
                ops.require(count < 8192 and not path.name.endswith(".promisor"), "promisor_git_pack_forbidden")
                ops.safe_path(path, outside_repo=False)
        self.check_loose(self.commit)
        ops.require(self.git("cat-file", "-t", self.commit, cap=100).strip() == b"commit", "git_commit_object_required")
        body = self.object("commit", self.commit, META_CAP)
        first = body.split(b"\n", 1)[0]
        ops.require(re.fullmatch(rb"tree [0-9a-f]{40}", first), "invalid_git_commit_tree")
        self.tree = first[5:].decode("ascii")
        self.tree_entries(self.tree)

    def git(self, *args, cap, allowed=(0,)):
        return bounded_command([self.binary, "--no-lazy-fetch", "--no-replace-objects", "--no-optional-locks",
                                "--no-pager", "--literal-pathspecs", *args],
                               cwd=self.root, cap=cap, deadline=self.deadline, allowed=allowed)

    def object(self, kind, oid, cap):
        ops.require(OID.fullmatch(oid), "invalid_git_object_oid")
        self.check_loose(oid)
        size = self.git("cat-file", "-s", oid, cap=100).strip()
        ops.require(re.fullmatch(rb"0|[1-9][0-9]*", size) and int(size) <= cap, "git_object_size_limit")
        body = self.git("cat-file", kind, oid, cap=int(size))
        ops.require(len(body) == int(size) and object_oid(kind, body) == oid, "git_object_hash_mismatch")
        return body

    def check_loose(self, oid):
        parent = self.objects / oid[:2]
        if os.path.lexists(parent):
            ops.safe_path(parent, directory=True, outside_repo=False)
        path = parent / oid[2:]
        if os.path.lexists(path):
            ops.safe_path(path, outside_repo=False)

    def tree_entries(self, oid):
        if oid not in self.tree_cache:
            body = self.object("tree", oid, META_CAP)
            self.meta_bytes += len(body)
            ops.require(self.meta_bytes <= META_TOTAL, "git_metadata_limit")
            self.tree_cache[oid] = parse_tree(body)
        return self.tree_cache[oid]

    def inventory(self, selected):
        result = self.git("ls-tree", "-r", "-z", "--full-tree", self.tree, "--", *selected, cap=META_CAP)
        ops.require(result.endswith(b"\0"), "invalid_git_inventory")
        files = {}
        for row in result[:-1].split(b"\0"):
            metadata, path = row.split(b"\t", 1)
            mode, kind, oid = metadata.decode("ascii").split(" ")
            name = source.name(path.decode("ascii"))
            ops.require(name in selected and name not in files and mode in {"100644", "100755"}
                        and kind == "blob" and OID.fullmatch(oid), "git_regular_blob_required")
            self.check_loose(oid)
            tree, chain = self.tree, []
            parts = name.split("/")
            for index, part in enumerate(parts):
                entries = self.tree_entries(tree)
                ops.require(part.encode() in entries, "git_tree_path_missing")
                actual_mode, actual_oid = entries[part.encode()]
                chain.append({"tree_oid": tree, "entry": part, "mode": actual_mode, "oid": actual_oid})
                if index < len(parts) - 1:
                    ops.require(actual_mode == "40000", "git_tree_directory_required")
                    tree = actual_oid
                else:
                    ops.require(actual_mode == mode and actual_oid == oid, "git_inventory_tree_mismatch")
            size = self.git("cat-file", "-s", oid, cap=100).strip()
            ops.require(re.fullmatch(rb"0|[1-9][0-9]*", size) and int(size) <= source.FILE_CAP, "selected_source_file_limit")
            files[name] = {"oid": oid, "mode": mode, "bytes": int(size), "tree_chain": chain}
        ops.require(set(files) == set(selected), "selected_git_paths_missing")
        return files


def selection(args):
    source.commit(args.runtime_commit)
    source.commit(args.ops_commit)
    ops.digest(args.selection_sha256)
    path = ops.safe_path(args.selection)
    ops.require(ops.sha_file(path, ops.JSON_CAP) == args.selection_sha256, "selection_hash_mismatch")
    selected = ops.read_json(path)
    ops.fields(selected, "schema runtime_commit ops_commit files")
    ops.fields(selected["files"], "runtime ops")
    ops.require(selected["schema"] == SELECTION_SCHEMA and selected["runtime_commit"] == args.runtime_commit
                and selected["ops_commit"] == args.ops_commit, "selection_commit_or_schema_mismatch")
    count = 0
    for scope, policy in PATHS.items():
        names = selected["files"][scope]
        ops.require(isinstance(names, list) and all(isinstance(name, str) for name in names), "invalid_source_selection")
        count += len(names)
        ops.require(count <= source.COUNT_CAP, "selected_source_count_limit")
        for name in names:
            source.name(name)
        ops.require(names == sorted(set(names)) and len({name.casefold() for name in names}) == len(names)
                    and set(names) == policy, "precise_source_selection_required")
    return selected


def content_policy(body):
    ops.require(not body.startswith((b"MZ", b"\x7fELF", b"\xfe\xed\xfa", b"\xce\xfa\xed", b"\xcf\xfa\xed", b"\xca\xfe\xba\xbe",
                                    b"SQLite format 3\0", b"PK\x03\x04", b"\x1f\x8b", b"\xd0\xcf\x11\xe0"))
                and b"\0" not in body and not body.startswith(b"version https://git-lfs.github.com/spec/v1"),
                "forbidden_source_content")
    body.decode("utf-8", "strict")
    ops.require(not re.search(rb"AGE-SECRET-KEY-1[0-9A-Z]{58}|-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----", body),
                "private_key_content_forbidden")


class BoundedArchive:
    def __init__(self, handle):
        self.handle, self.count = handle, 0

    def write(self, data):
        self.count += len(data)
        ops.require(self.count <= source.ARCHIVE_CAP, "source_archive_size_limit")
        return self.handle.write(data)


def completed_receipt(output, receipt):
    pending, final = output / "build-receipt.pending.json", output / "build-receipt.json"
    ops.write_new(pending, ops.canonical(receipt))
    ops.sync_dir(output)
    ops.safe_path(final, exists=False)
    # link is an atomic no-replace publication, unlike POSIX rename. The transient
    # second link is ONLY to our newly written receipt, removed before completion.
    os.link(pending, final)
    try:
        pending.unlink()
        ops.sync_dir(output)
    except OSError:
        # Preserve precisely our NEW receipt as diagnostic, never leave a completed name on failed publication.
        if os.path.lexists(pending):
            final.unlink()
        else:
            os.rename(final, pending)
        raise


def build(args):
    deadline = time.monotonic() + BUILD_SECONDS
    ops.require(type(args.epoch) is int and 0 <= args.epoch <= 2147483647, "explicit_ustar_epoch_required")
    output = ops.safe_path(args.new_output, exists=False)
    ops.safe_path(output.parent, directory=True, private=True)
    selected = selection(args)
    binary, binary_sha256, binary_links = trusted_git_tool()
    version = bounded_command([binary, "--no-lazy-fetch", "--no-replace-objects", "--no-optional-locks", "--version"],
                              cwd=output.parent, cap=200, deadline=deadline).decode("ascii").strip()
    ops.require(re.fullmatch(r"git version [0-9]+\.[0-9]+\.[0-9]+(?:[.\w-]+)?", version), "git_version_unavailable")
    repositories, inventories = {}, {}
    total = 0
    for scope in PATHS:
        repo = Repository(getattr(args, scope + "_repo"), getattr(args, scope + "_commit"), binary, deadline)
        ops.separate(output, repo.root)
        ops.separate(Path(args.selection), repo.root)
        repositories[scope] = repo
        inventory = repo.inventory(selected["files"][scope])
        inventories[scope] = inventory
        for entry in inventory.values():
            total += entry["bytes"]
            ops.require(total <= source.TOTAL_CAP, "selected_source_total_limit")
    # Validate every committed blob/content BEFORE any output; retain hashes, not payloads.
    files = {scope: {} for scope in PATHS}
    for scope, inventory in inventories.items():
        for name, entry in inventory.items():
            body = repositories[scope].object("blob", entry["oid"], source.FILE_CAP)
            content_policy(body)
            files[scope][name] = {"sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)}
    ops.require(time.monotonic() < deadline, "source_build_timeout")
    output.mkdir(mode=0o700)  # Atomic exclusive reservation, never rename onto an existing user directory.
    archive = output / "selected-source.tar"
    with ops.new_file(archive) as handle:
        bounded = BoundedArchive(handle)
        with tarfile.open(fileobj=bounded, mode="w|", format=tarfile.USTAR_FORMAT) as tar:
            for scope in sorted(PATHS):
                for name in sorted(files[scope]):
                    entry = inventories[scope][name]
                    body = repositories[scope].object("blob", entry["oid"], source.FILE_CAP)
                    content_policy(body)
                    ops.require(len(body) == files[scope][name]["bytes"]
                                and hashlib.sha256(body).hexdigest() == files[scope][name]["sha256"], "source_object_changed")
                    header = tarfile.TarInfo(scope + "/" + name)
                    header.mode, header.mtime, header.uid, header.gid = 0o644, args.epoch, 0, 0
                    header.uname = header.gname = ""
                    header.type, header.size = tarfile.REGTYPE, len(body)
                    tar.addfile(header, io.BytesIO(body))
        handle.flush()
        os.fsync(handle.fileno())
    combined = {scope + "/" + name: item for scope, entries in files.items() for name, item in entries.items()}
    source.verify_archive(archive, combined)
    ops.require(ops.sha_file(Path(args.selection), ops.JSON_CAP) == args.selection_sha256, "selection_changed")
    manifest = {"schema": source.SCHEMA, "runtime_commit": args.runtime_commit, "ops_commit": args.ops_commit,
        "archive": {"sha256": ops.sha_file(archive, source.ARCHIVE_CAP), "bytes": archive.stat().st_size}, "files": files}
    manifest_path = output / "selected-source.json"
    ops.write_new(manifest_path, ops.canonical(manifest))
    ops.sync_dir(output)
    receipt = {"schema": RECEIPT_SCHEMA, "completed": True, "source_only": True, "production_activated": False,
        "release_accepted": False, "key_authority_verified": False, "created_at": ops.stamp(), "policy": POLICY,
        "epoch": args.epoch, "selection_sha256": args.selection_sha256, "archive": manifest["archive"],
        "manifest_sha256": ops.sha_file(manifest_path, ops.JSON_CAP), "files": inventories,
        "commits": {scope: {"commit": repo.commit, "tree": repo.tree} for scope, repo in repositories.items()},
        "caps": {"files": source.COUNT_CAP, "file_bytes": source.FILE_CAP, "total_bytes": source.TOTAL_CAP,
                 "archive_bytes": source.ARCHIVE_CAP, "command_seconds": COMMAND_SECONDS, "build_seconds": BUILD_SECONDS,
                 "metadata_bytes": META_CAP, "metadata_total_bytes": META_TOTAL, "stderr_bytes": STDERR_CAP},
        "tools": {"git_version": version, "git_binary_sha256": binary_sha256, "git_binary_links": binary_links,
                  "python_version": list(sys.version_info[:3]), "helper_sha256": ops.sha_file(Path(__file__).absolute(), source.FILE_CAP)},
        "trust": "MAIN-reviewed Git objects/selection and immutable installation; not production trust or signature proof"}
    for scope, entries in receipt["files"].items():
        for name, entry in entries.items():
            entry["sha256"] = files[scope][name]["sha256"]
    ops.require(trusted_git_tool() == (binary, binary_sha256, binary_links), "git_tool_changed")
    ops.require(time.monotonic() < deadline, "source_build_timeout")
    completed_receipt(output, receipt)
    return receipt


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    for name in ("runtime-repo", "ops-repo", "selection", "new-output"):
        result.add_argument("--" + name, type=Path, required=True)
    for name in ("runtime-commit", "ops-commit", "selection-sha256"):
        result.add_argument("--" + name, required=True)
    result.add_argument("--epoch", type=int, required=True)
    return result


def main(argv=None):
    try:
        build(parser().parse_args(argv))
    except ops.RecoveryError as exc:
        print(f"source_bundle_failed: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError, KeyError, tarfile.TarError, subprocess.SubprocessError):
        print("source_bundle_failed: invalid_or_unavailable_input", file=sys.stderr)
        return 2
    print("source_bundle_complete: source_only=true production_activated=false release_accepted=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
