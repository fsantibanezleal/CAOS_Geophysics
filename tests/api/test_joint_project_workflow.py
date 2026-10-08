"""Real selected-project custody browser workflows; no new scientific fit.

The already-audited allocated application's lifespan remains open. This does
not claim a separately admitted restart, canonical MAIN mount or host grant.
"""
import asyncio
from functools import partial
import hashlib
import json
import os
from pathlib import Path
import queue
import shutil
import socket
import sqlite3
import subprocess
import threading
import time
from uuid import UUID, uuid4

import uvicorn
from sqlalchemy import text

from app import joint_execution as ex, joint_result as result
from app.models import ProcessingJob
from test_joint_protected import joint_harness as joint_harness
from test_joint_successor import successor as successor, allocated_harness as allocated_harness
from test_joint_datasets import upload_pair, create_dataset


def test_actual_selected_project_custody_browser(allocated_harness, monkeypatch, tmp_path):
    import conftest
    from app import server
    from app.accounts import provision_account
    root = Path(__file__).resolve().parents[2]
    ex.ordinary(tmp_path, directory=True, external=True)
    output = Path(os.environ['GEOPHYSICS_JOINT_INSTRUMENT_FIXTURE'])
    ex.ordinary(output, directory=True, external=True)
    node = shutil.which('node')
    assert node, 'Actual Node/browser dependencies required'
    paths = ('app/joint_result.py', 'app/joint_archive.py', 'app/joint_models.py', 'app/joint_datasets.py',
        'app/joint_processing.py', 'app/joint_contract.py', 'app/joint_roots.py',
        'app/migrations/candidates/0006_joint_artifacts.py', 'frontend/src/api/client.ts',
        'frontend/src/api/lifecycle.ts', 'frontend/src/api/joint-custody.ts',
        'frontend/src/api/joint-input.ts', 'frontend/src/api/joint-result.ts',
        'frontend/src/components/JointNativeInputPanel.tsx',
        'frontend/src/components/JointProjectWorkbench.tsx',
        'frontend/src/components/JointResultWorkbench.tsx',
        'frontend/src/components/ScientificPlots.tsx', 'frontend/src/styles.css',
        'frontend/src/data/citations.ts', 'frontend/e2e/joint-project-server.mjs',
        'frontend/e2e/joint-project-workflow.spec.ts', 'tests/api/test_joint_project_workflow.py')
    def pins(): return {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in paths}
    before = pins()
    public = tmp_path / 'public-project.json'
    public.write_text('{}', encoding='utf8')
    sock = socket.socket(); sock.bind(('127.0.0.1', 0))
    command = [node, str(root / 'frontend/e2e/joint-project-server.mjs'),
        f'http://127.0.0.1:{sock.getsockname()[1]}', str(public), str(tmp_path / 'vite-cache')]
    process = subprocess.Popen(command, cwd=root / 'frontend', stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, encoding='utf8',
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    lines = queue.Queue()
    def read_lines():
        for line in process.stdout: lines.put(line)
    threading.Thread(target=read_lines, daemon=True).start()
    service = None; thread = None
    try:
        deadline = time.monotonic() + 30; origin = None; diagnostics = []
        while time.monotonic() < deadline and origin is None:
            try: line = lines.get(timeout=.1)
            except queue.Empty:
                assert process.poll() is None, ''.join(diagnostics)[-4000:]
                continue
            diagnostics.append(line)
            try: origin = json.loads(line).get('origin')
            except json.JSONDecodeError: pass
        assert origin and origin.startswith('http://127.0.0.1:'), ''.join(diagnostics)[-6000:]
        (tmp_path / 'startup-observation.json').write_text(json.dumps(diagnostics), encoding='utf8')
        original_settings = conftest.Settings
        def settings(**values): return original_settings(**{**values, 'public_origin': origin})
        monkeypatch.setattr(conftest, 'Settings', settings)
        original_install = server.install_processing_routes
        def install(app, config, current_user, get_session):
            original_install(app, config, current_user, get_session)
            result.install_joint_result_routes(app, config, current_user, get_session)
        monkeypatch.setattr(server, 'install_processing_routes', install)
        harness = allocated_harness(auth_mode='local')
        original_request = harness.request
        def request(method, path, *, headers=None, **values):
            return original_request(method, path, headers={'Origin': origin, **(headers or {})}, **values)
        harness.request = request
        def local(email):
            password = 'private-actual-selected-custody-872'
            harness.client.portal.call(partial(provision_account, harness.app.state.sessions, email, password))
            login = harness.request('POST', '/api/auth/cookie/login', data={'username': email, 'password': password})
            assert login.status_code == 204, login.text
            return harness.client.get('/api/auth/me').json()['id']
        owner = local('selected-custody-owner@example.org')
        project = harness.project('Actual selected native archival project')
        other_project = harness.project('Other owned native project')
        indexed = create_dataset(harness, project['id'], upload_pair(harness, project['id']))
        assert indexed.status_code == 201, indexed.text
        dataset = indexed.json(); job_id = str(uuid4())
        request_value = {'schema': 'custody-test-historical-native-bytes/v1', 'execution_performed': False}
        request_sha = ex.digest(ex.canonical(request_value))
        async def retain():
            async with harness.app.state.sessions() as session:
                await session.execute(text('BEGIN IMMEDIATE'))
                job = ProcessingJob(id=job_id, owner_id=UUID(owner), project_id=project['id'],
                    dataset_id=dataset['dataset_id'], dataset_sha256=dataset['sha256'],
                    method_id=result.METHOD, request_json=request_value, request_sha256=request_sha,
                    preflight={'scientific_execution': False}, state='failed', error_code='custody_fixture_no_execution')
                session.add(job); await session.flush()
                members = result.inventory(output)
                receipt = await result.retain_terminal_output(harness.settings, session, job, output,
                    available_bytes=512 * 1024**2,
                    retained_bytes=sum(item['byte_count'] for item in members.values()))
                await session.commit(); return receipt
        print('Actual selected browser: retaining original failed archival job, no inverse', flush=True)
        payload = asyncio.run(retain()); original_inventory = result.inventory(output)
        cookies = [{'name': key, 'value': value} for key, value in harness.client.cookies.items()]
        foreign_owner = local('selected-custody-other@example.org')
        foreign_cookies = [{'name': key, 'value': value} for key, value in harness.client.cookies.items()]
        assert foreign_owner != owner and harness.messages == []
        data = {'project_id': project['id'], 'project_name': project['name'],
            'other_project_id': other_project['id'], 'other_project_name': other_project['name']}
        public.write_text(json.dumps(data), encoding='utf8')
        fixture = tmp_path / 'actual-browser-project.json'; evidence = tmp_path / 'browser-evidence'
        fixture.write_text(json.dumps({**data, 'origin': origin, 'job_id': job_id,
            'request_sha256': request_sha, 'cookies': cookies, 'other_cookies': foreign_cookies,
            'index': payload, 'evidence': str(evidence)}), encoding='utf8')
        # Use the held, successfully entered application, not a skipped failed
        # startup or a patched recovery audit. Its real owner/CSRF routes execute.
        service = uvicorn.Server(uvicorn.Config(harness.app, lifespan='off', log_level='error', access_log=False))
        thread = threading.Thread(target=lambda: service.run(sockets=[sock]), daemon=True); thread.start()
        deadline = time.monotonic() + 30
        while not service.started and thread.is_alive() and time.monotonic() < deadline: time.sleep(.02)
        assert service.started
        config = tmp_path / 'playwright.config.mjs'
        config.write_text('export default ' + json.dumps({'testDir': str(root / 'frontend/e2e'),
            'testMatch': 'joint-project-workflow.spec.ts', 'workers': 1, 'maxFailures': 1,
            'outputDir': str(tmp_path / 'browser-results'),
            'reporter': [['list'], ['json', {'outputFile': str(tmp_path / 'browser-receipt.json')}]],
            'use': {'headless': True, 'trace': 'retain-on-failure'}}) + ';', encoding='utf8')
        env = {**os.environ, 'GEOPHYSICS_JOINT_PROJECT_BROWSER_FIXTURE': str(fixture),
            'TEMP': str(tmp_path), 'TMP': str(tmp_path)}
        browser_command = [node, str(root / 'frontend/node_modules/@playwright/test/cli.js'), 'test', '--config=' + str(config)]
        grep = os.environ.get('GEOPHYSICS_JOINT_PROJECT_BROWSER_GREP')
        assert grep is None or grep == 'actual selected project read cancellation', 'Only explicit targeted privacy regression supported'
        if grep: browser_command += ['--grep', grep]
        expected = 1 if grep else 9
        print(f'Actual selected browser: {expected} local-route workflows starting', flush=True)
        completed = subprocess.run(browser_command, cwd=root / 'frontend', env=env,
            timeout=900)
        assert completed.returncode == 0, 'Actual browser workflow failed; preserve its JSON/trace receipt'
        receipt = json.loads((tmp_path / 'browser-receipt.json').read_text(encoding='utf8'))
        assert receipt['stats']['expected'] == expected
        assert receipt['stats']['unexpected'] == receipt['stats']['skipped'] == receipt['stats']['flaky'] == 0
        assert pins() == before and result.inventory(output) == original_inventory
        with sqlite3.connect(harness.settings.db_path) as db:
            assert db.execute('SELECT state,error_code FROM processing_jobs').fetchall() == [('failed', 'custody_fixture_no_execution')]
            assert db.execute('SELECT count(*) FROM joint_result_artifacts').fetchone() == (len(payload['members']),)
            assert db.execute('SELECT count(*) FROM joint_dataset_sources').fetchone() == (36,)
            assert db.execute('PRAGMA foreign_key_check').fetchall() == []
        assert harness.messages == []
        (tmp_path / 'source-pins.json').write_text(json.dumps(before, sort_keys=True), encoding='utf8')
        print(f'Actual selected custody browser{expected}PASS, no scientific execution or canonical parent admission', flush=True)
    finally:
        if service is not None: service.should_exit = True
        if thread is not None: thread.join(timeout=15)
        if thread is not None and thread.is_alive(): service.force_exit = True; thread.join(timeout=5)
        process.terminate()
        try: process.wait(timeout=10)
        except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)
        sock.close()
