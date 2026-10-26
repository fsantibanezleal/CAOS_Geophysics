"""Actual Linux socket/seal/FD controls; never broker launch authorization."""
import argparse
import array
from contextlib import ExitStack
import ctypes
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import sys
import tempfile


class Credentials(ctypes.Structure):
    _fields_ = [('pid', ctypes.c_int), ('uid', ctypes.c_uint), ('gid', ctypes.c_uint)]


class Inputs(ctypes.Structure):
    _fields_ = [('packet', ctypes.c_ubyte*352), ('fd', ctypes.c_int*3)]

    def __init__(self):
        super().__init__()
        self.fd[:] = [-1, -1, -1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def census():
    return set(os.listdir('/proc/self/fd'))


def load(library, library_sha, client, client_sha):
    if sys.platform != 'linux' or sha(library) != library_sha or sha(client) != client_sha:
        raise ValueError('unreviewed_fixture')
    spec = importlib.util.spec_from_file_location('bound_broker_client', client)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    native = ctypes.CDLL(str(Path(library).resolve()))
    native.lbr_receive.argtypes = [ctypes.c_int, ctypes.POINTER(Credentials), ctypes.POINTER(Inputs)]
    native.lbr_receive.restype = ctypes.c_int
    native.lbr_decode.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    native.lbr_decode.restype = ctypes.c_int
    native.lbr_dispose.argtypes = [ctypes.POINTER(Inputs)]
    native.lbr_dispose.restype = None
    return native, module


def controls(native, client):
    bodies = (b' {"number":1.00,"label":"\\u0061"}\n', b'{"x":1}', b'{"parent":null}')
    fields = dict(attempt=b'a'*16, job=b'j'*16, project=b'p'*16, owner=b'o'*16,
                  method_slot=b'm'*16, release_sha256=b'r'*32, profile_sha256=b'f'*32,
                  object_id=b'n'*16, worker_nonce=b'w'*16, boot_id=b'b'*16,
                  **client.bind_input_bytes(*bodies))
    packet = client.encode_submit(**fields)
    expected = Credentials(os.getpid(), os.getuid(), os.getgid())
    count = 0

    # Every case uses fresh sockets; no replay/adoption or persistent listener.
    def receive(data, fds, verdict, *, principal=expected, passcred=True, send=True, expected_bodies=bodies):
        nonlocal count
        before = census()
        sender, receiver = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET | socket.SOCK_CLOEXEC)
        out = Inputs()
        positions = [os.lseek(fd, 0, os.SEEK_CUR) for fd in fds[:3]]
        try:
            if passcred:
                receiver.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
            if send:
                ancillary = [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array('i', fds))] if fds else []
                sender.sendmsg([data], ancillary)
            got = native.lbr_receive(receiver.fileno(), ctypes.byref(principal), ctypes.byref(out))
            assert got == verdict, (count, got, verdict)
            if got == 0:
                assert bytes(out.packet) == data
                for fd, body, position in zip(out.fd, expected_bodies, positions, strict=True):
                    assert not os.get_inheritable(fd)
                    assert fcntl.fcntl(fd, fcntl.F_GETFL) & os.O_ACCMODE == os.O_RDONLY
                    assert os.pread(fd, len(body)+1, 0) == body
                    assert os.lseek(fd, 0, os.SEEK_CUR) == position
                # An occupied output cannot be overwritten or leak its handles.
                assert native.lbr_receive(receiver.fileno(), ctypes.byref(principal), ctypes.byref(out)) == 2
            else:
                assert list(out.fd) == [-1, -1, -1] and bytes(out.packet) == bytes(352)
        finally:
            native.lbr_dispose(ctypes.byref(out))
            native.lbr_dispose(ctypes.byref(out))
            sender.close()
            receiver.close()
        assert census() == before
        count += 1

    with client.sealed_inputs(*bodies) as fds:
        receive(packet, fds, 0)
        receive(packet, fds, 1, send=False)
        receive(packet, fds, 2, passcred=False)
        receive(packet, [], 2)
        receive(packet, fds[:2], 2)
        receive(packet, [*fds, fds[0]], 2)
        receive(packet, list(fds)*20, 2)  # Actual ancillary truncation and FD census.
        receive(packet[:-1], fds, 2)
        receive(packet+b'x', fds, 2)
        receive(packet, fds, 3, principal=Credentials(expected.pid+1, expected.uid, expected.gid))
        receive(packet, fds, 3, principal=Credentials(expected.pid, expected.uid+1, expected.gid))
        receive(packet, fds, 3, principal=Credentials(expected.pid, expected.uid, expected.gid+1))
        for offset in (0, 4, 6, 8, 12, 16, 336, 351):
            bad = bytearray(packet)
            bad[offset] ^= 1
            receive(bytes(bad), fds, 2)
        for offset in (24, 40, 56, 72, 88, 288, 304, 320):
            bad = bytearray(packet)
            bad[offset:offset+16] = bytes(16)
            receive(bytes(bad), fds, 2)
        for offset, cap in ((200, 5242880), (240, 65536), (280, 16384)):
            for size in (0, cap+1):
                bad = bytearray(packet)
                bad[offset:offset+8] = size.to_bytes(8, 'little')
                receive(bytes(bad), fds, 5)
        for offset in (168, 208, 248):
            bad = bytearray(packet)
            bad[offset] ^= 1
            receive(bytes(bad), fds, 6)
        os.lseek(fds[0], 1, os.SEEK_SET)
        receive(packet, fds, 0)
        with ExitStack() as stack:
            wrong = stack.enter_context(client.sealed_inputs(bodies[0]+b'x', *bodies[1:]))
            receive(packet, wrong, 5)
            raw = os.memfd_create('unsealed-control', os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
            stack.callback(os.close, raw)
            os.write(raw, bodies[0])
            receive(packet, [raw, *fds[1:]], 4)
            raw_reader = os.open('/proc/self/fd/'+str(raw), os.O_RDONLY | os.O_CLOEXEC)
            stack.callback(os.close, raw_reader)
            receive(packet, [raw_reader, *fds[1:]], 4)
            seals = fcntl.F_SEAL_WRITE | fcntl.F_SEAL_GROW | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_SEAL
            fcntl.fcntl(raw, fcntl.F_ADD_SEALS, fcntl.F_SEAL_GROW | fcntl.F_SEAL_SHRINK)
            receive(packet, [raw_reader, *fds[1:]], 4)
            fcntl.fcntl(raw, fcntl.F_ADD_SEALS, seals)
            receive(packet, [raw, *fds[1:]], 4)  # Seals do not turn O_RDWR into O_RDONLY.
            ordinary = stack.enter_context(tempfile.TemporaryFile())
            ordinary.write(bodies[0])
            ordinary.flush()
            receive(packet, [ordinary.fileno(), *fds[1:]], 4)
            ordinary_reader = os.open('/proc/self/fd/'+str(ordinary.fileno()), os.O_RDONLY | os.O_CLOEXEC)
            stack.callback(os.close, ordinary_reader)
            receive(packet, [ordinary_reader, *fds[1:]], 4)
    upper_bodies = (b's'*(5*1048576), b'p'*65536, b'l'*16384)
    upper_fields = {**fields, **client.bind_input_bytes(*upper_bodies)}
    with client.sealed_inputs(*upper_bodies) as upper_fds:
        receive(client.encode_submit(**upper_fields), upper_fds, 0, expected_bodies=upper_bodies)
    return dict(schema='geophysics.broker-native-input-control/v1', status='PASS',
                actual_socket_controls=count, descriptor_census_unchanged=True,
                peer_identity_accepted=False, native_launch_accepted=False,
                method_accepted=False, production_accepted=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library', required=True)
    parser.add_argument('--library-sha256', required=True)
    parser.add_argument('--client', required=True)
    parser.add_argument('--client-sha256', required=True)
    parser.add_argument('--receipt', help='Fresh operator-selected test receipt; no publication authority')
    args = parser.parse_args()
    native, client = load(args.library, args.library_sha256, args.client, args.client_sha256)
    raw = (json.dumps(controls(native, client), sort_keys=True)+'\n').encode()
    if args.receipt:
        with Path(args.receipt).open('xb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    sys.stdout.buffer.write(raw)


if __name__ == '__main__':
    main()
