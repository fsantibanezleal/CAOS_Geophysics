"""Pure explicit-platform preflight; no long-path registry or installed files."""
from pathlib import PureWindowsPath

import pytest

from app.errors import ApiError
from app.waveform_result import preflight_publication_paths


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
