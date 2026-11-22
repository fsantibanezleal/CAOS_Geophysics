"""Real owned SQLite boundary, but no privileged host or modeled success claim."""
import asyncio
from types import SimpleNamespace

import pytest

from app import profile_incomplete_recovery as recovery
from app.errors import ApiError
from test_profile_jobs import owned_dataset, profile_harness


@pytest.mark.parametrize("cancel",[True,False])
def test_real_owned_sql_is_checked_before_privilege_or_archive(make_harness,monkeypatch,cancel):
    harness = profile_harness(make_harness)
    project,_,dataset,metadata = owned_dataset(harness)
    path = f"/api/projects/{project['id']}/jobs"
    response = harness.request("POST",path,json=dict(dataset_id=dataset["dataset_id"],method_id=metadata["method"],parameters={}))
    assert response.status_code == 202
    identifier = response.json()["job_id"]
    if cancel:
        assert harness.request("POST",path+"/"+identifier+"/cancel").json()["state"] == "cancelled"
    calls = []
    class StopBeforePrivilege(RuntimeError):
        pass
    def command(settings,job,**kwargs):
        calls.append(job.id)
        assert settings == harness.settings and job.id == identifier and job.state == "cancelled"
        assert job.project_id == project["id"] and job.dataset_id == dataset["dataset_id"] and job.result_key is None
        assert kwargs == {"with_configuration":True}
        raise StopBeforePrivilege()
    monkeypatch.setattr(recovery,"os",SimpleNamespace(name="posix",geteuid=lambda:61901))
    monkeypatch.setattr(recovery,"installed_command",command)
    with pytest.raises(StopBeforePrivilege if cancel else ApiError):
        asyncio.run(recovery.recover_incomplete_job(harness.settings,identifier))
    assert calls == ([identifier] if cancel else [])
    assert not (harness.settings.data_dir/".profile-incomplete").exists()
    assert harness.client.get(path+"/"+identifier).json()["state"] == ("cancelled" if cancel else "queued")
