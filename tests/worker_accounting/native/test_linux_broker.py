"""Literal transport controls, not peer identity or native launch acceptance."""
import hashlib
import importlib.util
from pathlib import Path
import struct

import pytest

ROOT = Path(__file__).resolve().parents[3]


def module():
    spec = importlib.util.spec_from_file_location('broker_client', ROOT/'scripts/native_broker_client.py')
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def valid():
    return dict(attempt=b'a'*16, job=b'j'*16, project=b'p'*16, owner=b'o'*16,
                method_slot=b'm'*16, release_sha256=b'r'*32, profile_sha256=b'f'*32,
                source_sha256=b's'*32, source_bytes=1, parameter_sha256=b'c'*32,
                parameter_bytes=2, lineage_sha256=b'l'*32, lineage_bytes=3,
                object_id=b'n'*16, worker_nonce=b'w'*16, boot_id=b'b'*16)


def test_exact_submit_offsets_and_roundtrip():
    m = module()
    data = m.encode_submit(**valid())
    assert type(data) is bytes and len(data) == 352
    assert struct.unpack_from('<4sHHIIQ', data) == (b'LBR1', 1, 1, 352, 0, 1)
    for offset, field in ((24, 'attempt'), (40, 'job'), (56, 'project'),
                          (72, 'owner'), (88, 'method_slot'), (288, 'object_id'),
                          (304, 'worker_nonce'), (320, 'boot_id')):
        assert data[offset:offset+16] == valid()[field]
    for offset, field in ((104, 'release_sha256'), (136, 'profile_sha256'),
                          (168, 'source_sha256'), (208, 'parameter_sha256'),
                          (248, 'lineage_sha256')):
        assert data[offset:offset+32] == valid()[field]
    assert struct.unpack_from('<Q', data, 200)[0] == 1
    assert struct.unpack_from('<Q', data, 240)[0] == 2
    assert struct.unpack_from('<Q', data, 280)[0] == 3
    assert data[336:] == bytes(16)
    assert m.decode_submit(data) == valid()


@pytest.mark.parametrize('field', ['attempt', 'job', 'project', 'owner', 'method_slot',
                                  'object_id', 'worker_nonce', 'boot_id'])
@pytest.mark.parametrize('bad', [b'', bytes(16), b'a'*15, b'a'*17, 'a'*16,
                                bytearray(b'a'*16), None, 1])
def test_ids_are_exact_non_nil_bytes(field, bad):
    m = module()
    value = valid()
    value[field] = bad
    with pytest.raises(m.BrokerInputError, match='^protocol_invalid$'):
        m.encode_submit(**value)


@pytest.mark.parametrize('field', ['release_sha256', 'profile_sha256', 'source_sha256',
                                  'parameter_sha256', 'lineage_sha256'])
@pytest.mark.parametrize('bad', [b'x'*31, b'x'*33, 'x'*32, bytearray(32), None])
def test_hashes_are_literal_32_bytes(field, bad):
    m = module()
    value = valid()
    value[field] = bad
    with pytest.raises(m.BrokerInputError):
        m.encode_submit(**value)


@pytest.mark.parametrize('field,cap', [('source_bytes', 5*1048576),
                                      ('parameter_bytes', 65536), ('lineage_bytes', 16384)])
@pytest.mark.parametrize('kind', ['zero', 'negative', 'bool', 'float', 'plus_one', 'uint_overflow'])
def test_size_admission_before_encoding(field, cap, kind):
    m = module()
    value = valid()
    value[field] = dict(zero=0, negative=-1, bool=True, float=1.0,
                        plus_one=cap+1, uint_overflow=2**64)[kind]
    with pytest.raises(m.BrokerInputError, match='^input_bounds$'):
        m.encode_submit(**value)


@pytest.mark.parametrize('offset', [0, 4, 6, 8, 12, 16, 336, 351])
def test_header_reserved_and_sequence_corruption(offset):
    m = module()
    data = bytearray(m.encode_submit(**valid()))
    data[offset] ^= 1
    with pytest.raises(m.BrokerInputError):
        m.decode_submit(bytes(data))


@pytest.mark.parametrize('kind', ['short', 'long', 'mutable', 'text', 'none'])
def test_only_exact_bounded_packet_is_decoded(kind):
    m = module()
    data = m.encode_submit(**valid())
    bad = dict(short=data[:-1], long=data+b'x', mutable=bytearray(data),
               text=data.hex(), none=None)[kind]
    with pytest.raises(m.BrokerInputError):
        m.decode_submit(bad)


def test_input_hashes_preserve_original_json_dialect_and_empty_is_rejected():
    m = module()
    first = m.bind_input_bytes(b'{"x":1}', b'{"a":2}', b'{"v":3}')
    second = m.bind_input_bytes(b'{"x":1.0}', b'{"a":2}', b'{"v":3}')
    assert first['source_sha256'] == hashlib.sha256(b'{"x":1}').digest()
    assert first['source_sha256'] != second['source_sha256']
    assert first['source_bytes'] == 7
    for bad in (b'', bytearray(b'x'), 'x', b'x'*(5*1048576+1)):
        with pytest.raises(m.BrokerInputError):
            m.bind_input_bytes(bad, b'x', b'y')


def test_exact_caps_roundtrip():
    m = module()
    value = valid()
    value.update(source_bytes=5*1048576, parameter_bytes=65536, lineage_bytes=16384)
    assert m.decode_submit(m.encode_submit(**value)) == value


def test_unknown_fields_do_not_expand_the_wire():
    m = module()
    value = valid()
    value['argv'] = ['caller-controlled']
    with pytest.raises(m.BrokerInputError, match='^protocol_invalid$'):
        m.encode_submit(**value)


@pytest.mark.parametrize('offset,length', [(24, 16), (40, 16), (56, 16), (72, 16),
                                         (88, 16), (288, 16), (304, 16), (320, 16)])
def test_decoded_nil_identity_is_rejected(offset, length):
    m = module()
    data = bytearray(m.encode_submit(**valid()))
    data[offset:offset+length] = bytes(length)
    with pytest.raises(m.BrokerInputError, match='^protocol_invalid$'):
        m.decode_submit(bytes(data))


@pytest.mark.parametrize('offset,cap', [(200, 5*1048576), (240, 65536), (280, 16384)])
def test_decoded_oversize_cannot_bypass_encode_validation(offset, cap):
    m = module()
    for size in (0, cap+1, 2**64-1):
        data = bytearray(m.encode_submit(**valid()))
        struct.pack_into('<Q', data, offset, size)
        with pytest.raises(m.BrokerInputError, match='^input_bounds$'):
            m.decode_submit(bytes(data))


def test_no_shell_subprocess_or_scientific_parser_in_client():
    source = (ROOT/'scripts/native_broker_client.py').read_text('utf-8')
    for forbidden in ('import subprocess', 'import ctypes', 'import json', 'eval(', 'exec('):
        assert forbidden not in source


def test_unsupported_platform_has_no_descriptor_fallback():
    m = module()
    if m.sys.platform == 'linux':
        assert hasattr(m.os, 'memfd_create')
        return
    with pytest.raises(m.BrokerInputError, match='^unsupported_kernel$'):
        with m.sealed_inputs(b'x', b'y', b'z'):
            pytest.fail('Unsupported platform reached descriptor publication')
