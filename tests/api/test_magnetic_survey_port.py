"""Review the isolated mount against real account/SQLite/security lifecycles."""
from pathlib import Path
import sqlite3

import pytest
from pydantic import ValidationError

from app.magnetic_survey_port import MagneticSurveyCapability, install_magnetic_survey_port


@pytest.fixture
def mounted(make_harness, monkeypatch):
    import app.server as server
    original = server.install_auth

    def capture(application, settings, sender):
        dependencies = original(application, settings, sender)
        install_magnetic_survey_port(application, *dependencies)
        return dependencies

    monkeypatch.setattr(server, "install_auth", capture)
    return make_harness


def test_closed_port_real_owner_and_security(mounted):
    owner = mounted()
    owner.account()
    project = owner.project()
    route = f"/api/projects/{project['id']}/magnetic-line-surveys"
    response = owner.request("GET", route + "/capability")
    assert response.status_code == 200
    assert response.json() == MagneticSurveyCapability().model_dump()
    before = sorted(str(p.relative_to(owner.settings.data_dir)) for p in owner.settings.data_dir.rglob("*") if p.is_file())
    # Body is deliberately not parsed or used as a path/executable/recipe.
    refused = owner.request("POST", route + "/jobs", content=b'{"root":"C:/",bad',
                            headers={"Content-Type": "application/json"})
    assert refused.status_code == 409
    assert refused.json()["code"] == "method_closed"
    after = sorted(str(p.relative_to(owner.settings.data_dir)) for p in owner.settings.data_dir.rglob("*") if p.is_file())
    assert after == before
    with sqlite3.connect(owner.settings.db_path) as connection:
        assert connection.execute('SELECT count(*) FROM processing_jobs').fetchone()[0] == 0
        assert connection.execute('SELECT count(*) FROM raw_assets').fetchone()[0] == 0
    assert owner.client.post(route + "/jobs", json={}).status_code == 403
    assert owner.request("POST", route + "/jobs", json={}, headers={"Origin": "https://foreign.invalid"}).status_code == 403
    assert owner.request("GET", "/api/projects/absent/magnetic-line-surveys/capability").status_code == 404
    assert owner.request("POST", "/api/projects/absent/magnetic-line-surveys/jobs", json={}).status_code == 404
    owner.request("POST", "/api/auth/cookie/logout")
    assert owner.request("GET", route + "/capability").status_code == 401
    assert owner.request("POST", route + "/jobs", json={}).status_code == 401
    owner.account(email="other@example.org")
    assert owner.request("GET", route + "/capability").status_code == 404
    assert owner.request("POST", route + "/jobs", json={}).status_code == 404
    own_project = owner.project("Deletion check")
    own_route = f"/api/projects/{own_project['id']}/magnetic-line-surveys"
    assert owner.request("DELETE", f"/api/projects/{own_project['id']}").status_code == 200
    assert owner.request("GET", own_route + "/capability").status_code == 404
    assert owner.request("POST", own_route + "/jobs", json={}).status_code == 404


def test_capability_is_closed_and_not_an_activation_switch():
    for key, value in (("online", "open"), ("field_acceptance", "pass"),
                       ("original_s1_predictive", "pass"), ("owner_lifecycle", "integrated"),
                       ("extra", "anything")):
        with pytest.raises(ValidationError):
            MagneticSurveyCapability.model_validate({key: value})


def test_mount_proposal_applies_only_to_owned_server():
    import subprocess
    root = Path(__file__).resolve().parents[2]
    proposal = root / "docs/design/features/m03-aeromagnetic-lines/api-mount-proposal.patch"
    subprocess.run(["git", "apply", "--check", str(proposal)], cwd=root, check=True)
    source = (root / "app/server.py").read_text(encoding="utf-8")
    assert "install_magnetic_survey_port" not in source
