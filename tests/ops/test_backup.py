"""Real age/migrated SQLite drills and hostile inputs; all state is temporary."""

from __future__ import annotations

import asyncio
from contextlib import closing
from datetime import timedelta
import io
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from app.processing_contract import METHOD_ID
from app.worker import run_one
from scripts import ops_recovery as ops
from tests.api.conftest import ApiHarness, make_harness as make_harness  # noqa: F401


@pytest.fixture
def case(tmp_path, make_harness):
    age = shutil.which("age")
    keygen = shutil.which("age-keygen")
    assert age and keygen, "Install maintained age and age-keygen for the real encryption gates"
    key = tmp_path / "identity.txt"
    subprocess.run([keygen, "-o", str(key)], capture_output=True, check=True)
    os.chmod(key, 0o600)
    recipient = subprocess.run([keygen, "-y", str(key)], capture_output=True, check=True).stdout.decode().strip()
    harness = make_harness()
    owner = harness.account()["id"]
    projects = []
    for number in range(2):
        project = harness.project(f"Temporary survey {number}")
        asset, dataset = harness.processed_dataset(project["id"])
        response = harness.request("POST", f"/api/projects/{project['id']}/jobs", json={
            "dataset_id": dataset["dataset_id"], "method_id": METHOD_ID, "parameters": {"threshold": 6},
        })
        assert response.status_code == 202, response.text
        assert asyncio.run(run_one(harness.settings)) == response.json()["job_id"]
        assert harness.client.get(f"/api/projects/{project['id']}/jobs/{response.json()['job_id']}").json()["state"] == "succeeded"
        projects.append(project)
    harness.close()
    scratch = tmp_path / "scratch"
    scratch.mkdir(mode=0o700)
    source, database = harness.settings.data_dir, harness.settings.database_path
    deployment = str(uuid4())
    proof = tmp_path / "proof.json"
    ops.write_new(proof, ops.canonical({
        "schema": ops.PROOF_SCHEMA, "source": str(source), "database": str(database),
        "deployment_id": deployment, "mode": "fixture", "issued_at": ops.stamp(),
        "expires_at": (ops.now() + timedelta(minutes=30)).isoformat(),
        "ingress_blocked": True, "all_writers_accounted": True, "units": [],
    }))
    args = ops.parser().parse_args([
        "backup", "--source", str(source), "--database", str(database), "--maintenance-proof", str(proof),
        "--deployment-id", deployment, "--age-binary", age, "--identity", str(key), "--recipient", recipient,
        "--scratch-parent", str(scratch), "--new-output", str(tmp_path / "backup"), "--initialize-authority",
        "--expires-at", (ops.now() + timedelta(days=30)).isoformat(), "--policy-id", "restricted-30-days-v1",
        "--fixture-root", str(tmp_path), "--max-bytes", str(32 * 1024**2), "--max-file-bytes", str(8 * 1024**2),
        "--max-files", "128",
    ])
    return SimpleNamespace(args=args, harness=harness, projects=projects, owner=owner, root=tmp_path)


def restore_args(case, receipt, *, authority=None, authority_hash=None, target="restored"):
    return ops.parser().parse_args([
        "restore", "--deployment-id", case.args.deployment_id, "--age-binary", str(case.args.age_binary),
        "--identity", str(case.args.identity), "--scratch-parent", str(case.args.scratch_parent),
        "--snapshot", str(case.root / "backup" / "snapshot.age"), "--snapshot-sha256", receipt["snapshot_sha256"],
        "--authority", str(authority or case.root / "backup" / "authority.age"),
        "--authority-sha256", authority_hash or receipt["authority_sha256"],
        "--new-target", str(case.root / target), "--fixture-root", str(case.root),
        "--max-bytes", str(32 * 1024**2), "--max-file-bytes", str(8 * 1024**2), "--max-files", "128",
    ])


def test_encrypted_roundtrip(case):
    database_before = Path(case.args.database).read_bytes()
    receipt = ops.capture(case.args)
    assert Path(case.args.database).read_bytes() == database_before
    assert receipt["fixture_only"] and receipt["host_drill"] == "not_run"
    backup = case.root / "backup"
    assert {p.name for p in backup.iterdir()} == {"snapshot.age", "authority.age", "receipt.json"}
    assert (backup / "snapshot.age").read_bytes().startswith(b"age-encryption.org/v1")
    encrypted_before = (backup / "snapshot.age").read_bytes()
    restored = ops.restore(restore_args(case, receipt))
    target = case.root / "restored"
    assert restored["surviving_file_count"] == 6 and restored["removed_file_count"] == 0
    assert restored["production_activated"] is False and restored["sessions_revoked"] is True
    assert (backup / "snapshot.age").read_bytes() == encrypted_before
    with closing(ops.open_database(target / "private" / "api.sqlite3")) as connection:
        ops.validate_database(connection)
        assert connection.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == 2
        assert connection.execute("SELECT COUNT(*) FROM access_tokens").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM rate_windows").fetchone()[0] == 0
        surviving = ops.inventory(connection, target / "private", ops.Limits())
        assert {item["kind"] for item in surviving.values()} == {"raw", "dataset", "result"}
    assert list(Path(case.args.scratch_parent).iterdir()) == []
    assert not any(p.suffix in {".tar", ".sqlite3", ".txt"} for p in backup.iterdir())
    if os.name == "posix":
        assert backup.stat().st_mode & 0o077 == 0
        assert all(p.stat().st_mode & 0o077 == 0 for p in target.rglob("*"))


@pytest.mark.parametrize("limit", ["bytes", "count"])
def test_inventory_limit_precedes_derivative_reads(case, monkeypatch, limit):
    def unexpected_read(*args):
        raise AssertionError("Inventory ceiling must fail before loading derivative JSON")

    monkeypatch.setattr(ops, "read_json", unexpected_read)
    with closing(ops.open_database(Path(case.args.database))) as db:
        total, maximum = db.execute("SELECT SUM(byte_count),MAX(byte_count) FROM raw_assets").fetchone()
        limits = ops.Limits(total=total - 1, file=maximum) if limit == "bytes" else ops.Limits(count=1)
        with pytest.raises(ops.RecoveryError, match="inventory_limit|database_row_limit"):
            ops.inventory(db, Path(case.args.source), limits)


def test_deleted_project_cannot_return(case):
    receipt = ops.capture(case.args)
    with TestClient(case.harness.app) as client:
        reopened = ApiHarness(client, case.harness.app, case.harness.settings, case.harness.messages)
        response = reopened.request("POST", "/api/auth/cookie/login", data={
            "username": "reader@example.org", "password": "correct horse battery staple",
        })
        assert response.status_code == 204
        deleted = reopened.request("DELETE", f"/api/projects/{case.projects[0]['id']}")
        assert deleted.status_code == 200, deleted.text
        assert deleted.json()["external_backup_status"] == "pending_reconciliation"
    args = SimpleNamespace(**vars(case.args))
    args.command, args.new_output = "checkpoint", str(case.root / "checkpoint")
    args.authority, args.authority_sha256 = str(case.root / "backup" / "authority.age"), receipt["authority_sha256"]
    args.initialize_authority = False
    checkpoint = ops.capture(args)
    result = ops.restore(restore_args(case, receipt, authority=case.root / "checkpoint" / "authority.age",
                                      authority_hash=checkpoint["authority_sha256"]))
    assert result["removed_file_count"] == 3 and result["tombstone_count"] == 1
    private = case.root / "restored" / "private"
    with closing(ops.open_database(private / "api.sqlite3")) as db:
        assert [row[0] for row in db.execute("SELECT id FROM projects")] == [case.projects[1]["id"]]
        assert [row[0] for row in db.execute("SELECT project_id FROM deletion_receipts")] == [case.projects[0]["id"]]
        for table in ("raw_assets", "source_records", "observation_datasets", "processing_jobs"):
            assert db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 1
        assert db.execute("SELECT raw_bytes FROM account_usage").fetchone()[0] == db.execute("SELECT byte_count FROM raw_assets").fetchone()[0]
        surviving = ops.inventory(db, private, ops.Limits())
        assert len(surviving) == 3
    assert not (private / "projects" / case.owner / case.projects[0]["id"]).exists()
    assert not (private / "derived" / case.owner / case.projects[0]["id"]).exists()
    assert b"Temporary survey 0" not in (private / "api.sqlite3").read_bytes()
    # Run the existing application's read-only startup audit against the new target.
    from app.config import WorkerSettings
    from app.database import make_engine, reconcile_private_files
    from sqlalchemy.ext.asyncio import async_sessionmaker

    async def check_startup():
        settings = WorkerSettings(private)
        engine = make_engine(settings)
        try:
            await reconcile_private_files(settings, async_sessionmaker(engine, expire_on_commit=False))
        finally:
            await engine.dispose()

    asyncio.run(check_startup())
    # Cumulative checkpoints cannot drop the deletion or registrations.
    next_args = SimpleNamespace(**vars(args))
    next_args.new_output = str(case.root / "checkpoint-next")
    next_args.authority = str(case.root / "checkpoint" / "authority.age")
    next_args.authority_sha256 = checkpoint["authority_sha256"]
    following = ops.capture(next_args)
    assert following["authority_sequence"] == 3 and following["tombstone_count"] == 1


@pytest.mark.parametrize("failure", ["missing", "stale", "wrong_source", "ingress", "writers", "host_mode", "changed"])
def test_maintenance_rejection(case, failure):
    proof = Path(case.args.maintenance_proof)
    value = json.loads(proof.read_bytes())
    if failure == "missing":
        proof.unlink()
    elif failure == "stale":
        value["expires_at"] = (ops.now() - timedelta(seconds=1)).isoformat()
    elif failure == "wrong_source":
        value["source"] = str(case.root)
    elif failure == "ingress":
        value["ingress_blocked"] = False
    elif failure == "writers":
        value["all_writers_accounted"] = False
    elif failure == "host_mode":
        value["mode"] = "systemd"
    elif failure == "changed":
        maintenance = ops.Maintenance(proof, Path(case.args.source), Path(case.args.database), case.args.deployment_id, case.root)
        value["expires_at"] = (ops.now() + timedelta(minutes=20)).isoformat()
        proof.write_bytes(ops.canonical(value))
        with pytest.raises(ops.RecoveryError, match="maintenance_proof_changed"):
            maintenance.check()
        return
    if failure != "missing":
        proof.write_bytes(ops.canonical(value))
    before = Path(case.args.database).read_bytes()
    with pytest.raises(ops.RecoveryError):
        ops.capture(case.args)
    assert not (case.root / "backup").exists()
    assert Path(case.args.database).read_bytes() == before


@pytest.mark.parametrize("failure", ["unknown_file", "staging", "job_staging", "backup_entry", "tamper", "schema", "revision",
                                    "quota", "active", "foreign_key", "wal", "unknown_derivative", "owner", "request"])
def test_source_rejection(case, failure):
    root, database = Path(case.args.source), Path(case.args.database)
    with sqlite3.connect(database) as db:
        if failure == "schema":
            db.execute("CREATE TABLE unknown_table (data TEXT)")
        elif failure == "revision":
            db.execute("UPDATE alembic_version SET version_num='future'")
        elif failure == "quota":
            db.execute("UPDATE account_usage SET raw_bytes=1")
        elif failure == "active":
            db.execute("UPDATE processing_jobs SET state='running'")
        elif failure == "foreign_key":
            db.execute("UPDATE raw_assets SET source_id=? WHERE id=(SELECT id FROM raw_assets LIMIT 1)", (str(uuid4()),))
        elif failure == "owner":
            db.execute("UPDATE raw_assets SET owner_id=?", (str(uuid4()),))
        elif failure == "request":
            db.execute("UPDATE processing_jobs SET request_sha256=?", ("f" * 64,))
    if failure == "unknown_file":
        (root / "unknown").write_bytes(b"preserve")
    elif failure in {"staging", "job_staging", "backup_entry"}:
        path = root / {"staging": ".deleting", "job_staging": ".job-staging", "backup_entry": ".backups"}[failure] / "unknown"
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(b"preserve")
    elif failure == "tamper":
        next((root / "projects").rglob("*/*/*")).write_bytes(b"tamper")
    elif failure == "wal":
        Path(str(database) + "-wal").write_bytes(b"uncopied state")
    elif failure == "unknown_derivative":
        path = next((root / "derived").rglob("datasets/*.json"))
        data = json.loads(path.read_bytes())
        data["schema"] = "unknown/v99"
        raw = ops.canonical(data)
        path.write_bytes(raw)
        with sqlite3.connect(database) as db:
            db.execute("UPDATE observation_datasets SET sha256=?,byte_count=? WHERE storage_key=?",
                       (ops.hashlib.sha256(raw).hexdigest(), len(raw), path.relative_to(root).as_posix()))
    before = database.read_bytes()
    with pytest.raises((ops.RecoveryError, OSError)):
        ops.capture(case.args)
    assert database.read_bytes() == before and not (case.root / "backup").exists()


@pytest.mark.parametrize("failure", ["relative", "existing", "overlap", "key_target", "fixture_escape", "symlink", "hardlink"])
def test_path_rejection(case, failure):
    args = SimpleNamespace(**vars(case.args))
    existing = case.root / "existing"
    existing.mkdir()
    sentinel = existing / "do-not-change"
    sentinel.write_bytes(b"untouched")
    key_before = Path(args.identity).read_bytes()
    if failure == "relative":
        args.new_output = "relative"
    elif failure == "existing":
        args.new_output = str(existing)
    elif failure == "overlap":
        args.new_output = str(Path(args.source) / "backup")
    elif failure == "key_target":
        args.new_output = args.identity
    elif failure == "fixture_escape":
        args.new_output = str(case.root.parent / "outside-fixture")
    elif failure == "symlink":
        link = case.root / "linked"
        try:
            link.symlink_to(existing, target_is_directory=True)
        except OSError:
            pytest.skip("symlink creation privilege unavailable on this Windows host")
        args.new_output = str(link / "new-target")
    elif failure == "hardlink":
        path = case.root / "hard-key"
        os.link(args.identity, path)
        args.identity = str(path)
    with pytest.raises(ops.RecoveryError):
        ops.capture(args)
    assert sentinel.read_bytes() == b"untouched" and Path(case.args.identity).read_bytes() == key_before


def archive_manifest():
    return {
        "schema": ops.SNAPSHOT_SCHEMA, "deployment_id": str(uuid4()), "fixture_only": True,
        "database_revision": ops.REVISION, "tombstones": [],
        "registration": {"snapshot_id": str(uuid4()), "sha256": "0" * 64, "created_at": ops.stamp(),
                         "expires_at": (ops.now() + timedelta(days=1)).isoformat(), "policy_id": "test"},
        "files": {"api.sqlite3": {"sha256": ops.hashlib.sha256(b"db").hexdigest(), "bytes": 2,
                                  "kind": "database", "project_id": None, "owner_id": None}},
    }


@pytest.mark.parametrize("failure", ["traversal", "absolute", "drive", "backslash", "symlink", "hardlink", "directory",
                                    "duplicate", "hash", "unknown", "missing", "schema", "bytes", "count", "pax", "truncated", "trailing"])
def test_archive_rejection(tmp_path, failure):
    manifest = archive_manifest()
    limits = ops.Limits(total=8192, file=4096, count=8)
    if failure == "schema":
        manifest["schema"] = "unknown"
    if failure == "bytes":
        manifest["files"]["api.sqlite3"]["bytes"] = 9000
    if failure == "count":
        limits = ops.Limits(total=8192, file=4096, count=1)
        manifest["files"]["unexpected"] = manifest["files"]["api.sqlite3"].copy()
    archive = tmp_path / "hostile.tar"
    with ops.tarfile.open(archive, "w", format=ops.tarfile.PAX_FORMAT if failure == "pax" else ops.tarfile.USTAR_FORMAT) as tar:
        data = ops.canonical(manifest)
        header = ops.tarfile.TarInfo("manifest.json")
        header.size = len(data)
        tar.addfile(header, io.BytesIO(data))
        name = {"traversal": "../outside", "absolute": "/outside", "drive": "C:/outside",
                "backslash": "a\\b", "unknown": "unknown"}.get(failure, "api.sqlite3")
        header = ops.tarfile.TarInfo(name)
        header.size = 2
        if failure in {"symlink", "hardlink", "directory"}:
            header.type = {"symlink": ops.tarfile.SYMTYPE, "hardlink": ops.tarfile.LNKTYPE, "directory": ops.tarfile.DIRTYPE}[failure]
            header.linkname = "../outside" if failure != "directory" else ""
            header.size = 0
        if failure == "pax":
            header.pax_headers = {"comment": "disallowed extended header"}
        if failure != "missing":
            tar.addfile(header, io.BytesIO(b"xx" if failure == "hash" else b"db"))
        if failure == "duplicate":
            tar.addfile(header, io.BytesIO(b"db"))
    if failure == "truncated":
        archive.write_bytes(archive.read_bytes()[:700])
    elif failure == "trailing":
        archive.write_bytes(archive.read_bytes() + b"appended")
    outside = tmp_path / "outside"
    with pytest.raises((ops.RecoveryError, ops.tarfile.TarError)):
        ops.extract_archive(archive, tmp_path / "new", limits)
    assert not outside.exists()


@pytest.mark.parametrize("failure", ["hash", "snapshot_hash", "deployment", "unregistered", "expired", "conflict", "fixture_mode"])
def test_authority_rejection(case, failure):
    receipt = ops.capture(case.args)
    args = restore_args(case, receipt)
    if failure == "hash":
        args.authority_sha256 = "f" * 64
    elif failure == "snapshot_hash":
        args.snapshot_sha256 = "f" * 64
    elif failure == "deployment":
        args.deployment_id = str(uuid4())
    elif failure == "fixture_mode":
        args.fixture_root = None
    else:
        scratch = case.root / "edit"
        scratch.mkdir()
        age = ops.Age(Path(args.age_binary), Path(args.identity), case.args.recipient, ops.Limits())
        authority = ops.load_authority(age, Path(args.authority), args.authority_sha256, scratch,
                                       case.args.deployment_id, True)
        if failure == "unregistered":
            authority["snapshots"] = []
        elif failure == "expired":
            authority["snapshots"][0]["created_at"] = (ops.now() - timedelta(days=2)).isoformat()
            authority["snapshots"][0]["expires_at"] = (ops.now() - timedelta(days=1)).isoformat()
        elif failure == "conflict":
            authority["schema"] = "unknown"
        ops.write_new(scratch / "new.json", ops.canonical(authority))
        age.encrypt(scratch / "new.json", scratch / "authority.age")
        args.authority = str(scratch / "authority.age")
        args.authority_sha256 = ops.sha_file(Path(args.authority), ops.JSON_CAP)
    with pytest.raises(ops.RecoveryError):
        ops.restore(args)
    assert not (case.root / "restored").exists()
    assert (case.root / "backup" / "snapshot.age").exists()


def test_retention_and_chain(case):
    receipt = ops.capture(case.args)
    args = SimpleNamespace(**vars(case.args))
    args.initialize_authority = False
    args.authority, args.authority_sha256 = str(case.root / "backup" / "authority.age"), receipt["authority_sha256"]
    args.new_output = str(case.root / "backup-next")
    following = ops.capture(args)
    scratch = case.root / "inspect"
    scratch.mkdir()
    age = ops.Age(Path(args.age_binary), Path(args.identity), None, ops.Limits())
    authority = ops.load_authority(age, case.root / "backup-next" / "authority.age", following["authority_sha256"],
                                   scratch, args.deployment_id, True)
    assert authority["sequence"] == 2 and authority["predecessor_sha256"] == receipt["authority_sha256"]
    assert [item["snapshot_id"] for item in authority["snapshots"]] == [receipt["snapshot_id"], following["snapshot_id"]]
    assert all(item["policy_id"] == "restricted-30-days-v1" for item in authority["snapshots"])
    # A previously valid encrypted authority cannot match a separately recorded latest hash.
    stale = restore_args(case, receipt, authority_hash=following["authority_sha256"])
    with pytest.raises(ops.RecoveryError, match="authority_hash_mismatch"):
        ops.restore(stale)


def test_age_failure(case, capsys):
    receipt = ops.capture(case.args)
    corrupt = case.root / "backup" / "snapshot.age"
    corrupted = bytearray(corrupt.read_bytes())
    corrupted[-1] ^= 1
    corrupt.write_bytes(corrupted)
    age = ops.Age(Path(case.args.age_binary), Path(case.args.identity), None, ops.Limits())
    with pytest.raises(ops.RecoveryError, match="age_decryption_failed"):
        age.decrypt(corrupt, case.root / "new-plain", ops.Limits().archive)
    # Bounded decrypt refuses output growth even for valid authenticated input.
    large = case.root / "large.json"
    ops.write_new(large, b"x" * 10000)
    encryptor = ops.Age(Path(case.args.age_binary), Path(case.args.identity), case.args.recipient, ops.Limits())
    encryptor.encrypt(large, case.root / "large.age")
    with pytest.raises(ops.RecoveryError, match="decryption_limit"):
        age.decrypt(case.root / "large.age", case.root / "bounded", 100)
    args = restore_args(case, receipt)
    status = ops.main(["restore", "--deployment-id", args.deployment_id, "--age-binary", args.age_binary,
                       "--identity", args.identity, "--scratch-parent", args.scratch_parent,
                       "--snapshot", args.snapshot, "--snapshot-sha256", args.snapshot_sha256,
                       "--authority", args.authority, "--authority-sha256", args.authority_sha256,
                       "--new-target", args.new_target, "--fixture-root", args.fixture_root])
    assert status == 2
    captured = capsys.readouterr()
    assert captured.err == "recovery_failed: snapshot_hash_mismatch\n"
    assert "AGE-SECRET" not in captured.out + captured.err and str(case.root) not in captured.err


@pytest.mark.parametrize("failure", ["active", "unmasked", "pid", "cgroup", "populated", "good"])
def test_systemd_proof(tmp_path, monkeypatch, failure):
    props = {"LoadState": "masked", "ActiveState": "inactive", "SubState": "dead", "UnitFileState": "masked-runtime",
             "MainPID": "0", "ControlGroup": ""}
    if failure == "active":
        props["ActiveState"] = "active"
    elif failure == "unmasked":
        props["UnitFileState"] = "enabled"
    elif failure == "pid":
        props["MainPID"] = "42"
    elif failure == "cgroup":
        props.pop("ControlGroup")
    elif failure == "populated":
        props["ControlGroup"] = "/system.slice/geophysics-api.service"
        original_exists, original_file, original_read = Path.exists, Path.is_file, Path.read_text
        monkeypatch.setattr(Path, "exists", lambda path: True if "sys/fs/cgroup" in path.as_posix() else original_exists(path))
        monkeypatch.setattr(Path, "is_file", lambda path: True if "cgroup.events" in path.as_posix() else original_file(path))
        monkeypatch.setattr(Path, "read_text", lambda path, *args, **kwargs:
                            "populated 1\n" if "cgroup.events" in path.as_posix() else original_read(path, *args, **kwargs))
    def run(command, **kwargs):
        assert command[:2] == ["/usr/bin/systemctl", "show"]
        assert command[-1] == "geophysics-api.service"
        return SimpleNamespace(returncode=0, stdout="\n".join(f"{k}={v}" for k, v in props.items()).encode())
    monkeypatch.setattr(ops.subprocess, "run", run)
    if failure == "good":
        ops.Maintenance.check_unit("geophysics-api.service")
    else:
        with pytest.raises(ops.RecoveryError):
            ops.Maintenance.check_unit("geophysics-api.service")


def test_operational_contract():
    guide = (Path(__file__).resolve().parents[2] / "docs" / "operations" / "01_backup_restore.md").read_text()
    for text in ("Actual-host drill: NOT RUN", "latest authority", "synchronous", "--new-target", "--maintenance-proof",
                 "--authority-sha256", "not_attempted", "systemctl", "checkpoint", "30 days", "0700", "0600"):
        assert text in guide
    for text in ("operator-assisted", "run_one", ".job-staging", "StateDirectory", "quarantine"):
        assert text in guide


def test_strict_json_and_tombstone_conflicts():
    for value in (b'{"x":1,"x":2}', b'{"x":NaN}'):
        with pytest.raises(ops.RecoveryError):
            ops.parse_json(value)
    tombstone = {"id": str(uuid4()), "project_id": str(uuid4()), "owner_id": str(uuid4()), "deleted_at": ops.stamp(),
                 "asset_hashes": [], "asset_manifest": [], "derived_manifest": [], "backup_purge_status": "not_attempted"}
    changed = {**tombstone, "owner_id": str(uuid4())}
    with pytest.raises(ops.RecoveryError, match="tombstone_conflict"):
        ops.merge_tombstones([tombstone], [changed])
    assert ops.merge_tombstones([tombstone], []) == [tombstone]


def test_restore_never_overwrites_existing_target(case):
    receipt = ops.capture(case.args)
    existing = case.root / "restored"
    existing.mkdir()
    sentinel = existing / "sentinel"
    sentinel.write_bytes(b"existing user state")
    snapshot = (case.root / "backup" / "snapshot.age").read_bytes()
    with pytest.raises(ops.RecoveryError, match="new_target_required"):
        ops.restore(restore_args(case, receipt))
    assert sentinel.read_bytes() == b"existing user state"
    assert (case.root / "backup" / "snapshot.age").read_bytes() == snapshot


def test_stop_proof_rechecked_before_publication(case, monkeypatch):
    original = ops.Maintenance.check
    calls = []
    def check(proof):
        calls.append(True)
        if len(calls) >= 2:
            raise ops.RecoveryError("writer_not_stopped_masked")
        original(proof)
    monkeypatch.setattr(ops.Maintenance, "check", check)
    with pytest.raises(ops.RecoveryError, match="writer_not_stopped_masked"):
        ops.capture(case.args)
    assert len(calls) == 2 and not (case.root / "backup").exists()
    assert list(Path(case.args.scratch_parent).iterdir()) == []


def test_wrong_identity_and_timeout(case, monkeypatch):
    receipt = ops.capture(case.args)
    wrong = case.root / "wrong-identity.txt"
    subprocess.run([shutil.which("age-keygen"), "-o", str(wrong)], capture_output=True, check=True)
    os.chmod(wrong, 0o600)
    args = restore_args(case, receipt)
    args.identity = str(wrong)
    with pytest.raises(ops.RecoveryError, match="age_decryption_failed"):
        ops.restore(args)
    assert not (case.root / "restored").exists()
    age = ops.Age(Path(case.args.age_binary), Path(case.args.identity), case.args.recipient, ops.Limits())
    original = ops.subprocess.run
    def timeout(command, **kwargs):
        if "--encrypt" in command:
            raise subprocess.TimeoutExpired(command, 1)
        return original(command, **kwargs)
    monkeypatch.setattr(ops.subprocess, "run", timeout)
    with pytest.raises(ops.RecoveryError, match="age_timeout"):
        age.encrypt(Path(case.args.maintenance_proof), case.root / "timed-out.age")


@pytest.mark.skipif(os.name != "nt", reason="Windows junction-specific gate")
def test_windows_junction_rejected(tmp_path):
    destination = tmp_path / "owned"
    destination.mkdir()
    sentinel = destination / "sentinel"
    sentinel.write_bytes(b"preserve existing target")
    link = tmp_path / "junction"
    link_text, target_text = str(link).replace("'", "''"), str(destination).replace("'", "''")
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                    f"New-Item -ItemType Junction -Path '{link_text}' -Target '{target_text}' | Out-Null"],
                   capture_output=True, check=True)
    with pytest.raises(ops.RecoveryError, match="linked_path"):
        ops.safe_path(link / "new", exists=False)
    assert sentinel.read_bytes() == b"preserve existing target"


def test_tombstone_for_newer_owner_survives_external_authority(case):
    receipt = ops.capture(case.args)
    args = restore_args(case, receipt)
    scratch = case.root / "edit"
    scratch.mkdir()
    age = ops.Age(Path(args.age_binary), Path(args.identity), case.args.recipient, ops.Limits())
    authority = ops.load_authority(age, Path(args.authority), args.authority_sha256, scratch, args.deployment_id, True)
    newer = {"id": str(uuid4()), "project_id": str(uuid4()), "owner_id": str(uuid4()), "deleted_at": ops.stamp(),
             "asset_hashes": [], "asset_manifest": [], "derived_manifest": [], "backup_purge_status": "not_attempted"}
    authority["tombstones"] = [newer]
    ops.write_new(scratch / "next.json", ops.canonical(authority))
    age.encrypt(scratch / "next.json", scratch / "latest.age")
    args.authority, args.authority_sha256 = str(scratch / "latest.age"), ops.sha_file(scratch / "latest.age", ops.JSON_CAP)
    result = ops.restore(args)
    assert result["tombstone_count"] == 1 and result["removed_file_count"] == 0
    with sqlite3.connect(case.root / "restored" / "private" / "api.sqlite3") as db:
        assert db.execute("SELECT COUNT(*) FROM deletion_receipts").fetchone()[0] == 0
    inspect = case.root / "inspect"
    inspect.mkdir()
    carried = ops.load_authority(age, case.root / "restored" / "authority.age", args.authority_sha256,
                                inspect, args.deployment_id, True)
    assert carried["tombstones"] == [newer]
