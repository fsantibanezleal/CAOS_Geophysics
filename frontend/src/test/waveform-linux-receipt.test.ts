/** Authored closed operational grammar only, never native execution proof. */
import { describe,expect,it } from "vitest";
import actual from "./fixtures/waveform-authored-calculation.json";
import { WAVEFORM_METHOD,type WaveformJob,type WaveformDataset } from "../api/waveform-contracts";
import { readProtectedWaveform,waveformResultBytes,WAVEFORM_LINUX_SOURCES } from "../api/waveform-linux-receipt";

const id="00000000-0000-4000-8000-000000000001",h="a".repeat(64),other="b".repeat(64),encoder=new TextEncoder();
type RecordValue=Record<string,any>; // Authored mutation harness, not product data typing.
function canonical(value:any):string {
  if(typeof value==="bigint")return value.toString();
  if(Array.isArray(value))return "["+value.map(canonical).join(",")+"]";
  if(value&&typeof value==="object")return "{"+Object.keys(value).sort().map(k=>JSON.stringify(k)+":"+canonical(value[k])).join(",")+"}";
  return JSON.stringify(value);
}
async function digest(raw:string){return [...new Uint8Array(await crypto.subtle.digest("SHA-256",encoder.encode(raw)))].map(v=>v.toString(16).padStart(2,"0")).join("");}
async function packet(){
  const calculation=structuredClone(actual),source_hashes=Object.fromEntries(WAVEFORM_LINUX_SOURCES.map(name=>[name,h]));
  const installation={configuration_sha256:h,python_sha256:h,environment_sha256:h,invocation_sha256:h,source_hashes};
  const sources=Object.fromEntries(["miniseed","stationxml"].map(role=>[role,{asset_id:id,source_id:id,source_version:1,
    raw_sha256:calculation.sources[role as "miniseed"|"stationxml"].raw_sha256,raw_bytes:calculation.sources[role as "miniseed"|"stationxml"].raw_bytes,
    rights_decision:"mirror",private_storage_permission:"attested"}]));
  const members=[{name:"calculation.json",bytes:17605,sha256:h},{name:"receipt.json",bytes:833,sha256:h},
    {name:"manifest.json",bytes:2481,sha256:h},...calculation.array_descriptors.map(d=>({name:`c0${d.channel_index}-${d.name}.bin`,bytes:d.bytes,sha256:d.sha256}))].sort((a,b)=>a.name<b.name?-1:a.name>b.name?1:0);
  const run="1".repeat(32),scope="m08guard-"+run+".scope",stamp=9007199254740993n;
  const guardian={scope,group:"/system.slice/"+scope,identity_transport:"PIDFDs/ah",manager_job:"/org/freedesktop/systemd1/job/123",
    memory_limit_bytes:134217728,tasks_max:16,wall_limit_seconds:150,scope_removed:true};
  const eligibility={schema:"caos.m08-linux-resources.v2",run_id:run,status:"measured",cpu_ns:1000000000,user_cpu_ns:800000000,system_cpu_ns:200000000,
    budget_ns:60000000000,stop_ns:57000000000,sample_count:3,max_sample_gap_ns:50000000,peak_charge_bytes:1234,active_processes:0,
    drained_ns:stamp,stable_final_ns:stamp+100000000n,admission_sha256:h,memory_kind:"linux_cgroup_charge",runtime_authorized:false,
    method_accepted:false,host_admitted:false,guardian:{...guardian,status:"complete"}};
  const release={schema:"caos.m08-linux-release.v1",run_id:run,receipt_sha256:await digest(canonical(eligibility)),
    all_native_owned_handles_closed:true,scope_removed:true,runtime_authorized:false};
  const request={method_id:WAVEFORM_METHOD,scientific_request_sha256:calculation.request.scientific_sha256,
    implementation_sha256:await digest(canonical(source_hashes)),waveform_sources:sources,scientific_request:calculation.request.submitted};
  const job={job_id:id,project_id:id,dataset_id:id,dataset_sha256:h,request_sha256:h,method_id:WAVEFORM_METHOD,state:"succeeded",request} as unknown as WaveformJob;
  const dataset={dataset_id:id,project_id:id,owner_id:id,sources,request:calculation.request.submitted,
    scientific_request_sha256:calculation.request.scientific_sha256} as unknown as WaveformDataset;
  const execution:RecordValue={schema:"geophysics.waveform-linux-execution/v1",job:{id,owner_id:id,project_id:id,dataset_id:id,
    dataset_sha256:h,request_sha256:h,method_id:WAVEFORM_METHOD,implementation_sha256:request.implementation_sha256,
    scientific_request_sha256:request.scientific_request_sha256},sources,installation,stage:{device:1,inode:18446744073709551615n},
    root_custody:{device:1,inode:17,plan_sha256:h},outcome:{status:"computed",reason:"measured",run_id:run,
      receipt_sha256:release.receipt_sha256,release_sha256:await digest(canonical(release)),runtime_authorized:false},
    lifecycle:{extinction_proved:true,science_quiescent_ns:stamp+100000001n,caller:{reason:null,started_ns:null},
      final_counters:{cpu_ns:eligibility.cpu_ns,user_cpu_ns:eligibility.user_cpu_ns,system_cpu_ns:eligibility.system_cpu_ns,active_tasks:0,peak_charge_bytes:1234},
      guardian,run_id:run,admission_sha256:h,units:{service:"m08-"+run+".service",accounting:"m08"+run+".slice",guardian:scope}},
    native:{eligibility,release},calculation_sha256:h,members};
  const result:RecordValue={schema:"geophysics.waveform-result/v1",job_id:id,project_id:id,dataset_id:id,dataset_sha256:h,
    method_id:WAVEFORM_METHOD,request_sha256:h,scientific_request_sha256:request.scientific_request_sha256,sources,
    scientific_status:"computed",calculation_sha256:h,calculation,members,resources:{schema:"geophysics.waveform-resources/v1",
      cpu_ns:eligibility.cpu_ns,max_sample_gap_ns:eligibility.max_sample_gap_ns,peak_memory_bytes:1234,memory_kind:"linux_cgroup_charge",
      native_receipt_sha256:release.receipt_sha256,release_sha256:execution.outcome.release_sha256,runtime_authorized:false,host_admitted:false},
    linux_execution:execution,linux_installation:structuredClone(installation)};
  return {result:structuredClone(result),job:structuredClone(job),dataset:structuredClone(dataset)};
}
async function read(result:RecordValue,job:WaveformJob,dataset:WaveformDataset,raw=canonical(result)){
  return readProtectedWaveform(encoder.encode(raw),{...job,result_sha256:await digest(raw)},dataset);
}

describe("waveform complete Linux pair lexical custody, authored grammar only",()=>{
  it("retains exact raw uint64 bytes and returns defensive copies",async()=>{
    const {result,job,dataset}=await packet(),raw=canonical(result),parsed=await read(result,job,dataset,raw);
    expect(parsed.resources.memory_kind).toBe("linux_cgroup_charge");
    expect(new TextDecoder().decode(waveformResultBytes(parsed)!)).toBe(raw);
    const bytes=waveformResultBytes(parsed)!;bytes.fill(0);
    expect(new TextDecoder().decode(waveformResultBytes(parsed)!)).toBe(raw);
    expect(JSON.stringify(parsed)).not.toContain("linux_execution");
    expect(raw).toContain("18446744073709551615");expect(raw).toContain("9007199254740993");
  });
  it.each(["linux_execution","linux_installation"])("refuses missing %s",async key=>{
    const {result,job,dataset}=await packet();delete result[key];await expect(read(result,job,dataset)).rejects.toThrow();
  });
  it.each(["configuration_sha256","python_sha256","environment_sha256","invocation_sha256"])("binds installation %s",async key=>{
    const {result,job,dataset}=await packet();result.linux_installation[key]=other;await expect(read(result,job,dataset)).rejects.toThrow();
  });
  it.each(["job","stage","root_custody","lifecycle","native","outcome","installation"])("rejects unknown %s field",async key=>{
    const {result,job,dataset}=await packet();result.linux_execution[key].extra=true;await expect(read(result,job,dataset)).rejects.toThrow();
  });
  it.each(["float","exponent","bool","negative","overflow","rounded"])("refuses %s native stat tokens",async mode=>{
    const {result,job,dataset}=await packet();const token={float:"17.0",exponent:"17e0",bool:"true",negative:"-1",
      overflow:"18446744073709551616",rounded:"18446744073709552000"}[mode]!;
    await expect(read(result,job,dataset,canonical(result).replace("18446744073709551615",token))).rejects.toThrow();
  });
  it("refuses duplicate decoded keys, malformed UTF8 and excessive bytes",async()=>{
    const {result,job,dataset}=await packet(),raw=canonical(result);
    await expect(read(result,job,dataset,raw.replace('"extinction_proved":true','"extinction_proved":true,"extinction_\\u0070roved":true'))).rejects.toThrow();
    await expect(readProtectedWaveform(new Uint8Array([0xff]),job,dataset)).rejects.toThrow();
    await expect(readProtectedWaveform(new Uint8Array(4*1048576+1),job,dataset)).rejects.toThrow();
  });
  it("binds source, job, installation source map and release hashes",async()=>{
    const mutations=[(r:RecordValue)=>r.linux_execution.job.owner_id=other,(r:RecordValue)=>r.linux_execution.job.request_sha256=other,
      (r:RecordValue)=>r.linux_execution.sources.miniseed.raw_sha256=other,(r:RecordValue)=>r.linux_installation.source_hashes.unknown=h,
      (r:RecordValue)=>r.linux_execution.native.release.receipt_sha256=other];
    for(const mutate of mutations){const {result,job,dataset}=await packet();mutate(result);await expect(read(result,job,dataset)).rejects.toThrow();}
  });
  it("rejects unproved extinction, incorrect counters, timing, guardian and charge",async()=>{
    const mutations=[(r:RecordValue)=>r.linux_execution.lifecycle.extinction_proved=false,
      (r:RecordValue)=>r.linux_execution.lifecycle.final_counters.cpu_ns=0,
      (r:RecordValue)=>r.linux_execution.lifecycle.science_quiescent_ns=1,
      (r:RecordValue)=>r.linux_execution.lifecycle.guardian.scope_removed=false,
      (r:RecordValue)=>r.linux_execution.native.eligibility.cpu_ns=57000000000,
      (r:RecordValue)=>r.linux_execution.native.eligibility.memory_kind="rss",
      (r:RecordValue)=>r.linux_execution.outcome.runtime_authorized=true];
    for(const mutate of mutations){const {result,job,dataset}=await packet();mutate(result);await expect(read(result,job,dataset)).rejects.toThrow();}
  });
});
