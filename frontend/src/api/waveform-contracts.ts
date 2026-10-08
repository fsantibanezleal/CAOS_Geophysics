import { unzipSync } from "fflate";
import { processingObject as obj, processingId as id, processingText as text, keys, hash, integer, same, type DatasetReceipt, type ProcessingJob } from "./processing-contracts";

export const WAVEFORM_METHOD = "seismic.waveform-qc-classical/v1" as const;
export const isWaveformReceipt = (receipt:{modality:string}):receipt is WaveformReceipt => receipt.modality==="waveform_counts_response";
export const isWaveformJob = (job:{method_id:string}):job is WaveformJob => job.method_id===WAVEFORM_METHOD;
export type WaveformReceipt = Omit<DatasetReceipt, "modality" | "parser_version" | "qc_verdict"> & {
  modality: "waveform_counts_response"; parser_version: string; qc_verdict: "structural_index_not_physical_qc";
};
export type WaveformSources = Record<"miniseed" | "stationxml", {asset_id:string; source_id:string; source_version:number; raw_sha256:string; raw_bytes:number; rights_decision:string; private_storage_permission:"attested"}>;
export type WaveformJob = Omit<ProcessingJob,"method_id"|"request"> & {
  method_id:typeof WAVEFORM_METHOD;
  request:Omit<ProcessingJob["request"],"method_id"|"parameters"> & {
    method_id:typeof WAVEFORM_METHOD; parameters:{scientific_request_sha256:string};
    waveform_sources:WaveformSources; scientific_request:Record<string,unknown>; scientific_request_sha256:string; implementation_sha256:string;
  };
};
export interface WaveformDataset {
  schema:"geophysics.waveform-dataset/v1"; dataset_id:string; project_id:string; owner_id:string;
  raw_asset_id:string; parent_raw_sha256:string; version:1; parser_version:string;
  modality:"waveform_counts_response"; dimensions:{channel:number; sample:number; record:number};
  sources:WaveformSources; request:Record<string,unknown>; scientific_request_sha256:string;
  qc_verdict:"structural_index_not_physical_qc";
}
export interface ArrayDescriptor {channel_index:number; name:string; dtype:"<i4"|"<f8"|"|b1"; shape:number[]; unit:string; bytes:number; sha256:string}
export interface WaveformCalculation extends Record<string,unknown> {
  status:"computed"|"qc_only"; array_descriptors:ArrayDescriptor[];
  channels:{sample_rate_hz:number; start_us:number; npts:number; native_unit:string|null}[];
  request:{submitted:Record<string,unknown>; scientific_sha256:string};
  sources:Record<string,{raw_sha256:string;raw_bytes:number}>;
  qc:{reasons:string[]; warnings:unknown[]};
  acceptance:Record<string,false>; field_truth:null; candidates:unknown[]|null;
}
export interface WaveformResult {
  schema:"geophysics.waveform-result/v1"; job_id:string; project_id:string; dataset_id:string;
  dataset_sha256:string; method_id:typeof WAVEFORM_METHOD; request_sha256:string;
  scientific_request_sha256:string; sources:WaveformSources; scientific_status:"computed"|"qc_only";
  calculation_sha256:string; calculation:WaveformCalculation;
  members:{name:string;bytes:number;sha256:string}[];
  resources:{schema:string; cpu_ns:number; max_sample_gap_ns:number; peak_memory_bytes:number; memory_kind:"windows_job_committed"; native_receipt_sha256:string; release_sha256:string; runtime_authorized:false; host_admitted:false};
}
const arrays = "counts physical_native filtered_native edge_valid time_taper response_frequency_hz response_real response_imag inverse_real inverse_imag prefilter_weight characteristic psd_frequency_hz counts_psd physical_psd filtered_psd filter_sos".split(" ");
export function waveformMember(name:unknown):string {
  const value=text(name,"waveform member");
  if (!["calculation.json","evaluation.json","receipt.json","manifest.json"].includes(value) && !new RegExp(`^c0[0-2]-(?:${arrays.join("|")})\\.bin$`).test(value)) throw new Error("Invalid waveform member");
  return value;
}
export function parseWaveformSources(value:unknown):WaveformSources {
  const source=obj(value,"waveform sources");keys(source,["miniseed","stationxml"],"source pair");
  for(const role of ["miniseed","stationxml"]){const row=obj(source[role],role);keys(row,["asset_id","source_id","source_version","raw_sha256","raw_bytes","rights_decision","private_storage_permission"],role);id(row.asset_id);id(row.source_id);hash(row.raw_sha256);integer(row.raw_bytes,1,role==="miniseed"?16777216:2097152);integer(row.source_version,1);if(row.private_storage_permission!=="attested"||!["mirror","provider-link-only","derivative-only"].includes(String(row.rights_decision)))throw new Error("Waveform source rights");}
  return value as WaveformSources;
}
export function parseWaveformDataset(value:unknown):WaveformDataset {
  const data=obj(value,"waveform dataset");keys(data,"schema dataset_id version owner_id project_id raw_asset_id parent_raw_sha256 parser_version modality dimensions sources request scientific_request_sha256 qc_verdict".split(" "),"waveform dataset");
  for(const key of ["dataset_id","owner_id","project_id","raw_asset_id"])id(data[key]);hash(data.parent_raw_sha256);hash(data.scientific_request_sha256);
  if(data.schema!=="geophysics.waveform-dataset/v1"||data.version!==1||data.modality!=="waveform_counts_response"||data.qc_verdict!=="structural_index_not_physical_qc"||data.parser_version!==`m08-counts-response/v1/${data.scientific_request_sha256}`)throw new Error("Waveform dataset schema");
  const dimensions=obj(data.dimensions,"dimensions");keys(dimensions,["channel","sample","record"],"dimensions");integer(dimensions.channel,1,3);integer(dimensions.sample,1,180000);integer(dimensions.record,1,4096);
  const sources=parseWaveformSources(data.sources);same(sources.miniseed.asset_id,data.raw_asset_id,"original asset");same(sources.miniseed.raw_sha256,data.parent_raw_sha256,"original digest");obj(data.request,"scientific request");
  return value as WaveformDataset;
}
export function parseWaveformResult(value:unknown):WaveformResult {
  const data=obj(value,"waveform result");keys(data,"schema job_id project_id dataset_id dataset_sha256 method_id request_sha256 scientific_request_sha256 sources scientific_status calculation_sha256 calculation members resources".split(" "),"waveform result");
  for(const key of ["job_id","project_id","dataset_id"])id(data[key]);for(const key of ["dataset_sha256","request_sha256","scientific_request_sha256","calculation_sha256"])hash(data[key]);
  if(data.schema!=="geophysics.waveform-result/v1"||data.method_id!==WAVEFORM_METHOD||!["computed","qc_only"].includes(String(data.scientific_status)))throw new Error("Waveform result method/status");parseWaveformSources(data.sources);
  const c=obj(data.calculation,"calculation");keys(c,"acceptance array_descriptors candidates channels engines field_truth method processing qc request schema sources status".split(" "),"calculation");same(c.schema,"caos.local-waveform-result.v1","calculation schema");same(c.method,WAVEFORM_METHOD,"calculation method");same(c.status,data.scientific_status,"calculation status");const acceptance=obj(c.acceptance,"acceptance");keys(acceptance,["field_eligible","host_admitted","method_accepted","provider_verified"],"acceptance");if(c.field_truth!==null||Object.values(acceptance).some(v=>v!==false))throw new Error("Waveform result cannot grant scientific authority");
  if(!Array.isArray(c.channels)||c.channels.length<1||c.channels.length>3)throw new Error("Waveform channels");for(const [i,item] of c.channels.entries()){const row=obj(item,"channel");same(row.channel_index,i,"channel index");integer(row.npts,1,60000);integer(row.start_us,0);if(typeof row.sample_rate_hz!=="number"||!Number.isFinite(row.sample_rate_hz)||row.sample_rate_hz<1||row.sample_rate_hz>200)throw new Error("Waveform sample rate");if(![null,"m","m/s","m/s2"].includes(row.native_unit as string|null))throw new Error("Waveform native unit");}
  const qc=obj(c.qc,"QC");keys(qc,["channels","reasons","warnings"],"QC");if(!Array.isArray(qc.reasons)||!Array.isArray(qc.warnings)||!Array.isArray(qc.channels)||qc.channels.length!==c.channels.length)throw new Error("Waveform QC shape");for(const reason of [...qc.reasons,...qc.warnings])text(reason,"QC reason");if(c.status==="computed"&&(qc.reasons.length||!Array.isArray(c.candidates)))throw new Error("Computed waveform QC");if(c.status==="qc_only"&&c.candidates!==null)throw new Error("QC-only candidates");
  const request=obj(c.request,"calculation request");same(request.scientific_sha256,data.scientific_request_sha256,"scientific hash");
  if(!Array.isArray(c.array_descriptors)||c.array_descriptors.length>51)throw new Error("Waveform descriptor count");
  const descriptors=new Set<string>();for(const item of c.array_descriptors){const a=obj(item,"array");keys(a,["channel_index","name","dtype","shape","unit","bytes","sha256"],"array");integer(a.channel_index,0,2);if(!arrays.includes(String(a.name)))throw new Error("Unknown waveform array");hash(a.sha256);text(a.unit,"array unit");const dtype=a.name==="counts"?"<i4":a.name==="edge_valid"?"|b1":"<f8";same(a.dtype,dtype,"array dtype");if(!Array.isArray(a.shape)||a.shape.length<1||a.shape.length>2)throw new Error("Array shape");a.shape.forEach(v=>integer(v,1,131072));integer(a.bytes,1,33554432);same(a.bytes,a.shape.reduce((n,v)=>n*Number(v),dtype==="<f8"?8:dtype==="<i4"?4:1),"array byte shape");const name=`c0${a.channel_index}-${a.name}.bin`;if(descriptors.has(name))throw new Error("Duplicate waveform descriptor");descriptors.add(name);}
  if(!Array.isArray(data.members)||data.members.length<3||data.members.length>55)throw new Error("Waveform members");let total=0;const names=new Set<string>();for(const item of data.members){const member=obj(item,"member");keys(member,["name","bytes","sha256"],"member");const name=waveformMember(member.name);if(names.has(name))throw new Error("Duplicate waveform member");names.add(name);integer(member.bytes,1,33554432);total+=member.bytes;hash(member.sha256);}if(total>33554432||!["calculation.json","receipt.json","manifest.json"].every(n=>names.has(n))||[...descriptors].some(n=>!names.has(n)))throw new Error("Waveform inventory");
  for(const item of c.array_descriptors){const a=item as unknown as ArrayDescriptor;if(a.channel_index>=c.channels.length)throw new Error("Waveform descriptor channel");const member=(data.members as WaveformResult["members"]).find(m=>m.name===`c0${a.channel_index}-${a.name}.bin`)!;same(member.bytes,a.bytes,"Waveform array member size");same(member.sha256,a.sha256,"Waveform array member hash");}
  for(const name of names)if(name.endsWith(".bin")&&!descriptors.has(name))throw new Error("Unlisted waveform array");same((data.members as WaveformResult["members"]).find(m=>m.name==="calculation.json")!.sha256,data.calculation_sha256,"Waveform calculation member hash");
  const r=obj(data.resources,"resources");keys(r,"schema cpu_ns max_sample_gap_ns peak_memory_bytes memory_kind native_receipt_sha256 release_sha256 runtime_authorized host_admitted".split(" "),"resources");if(r.schema!=="geophysics.waveform-resources/v1"||r.memory_kind!=="windows_job_committed"||r.runtime_authorized!==false||r.host_admitted!==false)throw new Error("Waveform accounting kind/authority");integer(r.cpu_ns,0,60000000000);integer(r.max_sample_gap_ns,0,100000000);integer(r.peak_memory_bytes,0,1073741824);hash(r.native_receipt_sha256);hash(r.release_sha256);
  return value as WaveformResult;
}
export function bindWaveformResult(result:WaveformResult,job:WaveformJob,dataset:WaveformDataset){for(const key of ["job_id","project_id","dataset_id","dataset_sha256","request_sha256"])same(result[key as keyof WaveformResult],job[key as keyof WaveformJob],`waveform ${key}`);same(result.sources,dataset.sources,"waveform original pair");same(result.scientific_request_sha256,dataset.scientific_request_sha256,"waveform scientific hash");same(result.calculation.request.submitted,dataset.request,"waveform submitted request");}
async function digest(raw:Uint8Array){const buffer=new Uint8Array(raw).buffer;return [...new Uint8Array(await crypto.subtle.digest("SHA-256",buffer))].map(v=>v.toString(16).padStart(2,"0")).join("");}
export async function verifyWaveformZip(blob:Blob,result:WaveformResult){if(blob.size<22||blob.size>33554432+65536)throw new Error("Waveform ZIP bound");const expected=new Map(result.members.map(m=>[m.name,m]));const seen=new Set<string>();const files=unzipSync(new Uint8Array(await blob.arrayBuffer()),{filter:file=>{const row=expected.get(file.name);if(!row||seen.has(file.name)||file.compression!==0||file.size!==row.bytes||file.originalSize!==row.bytes)throw new Error("Waveform ZIP member bounds");seen.add(file.name);return true;}});if(seen.size!==expected.size)throw new Error("Waveform ZIP incomplete");for(const [name,raw]of Object.entries(files)){if(await digest(raw)!==expected.get(name)!.sha256)throw new Error("Waveform ZIP hash");}same(JSON.parse(new TextDecoder("utf-8",{fatal:true}).decode(files["calculation.json"])),result.calculation,"waveform saved calculation");if(await digest(files["calculation.json"])!==result.calculation_sha256)throw new Error("Waveform calculation seal");return files;}
export function decodeWaveformArray(raw:Uint8Array,descriptor:ArrayDescriptor):number[]{if(raw.byteLength!==descriptor.bytes)throw new Error("Waveform array size");const view=new DataView(raw.buffer,raw.byteOffset,raw.byteLength),step=descriptor.dtype==="<f8"?8:descriptor.dtype==="<i4"?4:1;const values=[];for(let i=0;i<raw.byteLength;i+=step){const value=step===8?view.getFloat64(i,true):step===4?view.getInt32(i,true):view.getUint8(i);if(!Number.isFinite(value)||step===1&&value>1)throw new Error("Waveform array value");values.push(value);}return values;}
