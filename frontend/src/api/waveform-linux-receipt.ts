/** Full waveform terminal validation and exact lexical custody, never native replay. */
import { profileJsonMembers } from "./profile-local-contracts";
import { strictVelocityJson } from "./velocity-local-contracts";
import { processingObject as object,processingId as uuid,same } from "./processing-contracts";
import { parseWaveformResult,parseWaveformSources,bindWaveformResult,waveformMember,
  type WaveformResult,type WaveformJob,type WaveformDataset } from "./waveform-contracts";

export const WAVEFORM_RESULT_BYTE_CAP=4*1048576;
export const WAVEFORM_LINUX_SOURCES=["scripts/waveform_m08_linux.py","scripts/waveform_m08_windows.py",
  "scripts/waveform_m08_files.py","scripts/waveform_m08_export.py","scripts/waveform_m08_child.py",
  "scripts/process_waveform_m08.py","data-pipeline/waveform_input.py","data-pipeline/waveform_processing.py",
  "data-pipeline/waveform_evaluation.py","app/waveform_contract.py","app/waveform_processing.py",
  "app/waveform_result.py","app/waveform_worker.py","app/waveform_linux_exec.py","scripts/qualify_waveform_m08_linux.py",
  "scripts/waveform_m08_guardian.py","scripts/waveform_m08_installation.py","scripts/waveform_m08_owned_reader.py",
  "scripts/waveform_m08_supervisor.py","app/waveform_linux_worker.py","app/waveform_linux_execution.py",
  "app/waveform_publication.py","app/waveform_stage.py"] as const;
const INSTALLATION="configuration_sha256 python_sha256 environment_sha256 invocation_sha256 source_hashes".split(" ");
const EXECUTION="schema job sources installation stage root_custody outcome lifecycle native calculation_sha256 members".split(" ");
const JOB="id owner_id project_id dataset_id dataset_sha256 request_sha256 method_id implementation_sha256 scientific_request_sha256".split(" ");
const LIFE="extinction_proved science_quiescent_ns caller final_counters guardian run_id admission_sha256 units".split(" ");
const ELIGIBILITY="schema run_id status cpu_ns user_cpu_ns system_cpu_ns budget_ns stop_ns sample_count max_sample_gap_ns peak_charge_bytes active_processes drained_ns stable_final_ns admission_sha256 memory_kind runtime_authorized method_accepted host_admitted guardian".split(" ");
const GUARDIAN="scope group identity_transport memory_limit_bytes tasks_max wall_limit_seconds manager_job scope_removed".split(" ");
const COUNTERS="cpu_ns user_cpu_ns system_cpu_ns active_tasks peak_charge_bytes".split(" ");
const RELEASE="schema run_id receipt_sha256 all_native_owned_handles_closed scope_removed runtime_authorized".split(" ");
const U64=(1n<<64n)-1n,I63=(1n<<63n)-1n,B=60000000000n,S=57000000000n,GAP=100000000n,MEMORY=1073741824n;
const encoder=new TextEncoder(),verified=new WeakSet<object>(),custody=new WeakMap<object,Uint8Array>();
function check(ok:unknown):asserts ok {if(!ok)throw new Error("Protected waveform receipt rejected");}
function closed(value:unknown,keys:readonly string[]){const row=object(value,"waveform operational record");check(Object.keys(row).length===keys.length&&keys.every(k=>Object.hasOwn(row,k)));return row;}
function hash(value:unknown):string {check(typeof value==="string"&&/^[a-f0-9]{64}$/.test(value));return value;}
type Node={raw:string;value:Record<string,unknown>};
function child(parent:Node,key:string):Node {return {raw:token(parent,key),value:object(parent.value[key],"waveform operational child")};}
function token(parent:Node,key:string){const field=profileJsonMembers(parent.raw).get(key);check(field);return parent.raw.slice(field.valueStart,field.valueEnd);}
function integerToken(raw:string,low=0n,high=U64){check(raw.length<=21&&/^-?(?:0|[1-9][0-9]*)$/.test(raw));const value=BigInt(raw);check(value>=low&&value<=high);return value;}
function integer(node:Node,key:string,low=0n,high=U64){return integerToken(token(node,key),low,high);}
async function digest(raw:Uint8Array){return [...new Uint8Array(await crypto.subtle.digest("SHA-256",raw as Uint8Array<ArrayBuffer>))].map(v=>v.toString(16).padStart(2,"0")).join("");}

/** Already bounded/duplicate-preflighted native subtree; Python int, not Number. */
function nativeCanonical(raw:string):string {
  if(raw[0]==="{")return "{"+[...profileJsonMembers(raw)].sort(([a],[b])=>a<b?-1:a>b?1:0)
    .map(([key,field])=>{check(/^[\x20-\x7e]+$/.test(key));return JSON.stringify(key)+":"+nativeCanonical(raw.slice(field.valueStart,field.valueEnd));}).join(",")+"}";
  if(raw[0]==="["){
    const items:string[]=[];let start=1,depth=0;
    for(let i=1;i<raw.length-1;i++){
      if(raw[i]==='"'){for(i++;i<raw.length;i++){if(raw[i]==="\\")i++;else if(raw[i]==='"')break;}}
      else if(raw[i]==="{"||raw[i]==="[")depth++;
      else if(raw[i]==="}"||raw[i]==="]")depth--;
      else if(raw[i]===","&&depth===0){items.push(nativeCanonical(raw.slice(start,i).trim()));start=i+1;}
    }
    if(raw.slice(start,-1).trim())items.push(nativeCanonical(raw.slice(start,-1).trim()));
    return "["+items.join(",")+"]";
  }
  if(raw[0]==='"'){const value=JSON.parse(raw);check(typeof value==="string"&&/^[\x20-\x7e]*$/.test(value));return JSON.stringify(value);}
  if(raw==="true"||raw==="false"||raw==="null")return raw;
  return integerToken(raw).toString();
}
function identity(node:Node,extra:readonly string[]=[]){closed(node.value,["device","inode",...extra]);integer(node,"device");integer(node,"inode",1n);}
function guardian(node:Node,run:string,complete=false){
  closed(node.value,[...GUARDIAN,...(complete?["status"]:[])]);const scope="m08guard-"+run+".scope";
  check(node.value.scope===scope&&node.value.group==="/system.slice/"+scope&&node.value.identity_transport==="PIDFDs/ah"&&node.value.scope_removed===true);
  check(integer(node,"memory_limit_bytes")===134217728n&&integer(node,"tasks_max")===16n&&integer(node,"wall_limit_seconds")===150n);
  check(typeof node.value.manager_job==="string"&&/^\/org\/freedesktop\/systemd1\/job\/[0-9]{1,20}$/.test(node.value.manager_job));
  if(complete)check(node.value.status==="complete");
}

async function verifyPair(outer:Node,job:WaveformJob,ownerId:string):Promise<boolean>{
  const hasExecution=Object.hasOwn(outer.value,"linux_execution"),hasInstallation=Object.hasOwn(outer.value,"linux_installation");
  check(hasExecution===hasInstallation);if(!hasExecution)return false;
  const receipt=child(outer,"linux_execution"),installation=child(outer,"linux_installation");
  check(encoder.encode(receipt.raw).length<=65536);
  // Independently reapply the native subtree's tighter finite graph bound.
  strictVelocityJson(encoder.encode(receipt.raw),4096,65536,24);
  closed(receipt.value,EXECUTION);closed(installation.value,INSTALLATION);
  const bound=child(receipt,"installation");closed(bound.value,INSTALLATION);
  for(const key of INSTALLATION.filter(k=>k!=="source_hashes"))same(hash(bound.value[key]),hash(installation.value[key]),"waveform installation binding");
  const sourceMap=closed(bound.value.source_hashes,WAVEFORM_LINUX_SOURCES),installedMap=closed(installation.value.source_hashes,WAVEFORM_LINUX_SOURCES);
  Object.values(sourceMap).forEach(hash);Object.values(installedMap).forEach(hash);same(sourceMap,installedMap,"waveform full source map");
  same(await digest(encoder.encode(nativeCanonical(token(bound,"source_hashes")))),job.request.implementation_sha256,"waveform admitted implementation");
  const expected={id:job.job_id,owner_id:ownerId,project_id:job.project_id,dataset_id:job.dataset_id,dataset_sha256:job.dataset_sha256,
    request_sha256:job.request_sha256,method_id:job.method_id,implementation_sha256:job.request.implementation_sha256,
    scientific_request_sha256:job.request.scientific_request_sha256};
  closed(receipt.value.job,JOB);same(receipt.value.job,expected,"waveform admitted job");
  for(const key of ["id","owner_id","project_id","dataset_id"] as const){uuid(expected[key]);check(expected[key]===expected[key].toLowerCase());}
  for(const key of ["dataset_sha256","request_sha256","implementation_sha256","scientific_request_sha256"] as const)hash(expected[key]);
  same(receipt.value.schema,"geophysics.waveform-linux-execution/v1","waveform terminal schema");
  parseWaveformSources(receipt.value.sources);same(receipt.value.sources,job.request.waveform_sources,"waveform admitted original pair");
  same(receipt.value.sources,outer.value.sources,"waveform result original pair");
  identity(child(receipt,"stage"));const root=child(receipt,"root_custody");identity(root,["plan_sha256"]);hash(root.value.plan_sha256);
  const life=child(receipt,"lifecycle");closed(life.value,LIFE);check(life.value.extinction_proved===true);
  const quiescent=integer(life,"science_quiescent_ns",1n),run=life.value.run_id;
  check(typeof run==="string"&&/^[a-f0-9]{32}$/.test(run));hash(life.value.admission_sha256);
  const caller=closed(life.value.caller,["reason","started_ns"]);check(caller.reason===null&&caller.started_ns===null);
  const units=closed(life.value.units,["service","accounting","guardian"]);
  same(units,{service:"m08-"+run+".service",accounting:"m08"+run+".slice",guardian:"m08guard-"+run+".scope"},"waveform exact native units");
  const final=child(life,"final_counters");closed(final.value,COUNTERS);for(const key of COUNTERS)integer(final,key,0n,I63);
  check(integer(final,"active_tasks")===0n&&integer(final,"user_cpu_ns")<=integer(final,"cpu_ns")&&integer(final,"system_cpu_ns")<=integer(final,"cpu_ns"));
  const outerGuardian=child(life,"guardian");guardian(outerGuardian,run);
  const outcome=closed(receipt.value.outcome,["status","reason","run_id","receipt_sha256","release_sha256","runtime_authorized"]);
  check(outcome.reason==="measured"&&outcome.runtime_authorized===false&&["computed","qc_only"].includes(String(outcome.status))&&outcome.run_id===run);
  const native=child(receipt,"native");closed(native.value,["eligibility","release"]);
  const measured=child(native,"eligibility"),release=child(native,"release");closed(measured.value,ELIGIBILITY);closed(release.value,RELEASE);
  check(measured.value.schema==="caos.m08-linux-resources.v2"&&measured.value.status==="measured"&&measured.value.run_id===run&&
    measured.value.memory_kind==="linux_cgroup_charge"&&measured.value.runtime_authorized===false&&measured.value.method_accepted===false&&measured.value.host_admitted===false);
  check(integer(measured,"budget_ns")===B&&integer(measured,"stop_ns")===S);
  const cpu=integer(measured,"cpu_ns",0n,B);check(cpu<S&&integer(measured,"user_cpu_ns",0n,B)<=cpu&&integer(measured,"system_cpu_ns",0n,B)<=cpu);
  integer(measured,"max_sample_gap_ns",0n,GAP);integer(measured,"peak_charge_bytes",0n,MEMORY);
  check(integer(measured,"active_processes")===0n&&integer(measured,"sample_count",2n)>=2n);
  const stable=integer(measured,"stable_final_ns"),drained=integer(measured,"drained_ns");check(stable>=drained+GAP&&quiescent>=stable);
  same(hash(measured.value.admission_sha256),life.value.admission_sha256,"waveform admission receipt");
  for(const key of ["cpu_ns","user_cpu_ns","system_cpu_ns","peak_charge_bytes"])check(integer(measured,key)===integer(final,key));
  const innerGuardian=child(measured,"guardian");guardian(innerGuardian,run,true);same(innerGuardian.value,{...outerGuardian.value,status:"complete"},"waveform guardian binding");
  const measuredSha=await digest(encoder.encode(nativeCanonical(measured.raw))),releaseSha=await digest(encoder.encode(nativeCanonical(release.raw)));
  same(release.value,{schema:"caos.m08-linux-release.v1",run_id:run,receipt_sha256:measuredSha,
    all_native_owned_handles_closed:true,scope_removed:true,runtime_authorized:false},"waveform native release");
  same(hash(outcome.receipt_sha256),measuredSha,"waveform terminal receipt SHA");same(hash(outcome.release_sha256),releaseSha,"waveform terminal release SHA");
  same(hash(receipt.value.calculation_sha256),outer.value.calculation_sha256,"waveform terminal calculation");same(outcome.status,outer.value.scientific_status,"waveform scientific status");
  check(nativeCanonical(token(receipt,"members"))===nativeCanonical(token(outer,"members")));
  const members=receipt.value.members;check(Array.isArray(members)&&members.length>=3&&members.length<=55);
  const names:string[]=[];let total=0;
  for(const member of members){const m=closed(member,["name","bytes","sha256"]);names.push(waveformMember(m.name));hash(m.sha256);
    check(typeof m.bytes==="number"&&Number.isSafeInteger(m.bytes)&&m.bytes>0&&m.bytes<=33554432);total+=m.bytes;}
  check(total<=33554432&&new Set(names).size===names.length&&names.every((name,i)=>name===[...names].sort()[i])&&
    ["calculation.json","manifest.json","receipt.json"].every(name=>names.includes(name)));
  same(outer.value.resources,{schema:"geophysics.waveform-resources/v1",cpu_ns:Number(cpu),max_sample_gap_ns:Number(integer(measured,"max_sample_gap_ns")),
    peak_memory_bytes:Number(integer(measured,"peak_charge_bytes")),memory_kind:"linux_cgroup_charge",native_receipt_sha256:measuredSha,
    release_sha256:releaseSha,runtime_authorized:false,host_admitted:false},"waveform portable charge projection");
  // Entire operational subtree contains only exact bounded integer tokens.
  nativeCanonical(receipt.raw);nativeCanonical(installation.raw);
  return true;
}

/** Read-only token query: no public API can register an unverified envelope. */
export function isVerifiedWaveformEnvelope(value:object){return verified.has(value);}
/** Exact original transport bytes, including pair; never stringify rounded ints. */
export function waveformResultBytes(result:WaveformResult){return custody.get(result)?.slice()??null;}
function freeze(value:unknown){if(value&&typeof value==="object"){Object.values(value).forEach(freeze);Object.freeze(value);}}
export async function readProtectedWaveform(bytes:Uint8Array,job:WaveformJob,dataset:WaveformDataset):Promise<WaveformResult>{
  check(job.state==="succeeded"&&bytes.length>0&&bytes.length<=WAVEFORM_RESULT_BYTE_CAP);
  // Clone BEFORE await: caller mutation cannot replace the independently hashed bytes.
  const retained=bytes.slice();same(await digest(retained),hash(job.result_sha256),"waveform retained result SHA");
  const payload=object(strictVelocityJson(retained,2200000,WAVEFORM_RESULT_BYTE_CAP,24),"waveform protected result");
  const raw=new TextDecoder("utf-8",{fatal:true,ignoreBOM:true}).decode(retained),paired=await verifyPair({raw,value:payload},job,dataset.owner_id);
  const scientific={...payload};delete scientific.linux_execution;delete scientific.linux_installation;
  if(paired)verified.add(scientific);
  const result=parseWaveformResult(scientific);bindWaveformResult(result,job,dataset);
  custody.set(result,retained);freeze(result);return result;
}
