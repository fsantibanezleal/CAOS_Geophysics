"""Host-fixture recipe and orchestration; never labelled actual Linux host evidence."""

from contextlib import closing
from datetime import timedelta
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest

from scripts import ops_host_fixture as host
from scripts import ops_recovery as ops
from scripts import ops_source_pin as source
from tests.ops.test_source_pin import seal_bundle


@pytest.fixture
def runtime():
    selected = os.environ.get("GEOPHYSICS_OPS_MT_CHECKOUT")
    if not selected:
        pytest.skip("Explicit read-only MT fixture runtime needed")
    checkout = Path(selected).resolve(strict=True)
    assert (checkout / "app/mt_contract.py").is_file()
    return checkout


def call_fixture(runtime, root, mode, candidate=None):
    args = [sys.executable, "-B", str(host.RUNNER), mode]
    if candidate:
        args.append(str(candidate))
    args += [str(runtime), str(root)]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    env.pop("PYTHONPATH", None)
    return subprocess.run(args, cwd=runtime, env=env, capture_output=True, timeout=240)


def test_prepare_and_delete_cli(runtime, tmp_path):
    root = tmp_path / "state"
    prepared = call_fixture(runtime, root, "--prepare-state")
    assert prepared.returncode == 0, prepared.stderr.decode(errors="replace")[-4000:]
    marker = ops.read_json(root / "fixture-state.json")
    assert marker["main_owned"] and marker["nongate"] and marker["fixture_only"]
    assert marker["production_activated"] is False and len(marker["files"]) == 11
    assert not list(root.rglob("*.age")) and not list(root.rglob("*identity*"))
    assert not list(root.rglob("proof*.json"))
    source, database = Path(marker["source"]), Path(marker["database"])
    db_before = database.read_bytes()
    repeat = call_fixture(runtime, root, "--prepare-state")
    assert repeat.returncode != 0 and database.read_bytes() == db_before
    # Stale immutable raw state and a changed DB refuse deletion before API mutation.
    raw_name = next(name for name, item in marker["files"].items() if item["kind"] == "raw")
    raw = source / raw_name
    original_raw = raw.read_bytes()
    raw.write_bytes(original_raw + b"changed fixture bytes")
    refused = call_fixture(runtime, root, "--delete-fixture-project")
    assert refused.returncode != 0 and database.read_bytes() == db_before
    raw.write_bytes(original_raw)
    database.write_bytes(db_before + b"stale fixture bytes")
    refused = call_fixture(runtime, root, "--delete-fixture-project")
    assert refused.returncode != 0 and not (root / "fixture-deletion.json").exists()
    database.write_bytes(db_before)
    sentinel = root / "preserve-existing.txt"
    sentinel.write_bytes(b"not a key; preserve")
    deleted = call_fixture(runtime, root, "--delete-fixture-project")
    assert deleted.returncode == 0, deleted.stderr.decode(errors="replace")[-4000:]
    evidence = ops.read_json(root / "fixture-deletion.json")
    assert len(evidence["files"]) == 7 and evidence["project_id"] == marker["disposable_project_id"]
    assert evidence["external_backup_status"] == "pending_reconciliation"
    with closing(ops.open_database(database)) as db:
        assert ops.inventory(db, source, ops.Limits()) == evidence["files"]
        assert db.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == 2
        assert db.execute("SELECT COUNT(*) FROM deletion_receipts").fetchone()[0] == 1
    after = database.read_bytes()
    repeat = call_fixture(runtime, root, "--delete-fixture-project")
    assert repeat.returncode != 0 and database.read_bytes() == after
    assert sentinel.read_bytes() == b"not a key; preserve"


@pytest.mark.parametrize("case", ["repository", "relative", "unmarked", "linked"])
def test_fixture_boundary_rejection(runtime, tmp_path, case):
    mode = "--prepare-state"
    if case == "repository":
        root = runtime / "never-create-fixture"
    elif case == "relative":
        root = Path("never-create-fixture")
    elif case == "unmarked":
        root = tmp_path / "unmarked"
        root.mkdir(mode=0o700)
        mode = "--delete-fixture-project"
    else:
        root = tmp_path / "linked"
        destination = tmp_path / "destination"
        destination.mkdir()
        try:
            root.symlink_to(destination, target_is_directory=True)
        except OSError:
            pytest.skip("Ordinary symlink privilege unavailable")
    response = call_fixture(runtime, root, mode)
    assert response.returncode != 0
    if case in ("repository", "relative"):
        assert not (runtime / "never-create-fixture").exists()


def arguments(tmp_path):
    return host.parser().parse_args(["--new-fixture-root", str(tmp_path / "fixture"), "--runtime-checkout", str(tmp_path / "runtime"),
        "--runtime-commit", "0" * 40,
        "--age-binary", str(tmp_path / "age"), "--age-keygen-binary", str(tmp_path / "age-keygen"),
        "--units", "geophysics-ops-fixture-api.service", "geophysics-ops-fixture-worker.service"])


@pytest.mark.parametrize("case", ["platform", "disk", "units", "binary", "version", "existing"])
def test_host_platform_and_binary_guards(tmp_path, monkeypatch, case):
    args = arguments(tmp_path)
    (args.runtime_checkout / "app").mkdir(parents=True)
    (args.runtime_checkout / "app/mt_contract.py").write_bytes(b"fixture")
    (tmp_path / "age").write_bytes(b"fixture")
    (tmp_path / "age-keygen").write_bytes(b"fixture")
    monkeypatch.setattr(host, "linux_host", lambda: case != "platform")
    monkeypatch.setattr(host.shutil, "disk_usage", lambda path: SimpleNamespace(total=1_000_000_000, free=294_200_000 if case == "disk" else 400_000_000))
    if case == "units":
        args.units[0] = "geophysics-api.service"
    elif case == "existing":
        args.new_fixture_root.mkdir()
        (args.new_fixture_root / "preserve").write_bytes(b"existing")
    elif case == "version":
        monkeypatch.setattr(host.ops, "sha_file", lambda *args: host.AGE_SHA256)
        monkeypatch.setattr(host, "run_private", lambda *args, **kwargs: b"v1.1.1")
    expected = {"platform": "linux_fixture_only", "disk": "fixture_disk_headroom_failed",
        "units": "dummy_fixture_units_only", "binary": "fixture_binary_hash_mismatch",
        "version": "fixture_binary_version_mismatch", "existing": "new_target_required"}[case]
    with pytest.raises(ops.RecoveryError, match=expected):
        host.preflight(args)
    if case == "existing":
        assert (args.new_fixture_root / "preserve").read_bytes() == b"existing"
    else:
        assert not args.new_fixture_root.exists()


def test_dummy_state_checked_before_any_fixture_write(tmp_path, monkeypatch):
    args = arguments(tmp_path)
    (args.runtime_checkout / "app").mkdir(parents=True)
    (args.runtime_checkout / "app/mt_contract.py").write_bytes(b"fixture")
    monkeypatch.setattr(host, "linux_host", lambda: True)
    monkeypatch.setattr(host.shutil, "disk_usage", lambda path: SimpleNamespace(total=1_000_000_000, free=400_000_000))
    monkeypatch.setattr(host, "verify_binary", lambda path, expected: path)
    monkeypatch.setattr(host, "runtime_revision", lambda *a: {"controlled_test": True})
    observed = []
    def refused(unit):
        observed.append(unit)
        ops.require(False, "writer_not_stopped_masked")
    monkeypatch.setattr(ops.Maintenance, "check_unit", refused)
    with pytest.raises(ops.RecoveryError, match="writer_not_stopped_masked"):
        host.preflight(args)
    assert observed == ["geophysics-ops-fixture-api.service"] and not args.new_fixture_root.exists()


@pytest.mark.parametrize("failure", [None, "maintenance", "capture"])
def test_host_orchestration(runtime, tmp_path, monkeypatch, failure):
    """Real API + age + restore on Windows using an explicitly fixture-mode proof bridge.

    Only tests wiring; does NOT exercise actual Linux/systemd or Linux pinned executables.
    """
    args = arguments(tmp_path)
    root = args.new_fixture_root
    args.runtime_commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=runtime, capture_output=True, check=True).stdout.decode().strip()
    age, keygen = shutil.which("age"), shutil.which("age-keygen")
    assert age and keygen
    monkeypatch.setattr(host, "preflight", lambda args: (root, runtime, Path(age), Path(keygen), {"controlled_test": True}))
    real_prepare = ops.prepare

    def prepare_fixture(args):
        args.fixture_root = str(root)
        return real_prepare(args)

    monkeypatch.setattr(ops, "prepare", prepare_fixture)

    def fixture_proof(root, name, state, deployment, units):
        if failure == "maintenance":
            raise ops.RecoveryError("controlled_maintenance_failure")
        path = root / name
        ops.write_new(path, ops.canonical({"schema": ops.PROOF_SCHEMA, "source": state["source"], "database": state["database"],
            "deployment_id": deployment, "mode": "fixture", "issued_at": ops.stamp(),
            "expires_at": (ops.now() + timedelta(minutes=30)).isoformat(), "ingress_blocked": True,
            "all_writers_accounted": True, "units": []}))
        return path

    monkeypatch.setattr(host, "proof", fixture_proof)
    if failure == "capture":
        monkeypatch.setattr(ops, "capture", lambda args: ops.require(False, "controlled_capture_failure"))
    if failure:
        with pytest.raises(ops.RecoveryError, match="controlled_"):
            host.scenario(args)
        assert not (root / "main-owned-fixture-receipt.json").exists()
        assert (root / "state/fixture-state.json").exists()
    else:
        receipt = host.scenario(args)
        assert receipt["main_owned"] and receipt["nongate"] and receipt["fixture_only"]
        assert receipt["production_activated"] is False and receipt["release_accepted"] is False
        assert receipt["restored"]["surviving_file_count"] == 7 and receipt["restored"]["removed_file_count"] == 4
        assert receipt["restored"]["fixture_only"] is True  # Controlled test, not host evidence.
        assert receipt["key_escrow_tested"] is False and receipt["offhost_durability_tested"] is False
        assert (root / "backup/snapshot.age").exists() and (root / "fixture-identity.txt").exists()


def test_host_fixture_guide():
    guide = (Path(__file__).parents[2] / "docs/operations/02_isolated_host_fixture.md").read_text()
    for required in ("nongate", "main-owned", "30%", "not sigsum", host.AGE_SHA256, host.KEYGEN_SHA256,
                     "--prepare-state", "--delete-fixture-project", "dummy", "NOT RUN", "1.3.1/age/age"):
        assert required in guide


@pytest.mark.parametrize("case", ["stdout", "stderr", "timeout", "success"])
def test_child_output_and_time_caps(case):
    if case == "success":
        expected = b"fixture\r\n" if os.name == "nt" else b"fixture\n"
        assert host.run_private([sys.executable, "-B", "-c", "print('fixture')"], timeout=10) == expected
    elif case == "timeout":
        with pytest.raises(ops.RecoveryError, match="fixture_child_timeout"):
            host.run_private([sys.executable, "-B", "-c", "import time; time.sleep(2)"], timeout=.05)
    else:
        with pytest.raises(ops.RecoveryError, match="fixture_child_failed"):
            host.run_private([sys.executable, "-B", "-c", f"import sys; sys.{case}.write('x'*300000)"], timeout=10)


def test_selected_archive_actual_api_cli(runtime, tmp_path):
    """Real M05/M06/deletion through a no-Git selected archive; no Linux evidence."""
    copied_runtime, copied_ops = tmp_path / "runtime", tmp_path / "ops"
    copied_runtime.mkdir()
    copied_ops.mkdir()
    required = source.REQUIRED_RUNTIME | {path.relative_to(runtime).as_posix() for path in (runtime / "app").rglob("*")
                                          if path.is_file() and "__pycache__" not in path.parts}
    for tree, original, names in ((copied_runtime, runtime, required),
                                  (copied_ops, Path(__file__).parents[2], source.REQUIRED_OPS)):
        for name in names:
            destination = tree / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original / name, destination)
    args, manifest = seal_bundle(tmp_path, copied_runtime, copied_ops)
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=runtime, capture_output=True, check=True).stdout.decode().strip()
    manifest["runtime_commit"] = revision
    args.source_manifest.write_bytes(ops.canonical(manifest))
    args.source_manifest_sha256 = ops.sha_file(args.source_manifest, ops.JSON_CAP)
    root = tmp_path / "state"
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    env.pop("PYTHONPATH", None)
    def call(mode):
        return subprocess.run([sys.executable, "-B", str(copied_ops / "tests/ops/mt_drill.py"), mode,
            "--runtime-commit", revision, *source.source_options(args), str(copied_runtime), str(root)],
            cwd=copied_runtime, env=env, capture_output=True, timeout=240)
    prepared = call("--prepare-state")
    assert prepared.returncode == 0, prepared.stderr.decode(errors="replace")[-4000:]
    marker = ops.read_json(root / "fixture-state.json")
    assert marker["source_provenance"]["mode"] == "selected-archive" and len(marker["files"]) == 11
    assert not (copied_runtime / ".git").exists() and not (copied_ops / ".git").exists()
    database = Path(marker["database"])
    before = database.read_bytes()
    code = copied_runtime / "app/mt_contract.py"
    original = code.read_bytes()
    code.write_bytes(original + b"\n# drift\n")
    refused = call("--delete-fixture-project")
    assert refused.returncode != 0 and database.read_bytes() == before
    code.write_bytes(original)
    deleted = call("--delete-fixture-project")
    assert deleted.returncode == 0, deleted.stderr.decode(errors="replace")[-4000:]
    assert len(ops.read_json(root / "fixture-deletion.json")["files"]) == 7
    assert not list(root.rglob("*.age")) and not list(root.rglob("*identity*"))
