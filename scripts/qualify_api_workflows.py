"""Bounded real HTTP checks for newly owned qualification projects, no worker."""

from hashlib import sha256
from http.cookies import SimpleCookie
from io import BytesIO
import json
import re
import time
from urllib.parse import urlencode
import uuid
import zipfile

from verify_local_service import UnixConnection

ORIGIN = 'https://geophysics.ml.fasl-work.com'
MAX_RESPONSE = 262144
RAW = (b'station,x,y,z,g,sigma\nS1,0,0,100,1,0.1\nS2,10,0,100,2,0.1\n'
       b'S3,20,0,100,3,0.1\nS4,30,0,100,4,0.1\nS5,40,0,100,100,0.1\n')


def metadata():
    return {'filename': 'qualification-stations.csv', 'mime': 'text/csv', 'format': 'gravity_csv',
            'source': {'provider': 'Operator qualification',
                       'rights_statement': 'Original synthetic CSV authored for private service qualification.',
                       'rights_decision': 'mirror', 'private_storage_permission': 'attested',
                       'attribution': 'Internal transport control; not a geophysical field experiment',
                       'expected_bytes': len(RAW), 'expected_sha256': sha256(RAW).hexdigest()},
            'physical': {'coordinate_reference': 'epsg', 'epsg': 32719, 'axis_order': 'xy',
                         'horizontal_datum': 'WGS84', 'vertical_datum': 'synthetic local benchmark',
                         'vertical_positive': 'up', 'horizontal_unit': 'm', 'vertical_unit': 'm',
                         'measurement_unit': 'mGal', 'epoch_utc': '2026-10-04T00:00:00Z',
                         'component_frame': 'local vertical up',
                         'geometry': {'station_id_column': 'station', 'x_column': 'x', 'y_column': 'y',
                                      'z_column': 'z', 'value_column': 'g', 'sigma_column': 'sigma'}}}


class Session:
    def __init__(self, socket_path, deadline, connection_factory=UnixConnection):
        self.socket_path, self.deadline, self.factory = socket_path, deadline, connection_factory
        self.cookies = {}
        self.csrf = ''

    def request(self, method, path, expected, *, payload=None, raw=None, headers=None, guarded=True):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0 or not path.startswith('/api/') or '\r' in path or '\n' in path:
            raise ValueError('workflow deadline or route boundary')
        connection = self.factory(self.socket_path)
        connection.timeout = min(10, remaining)
        outgoing = {'Host': 'geophysics.ml.fasl-work.com', 'X-Forwarded-Proto': 'https',
                    'Accept': 'application/json', 'Cookie': '; '.join(f'{k}={v}' for k, v in self.cookies.items())}
        if guarded and method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            outgoing.update(Origin=ORIGIN, **{'X-CSRF-Token': self.csrf})
        body = raw
        if payload is not None:
            body = json.dumps(payload, allow_nan=False).encode('utf-8')
            outgoing['Content-Type'] = 'application/json'
        outgoing.update(headers or {})
        try:
            connection.request(method, path, body=body, headers=outgoing)
            response = connection.getresponse()
            response_headers = response.getheaders()
            data = response.read(MAX_RESPONSE + 1)
            if (sum(len(k) + len(v) for k, v in response_headers) > 16384 or len(data) > MAX_RESPONSE
                    or response.status != expected or response.getheader('Content-Encoding') not in (None, 'identity')):
                raise ValueError('workflow HTTP status/byte boundary')
            for key, value in response_headers:
                if key.lower() != 'set-cookie':
                    continue
                parsed = SimpleCookie()
                parsed.load(value)
                if len(parsed) != 1:
                    raise ValueError('unexpected cookie representation')
                for name, cookie in parsed.items():
                    if (name not in ('__Host-geophysics_csrf', '__Host-geophysics_session') or not cookie['secure']
                            or not cookie['httponly'] or cookie['samesite'].lower() != 'strict'
                            or cookie['path'] != '/' or cookie['domain']):
                        raise ValueError('HTTPS cookie restrictions differ')
                    if cookie['max-age'] == '0' or not cookie.value:
                        self.cookies.pop(name, None)
                    else:
                        if not re.fullmatch(r'[A-Za-z0-9_.~-]{1,1024}', cookie.value):
                            raise ValueError('invalid cookie value')
                        self.cookies[name] = cookie.value
            return data
        finally:
            connection.close()

    def object(self, method, path, expected=200, **kwargs):
        value = json.loads(self.request(method, path, expected, **kwargs))
        if not isinstance(value, dict):
            raise ValueError('workflow response must be object')
        return value

    def login(self, credentials):
        self.csrf = self.object('GET', '/api/auth/csrf')['csrf_token']
        self.request('POST', '/api/auth/cookie/login', 204, raw=urlencode(credentials).encode(),
                     headers={'Content-Type': 'application/x-www-form-urlencoded'})
        if '__Host-geophysics_session' not in self.cookies:
            raise ValueError('secure session absent')
        return self.object('GET', '/api/auth/me')['id']


def workflows(socket_path, owner, second, deadline, record, connection_factory=UnixConnection):
    """Only successful controls remove the exact three projects created here.

    Connection injection is an internal test seam, never a serialized option.
    Receipt records no account identifiers, cookies, credential bodies or errors.
    """
    owner_session = Session(socket_path, deadline, connection_factory)
    other_session = Session(socket_path, deadline, connection_factory)
    projects = record.setdefault('qualification_projects', [])
    record['authenticated_workflows_passed'] = False
    record['workflow_stage'] = 'separate_sessions'
    owner_id = owner_session.login(owner)
    other_id = other_session.login(second)
    if owner_id == other_id:
        raise ValueError('distinct real accounts required')
    record['workflow_stage'] = 'csrf_origin'
    owner_session.request('POST', '/api/projects', 403, payload={'name': 'must-not-exist'}, guarded=False)
    owner_session.request('POST', '/api/projects', 403, payload={'name': 'must-not-exist'},
                          headers={'Origin': 'https://cross-site.invalid'})
    record['workflow_stage'] = 'plural_projects'
    for session, label in ((owner_session, 'owner-a'), (owner_session, 'owner-b'), (other_session, 'other')):
        project = session.object('POST', '/api/projects', 201,
                                 payload={'name': 'Service qualification ' + label + ' ' + uuid.uuid4().hex,
                                          'description': 'Fresh synthetic transport check; not method acceptance.'})
        identifier = project.get('id')
        if not isinstance(identifier, str) or str(uuid.UUID(identifier)) != identifier or identifier in projects:
            raise ValueError('fresh project identity invalid')
        projects.append(identifier)
    first, additional, other_project = projects
    owner_session.object('PATCH', f'/api/projects/{additional}', payload={'description': 'Verified plural project update'})
    listing = owner_session.object('GET', '/api/projects')['projects']
    if not {first, additional}.issubset({p['id'] for p in listing}) or other_project in {p['id'] for p in listing}:
        raise ValueError('plural owner project listing differs')
    record['workflow_stage'] = 'immutable_original'
    asset = owner_session.object('POST', f'/api/projects/{first}/assets', 201, raw=RAW,
                                 headers={'Content-Type': 'text/csv', 'X-Asset-Metadata': json.dumps(metadata())})
    asset_id = asset['asset_id']
    if asset['sha256'] != sha256(RAW).hexdigest() or asset['byte_count'] != len(RAW):
        raise ValueError('immutable upload receipt differs')
    asset_path = f'/api/projects/{first}/assets/{asset_id}'
    if owner_session.request('GET', asset_path + '/download', 200) != RAW:
        raise ValueError('original byte replay differs')
    record['workflow_stage'] = 'processing_dataset'
    dataset = owner_session.object('POST', f'/api/projects/{first}/datasets', 201, payload={'asset_id': asset_id})
    dataset_path = f'/api/projects/{first}/datasets/{dataset["dataset_id"]}'
    owner_session.object('GET', dataset_path)
    record['workflow_stage'] = 'original_export'
    archive_bytes = owner_session.request('GET', f'/api/projects/{first}/export', 200)
    with zipfile.ZipFile(BytesIO(archive_bytes)) as archive:
        manifest = json.loads(archive.read('manifest.json'))
        assets = manifest['raw_assets']
        if len(assets) != 1 or assets[0]['sha256'] != sha256(RAW).hexdigest():
            raise ValueError('export receipt differs')
        member = assets[0]['zip_member']
        if archive.getinfo(member).file_size != len(RAW) or archive.read(member) != RAW:
            raise ValueError('export original differs')
    record['workflow_stage'] = 'cross_owner_isolation'
    for path in (f'/api/projects/{first}', asset_path, asset_path + '/download',
                 f'/api/projects/{first}/export', dataset_path):
        other_session.request('GET', path, 404)
    other_session.request('DELETE', f'/api/projects/{first}', 404)
    owner_session.request('GET', f'/api/projects/{other_project}', 404)
    # All preceding checks passed: delete only freshly recorded project IDs via API.
    record['workflow_stage'] = 'owned_project_deletion'
    for session, identifier in ((owner_session, first), (owner_session, additional), (other_session, other_project)):
        session.object('DELETE', f'/api/projects/{identifier}')
        session.request('GET', f'/api/projects/{identifier}', 404)
    record['workflow_stage'] = 'logout_revocation'
    for session in (owner_session, other_session):
        session.request('POST', '/api/auth/cookie/logout', 204)
        session.request('GET', '/api/auth/me', 401)
    record.update(authenticated_workflows_passed=True, qualification_projects_deleted=True,
                  raw_bytes=len(RAW), raw_sha256=sha256(RAW).hexdigest(), worker_jobs_run=0, workflow_stage='passed')
