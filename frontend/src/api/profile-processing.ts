/** Protected profile API: owner/request receipts and exact producer lexical bytes. */
import { unzipSync } from "fflate";
import { ApiClient } from "./client";
import { ProcessingApi } from "./processing";
import { profileJsonMembers, readProfileFiles, type ProfileAdmission } from "./profile-local-contracts";
import { strictVelocityJson } from "./velocity-local-contracts";
import { M07_METHOD,M09_METHOD,isProfileJob,isProfileReceipt,parseProjectDatasetReceipt,parseProjectProcessingJob,
  processingId as id,processingObject as obj,processingText as text,same,
  type ProfileDatasetReceipt,type ProfileProcessingJob } from "./processing-contracts";

const digest = async (bytes:Uint8Array)=>[...new Uint8Array(await crypto.subtle.digest("SHA-256",bytes as Uint8Array<ArrayBuffer>))].map(v=>v.toString(16).padStart(2,"0")).join("");
function check(ok:unknown):asserts ok {if(!ok)throw new Error("Protected profile response rejected");}
export async function readProtectedProfile(bytes:Uint8Array,job:ProfileProcessingJob,receipt:ProfileDatasetReceipt):Promise<ProfileAdmission>{
  check(job.state==="succeeded" && bytes.length<=8*1048576 && await digest(bytes)===job.result_sha256);
  const result=obj(strictVelocityJson(bytes,2200000,8*1048576,20),"profile job result");
  same(result.schema,"geophysics.processing-result/v1","profile schema");
  for(const key of ["job_id","dataset_id","dataset_sha256","method_id","request_sha256"] as const) same(result[key],job[key],`profile ${key}`);
  same(job.dataset_sha256,receipt.sha256,"profile dataset receipt");same(job.project_id,receipt.project_id,"profile project");
  same(result.raw_asset_id,receipt.raw_asset_id,"profile original");same(result.raw_sha256,receipt.raw_sha256,"profile original hash");
  same(result.parameters,{},"frozen profile settings");same(result.execution_lane,"protected-worker","profile lane");same(result.truth,null,"field truth");
  same(result.child_code_sha256,job.request.profile_child_sha256,"admitted child code");
  const profile=obj(result.profile,"portable profile"),engine=obj(profile.engine_report,"profile report");
  same(profile.code_hashes,job.request.profile_code_hashes,"admitted profile modules");
  same(result.numerical_verdict,engine.inverse_status,"separate scientific verdict");
  same(obj(profile.original,"profile original").sha256,receipt.raw_sha256,"portable original hash");
  const raw=new TextDecoder("utf-8",{fatal:true}).decode(bytes),member=profileJsonMembers(raw).get("profile");check(member);
  const environment=profileJsonMembers(raw).get("environment");check(environment);
  same(await digest(new TextEncoder().encode(raw.slice(environment.valueStart,environment.valueEnd))),result.environment_sha256,"producer environment hash");
  same(result.raw_bytes,originalBytes(profile),"original byte count");
  const portable=new TextEncoder().encode(raw.slice(member.valueStart,member.valueEnd));
  const settings=profileJsonMembers(new TextDecoder().decode(portable)).get("numerical_settings");check(settings);
  const original=obj(profile.original,"profile original");
  const manifest={schema:"geophysics.supplied-profile-manifest/v1",result:{name:"result.json",bytes:portable.length,sha256:await digest(portable)},
    method:profile.method,source_sha256:original.sha256,content_sha256:profile.content_sha256,
    configuration_sha256:await digest(new TextEncoder().encode(new TextDecoder().decode(portable).slice(settings.valueStart,settings.valueEnd)))};
  return readProfileFiles(new Blob([portable as Uint8Array<ArrayBuffer>]),new Blob([JSON.stringify(manifest)]));
}
const originalBytes=(profile:Record<string,unknown>)=>obj(profile.original,"profile original").bytes;

export async function verifyProfileBundle(blob:Blob,job:ProfileProcessingJob,receipt:ProfileDatasetReceipt){
  check(blob.size>=22&&blob.size<=17*1048576);const names=new Set<string>();
  const files=unzipSync(new Uint8Array(await blob.arrayBuffer()),{filter:file=>{
    check(["manifest.json","dataset.json","result.json"].includes(file.name)&&!names.has(file.name)&&file.compression===0&&file.size===file.originalSize&&file.originalSize<=(file.name==="manifest.json"?262144:8*1048576));names.add(file.name);return true;}});
  check(names.size===3);
  const decode=(name:string)=>strictVelocityJson(files[name],2200000,name==="manifest.json"?262144:8*1048576,20);
  const manifest=obj(decode("manifest.json"),"profile export manifest"),dataset=obj(decode("dataset.json"),"profile export dataset");
  const datasetSha=await digest(files["dataset.json"]),resultSha=await digest(files["result.json"]);
  same(datasetSha,receipt.sha256,"export dataset hash");same(resultSha,job.result_sha256,"export result hash");
  same(manifest.members,{"dataset.json":{sha256:datasetSha,bytes:files["dataset.json"].length},"result.json":{sha256:resultSha,bytes:files["result.json"].length}},"export member hashes");
  same(manifest.raw_bytes_included,false,"no original export");same(manifest.schema,"geophysics.processing-bundle/v1","export schema");
  same(manifest.dataset_id,receipt.dataset_id,"export dataset");same(manifest.job_id,job.job_id,"export job");
  id(dataset.owner_id);same(dataset.project_id,receipt.project_id,"export project");
  const admitted=await readProtectedProfile(files["result.json"],job,receipt);
  same(dataset.geometry,admitted.result.geometry,"export native geometry");same(dataset.profile_metadata,admitted.result.metadata,"export declaration");
  same(dataset.dataset_id,receipt.dataset_id,"dataset identity");same(dataset.raw_asset_id,receipt.raw_asset_id,"dataset raw identity");
  same(dataset.parent_raw_sha256,receipt.raw_sha256,"dataset raw hash");same(dataset.modality,receipt.modality,"dataset modality");
  same(dataset.method_id,job.method_id,"dataset method");same(dataset.parser_version,receipt.parser_version,"dataset parser");same(dataset.truth,null,"dataset truth");
  same(obj(dataset.dimensions,"profile dimensions").measurement,receipt.row_count,"measurement count");
  for(const model of admitted.models) same(model.observed,dataset.observed,"original observations");
  const expectedManifest={schema:"geophysics.processing-bundle/v1",dataset_id:receipt.dataset_id,job_id:job.job_id,method_id:job.method_id,parameters:{},
    rights:obj(obj(dataset.profile_metadata,"profile metadata").source,"profile source").rights,axes:["measurement"],dimensions:dataset.dimensions,
    units:{position:"m",observation:receipt.modality==="ert_profile"?"ohm":"s"},
    provenance:{raw_sha256:receipt.raw_sha256,dataset_sha256:receipt.sha256,request_sha256:job.request_sha256,child_code_sha256:job.request.profile_child_sha256,profile_code_hashes:job.request.profile_code_hashes},
    members:manifest.members,raw_bytes_included:false};
  same(manifest,expectedManifest,"complete export manifest");
  return admitted;
}

export class ProfileProcessingApi extends ProcessingApi{
  constructor(private readonly client:ApiClient){super(client);}
  private root(project:string){return `/api/projects/${id(project)}`;}
  private async token(signal?:AbortSignal){const value=await this.client.requestJson("/api/auth/csrf",v=>obj(v,"CSRF"),{signal});return text(value.csrf_token,"CSRF");}
  async validateProfile(project:string,asset:string,metadata:unknown,signal?:AbortSignal){
    const receipt=await this.client.requestJson(`${this.root(project)}/datasets`,parseProjectDatasetReceipt,{method:"POST",csrfToken:await this.token(signal),body:{asset_id:id(asset),profile_metadata:metadata},signal});
    check(isProfileReceipt(receipt));same(receipt.project_id,project,"profile project");same(receipt.raw_asset_id,asset,"profile asset");return receipt;
  }
  async submitProfile(project:string,receipt:ProfileDatasetReceipt,signal?:AbortSignal){
    same(receipt.project_id,project,"submitted project");const method=receipt.modality==="ert_profile"?M07_METHOD:M09_METHOD;
    const job=await this.client.requestJson(`${this.root(project)}/jobs`,parseProjectProcessingJob,{method:"POST",csrfToken:await this.token(signal),body:{dataset_id:receipt.dataset_id,method_id:method,parameters:{}},signal});
    check(isProfileJob(job));same(job.dataset_id,receipt.dataset_id,"submitted dataset");same(job.dataset_sha256,receipt.sha256,"submitted hash");same(job.request.raw_sha256,receipt.raw_sha256,"submitted original");return job;
  }
  async profileResult(project:string,job:ProfileProcessingJob,receipt:ProfileDatasetReceipt,signal?:AbortSignal){
    same(job.project_id,project,"requested project");same(receipt.project_id,project,"requested receipt");
    return readProtectedProfile(await this.client.requestJsonBytes(`${this.root(project)}/jobs/${id(job.job_id)}/result`,8*1048576,signal),job,receipt);
  }
  async profileExport(project:string,job:ProfileProcessingJob,receipt:ProfileDatasetReceipt,signal?:AbortSignal){
    same(job.project_id,project,"export project");const blob=await this.client.requestBlob(`${this.root(project)}/jobs/${id(job.job_id)}/export`,{signal});await verifyProfileBundle(blob,job,receipt);return blob;
  }
}
