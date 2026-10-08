"""Real loopback browser custody, explicit allocated fixture; no host/science grant."""
from __future__ import annotations

from dataclasses import replace
from functools import partial
import json
import hashlib
import os
from pathlib import Path
import queue
import shutil
import socket
import sqlite3
import subprocess
import threading
import time

import pytest
import uvicorn

from test_joint_protected import joint_harness
from test_joint_successor import successor, allocated_harness


def test_actual_allocated_browser_input_custody(allocated_harness, tmp_path):
    from app.accounts import provision_account
    from app.server import create_app
    from app.joint_contract import external_root
    external_root(tmp_path)
    source = os.environ.get('GEOPHYSICS_JOINT_MATRIX_FIXTURE')
    if not source: pytest.fail('Explicit actual original matrix fixture required, no skipped browser gate')
    node = shutil.which('node')
    if not node: pytest.fail('Actual Node runtime required')
    root = Path(__file__).resolve().parents[2]
    source_files=('frontend/src/api/client.ts','frontend/src/api/joint-input.ts',
        'frontend/src/api/joint-result.ts','frontend/src/components/JointNativeInputPanel.tsx',
        'frontend/e2e/joint-native-input-server.mjs','frontend/e2e/joint-native-input.spec.ts',
        'app/joint_processing.py','app/joint_datasets.py','app/joint_roots.py','app/joint_models.py',
        'app/migrations/candidates/0006_joint_artifacts.py')
    def hashes(): return {name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in source_files}
    source_pins=hashes()
    harness = allocated_harness(auth_mode='local'); cases=[]
    # Nine actual local owners; no email transport or weakened10/auth window.
    for index in range(9):
        email=f'native-browser-{index}@example.org'; password='private-test-local-password-872'
        harness.client.portal.call(partial(provision_account,harness.app.state.sessions,email,password))
        response=harness.request('POST','/api/auth/cookie/login',data={'username':email,'password':password})
        assert response.status_code==204,response.text
        owner=harness.client.get('/api/auth/me').json()['id']
        project=harness.project(f'Actual original browser {index}')['id']; other=harness.project(f'Privacy reset {index}')['id']
        cases.append({'owner_id':owner,'project_id':project,'other_project_id':other,
            'cookies':[{'name':key,'value':value} for key,value in harness.client.cookies.items()]})
    harness.close()
    public=tmp_path/'public-cases.json'
    public.write_text(json.dumps([{k:v for k,v in item.items() if k!='cookies'} for item in cases]),encoding='utf-8')
    sock=socket.socket();sock.bind(('127.0.0.1',0));api_port=sock.getsockname()[1]
    command=[node,str(root/'frontend/e2e/joint-native-input-server.mjs'),f'http://127.0.0.1:{api_port}',str(public),str(tmp_path/'vite-cache')]
    process=subprocess.Popen(command,cwd=root/'frontend',stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8')
    lines=queue.Queue()
    def output():
        for line in process.stdout: lines.put(line)
    reader=threading.Thread(target=output,daemon=True);reader.start()
    server=None;thread=None
    try:
        expires=time.monotonic()+30; origin=None;diagnostics=[]
        while time.monotonic()<expires and origin is None:
            try: line=lines.get(timeout=.1)
            except queue.Empty:
                if process.poll() is not None: pytest.fail('Private component fixture failed to start: '+''.join(diagnostics)[-4000:])
                continue
            diagnostics.append(line)
            try: origin=json.loads(line).get('origin')
            except json.JSONDecodeError: pass
        assert origin and origin.startswith('http://127.0.0.1:'),'Explicit local fixture not ready'
        settings=replace(harness.settings,public_origin=origin)
        async def mail(*args): raise AssertionError('No SMTP path permitted in local-user fixture')
        app=create_app(settings,mail)
        server=uvicorn.Server(uvicorn.Config(app,log_level='error',access_log=False))
        thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True);thread.start()
        expires=time.monotonic()+30
        while not server.started and time.monotonic()<expires and thread.is_alive(): time.sleep(.02)
        assert server.started,'Actual allocated authenticated ASGI fixture not ready'
        evidence=tmp_path/'browser-evidence'; fixture=tmp_path/'browser-fixture.json'
        fixture.write_text(json.dumps({'origin':origin,'cases':cases,'originals':str(Path(source)/'joint-control-00'),'evidence':str(evidence)}),encoding='utf-8')
        config=tmp_path/'playwright.config.mjs'
        config.write_text('export default '+json.dumps({'testDir':str(root/'frontend/e2e'),
            'testMatch':'joint-native-input.spec.ts','workers':1,'maxFailures':1,'outputDir':str(tmp_path/'browser-results'),
            'reporter':[['list'],['json',{'outputFile':str(tmp_path/'browser-receipt.json')}]],
            'use':{'headless':True,'trace':'retain-on-failure'}})+';',encoding='utf-8')
        env={**os.environ,'GEOPHYSICS_JOINT_INPUT_BROWSER_FIXTURE':str(fixture),'TEMP':str(tmp_path),'TMP':str(tmp_path)}
        result=subprocess.run([node,str(root/'frontend/node_modules/@playwright/test/cli.js'),'test','--config='+str(config)],
            cwd=root/'frontend',env=env,capture_output=True,text=True,encoding='utf-8',timeout=600)
        assert result.returncode==0,result.stdout[-24000:]+result.stderr[-12000:]
        receipt=json.loads((tmp_path/'browser-receipt.json').read_text(encoding='utf-8'))
        assert receipt['stats']['expected']==9 and receipt['stats']['unexpected']==receipt['stats']['skipped']==receipt['stats']['flaky']==0
        assert hashes()==source_pins,'Source changed during actual protected browser gate'
        (tmp_path/'source-pins.json').write_text(json.dumps(source_pins,sort_keys=True),encoding='utf-8')
        with sqlite3.connect(settings.db_path) as db:
            assert db.execute('SELECT version_num FROM alembic_version').fetchall()==[('0006_joint_artifacts',)]
            assert db.execute('SELECT count(*) FROM joint_dataset_sources').fetchone()==(324,)
            assert db.execute('SELECT count(*) FROM physical_dataset_families').fetchone()==(9,)
            assert db.execute('SELECT count(*) FROM processing_jobs').fetchone()==(0,)
            assert db.execute('PRAGMA foreign_key_check').fetchall()==[]
            for item in cases:
                count=db.execute('SELECT count(*) FROM raw_assets WHERE owner_id=? AND project_id=?',(item['owner_id'],item['project_id'])).fetchone()[0]
                assert 36<=count<=40  # Explicit cancel may retain an uncertain original.
                assert db.execute('SELECT published_count,reserved_count,state FROM physical_dataset_families WHERE owner_id=?',(item['owner_id'],)).fetchall()==[(1,0,'published')]
        print('Actual native custody browser9PASS; no inverse, canonical mount or host/scientific admission')
    finally:
        if server is not None: server.should_exit=True
        if thread is not None: thread.join(timeout=15)
        if thread is not None and thread.is_alive(): server.force_exit=True;thread.join(timeout=5)
        process.terminate()
        try: process.wait(timeout=10)
        except subprocess.TimeoutExpired: process.kill();process.wait(timeout=5)
        sock.close()
