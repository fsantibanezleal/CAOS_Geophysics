"""Exact namespace controls, not permission to adopt a new runtime inventory."""
from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest


def module():
    path = Path(__file__).resolve().parents[2] / "scripts/waveform_m08_installation.py"
    spec = importlib.util.spec_from_file_location("m08_closure_test",path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def inventory():
    return {"pkg":dict(kind="directory",uid=0,gid=0,mode=0o755,device=1,inode=2),
        "pkg/module.py":dict(kind="file",uid=0,gid=0,mode=0o644,device=1,inode=3,bytes=8,sha256="a"*64)}


def test_exact_inventory_rejects_added_missing_or_changed_interpreted_names():
    value = module()
    expected = inventory()
    value.validate_inventory(deepcopy(expected),expected)
    for change in (lambda o:o.update({"pkg/added.py":o["pkg/module.py"]}),
                   lambda o:o.pop("pkg/module.py"),lambda o:o["pkg/module.py"].update(sha256="b"*64),
                   lambda o:o["pkg/module.py"].update(inode=4)):
        observed = deepcopy(expected)
        change(observed)
        with pytest.raises(ValueError):
            value.validate_inventory(observed,expected)


@pytest.mark.parametrize("name",["../escape.py","/absolute.py","pkg//module.py","pkg/./module.py","pkg\\module.py"])
def test_inventory_name_cannot_escape(name):
    value = module()
    observed = {name:inventory()["pkg/module.py"]}
    with pytest.raises(ValueError):
        value.validate_inventory(observed,observed)


@pytest.mark.parametrize("mutate",[
    lambda o:o["pkg/module.py"].update(uid=61901),lambda o:o["pkg/module.py"].update(mode=0o666),
    lambda o:o["pkg/module.py"].update(kind="socket"),lambda o:o["pkg/module.py"].update(bytes=-1),
    lambda o:o["pkg/module.py"].update(extra=True),lambda o:o["pkg"].update(mode=0o777),
])
def test_self_equal_inventory_is_not_authority_if_unsafe(mutate):
    value = module()
    observed = inventory()
    mutate(observed)
    with pytest.raises(ValueError):
        value.validate_inventory(observed,observed)


def inactive_target():
    return dict(device=1,inode=2,uid=0,gid=0,mode=0o644,links=1,bytes=4,
                mtime_ns=3,ctime_ns=4,sha256="a"*64)


def test_optional_inactive_target_grammar_is_closed_and_empty_compatible():
    value = module()
    assert value.validate_inactive_targets({}) == {}
    target = {"/etc/python3.12/sitecustomize.py":inactive_target()}
    assert value.validate_inactive_targets(target) == target


@pytest.mark.parametrize("field,bad",[
    ("device",True),("inode",0),("uid",61901),("gid",-1),("mode",0o666),
    ("links",0),("bytes",256*1024**2+1),("mtime_ns",-1),
    ("ctime_ns",2**64),("sha256","A"*64),("extra",1),
])
def test_inactive_target_identity_cannot_self_attest_unsafe(field,bad):
    value = module()
    record = inactive_target()
    record[field] = bad
    with pytest.raises(ValueError):
        value.validate_inactive_targets({"/etc/python3.12/sitecustomize.py":record})


@pytest.mark.parametrize("name",["/etc/python3.12/ordinary.py","/tmp/../sitecustomize.py",
                                "/etc//sitecustomize.py","relative/sitecustomize.py"])
def test_only_canonical_inactive_hook_targets_are_declarable(name):
    with pytest.raises(ValueError):
        module().validate_inactive_targets({name:inactive_target()})


def test_inactive_target_must_be_used_not_just_declared():
    value = module()
    with pytest.raises(ValueError):
        value.inactive_inventory({"/opt/source":inventory()},
                                 {"/etc/python3.12/sitecustomize.py":inactive_target()})


def test_complete_closure_refuses_nonisolated_or_site_enabled_entry():
    import sys
    if sys.flags.isolated and sys.flags.no_site:
        pytest.skip("test requires ordinary entry to exercise refusal")
    with pytest.raises(ValueError):
        module().verify_import_closure({})


def test_native_target_grammar_is_not_generic_outward_link_permission():
    value = module()
    name = "/usr/lib/x86_64-linux-gnu/libpython3.12.so.1.0"
    assert value.validate_inactive_targets({name:inactive_target()},native=True)
    for bad in ("/etc/python3.12/sitecustomize.py","/usr/lib/ordinary.so","/usr/lib/libpython.so"):
        with pytest.raises(ValueError):
            value.validate_inactive_targets({bad:inactive_target()},native=True)
