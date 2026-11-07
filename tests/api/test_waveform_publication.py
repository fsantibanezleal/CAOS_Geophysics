"""Actual POSIX storage operations, not native science or installed queue proof."""
from contextlib import ExitStack
import errno
import os
import sys
from uuid import uuid4

import pytest

from app.errors import ApiError
from app.waveform_publication import adopt_export, verify_adopted_path

pytestmark = pytest.mark.skipif(sys.platform != "linux",reason="actual Linux renameat2 storage gate")


def identity(fd):
    info = os.fstat(fd)
    return dict(device=info.st_dev,inode=info.st_ino)


@pytest.fixture
def held(tmp_path):
    stage,target = tmp_path/"stage",tmp_path/"target"
    stage.mkdir()
    target.mkdir()
    export = stage/"export"
    export.mkdir()
    (export/"retained.bin").write_bytes(b"actual owned storage bytes")
    (stage/"root_receipt.json").write_bytes(b"retained receipt control")
    with ExitStack() as leases:
        fds = []
        for path in (stage,export,target):
            fd = os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
            leases.callback(os.close,fd)
            fds.append(fd)
        yield stage,export,target,fds,str(uuid4())


def test_actual_adoption_preserves_directory_and_member_inodes(held):
    stage,export,target,(stage_fd,export_fd,target_fd),identifier = held
    directory_inode = export.stat().st_ino
    file_inode = (export/"retained.bin").stat().st_ino
    adopt_export(stage_fd,export_fd,target_fd,identifier,identity(stage_fd))
    assert not export.exists()
    assert (target/identifier).stat().st_ino == directory_inode
    assert (target/identifier/"retained.bin").stat().st_ino == file_inode
    assert (target/identifier/"retained.bin").read_bytes() == b"actual owned storage bytes"
    assert os.listdir(export_fd) == ["retained.bin"]
    assert set(os.listdir(stage)) == {"root_receipt.json"}


@pytest.mark.parametrize("kind",["directory","file","symlink"])
def test_existing_destination_is_never_overwritten(held,kind):
    stage,export,target,(stage_fd,export_fd,target_fd),identifier = held
    destination = target/identifier
    if kind == "directory":
        destination.mkdir()
        (destination/"sentinel").write_bytes(b"keep")
    elif kind == "file":
        destination.write_bytes(b"keep")
    else:
        destination.symlink_to(export,target_is_directory=True)
    before = destination.lstat()
    with pytest.raises(ApiError):
        adopt_export(stage_fd,export_fd,target_fd,identifier,identity(stage_fd))
    assert destination.lstat().st_ino == before.st_ino
    assert (export/"retained.bin").read_bytes() == b"actual owned storage bytes"
    assert (stage/"root_receipt.json").exists()


def test_changed_stage_or_source_identity_refuses_without_move(held):
    stage,export,target,(stage_fd,export_fd,target_fd),identifier = held
    wrong = {**identity(stage_fd),"inode":identity(stage_fd)["inode"]+1}
    with pytest.raises(ApiError):
        adopt_export(stage_fd,export_fd,target_fd,identifier,wrong)
    renamed = stage/"retained-original-export"
    export.rename(renamed)
    export.mkdir()
    with pytest.raises(ApiError):
        adopt_export(stage_fd,export_fd,target_fd,identifier,identity(stage_fd))
    assert not (target/identifier).exists()
    assert (renamed/"retained.bin").exists()


@pytest.mark.parametrize("error",[errno.EXDEV,errno.ENOSYS,errno.EIO])
def test_unsupported_or_failed_rename_retains_source_no_copy(held,monkeypatch,error):
    import app.waveform_publication as publication
    _,export,target,(stage_fd,export_fd,target_fd),identifier = held
    def fail(*_):
        raise OSError(error,"authored syscall failure")
    monkeypatch.setattr(publication,"_rename_noreplace",fail)
    with pytest.raises(ApiError):
        adopt_export(stage_fd,export_fd,target_fd,identifier,identity(stage_fd))
    assert (export/"retained.bin").exists() and not (target/identifier).exists()


def test_postrename_readback_failure_retains_installed_bytes(held,monkeypatch):
    import app.waveform_publication as publication
    _,export,target,(stage_fd,export_fd,target_fd),identifier = held
    actual = publication._rename_noreplace
    def move_then_fail(*args):
        actual(*args)
        raise OSError(errno.EIO,"authored uncertain acknowledgement")
    monkeypatch.setattr(publication,"_rename_noreplace",move_then_fail)
    with pytest.raises(ApiError):
        adopt_export(stage_fd,export_fd,target_fd,identifier,identity(stage_fd))
    assert not export.exists()
    assert (target/identifier/"retained.bin").read_bytes() == b"actual owned storage bytes"


@pytest.mark.parametrize("replacement",["directory","symlink","parent"])
def test_precommit_destination_identity_rejects_replacement_retaining_original(held,replacement):
    _,_,target,(stage_fd,export_fd,target_fd),identifier = held
    adopt_export(stage_fd,export_fd,target_fd,identifier,identity(stage_fd))
    destination = target/identifier
    verify_adopted_path(destination,export_fd)
    if replacement == "parent":
        retained = target.with_name("retained-target")
        target.rename(retained)
        target.mkdir()
        destination.mkdir()
        original = retained/identifier
    else:
        original = target/"retained-export"
        destination.rename(original)
        if replacement == "symlink":
            destination.symlink_to(original,target_is_directory=True)
        else:
            destination.mkdir()
    with pytest.raises(ApiError):
        verify_adopted_path(destination,export_fd)
    assert (original/"retained.bin").read_bytes() == b"actual owned storage bytes"


@pytest.mark.parametrize("mutation",["none","unknown","receipt","replacement"])
def test_postcommit_stage_cleanup_exact_inventory_only(tmp_path,mutation):
    from app.waveform_stage import cleanup_stage
    from scripts.waveform_m08_installation import canonical
    identifier = str(uuid4())
    stage = tmp_path/identifier
    stage.mkdir()
    with ExitStack() as leases:
        parent_fd = os.open(tmp_path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
        leases.callback(os.close,parent_fd)
        stage_fd = os.open(identifier,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=parent_fd)
        leases.callback(os.close,stage_fd)
        receipt = {"stage":identity(stage_fd),"authored":"postcommit cleanup control only"}
        (stage/"root_receipt.json").write_bytes(canonical(receipt))
        retained = stage
        if mutation == "unknown":
            (stage/"unknown").write_bytes(b"retain")
        elif mutation == "receipt":
            (stage/"root_receipt.json").write_bytes(b"changed")
        elif mutation == "replacement":
            retained = tmp_path/"retained-stage"
            stage.rename(retained)
            stage.mkdir()
        if mutation == "none":
            cleanup_stage(parent_fd,stage_fd,identifier,receipt)
            assert not stage.exists()
        else:
            with pytest.raises(ValueError):
                cleanup_stage(parent_fd,stage_fd,identifier,receipt)
            assert (retained/"root_receipt.json").exists()
