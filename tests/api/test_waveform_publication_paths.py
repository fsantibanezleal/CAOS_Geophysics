"""Pure explicit-platform preflight; no long-path registry or installed files."""
from pathlib import PureWindowsPath

import pytest

from app.errors import ApiError
from app.waveform_result import preflight_publication_paths, preflight_lifecycle_paths


def windows_path(units):
    return PureWindowsPath("E:/" + "a" * (units - 3))


def rejected(target, directory, names):
    with pytest.raises(ApiError) as error:
        preflight_publication_paths(target, directory, [{"name": name} for name in names], platform="nt")
    assert error.value.code == "waveform_storage_unavailable"
    assert error.value.status == 503


def test_windows_259_unit_exact_targets_and_members_pass():
    name = "c00-response_frequency_hz.bin"
    directory = windows_path(259 - 1 - len(name))
    assert len(str(directory / name).encode("utf-16-le")) // 2 == 259
    preflight_publication_paths(windows_path(259), directory, [{"name": name}], platform="nt")


@pytest.mark.parametrize("units", [260, 261, 400])
def test_windows_metadata_target_rejected_before_any_install(units):
    rejected(windows_path(units), PureWindowsPath("E:/_Datos/short"), ["manifest.json"])


def test_every_generated_member_is_preflighted_not_just_manifest():
    name = "c00-response_frequency_hz.bin"
    directory = windows_path(260 - 1 - len(name))
    assert len(str(directory / "manifest.json")) < 260
    assert len(str(directory / name)) == 260
    rejected(PureWindowsPath("E:/_Datos/result.json"), directory, ["manifest.json", name])


def test_windows_astral_characters_count_as_two_utf16_units():
    target = PureWindowsPath("E:/" + "a" * 255 + chr(0x10000))
    assert len(str(target)) == 259
    assert len(str(target).encode("utf-16-le")) // 2 == 260
    rejected(target, PureWindowsPath("E:/_Datos/short"), ["manifest.json"])


@pytest.mark.parametrize("prefix", ["\\\\?\\E:\\", "\\\\.\\E:\\"])
def test_windows_device_prefix_is_not_an_unchecked_bypass(prefix):
    rejected(PureWindowsPath(prefix + "result.json"), PureWindowsPath("E:/_Datos/short"), ["manifest.json"])


def test_nonwindows_explicit_platform_does_not_inherit_windows_limit():
    preflight_publication_paths(windows_path(400), windows_path(400), [{"name": "manifest.json"}], platform="posix")


def test_preflight_never_opens_or_creates_files(monkeypatch):
    from pathlib import Path

    def no_io(*args, **kwargs):
        pytest.fail("Pure preflight attempted filesystem mutation")

    monkeypatch.setattr(Path, "mkdir", no_io)
    monkeypatch.setattr(Path, "open", no_io)
    preflight_publication_paths(windows_path(20), windows_path(20), [{"name": "manifest.json"}], platform="nt")
    rejected(windows_path(20), windows_path(250), ["c00-response_frequency_hz.bin"])


OWNER = "00000000-0000-4000-8000-000000000001"
PROJECT = "00000000-0000-4000-8000-000000000002"
JOB = "00000000-0000-4000-8000-000000000003"
LONGEST = "c00-response_frequency_hz.bin"


def lifecycle(data_root,*,owner=OWNER,project=PROJECT,platform="nt"):
    live = data_root/"derived"/owner/project
    preflight_lifecycle_paths(data_root,owner,project,live/"results"/(JOB+".json"),
        live/"waveforms"/JOB,[{"name":"manifest.json"},{"name":LONGEST}],platform=platform)


def lifecycle_root(deleted_units):
    suffix = PureWindowsPath(".deleting")/f"{OWNER}--{PROJECT}--derived"/"waveforms"/JOB/LONGEST
    return windows_path(deleted_units-1-len(str(suffix)))


def test_supported_whole_lifecycle_259_units_passes_without_io(monkeypatch):
    from pathlib import Path
    def no_io(*args,**kwargs):
        pytest.fail("Lifecycle preflight must be pure")
    monkeypatch.setattr(Path,"mkdir",no_io)
    monkeypatch.setattr(Path,"open",no_io)
    root = lifecycle_root(259)
    assert len(str(root/".deleting"/f"{OWNER}--{PROJECT}--derived"/"waveforms"/JOB/LONGEST)) == 259
    lifecycle(root)


@pytest.mark.parametrize("units",[260,265,271])
def test_live_supported_but_generated_deletion_target_refuses_before_install(units):
    root = lifecycle_root(units)
    live = root/"derived"/OWNER/PROJECT
    preflight_publication_paths(live/"results"/(JOB+".json"),live/"waveforms"/JOB,[{"name":LONGEST}],platform="nt")
    with pytest.raises(ApiError) as error:
        lifecycle(root)
    assert error.value.status == 503 and error.value.code == "waveform_storage_unavailable"


def test_lifecycle_utf16_not_character_count_and_posix_unchanged():
    root = lifecycle_root(259)
    value = str(root)
    astral = PureWindowsPath(value[:-1]+chr(0x10000))
    with pytest.raises(ApiError):
        lifecycle(astral)
    lifecycle(lifecycle_root(400),platform="posix")


@pytest.mark.parametrize("owner,project",[("A0000000-0000-4000-8000-000000000001",PROJECT),("../outside",PROJECT),(OWNER,"wrong")])
def test_lifecycle_generated_identity_is_not_request_selected_path(owner,project):
    with pytest.raises(ApiError):
        lifecycle(PureWindowsPath("E:/_Datos/short"),owner=owner,project=project)


def test_lifecycle_refuses_unbound_live_path():
    root = PureWindowsPath("E:/_Datos/short")
    with pytest.raises(ApiError):
        preflight_lifecycle_paths(root,OWNER,PROJECT,root/"other.json",root/"other",[],platform="nt")
