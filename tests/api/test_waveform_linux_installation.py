"""Closed installation controls; authored packets are not native host proof."""
from copy import deepcopy
import importlib.util
from pathlib import Path
from uuid import uuid4
import stat
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


def module():
    spec = importlib.util.spec_from_file_location("m08_installation_test", ROOT / "scripts/waveform_m08_installation.py")
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def configuration(value):
    return dict(schema="geophysics.waveform-linux-installation/v3",source_root="/opt/fasl/waveform-source",
        source_revision="a"*40,data_root="/var/lib/fasl-private/waveform",custody_root="/srv/device-data/waveform-custody",
        science_work_root="/srv/device-temp/waveform-science",
        uid=61901,gid=61901,science_uid=65534,science_gid=65534,python="/usr/bin/python3.12",python_sha256="b"*64,
        site_packages="/opt/fasl/waveform-runtime/site-packages",admission_path="/srv/device-data/waveform-policy/admission.json",
        admission_sha256="c"*64,import_closure_path="/opt/fasl/waveform-policy/imports.json",import_closure_sha256="d"*64,
        launch_python_sha256="f"*64,
        source_hashes={name:"e"*64 for name in value.SOURCE_FILES})


def test_fixed_authority_accepts_no_request_selected_paths_or_commands():
    value = module()
    config = configuration(value)
    value.validate_configuration(config)
    identifier = str(uuid4())
    assert value.installed_argv(config,identifier) == ["/usr/bin/sudo","-n","/usr/bin/python3","-I","-S","-B",
        config["source_root"]+"/scripts/waveform_m08_supervisor.py",identifier]
    assert config == configuration(value)


def test_unprivileged_launch_cwd_is_fixed_outside_root_only_custody():
    value = module()
    config = configuration(value)
    identifier = str(uuid4())
    assert value.installed_cwd(config) == "/"
    invocation = dict(argv=value.installed_argv(config,identifier),
        launcher_sha256=config["launch_python_sha256"],cwd="/",environment=value.installed_environment(config))
    assert value.installation_binding(config,identifier)["invocation_sha256"] == value.sha(value.canonical(invocation))


@pytest.mark.parametrize("mutate",[
    lambda c:c.update(command="/bin/sh"),lambda c:c.update(uid=0),lambda c:c.update(science_uid=0),
    lambda c:c.update(custody_root="/run/waveform"),lambda c:c.update(custody_root="/tmp/waveform"),
    lambda c:c.update(custody_root=c["data_root"]+"/worker-replaceable"),
    lambda c:c.update(data_root=c["source_root"]+"/raw"),lambda c:c.update(python="../python"),
    lambda c:c.update(source_revision="0"*39),lambda c:c["source_hashes"].update(extra="e"*64),
    lambda c:c.update(import_closure_sha256="X"*64),lambda c:c.update(custody_root="/srv/device-data/../other"),
    lambda c:c.update(science_work_root="/run/waveform"),
    lambda c:c.update(science_work_root=c["custody_root"]+"/science"),
    lambda c:c.update(science_work_root=c["site_packages"]+"/science"),
])
def test_changed_or_unsafe_installation_refuses(mutate):
    value = module()
    config = configuration(value)
    mutate(config)
    with pytest.raises(ValueError):
        value.validate_configuration(config)


def test_receipt_must_match_checked_installation_snapshot():
    value = module()
    config = configuration(value)
    identifier = str(uuid4())
    expected = value.installation_binding(config,identifier)
    assert set(expected) == {"configuration_sha256","python_sha256","environment_sha256","invocation_sha256","source_hashes"}
    assert value.validate_installation_binding(deepcopy(expected),config,identifier) == expected
    for name in expected:
        changed = deepcopy(expected)
        changed[name] = None
        with pytest.raises(ValueError):
            value.validate_installation_binding(changed,config,identifier)


@pytest.mark.parametrize("field",["custody_root","science_work_root","launch_python_sha256","python_sha256","admission_sha256",
                                  "import_closure_sha256","site_packages","source_revision","source_hashes"])
def test_valid_but_changed_configuration_is_not_the_prelaunch_snapshot(field):
    value = module()
    config = configuration(value)
    identifier = str(uuid4())
    checked = value.installation_binding(config,identifier)
    changed = deepcopy(config)
    if field == "source_hashes":
        changed[field][next(iter(changed[field]))] = "f"*64
    elif field.endswith("sha256"):
        changed[field] = "a"*64
    elif field == "source_revision":
        changed[field] = "b"*40
    else:
        changed[field] += "-other"
    value.validate_configuration(changed)
    with pytest.raises(ValueError):
        value.validate_installation_binding(value.installation_binding(changed,identifier),checked=checked)


def test_historical_binding_is_closed_but_does_not_read_current_configuration(monkeypatch):
    value = module()
    expected = value.installation_binding(configuration(value),str(uuid4()))
    monkeypatch.setattr(value,"read_installation",lambda **_:pytest.fail("historical reads must not inspect today's installation"))
    assert value.validate_recorded_binding(deepcopy(expected)) == expected
    for changed in ({**expected,"extra":True},{key:item for key,item in expected.items() if key != "environment_sha256"}):
        with pytest.raises(ValueError):
            value.validate_recorded_binding(changed)


def test_uuid_change_cannot_reuse_an_installation_invocation():
    value = module()
    config = configuration(value)
    checked = value.installation_binding(config,str(uuid4()))
    with pytest.raises(ValueError):
        value.validate_installation_binding(value.installation_binding(config,str(uuid4())),checked=checked)


def test_custody_budget_refuses_unknown_or_excess_debt_without_adoption():
    value = module()
    value.custody_budget([18*1024**2]*4,[65536]*256,0)
    value.custody_budget([],[65536]*255,1)
    for plans,receipts,extra in (([1]*4,[],1),([21*1024**2]*4,[],0),([],[1]*257,0),([],[1]*256,1),([-1],[],0)):
        with pytest.raises(ValueError):
            value.custody_budget(plans,receipts,extra)


def test_nonroot_snapshot_does_not_open_root_only_custody_interior(monkeypatch):
    value = module()
    config = configuration(value)
    custody = Path(config['custody_root'])
    inspected = []
    monkeypatch.setattr(value.os,'geteuid',lambda:61901,raising=False)
    monkeypatch.setattr(Path,'lstat',lambda _:SimpleNamespace(st_mode=stat.S_IFDIR|0o700,st_uid=0))
    def exists(path):
        assert path != custody/'.git', 'nonroot must not inspect root-only entries'
        inspected.append(path)
        return False
    monkeypatch.setattr(Path,'exists',exists)
    value.verify_working_roots(config)
    assert custody.parent/'.git' in inspected
    assert Path(config['data_root'])/'.git' in inspected
    assert Path(config['science_work_root'])/'.git' in inspected


@pytest.mark.parametrize('mode,uid',[(stat.S_IFLNK|0o700,0),(stat.S_IFDIR|0o755,0),(stat.S_IFDIR|0o700,61901)])
def test_nonroot_snapshot_refuses_untrusted_custody_boundary(monkeypatch,mode,uid):
    value = module()
    monkeypatch.setattr(value.os,'geteuid',lambda:61901,raising=False)
    monkeypatch.setattr(Path,'lstat',lambda _:SimpleNamespace(st_mode=mode,st_uid=uid))
    monkeypatch.setattr(Path,'exists',lambda _:False)
    with pytest.raises(ValueError):
        value.verify_working_roots(configuration(value))


def test_root_bootstrap_still_checks_custody_interior(monkeypatch):
    value = module()
    config = configuration(value)
    monkeypatch.setattr(value.os,'geteuid',lambda:0,raising=False)
    monkeypatch.setattr(Path,'exists',lambda p:p == Path(config['custody_root'])/'.git')
    with pytest.raises(ValueError):
        value.verify_working_roots(config)
