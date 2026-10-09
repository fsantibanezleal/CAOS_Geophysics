"""Actual search-only directory permissions; not science or native queue proof."""
import os
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'data-pipeline'))
from waveform_input import WaveformInputError
from waveform_m08_files import create_output, open_output

pytestmark = pytest.mark.skipif(sys.platform != 'linux' or os.geteuid() == 0,
    reason='Requires actual ordinary Linux DAC permissions, never root bypass')


@pytest.fixture
def search_parent(tmp_path):
    parent = tmp_path/'search-only'
    parent.mkdir(mode=0o700)
    leaf = parent/'readable-leaf'
    leaf.mkdir(mode=0o700)
    # Same effective DAC rights as a nonroot caller traversing root-owned0711.
    # This newly owned test directory alone is restored for pytest cleanup.
    parent.chmod(0o111)
    try:
        yield parent,leaf
    finally:
        parent.chmod(0o700)


def test_search_only_ancestor_is_not_directory_read_authority(search_parent):
    parent,leaf = search_parent
    with pytest.raises(PermissionError):
        os.open(parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
    with create_output(leaf/'export',trusted_parent=leaf) as held:
        with held.create_regular('receipt.json') as stream:
            stream.write(b'{}')
            held.flush_file(stream)
        assert held.names(55) == ['receipt.json']
        assert os.fstat(held.fd).st_ino == (leaf/'export').stat().st_ino
        import fcntl
        assert fcntl.fcntl(held.held[-2],fcntl.F_GETFL) & os.O_PATH == 0
        assert all(fcntl.fcntl(fd,fcntl.F_GETFL) & os.O_PATH for fd in held.held[:-2])
        assert all(not os.get_inheritable(fd) for fd in held.held)
    with open_output(leaf/'export') as held:
        with held.open_regular('receipt.json') as stream:
            assert stream.read() == b'{}'


def test_search_handle_never_adopts_a_link(search_parent):
    parent,leaf = search_parent
    link = leaf/'linked'
    link.symlink_to(leaf,target_is_directory=True)
    with pytest.raises(WaveformInputError):
        create_output(link/'export',trusted_parent=link)
    assert not (leaf/'export').exists()
    assert parent.stat().st_mode & 0o777 == 0o111


def test_readable_final_directory_is_still_required(search_parent):
    _,leaf = search_parent
    closed = leaf/'closed'
    closed.mkdir(mode=0o111)
    try:
        with pytest.raises(WaveformInputError):
            open_output(closed)
    finally:
        closed.chmod(0o700)


def test_replaced_named_export_does_not_replace_the_held_identity(search_parent):
    _,leaf = search_parent
    with create_output(leaf/'export',trusted_parent=leaf) as held:
        held.path.rename(leaf/'retained')
        held.path.mkdir(mode=0o700)
        with pytest.raises(WaveformInputError):
            held.check_identity()
        assert os.fstat(held.fd).st_ino == (leaf/'retained').stat().st_ino
