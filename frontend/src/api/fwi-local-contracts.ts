/** Local byte/array admission. This module never uploads or executes an inverse. */
import { strictVelocityJson } from "./velocity-local-contracts";

export type FwiMethod = "fwi-l2" | "fwi-multiscale";
export const FWI_METHODS: FwiMethod[] = ["fwi-l2", "fwi-multiscale"];
type Descriptor = {name:string;dtype:"float32-le";shape:number[];units:string;bytes:number;sha256:string};
export type FwiState = {history:number[];history_records:Record<string,number|string|number[]>[];
  frame_history_indices:number[];frame_indices:number[];
  state_identity:{final_frame_index:number;selected_iteration:number;frame_quantity:"velocity_m_s";predictions:"final-model"};
  solver:Record<string,unknown>;metrics:Record<string,number>;numerical_verdict:"finite-budget";truth:null;model_recovery_evaluated:false};
export type FwiManifest = {
  schema:"geophysics.fwi-local-result/v1";id:string;complete:true;truth:null;execution_lane:"local-cpu"|"local-cuda";
  request_utf8:string;
  request:{schema:"geophysics.fwi-user-data/v1";id:string;source:{citation:string;rights:string;scope:string};
    acquisition:{frame:string;spacing_m:number;dt_s:number;sources_m:number[][];receivers_m:number[][];wavelet:string;amplitude_convention:string};
    observed:Omit<Descriptor,"name">;initial:Omit<Descriptor,"name">;parameters:{frequency_hz:number;beta:number;iterations_per_stage:number}};
  originals:Record<string,{bytes:number;sha256:string}>;active_receivers:boolean[];source_hashes:Record<string,string>;
  environment:Record<string,string>;resources:Record<string,number>;methods:Record<FwiMethod,FwiState>;arrays:Record<string,Descriptor>;
};
export type FwiAdmission = {manifest:FwiManifest;manifestSha256:string;arrays:Record<string,Float32Array>;manifestBytes:Uint8Array;physicsReplayed:false};
type LocalFile = Pick<File,"name"|"size"|"arrayBuffer">;
const demand:(value:unknown)=>asserts value = value=>{if(!value)throw new Error("Acoustic local generation rejected");};
const obj=(value:unknown):Record<string,unknown>=>{demand(value!==null&&typeof value==="object"&&!Array.isArray(value));return value as Record<string,unknown>;};
function closed(value:unknown,keys:string){const record=obj(value),expected=keys.split(" ");demand(Object.keys(record).length===expected.length&&expected.every(key=>Object.hasOwn(record,key)));return record;}
function num(value:unknown,lower=-Infinity,upper=Infinity){demand(typeof value==="number"&&Number.isFinite(value)&&value>=lower&&value<=upper);return value;}
function int(value:unknown,lower:number,upper:number){const result=num(value,lower,upper);demand(Number.isInteger(result));return result;}
function sha(value:unknown){demand(typeof value==="string"&&/^[a-f0-9]{64}$/.test(value));return value;}
function text(value:unknown,max=2048){demand(typeof value==="string"&&value.trim().length>0&&value.length<=max);return value;}
function same(a:unknown,b:unknown){demand(JSON.stringify(a)===JSON.stringify(b));}
function sorted(value:unknown):unknown {if(Array.isArray(value))return value.map(sorted);if(value&&typeof value==="object")return Object.fromEntries(Object.entries(value).sort(([a],[b])=>a.localeCompare(b)).map(([key,item])=>[key,sorted(item)]));return value;}
function finiteTree(value:unknown){if(typeof value==="number")num(value);else if(Array.isArray(value))value.forEach(finiteTree);else if(value&&typeof value==="object")Object.values(value).forEach(finiteTree);}
async function hash(bytes:Uint8Array){const result=await crypto.subtle.digest("SHA-256",new Uint8Array(bytes));return Array.from(new Uint8Array(result),value=>value.toString(16).padStart(2,"0")).join("");}
function descriptor(value:unknown,shape:number[],units:string,named?:string){
  const d=closed(value,`${named?"name ":""}shape dtype units bytes sha256`);
  same(d.shape,shape);demand(d.dtype==="float32-le"&&d.units===units);if(named)demand(d.name===named+".f32");
  shape.forEach(size=>int(size,1,128*3200));demand(int(d.bytes,1,16*1048576)===4*shape.reduce((a,b)=>a*b,1));sha(d.sha256);
}
const expectedNames=["observed","initial",...FWI_METHODS.flatMap(method=>["model","background","predicted","residual","frames"].map(kind=>`${method}-${kind}`))];

export function parseFwiManifest(bytes:Uint8Array):FwiManifest {
  const m=closed(strictVelocityJson(bytes,160000,2*1048576),"schema id request request_utf8 originals execution_lane truth methods active_receivers source_hashes environment resources arrays complete");finiteTree(m);
  demand(m.schema==="geophysics.fwi-local-result/v1"&&m.complete===true&&m.truth===null&&["local-cpu","local-cuda"].includes(String(m.execution_lane)));
  const q=closed(m.request,"schema id source acquisition observed initial parameters");demand(q.schema==="geophysics.fwi-user-data/v1");demand(/^[A-Za-z0-9_-]{1,64}$/.test(text(q.id,64))&&m.id===q.id);
  const requestRaw=new TextEncoder().encode(text(m.request_utf8,16384));demand(requestRaw.length<=16384);same(sorted(strictVelocityJson(requestRaw,4000,16384)),sorted(q));
  const source=closed(q.source,"citation rights scope");text(source.citation);demand(["owner-permitted","CC0","CC-BY"].includes(String(source.rights))&&["owner-provided","synthetic-control"].includes(String(source.scope)));
  const ac=closed(q.acquisition,"frame spacing_m dt_s sources_m receivers_m wavelet amplitude_convention");
  demand(ac.frame==="local-x-z-down"&&ac.spacing_m===12.5&&ac.dt_s===.0005&&ac.wavelet==="Ricker-peak-at-1.5-over-f"&&ac.amplitude_convention==="Deepwave-scalar-point-source");same(ac.sources_m,[[300,75],[800,75],[1275,75]]);
  const obs=obj(q.observed);demand(Array.isArray(obs.shape)&&obs.shape.length===3);const shape=obs.shape as number[];demand(shape[0]===3&&[20,40].includes(shape[1]));int(shape[2],512,3200);
  same(ac.receivers_m,Array.from({length:shape[1]},(_,index)=>[Math.floor(6+114*index/(shape[1]-1))*12.5,75]));
  descriptor(q.observed,shape,"point-source-amplitude");descriptor(q.initial,[96,128],"m/s");
  const parameters=closed(q.parameters,"frequency_hz beta iterations_per_stage");num(parameters.frequency_hz,4,12);num(parameters.beta,.0001,.1);const iterations=int(parameters.iterations_per_stage,1,100);
  const originals=closed(m.originals,"request.json observed.f32 initial.f32");for(const [name,item] of Object.entries(originals)){const d=closed(item,"bytes sha256");int(d.bytes,1,16*1048576);sha(d.sha256);if(name!=="request.json"){const member=obj(q[name.split(".")[0]]);demand(d.bytes===member.bytes&&d.sha256===member.sha256);}}
  const hashes=closed(m.source_hashes,"fwi_user_data.py seismic.py geology.py");Object.values(hashes).forEach(sha);
  const env=closed(m.environment,"torch deepwave numpy device");Object.values(env).forEach(v=>text(v,256));
  const resource=closed(m.resources,"wall_seconds peak_sampled_rss_bytes rss_sampling_seconds peak_cuda_allocated_bytes");num(resource.wall_seconds,0);int(resource.peak_sampled_rss_bytes,1,Number.MAX_SAFE_INTEGER);demand(resource.rss_sampling_seconds===.02);int(resource.peak_cuda_allocated_bytes,0,Number.MAX_SAFE_INTEGER);
  same(m.active_receivers,Array.from({length:shape[1]},(_,index)=>index%5!==2));
  const arrays=closed(m.arrays,expectedNames.join(" ")),methods=closed(m.methods,FWI_METHODS.join(" "));
  let total=0;
  for(const name of expectedNames){
    const d=obj(arrays[name]);let expected=[96,128],units="m/s";
    if(name==="observed"||name.endsWith("-predicted")||name.endsWith("-residual")){expected=shape;units="point-source-amplitude";}
    else if(name.endsWith("-frames")){demand(Array.isArray(d.shape)&&d.shape.length===3);expected=[int(d.shape[0],1,128),96,128];}
    descriptor(d,expected,units,name);total+=num(d.bytes);
  }
  demand(total<=64*1048576);
  for(const method of FWI_METHODS){
    const s=closed(methods[method],"history history_records frame_history_indices frame_indices state_identity solver metrics numerical_verdict truth model_recovery_evaluated");
    demand(s.truth===null&&s.model_recovery_evaluated===false&&s.numerical_verdict==="finite-budget");
    demand(Array.isArray(s.history_records)&&s.history_records.length===4*(iterations+1)&&Array.isArray(s.history)&&s.history.length===s.history_records.length);
    for(let index=0;index<s.history.length;index++){num(s.history[index],0);demand(obj(s.history_records[index]).relative_mse===s.history[index]);}
    const indices=s.frame_history_indices;demand(Array.isArray(indices)&&indices.length=== (obj(arrays[method+"-frames"]).shape as number[])[0]);
    indices.forEach((value,index)=>{int(value,0,(s.history_records as unknown[]).length-1);if(index)demand(value>indices[index-1]);});same(s.frame_indices,indices);
    const identity=closed(s.state_identity,"final_frame_index selected_iteration frame_quantity predictions");
    demand(identity.frame_quantity==="velocity_m_s"&&identity.predictions==="final-model"&&identity.final_frame_index===indices.length-1&&identity.selected_iteration===s.history.length-1&&indices.at(-1)===identity.selected_iteration);
    const solver=obj(s.solver);demand(solver.truth_used_by_inverse===false&&solver.stopping==="finite_budget"&&solver.terminal_update_evaluated===true&&solver.iterations_per_stage===iterations&&solver.optimizer_calls===4*iterations&&solver.lbfgs_max_eval_per_call===25&&solver.beta===parameters.beta);same(solver.bounds_m_s,[1400,4400]);
    const metrics=closed(s.metrics,"fitted_initial_relative_mse fitted_final_relative_mse withheld_initial_relative_mse withheld_final_relative_mse");Object.values(metrics).forEach(value=>num(value,0));
  }
  return m as unknown as FwiManifest;
}

export async function readFwiFiles(files:readonly LocalFile[]):Promise<FwiAdmission>{
  demand(files.length===13&&new Set(files.map(file=>file.name)).size===13);
  const inventory=new Map(files.map(file=>[file.name,file]));demand(files.every(file=>["manifest.json",...expectedNames.map(name=>name+".f32")].includes(file.name)));
  const manifestFile=inventory.get("manifest.json")!;demand(manifestFile.size>0&&manifestFile.size<=2*1048576);
  const manifestBytes=new Uint8Array(await manifestFile.arrayBuffer());demand(manifestBytes.byteLength===manifestFile.size);
  const manifest=parseFwiManifest(manifestBytes),arrays:Record<string,Float32Array>={};
  const requestBytes=new TextEncoder().encode(manifest.request_utf8);demand(manifest.originals["request.json"].bytes===requestBytes.length&&manifest.originals["request.json"].sha256===await hash(requestBytes));
  for(const name of expectedNames){
    const descriptor=manifest.arrays[name],file=inventory.get(descriptor.name)!;demand(file.size===descriptor.bytes);
    const bytes=new Uint8Array(await file.arrayBuffer());demand(bytes.byteLength===file.size&&(await hash(bytes))===descriptor.sha256);
    const values=new Float32Array(bytes.byteLength/4),view=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength);
    for(let index=0;index<values.length;index++){const value=view.getFloat32(index*4,true);num(value);values[index]=value;}
    arrays[name]=values;
    if(descriptor.units==="m/s")demand(values.every(value=>value>=1400&&value<=4400));
  }
  demand(manifest.arrays.observed.sha256===manifest.request.observed.sha256&&manifest.arrays.initial.sha256===manifest.request.initial.sha256);
  demand(Array.from(arrays.initial).every(value=>value>1400&&value<4400));
  for(const method of FWI_METHODS){
    const model=arrays[method+"-model"],frames=arrays[method+"-frames"],start=frames.length-model.length;
    demand(model.every((value,index)=>value===frames[start+index]));
    demand(model.every(value=>value>=1400&&value<=4400));
    const predicted=arrays[method+"-predicted"],residual=arrays[method+"-residual"];
    demand(residual.every((value,index)=>value===Math.fround(arrays.observed[index]-predicted[index])));
  }
  return {manifest,arrays,manifestBytes,manifestSha256:await hash(manifestBytes),physicsReplayed:false};
}
