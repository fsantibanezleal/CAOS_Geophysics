import { describe, expect, it } from "vitest";
import { profileProducerBytes, PROFILE_LINUX_SOURCES, verifyProfileLinuxPair } from "../api/profile-linux-receipt";
import { strictVelocityJson } from "../api/velocity-local-contracts";
import type { ProfileProcessingJob } from "../api/processing-contracts";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { unzipSync, zipSync } from "fflate";
import { readProtectedProfile, verifyProfileBundle } from "../api/profile-processing";
import { profileJsonMembers } from "../api/profile-local-contracts";
import { isProfileJob, isProfileReceipt, parseProjectDatasetReceipt, parseProjectProcessingJob } from "../api/processing-contracts";

// Authored operational GRAMMAR controls, not an accepted native/paired science
// result. Never graft an installation record onto a historical q04 result.
const h="a".repeat(64),other="b".repeat(64),jobId="4f835035-83ce-4cff-8339-b185fe2cfd75";
const encoder=new TextEncoder();
const digest=async(raw:Uint8Array)=>[...new Uint8Array(await crypto.subtle.digest("SHA-256",raw as Uint8Array<ArrayBuffer>))].map(v=>v.toString(16).padStart(2,"0")).join("");
const job={job_id:jobId,request_sha256:h,dataset_sha256:h,
  request:{raw_sha256:h,profile_child_sha256:h,profile_code_hashes:{"ert.py":h,"profile_mesh.py":h,"supplied_profiles.py":h}},
  preflight:{wall_limit_seconds:600,memory_limit_bytes:2147483648,scratch_limit_bytes:67108864}} as unknown as ProfileProcessingJob;
const producer='{"authored_control":"grammar-only, not native proof","float_tokens":[1.0,-0.0,1e-20,9007199254740993],"raw_bytes":42}';
type RecordValue=Record<string,any>; // Authored mutation harness, never production data typing.
async function packet(){
  const sources=Object.fromEntries(PROFILE_LINUX_SOURCES.map(name=>[name,h]));
  const installation={configuration_sha256:h,python_sha256:h,environment_sha256:h,invocation_sha256:h,source_hashes:sources};
  const unit="geophysics-profile-"+jobId+".service",scope="geophysics-profile-guardian-"+jobId+".scope";
  const execution:RecordValue={schema:"geophysics.profile-linux-execution/v1",job_id:jobId,request_sha256:h,dataset_sha256:h,raw_sha256:h,
    ...installation,unit,terminal:{MainPID:"0",SubState:"dead",Result:"success",ExecMainStatus:"0",ControlGroup:""},
    stop_reason:null,failure:null,launch_attempted:true,extinction:"proved",guardian_status:"complete",
    guardian_scope:{scope,group:"/system.slice/"+scope,memory_limit_bytes:134217728,tasks_max:16,wall_limit_seconds:630,identity_transport:"PIDFDs/ah",manager_job:"/org/freedesktop/systemd1/job/123"},
    mounted_input_identities:{original:{device:1,inode:17,bytes:42,sha256:h},"dataset.json":{device:1,inode:18,bytes:52,sha256:h}},
    retained_stage_identity:{device:1,inode:19},wall_seconds:123.5,
    resources:{sampled_root_rss_peak_bytes:1024,rss_samples:1,kernel_memcg_peak_bytes:2048,sampled_unit_rss_peak_bytes:1024,unit_rss_samples:1,memcg_reads:1,
      memory_events:"oom 0\noom_kill 0\n",cgroup_events:null,exact_group_removed:true,hard_writable_scratch_bytes:4096,held_input_bytes:94},
    retained:{"result.json":{bytes:encoder.encode(producer).length,sha256:await digest(encoder.encode(producer))},"stderr.txt":{bytes:0,sha256:await digest(new Uint8Array())}},
    originals_reverified:true,held_inputs_state:"declared_copies_removed",cpu_accounting_admitted:false,host_admission:false};
  return {execution,installation:structuredClone(installation)};
}
function outer(execution:unknown,installation:unknown){return producer.slice(0,-1)+',"linux_execution":'+JSON.stringify(execution)+',"linux_installation":'+JSON.stringify(installation)+'}';}
async function verify(raw:string,admittedJob=job){return verifyProfileLinuxPair(raw,strictVelocityJson(encoder.encode(raw)) as Record<string,unknown>,admittedJob);}

describe("closed optional Linux pair, not native proof",()=>{
  it("leaves an absent pair without a Linux execution claim",async()=>{await expect(verify(producer)).resolves.toBeUndefined();});
  it("verifies the authored grammar and preserves every original numeric token",async()=>{
    const {execution,installation}=await packet(),raw=outer(execution,installation);
    expect(new TextDecoder().decode(profileProducerBytes(raw))).toBe(producer);
    expect(JSON.stringify(JSON.parse(producer))).not.toBe(producer);
    await expect(verify(raw)).resolves.toBeUndefined();
    const normalized=JSON.stringify(JSON.parse(raw));await expect(verify(normalized)).rejects.toThrow();
  });
  it.each(["linux_execution","linux_installation"])("refuses missing partner %s",async missing=>{
    const {execution,installation}=await packet();
    const raw=producer.slice(0,-1)+(missing==="linux_execution"?',"linux_installation":'+JSON.stringify(installation):',"linux_execution":'+JSON.stringify(execution))+'}';
    await expect(verify(raw)).rejects.toThrow();
  });
  it.each(["configuration_sha256","python_sha256","environment_sha256","invocation_sha256"])("refuses installation digest drift %s",async key=>{
    const {execution,installation}=await packet();(installation as RecordValue)[key]=other;await expect(verify(outer(execution,installation))).rejects.toThrow();
  });
  it.each(["execution","installation","resources","terminal","guardian_scope","mounted_input_identities","retained_stage_identity","retained"])("refuses extra or missing closed %s fields",async section=>{
    for(const remove of [false,true]){
      const {execution,installation}=await packet(),target=section==="execution"?execution:section==="installation"?installation:execution[section];
      if(remove)delete (target as RecordValue)[Object.keys(target)[0]];else (target as RecordValue).unknown=true;
      await expect(verify(outer(execution,installation))).rejects.toThrow();
    }
  });
  it.each(PROFILE_LINUX_SOURCES)("binds exact source %s",async name=>{
    const {execution,installation}=await packet();execution.source_hashes[name]=other;
    await expect(verify(outer(execution,installation))).rejects.toThrow();
  });
  it("refuses missing/extra sources and admitted child or numerical source drift",async()=>{
    const {execution,installation}=await packet();execution.source_hashes.unknown=h;installation.source_hashes=structuredClone(execution.source_hashes);
    await expect(verify(outer(execution,installation))).rejects.toThrow();
    for(const key of ["scripts/process_profile_job.py","data-pipeline/ert.py","data-pipeline/profile_mesh.py","data-pipeline/supplied_profiles.py"]){
      const fresh=await packet();fresh.execution.source_hashes[key]=other;fresh.installation.source_hashes=structuredClone(fresh.execution.source_hashes);
      await expect(verify(outer(fresh.execution,fresh.installation))).rejects.toThrow();
    }
  });
  it.each(["job_id","request_sha256","dataset_sha256","raw_sha256","unit"])("binds the admitted job %s",async key=>{
    const {execution,installation}=await packet();execution[key]=other;await expect(verify(outer(execution,installation))).rejects.toThrow();
  });
  it.each(["launch_attempted","originals_reverified","cpu_accounting_admitted","host_admission"])("requires literal operational boolean %s",async key=>{
    const {execution,installation}=await packet();execution[key]=!execution[key];await expect(verify(outer(execution,installation))).rejects.toThrow();
  });
  it.each(["failure","stop_reason","extinction","guardian_status","held_inputs_state"])("refuses non-success evidence %s",async key=>{
    const {execution,installation}=await packet();execution[key]="unproved";await expect(verify(outer(execution,installation))).rejects.toThrow();
  });
  it.each(["MainPID","ExecMainStatus","Result","SubState","ControlGroup"])("requires extinct successful terminal %s",async key=>{
    const {execution,installation}=await packet();execution.terminal[key]="foreign-or-live";await expect(verify(outer(execution,installation))).rejects.toThrow();
  });
  it("requires exact guardian scope, transport, actual original limits and manager job",async()=>{
    for(const [key,value] of [["scope","foreign.scope"],["group","/other"],["memory_limit_bytes",1],["tasks_max",17],
      ["wall_limit_seconds",629],["identity_transport","PIDs"],["manager_job","/foreign/123"]]){
      const {execution,installation}=await packet();execution.guardian_scope[key as string]=value;await expect(verify(outer(execution,installation))).rejects.toThrow();
    }
  });
  it("uses exact int64 lexical grammar, never JS-rounded identity or float counters",async()=>{
    const {execution,installation}=await packet(),raw=outer(execution,installation);
    await expect(verify(raw.replace('"inode":19','"inode":9007199254740993'))).resolves.toBeUndefined();
    for(const token of ["1.0","1e0","true","-1","9223372036854775808"])
      await expect(verify(raw.replace('"rss_samples":1','"rss_samples":'+token))).rejects.toThrow();
    await expect(verify(raw.replace('"inode":19','"inode":9223372036854775808'))).rejects.toThrow();
  });
  it("requires bounded resources, original bytes and an exactly empty or removed group",async()=>{
    for(const [key,value] of [["rss_samples",0],["kernel_memcg_peak_bytes",2147483649],["hard_writable_scratch_bytes",67108865],["held_input_bytes",95],
      ["exact_group_removed",false],["memory_events","x".repeat(4097)]]){
      const {execution,installation}=await packet();execution.resources[key as string]=value;await expect(verify(outer(execution,installation))).rejects.toThrow();
    }
    const {execution,installation}=await packet();execution.resources.exact_group_removed=false;execution.resources.cgroup_events="populated 0\r";
    await expect(verify(outer(execution,installation))).resolves.toBeUndefined();
    execution.resources.cgroup_events="populated 01\n";await expect(verify(outer(execution,installation))).rejects.toThrow();
  });
  it("refuses mounted input identity, source byte/hash and retained byte/hash drift",async()=>{
    for(const mutate of [(r:RecordValue)=>r.mounted_input_identities.original.bytes++,
      (r:RecordValue)=>r.mounted_input_identities.original.sha256=other,(r:RecordValue)=>r.mounted_input_identities["dataset.json"].inode=0,
      (r:RecordValue)=>r.retained["result.json"].bytes++,(r:RecordValue)=>r.retained["result.json"].sha256=other,
      (r:RecordValue)=>r.retained["stderr.txt"].bytes=-1,(r:RecordValue)=>r.wall_seconds=641]){
      const {execution,installation}=await packet();mutate(execution);await expect(verify(outer(execution,installation))).rejects.toThrow();
    }
  });
  it("does not exclude nested or similarly named scientific members",async()=>{
    const {execution,installation}=await packet(),raw=outer(execution,installation).replace('"float_tokens"','"linux_execution_shadow"');
    await expect(verify(raw)).rejects.toThrow();
  });
  it("requires bounded duplicate-free preflight before interpretation",async()=>{
    const {execution,installation}=await packet(),raw=outer(execution,installation);
    await expect(verify(raw.replace('"host_admission":false','"host_admission":false,"host_admission":false'))).rejects.toThrow();
  });
});

// Original completed worker bytes only. Operational mutations below are
// rejection controls, not authored successful paired scientific results.
describe("original protected worker pair read and ZIP",()=>{
  for(const name of ["GEOPHYSICS_PROFILE_JOB_ERT","GEOPHYSICS_PROFILE_JOB_TRAVELTIME"]){
    it.skipIf(!process.env[name])(`checks actual bytes and rejects operational drift: ${name}`,async()=>{
      const root=process.env[name]!,bindings=JSON.parse(readFileSync(join(root,"bindings.json"),"utf8"));
      const admittedJob=parseProjectProcessingJob(bindings.job),receipt=parseProjectDatasetReceipt(bindings.receipt);
      if(!isProfileJob(admittedJob)||!isProfileReceipt(receipt))throw new Error("Not original worker bindings");
      const original=readFileSync(join(root,"result.json")),raw=new TextDecoder().decode(original),fields=profileJsonMembers(raw);
      const execution=fields.get("linux_execution"),installation=fields.get("linux_installation");
      await readProtectedProfile(new Uint8Array(original),admittedJob,receipt);
      const archive=new Uint8Array(readFileSync(join(root,"export.zip")));
      await verifyProfileBundle(new Blob([archive]),admittedJob,receipt);
      if(!execution&&!installation)return; // Original Windows bytes, no Linux claim.
      expect(execution&&installation).toBeTruthy();
      const producerBytes=profileProducerBytes(raw),op=JSON.parse(raw.slice(execution!.valueStart,execution!.valueEnd));
      expect(producerBytes.length).toBe(op.retained["result.json"].bytes);
      expect(await digest(producerBytes)).toBe(op.retained["result.json"].sha256);
      const remove=(key:string)=>{
        const field=fields.get(key)!;
        return raw[field.end]===","?raw.slice(0,field.start)+raw.slice(field.end+1):raw.slice(0,field.start-1)+raw.slice(field.end);
      };
      const installationRecord=JSON.parse(raw.slice(installation!.valueStart,installation!.valueEnd));
      const mutated=[remove("linux_execution"),remove("linux_installation")];
      for(const key of INSTALLATION_DIGESTS){
        const value={...installationRecord,[key]:installationRecord[key]==="0".repeat(64)?h:"0".repeat(64)};
        mutated.push(raw.slice(0,installation!.valueStart)+JSON.stringify(value)+raw.slice(installation!.valueEnd));
      }
      mutated.push(raw.slice(0,installation!.valueStart)+JSON.stringify({...installationRecord,unknown:true})+raw.slice(installation!.valueEnd));
      for(const changed of mutated){
        const bytes=encoder.encode(changed),sha=await digest(bytes),jobWithChangedOuter={...admittedJob,result_sha256:sha};
        await expect(readProtectedProfile(bytes,jobWithChangedOuter,receipt)).rejects.toThrow();
        const members=unzipSync(archive),manifest=JSON.parse(new TextDecoder().decode(members["manifest.json"]));
        members["result.json"]=bytes;manifest.members["result.json"]={bytes:bytes.length,sha256:sha};
        members["manifest.json"]=encoder.encode(JSON.stringify(manifest));
        await expect(verifyProfileBundle(new Blob([zipSync(members,{level:0})]),jobWithChangedOuter,receipt)).rejects.toThrow();
      }
    });
  }
});
const INSTALLATION_DIGESTS=["configuration_sha256","python_sha256","environment_sha256","invocation_sha256"];
