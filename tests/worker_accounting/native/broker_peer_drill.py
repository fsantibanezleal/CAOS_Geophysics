"""Actual kernel peer PIDFD controls, not service authorization or science."""
import argparse
import array
import ctypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import select
import socket
import tempfile


def bound_module(name, path, expected):
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def controls(native, client, fixture):
    class Peer(ctypes.Structure):
        _fields_ = [('credentials', fixture.Credentials), ('pidfd', ctypes.c_int)]

        def __init__(self):
            super().__init__()
            self.pidfd = -1

    native.lbr_peer_open.argtypes = [ctypes.c_int, ctypes.POINTER(Peer)]
    native.lbr_peer_open.restype = ctypes.c_int
    native.lbr_peer_live.argtypes = [ctypes.POINTER(Peer)]
    native.lbr_peer_live.restype = ctypes.c_int
    native.lbr_peer_dispose.argtypes = [ctypes.POINTER(Peer)]
    native.lbr_peer_dispose.restype = None
    native.lbr_receive_peer.argtypes = [ctypes.c_int, ctypes.POINTER(Peer), ctypes.POINTER(fixture.Inputs)]
    native.lbr_receive_peer.restype = ctypes.c_int
    before = fixture.census()
    cases = 0
    for kind, verdict in ((socket.SOCK_SEQPACKET, 0), (socket.SOCK_STREAM, 2), (socket.SOCK_DGRAM, 2)):
        sender, receiver = socket.socketpair(socket.AF_UNIX, kind | socket.SOCK_CLOEXEC)
        peer = Peer()
        try:
            assert native.lbr_peer_open(receiver.fileno(), ctypes.byref(peer)) == verdict
            if verdict == 0:
                assert (peer.credentials.pid, peer.credentials.uid, peer.credentials.gid) == (
                    os.getpid(), os.getuid(), os.getgid())
                assert peer.pidfd >= 0 and not os.get_inheritable(peer.pidfd)
                assert native.lbr_peer_live(ctypes.byref(peer)) == 0
                assert native.lbr_peer_open(receiver.fileno(), ctypes.byref(peer)) == 2
            else:
                assert peer.pidfd == -1
            cases += 1
        finally:
            native.lbr_peer_dispose(ctypes.byref(peer))
            native.lbr_peer_dispose(ctypes.byref(peer))
            sender.close()
            receiver.close()
        assert fixture.census() == before

    bodies = (b'{"raw":1.00}', b'{"parameter":1}', b'{"lineage":null}')
    fields = dict(attempt=b'a'*16, job=b'j'*16, project=b'p'*16, owner=b'o'*16,
                  method_slot=b'm'*16, release_sha256=b'r'*32, profile_sha256=b'f'*32,
                  object_id=b'n'*16, worker_nonce=b'w'*16, boot_id=b'b'*16,
                  **client.bind_input_bytes(*bodies))
    packet = client.encode_submit(**fields)
    with client.sealed_inputs(*bodies) as fds:
        sender, receiver = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET | socket.SOCK_CLOEXEC)
        peer = Peer()
        out = fixture.Inputs()
        try:
            receiver.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
            assert native.lbr_peer_open(receiver.fileno(), ctypes.byref(peer)) == 0
            sender.sendmsg([packet], [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array('i', fds))])
            assert native.lbr_receive_peer(receiver.fileno(), ctypes.byref(peer), ctypes.byref(out)) == 0
            assert bytes(out.packet) == packet
            native.lbr_dispose(ctypes.byref(out))
            # This is an owned test child, never native/scientific birth proof.
            child = os.fork()
            if child == 0:
                receiver.close()
                sender.sendmsg([packet], [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array('i', fds))])
                os._exit(0)
            assert select.select([receiver], [], [], 2)[0]
            try:
                assert native.lbr_receive_peer(receiver.fileno(), ctypes.byref(peer), ctypes.byref(out)) == 3
                assert list(out.fd) == [-1, -1, -1]
                assert native.lbr_peer_live(ctypes.byref(peer)) == 0  # Connector is still parent.
            finally:
                _, status = os.waitpid(child, 0)
                assert os.waitstatus_to_exitcode(status) == 0
            cases += 2
        finally:
            native.lbr_dispose(ctypes.byref(out))
            native.lbr_peer_dispose(ctypes.byref(peer))
            sender.close()
            receiver.close()
    assert fixture.census() == before

    # A fresh filesystem connection pins the actual child connector, then its
    # retained PIDFD becomes readable after exit. Never reopen that numeric PID.
    with tempfile.TemporaryDirectory(prefix='broker-peer-') as directory:
        path = str(Path(directory)/'peer.sock')
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET | socket.SOCK_CLOEXEC)
        listener.settimeout(2)
        listener.bind(path)
        listener.listen(1)
        gate_read, gate_write = os.pipe2(os.O_CLOEXEC)
        child = os.fork()
        if child == 0:
            listener.close()
            os.close(gate_write)
            connection = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET | socket.SOCK_CLOEXEC)
            connection.connect(path)
            connection.send(b'ready')
            os.read(gate_read, 1)
            os._exit(0)
        os.close(gate_read)
        peer = Peer()
        connection = None
        try:
            connection, _ = listener.accept()
            assert connection.recv(5) == b'ready'
            assert native.lbr_peer_open(connection.fileno(), ctypes.byref(peer)) == 0
            assert peer.credentials.pid == child and native.lbr_peer_live(ctypes.byref(peer)) == 0
        finally:
            os.close(gate_write)
            _, status = os.waitpid(child, 0)
        try:
            assert os.waitstatus_to_exitcode(status) == 0
            held = peer.pidfd
            assert held >= 0 and native.lbr_peer_live(ctypes.byref(peer)) == 3
            out = fixture.Inputs()
            assert native.lbr_receive_peer(connection.fileno(), ctypes.byref(peer), ctypes.byref(out)) == 3
            assert peer.pidfd == held and list(out.fd) == [-1, -1, -1]
            cases += 1
        finally:
            native.lbr_peer_dispose(ctypes.byref(peer))
            if connection is not None:
                connection.close()
            listener.close()
    assert fixture.census() == before
    return dict(schema='geophysics.broker-kernel-peer-control/v1', status='PASS',
                actual_peer_cases=cases, descriptor_census_unchanged=True,
                service_identity_accepted=False, native_launch_accepted=False, production_accepted=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('library', 'library-sha256', 'client', 'client-sha256', 'fixture', 'fixture-sha256', 'receipt'):
        parser.add_argument('--'+name, required=True)
    args = parser.parse_args()
    fixture = bound_module('bound_receiver_fixture', args.fixture, args.fixture_sha256)
    native, client = fixture.load(args.library, args.library_sha256, args.client, args.client_sha256)
    raw = (json.dumps(controls(native, client, fixture), sort_keys=True)+'\n').encode()
    with Path(args.receipt).open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.write(1, raw)


if __name__ == '__main__':
    main()
