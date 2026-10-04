"""Local release-contract tests, not actual-host or scientific acceptance."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))


def module():
    spec = importlib.util.spec_from_file_location("service_release", ROOT / "scripts/prepare_service_release.py")
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def fixture(tmp_path):
    source = tmp_path / "source"
    build = source / "frontend/dist"
    build.mkdir(parents=True)
    (source / "app").mkdir()
    (source / "app/main.py").write_text("app = None\n", encoding="utf-8")
    (build / "index.html").write_text('<script src="/assets/a.js"></script>', encoding="utf-8")
    (build / "assets").mkdir()
    (build / "assets/a.js").write_bytes(b"actual reviewed bytes\x00")
    return source, build


def test_release_admission():
    service = module()
    unresolved = [{"id": f"R-{i:03}", "verdict": "pass"} for i in range(1, 20)]
    unresolved[16]["verdict"] = "unresolved"
    unresolved[17]["verdict"] = "unresolved"
    service.require_pre_cutover({"requirements": unresolved})
    unresolved[7]["verdict"] = "fail"
    with pytest.raises(ValueError, match="R-008"):
        service.require_pre_cutover({"requirements": unresolved})
    with pytest.raises(ValueError):
        service.require_pre_cutover({"requirements": unresolved[:-1]})


def test_external_reviewed_build_has_same_policy(tmp_path):
    from check_single_origin import check
    build = tmp_path / 'external-build'
    (build / 'assets').mkdir(parents=True)
    (build / 'index.html').write_text('<script src="/assets/reviewed.js"></script>', encoding='utf-8')
    assert check(ROOT, built=True, build_dir=build) == []
    (build / 'index.html').write_text('<script src="assets/not-root.js"></script>', encoding='utf-8')
    assert any('root-relative' in e for e in check(ROOT, built=True, build_dir=build))
    (build / 'index.html').write_text('<script src="/assets/reviewed.js"></script>', encoding='utf-8')
    (build / 'CNAME').write_text('secondary.example.org', encoding='ascii')
    assert any('CNAME' in e for e in check(ROOT, built=True, build_dir=build))


def test_external_build_requires_absolute_nontraversing_existing_path(tmp_path):
    from check_single_origin import check
    assert any('unsafe' in e for e in check(ROOT, built=True, build_dir=Path('relative-build')))
    assert any('unsafe' in e for e in check(ROOT, built=True, build_dir=tmp_path / 'other/../build'))
    assert any('unsafe' in e for e in check(ROOT, built=True, build_dir=tmp_path / 'absent'))
    assert any('requires built' in e for e in check(ROOT, build_dir=tmp_path))


def test_bundle_integrity(tmp_path):
    service = module()
    source, build = fixture(tmp_path)
    out = tmp_path / "candidate"
    receipt = service.copy_bundle(source, build, out, ["app/main.py"], "a" * 40)
    assert receipt["qualification_only"] is True
    assert receipt["full_release_accepted"] is False
    assert (out / "web/assets/a.js").read_bytes() == b"actual reviewed bytes\x00"
    assert (out / "source/app/main.py").read_bytes() == (source / "app/main.py").read_bytes()
    assert service.verify_bundle(out) == receipt
    with pytest.raises(FileExistsError):
        service.copy_bundle(source, build, out, ["app/main.py"], "a" * 40)
    (out / "web/assets/a.js").write_bytes(b"changed")
    with pytest.raises(ValueError, match="integrity"):
        service.verify_bundle(out)


@pytest.mark.parametrize("name", ["../secret", "/absolute", "app/../secret", "app\\secret", "app/a:b", "app/a.", "app/CON.py"])
def test_bad_paths(name):
    with pytest.raises(ValueError):
        module().safe_relative(name)


def test_symlink_rejected(tmp_path):
    service = module()
    source, build = fixture(tmp_path)
    target = tmp_path / "outside"
    target.write_bytes(b"not a public asset")
    try:
        (build / "linked").symlink_to(target)
    except OSError as exc:
        pytest.skip(f"OS denies creation of test-only symlink: {exc}")
    with pytest.raises(ValueError, match="link"):
        service.copy_bundle(source, build, tmp_path / "candidate", ["app/main.py"], "a" * 40)
    assert not (tmp_path / "candidate").exists()


def test_fail_closed(tmp_path):
    service = module()
    source, build = fixture(tmp_path)
    with pytest.raises(ValueError):
        service.copy_bundle(source, build, source / "app/nested", ["app/main.py"], "a" * 40)
    with pytest.raises(ValueError):
        service.copy_bundle(source, build, tmp_path / "bad", ["app/main.py"], "not-a-revision")
    out = tmp_path / "candidate"
    service.copy_bundle(source, build, out, ["app/main.py"], "a" * 40)
    (out / "web/unlisted.txt").write_text("unexpected", encoding="utf-8")
    with pytest.raises(ValueError, match="inventory"):
        service.verify_bundle(out)


def test_bounds_and_duplicate_manifest(tmp_path, monkeypatch):
    service = module()
    source, build = fixture(tmp_path)
    monkeypatch.setattr(service, "MAX_FILES", 2)
    with pytest.raises(ValueError, match="bound"):
        service.copy_bundle(source, build, tmp_path / "candidate", ["app/main.py"], "a" * 40)
    assert not (tmp_path / "candidate").exists()
    with pytest.raises(ValueError, match="duplicate"):
        service.strict_json(b'{"a":1,"a":2}')
    with pytest.raises(ValueError):
        service.strict_json(b'{"a":NaN}')


def test_service_boundaries():
    socket = (ROOT / "deploy/service/geophysics-api.socket").read_text(encoding="utf-8")
    api = (ROOT / "deploy/service/geophysics-api.service").read_text(encoding="utf-8")
    nginx = (ROOT / "deploy/service/geophysics.nginx").read_text(encoding="utf-8")
    assert "SocketMode=0660" in socket and "SocketGroup=www-data" in socket
    assert "--fd 3" in api and "--host" not in api and "PrivateNetwork=yes" in api
    assert "root /var/www/geophysics.ml.fasl-work.com/current/web;" in nginx
    assert "proxy_pass http://unix:/run/geophysics-api/api.sock:;" in nginx
    assert "proxy_set_header X-Forwarded-Proto $scheme;" in nginx
    assert "proxy_set_header X-Forwarded-For $remote_addr;" in nginx
    assert "proxy_cache off;" in nginx and "proxy_intercept_errors off;" in nginx
    assert "location ^~ /api/" in nginx


def test_worker_isolation():
    api = (ROOT / "deploy/service/geophysics-api.service").read_text(encoding="utf-8")
    worker = (ROOT / "deploy/service/geophysics-worker.service").read_text(encoding="utf-8")
    assert "EnvironmentFile=/etc/geophysics/api.env" in api
    assert "EnvironmentFile=/etc/geophysics/worker.env" in worker
    assert "api.env" not in worker and "GEOPHYSICS_AUTH_SECRET" not in worker
    assert "MemoryMax=2G" in worker and "MemorySwapMax=0" in worker
    for text in (api, worker):
        assert "User=geophysics" in text and "KillMode=control-group" in text
        assert "ProtectSystem=strict" in text and "NoNewPrivileges=yes" in text
        assert "ReadWritePaths=/var/lib/geophysics" in text


def test_capacity_and_retention(tmp_path):
    service = module()
    releases = tmp_path / "releases"
    releases.mkdir()
    for name in ("release-a", "release-b", "release-c"):
        (releases / name).mkdir()
        (releases / name / "member").write_bytes(b"123")
    assert service.retained_inventory(releases, "release-a", ["release-b", "release-c"]) == [
        {"id": "release-a", "role": "current", "bytes": 3},
        {"id": "release-b", "role": "rollback", "bytes": 3},
        {"id": "release-c", "role": "rollback", "bytes": 3},
    ]
    with pytest.raises(ValueError):
        service.retained_inventory(releases, "release-a", ["release-a", "release-c"])
    assert service.mem_available("MemTotal: 8000 kB\nMemAvailable: 4000 kB\n") == 4096000
    with pytest.raises(ValueError):
        service.mem_available("MemTotal: 8000 kB\n")


def test_activation_and_rollback():
    # Ordering is tested against the real committed installer, not called on this workstation.
    text = (ROOT / "deploy/activate-service.sh").read_text(encoding="utf-8")
    assert text.index("verify_bundle") < text.index("systemctl stop")
    assert text.index("require_pre_cutover") < text.index("systemctl stop")
    assert "trap rollback ERR" in text and "nginx -t" in text
    assert "alembic downgrade" not in text and "rm -rf" not in text
    assert "GEOPHYSICS_AUTH_SECRET" not in text


def test_empty_directory_bound(tmp_path, monkeypatch):
    service = module()
    root = tmp_path / "inventory"
    root.mkdir()
    for i in range(3):
        (root / str(i)).mkdir()
    monkeypatch.setattr(service, "MAX_ENTRIES", 2)
    with pytest.raises(ValueError, match="entry bound"):
        service.inventory(root)


def test_dotdot_absolute_path(tmp_path):
    with pytest.raises(ValueError):
        module().no_links(tmp_path / "folder/../other")


def test_insufficient_local_destination_before_writes(tmp_path, monkeypatch):
    service = module()
    source, build = fixture(tmp_path)
    monkeypatch.setattr(service.shutil, "disk_usage", lambda p: SimpleNamespace(free=0))
    out = tmp_path / "candidate"
    with pytest.raises(ValueError, match="destination capacity"):
        service.copy_bundle(source, build, out, ["app/main.py"], "a" * 40)
    assert not out.exists()
