"""Local M03 source-profile containment/measurements; no host admission.

The resource probe is NOT a predictive study or full-method acceptance. It
uses labelled synthetic zero-target maximum-shape controls, never opens a new
survey's magnetic truth, and retains actual refusal/cancellation evidence.
"""
from __future__ import annotations

import argparse
import ctypes
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"data-pipeline"))
import magnetic_line_contract as c
import magnetic_lines as p
import magnetic_line_validation as v


def _generator():
    file = ROOT/"tests/fixtures/magnetic_lines/generate.py"
    spec = importlib.util.spec_from_file_location("m03_resource_geometry",file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _new_json(path, value):
    data = c.canonical_bytes(value)
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        import os
        os.fsync(stream.fileno())
    return sha256(data).hexdigest()


def geometry_packet():
    """Fresh NULL geometry sealed BEFORE any new study values or predictions."""
    g = _generator()
    rows = g.refinement_geometry_rows()
    studies = []
    for width in (100.,50.):
        req = g.geometry_request(rows)
        profile = "m03-local-320/1" if width == 50. else None
        req["equivalent_sources"]["source_geometry"].update(block_e_m=width,block_n_m=width,max_sources=320 if profile else 256)
        seal = v.make_partitions(rows,req,local_profile=profile)
        proof = p.local_source_preallocation(rows,req,local_profile=profile)
        studies.append(dict(source_block_m=width,request=req,partitions=seal,preallocation=proof))
    return dict(schema="m03-new-null-geometry/1",geometry=v.geometry_manifest(rows),geometry_sha256=c.digest(v.geometry_manifest(rows)),
        studies=studies,magnetic_values_generated=False,original_s1_replaced=False,vps_admitted=False)


class Basic(ctypes.Structure):
    _fields_ = [("process_cpu",ctypes.c_longlong),("job_cpu",ctypes.c_longlong),("flags",ctypes.c_uint32),
        ("min_working",ctypes.c_size_t),("max_working",ctypes.c_size_t),("active",ctypes.c_uint32),
        ("affinity",ctypes.c_size_t),("priority",ctypes.c_uint32),("scheduling",ctypes.c_uint32)]


class IO(ctypes.Structure):
    _fields_ = [("counter"+str(i),ctypes.c_ulonglong) for i in range(6)]


class Limits(ctypes.Structure):
    _fields_ = [("basic",Basic),("io",IO),("process_memory",ctypes.c_size_t),("job_memory",ctypes.c_size_t),
        ("peak_process_memory",ctypes.c_size_t),("peak_job_memory",ctypes.c_size_t)]


class Accounting(ctypes.Structure):
    _fields_ = [("user",ctypes.c_longlong),("kernel",ctypes.c_longlong),("period_user",ctypes.c_longlong),("period_kernel",ctypes.c_longlong),
        ("faults",ctypes.c_uint32),("total",ctypes.c_uint32),("active",ctypes.c_uint32),("terminated",ctypes.c_uint32)]


class Startup(ctypes.Structure):
    _fields_ = [("cb",ctypes.c_uint32),("reserved",ctypes.c_wchar_p),("desktop",ctypes.c_wchar_p),("title",ctypes.c_wchar_p),
        *[(k,ctypes.c_uint32) for k in ("x","y","width","height","chars_x","chars_y","fill","flags")],
        ("show",ctypes.c_ushort),("reserved_bytes",ctypes.c_ushort),("reserved_ptr",ctypes.c_void_p),
        ("stdin",ctypes.c_void_p),("stdout",ctypes.c_void_p),("stderr",ctypes.c_void_p)]


class ProcessInfo(ctypes.Structure):
    _fields_ = [("process",ctypes.c_void_p),("thread",ctypes.c_void_p),("pid",ctypes.c_uint32),("tid",ctypes.c_uint32)]


class StartupEx(ctypes.Structure):
    _fields_ = [("startup",Startup),("attributes",ctypes.c_void_p)]


class Memory(ctypes.Structure):
    _fields_ = [("cb",ctypes.c_uint32),("faults",ctypes.c_uint32),*[(k,ctypes.c_size_t) for k in
        ("peak_working","working","peak_paged","paged","peak_nonpaged","nonpaged","pagefile","peak_pagefile","private")]]


def terminal_counters(api, psapi, job, process):
    """Retained process lifetime peaks and Job totals; no zero on query failure."""
    accounting, limits, memory = Accounting(), Limits(), Memory(cb=ctypes.sizeof(Memory))
    code = ctypes.c_uint32()
    if not api.QueryInformationJobObject(job,1,ctypes.byref(accounting),ctypes.sizeof(accounting),None) or \
        not api.QueryInformationJobObject(job,9,ctypes.byref(limits),ctypes.sizeof(limits),None) or \
        not psapi.GetProcessMemoryInfo(process,ctypes.byref(memory),ctypes.sizeof(memory)) or \
        not api.GetExitCodeProcess(process,ctypes.byref(code)) or code.value == 259:
        c.fail("local_profile.terminal_measurement","resource_refused")
    return accounting, limits, memory, code.value


def resource_eligible(record):
    """Each measured ceiling and cancellation reserve is necessary, not averaged."""
    if record.get("measurement_complete") is not True:
        return False
    for key, limit in (("child_tree_cpu_s",60),("controller_cpu_s",10),("wall_s",120),
        ("peak_tree_rss_bytes",536870912),("peak_job_commit_bytes",536870912),("peak_owned_scratch_bytes",67108864)):
        value = record.get(key)
        if type(value) not in (int,float) or not __import__("math").isfinite(value) or not 0 <= value <= limit:
            return False
    if record.get("mode") == "cancel":
        return record.get("terminal") == "cancelled" and record.get("exit_code") != 0 and all(
            type(record.get(k)) in (int,float) and 0 <= record[k] <= 10 for k in ("post_stop_cpu_s","post_stop_wall_s"))
    return record.get("terminal") == "completed" and record.get("exit_code") == 0


def measured_child(mode, output_directory, *, direct_base_runtime=False):
    """Suspended before Job assignment: actual lifetime CPU/commit/RSS/kill.

    One process only (no unaccounted descendants). Job commit<=512MiB is a
    stricter additional ceiling than RSS. Unavailable assignment/measurement
    refuses. Both controller CPU and post-termination totals are recorded.
    """
    if platform.system()!="Windows":
        c.fail("local_profile.windows_controller","resource_refused")
    api = ctypes.WinDLL("kernel32",use_last_error=True)
    api.CreateJobObjectW.argtypes = [ctypes.c_void_p,ctypes.c_wchar_p]
    api.CreateJobObjectW.restype = ctypes.c_void_p
    for name,args,ret in (
        ("SetInformationJobObject",[ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_uint32],ctypes.c_int),
        ("QueryInformationJobObject",[ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_uint32,ctypes.c_void_p],ctypes.c_int),
        ("AssignProcessToJobObject",[ctypes.c_void_p,ctypes.c_void_p],ctypes.c_int),
        ("TerminateJobObject",[ctypes.c_void_p,ctypes.c_uint32],ctypes.c_int),
        ("CloseHandle",[ctypes.c_void_p],ctypes.c_int),
        ("ResumeThread",[ctypes.c_void_p],ctypes.c_uint32),
        ("WaitForSingleObject",[ctypes.c_void_p,ctypes.c_uint32],ctypes.c_uint32),
        ("GetExitCodeProcess",[ctypes.c_void_p,ctypes.c_void_p],ctypes.c_int),
        ("TerminateProcess",[ctypes.c_void_p,ctypes.c_uint32],ctypes.c_int),
        ("SetHandleInformation",[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32],ctypes.c_int),
        ("InitializeProcThreadAttributeList",[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p],ctypes.c_int),
        ("UpdateProcThreadAttribute",[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_void_p],ctypes.c_int),
        ("DeleteProcThreadAttributeList",[ctypes.c_void_p],None),
        ("CreateProcessW",[ctypes.c_wchar_p,ctypes.c_wchar_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int,ctypes.c_uint32,
            ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_void_p,ctypes.c_void_p],ctypes.c_int)):
        function = getattr(api,name)
        function.argtypes,function.restype = args,ret
    psapi = ctypes.WinDLL("psapi",use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p,ctypes.c_void_p,ctypes.c_uint32]
    psapi.GetProcessMemoryInfo.restype = ctypes.c_int
    job = api.CreateJobObjectW(None,None)
    if not job:
        c.fail("local_profile.job_creation","resource_refused")
    process = ProcessInfo()
    start,controller_start = time.monotonic(),time.process_time()
    user=kernel=peak_rss=peak_commit=peak_scratch=0
    stopped_at=stop_wall=None
    cause="completed"
    streams=[]
    try:
        limits = Limits()
        limits.basic.flags = 0x2000|0x200|0x8|0x4
        limits.basic.active=1
        limits.basic.job_cpu=600000000
        limits.job_memory=536870912
        if not api.SetInformationJobObject(job,9,ctypes.byref(limits),ctypes.sizeof(limits)):
            c.fail("local_profile.job_limits","resource_refused")
        executable = str(Path(sys.base_prefix)/"python.exe") if direct_base_runtime else sys.executable
        command = subprocess.list2cmdline([executable,"-I",str(Path(__file__).resolve()),"--resource-child",mode,
            "--job-handle",str(job),"--scientific-site-packages",str(Path(sys.prefix)/"Lib/site-packages"),
            "--output-directory",str(output_directory)])
        import msvcrt
        streams=[open("NUL","rb"),(output_directory/(mode+"-stdout.txt")).open("xb"),(output_directory/(mode+"-stderr.txt")).open("xb")]
        standard=[msvcrt.get_osfhandle(s.fileno()) for s in streams]
        startup = StartupEx(startup=Startup(cb=ctypes.sizeof(StartupEx),flags=1|0x100,show=0,
            stdin=standard[0],stdout=standard[1],stderr=standard[2]))
        size = ctypes.c_size_t()
        api.InitializeProcThreadAttributeList(None,1,0,ctypes.byref(size))
        storage = ctypes.create_string_buffer(size.value)
        startup.attributes = ctypes.cast(storage,ctypes.c_void_p)
        handles = (ctypes.c_void_p*4)(job,*standard)
        if not all(api.SetHandleInformation(h,1,1) for h in (job,*standard)) or not api.InitializeProcThreadAttributeList(startup.attributes,1,0,ctypes.byref(size)) or \
            not api.UpdateProcThreadAttribute(startup.attributes,0,0x20002,ctypes.byref(handles),ctypes.sizeof(handles),None,None):
            c.fail("local_profile.restricted_inheritance","resource_refused")
        # CREATE_SUSPENDED | CREATE_NO_WINDOW; no pipe buffering/unbounded output.
        thread_keys=("OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","OMP_NUM_THREADS","NUMBA_NUM_THREADS")
        environment={k:value for k,value in os.environ.items() if k.upper() not in (*thread_keys,"NUMBA_CACHE_DIR")}
        environment.update({k:"1" for k in thread_keys})
        environment["NUMBA_CACHE_DIR"]=str(output_directory/(mode+"-owned-numba-cache"))
        block=ctypes.create_unicode_buffer("\0".join(k+"="+value for k,value in sorted(environment.items()))+"\0\0")
        if not api.CreateProcessW(executable,ctypes.create_unicode_buffer(command),None,None,True,0x4|0x08000000|0x80000|0x400,block,
                                  str(ROOT),ctypes.byref(startup),ctypes.byref(process)):
            c.fail("local_profile.child_creation","resource_refused")
        api.DeleteProcThreadAttributeList(startup.attributes)
        if not api.AssignProcessToJobObject(job,process.process):
            api.TerminateProcess(process.process,2)
            c.fail("local_profile.job_assignment","resource_refused")
        if api.ResumeThread(process.thread)==0xFFFFFFFF:
            c.fail("local_profile.child_resume","resource_refused")
        while True:
            accounting=Accounting()
            current=Limits()
            memory=Memory(cb=ctypes.sizeof(Memory))
            if not api.QueryInformationJobObject(job,1,ctypes.byref(accounting),ctypes.sizeof(accounting),None) or \
                not api.QueryInformationJobObject(job,9,ctypes.byref(current),ctypes.sizeof(current),None) or \
                not psapi.GetProcessMemoryInfo(process.process,ctypes.byref(memory),ctypes.sizeof(memory)):
                cause="measurement_refused"
                api.TerminateJobObject(job,2)
                break
            user,kernel = accounting.user/1e7,accounting.kernel/1e7
            peak_rss=max(peak_rss,memory.peak_working)
            peak_commit=max(peak_commit,current.peak_job_memory)
            elapsed = time.monotonic()-start
            scratch=sum(f.stat().st_size for f in output_directory.rglob("*") if f.is_file())
            peak_scratch=max(peak_scratch,scratch)
            if stopped_at is None and (user+kernel>=50 or elapsed>=120 or peak_rss>536870912 or scratch>67108864 or
                time.process_time()-controller_start>10 or
                (mode=="cancel" and (output_directory/"cancel-ready.json").is_file())):
                stopped_at,stop_wall = user+kernel,time.monotonic()
                cause="cancelled" if mode=="cancel" else "resource_refused"
                if not api.TerminateJobObject(job,2):
                    cause="stop_refused"
                    break
            wait = api.WaitForSingleObject(process.process,20)
            if wait==0:
                break
            if wait!=258 or (stop_wall is not None and time.monotonic()-stop_wall>10):
                cause="stop_refused"
                break
        accounting,current,memory,code = terminal_counters(api,psapi,job,process.process)
        user,kernel = accounting.user/1e7,accounting.kernel/1e7
        peak_rss=max(peak_rss,memory.peak_working)
        peak_commit=max(peak_commit,current.peak_job_memory)
        peak_scratch=max(peak_scratch,sum(f.stat().st_size for f in output_directory.rglob("*") if f.is_file()))
        if code!=0 and cause=="completed":
            cause="resource_or_native_refused"
        record = dict(mode=mode,terminal=cause,exit_code=code,measurement_complete=True,child_tree_user_s=user,child_tree_kernel_s=kernel,
            child_tree_cpu_s=user+kernel,controller_cpu_s=time.process_time()-controller_start,wall_s=time.monotonic()-start,
            peak_tree_rss_bytes=peak_rss,peak_job_commit_bytes=peak_commit,
            peak_owned_scratch_bytes=peak_scratch,
            post_stop_cpu_s=None if stopped_at is None else max(0.,user+kernel-stopped_at),
            post_stop_wall_s=None if stop_wall is None else time.monotonic()-stop_wall,
            active_process_limit=1,cpu_limit_s=60,stop_cpu_s=50,wall_limit_s=120,rss_limit_bytes=536870912,commit_limit_bytes=536870912,
            suspended_before_assignment=True,vps_admitted=False,direct_base_runtime=direct_base_runtime,
            executable_sha256=sha256(Path(executable).read_bytes()).hexdigest())
        _new_json(output_directory/(mode+"-measurement.json"),record)
        return record
    finally:
        api.CloseHandle(job)  # Kill-on-close; cleanup ONLY this owned process job.
        if process.thread:
            api.CloseHandle(process.thread)
        if process.process:
            api.CloseHandle(process.process)
        for stream in streams:
            stream.close()


def run_contract_probe(directory, job_handle):
    """Opened S3 -> one25-fit run -> actual immutable export and verified custody."""
    p._local_resource_guard(job_handle)
    g = _generator()
    raw,meta,request = g.instrument_input(raw_mirroring="allowed")
    request["export_policy"]["raw_requested"] = "include"
    request["equivalent_sources"]["source_geometry"]["max_sources"] = 320
    originals = (raw,c.canonical_bytes(meta),c.canonical_bytes(request))
    custody = p.export_run(*originals,directory/"contract-bundle",local_profile="m03-local-320/1",local_job_handle=job_handle)
    verified,result,body = p.verify_bundle(directory/"contract-bundle",local_profile="m03-local-320/1",local_job_handle=job_handle)
    if verified != custody or tuple(body[k] for k in ("original.csv","sidecar.json","request.json")) != originals or \
        result["fit"]["production_fit_count"] != 25 or len(list((directory/"contract-bundle").iterdir())) != 7:
        c.fail("profile.full_export_custody","custody_mismatch")
    _new_json(directory/"contract-probe.json",dict(production_fit_count=result["fit"]["production_fit_count"],
        numerical_success=result["verdict"]["numerical_success"],fresh_study_truth_generated=False,
        schema=result["schema"],result_sha256=sha256(body["result.json"]).hexdigest(),
        custody_sha256=sha256(c.canonical_bytes(custody)).hexdigest(),immutable_export_verified=True,
        export_member_count=7,additional_verification_fits=0))


def resource_child(mode, directory, job_handle):
    p._local_resource_guard(job_handle)
    api=ctypes.WinDLL("kernel32",use_last_error=True)
    api.GetCurrentProcess.restype=ctypes.c_void_p
    api.QueryFullProcessImageNameW.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_wchar_p,ctypes.c_void_p]
    api.QueryFullProcessImageNameW.restype=ctypes.c_int
    image=ctypes.create_unicode_buffer(32768)
    count=ctypes.c_uint32(len(image))
    if not api.QueryFullProcessImageNameW(api.GetCurrentProcess(),0,image,ctypes.byref(count)):
        c.fail("profile.actual_process_image","custody_mismatch")
    _new_json(directory/(mode+"-stage.json"),dict(stage="scientific_imports_started",actual_job_membership=True,
        python_revision=platform.python_version(),python_executable_sha256=sha256(Path(image.value).read_bytes()).hexdigest()))
    p.engines()
    if mode=="contract":
        run_contract_probe(directory,job_handle)
        return
    g = _generator()
    if mode in ("study-100","study-50"):
        packet=c.strict_json(c.read_bounded(directory/"fresh-null-geometry.json",2097152))
        expected=geometry_packet()
        if packet!=expected or packet["magnetic_values_generated"] is not False:
            c.fail("study.geometry_seal","custody_mismatch")
        for key in ("probe","cancel","contract"):
            measurement=c.strict_json(c.read_bounded(directory/(key+"-measurement.json"),2097152))
            if not resource_eligible(measurement):
                c.fail("study.actual_profile_prerequisite","resource_refused")
            if key=="cancel" and (measurement["post_stop_cpu_s"] is None or measurement["post_stop_cpu_s"]>10 or measurement["post_stop_wall_s"]>10):
                c.fail("study.cancel_reserve","resource_refused")
        ready=c.strict_json(c.read_bounded(directory/"cancel-ready.json",2097152))
        if ready["stage"]!="repeated_real_native_fit_workload" or ready["completed_native_fits"]<1:
            c.fail("study.native_cancellation_evidence","resource_refused")
        width=100. if mode=="study-100" else 50.
        # The first NEW values are generated ONLY after the independent NULL
        # seals and all actual cold profile prerequisites have passed.
        raw,meta,request=g.refinement_input(width,packet["geometry_sha256"])
        originals=(raw,c.canonical_bytes(meta),c.canonical_bytes(request))
        for name,body in zip(("input.csv","sidecar.json","request.json"),originals):
            with (directory/(mode+"-"+name)).open("xb") as stream:
                stream.write(body)
        _new_json(directory/(mode+"-input-identity.json"),dict(raw_sha256=sha256(raw).hexdigest(),raw_bytes=len(raw),
            sidecar_sha256=sha256(originals[1]).hexdigest(),request_sha256=sha256(originals[2]).hexdigest(),
            geometry_manifest_sha256=packet["geometry_sha256"],truth_generated=True,outer_evaluations_at_this_stage=0))
        profile="m03-local-320/1" if width==50. else None
        custody=p.export_run(*originals,directory/mode,local_profile=profile,local_job_handle=job_handle)
        _,result,_=p.verify_bundle(directory/mode,local_profile=profile,local_job_handle=job_handle)
        _new_json(directory/(mode+"-outcome.json"),dict(source_block_m=width,source_count=result["fit"]["source_positions"]["shape"][0],
            request_sha256=sha256(originals[2]).hexdigest(),raw_sha256=sha256(raw).hexdigest(),custody=custody,
            outer_rmse_nT=result["evaluation"]["outer"]["rmse_nT"],synthetic_quality=result["evaluation"]["synthetic_acceptance"],
            selected_candidate_id=result["fit"]["selected_candidate_id"],outer_evaluations=result["partitions"]["evaluation_count"],
            numerical_success=result["verdict"]["numerical_success"],original_s1_replaced=False,vps_admitted=False))
        return
    rows = []
    for i in range(400):
        b = i%320
        rows.append(dict(row_id=f"R{i:03d}",line_id="resource-only",line_kind="flight",sensor_id="S0",ordinal=i,utc=None,
            easting_m=float(100*(b%20)),northing_m=float(100*(b//20)),upward_m=80.,terrain_upward_m=0.,clearance_m=80.,
            heading_deg=None,magnetic_nT=0.,uncertainty_nT=None))
    config=g.geometry_request(g.geometry_rows())["equivalent_sources"]
    config["source_geometry"].update(origin_e_m=0.,origin_n_m=0.,block_e_m=50.,block_n_m=50.,max_sources=320)
    if mode=="cancel":
        p.fit_equivalent(rows,config,500.,.0001,local_profile="m03-local-320/1",local_job_handle=job_handle)
        _new_json(directory/"cancel-ready.json",dict(stage="repeated_real_native_fit_workload",completed_native_fits=1,
            precise_instruction_pointer_claim=False))
        while True:
            p.fit_equivalent(rows,config,500.,.0001,local_profile="m03-local-320/1",local_job_handle=job_handle)
    completed=0
    for depth in config["depth_candidates_m"]:
        for damping in config["damping_candidates"]:
            for fold in range(3):
                fit=p.fit_equivalent(rows,config,depth,damping,local_profile="m03-local-320/1",local_job_handle=job_handle)
                assert len(fit["source_positions"])==320
                completed+=1
    p.fit_equivalent(rows,config,500.,.0001,local_profile="m03-local-320/1",local_job_handle=job_handle)
    completed+=1
    _new_json(directory/"component-probe.json",dict(schema="m03-resource-component/1",rows=400,sources=320,fits=completed,
        target="synthetic_exact_zero_resource_only",outer_evaluations=0,fresh_study_truth_generated=False,
        whole_scientific_pipeline_measured=False,full_request_serialization_measured=False,native_solver_cancel_proved=False))


def main(argv=None):
    controller_start = time.process_time()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-directory",required=True)
    parser.add_argument("--resource-child",choices=("probe","cancel","contract","study-100","study-50"))
    parser.add_argument("--job-handle",type=int)
    parser.add_argument("--scientific-site-packages")
    parser.add_argument("--direct-base-runtime",action="store_true")
    parser.add_argument("--resource-only",action="store_true",help="Probe/cancel/previously opened contract only; never generate new study truth")
    args=parser.parse_args(argv)
    directory=Path(args.output_directory)
    try:
        if args.resource_child:
            if args.scientific_site_packages:
                # Explicit existing owned virtualenv package path. No install,
                # sys.prefix rewriting or claim of virtualenv executable origin.
                site = Path(args.scientific_site_packages).resolve()
                if site.name!="site-packages" or not site.is_dir():
                    c.fail("profile.scientific_site","custody_mismatch")
                sys.path.insert(0,str(site))
            resource_child(args.resource_child,directory,args.job_handle)
            return 0
        directory=p._safe_directory(directory,absent=True)
        directory.mkdir()
        geometry_sha=_new_json(directory/"fresh-null-geometry.json",geometry_packet())
        pin=_new_json(directory/"source-pins.json",dict(source={name:sha256((ROOT/name).read_bytes()).hexdigest() for name in (
            "scripts/check_magnetic_artifacts.py","data-pipeline/magnetic_lines.py","data-pipeline/magnetic_line_validation.py",
            "data-pipeline/magnetic_line_contract.py","tests/fixtures/magnetic_lines/generate.py")},environment=p.environment_identity()))
        measured=[]
        eligible=True
        for mode in ("probe","cancel","contract"):
            record=measured_child(mode,directory,direct_base_runtime=args.direct_base_runtime)
            measured.append(record)
            eligible &= resource_eligible(record)
        if eligible and not args.resource_only:
            for mode in ("study-100","study-50"):
                measured.append(measured_child(mode,directory,direct_base_runtime=args.direct_base_runtime))
            eligible &= all(resource_eligible(r) for r in measured[-2:])
        controller_cpu = time.process_time()-controller_start
        eligible &= controller_cpu <= 10
        verdict = ("local_component_resource_pass" if args.resource_only else "local_resource_pass") if eligible else "resource_refused"
        _new_json(directory/"study-resource-outcome.json",dict(schema="m03-local-study-resource/1",geometry_file_sha256=geometry_sha,
            source_pins_file_sha256=pin,measurements=measured,verdict=verdict,controller_total_cpu_s=controller_cpu,
            measurement_scope="component_and_existing_contract_only" if args.resource_only else "component_contract_and_both_fresh_studies",
            fresh_truth_generated=any((directory/(m+"-input-identity.json")).exists() for m in ("study-100","study-50")),
            original_s1_replaced=False,vps_admitted=False))
        print(json.dumps(dict(verdict=verdict,vps_admitted=False)))
        return 0 if eligible else 2
    except c.MagneticContractError as exc:
        if args.resource_child:
            _new_json(directory/(args.resource_child+"-child-refusal.json"),exc.error)
            return 2
        print(json.dumps(exc.error))
        return 2
    except Exception:
        error=p.LocalWorkflowError("numerical_failure","profile.component",stage="fit")
        if args.resource_child:
            _new_json(directory/(args.resource_child+"-child-refusal.json"),error.error)
        else:
            print(json.dumps(error.error))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
