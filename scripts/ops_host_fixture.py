"""Main-owned nongate Linux recovery fixture; no installer/service/production writes."""

from __future__ import annotations

import argparse
from contextlib import closing
from datetime import timedelta
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
from uuid import uuid4

try:
    from scripts import ops_recovery as ops
    from scripts import ops_source_pin as sources
except ModuleNotFoundError:
    import ops_recovery as ops
    import ops_source_pin as sources


AGE_SHA256 = "2e305637f2a0555305e21c17fb74446acbb39b53135d43d4b744e50c287133a5"
KEYGEN_SHA256 = "c56ef69834e18ca4d3b953117f4481522c35fb6862a5d2871685aa4685893664"
ARCHIVE_SHA256 = "bdc69c09cbdd6cf8b1f333d372a1f58247b3a33146406333e30c0f26e8f51377"
LIMITS = ops.Limits(total=32 * 1024**2, file=8 * 1024**2, count=128, seconds=300)
UNIT = re.compile(r"geophysics-ops-fixture-[a-z0-9-]+\.service")
RUNNER = Path(__file__).resolve().parents[1] / "tests/ops/mt_drill.py"


def run_private(command, *, cwd=None, timeout=300):
    """Bound private child diagnostics during reads, never emit them to public logs."""
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "GIT_OPTIONAL_LOCKS": "0"}
    environment.pop("PYTHONPATH", None)
    process = subprocess.Popen([str(item) for item in command], cwd=cwd, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, env=environment)
    stdout = bytearray()
    overflow = threading.Event()
    def drain(stream, retain):
        count = 0
        try:
            while block := stream.read(4096):
                count += len(block)
                if count > 256 * 1024:
                    overflow.set()
                    try:
                        process.kill()
                    except OSError:
                        pass  # Child may already have exited; overflow still fails closed.
                    break
                if retain:
                    stdout.extend(block)
        finally:
            stream.close()
    readers = [threading.Thread(target=drain, args=(process.stdout, True), daemon=True),
               threading.Thread(target=drain, args=(process.stderr, False), daemon=True)]
    for reader in readers:
        reader.start()
    try:
        status = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        raise ops.RecoveryError("fixture_child_timeout") from None
    finally:
        for reader in readers:
            reader.join(timeout=1)
    ops.require(status == 0 and not overflow.is_set() and not any(reader.is_alive() for reader in readers),
                "fixture_child_failed")
    return bytes(stdout)


def verify_binary(path, expected):
    binary = ops.safe_path(path, outside_repo=False)
    ops.require(ops.sha_file(binary, 32 * 1024**2) == expected, "fixture_binary_hash_mismatch")
    ops.require(run_private([binary, "--version"], timeout=10).decode("ascii").strip() == "v1.3.1",
                "fixture_binary_version_mismatch")
    return binary


def preflight(args):
    ops.require(linux_host(), "linux_fixture_only")
    root = ops.safe_path(args.new_fixture_root, exists=False)
    ops.safe_path(root.parent, directory=True, private=True)
    checkout = ops.safe_path(args.runtime_checkout, directory=True, outside_repo=False)
    ops.separate(root, checkout)
    ops.require((checkout / "app/mt_contract.py").is_file(), "reviewed_mt_runtime_required")
    ops.require(len(args.units) == 2 and len(set(args.units)) == 2
                and all(UNIT.fullmatch(unit) for unit in args.units), "dummy_fixture_units_only")
    disk = shutil.disk_usage(root.parent)
    ops.require(disk.free * 100 >= disk.total * 30 and disk.free >= 128 * 1024**2, "fixture_disk_headroom_failed")
    age = verify_binary(args.age_binary, AGE_SHA256)
    keygen = verify_binary(args.age_keygen_binary, KEYGEN_SHA256)
    runtime_revision(checkout, args.runtime_commit, args)
    for unit in args.units:
        ops.Maintenance.check_unit(unit)
    # Fixture identity generation is confined to a new root below; nothing has been written yet.
    return root, checkout, age, keygen, {"total": disk.total, "free": disk.free, "threshold_percent": 30}


def linux_host():
    return sys.platform == "linux" and os.name == "posix"


def runtime_revision(checkout, expected, args):
    return sources.verify(checkout, expected, args, Path(__file__).resolve().parents[1])


def proof(root, name, state, deployment, units):
    path = root / name
    ops.write_new(path, ops.canonical({"schema": ops.PROOF_SCHEMA,
        "source": state["source"], "database": state["database"], "deployment_id": deployment,
        "mode": "systemd", "issued_at": ops.stamp(), "expires_at": (ops.now() + timedelta(minutes=30)).isoformat(),
        "ingress_blocked": True, "all_writers_accounted": True, "units": units}))
    # Actual observations, not dummy proof acceptance: API fixture child has exited; no public listener was bound.
    ops.Maintenance(path, Path(state["source"]), Path(state["database"]), deployment, None)
    return path


def capture_args(command, root, state, deployment, age, identity, recipient, maintenance, output, previous=None):
    argv = [command, "--source", state["source"], "--database", state["database"], "--deployment-id", deployment,
            "--maintenance-proof", str(maintenance), "--age-binary", str(age), "--identity", str(identity),
            "--recipient", recipient, "--scratch-parent", str(root / "scratch"), "--new-output", str(output),
            "--max-bytes", str(LIMITS.total), "--max-file-bytes", str(LIMITS.file), "--max-files", str(LIMITS.count),
            "--timeout-seconds", str(LIMITS.seconds)]
    if previous:
        argv += ["--authority", str(root / "backup/authority.age"), "--authority-sha256", previous["authority_sha256"]]
    else:
        argv += ["--initialize-authority", "--expires-at", (ops.now() + timedelta(days=1)).isoformat(),
                 "--policy-id", "nongate-private-fixture-1-day-v1"]
    return ops.parser().parse_args(argv)


def restore_args(root, deployment, age, identity, backup, authority, authority_hash, target):
    return ops.parser().parse_args(["restore", "--deployment-id", deployment, "--age-binary", str(age),
        "--identity", str(identity), "--scratch-parent", str(root / "scratch"), "--snapshot", str(root / "backup/snapshot.age"),
        "--snapshot-sha256", backup["snapshot_sha256"], "--authority", str(authority), "--authority-sha256", authority_hash,
        "--new-target", str(target), "--max-bytes", str(LIMITS.total), "--max-file-bytes", str(LIMITS.file),
        "--max-files", str(LIMITS.count), "--timeout-seconds", str(LIMITS.seconds)])


def fixture_command(checkout, state_root, mode, args, candidate=None):
    command = [sys.executable, "-B", RUNNER, mode]
    if candidate is not None:
        command.append(candidate)
    command.extend(["--runtime-commit", args.runtime_commit, *sources.source_options(args)])
    command.extend([checkout, state_root])
    run_private(command, cwd=checkout)


def scenario(args):
    root, checkout, age, keygen, disk = preflight(args)
    root.mkdir(mode=0o700)
    (root / "scratch").mkdir(mode=0o700)
    state_root = root / "state"
    fixture_command(checkout, state_root, "--prepare-state", args)
    source_provenance = runtime_revision(checkout, args.runtime_commit, args)
    state = ops.read_json(state_root / "fixture-state.json")
    ops.require(state.get("fixture_only") is True and state.get("main_owned") is True and state.get("nongate") is True
                and state.get("production_activated") is False and state.get("runtime_commit") == args.runtime_commit
                and len(state.get("files", {})) == 11,
                "invalid_fixture_marker")
    identity = root / "fixture-identity.txt"
    ops.safe_path(identity, exists=False)
    run_private([keygen, "-o", identity], timeout=10)
    ops.safe_path(identity, private=True)
    recipient = run_private([keygen, "-y", identity], timeout=10).decode("ascii").strip()
    deployment = str(uuid4())
    maintenance = proof(root, "proof-before.json", state, deployment, args.units)
    original_hash = ops.sha_file(Path(state["database"]), LIMITS.file)
    backup = ops.capture(capture_args("backup", root, state, deployment, age, identity, recipient, maintenance, root / "backup"))
    ops.require(ops.sha_file(Path(state["database"]), LIMITS.file) == original_hash, "fixture_source_changed")
    cipher_hash = ops.sha_file(root / "backup/snapshot.age", LIMITS.archive)
    roundtrip = ops.restore(restore_args(root, deployment, age, identity, backup, root / "backup/authority.age",
                                       backup["authority_sha256"], state_root / "roundtrip"))
    with closing(ops.open_database(state_root / "roundtrip/private/api.sqlite3")) as db:
        ops.require(ops.inventory(db, state_root / "roundtrip/private", LIMITS) == state["files"], "fixture_roundtrip_changed")
    ops.require(roundtrip["surviving_file_count"] == 11, "fixture_roundtrip_count")
    fixture_command(checkout, state_root, "--delete-fixture-project", args)
    ops.require(runtime_revision(checkout, args.runtime_commit, args) == source_provenance, "fixture_source_changed")
    deletion = ops.read_json(state_root / "fixture-deletion.json")
    maintenance = proof(root, "proof-after.json", state, deployment, args.units)
    checkpoint = ops.capture(capture_args("checkpoint", root, state, deployment, age, identity, recipient, maintenance,
                                         root / "checkpoint", backup))
    recovered = ops.restore(restore_args(root, deployment, age, identity, backup, root / "checkpoint/authority.age",
                                        checkpoint["authority_sha256"], state_root / "restored"))
    private = state_root / "restored/private"
    with closing(ops.open_database(private / "api.sqlite3")) as db:
        ops.require(ops.inventory(db, private, LIMITS) == deletion["files"], "fixture_survivors_changed")
        ops.require(db.execute("SELECT COUNT(*) FROM projects WHERE id=?", (state["disposable_project_id"],)).fetchone()[0] == 0
                    and db.execute("SELECT COUNT(*) FROM deletion_receipts WHERE project_id=?", (state["disposable_project_id"],)).fetchone()[0] == 1
                    and db.execute("SELECT COUNT(*) FROM access_tokens").fetchone()[0] == 0, "fixture_deleted_project_returned")
    ops.require(recovered["removed_file_count"] == 4 and recovered["surviving_file_count"] == 7
                and recovered["tombstone_count"] == 1 and recovered["sessions_revoked"] is True
                and recovered["production_activated"] is False, "fixture_recovery_count")
    ops.require(ops.sha_file(root / "backup/snapshot.age", LIMITS.archive) == cipher_hash, "fixture_ciphertext_changed")
    fixture_command(checkout, state_root, "--audit-private", args, private)
    ops.require(runtime_revision(checkout, args.runtime_commit, args) == source_provenance, "fixture_source_changed")
    receipt = {"schema": "geophysics.ops-host-fixture-evidence/v1", "created_at": ops.stamp(), "main_owned": True,
        "nongate": True, "fixture_only": True, "release_accepted": False, "production_activated": False,
        "runtime_commit": state["runtime_commit"], "source_provenance": source_provenance,
        "age_sha256": AGE_SHA256, "age_keygen_sha256": KEYGEN_SHA256,
        "release_archive_sha256": ARCHIVE_SHA256, "provenance": "official HTTPS release-API digest; no sigsum verification",
        "disk": disk, "deployment_id": deployment, "local_fixture_key_only": True, "key_escrow_tested": False,
        "offhost_durability_tested": False, "roundtrip": roundtrip, "restored": recovered,
        "backup_sha256": cipher_hash, "backup_erasure": "not_attempted", "core_host_drill": "not_run"}
    ops.write_new(root / "main-owned-fixture-receipt.json", ops.canonical(receipt))
    return receipt


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    for name in ("new-fixture-root", "runtime-checkout", "age-binary", "age-keygen-binary"):
        result.add_argument("--" + name, required=True, type=Path)
    result.add_argument("--runtime-commit", required=True, help="Reviewed runtime full 40-character SHA; clean Git or pinned archive")
    sources.add_arguments(result)
    result.add_argument("--units", nargs=2, required=True, help="Two already masked geophysics-ops-fixture-*.service units")
    return result


def main(argv=None):
    try:
        scenario(parser().parse_args(argv))
    except ops.RecoveryError as exc:
        print(f"fixture_failed: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError):
        print("fixture_failed: invalid_or_unavailable_private_input", file=sys.stderr)
        return 2
    print("private_fixture_complete: main_owned=true nongate=true release_accepted=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
