"""Isolated integration runner; imports exactly one explicitly selected MT app tree.

Called by test_backup_mt, not an operator/production utility. All writes are fixtures.
"""

from __future__ import annotations

import asyncio
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


def main():
    checkout, root = (Path(item).resolve(strict=True) for item in sys.argv[1:])
    assert root != checkout and not root.is_relative_to(checkout)
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["MPLCONFIGDIR"] = str(root / "mpl")
    sys.path.insert(0, str(checkout))
    spec = importlib.util.spec_from_file_location("ops_recovery", Path(__file__).parents[2] / "scripts/ops_recovery.py")
    ops = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = ops
    spec.loader.exec_module(ops)
    import pytest
    from fastapi.testclient import TestClient
    from tests.api.conftest import ApiHarness, make_harness
    from tests.api.test_online_mt import NATIVE, LAYERED, upload_dataset, submit, complete
    from app.mt_contract import M05_ID, M06_ID
    from app.processing_contract import METHOD_ID
    from app.worker import run_one

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
        ops.write_new(root / "integration.json", ops.canonical({"args": encoded_args, "receipt": recovered,
            "runtime_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=checkout, capture_output=True, check=True).stdout.decode().strip()}))
    finally:
        try:
            next(fixture)
        except StopIteration:
            pass
        monkeypatch.undo()


if __name__ == "__main__":
    main()
