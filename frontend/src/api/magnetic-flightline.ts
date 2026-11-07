import { ApiClient } from "./client";
import { processingId, processingObject, processingText } from "./processing-contracts";

export const M03_FLIGHTLINE_METHOD = "magnetic.flightline-qc-grid/v1" as const;
const root = (project: string) => `/api/projects/${processingId(project)}`;
const digest = (value: unknown): value is string => typeof value === "string" && /^[a-f0-9]{64}$/.test(value);
const text = (value: unknown, name: string) => processingText(value, name);
const finite = (value: unknown, name: string) => { if (typeof value !== "number" || !Number.isFinite(value)) throw new Error(`Invalid M03 ${name}`); return value; };

export interface M03Receipt { dataset_id: string; project_id: string; raw_asset_id: string; version: number; schema: string; modality: string; row_count: number; parser_version: string; raw_sha256: string; sha256: string; created_at: string; qc_verdict: string }
export interface M03Job { job_id: string; project_id: string; dataset_id: string; dataset_sha256: string; method_id: string; state: "queued"|"running"|"succeeded"|"failed"|"cancelled"; cancel_requested: boolean; request_sha256: string; result_sha256: string|null; error: {code:string;message:string}|null; request: {parameters: {grid_spacing_m:number;holdout_fraction:number;seed:string}} }
export interface M03Result {
  schema: "magnetic-flightline-process-result-1"; job_id: string; dataset_id: string; dataset_sha256: string; request_sha256: string; result_sha256?: string;
  source: Record<string, unknown>; configuration: Record<string, unknown>; geometry_qc: { lines: Array<Record<string, unknown>>; crossovers?: Array<Record<string, unknown>>; [key:string]: unknown };
  split: {fit_line_ids:string[];holdout_line_ids:string[];[key:string]:unknown}; heldout_interpolation: {heldout_row_count:number;supported_heldout_row_count:number;coverage_fraction:number;mae:number|null;rmse:number|null;interpretation:string};
  grid: {x_easting_m:number[];y_northing_m:number[];shape_yx:number[];values:number[][];support_mask:boolean[][];unsupported_value_encoding:string}; limitations:string[]; claims?: Record<string,unknown>;
}
function parseReceipt(raw: unknown): M03Receipt {
  const r=processingObject(raw,"M03 dataset receipt");
  for(const key of ["dataset_id","project_id","raw_asset_id"])processingId(text(r[key],key));
  if(r.schema!=="geophysics.observation-dataset/v1"||r.modality!=="magnetic_flightline"||r.version!==1||!Number.isSafeInteger(r.row_count)||Number(r.row_count)<12||Number(r.row_count)>250000||r.parser_version!=="magnetic-flightline-original/v1"||r.qc_verdict!=="source_bound_not_numerically_processed"||!digest(r.raw_sha256)||!digest(r.sha256)||typeof r.created_at!=="string"||!Number.isFinite(Date.parse(r.created_at)))throw new Error("Invalid M03 magnetic dataset receipt");
  return raw as M03Receipt;
}
function parseJob(raw: unknown): M03Job {
  const j=processingObject(raw,"M03 job");
  for(const key of ["job_id","project_id","dataset_id"])processingId(text(j[key],key));
  const req=processingObject(j.request,"M03 job request"), params=processingObject(req.parameters,"M03 parameters");
  if(j.method_id!==M03_FLIGHTLINE_METHOD||!(["queued","running","succeeded","failed","cancelled"] as unknown[]).includes(j.state)||typeof j.cancel_requested!=="boolean"||!digest(j.dataset_sha256)||!digest(j.request_sha256)||(j.result_sha256!==null&&!digest(j.result_sha256)))throw new Error("Invalid M03 job receipt");
  finite(params.grid_spacing_m,"grid_spacing_m");finite(params.holdout_fraction,"holdout_fraction");text(params.seed,"seed");
  if(j.error!==null){const error=processingObject(j.error,"M03 job error");text(error.code,"error code");text(error.message,"error message");}
  return raw as M03Job;
}
function parseResult(raw: unknown, job: M03Job, receipt: M03Receipt): M03Result {
  const r=processingObject(raw,"M03 result");
  if(r.schema!=="magnetic-flightline-process-result-1"||r.job_id!==job.job_id||r.dataset_id!==receipt.dataset_id||r.dataset_sha256!==receipt.sha256||r.request_sha256!==job.request_sha256)throw new Error("M03 result identity does not match the selected job and dataset");
  const score=processingObject(r.heldout_interpolation,"M03 held-out score"), grid=processingObject(r.grid,"M03 grid");
  const x=grid.x_easting_m,y=grid.y_northing_m,values=grid.values,mask=grid.support_mask;
  if(!Array.isArray(x)||!Array.isArray(y)||x.length<2||y.length<2||!Array.isArray(values)||!Array.isArray(mask)||values.length!==y.length||mask.length!==y.length||values.some((row,i)=>!Array.isArray(row)||row.length!==x.length||!Array.isArray(mask[i])||mask[i].length!==x.length))throw new Error("M03 grid axes, values and support mask disagree");
  const valueRows=values as unknown[][], maskRows=mask as unknown[][];
  const shape=grid.shape_yx;
  if(!Array.isArray(shape)||shape.length!==2||shape[0]!==y.length||shape[1]!==x.length)throw new Error("M03 grid declared shape does not match axes");
  x.forEach(v=>finite(v,"easting axis"));y.forEach(v=>finite(v,"northing axis"));
  valueRows.forEach((row,i)=>row.forEach((v,j)=>{finite(v,"grid value");if(typeof maskRows[i][j]!=="boolean")throw new Error("Invalid M03 support mask");}));
  const source=processingObject(r.source,"M03 source lineage");if(source.sha256!==receipt.raw_sha256)throw new Error("M03 result source digest differs from the uploaded original");
  const geometry=processingObject(r.geometry_qc,"M03 geometry QC"),split=processingObject(r.split,"M03 split");
  if(!Array.isArray(r.limitations)||!r.limitations.every(v=>typeof v==="string")||!Array.isArray(geometry.lines)||!Array.isArray(split.fit_line_ids)||!Array.isArray(split.holdout_line_ids)||![...split.fit_line_ids,...split.holdout_line_ids].every(v=>typeof v==="string"))throw new Error("Incomplete M03 scientific result");
  for(const lineRaw of geometry.lines){const line=processingObject(lineRaw,"M03 line summary"),extent=processingObject(line.coordinate_extent_m,"M03 line extent"),height=processingObject(line.sensor_height_m,"M03 height QC");text(line.line_id,"line ID");if(!["flight","tie"].includes(String(line.role))||!Array.isArray(extent.easting)||!Array.isArray(extent.northing)||extent.easting.length!==2||extent.northing.length!==2||!Array.isArray(height.qc_outlier_rows))throw new Error("Invalid M03 line geometry or height QC");[...extent.easting,...extent.northing,height.minimum,height.median,height.maximum,height.mad].forEach(v=>finite(v,"line QC value"));}
  const rows=finite(score.heldout_row_count,"held-out row count"),supported=finite(score.supported_heldout_row_count,"supported held-out row count"),coverage=finite(score.coverage_fraction,"coverage fraction");if(!Number.isInteger(rows)||!Number.isInteger(supported)||supported<0||supported>rows||coverage<0||coverage>1||Math.abs(coverage-(rows?supported/rows:0))>1e-9)throw new Error("M03 held-out coverage count mismatch");if(score.mae!==null&&finite(score.mae,"MAE")<0)throw new Error("Invalid M03 MAE");if(score.rmse!==null&&finite(score.rmse,"RMSE")<0)throw new Error("Invalid M03 RMSE");
  return raw as M03Result;
}
export class MagneticFlightlineApi {
  constructor(private readonly api:ApiClient){}
  async createDataset(project:string,asset:string,request:Record<string,unknown>,signal?:AbortSignal){
    const csrf=await this.api.requestJson("/api/auth/csrf",v=>processingObject(v,"csrf"),{signal});
    const receipt=await this.api.requestJson(`${root(project)}/datasets`,v=>parseReceipt(v),{method:"POST",csrfToken:text(csrf.csrf_token,"CSRF token"),body:{asset_id:processingId(asset),magnetic_request:request},signal});
    if(receipt.project_id!==project||receipt.raw_asset_id!==asset)throw new Error("M03 dataset receipt does not match requested project and source");return receipt;
  }
  async methods(project:string,dataset:string,signal?:AbortSignal){return this.api.requestJson(`${root(project)}/datasets/${processingId(dataset)}/methods`,raw=>{
    const m=processingObject(raw,"M03 eligibility");if(m.dataset_id!==dataset||!Array.isArray(m.methods)||!Array.isArray(m.unavailable))throw new Error("Invalid method eligibility response");
    const row=[...m.methods,...m.unavailable].map(x=>processingObject(x,"method eligibility")).find(x=>x.method_id===M03_FLIGHTLINE_METHOD);
    if(!row)return{eligible:false,reason:"The host has not advertised M03 for this dataset.",reason_fields:["dataset.method_catalog"]};
    const reason=[row.reason,row.scope,row.lane].find(v=>typeof v==="string"&&v.trim()) as string|undefined;
    const pending=reason?.toLowerCase().includes("pending_host_admission")??false;
    const reasonFields=Array.isArray(row.reason_fields)&&row.reason_fields.every(v=>typeof v==="string"&&v.trim())?row.reason_fields as string[]:[];
    if(row.eligible!==true&&!reasonFields.length)throw new Error("M03 ineligibility response has no field-specific reason");
    return{eligible:row.eligible===true&&!pending,reason:pending?"pending_host_admission · M03 worker is implemented; online execution awaits measured ML VPS resource admission. The local pipeline remains available.":reason??"",reason_fields:reasonFields};
  },{signal});}
  async submit(project:string,receipt:M03Receipt,parameters:{grid_spacing_m:number;holdout_fraction:number;seed:string},signal?:AbortSignal){
    const csrf=await this.api.requestJson("/api/auth/csrf",v=>processingObject(v,"csrf"),{signal});
    const job=await this.api.requestJson(`${root(project)}/jobs`,parseJob,{method:"POST",csrfToken:text(csrf.csrf_token,"CSRF token"),body:{dataset_id:receipt.dataset_id,method_id:M03_FLIGHTLINE_METHOD,parameters},signal});
    if(job.project_id!==project||job.dataset_id!==receipt.dataset_id||job.dataset_sha256!==receipt.sha256)throw new Error("M03 job is not bound to the selected dataset");return job;
  }
  async jobs(project:string,signal?:AbortSignal){return this.api.requestJson(`${root(project)}/jobs`,raw=>{const o=processingObject(raw,"jobs");if(!Array.isArray(o.jobs))throw new Error("Invalid jobs list");return o.jobs.filter(v=>processingObject(v,"job").method_id===M03_FLIGHTLINE_METHOD).map(parseJob);},{signal});}
  async result(project:string,job:M03Job,receipt:M03Receipt,signal?:AbortSignal){if(job.state!=="succeeded")throw new Error("M03 result is not ready");return this.api.requestJson(`${root(project)}/jobs/${processingId(job.job_id)}/result`,raw=>parseResult(raw,job,receipt),{signal});}
}
