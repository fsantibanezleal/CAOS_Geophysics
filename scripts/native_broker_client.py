"""Closed LBR1 request bytes and sealed-input preparation; no launch authority.

This module never authenticates a peer, opens a broker socket, starts science,
interprets scientific JSON or grants a profile. The native receiver must repeat
framing/seal/hash checks against its immutable registry. Production lifecycle,
LCX2, peer identity and measured containment remain separate required gates.
"""
from contextlib import contextmanager
import hashlib
import os
import stat
import struct
import sys

PACKET_BYTES = 352
HEADER = struct.Struct('<4sHHIIQ')
IDS = ((24, 'attempt'), (40, 'job'), (56, 'project'), (72, 'owner'),
       (88, 'method_slot'), (288, 'object_id'), (304, 'worker_nonce'), (320, 'boot_id'))
HASHES = ((104, 'release_sha256'), (136, 'profile_sha256'),
          (168, 'source_sha256'), (208, 'parameter_sha256'), (248, 'lineage_sha256'))
SIZES = ((200, 'source_bytes', 5*1048576), (240, 'parameter_bytes', 65536),
         (280, 'lineage_bytes', 16384))
FIELDS = frozenset(name for _, name in IDS+HASHES) | frozenset(name for _, name, _ in SIZES)


class BrokerInputError(ValueError):
    """Fixed safe input/transport code, never caller content or OS detail."""


def _require(ok, code='protocol_invalid'):
    if not ok:
        raise BrokerInputError(code)


def _validate(fields):
    _require(type(fields) is dict and fields.keys() == FIELDS)
    for _, name in IDS:
        value = fields[name]
        _require(type(value) is bytes and len(value) == 16 and value != bytes(16))
    for _, name in HASHES:
        value = fields[name]
        _require(type(value) is bytes and len(value) == 32)
    for _, name, cap in SIZES:
        value = fields[name]
        _require(type(value) is int and 1 <= value <= cap, 'input_bounds')


def encode_submit(**fields):
    _validate(fields)
    result = bytearray(PACKET_BYTES)
    HEADER.pack_into(result, 0, b'LBR1', 1, 1, PACKET_BYTES, 0, 1)
    for offset, name in IDS:
        result[offset:offset+16] = fields[name]
    for offset, name in HASHES:
        result[offset:offset+32] = fields[name]
    for offset, name, _ in SIZES:
        struct.pack_into('<Q', result, offset, fields[name])
    return bytes(result)


def decode_submit(data):
    _require(type(data) is bytes and len(data) == PACKET_BYTES)
    _require(HEADER.unpack_from(data) == (b'LBR1', 1, 1, PACKET_BYTES, 0, 1)
             and data[336:] == bytes(16))
    fields = {name: data[offset:offset+16] for offset, name in IDS}
    fields.update({name: data[offset:offset+32] for offset, name in HASHES})
    fields.update({name: struct.unpack_from('<Q', data, offset)[0] for offset, name, _ in SIZES})
    _validate(fields)
    return fields


def _validate_inputs(source, parameter, lineage):
    bodies = source, parameter, lineage
    for body, (_, _, cap) in zip(bodies, SIZES):
        _require(type(body) is bytes and 1 <= len(body) <= cap, 'input_bounds')
    return bodies


def bind_input_bytes(source, parameter, lineage):
    bodies = _validate_inputs(source, parameter, lineage)
    result = {}
    for body, (_, name, _) in zip(bodies, SIZES):
        result[name] = len(body)
        result[name.removesuffix('_bytes')+'_sha256'] = hashlib.sha256(body).digest()
    return result


def _sealed_input(body):
    import fcntl
    flags = os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING
    seals = fcntl.F_SEAL_WRITE | fcntl.F_SEAL_GROW | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_SEAL
    writer = os.memfd_create('geophysics-broker-input', flags)
    reader = None
    try:
        view = memoryview(body)
        written = 0
        while written < len(view):
            count = os.write(writer, view[written:written+65536])
            _require(count > 0, 'input_bounds')
            written += count
        fcntl.fcntl(writer, fcntl.F_ADD_SEALS, seals)
        before = os.fstat(writer)
        _require(stat.S_ISREG(before.st_mode) and before.st_size == len(body)
                 and fcntl.fcntl(writer, fcntl.F_GET_SEALS) & seals == seals, 'input_unsealed')
        # Only the held, newly created self descriptor is reopened read-only.
        # No caller path or debug name is accepted as an input identity.
        reader = os.open('/proc/self/fd/'+str(writer), os.O_RDONLY | os.O_CLOEXEC)
        after = os.fstat(reader)
        _require((before.st_dev, before.st_ino, before.st_size) ==
                 (after.st_dev, after.st_ino, after.st_size)
                 and fcntl.fcntl(reader, fcntl.F_GETFL) & os.O_ACCMODE == os.O_RDONLY
                 and fcntl.fcntl(reader, fcntl.F_GET_SEALS) & seals == seals
                 and not os.get_inheritable(reader), 'input_unsealed')
        result, reader = reader, None
        return result
    finally:
        if reader is not None:
            os.close(reader)
        os.close(writer)


@contextmanager
def sealed_inputs(source, parameter, lineage):
    _require(sys.platform == 'linux' and hasattr(os, 'memfd_create'), 'unsupported_kernel')
    bodies = _validate_inputs(source, parameter, lineage)
    owned = []
    failed = False
    try:
        try:
            for body in bodies:
                owned.append(_sealed_input(body))
        except OSError:
            failed = True
        # Raise outside the OS exception handler: no private errno/path context.
        if failed:
            raise BrokerInputError('input_unsealed') from None
        yield tuple(owned)
    finally:
        for descriptor in reversed(owned):
            os.close(descriptor)
