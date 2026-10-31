"""Finite held waveform stage verification and known postcommit receipt cleanup."""
from __future__ import annotations

import os

from app.waveform_linux_execution import identity
from scripts.waveform_m08_installation import canonical, regular_at, require, sha


def verify_stage(stage_fd, expected_identity, receipt):
    require(identity(stage_fd) == expected_identity and set(os.listdir(stage_fd)) == {"export","root_receipt.json"})
    require(regular_at(stage_fd,"root_receipt.json",65536) == canonical(receipt))
    export = os.open("export",os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=stage_fd)
    try:
        require(set(os.listdir(export)) == {member["name"] for member in receipt["members"]})
        for member in receipt["members"]:
            raw = regular_at(export,member["name"],33554432)
            require(len(raw) == member["bytes"] and sha(raw) == member["sha256"])
    finally:
        os.close(export)


def cleanup_stage(parent_fd, stage_fd, identifier, receipt):
    require(identity(stage_fd) == receipt["stage"] and set(os.listdir(stage_fd)) == {"root_receipt.json"})
    require(regular_at(stage_fd,"root_receipt.json",65536) == canonical(receipt))
    current = os.stat(identifier,dir_fd=parent_fd,follow_symlinks=False)
    require(dict(device=current.st_dev,inode=current.st_ino) == receipt["stage"])
    os.unlink("root_receipt.json",dir_fd=stage_fd)
    os.fsync(stage_fd)
    os.rmdir(identifier,dir_fd=parent_fd)
    os.fsync(parent_fd)
