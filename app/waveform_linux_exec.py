"""Waveform-only selected Linux context; never profiles/shared worker policy."""
from __future__ import annotations

from copy import deepcopy
import os

from app.errors import ApiError
from app.processing_contract import sha256


def bind_context(context, stage_root, stage, job_id):
    from waveform_m08_linux import read_admission, canonical
    from waveform_m08_files import open_output, validate_path
    admission, digest = read_admission(context["admission_path"], context["python"])
    if digest != context["admission_sha256"] or validate_path(admission["parent"]["path"]) != stage_root:
        raise ApiError(409, "waveform_context_unavailable", "Selected Linux waveform context changed")
    with open_output(stage_root) as parent, open_output(stage) as child:
        if list(parent.identity) != admission["parent"]["identity"]:
            raise ApiError(409, "waveform_context_unavailable", "Selected Linux waveform staging identity changed")
        bound = deepcopy(admission)
        bound["parent"] = {"path": str(stage), "identity": list(child.identity),
                           "context_receipt_sha256": sha256(canonical({"selected": digest, "job_id": job_id,
                                                                       "identity": list(child.identity)}))}
    path = stage / "admission.json"
    encoded = canonical(bound)
    with path.open("xb") as stream:
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())
    return {**context, "admission_path": str(path), "admission_sha256": sha256(encoded)}


def checked_resources(receipt, release):
    from waveform_m08_linux import RESOURCE, RELEASE, B, S, GAP, MEMORY, canonical
    from waveform_m08_windows import require, integer, ControlError, precount
    from app.waveform_contract import INPUT
    try:
        # Native clocks/identities use the reviewed uint64 graph bound, not the
        # scientific request's JS-safe integer dialect. Portable fields stay
        # below their unchanged scientific/resource limits.
        precount(receipt, 65536, max_nodes=4096, max_depth=8)
        precount(release, 65536, max_nodes=4096, max_depth=8)
        require(type(receipt) is dict and set(receipt) == set("schema run_id status cpu_ns user_cpu_ns system_cpu_ns budget_ns stop_ns sample_count max_sample_gap_ns peak_charge_bytes active_processes drained_ns stable_final_ns admission_sha256 memory_kind runtime_authorized method_accepted host_admitted guardian".split()))
        require(receipt["schema"] == RESOURCE and receipt["status"] == "measured"
                and receipt["memory_kind"] == "linux_cgroup_charge"
                and integer(receipt["budget_ns"]) == B and integer(receipt["stop_ns"]) == S)
        import re
        require(type(receipt["run_id"]) is str and re.fullmatch("[a-f0-9]{32}", receipt["run_id"])
                and type(receipt["admission_sha256"]) is str and re.fullmatch("[a-f0-9]{64}", receipt["admission_sha256"]))
        for key, cap in (("cpu_ns", B), ("user_cpu_ns", B), ("system_cpu_ns", B), ("max_sample_gap_ns", GAP), ("peak_charge_bytes", MEMORY)):
            integer(receipt[key], cap)
        require(receipt["cpu_ns"] < S and receipt["user_cpu_ns"] <= receipt["cpu_ns"]
                and receipt["system_cpu_ns"] <= receipt["cpu_ns"])
        require(integer(receipt["active_processes"]) == 0 and integer(receipt["sample_count"]) >= 2
                and integer(receipt["stable_final_ns"]) >= integer(receipt["drained_ns"]) + GAP)
        require(all(receipt[k] is False for k in ("runtime_authorized", "method_accepted", "host_admitted")))
        from waveform_m08_guardian import guardian_names
        guardian = receipt["guardian"]
        expected_scope = guardian_names(receipt["run_id"])[2]
        require(type(guardian) is dict and set(guardian) == set("scope group identity_transport memory_limit_bytes tasks_max wall_limit_seconds manager_job status scope_removed".split())
                and guardian["scope"] == expected_scope and guardian["group"] == "/system.slice/" + expected_scope
                and guardian["identity_transport"] == "PIDFDs/ah" and type(guardian["memory_limit_bytes"]) is int and guardian["memory_limit_bytes"] == 128*1024**2
                and type(guardian["tasks_max"]) is int and guardian["tasks_max"] == 16
                and type(guardian["wall_limit_seconds"]) is int and guardian["wall_limit_seconds"] == 150
                and type(guardian["manager_job"]) is str and re.fullmatch(r"/org/freedesktop/systemd1/job/[0-9]{1,20}", guardian["manager_job"])
                and guardian["status"] == "complete" and guardian["scope_removed"] is True)
        expected = {"schema": RELEASE, "run_id": receipt["run_id"], "receipt_sha256": sha256(canonical(receipt)),
                    "all_native_owned_handles_closed": True, "scope_removed": True, "runtime_authorized": False}
        require(release == expected and release["all_native_owned_handles_closed"] is True and release["scope_removed"] is True
                and release["runtime_authorized"] is False)
        return {"schema": "geophysics.waveform-resources/v1", "cpu_ns": receipt["cpu_ns"],
                "max_sample_gap_ns": receipt["max_sample_gap_ns"], "peak_memory_bytes": receipt["peak_charge_bytes"],
                "memory_kind": "linux_cgroup_charge", "native_receipt_sha256": release["receipt_sha256"],
                "release_sha256": sha256(canonical(release)), "runtime_authorized": False, "host_admitted": False}
    except (ControlError, KeyError, TypeError, ValueError, INPUT.WaveformInputError):
        raise ApiError(409, "waveform_resource_invalid", "Final Linux waveform scope or release is invalid") from None
