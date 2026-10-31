"""Actual root-owned POSIX inactive-link census, never runtime/science admission."""
from copy import deepcopy
import os
import stat
import sys

import pytest

from scripts import waveform_m08_installation as authority

pytestmark = pytest.mark.skipif(sys.platform != "linux" or os.geteuid() != 0,
                               reason="actual Linux root-owned inactive census")


def fixture(tmp_path):
    tmp_path.chmod(0o700)
    held = authority.directory_fd(tmp_path,root_owned=True)
    os.close(held)
    root,targets = tmp_path/"stdlib",tmp_path/"configuration"
    root.mkdir(mode=0o755)
    targets.mkdir(mode=0o755)
    target = targets/"sitecustomize.py"
    # Executing this hook would fail. Census reads bytes only.
    raw = b"raise RuntimeError('inactive hook must not execute')\n"
    target.write_bytes(raw)
    target.chmod(0o644)
    (root/"sitecustomize.py").symlink_to(target)
    info = target.stat()
    record = dict(device=info.st_dev,inode=info.st_ino,uid=info.st_uid,gid=info.st_gid,
                  mode=stat.S_IMODE(info.st_mode),links=info.st_nlink,bytes=info.st_size,
                  mtime_ns=info.st_mtime_ns,ctime_ns=info.st_ctime_ns,sha256=authority.sha(raw))
    return root,target,{str(target):record}


def test_exact_outward_inactive_target_requires_explicit_binding(tmp_path):
    root,target,targets = fixture(tmp_path)
    with pytest.raises(ValueError):
        authority.snapshot_tree(root)
    observed = authority.snapshot_tree(root,inactive_link_targets=targets)
    assert set(observed) == {"sitecustomize.py"}
    assert observed["sitecustomize.py"]["kind"] == "link"
    assert authority.inactive_inventory({str(root):observed},targets) == {
        str(root/"sitecustomize.py"):targets[str(target)]["sha256"]}


@pytest.mark.parametrize("mutation",["bytes","mode","inode","mtime_ns","ctime_ns","sha256"])
def test_target_mismatch_refuses_before_census(tmp_path,mutation):
    root,target,targets = fixture(tmp_path)
    wrong = deepcopy(targets)
    wrong[str(target)][mutation] = "b"*64 if mutation == "sha256" else wrong[str(target)][mutation]+1
    with pytest.raises(ValueError):
        authority.snapshot_tree(root,inactive_link_targets=wrong)
    assert target.exists() and (root/"sitecustomize.py").is_symlink()


@pytest.mark.parametrize("mutation",["changed","writable","nonroot","symlink","ordinary","unused"])
def test_actual_changed_or_unbound_targets_refuse(tmp_path,mutation):
    root,target,targets = fixture(tmp_path)
    if mutation == "changed":
        target.write_bytes(b"changed")
    elif mutation == "writable":
        target.chmod(0o666)
    elif mutation == "nonroot":
        os.chown(target,61901,61901)
    elif mutation == "symlink":
        saved = target.with_name("retained.py")
        target.rename(saved)
        target.symlink_to(saved)
    elif mutation == "ordinary":
        (root/"ordinary.py").symlink_to(target)
    elif mutation == "unused":
        (root/"sitecustomize.py").unlink()
    with pytest.raises((ValueError,OSError)):
        observed = authority.snapshot_tree(root,inactive_link_targets=targets)
        authority.inactive_inventory({str(root):observed},targets)
    assert target.exists()


def test_existing_inward_hook_uses_exact_inventoried_member(tmp_path):
    tmp_path.chmod(0o700)
    target = tmp_path/"original.py"
    target.write_bytes(b"raise RuntimeError('must remain inactive')\n")
    target.chmod(0o644)
    (tmp_path/"sitecustomize.py").symlink_to(target.name)
    observed = authority.snapshot_tree(tmp_path)
    assert authority.inactive_inventory({str(tmp_path):observed},{}) == {
        str(tmp_path/"sitecustomize.py"):observed["original.py"]["sha256"]}


@pytest.mark.parametrize("mutation",["none","missing","digest","unused","non-elf","ordinary"])
def test_native_target_requires_exact_inventory_and_existing_image_digest(tmp_path,mutation):
    root,hook,unused = fixture(tmp_path)
    (root/"sitecustomize.py").unlink()
    target = hook.with_name("libpython3.12.so.1.0")
    raw = b"\x7fELFauthored census bytes, NOT a qualified native executable"
    target.write_bytes(raw)
    target.chmod(0o644)
    info = target.stat()
    record = dict(device=info.st_dev,inode=info.st_ino,uid=info.st_uid,gid=info.st_gid,
                  mode=stat.S_IMODE(info.st_mode),links=info.st_nlink,bytes=info.st_size,
                  mtime_ns=info.st_mtime_ns,ctime_ns=info.st_ctime_ns,sha256=authority.sha(raw))
    targets = {str(target):record}
    (root/"libpython3.12.so").symlink_to(target)
    images = {str(target):record["sha256"]}
    if mutation == "missing":
        images.clear()
    elif mutation == "digest":
        images[str(target)] = "a"*64
    elif mutation == "unused":
        (root/"libpython3.12.so").unlink()
    elif mutation == "non-elf":
        target.write_bytes(b"not an image")
    elif mutation == "ordinary":
        (root/"ordinary.so").symlink_to(target)
    if mutation == "none":
        with pytest.raises(ValueError):
            authority.snapshot_tree(root)
        observed = authority.snapshot_tree(root,native_link_targets=targets)
        authority.validate_native_links({str(root):observed},targets,images)
    else:
        with pytest.raises(ValueError):
            observed = authority.snapshot_tree(root,native_link_targets=targets)
            authority.validate_native_links({str(root):observed},targets,images)
    assert target.exists()
