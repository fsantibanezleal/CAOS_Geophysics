"""Value-free native-parent containment prerequisite, before any matrix retry.

Ordinary CP313 cannot directly CreateProcess this Store-hosted CP312 image.
Use the explicitly permitted primary product venv ONLY as the parent context;
the bounded scientific Job still launches the original real image, never the
redirector. No native policy/source/ABI/caps or original data are changed.
"""
import argparse
import ctypes
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import time

from run_m03_qr_reproduction import dispatcher_ancestry,base,core,io,read,require,runtime

PARENT_SHA='0b471133e110cfb53a061cad528ce8e517d7b9ac41a0a396c39ad795a487fc14'
IMAGE_SHA='5365b422ee178f691988eb937b7abca5f48910b148f76fcce6dbaf5585c948d0'


def image_identity():
    native=ctypes.WinDLL('kernel32',use_last_error=True)
    native.GetModuleFileNameW.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_uint32]
    native.GetModuleFileNameW.restype=ctypes.c_uint32
    buffer=ctypes.create_unicode_buffer(32768)
    length=native.GetModuleFileNameW(None,buffer,len(buffer))
    require(0<length<len(buffer))
    path=Path(buffer.value).resolve(strict=True)
    return dict(path=str(path),sha256=sha256(path.read_bytes()).hexdigest())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('output','packages','dispatcher-lock','parent-executable'):
        parser.add_argument('--'+name,required=True)
    parser.add_argument('--native-child',action='store_true')
    args=parser.parse_args()
    lock=base.strict_json(read(args.dispatcher_lock,65536));require(set(lock)=={'pid','token'})
    occupancy=dispatcher_ancestry(lock['pid'])
    parent=Path(args.parent_executable).resolve(strict=True)
    require(sha256(parent.read_bytes()).hexdigest()==PARENT_SHA)
    output=Path(args.output);io.external_path(output.parent)
    packages=Path(args.packages).resolve(strict=True);require(packages.is_dir())
    if not args.native_child:
        require(sys.version_info[:2]==(3,13) and not output.exists())
        output.mkdir()
        command=[str(parent),'-B','-S',str(Path(__file__).resolve()),'--native-child',
            '--output',str(output),'--packages',str(packages),'--dispatcher-lock',args.dispatcher_lock,
            '--parent-executable',str(parent)]
        core._write_member(output,'parent-context-seal.json',base.canonical_bytes(dict(
            schema='m03-native-parent-context-seal/1',parent_redirector_sha256=PARENT_SHA,
            native_image_sha256=IMAGE_SHA,source_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
            dispatcher_lock=lock,occupancy=occupancy,argv=command,magnetic_value_access='not_opened',
            original_data_access='not_opened',native_fit_count=0,host_admission='not_established')))
        started=time.perf_counter()
        # Store activation can expand an absent SystemDrive literally. Its
        # platform cache must then land in the external counted bootstrap, not
        # the source checkout, before the script itself starts.
        completed=subprocess.run(command,cwd=output,check=False,timeout=45)
        if completed.returncode:return completed.returncode
        receipt=base.strict_json(read(output/'native-context-result.json'))
        require(receipt['verdict']=='component_pass' and receipt['native_fit_count']==0 and
                receipt['original_data_access']=='not_opened' and receipt['native_parent_image']['sha256']==IMAGE_SHA)
        drain=dict(
            schema='m03-native-parent-context-drain/2',bootstrap_exit=completed.returncode,
            bootstrap_wall_s=time.perf_counter()-started,receipt_sha256=base.digest(receipt),
            scientific_job_active_processes=receipt['lifetime']['active_processes'],
            scientific_job_total_processes=receipt['lifetime']['total_processes'],
            bootstrap_not_scientific_child=True,host_admission='not_established',bootstrap_owned_bytes=0)
        size=runtime.owned_bytes(output)
        for _ in range(8):
            exact=size+len(base.canonical_bytes(drain))
            if drain['bootstrap_owned_bytes']==exact:break
            drain['bootstrap_owned_bytes']=exact
        else:require(False)
        require(drain['bootstrap_owned_bytes']<=16*1024**2)
        core._write_member(output,'parent-context-drain.json',base.canonical_bytes(drain))
        require(runtime.owned_bytes(output)==drain['bootstrap_owned_bytes'])
        print(json.dumps(receipt,sort_keys=True),flush=True)
        return 0
    require(sys.version_info[:3]==(3,12,10) and output.is_dir())
    image=image_identity();require(image['sha256']==IMAGE_SHA)
    executable=Path(sys.base_prefix)/'python.exe'
    require(sha256(executable.read_bytes()).hexdigest()==IMAGE_SHA)
    workspace=output/'value-free-worker';workspace.mkdir()
    # Intentionally invalid fixed plan. The actual worker proves its inherited
    # scientific Job BEFORE closed-plan refusal; no CSV/array/value is present.
    core._write_member(workspace,'plan.json',b'{}')
    limits=dict(memory_bytes=512*1024**2,scratch_bytes=16*1024**2,cpu_s=10,wall_s=30,parent_cpu_s=10)
    lifetime=runtime.run_worker(executable,packages,workspace,workspace/'plan.json',configured_limits=limits)
    require(lifetime['verdict']=='resource_refused' and lifetime['exit_code']==2 and
        lifetime['active_processes']==0 and lifetime['total_processes']==1 and
        lifetime['actual_executable_sha256']==IMAGE_SHA and 0<lifetime['cpu_s']<=10 and 0<lifetime['wall_s']<=30 and
        0<=lifetime['parent_cpu_s']<=10 and 0<lifetime['peak_rss_bytes']<=512*1024**2 and
        0<lifetime['peak_committed_bytes']<=512*1024**2 and 0<lifetime['scratch_bytes']<=16*1024**2 and
        lifetime['stop_cpu_s'] is None and lifetime['stop_wall_s'] is None and lifetime['enforced_limits']==limits)
    error=base.strict_json(read(workspace/'stdout.log',65536))
    require(error==core.SurveyError('invalid_contract','seal').error)
    receipt=dict(schema='m03-native-parent-context/1',verdict='component_pass',
        native_parent_image=image,parent_redirector_sha256=PARENT_SHA,lifetime=lifetime,
        expected_worker_refusal=error,source_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
        occupancy=occupancy,native_fit_count=0,original_data_access='not_opened',
        magnetic_value_access='not_opened',host_admission='not_established')
    core._write_member(output,'native-context-result.json',base.canonical_bytes(receipt))
    return 0


if __name__=='__main__':raise SystemExit(main())
