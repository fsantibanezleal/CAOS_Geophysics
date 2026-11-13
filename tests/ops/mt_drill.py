"""Isolated integration runner; imports exactly one explicitly selected MT app tree.

Called by test_backup_mt and the separately reviewed private host-fixture harness.
All writes are disposable fixtures; never a production utility or service controller.
"""

from __future__ import annotations

import asyncio
import argparse
from contextlib import closing
from datetime import timedelta
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace
from uuid import uuid4


STATE_SCHEMA = "geophysics.ops-fixture-state/v1"


def sealed_tree(ops, root):
    """Only a NEW runner-owned fixture tree; inspect before changing its modes."""
    for path in (root, *root.rglob("*")):
        ops.safe_path(path, directory=path.is_dir())
        os.chmod(path, 0o700 if path.is_dir() else 0o600)


def checked_state(ops, root, runtime, provenance):
    state = ops.read_json(root / "fixture-state.json")
    ops.fields(state, "schema fixture_only main_owned nongate production_activated root source database runtime_commit "
               "created_at owner_id disposable_project_id survivor_project_ids database_sha256 files source_provenance")
    ops.require(state["schema"] == STATE_SCHEMA and state["fixture_only"] is True and state["main_owned"] is True
                and state["nongate"] is True and state["production_activated"] is False
                and state["root"] == str(root) and state["runtime_commit"] == runtime
                and state["source_provenance"] == provenance, "invalid_fixture_marker")
    source = ops.safe_path(root / "case-0/private", directory=True, private=True)
    database = ops.safe_path(source / "api.sqlite3", private=True)
    ops.require(state["source"] == str(source) and state["database"] == str(database), "fixture_path_mismatch")
    return state, source, database


def main():
    sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))
    import ops_source_pin as sources
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--prepare-state", action="store_true")
    mode.add_argument("--delete-fixture-project", action="store_true")
    mode.add_argument("--audit-private", type=Path)
    parser.add_argument("--runtime-commit")
    sources.add_arguments(parser)
    parser.add_argument("checkout", type=Path)
    parser.add_argument("root", type=Path)
    selected = parser.parse_args()
    spec = importlib.util.spec_from_file_location("ops_recovery", Path(__file__).parents[2] / "scripts/ops_recovery.py")
    ops = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = ops
    spec.loader.exec_module(ops)
    checkout = ops.safe_path(selected.checkout, directory=True, outside_repo=False)
    root = ops.safe_path(selected.root, exists=not selected.prepare_state, directory=True)
    ops.separate(root, checkout)
    if selected.runtime_commit:
        runtime = selected.runtime_commit
    else:
        ops.require(not sources.source_options(selected), "explicit_source_commit_required")
        runtime = subprocess.run(["git", "rev-parse", "HEAD"], cwd=checkout, capture_output=True, check=True).stdout.decode().strip()
    provenance = sources.verify(checkout, runtime, selected, Path(__file__).parents[2])
    if selected.prepare_state:
        ops.safe_path(root.parent, directory=True, private=True)
        root.mkdir(mode=0o700)
    ops.safe_path(root, directory=True, private=True)
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["MPLCONFIGDIR"] = str(root / "mpl")
    sys.path.insert(0, str(checkout))
    import pytest
    from fastapi.testclient import TestClient
    from tests.api.conftest import ApiHarness, make_harness
    from tests.api.test_online_mt import NATIVE, LAYERED, upload_dataset, submit, complete
    from app.mt_contract import M05_ID, M06_ID
    from app.processing_contract import METHOD_ID
    from app.worker import run_one

    if selected.delete_fixture_project or selected.audit_private:
        state, source, database = checked_state(ops, root, runtime, provenance)
        if selected.audit_private:
            private = ops.safe_path(selected.audit_private, directory=True, private=True)
            ops.require(private.is_relative_to(root) and private != source, "fixture_candidate_boundary")
            from app.config import WorkerSettings
            from app.database import reconcile_private_files
            from sqlalchemy import URL
            from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

            async def audit():
                # Reuse the app's reconciliation logic with a genuinely read-only connection.
                # make_engine's normal journal-mode initialization would mutate a restored DB header.
                url = URL.create("sqlite+aiosqlite", database="file:" + (private / "api.sqlite3").as_posix(),
                                 query={"mode": "ro", "immutable": "1", "uri": "true"})
                engine = create_async_engine(url)
                try:
                    await reconcile_private_files(WorkerSettings(private), async_sessionmaker(engine, expire_on_commit=False))
                finally:
                    await engine.dispose()

            before = ops.sha_file(private / "api.sqlite3", ops.Limits().file)
            asyncio.run(audit())
            ops.require(ops.sha_file(private / "api.sqlite3", ops.Limits().file) == before, "candidate_audit_changed_database")
            ops.require(sources.verify(checkout, runtime, selected, Path(__file__).parents[2]) == provenance, "fixture_source_changed")
            print("fixture_candidate_audited")
            return
        ops.safe_path(root / "fixture-deletion.json", exists=False)
        ops.require(ops.sha_file(database, ops.Limits().file) == state["database_sha256"], "fixture_database_changed")
        with closing(ops.open_database(database)) as db:
            ops.require(ops.inventory(db, source, ops.Limits()) == state["files"], "fixture_inventory_changed")
            ops.require([tuple(row) for row in db.execute("SELECT owner_id FROM projects WHERE id=?", (state["disposable_project_id"],))]
                        == [(state["owner_id"],)], "fixture_project_changed")
            ops.audit_tree(source, database, state["files"], ops.Limits())
        from app.config import Settings
        from app.server import create_app
        settings = Settings(data_dir=source, db_path=database, public_origin="http://testserver", cookie_secure=False,
                            auth_secret="test-secret-with-at-least-32-characters-123456", mt_online_enabled=True, auth_mode="email")

        async def no_smtp(*args):
            raise AssertionError("Fixture must never send email")

        app = create_app(settings, no_smtp)
        with TestClient(app) as client:
            fixture_client = ApiHarness(client, app, settings, [])
            assert fixture_client.request("POST", "/api/auth/cookie/login", data={
                "username": "reader@example.org", "password": "correct horse battery staple"}).status_code == 204
            deleted = fixture_client.request("DELETE", f"/api/projects/{state['disposable_project_id']}")
            assert deleted.status_code == 200, deleted.text
            assert deleted.json()["external_backup_status"] == "pending_reconciliation"
        with closing(ops.open_database(database)) as db:
            survivors = ops.inventory(db, source, ops.Limits())
            expected = {key: value for key, value in state["files"].items() if value["project_id"] != state["disposable_project_id"]}
            ops.require(survivors == expected and len(survivors) == 7, "fixture_survivor_changed")
        sealed_tree(ops, source)
        ops.require(sources.verify(checkout, runtime, selected, Path(__file__).parents[2]) == provenance, "fixture_source_changed")
        ops.write_new(root / "fixture-deletion.json", ops.canonical({"schema": "geophysics.ops-fixture-deletion/v1",
            "fixture_only": True, "main_owned": True, "nongate": True, "project_id": state["disposable_project_id"],
            "database_sha256": ops.sha_file(database, ops.Limits().file), "files": survivors,
            "external_backup_status": "pending_reconciliation", "production_activated": False}))
        print("fixture_project_deleted")
        return

    monkeypatch = pytest.MonkeyPatch()
    fixture = make_harness.__wrapped__(root, monkeypatch)
    factory = next(fixture)
    try:
        harness = factory(mt_online_enabled=True)
        owner = harness.account()["id"]
        projects = []
        for source, station, rotation, thickness, initial in (
            (NATIVE, "HALFSPACE_100_NATIVE", 0, [], [100]),
            (LAYERED, "TWO_LAYER_NOISY_ROTATED", 27, [350], [100, 100]),
        ):
            project, _asset, dataset, _body = upload_dataset(harness, source, station=station, count=24, rotation=rotation)
            screen, qc = complete(harness, submit(harness, project, dataset, M05_ID, {}))
            solved, _ = complete(harness, submit(harness, project, dataset, M06_ID, {
                "qc_job_id": qc["job_id"], "thickness_m": thickness, "initial_ohm_m": initial,
                "beta": .001, "bootstrap_samples": 20, "seed": 61001,
            }))
            assert screen["inverse"] is None and solved["inverse"]["truth"] is None
            # Existing MT owner's scientific bundle re-import, not a second solver.
            from app.bundle import verify_bundle
            exported = harness.client.get(f"/api/projects/{project['id']}/jobs/{solved['job_id']}/export")
            assert exported.status_code == 200, exported.text
            verify_bundle(exported.content)
            projects.append(project)
        gravity = harness.project("Gravity survivor")
        _, dataset = harness.processed_dataset(gravity["id"])
        queued = harness.request("POST", f"/api/projects/{gravity['id']}/jobs", json={
            "dataset_id": dataset["dataset_id"], "method_id": METHOD_ID, "parameters": {"threshold": 6}})
        assert queued.status_code == 202
        assert asyncio.run(run_one(harness.settings)) == queued.json()["job_id"]
        harness.close()
        if selected.prepare_state:
            source, database = harness.settings.data_dir, harness.settings.database_path
            sealed_tree(ops, root)
            ops.require(sources.verify(checkout, runtime, selected, Path(__file__).parents[2]) == provenance, "fixture_source_changed")
            with closing(ops.open_database(database)) as db:
                files = ops.inventory(db, source, ops.Limits())
                ops.require(len(files) == 11, "fixture_generation_incomplete")
                ops.audit_tree(source, database, files, ops.Limits())
            ops.write_new(root / "fixture-state.json", ops.canonical({"schema": STATE_SCHEMA, "fixture_only": True,
                "main_owned": True, "nongate": True, "production_activated": False, "root": str(root),
                "source": str(source), "database": str(database), "runtime_commit": runtime, "created_at": ops.stamp(),
                "owner_id": owner, "disposable_project_id": projects[0]["id"],
                "survivor_project_ids": [projects[1]["id"], gravity["id"]], "files": files,
                "database_sha256": ops.sha_file(database, ops.Limits().file), "source_provenance": provenance}))
            print("fixture_state_created")
            return
        key = root / "identity.txt"
        subprocess.run([shutil.which("age-keygen"), "-o", str(key)], capture_output=True, check=True)
        os.chmod(key, 0o600)
        recipient = subprocess.run([shutil.which("age-keygen"), "-y", str(key)], capture_output=True, check=True).stdout.decode().strip()
        scratch = root / "scratch"
        scratch.mkdir(mode=0o700)
        proof = root / "proof.json"
        deployment = str(uuid4())
        source, database = harness.settings.data_dir, harness.settings.database_path
        ops.write_new(proof, ops.canonical({
            "schema": ops.PROOF_SCHEMA, "source": str(source), "database": str(database),
            "deployment_id": deployment, "mode": "fixture", "issued_at": ops.stamp(),
            "expires_at": (ops.now() + timedelta(minutes=30)).isoformat(),
            "ingress_blocked": True, "all_writers_accounted": True, "units": [],
        }))
        args = ops.parser().parse_args([
            "backup", "--source", str(source), "--database", str(database), "--maintenance-proof", str(proof),
            "--deployment-id", deployment, "--age-binary", shutil.which("age"), "--identity", str(key),
            "--recipient", recipient, "--scratch-parent", str(scratch), "--new-output", str(root / "backup"),
            "--initialize-authority", "--expires-at", (ops.now() + timedelta(days=30)).isoformat(),
            "--policy-id", "restricted-30-days-v1", "--fixture-root", str(root),
        ])
        original_db = database.read_bytes()
        with closing(ops.open_database(database)) as db:
            before = ops.inventory(db, source, ops.Limits())
        assert len(before) == 11
        receipt = ops.capture(args)
        assert database.read_bytes() == original_db
        ciphertext = (root / "backup/snapshot.age").read_bytes()

        def restore(authority, authority_hash, target):
            return ops.restore(ops.parser().parse_args([
                "restore", "--deployment-id", deployment, "--age-binary", shutil.which("age"),
                "--identity", str(key), "--scratch-parent", str(scratch),
                "--snapshot", str(root / "backup/snapshot.age"), "--snapshot-sha256", receipt["snapshot_sha256"],
                "--authority", str(authority), "--authority-sha256", authority_hash,
                "--new-target", str(root / target), "--fixture-root", str(root),
            ]))

        roundtrip = restore(root / "backup/authority.age", receipt["authority_sha256"], "roundtrip")
        assert roundtrip["surviving_file_count"] == 11
        with closing(ops.open_database(root / "roundtrip/private/api.sqlite3")) as db:
            assert ops.inventory(db, root / "roundtrip/private", ops.Limits()) == before
        with TestClient(harness.app) as client:
            reopened = ApiHarness(client, harness.app, harness.settings, harness.messages)
            assert reopened.request("POST", "/api/auth/cookie/login", data={
                "username": "reader@example.org", "password": "correct horse battery staple"}).status_code == 204
            deleted = reopened.request("DELETE", f"/api/projects/{projects[0]['id']}")
            assert deleted.status_code == 200, deleted.text
            assert deleted.json()["external_backup_status"] == "pending_reconciliation"
            assert client.get(f"/api/projects/{projects[0]['id']}").status_code == 404
        checkpoint_args = SimpleNamespace(**vars(args))
        checkpoint_args.command, checkpoint_args.new_output = "checkpoint", str(root / "checkpoint")
        checkpoint_args.initialize_authority = False
        checkpoint_args.authority, checkpoint_args.authority_sha256 = str(root / "backup/authority.age"), receipt["authority_sha256"]
        checkpoint = ops.capture(checkpoint_args)
        recovered = restore(root / "checkpoint/authority.age", checkpoint["authority_sha256"], "restored")
        assert recovered["removed_file_count"] == 4 and recovered["surviving_file_count"] == 7
        assert recovered["tombstone_count"] == 1 and recovered["production_activated"] is False
        assert (root / "backup/snapshot.age").read_bytes() == ciphertext
        private = root / "restored/private"
        with closing(ops.open_database(private / "api.sqlite3")) as db:
            surviving = ops.inventory(db, private, ops.Limits())
            assert surviving == {key: value for key, value in before.items() if value["project_id"] != projects[0]["id"]}
            assert db.execute("SELECT COUNT(*) FROM access_tokens").fetchone()[0] == 0
            assert db.execute("SELECT COUNT(*) FROM processing_jobs").fetchone()[0] == 3
            assert db.execute("SELECT project_id FROM deletion_receipts").fetchone()[0] == projects[0]["id"]
        assert not (private / "projects" / owner / projects[0]["id"]).exists()
        assert not (private / "derived" / owner / projects[0]["id"]).exists()
        from app.config import WorkerSettings
        from app.database import make_engine, reconcile_private_files
        from sqlalchemy.ext.asyncio import async_sessionmaker

        async def startup():
            engine = make_engine(WorkerSettings(private))
            try:
                await reconcile_private_files(WorkerSettings(private), async_sessionmaker(engine, expire_on_commit=False))
            finally:
                await engine.dispose()

        asyncio.run(startup())
        # Metadata contains paths/public recipient only, never identity contents.
        encoded_args = {name: str(value) if isinstance(value, Path) else value for name, value in vars(args).items()}
        ops.require(sources.verify(checkout, runtime, selected, Path(__file__).parents[2]) == provenance, "fixture_source_changed")
        ops.write_new(root / "integration.json", ops.canonical({"args": encoded_args, "receipt": recovered,
            "runtime_commit": runtime}))
    finally:
        try:
            next(fixture)
        except StopIteration:
            pass
        monkeypatch.undo()


if __name__ == "__main__":
    main()
