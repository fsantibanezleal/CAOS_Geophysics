"""Actual Linux sealed-input operations only; no broker or science launch."""
import errno
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys


def run(source):
    if sys.platform != 'linux' or not hasattr(os, 'memfd_create'):
        raise RuntimeError('unsupported_kernel')
    spec = importlib.util.spec_from_file_location('broker_client', source)
    client = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(client)
    original = (b'{"x":1.0}', b'{"phase":2}', b'{"lineage":3}')
    seals = fcntl.F_SEAL_WRITE | fcntl.F_SEAL_GROW | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_SEAL
    before = len(os.listdir('/proc/self/fd'))
    refused = 0
    with client.sealed_inputs(*original) as descriptors:
        assert len(descriptors) == 3
        for descriptor, expected in zip(descriptors, original):
            assert os.pread(descriptor, len(expected)+1, 0) == expected
            assert not os.get_inheritable(descriptor)
            assert fcntl.fcntl(descriptor, fcntl.F_GETFL) & os.O_ACCMODE == os.O_RDONLY
            assert fcntl.fcntl(descriptor, fcntl.F_GET_SEALS) & seals == seals
            writer = os.open('/proc/self/fd/'+str(descriptor), os.O_RDWR | os.O_CLOEXEC)
            try:
                for operation in (lambda: os.pwrite(writer, b'x', 0),
                                  lambda: os.ftruncate(writer, 0),
                                  lambda: os.ftruncate(writer, len(expected)+1)):
                    try:
                        operation()
                    except OSError as failure:
                        assert failure.errno == errno.EPERM
                        refused += 1
                    else:
                        raise AssertionError('sealed_input_mutation_succeeded')
                assert os.pread(descriptor, len(expected)+1, 0) == expected
            finally:
                os.close(writer)
    for descriptor in descriptors:
        try:
            os.fstat(descriptor)
        except OSError as failure:
            assert failure.errno == errno.EBADF
        else:
            raise AssertionError('descriptor_survived_context_exit')
    assert len(os.listdir('/proc/self/fd')) == before

    class CallerFailure(Exception):
        pass

    try:
        with client.sealed_inputs(*original):
            raise CallerFailure('caller_failure')
    except CallerFailure:
        pass
    assert len(os.listdir('/proc/self/fd')) == before

    real = client._sealed_input
    calls = 0

    def fail_second(body):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError(errno.EMFILE, 'private-detail-must-not-escape')
        return real(body)

    client._sealed_input = fail_second
    try:
        try:
            with client.sealed_inputs(*original):
                raise AssertionError('partial_failure_published_descriptors')
        except client.BrokerInputError as failure:
            assert str(failure) == 'input_unsealed'
            assert failure.__cause__ is None and failure.__context__ is None
        else:
            raise AssertionError('partial_failure_not_reported')
        assert calls == 2 and len(os.listdir('/proc/self/fd')) == before
    finally:
        client._sealed_input = real
    return dict(schema='geophysics.broker-memfd-control/v1', status='PASS',
                source_sha256=hashlib.sha256(Path(source).read_bytes()).hexdigest(),
                inputs=3, mutation_refusals=refused, read_only=True,
                fd_closure=True, partial_failure_closure=True,
                caller_failure_closure=True,
                native_launch_accepted=False, peer_identity_accepted=False,
                method_accepted=False, production_accepted=False)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('one source path required')
    print(json.dumps(run(Path(sys.argv[1])), sort_keys=True))
