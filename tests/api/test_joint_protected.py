"""Actual native source transports and strict custody negatives, no inverse claim."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from uuid import UUID

import pytest

from app import joint_contract as contract


def test_no_numerical_import():
    script = "import sys;sys.path.insert(0,sys.argv[1]);import app.joint_contract;assert not {'numpy','simpeg','scipy','torch'} & set(sys.modules)"
    result = subprocess.run([sys.executable,'-B','-S','-c',script,str(Path(__file__).resolve().parents[2])],
        capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr


def test_external_only_storage_before_creation(tmp_path):
    assert contract.external_root(tmp_path)==tmp_path
    with pytest.raises(ValueError): contract.external_root(Path('relative'))
    with pytest.raises(ValueError): contract.external_root(Path(__file__).resolve().parents[2])


def source_rows():
    owner=UUID('11111111-1111-4111-8111-111111111111');project='22222222-2222-4222-8222-222222222222'
    asset=SimpleNamespace(id='33333333-3333-4333-8333-333333333333',owner_id=owner,project_id=project,
        source_id='44444444-4444-4444-8444-444444444444',sha256='a'*64,byte_count=128)
    source=SimpleNamespace(id=asset.source_id,owner_id=owner,project_id=project,sha256=asset.sha256,
        version=1,private_storage_permission='attested',rights_decision='provider-link-only')
    return owner,project,asset,source


def test_source_dependencies():
    owner,project,asset,source=source_rows()
    result=contract.source_identity(asset,source,owner_id=owner,project_id=project)
    assert result['source_version']==1 and result['raw_sha256']==asset.sha256
    for row,key,value in ((asset,'owner_id',UUID('55555555-5555-4555-8555-555555555555')),
            (source,'project_id','66666666-6666-4666-8666-666666666666'),
            (source,'rights_decision','forbidden'),(source,'private_storage_permission',None),
            (source,'sha256','b'*64),(source,'version',True),(asset,'byte_count',True)):
        before=getattr(row,key);setattr(row,key,value)
        try:
            with pytest.raises(ValueError): contract.source_identity(asset,source,owner_id=owner,project_id=project)
        finally: setattr(row,key,before)


@pytest.mark.parametrize('role',['development','sealed'])
def test_native_transport(role):
    root=os.environ.get('GEOPHYSICS_JOINT_MATRIX_FIXTURE')
    if not root: pytest.skip('explicit actual external full24 source fixture required')
    for i in range(24):
        directory=Path(root)/f'joint-control-{i:02d}'/role
        main='request.json' if role=='development' else 'sealed.json'
        raw=(directory/main).read_bytes();value,members=contract.manifest(raw,role)
        assert set(members)=={p.name for p in directory.iterdir()}
        for name,binding in members.items():
            content=(directory/name).read_bytes()
            assert hashlib.sha256(content).hexdigest()==binding['sha256']
            if binding['bytes'] is not None: assert len(content)==binding['bytes']
            if name.endswith('.npy'):
                descriptor=value['arrays'][name[:-4]]
                offset=contract.native_header(content[:4106],descriptor,len(content))
                assert hashlib.sha256(content[offset:]).hexdigest()==descriptor['data_sha256']
                with pytest.raises(ValueError): contract.native_header(b'PK\x03\x04'+content[4:4106],descriptor,len(content))
                changed=dict(descriptor,shape=[True])
                with pytest.raises(ValueError): contract.native_header(content[:4106],changed,len(content))


@pytest.mark.parametrize('raw',[b'{"a":1,"a":2}',b'{"a":NaN}',b'{"a":1e999}',
    b'['*9+b'0'+b']'*9,b'\xef\xbb\xbf{}',b' '*262145],ids=['duplicate','nan','overflow','depth','bom','bytes'])
def test_metadata_negatives(raw):
    with pytest.raises(ValueError): contract.bounded_json(raw)


def test_transport_caps_before_native_values():
    root=os.environ.get('GEOPHYSICS_JOINT_MATRIX_FIXTURE')
    if not root: pytest.skip('actual external native metadata required')
    raw=(Path(root)/'joint-control-00/development/request.json').read_bytes()
    original=json.loads(raw)
    for invalid in ([False],[4097],[1,1,1],[],[4096,4096]):
        value=json.loads(raw);d=value['arrays']['density_start'];d['shape']=invalid
        d['file_bytes']=128+(1 if invalid==[False] else __import__('math').prod(invalid))*8
        with pytest.raises(ValueError): contract.manifest(json.dumps(value).encode(),'development')
    value=json.loads(raw);value['raw_access']['gravity']['raw_present']=0
    with pytest.raises(ValueError): contract.manifest(json.dumps(value).encode(),'development')
    value=json.loads(raw);value['arrays']['../../escape']=value['arrays'].pop('density_start')
    with pytest.raises(ValueError): contract.manifest(json.dumps(value).encode(),'development')
    assert contract.manifest(raw,'development')[0]==original


@pytest.fixture
def joint_harness(make_harness,monkeypatch):
    # Mount the owned leaf through the real canonical assembly's auth/session
    # dependencies. This does not edit/mount MAIN or start an extra claimant.
    import app.server as server
    from app.joint_processing import install_joint_routes
    original=server.install_processing_routes
    def install(app,settings,current_user,get_session):
        original(app,settings,current_user,get_session)
        install_joint_routes(app,settings,current_user,get_session)
    monkeypatch.setattr(server,'install_processing_routes',install)
    return make_harness


def original_member(role,name):
    root=os.environ.get('GEOPHYSICS_JOINT_MATRIX_FIXTURE')
    if not root: pytest.skip('explicit actual external full24 source fixture required')
    directory=Path(root)/'joint-control-00'/role
    content=(directory/name).read_bytes()
    main='request.json' if role=='development' else 'sealed.json'
    value=json.loads((directory/main).read_bytes())
    descriptor=value['arrays'][name[:-4]] if name.endswith('.npy') else None
    return content,{'role':role,'name':name,'descriptor':descriptor,'source':{
        'provider':'Explicit local supplied original','rights_statement':'I attest permission to store this original privately.',
        'rights_decision':'mirror','private_storage_permission':'attested','attribution':'Local validation source',
        'expected_bytes':len(content),'expected_sha256':hashlib.sha256(content).hexdigest()}}


def upload_member(harness,project,role,name,*,body=None,metadata=None):
    original,meta=original_member(role,name)
    return harness.request('POST',f'/api/projects/{project}/joint-members',content=original if body is None else body,
        headers={'Content-Type':'application/octet-stream','X-Joint-Member-Metadata':json.dumps(meta if metadata is None else metadata)})


def test_real_native_upload_exact_private_lifecycle(joint_harness):
    import io
    import zipfile
    from app.server import create_app
    from fastapi.testclient import TestClient
    harness=joint_harness();harness.account();project=harness.project()['id'];receipts={}
    root=Path(os.environ['GEOPHYSICS_JOINT_MATRIX_FIXTURE'])/'joint-control-00'
    for role in ('development','sealed'):
        for path in sorted((root/role).iterdir()):
            response=upload_member(harness,project,role,path.name)
            assert response.status_code==201,response.text
            receipt=response.json();receipts[receipt['asset_id']]=(path,receipt)
            assert receipt['detected_format']=='joint_native'
            assert receipt['physical_metadata']['scientific_values_decoded'] is False
            assert receipt['physical_metadata']['scientific_accepted'] is False
            download=harness.request('GET',receipt['download_url'])
            assert download.status_code==200 and download.content==path.read_bytes()
            assert download.headers['x-content-sha256']==hashlib.sha256(download.content).hexdigest()
    # More than20 real native members complete without widening generic uploads.
    assert 20<len(receipts)<=40
    listing=harness.request('GET',f'/api/projects/{project}/assets')
    assert listing.status_code==200 and len(listing.json()['assets'])==len(receipts)
    exported=harness.request('GET',f'/api/projects/{project}/export')
    assert exported.status_code==200
    with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
        manifest=json.loads(archive.read('manifest.json'))
        for item in manifest['raw_assets']:
            path,receipt=receipts[item['asset_id']]
            assert archive.read(item['zip_member'])==path.read_bytes()
            assert item['sha256']==receipt['sha256']
    # Actual canonical startup audit accepts every row/file/quota relationship.
    async def local_mail(*args): pass
    with TestClient(create_app(harness.settings,local_mail)) as reopened:
        assert reopened.get('/api/auth/csrf').status_code==200
    response=harness.request('DELETE',f'/api/projects/{project}')
    assert response.status_code==200,response.text
    assert not list((harness.settings.data_dir/'projects').rglob('*.*'))
    assert list((harness.settings.data_dir/'.staging').iterdir())==[]
    with TestClient(create_app(harness.settings,local_mail)) as reopened:
        assert reopened.get('/api/auth/csrf').status_code==200


def test_member_source_rights_caps_headers_and_data(joint_harness):
    harness=joint_harness();harness.account();project=harness.project()['id']
    original,meta=original_member('development','density_start.npy')
    for field,value in (('name','../../escape'),('role','train'),('descriptor',dict(meta['descriptor'],shape=[True]))):
        changed=dict(meta);changed[field]=value
        assert upload_member(harness,project,'development','density_start.npy',metadata=changed).status_code==422
    for field,value in (('rights_decision','forbidden'),('private_storage_permission',None),('expected_bytes',True)):
        changed=json.loads(json.dumps(meta));changed['source'][field]=value
        assert upload_member(harness,project,'development','density_start.npy',metadata=changed).status_code==422
    changed=original[:-1]+bytes([original[-1]^1])
    assert upload_member(harness,project,'development','density_start.npy',body=changed).status_code==422
    # Source/file digest matches altered actual bytes, but data digest remains
    # independently checked and rejects the alteration.
    altered=json.loads(json.dumps(meta));digest=hashlib.sha256(changed).hexdigest()
    altered['source']['expected_sha256']=digest;altered['descriptor']['file_sha256']=digest
    assert upload_member(harness,project,'development','density_start.npy',body=changed,metadata=altered).status_code==422
    for magic in (b'PK\x03\x04',b'PK\x05\x06',b'\x1f\x8b',b'7z\xbc\xaf\x27\x1c',b'Rar!'):
        body=magic+original[len(magic):];altered=json.loads(json.dumps(meta));digest=hashlib.sha256(body).hexdigest()
        altered['source']['expected_sha256']=digest;altered['descriptor']['file_sha256']=digest
        assert upload_member(harness,project,'development','density_start.npy',body=body,metadata=altered).status_code==415
    assert harness.request('GET',f'/api/projects/{project}/assets').json()['assets']==[]
    assert list((harness.settings.data_dir/'.staging').iterdir())==[]


def test_native_quota_and_cross_owner(joint_harness):
    original,_=original_member('development','density_start.npy')
    # Respect canonical Settings: quota cannot be below maximum single upload.
    harness=joint_harness(max_upload_bytes=len(original),account_quota_bytes=len(original));harness.account();project=harness.project()['id']
    assert upload_member(harness,project,'development','density_start.npy').status_code==201
    assert upload_member(harness,project,'development','density_start.npy').status_code==507
    assert list((harness.settings.data_dir/'.staging').iterdir())==[]
    other=joint_harness();other.account();other_project=other.project()['id']
    uploaded=upload_member(other,other_project,'development','density_start.npy');assert uploaded.status_code==201
    other.account(email='another@example.org')
    assert other.request('GET',uploaded.json()['download_url']).status_code==404
    assert upload_member(other,other_project,'development','density_start.npy').status_code==404


def test_native_rate_bound_is_persistent(joint_harness):
    harness=joint_harness();harness.account();project=harness.project()['id']
    # Actual rejected byte streams still consume admission, not free retries.
    original,_=original_member('development','density_start.npy')
    changed=original[:-1]+bytes([original[-1]^1])
    for _ in range(80):
        assert upload_member(harness,project,'development','density_start.npy',body=changed).status_code==422
    assert upload_member(harness,project,'development','density_start.npy').status_code==429
    assert harness.request('GET',f'/api/projects/{project}/assets').json()['assets']==[]
    assert list((harness.settings.data_dir/'.staging').iterdir())==[]


@pytest.mark.parametrize('committed',[False,True],ids=['commit-not-confirmed','commit-written-response-lost'])
def test_uncertain_native_commit_preserves_actual_original(joint_harness,monkeypatch,committed):
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.server import create_app
    from fastapi.testclient import TestClient
    harness=joint_harness();harness.account();project=harness.project()['id']
    original_commit=AsyncSession.commit;triggered=False
    async def uncertain(session):
        nonlocal triggered
        root=harness.settings.data_dir/'projects'
        if not triggered and root.exists() and any(p.is_file() for p in root.rglob('*')):
            triggered=True
            if committed: await original_commit(session)
            raise RuntimeError('injected_unknown_commit_outcome')
        return await original_commit(session)
    monkeypatch.setattr(AsyncSession,'commit',uncertain)
    with pytest.raises(RuntimeError,match='injected_unknown_commit_outcome'):
        upload_member(harness,project,'development','density_start.npy')
    assert triggered
    actual=[p for p in (harness.settings.data_dir/'projects').rglob('*') if p.is_file()]
    assert len(actual)==1 and actual[0].read_bytes()==original_member('development','density_start.npy')[0]
    assert list((harness.settings.data_dir/'.staging').iterdir())==[]
    listing=harness.request('GET',f'/api/projects/{project}/assets')
    assert len(listing.json()['assets'])==int(committed)
    async def local_mail(*args): pass
    if committed:
        with TestClient(create_app(harness.settings,local_mail)) as reopened:
            assert reopened.get('/api/auth/csrf').status_code==200
    else:
        with pytest.raises(RuntimeError,match='private_recovery_required'):
            with TestClient(create_app(harness.settings,local_mail)): pass


def test_native_leaf_inherits_canonical_csrf_and_origin(joint_harness):
    harness=joint_harness();harness.account();project=harness.project()['id']
    body,meta=original_member('development','density_start.npy')
    headers={'Content-Type':'application/octet-stream','X-Joint-Member-Metadata':json.dumps(meta)}
    url=f'/api/projects/{project}/joint-members'
    assert harness.client.post(url,content=body,headers={**headers,'Origin':'http://testserver'}).status_code==403
    assert harness.client.post(url,content=body,headers={**headers,'Origin':'https://foreign.invalid',
        'X-CSRF-Token':harness.csrf}).status_code==403
    assert harness.request('GET',f'/api/projects/{project}/assets').json()['assets']==[]
