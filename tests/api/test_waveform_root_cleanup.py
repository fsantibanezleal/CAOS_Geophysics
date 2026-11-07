"""Actual root-owned finite storage controls; NOT science or installed queue proof."""
from contextlib import ExitStack
import os
import sys

import pytest

from scripts import waveform_m08_installation as authority
from scripts.waveform_m08_supervisor import cleanup_custody

pytestmark = pytest.mark.skipif(sys.platform != "linux" or os.geteuid() != 0,
                               reason="actual Linux root custody storage control")


@pytest.mark.parametrize("mutation",["none","unknown","changed","link"])
def test_known_inventory_only_before_first_unlink(tmp_path,mutation):
    tmp_path.chmod(0o700)
    child = tmp_path/"export"
    child.mkdir(mode=0o700)
    raw = b"authored storage control, not calculation"
    (tmp_path/"request").write_bytes(raw)
    member = child/"calculation.json"
    member.write_bytes(raw)
    expected = {"export":{"kind":"directory"},
                "request":dict(kind="file",bytes=len(raw),sha256=authority.sha(raw)),
                "export/calculation.json":dict(kind="file",bytes=len(raw),sha256=authority.sha(raw))}
    if mutation == "unknown":
        (child/"unknown").write_bytes(b"keep unknown")
    elif mutation == "changed":
        member.write_bytes(b"changed")
    elif mutation == "link":
        (child/"link").symlink_to(member)
    with ExitStack() as leases:
        fd = os.open(tmp_path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
        leases.callback(os.close,fd)
        if mutation == "none":
            cleanup_custody(authority,fd,expected)
            assert not os.listdir(fd)
        else:
            with pytest.raises((ValueError,OSError)):
                cleanup_custody(authority,fd,expected)
            assert (tmp_path/"request").read_bytes() == raw
            assert member.exists()


@pytest.mark.parametrize("mutation",["none","nested","link","nonempty-anchor","unknown-anchor"])
def test_startup_custody_rejects_unknown_nested_or_unresolved_mount_debt(tmp_path,mutation):
    from uuid import uuid4
    from scripts.waveform_m08_supervisor import custody_inventory
    root = tmp_path/"custody"
    root.mkdir(mode=0o700)
    paths = {name:root/name for name in ("plans","runs","receipts")}
    for path in paths.values():
        path.mkdir(mode=0o700)
    (root/".lock").write_bytes(b"")
    identifier = str(uuid4())
    run = paths["runs"]/identifier
    run.mkdir(mode=0o700)
    (run/"request").write_bytes(b"authored control")
    installation = {name:"a"*64 for name in
                    ("configuration_sha256","python_sha256","environment_sha256","invocation_sha256")}
    installation["source_hashes"] = {name:"b"*64 for name in authority.SOURCE_FILES}
    plan = dict(schema="geophysics.waveform-custody-plan/v1",job_id=identifier,request_sha256="c"*64,
                record_sha256="d"*64,input_bytes=16,stage={"device":1,"inode":1},installation=installation)
    (paths["plans"]/(identifier+".json")).write_bytes(authority.canonical(plan))
    science = tmp_path/"science"
    science.mkdir(mode=0o711)
    if mutation == "nested":
        native = run/("export.a4-"+"a"*32)
        native.mkdir(mode=0o700)
        (native/"unknown").write_bytes(b"retain")
    elif mutation == "link":
        (run/"miniseed").symlink_to(run/"request")
    elif mutation == "nonempty-anchor":
        anchor = science/identifier
        anchor.mkdir(mode=0o711)
        (anchor/"unknown").write_bytes(b"retain")
    elif mutation == "unknown-anchor":
        (science/str(uuid4())).mkdir(mode=0o711)
    with ExitStack() as leases:
        fds = []
        for path in (root,paths["plans"],paths["runs"],paths["receipts"],science):
            fd = os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
            leases.callback(os.close,fd)
            fds.append(fd)
        if mutation == "none":
            assert custody_inventory(authority,*fds) == ([16],[])
        else:
            with pytest.raises((ValueError,OSError)):
                custody_inventory(authority,*fds)
        assert (run/"request").read_bytes() == b"authored control"
