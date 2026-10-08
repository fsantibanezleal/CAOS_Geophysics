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
