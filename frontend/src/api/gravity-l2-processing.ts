import { unzipSync } from "fflate";
import { ApiClient } from "./client";
import { ProcessingApi } from "./processing";
import { GRAVITY_L2_METHOD, bindGravityL2Result, parseGravityL2Job, parseGravityL2Result, validateGravityL2Parameters, type GravityL2Job, type GravityL2Parameters } from "./gravity-l2-contracts";
import { parseGravityDataset, processingId, processingObject, processingText, same, sha, type DatasetReceipt, type GravityDataset } from "./processing-contracts";

const canonical=(v:unknown):string=>Array.isArray(v)?`[${v.map(canonical).join(",")}]`:v&&typeof v==="object"?`{${Object.entries(v as Record<string,unknown>).sort(([a],[b])=>a<b?-1:a>b?1:0).map(([k,x])=>`${JSON.stringify(k)}:${canonical(x)}`).join(",")}}`:JSON.stringify(v);
export class GravityL2ProcessingApi extends ProcessingApi {
 constructor(private readonly client:ApiClient){super(client);}
 private root(project:string){return `/api/projects/${processingId(project)}`;}
 private path(project:string,job:string){return `${this.root(project)}/jobs/${processingId(job)}`;}
 async submitGravityL2(project:string,receipt:DatasetReceipt,parameters:GravityL2Parameters,signal?:AbortSignal){
  same(receipt.project_id,project,"project");validateGravityL2Parameters(parameters);
  const token=await this.client.requestJson("/api/auth/csrf",v=>processingObject(v,"csrf"),{signal});
  const job=await this.client.requestJson(`${this.root(project)}/jobs`,parseGravityL2Job,{method:"POST",csrfToken:processingText(token.csrf_token,"CSRF"),body:{dataset_id:receipt.dataset_id,method_id:GRAVITY_L2_METHOD,parameters},signal});
  same(job.project_id,project,"submitted project");same(job.dataset_id,receipt.dataset_id,"submitted dataset");same(job.dataset_sha256,receipt.sha256,"submitted dataset hash");same(job.request.parameters,parameters,"submitted M02 parameters");same(job.request.raw_asset_id,receipt.raw_asset_id,"source original");same(job.request.raw_sha256,receipt.raw_sha256,"source hash");return job;
 }
 async gravityL2Result(project:string,job:GravityL2Job,dataset:GravityDataset,receipt:DatasetReceipt,signal?:AbortSignal){
  same(job.project_id,project,"job project");same(dataset.project_id,project,"dataset project");same(job.dataset_sha256,receipt.sha256,"dataset SHA");if(job.state!=="succeeded")throw new Error("A non-success M02 job has no result");
  const raw=await this.client.requestJsonBytes(`${this.path(project,job.job_id)}/result`,128*1048576,signal);if(await sha(raw)!==job.result_sha256)throw new Error("M02 result bytes differ from the recorded job SHA-256");let payload:unknown;try{payload=JSON.parse(new TextDecoder("utf-8",{fatal:true}).decode(raw));}catch{throw new Error("M02 result is not valid UTF-8 JSON");}const result=await parseGravityL2Result(payload);bindGravityL2Result(result,job,dataset,receipt);return result;
 }
 async gravityL2Export(project:string,job:GravityL2Job,dataset:GravityDataset,receipt:DatasetReceipt,signal?:AbortSignal){
  same(job.project_id,project,"job project");same(job.dataset_sha256,receipt.sha256,"dataset SHA");if(job.state!=="succeeded")throw new Error("A non-success M02 job has no export");
  const blob=await this.client.requestBlob(`${this.path(project,job.job_id)}/export`,{signal});if(blob.size<22||blob.size>130*1048576)throw new Error("M02 ZIP is outside the permitted size");
  const names=new Set<string>();const files=unzipSync(new Uint8Array(await blob.arrayBuffer()),{filter:f=>{if(!["manifest.json","dataset.json","result.json"].includes(f.name)||names.has(f.name)||f.compression!==0||f.size!==f.originalSize||f.originalSize>64*1048576)throw new Error("Unexpected M02 export member");names.add(f.name);return true;}});if(names.size!==3)throw new Error("M02 ZIP must contain exactly three members");
  const decode=(name:string)=>JSON.parse(new TextDecoder("utf-8",{fatal:true}).decode(files[name])) as unknown;const manifest=processingObject(decode("manifest.json"),"manifest"),savedData=parseGravityDataset(decode("dataset.json")),savedResult=await parseGravityL2Result(decode("result.json"));same(savedData,dataset,"exported dataset");bindGravityL2Result(savedResult,job,dataset,receipt);
  const members=processingObject(manifest.members,"members");if(Object.keys(members).sort().join(",")!=="dataset.json,result.json")throw new Error("M02 bundle member set mismatch");for(const [name,value] of [["dataset.json",files["dataset.json"]],["result.json",files["result.json"]]] as const){const row=processingObject(members[name],"member");if(Object.keys(row).sort().join(",")!=="bytes,sha256")throw new Error("M02 bundle member schema mismatch");same(row.sha256,await sha(value),`${name} digest`);same(row.bytes,value.byteLength,`${name} size`);}same(processingObject(members["dataset.json"],"dataset member").sha256,receipt.sha256,"export dataset receipt");same(processingObject(members["result.json"],"result member").sha256,job.result_sha256,"export result receipt");
  const expected={schema:"geophysics.processing-bundle/v1",dataset_id:dataset.dataset_id,job_id:job.job_id,method_id:GRAVITY_L2_METHOD,parameters:job.request.parameters,rights_decision:dataset.rights_decision,rights_statement:dataset.rights_statement,axes:dataset.axis_order,dimensions:dataset.dimensions,units:{model:"kg/m3",observation:"mGal",coordinates:"m"},provenance:{raw_sha256:dataset.parent_raw_sha256,dataset_sha256:receipt.sha256,request_sha256:job.request_sha256,engine_sha256:savedResult.engine_sha256},members,raw_bytes_included:false};same(manifest,expected,"M02 export manifest");
  return blob;
 }
}
