"""Read-only source-scope checks; these are not compiled/native gate evidence."""
import hashlib
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "scripts/native_physical_cpu"
PROTECTED = {
    "scripts/physical_accounting_protocol.py":
        "550a49d5b6ab3ec289f0c8722339c4a84af1d3b59e2786febce3c6d5566be622",
    "tests/worker_accounting/test_protocol.py":
        "662c9b1e0cf642b9ec0cea79bde897885752d4255188fc71de70e19ff3ce9215",
}


def test_no_shared_or_policy_changes():
    for name, expected in PROTECTED.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected


def test_core_has_no_platform_io_heap_or_policy_hooks():
    text = "\n".join((CORE / name).read_text("utf-8") for name in ("controller.h", "controller.c"))
    includes = re.findall(r"^\s*#\s*include\s+[<\"]([^>\"]+)", text, re.M)
    assert set(includes) <= {"stdint.h", "stddef.h", "limits.h", "controller.h"}
    forbidden = (
        r"\b(?:CreateProcess|CreateJobObject|QueryInformationJobObject|TerminateJobObject|"
        r"ResumeThread|LoadLibrary|GetProcAddress|GetProcessTimes|QueryPerformanceCounter)\w*\s*\(",
        r"\b(?:clone|clone3|fork|exec\w*|kill|syscall|wait\w*|open|fopen|fread|fwrite|"
        r"printf|fprintf|socket|poll|clock_gettime|malloc|calloc|realloc|free|getenv|system)\s*\(",
        r"#\s*pragma\s+pack", r"\b__int128\b",
    )
    assert all(not re.search(pattern, text) for pattern in forbidden)
    assert "NCC_STATE_BYTES" in text and "NCC_SNAPSHOT_WORDS" in text
    assert not (CORE / "windows_job.c").exists()
    assert not (CORE / "linux_cgroup.c").exists()


def test_probe_is_sdk_layout_only_no_native_api_calls():
    text = (CORE / "abi_probe.c").read_text("utf-8")
    assert "#include <Windows.h>" in text
    assert "JOBOBJECT_BASIC_LIMIT_INFORMATION" in text
    assert "JOBOBJECT_BASIC_ACCOUNTING_INFORMATION" in text
    for name in ("CreateJobObject", "QueryInformationJobObject", "CreateProcess",
                 "TerminateJobObject", "GetProcessTimes", "QueryPerformanceCounter"):
        assert not re.search(r"\b" + name + r"\w*\s*\(", text)
    assert not re.search(r"#\s*pragma\s+pack", text)
    assert "offsetof(" in text and "sizeof(" in text
