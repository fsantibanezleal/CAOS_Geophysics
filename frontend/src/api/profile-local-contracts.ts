/** Native profile-result admission; no inverse execution or source signature. */
import { strictVelocityJson } from "./velocity-local-contracts";

type Obj = Record<string, unknown>;
export type ProfileMesh = {nodes:number[][];cells:number[][]};
export type ProfileModel = {name:string;values:number[];centres:number[][];coverage:number[];unit:string;coverageUnit:string;
  mesh:ProfileMesh|null;observed:number[];predicted:number[];residual:number[];sigma:number[];training:number[];held:number[];report:Obj};
export type ParsedProfile = {result:Obj;models:ProfileModel[];sensors:number[][];rows:number[][];method:"ert"|"traveltime";sourceId:string;verdict:string};
export type ProfileAdmission = ParsedProfile & {resultSha256:string;manifestSha256:string;resultBytes:number;physicsReplayed:false};
const require:(ok:unknown)=>asserts ok = ok=>{if(!ok)throw new Error("Supplied profile files rejected: invalid or inconsistent contract");};
function obj(v:unknown):Obj { require(v!==null && typeof v==="object" && !Array.isArray(v));return v as Obj; }
function closed(v:unknown,keys:string[]) {const r=obj(v);require(Object.keys(r).length===keys.length&&keys.every(k=>Object.hasOwn(r,k)));return r;}
function number(v:unknown,lo=-Infinity,hi=Infinity):number {require(typeof v==="number"&&Number.isFinite(v)&&v>=lo&&v<=hi);return v;}
function integer(v:unknown,lo:number,hi:number) {const n=number(v,lo,hi);require(Number.isInteger(n));return n;}
function text(v:unknown):string {require(typeof v==="string"&&v.trim().length>0&&[...v].length<=256&&!/[\u0000-\u001f\u007f]/.test(v));return v;}
function hash(v:unknown):string {require(typeof v==="string"&&/^[a-f0-9]{64}$/.test(v));return v;}
function vector(v:unknown,n:number,lo=-Infinity,hi=Infinity):number[] {require(Array.isArray(v)&&v.length===n);return v.map(x=>number(x,lo,hi));}
function points(v:unknown,lo:number,hi:number):number[][] {require(Array.isArray(v));integer(v.length,lo,hi);return v.map(p=>vector(p,2));}
function allFinite(v:unknown) {if(typeof v==="number")number(v);else if(Array.isArray(v))v.forEach(allFinite);else if(v!==null&&typeof v==="object")Object.values(v).forEach(allFinite);}
function near(a:number,b:number) {require(Math.abs(a-b)<=1e-12+1e-12*Math.max(Math.abs(a),Math.abs(b)));}
function partition(v:unknown,n:number):number[] {require(Array.isArray(v));return v.map(i=>integer(i,0,n-1));}
function folds(training:unknown,held:unknown,n:number) {
  const tr=partition(training,n),he=partition(held,n),joined=[...tr,...he];
  require(tr.length>0&&he.length>0&&joined.length===n&&new Set(joined).size===n);return {training:tr,held:he};
}
function mesh(value:unknown,n:number,centres:number[][]):ProfileMesh|null {
  if(value===undefined)return null; // Historical native-centre result, not interpolated cells.
  const d=closed(value,["schema","coordinate_unit","vertical_positive","node_xz_m","cell_node_ids"]);
  require(d.schema==="geophysics.profile-parameter-mesh/v1"&&d.coordinate_unit==="m"&&d.vertical_positive==="up");
  const nodes=points(d.node_xz_m,3,200000);require(Array.isArray(d.cell_node_ids)&&d.cell_node_ids.length===n);
  const cells=d.cell_node_ids.map((r,i)=>{
    const ids=vector(r,3,0,nodes.length-1);require(ids.every(Number.isInteger)&&new Set(ids).size===3);
    const [a,b,c]=ids.map(j=>nodes[j]);require((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])!==0);
    for(let axis=0;axis<2;axis++) require(Math.abs((a[axis]+b[axis]+c[axis])/3-centres[i][axis])<=1e-8+1e-12*Math.abs(centres[i][axis]));
    return ids;
  });return {nodes,cells};
}

export function parseProfileResult(value:unknown):ParsedProfile {
  allFinite(value);
  const r=closed(value,["schema","method","metadata","original","geometry","engine_report","code_hashes","numerical_settings","scope","content_sha256"]);
  require(r.schema==="geophysics.supplied-profile-result/v1");hash(r.content_sha256);
  const method=r.method==="ert.topographic-profile/v1"?"ert":r.method==="traveltime.first-arrival-profile/v1"?"traveltime":null;require(method);
  const meta=closed(r.metadata,["schema","method","source","frame","weights"]);require(meta.schema==="geophysics.supplied-profile/v1"&&meta.method===r.method);
  const source=closed(meta.source,["source_id","kind","citation","rights","sha256","bytes"]),sourceId=text(source.source_id);text(source.citation);
  require(["user_upload","field","synthetic_control"].includes(String(source.kind)));hash(source.sha256);integer(source.bytes,1,8*1048576);
  const rights=closed(source.rights,["holder","processing_allowed","redistribution_allowed"]);text(rights.holder);require(rights.processing_allowed===true&&typeof rights.redistribution_allowed==="boolean");
  const f=closed(meta.frame,["horizontal_reference","vertical_datum","coordinate_unit","vertical_positive","profile_axes"]);text(f.horizontal_reference);text(f.vertical_datum);
  require(f.coordinate_unit==="m"&&f.vertical_positive==="up"&&JSON.stringify(f.profile_axes)==='["distance","elevation"]');
  require(closed(meta.weights,["policy"]).policy==="provider-example-conditional/v1");
  const original=closed(r.original,["sha256","bytes"]);require(original.sha256===source.sha256&&original.bytes===source.bytes);
  const scope=closed(r.scope,["uploaded","raw_copied","execution","rights","uncertainty","truth_available","residual_convention"]);
  require(scope.uploaded===false&&scope.raw_copied===false&&scope.execution==="explicit-local"&&scope.truth_available===false&&scope.residual_convention==="predicted-minus-observed"&&scope.uncertainty==="assumed-not-calibrated"&&scope.rights==="operator-declaration-not-independent-permission-review");
  const code=obj(r.code_hashes),engineName=method==="ert"?"ert.py":"traveltime.py";
  closed(code,[engineName,"supplied_profiles.py",...(Object.hasOwn(code,"profile_mesh.py")?["profile_mesh.py"]:[])]);Object.values(code).forEach(hash);require(Object.keys(obj(r.numerical_settings)).length>0);
  const g=closed(r.geometry,method==="ert"?["sensor_xz_m","abmn_zero_based","row_ids_zero_based"]:["sensor_xy_m","shot_geophone_zero_based","row_ids_zero_based"]);
  const sensors=points(g[method==="ert"?"sensor_xz_m":"sensor_xy_m"],method==="ert"?4:2,method==="ert"?512:1024);
  require(sensors.every((p,i)=>i===0||p[0]>sensors[i-1][0]));
  const pairs=g[method==="ert"?"abmn_zero_based":"shot_geophone_zero_based"];require(Array.isArray(pairs));integer(pairs.length,4,method==="ert"?20000:100000);
  const rows=pairs.map(p=>{const ids=vector(p,method==="ert"?4:2,0,sensors.length-1);require(ids.every(Number.isInteger)&&new Set(ids).size===ids.length);return ids;});
  require(JSON.stringify(g.row_ids_zero_based)===JSON.stringify(rows.map((_,i)=>i)));
  const e=obj(r.engine_report);require(e.schema===`inverse-earth.local-${method==="ert"?"ert-m07":"traveltime-m09"}/v1`&&e.source_id===sourceId&&e.source_sha256===original.sha256&&e.source_bytes===original.bytes&&e.truth===null&&e.field_geology_claim===null&&e.raw_publication===false&&e.rights_decision==="supplied-declaration-not-verified");
  require(typeof e.inverse_status==="string"&&["passed","not-converged","ineligible","unverified"].includes(e.inverse_status));
  const models:ProfileModel[]=[];
  const add=(name:string,v:unknown,observed:number[],part:{training:number[];held:number[]})=>{
    const d=obj(v),n=integer(d.mesh_cells,2,100000),centres=points(d[method==="ert"?"model_cell_center_xz_m":"model_cell_center_xy_m"],n,n);
    const values=vector(d[method==="ert"?"model_resistivity_ohm_m":"model_velocity_m_s"],n,0);require(values.every(v=>v>0));
    const coverage=vector(d[method==="ert"?"coverage_log10_sensitivity_per_cell":"raypath_coverage_m_per_cell"],n,method==="ert"?-Infinity:0);
    const predicted=vector(d[method==="ert"?"predicted_r_ohm":"predicted_t_s"],rows.length,0);require(predicted.every(v=>v>0));
    const residual=vector(d[method==="ert"?"signed_residual_r_ohm":"signed_residual_t_s"],rows.length);
    residual.forEach((v,i)=>near(v,predicted[i]-observed[i]));
    const sigma=observed.map(v=>Math.max(.03*Math.abs(v),method==="ert"?.001:.0001));
    models.push({name,values,centres,coverage,unit:method==="ert"?"Ω m":"m/s",coverageUnit:method==="ert"?"log₁₀ sensitivity / cell size":"m",mesh:mesh(d.parameter_mesh,n,centres),observed,predicted,residual,sigma,...part,report:d});
  };
  if(e.inverse!==undefined){
    if(method==="ert"){
      const d=obj(e.inverse),split=obj(e.split),observed=vector(d.observed_r_ohm,rows.length,0);require(observed.every(v=>v>0));
      add("interleaved",d,observed,folds(split.training_rows,split.heldout_rows,rows.length));
    }else{
      const inverse=obj(e.inverse),observations=obj(e.observations),split=obj(e.split),observed=vector(observations.picked_t_s,rows.length,0);require(observed.every(v=>v>0));
      require(JSON.stringify(observations.sensor_xy_m)===JSON.stringify(sensors)&&JSON.stringify(observations.shot_geophone_zero_based)===JSON.stringify(rows));
      for(const name of ["interleaved","central_block"]){if(inverse[name]===undefined)continue;const s=obj(split[name]);const part=folds(s.training_rows,s.heldout_rows,rows.length);
        const trainShots=new Set(part.training.map(i=>rows[i][0]));require(part.held.every(i=>!trainShots.has(rows[i][0])));add(name,inverse[name],observed,part);}
    }
  }
  if(e.inverse_status==="passed")require(models.length===(method==="ert"?1:2));
  return {result:r,models,sensors,rows,method,sourceId,verdict:e.inverse_status};
}

async function digest(raw:Uint8Array){return [...new Uint8Array(await crypto.subtle.digest("SHA-256",raw as Uint8Array<ArrayBuffer>))].map(v=>v.toString(16).padStart(2,"0")).join("");}
/** Extract root member original lexical bytes, preserving Python floating tokens. */
function members(raw:string){
  const found=new Map<string,{start:number;end:number;valueStart:number;valueEnd:number}>();let depth=0;
  for(let i=0;i<raw.length;i++){
    const c=raw[i];if(c==='"'){
      const start=i;for(i++;i<raw.length;i++){if(raw[i]==="\\")i++;else if(raw[i]==='"')break;}
      let colon=i+1;while(/\s/.test(raw[colon]??"")&&colon<raw.length)colon++;
      if(depth===1&&raw[colon]===":"){
        const key=JSON.parse(raw.slice(start,i+1));let v=colon+1;while(/\s/.test(raw[v]??"")&&v<raw.length)v++;
        let j=v,nested=0;
        for(;j<raw.length;j++){if(raw[j]==='"'){for(j++;j<raw.length;j++){if(raw[j]==="\\")j++;else if(raw[j]==='"')break;}}
          else if(raw[j]==="{"||raw[j]==="[")nested++;else if(raw[j]==="}"||raw[j]==="]"){if(nested===0)break;nested--;}
          else if(raw[j]===","&&nested===0)break;}
        let end=j;while(end>v&&/\s/.test(raw[end-1]))end--;
        found.set(key,{start,end:j,valueStart:v,valueEnd:end});i=j-1;
      }
    }else if(c==="{"||c==="[")depth++;else if(c==="}"||c==="]")depth--;
  }return found;
}
export async function readProfileFiles(resultFile:Blob,manifestFile:Blob):Promise<ProfileAdmission>{
  integer(resultFile.size,1,32*1048576);integer(manifestFile.size,1,65536);
  const [a,b]=await Promise.all([resultFile.arrayBuffer(),manifestFile.arrayBuffer()]);require(a.byteLength===resultFile.size&&b.byteLength===manifestFile.size);
  const bytes=new Uint8Array(a),result=parseProfileResult(strictVelocityJson(bytes,2000000,32*1048576,18));
  const m=closed(strictVelocityJson(new Uint8Array(b),40000,65536),["schema","result","method","source_sha256","content_sha256","configuration_sha256"]);
  const member=closed(m.result,["name","bytes","sha256"]),resultSha256=await digest(bytes);
  require(m.schema==="geophysics.supplied-profile-manifest/v1"&&member.name==="result.json"&&member.bytes===a.byteLength&&member.sha256===resultSha256&&m.method===result.result.method&&m.source_sha256===obj(result.result.original).sha256&&m.content_sha256===result.result.content_sha256);
  const raw=new TextDecoder("utf-8",{fatal:true}).decode(bytes),fields=members(raw),content=fields.get("content_sha256"),settings=fields.get("numerical_settings");require(content&&settings);
  let without:string;if(raw[content.end]===",")without=raw.slice(0,content.start)+raw.slice(content.end+1);else{require(raw[content.start-1]===",");without=raw.slice(0,content.start-1)+raw.slice(content.end);}
  require(await digest(new TextEncoder().encode(without))===result.result.content_sha256);
  require(await digest(new TextEncoder().encode(raw.slice(settings.valueStart,settings.valueEnd)))===m.configuration_sha256);
  return {...result,resultSha256,manifestSha256:await digest(new Uint8Array(b)),resultBytes:a.byteLength,physicsReplayed:false};
}
export function profileSelection(parsed:ParsedProfile,model:number,row:number,cell:number){
  const m=parsed.models[integer(model,0,parsed.models.length-1)];integer(row,0,parsed.rows.length-1);integer(cell,0,m.values.length-1);
  return {fold:m.name,row:{index:row,sensors_zero_based:parsed.rows[row],observed:m.observed[row],predicted:m.predicted[row],residual:m.residual[row],sigma:m.sigma[row],partition:m.held.includes(row)?"held":"training"},cell:{index:cell,centre_m:m.centres[cell],value:m.values[cell],unit:m.unit,coverage:m.coverage[cell],coverage_unit:m.coverageUnit,nodes_m:m.mesh?.cells[cell].map(i=>m.mesh!.nodes[i])??null}};
}
