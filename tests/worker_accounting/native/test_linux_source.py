"""Static scope/call-path controls, never native runtime qualification."""
import hashlib
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "scripts/native_physical_cpu"


def test_frozen_i01_bytes():
    frozen = {
        "controller.h": "f6ed0337b98c98470db4b1e6f57bdc5d81426e4f5534a0e726018a56ad40492f",
        "controller.c": "801dad97ae188f99a7b672eec2aee0fc673be065ac04d0a0ce46d2535be92d7a",
        "abi_probe.c": "d002f82464a234c1ce8f3bd39152df21d230624201d7d6a56d5459c6718a88d1",
        "capture_build.py": "136ea6af5ad102944010c8815871255ecebdbc0210b425bd458251b92a20cd36",
    }
    for name, expected in frozen.items():
        assert hashlib.sha256((CORE / name).read_bytes()).hexdigest() == expected


def test_no_fallback_or_activation():
    native = (CORE / "linux_controller.c").read_text("utf-8")
    loop = (CORE / "linux_main.c").read_text("utf-8")
    assert "SYS_clone3" in native and "CLONE_INTO_CGROUP | CLONE_PIDFD" in native
    assert '"cgroup.kill"' in native and '"cpu.stat"' in native
    assert "setgroups(0, NULL)" in native
    assert "PR_SET_NO_NEW_PRIVS" in native and "SYS_capset" in native
    assert "PR_SET_PDEATHSIG" in native and "getppid() != expected_parent" in native
    assert "PR_CAPBSET_DROP" in native and "SECCOMP_SET_MODE_FILTER" in native
    assert "AUDIT_ARCH_X86_64" in native and "SYS_unshare" in native and "SYS_setns" in native
    assert "poll(" in loop and "lc_sample(" in loop
    assert "l.out_eof ? -1 : l.object.out_fd" in loop
    assert "l.err_eof ? -1 : l.object.err_fd" in loop
    assert "#define LC_TRACE_SAMPLES 65536u" in (CORE / "linux_controller.h").read_text("utf-8")
    assert "lc_stop(" in loop and "lc_sha_update(" in loop
    for text in (native, loop):
        assert not re.search(r"\b(?:fork|vfork|system|popen|malloc|calloc|realloc)\s*\(", text)
        assert "psutil" not in text and "cgroup.procs\", O_WRONLY" not in text
    assert "geophysics-cpu-qual-" in native
    assert "user.slice" not in native


def test_probe_has_no_native_operations():
    probe = (CORE / "linux_probe.c").read_text("utf-8")
    assert "struct clone_args" in probe and "offsetof(" in probe
    for call in ("clone3", "syscall", "setuid", "mkdir", "execve", "kill"):
        assert not re.search(r"\b" + call + r"\s*\(", probe)


def test_enum_names_are_distinct_before_linux_compile():
    header = (CORE / "linux_controller.h").read_text("utf-8")
    entries = re.findall(r"\b(LC_[A-Z_]+)\s*=\s*[0-9]+", header)
    assert len(entries) == 33 and len(set(entries)) == len(entries)


def test_fixture_system_cpu_has_native_work_not_supplied_accounting():
    fixture = (CORE / "linux_fixture.c").read_text("utf-8")
    from scripts.run_linux_cpu_controls import CASES
    assert CASES["system_cpu"] == ("--system-cpu", 1)
    assert "syscall(SYS_gettid)" in fixture
    assert "CLOCK_THREAD_CPUTIME_ID" in fixture and "UINT64_C(200000000)" in fixture


def test_science_cwd_path_descriptor_is_leaf_only():
    native = (CORE / "linux_controller.c").read_text("utf-8")
    start = native.index("static int open_path(")
    stop = native.index("static int read_fd(", start)
    opener = native[start:stop]
    assert "int access = (!slash && directory && writable_leaf) ? O_PATH : O_RDONLY;" in opener
    assert "openat(fd, name, access | O_CLOEXEC | O_NOFOLLOW" in opener
    assert "((slash || directory) ? O_DIRECTORY : 0)" in opener
    assert "st.st_uid != (slash ? 0u : leaf_owner)" in opener
    assert "(st.st_mode & 0777u) != 0700u" in opener
    assert "open_path(c->cwd, 1, (uid_t)c->uid, 1)" in native
    assert "open_path(c->executable, 0, 0, 0)" in native
    assert native.index("setresuid(") < native.index("science_filter()) child_fail") < native.index("fchdir(6)) child_fail")
    for forbidden in ("CAP_DAC_OVERRIDE", "CAP_DAC_READ_SEARCH", "setfsuid(", "chmod("):
        assert forbidden not in native


def test_cpu_dialect_optional_force_idle_never_changes_charge():
    native = (CORE / "linux_controller.c").read_text("utf-8")
    body = native[native.index("int lc_parse_cpu("):native.index("int lc_parse_events(")]
    keys = re.findall(r'"([a-z_.]+)"', body)
    assert keys == ["usage_usec", "user_usec", "system_usec", "nr_periods",
                    "nr_throttled", "throttled_usec", "nr_bursts", "burst_usec",
                    "core_sched.force_idle_usec"]
    assert "keyed(p, n, keys, 9, v, &seen)" in body and "(seen & 7u) != 7u" in body
    assert "ncc_linux_cpu(v[0], v[1], v[2], &s->cpu_ns)" in body
    assert "v[8]" not in body  # optional idle diagnostic is not executed CPU
    keyed = native[native.index("static int keyed("):native.index("int lc_parse_cpu(")]
    assert "key == count" in keyed and "(*seen & (1u << key))" in keyed


def test_child_failure_stages_are_fixed_safe_literals():
    native = (CORE / "linux_controller.c").read_text("utf-8")
    loop = (CORE / "linux_main.c").read_text("utf-8")
    start = native.index("static void child_setup(")
    body = native[start:native.index("int lc_birth(", start)]
    stages = re.findall(r"child_fail\((?:ready|3), '([A-L])'\)", body)
    assert sorted(set(stages)) == list("ABCDEFGHIJKL")
    assert "science_filter()) child_fail(3, 'I')" in body
    assert "fchdir(6)) child_fail(3, 'J')" in body
    assert '"linux_child_setup_unknown\\n"' in loop
    assert all('"linux_child_setup_' + stage + '\\n"' in loop for stage in "ABCDEFGHIJKL")
    assert "fputs(setup_failures[byte-'A'],stderr)" in loop
