/** Optional operational pair only; byte custody is not scientific/host admission. */
import { profileJsonMembers } from "./profile-local-contracts";
import { processingObject as object, same, type ProfileProcessingJob } from "./processing-contracts";

export const PROFILE_LINUX_SOURCES = ["app/profile_linux_exec.py","scripts/profile_linux_supervisor.py","scripts/profile_linux_child.py",
  "scripts/process_profile_job.py","scripts/process_supplied_profile.py","data-pipeline/ert.py","data-pipeline/traveltime.py",
  "data-pipeline/profile_mesh.py","data-pipeline/supplied_profiles.py","data-pipeline/sources.py","data/source-ledger.json"] as const;
const INSTALLATION = "configuration_sha256 python_sha256 environment_sha256 invocation_sha256 source_hashes".split(" ");
const EXECUTION = "schema job_id request_sha256 dataset_sha256 raw_sha256 environment_sha256 unit terminal stop_reason failure launch_attempted extinction guardian_status guardian_scope invocation_sha256 source_hashes configuration_sha256 python_sha256 mounted_input_identities retained_stage_identity wall_seconds resources retained originals_reverified held_inputs_state cpu_accounting_admitted host_admission".split(" ");
const RESOURCES = "sampled_root_rss_peak_bytes rss_samples kernel_memcg_peak_bytes sampled_unit_rss_peak_bytes unit_rss_samples memcg_reads memory_events cgroup_events exact_group_removed hard_writable_scratch_bytes held_input_bytes".split(" ");
const LIMIT = (1n<<63n)-1n, encoder = new TextEncoder();
function check(ok:unknown):asserts ok {if(!ok)throw new Error("Protected profile Linux pair rejected");}
function closed(value:unknown,keys:readonly string[]){const record=object(value,"Linux operational record");check(Object.keys(record).length===keys.length&&keys.every(k=>Object.hasOwn(record,k)));return record;}
function hash(value:unknown){check(typeof value==="string"&&/^[a-f0-9]{64}$/.test(value));return value;}
type Node={raw:string;value:Record<string,unknown>};
function child(parent:Node,key:string):Node {
  const field=profileJsonMembers(parent.raw).get(key);check(field);
  return {raw:parent.raw.slice(field.valueStart,field.valueEnd),value:object(parent.value[key],"Linux nested record")};
}
/** Python int, not JS-rounded integers or JSON float/exponent/bool coercion. */
function integer(node:Node,key:string,low=0n,high=LIMIT){
  const field=profileJsonMembers(node.raw).get(key);check(field);
  const token=node.raw.slice(field.valueStart,field.valueEnd);
  check(token.length<=20&&/^-?(?:0|[1-9][0-9]*)$/.test(token));
  const value=BigInt(token);check(value>=low&&value<=high);return value;
}
function admittedInteger(value:number){check(Number.isSafeInteger(value)&&value>=0);return BigInt(value);}
async function digest(bytes:Uint8Array){return [...new Uint8Array(await crypto.subtle.digest("SHA-256",bytes as Uint8Array<ArrayBuffer>))].map(v=>v.toString(16).padStart(2,"0")).join("");}

/** Preserve every scientific token/order/byte; exclude only the TWO root members. */
export function profileProducerBytes(raw:string):Uint8Array {
  const fields=[...profileJsonMembers(raw)],first=fields[0]?.[1],last=fields.at(-1)?.[1];check(first&&last);
  const retained=fields.filter(([key])=>key!=="linux_execution"&&key!=="linux_installation");check(retained.length>0);
  return encoder.encode(raw.slice(0,first.start)+retained.map(([,field])=>raw.slice(field.start,field.end)).join(",")+raw.slice(last.end));
}

/** Caller has already run bounded duplicate/depth/UTF8 JSON preflight on raw. */
export async function verifyProfileLinuxPair(raw:string,payload:Record<string,unknown>,job:ProfileProcessingJob):Promise<void>{
  const execution=Object.hasOwn(payload,"linux_execution"),installation=Object.hasOwn(payload,"linux_installation");
  check(execution===installation);if(!execution)return; // Windows: no Linux claim.
  const outer:Node={raw,value:payload},receipt=child(outer,"linux_execution"),binding=child(outer,"linux_installation");
  closed(receipt.value,EXECUTION);closed(binding.value,INSTALLATION);
  check(encoder.encode(receipt.raw).byteLength<=65536);
  for(const key of INSTALLATION.filter(k=>k!=="source_hashes"))same(hash(receipt.value[key]),hash(binding.value[key]),"frozen Linux installation");
  const sources=closed(receipt.value.source_hashes,PROFILE_LINUX_SOURCES),installed=closed(binding.value.source_hashes,PROFILE_LINUX_SOURCES);
  Object.values(sources).forEach(hash);Object.values(installed).forEach(hash);same(sources,installed,"Linux installation sources");
  same(sources["scripts/process_profile_job.py"],job.request.profile_child_sha256,"Linux admitted child");
  for(const [name,value] of Object.entries(job.request.profile_code_hashes))same(sources["data-pipeline/"+name],value,"Linux admitted engine source");
  same(receipt.value.schema,"geophysics.profile-linux-execution/v1","Linux receipt schema");
  for(const [key,expected] of [["job_id",job.job_id],["request_sha256",job.request_sha256],
    ["dataset_sha256",job.dataset_sha256],["raw_sha256",job.request.raw_sha256]])same(receipt.value[key],expected,"Linux admitted job");
  for(const key of ["request_sha256","dataset_sha256","raw_sha256"])hash(receipt.value[key]);
  const unit="geophysics-profile-"+job.job_id+".service",scope="geophysics-profile-guardian-"+job.job_id+".scope";
  same(receipt.value.unit,unit,"Linux exact unit");
  check(receipt.value.failure===null&&receipt.value.stop_reason===null&&receipt.value.launch_attempted===true&&
    receipt.value.extinction==="proved"&&receipt.value.guardian_status==="complete"&&receipt.value.originals_reverified===true&&
    receipt.value.held_inputs_state==="declared_copies_removed"&&receipt.value.cpu_accounting_admitted===false&&receipt.value.host_admission===false);
  const terminal=closed(receipt.value.terminal,["MainPID","SubState","Result","ExecMainStatus","ControlGroup"]);
  check(terminal.MainPID==="0"&&terminal.ExecMainStatus==="0"&&terminal.Result==="success"&&
    ["dead","exited"].includes(String(terminal.SubState))&&typeof terminal.SubState==="string"&&
    (terminal.ControlGroup===""||terminal.ControlGroup==="/system.slice/"+unit));
  const guardian=child(receipt,"guardian_scope");
  closed(guardian.value,["scope","group","memory_limit_bytes","tasks_max","wall_limit_seconds","identity_transport","manager_job"]);
  check(guardian.value.scope===scope&&guardian.value.group==="/system.slice/"+scope&&guardian.value.identity_transport==="PIDFDs/ah"&&
    typeof guardian.value.manager_job==="string"&&/^\/org\/freedesktop\/systemd1\/job\/[0-9]{1,20}$/.test(guardian.value.manager_job));
  check(integer(guardian,"memory_limit_bytes")===128n*1048576n&&integer(guardian,"tasks_max")===16n);
  check(integer(guardian,"wall_limit_seconds",31n,630n)===admittedInteger(job.preflight.wall_limit_seconds)+30n);
  const stage=child(receipt,"retained_stage_identity");closed(stage.value,["device","inode"]);
  integer(stage,"device");integer(stage,"inode");
  const mounted=child(receipt,"mounted_input_identities");closed(mounted.value,["original","dataset.json"]);
  let held=0n;
  for(const name of ["original","dataset.json"]){
    const member=child(mounted,name);closed(member.value,["device","inode","bytes","sha256"]);
    integer(member,"device");integer(member,"inode",1n);
    const bytes=integer(member,"bytes",1n,name==="original"?1000000n:2n*1048576n);held+=bytes;
    same(member.value.sha256,name==="original"?receipt.value.raw_sha256:receipt.value.dataset_sha256,"Linux mounted source hash");
    if(name==="original")check(bytes===integer(outer,"raw_bytes",1n));
  }
  const wall=receipt.value.wall_seconds;
  check(typeof wall==="number"&&Number.isFinite(wall)&&wall>=0&&wall<=job.preflight.wall_limit_seconds+40);
  const resources=child(receipt,"resources");closed(resources.value,RESOURCES);
  for(const key of ["sampled_root_rss_peak_bytes","sampled_unit_rss_peak_bytes","kernel_memcg_peak_bytes","rss_samples","unit_rss_samples","memcg_reads"])integer(resources,key,1n);
  check(integer(resources,"kernel_memcg_peak_bytes",1n)<=admittedInteger(job.preflight.memory_limit_bytes));
  check(integer(resources,"hard_writable_scratch_bytes",4096n,64n*1048576n)<=admittedInteger(job.preflight.scratch_limit_bytes));
  check(integer(resources,"held_input_bytes",1n)===held&&typeof resources.value.exact_group_removed==="boolean");
  for(const name of ["memory_events","cgroup_events"]){const value=resources.value[name];check(value===null||typeof value==="string"&&[...value].length<=4096);}
  check(resources.value.exact_group_removed===true||typeof resources.value.cgroup_events==="string"&&
    resources.value.cgroup_events.split(/\r\n|[\n\r\v\f\x1c-\x1e\x85\u2028\u2029]/).includes("populated 0"));
  const retained=child(receipt,"retained");closed(retained.value,["result.json","stderr.txt"]);
  for(const name of ["result.json","stderr.txt"]){
    const member=child(retained,name);closed(member.value,["bytes","sha256"]);
    integer(member,"bytes",name==="result.json"?1n:0n,32n*1048576n);hash(member.value.sha256);
  }
  const producer=profileProducerBytes(raw),result=child(retained,"result.json");
  check(integer(result,"bytes",1n)===BigInt(producer.byteLength));
  same(await digest(producer),result.value.sha256,"exact retained producer lexical bytes");
}
