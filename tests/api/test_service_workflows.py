"""Real migrated HTTPS-profile API replay; not actual Unix/systemd proof."""

from dataclasses import replace
from functools import partial
from pathlib import Path
import sys
import time

from fastapi.testclient import TestClient
import pytest

from app.accounts import provision_account
from app.server import create_app

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from qualify_api_workflows import Session, workflows  # noqa: E402

TEST_OWNER = {'username': 'owner@example.org', 'password': 'test-only-owner-password'}
TEST_OTHER = {'username': 'other@example.org', 'password': 'test-only-other-password'}


@pytest.fixture
def connection_factory(make_harness):
    harness = make_harness(auth_mode='local')
    settings = replace(harness.settings, public_origin='https://geophysics.ml.fasl-work.com', cookie_secure=True)
    harness.close()
    app = create_app(settings)
    with TestClient(app, base_url=settings.public_origin) as client:
        for account in (TEST_OWNER, TEST_OTHER):
            client.portal.call(partial(provision_account, app.state.sessions, account['username'], account['password']))

        class Response:
            def __init__(self, response):
                self.response = response
                self.status = response.status_code

            def getheaders(self):
                return self.response.headers.multi_items()

            def getheader(self, name):
                return self.response.headers.get(name)

            def read(self, bound):
                return self.response.content[:bound]

        class Connection:
            def __init__(self, path):
                self.response = None

            def request(self, method, path, *, body, headers):
                client.cookies.clear()  # ONLY the qualifier's independently held Cookie header applies.
                self.response = client.request(method, path, content=body, headers=headers)

            def getresponse(self):
                return Response(self.response)

            def close(self):
                pass

        yield Connection


def test_actual_api_auth_plural_raw_export_and_dataset(connection_factory):
    record = {}
    workflows('test-socket', TEST_OWNER, TEST_OTHER, time.monotonic() + 30, record, connection_factory)
    assert record['authenticated_workflows_passed'] is True
    assert record['qualification_projects_deleted'] is True
    assert len(set(record['qualification_projects'])) == 3
    assert record['worker_jobs_run'] == 0
    assert 'password' not in str(record) and 'test-only' not in str(record)


def test_same_account_never_creates_projects(connection_factory):
    record = {}
    with pytest.raises(ValueError, match='distinct'):
        workflows('test-socket', TEST_OWNER, TEST_OWNER, time.monotonic() + 30, record, connection_factory)
    assert record['qualification_projects'] == []
    assert record['authenticated_workflows_passed'] is False


def test_expired_session_never_requests(connection_factory):
    with pytest.raises(ValueError, match='deadline'):
        Session('test-socket', 0, connection_factory).request('GET', '/api/auth/config', 200)
