"""Ordinary native receipt grammar checks, not Linux OS qualification."""
from copy import deepcopy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "data-pipeline"))

from app.errors import ApiError
from app.waveform_linux_exec import checked_resources
from waveform_m08_linux import RESOURCE, RELEASE, B, S, GAP, MEMORY, canonical
from waveform_input import sha


def measured():
    # Deliberately beyond JS's integer domain. Private native monotonic clocks
    # are uint64; public scientific/result values never receive these stamps.
    stamp = 9007199254741000
    receipt = {"schema": RESOURCE, "run_id": "a" * 32, "status": "measured", "cpu_ns": 13000,
               "user_cpu_ns": 5000, "system_cpu_ns": 8000, "budget_ns": B, "stop_ns": S,
               "sample_count": 4, "max_sample_gap_ns": GAP, "peak_charge_bytes": 1024,
               "active_processes": 0, "drained_ns": stamp, "stable_final_ns": stamp + GAP,
               "admission_sha256": "b" * 64, "memory_kind": "linux_cgroup_charge",
               "runtime_authorized": False, "method_accepted": False, "host_admitted": False,
               "guardian": {"scope": "m08guard-" + "a"*32 + ".scope",
                    "group": "/system.slice/m08guard-" + "a"*32 + ".scope", "identity_transport": "PIDFDs/ah",
                    "memory_limit_bytes": 128*1024**2, "tasks_max": 16, "wall_limit_seconds": 150,
                    "manager_job": "/org/freedesktop/systemd1/job/123", "status": "complete", "scope_removed": True}}
    return receipt


def released(receipt):
    return {"schema": RELEASE, "run_id": receipt["run_id"], "receipt_sha256": sha(canonical(receipt)),
            "all_native_owned_handles_closed": True, "scope_removed": True, "runtime_authorized": False}


def test_native_uint64_clocks_project_only_safe_measured_resource_fields():
    receipt = measured()
    result = checked_resources(receipt, released(receipt))
    assert result["memory_kind"] == "linux_cgroup_charge" and result["cpu_ns"] == 13000
    assert "drained_ns" not in result and "stable_final_ns" not in result
    assert result["runtime_authorized"] is False and result["host_admitted"] is False


def test_actual_kernel_cpu_stat_core_scheduling_field_preserves_lifetime():
    from waveform_m08_linux import parse_cpu
    raw = b'usage_usec 13000\nuser_usec 5000\nsystem_usec 8000\ncore_sched.force_idle_usec 91\nnr_periods 0\n'
    assert parse_cpu(raw) == (13000000,5000000,8000000)


@pytest.mark.parametrize('extra',[b'core_sched.other_usec 0\n',b'other.dotted 0\n',
    b'core_sched.force_idle_usec -1\n',b'core_sched.force_idle_usec 1\ncore_sched.force_idle_usec 2\n'])
def test_cpu_stat_exact_new_field_does_not_admit_arbitrary_or_duplicate_fields(extra):
    from waveform_m08_linux import parse_cpu
    from waveform_m08_windows import ControlError
    with pytest.raises(ControlError):
        parse_cpu(b'usage_usec 13\nuser_usec 5\nsystem_usec 8\n'+extra)


@pytest.mark.parametrize("key,value", [("cpu_ns", S), ("cpu_ns", B + 1), ("user_cpu_ns", 13001),
    ("system_cpu_ns", 13001), ("budget_ns", float(B)), ("stop_ns", float(S)), ("active_processes", False),
    ("active_processes", 1), ("peak_charge_bytes", MEMORY + 1), ("max_sample_gap_ns", GAP + 1),
    ("memory_kind", "rss"), ("runtime_authorized", True), ("method_accepted", True), ("host_admitted", True),
    ("stable_final_ns", 9007199254741000 + GAP - 1)])
def test_invalid_native_receipt_is_not_acceptance(key, value):
    receipt = measured()
    receipt[key] = value
    with pytest.raises(ApiError) as error:
        checked_resources(receipt, released(receipt))
    assert error.value.code == "waveform_resource_invalid"


def test_release_digest_or_scope_extinction_cannot_be_substituted():
    receipt = measured()
    release = released(receipt)
    for key, value in (("receipt_sha256", "c" * 64), ("scope_removed", False),
                       ("all_native_owned_handles_closed", 1), ("runtime_authorized", True)):
        bad = deepcopy(release)
        bad[key] = value
        with pytest.raises(ApiError):
            checked_resources(receipt, bad)


@pytest.mark.parametrize("key,value", [("status", "failed"), ("scope_removed", False),
    ("identity_transport", "numeric-PIDs"), ("scope", "another.scope"), ("group", "/user.slice"),
    ("memory_limit_bytes", 134217728.0), ("tasks_max", 16.0), ("wall_limit_seconds", 150.0)])
def test_guardian_identity_completion_and_readbacks_are_required(key, value):
    receipt = measured()
    receipt["guardian"][key] = value
    with pytest.raises(ApiError):
        checked_resources(receipt, released(receipt))
