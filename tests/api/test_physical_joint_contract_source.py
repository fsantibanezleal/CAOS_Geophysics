"""Light source/native-envelope contracts; no fits, API or native admission."""

import ast
import io
from pathlib import Path
import subprocess

import pytest

from app import physical_joint_native_contract as native
from app import physical_joint_dataset_contract as datasets
from app.physical_contract import byte_sha
from app.physical_joint_custody import scan_stream

ROOT = Path(__file__).resolve().parents[2]
PIN = '41b2afe72fd370db77d06b8827d31e8a2b8cc18b'


def original(name):
    return subprocess.check_output(['git','-C',str(ROOT),'show',PIN+':app/'+name+'.py']).decode()


def test_pure_native_grammar_is_the_exact_reviewed_owner_source():
    assert ast.dump(ast.parse(Path(native.__file__).read_text(encoding='utf-8'))) == ast.dump(ast.parse(original('joint_contract')))


def test_all_dataset_structural_predicates_are_copied_not_relaxed():
    before, after = ast.parse(original('joint_datasets')), ast.parse(Path(datasets.__file__).read_text(encoding='utf-8'))
    for name in ('close_manifests','validate_dataset'):
        one = next(n for n in before.body if isinstance(n,ast.FunctionDef) and n.name == name)
        two = next(n for n in after.body if isinstance(n,ast.FunctionDef) and n.name == name)
        assert ast.dump(one) == ast.dump(two)


def npy():
    # Envelope/hash mechanism control only, explicitly not scientific data.
    header = b"{'descr': '<f8', 'fortran_order': False, 'shape': (32,)}\n"
    data = bytes(256)
    body = b'\x93NUMPY\x01\x00'+len(header).to_bytes(2,'little')+header+data
    descriptor = dict(dtype='<f8',shape=[32],file_bytes=len(body),file_sha256=byte_sha(body),data_sha256=byte_sha(data))
    return body, descriptor


def test_stream_closes_header_whole_digest_and_undecoded_data_digest():
    body, descriptor = npy()
    assert scan_stream(io.BytesIO(body), byte_count=len(body), sha256=byte_sha(body), descriptor=descriptor) == dict(bytes=len(body),sha256=byte_sha(body))


@pytest.mark.parametrize('damage', ['data','header','length','whole_sha','file_sha','data_sha','dtype','shape','fortran','version'])
def test_native_envelope_never_accepts_rehashed_or_malformed_substitute(damage):
    body, descriptor = npy()
    expected = byte_sha(body)
    if damage == 'data': body = body[:-1]+b'1'
    if damage == 'header': body = body[:10]+b'!'+body[11:]
    if damage == 'length': body += b'!'
    if damage == 'whole_sha': expected = '0'*64
    if damage == 'file_sha': descriptor['file_sha256'] = '0'*64
    if damage == 'data_sha': descriptor['data_sha256'] = '0'*64
    if damage == 'dtype': descriptor['dtype'] = '<i8'
    if damage == 'shape': descriptor['shape'] = [31]
    if damage == 'fortran': body = body.replace(b'False',b' True')
    if damage == 'version': body = body[:6]+b'\x02\x00'+body[8:]
    with pytest.raises(ValueError):
        scan_stream(io.BytesIO(body), byte_count=descriptor['file_bytes'], sha256=expected, descriptor=descriptor)


def test_stream_never_requests_or_retains_an_entire_large_member():
    class Repeated:
        left = 2*65536+7
        def read(self, count):
            assert 0 < count <= 65536
            value = b'a'*min(count,self.left)
            self.left -= len(value)
            return value
    count = Repeated.left
    assert scan_stream(Repeated(), byte_count=count, sha256=byte_sha(b'a'*count), descriptor=None)['bytes'] == count
