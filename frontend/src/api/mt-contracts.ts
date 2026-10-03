/** Actual online MT serialization contract. No field truth or gravity dispatch. */
import { unzipSync } from "fflate";
import { rawPhysical, type RawPhysicalMetadata } from "./contracts";
import { hash, integer, keys, number, processingId as id, processingObject as obj, processingText as text, same, sha, M05_METHOD, M06_METHOD, type EdiDatasetReceipt, type MtProcessingJob, type MtInverseParameters } from "./processing-contracts";
import { mtForward } from "../mt";

export interface MtSource { provider: string; exact_url: string | null; doi: string | null; citation: string | null; rights_decision: "mirror" | "provider-link-only" | "derivative-only"; rights_statement: string; attribution: string }
export interface EdiDataset {
  schema: "geophysics.observation-dataset/v1"; dataset_id: string; version: 1; owner_id: string; project_id: string; raw_asset_id: string;
  parent_raw_sha256: string; parent_raw_bytes: number; parser_version: "edi-strict-envelope/v1"; modality: "edi_transfer_function";
  dimensions: {frequency: number}; axis_order: ["frequency"]; physical_metadata: RawPhysicalMetadata; qc_verdict: "awaiting_full_tensor_qc"; source: MtSource;
}
export interface MtCurves {real: number[]; imag: number[]; apparent: number[]; phase: number[]}
export interface MtTensor {real: number[][][]; imag: number[][][]; sigma: number[][][]; rotation_deg: number[]}
export interface MtCompatibility {xx_component_wrms: number; yy_component_wrms: number; antisymmetry_conservative_wrms: number; threshold: 3; passes_screen: boolean; criteria: string; caveat: string}
export interface MtProvenance {
  source_file: string; source_sha256: string; source_bytes: number; parser: string; parser_version: string; preflight: string;
  original_units: "mt" | "ohm"; output_units: "ohm"; units_multiplier_to_ohm: number; original_sign_convention: "+" | "-"; output_sign_convention: "+";
  variance_convention: "complex" | "per-real-component"; sigma_definition: string; error_assumption: string;
  interpretation_arguments: {units: string | null; sign_convention: string | null; variance_convention: string | null};
  rotation_action: string; rotation_reference: string | null; original_rotation_deg: number[]; frequency_permutation: number[]; original_frequency_hz: number[];
  tipper_present: boolean; tipper_used_in_1d_inversion: false; data_kind: string; synthetic: boolean; target_known: false;
}
export interface MtTipper {present: true; used_in_1d_inversion: false; raw_variance_convention: string; rotation_deg: number[]; missing_frequency_hz: number[]; components: Record<"X" | "Y", {real: (number | null)[]; imag: (number | null)[]; variance: (number | null)[]}>}
export interface MtScreen {
  schema: "inverse-earth/edi-screen/v1"; id: string; family: "mt"; source_kind: string; truth: null; methods: Record<string, never>;
  inversion_performed: false; one_d_fit_performed: false; one_d_inversion_eligible: boolean; interpretation: string; frequencies_hz: number[];
  observed: Record<"xy" | "yx", MtCurves & {sigma_real_imag_ohm: number[]}>; tensor: MtTensor; compatibility: MtCompatibility; provenance: MtProvenance;
  metadata: {header: Record<string, unknown>; info: Record<string, unknown>; mtsect: Record<string, unknown>; measurement_layout: Record<string, unknown>; tipper?: MtTipper; [key: string]: unknown};
}
export interface MtFitSummary {model_ohm_m: number[]; training_objective: number; training_component_wrms: number; heldout_component_wrms: number; solver_success: boolean; stop_reason: string}
export interface MtProtocol {
  frequency_partition: string; training_mask: boolean[]; selection: string; starts: (MtFitSummary & {initial_ohm_m: number[]})[];
  halfspace_baseline: MtFitSummary; beta_sensitivity: MtFitSummary & {beta: number}; thickness_sensitivity: (MtFitSummary & {thickness_m: number[]})[];
  selected_start_ohm_m: number[]; uncertainty_limit: string;
}
export interface MtBootstrap {
  kind: "conditional-parametric-bootstrap"; solver: string; conditioning: string; members: number; quantiles: [number, number]; lower: number[]; upper: number[]; mean: number[]; std: number[];
  units: "ohm m"; target: string; confidence: number; interval_method: string; conditioning_model: number[]; fixed_thickness_m: number[]; bounds_ohm_m: [1,6000];
  sigma_per_real_component: number[]; active: boolean[]; initial_model: number[]; beta: number; sampling_law: string; seed: number; sample_seeds: number[]; successful_seeds: number[];
  requested: number; completed: number; failures: {seed: number; error: string}[]; samples: number[][]; interval_ohm_m: [number[], number[]] | null; status: "computed" | "incomplete"; limitations: string;
}
export interface MtMethod {
  name: string; name_es: string; model: number[]; predicted: MtCurves; residual: MtCurves; frames: number[][]; history: number[];
  states: {frame_index: number; kind: string; step: number; objective: {data: number; regularization: number; total: number}}[];
  metrics: {wrms: number; active_component_wrms: number; withheld_component_wrms: number; initial_component_wrms: number; objective: number; data_objective: number; regularization_objective: number; other_component_wrms: number};
  solver: {algorithm: string; max_nfev: number; nfev: number; residual_calls: number; success: boolean; status: number; stop_reason: string; optimality: number; tolerance: {ftol: number; xtol: number; gtol: number}; scipy_cost_multiplier_to_J: 2; device: "cpu"; dtype: "float64"; bounds_ohm_m: [1,6000]; beta: number; initial_model: number[]; fixed_thickness_m: number[]; objective: string; residual_normalization: string; sigma_definition: string; regularization_normalization: string};
  identifiability: {kind: string; singular_values: number[]; numerical_rank: number; effective_rank: number; parameter_count: number; condition_number: number | null; singular_threshold: number; local_logrho_sd: number[]; weak_direction_participation: number[]; near_bound: boolean[]; unresolved_layers: number[]; status: "locally_resolved" | "unresolved"; caveat: string};
  evaluation: {status: "unresolved" | "failed"; reason_codes: string[]; target: string; target_units: "ohm m"; criteria: string; model_recovery: string};
  state_identity: {final_frame_index: number; selected_iteration: number; frame_quantity: string; predictions: "final-model"};
  state: {selected_frame: number; selected_step: number; model_sha256: string; history_quantity: string; model_sha256_encoding: string; final_is_last_frame: true; predictions_from: "selected_final"};
  objective: {definition: string; beta: number; data: number; regularization: number; total: number}; target: {quantity: string; units: "ohm m"; dimensionality: string; provenance: string}; device: "cpu"; uncertainty: MtBootstrap;
}
export interface MtInverse {
  schema: "inverse-earth/edi-1d/v1"; id: string; family: "mt"; source_kind: string; component: "xy"; geometry: string; units: "ohm m"; data_units: "ohm";
  frequencies: number[]; thickness: number[]; observed: MtCurves; sigma: number[]; active: boolean[]; methods: {"mt-lm": MtMethod}; tensor: MtTensor; compatibility: MtCompatibility;
  provenance: MtProvenance; metadata: MtScreen["metadata"]; parameters: {regularization: number; bounds_ohm_m: [1,6000]; component: "xy"}; truth: null; clean: null; evaluation_protocol: MtProtocol;
}
export interface MtResult {
  schema: "geophysics.processing-result/v1"; job_id: string; dataset_id: string; dataset_sha256: string; method_id: typeof M05_METHOD | typeof M06_METHOD; request_sha256: string;
  parameters: Record<string, never> | MtInverseParameters; raw_asset_id: string; raw_sha256: string; raw_bytes: number; engine_sha256: string; parser_sha256: string; forward_sha256: string;
  environment: {python: string; packages: Record<string,string>}; environment_sha256: string; axis_order: ["frequency"]; dimensions: {frequency: number}; frequency_hz: number[];
  physical_metadata: RawPhysicalMetadata; source: MtSource; screen: MtScreen; inverse: MtInverse | null; qc_screen_sha256: string | null; truth: null; interpretation_limit: string;
}
const reject = (why: string): never => {throw new Error(`MT contract rejected: ${why}`);};
const expect: (condition: unknown, why: string) => asserts condition = (condition, why) => {if (!condition) reject(why);};
const close = (a: number, b: number, label: string) => expect(Math.abs(a-b) <= 1e-8*Math.max(1e-10,Math.abs(a),Math.abs(b)), label);
const vector = (value: unknown, n?: number, positive = false): number[] => {
  expect(Array.isArray(value) && (n === undefined || value.length === n), "vector dimensions");
  const row = value as number[]; row.forEach(v => {number(v); if (positive) expect(v > 0, "positive quantity");}); return row;
};
const bools = (value: unknown, n: number): boolean[] => {expect(Array.isArray(value) && value.length === n && value.every(v => typeof v === "boolean"), "boolean mask"); return value as boolean[];};
function source(value: unknown): MtSource {
  const d=obj(value,"source"); keys(d,["provider","exact_url","doi","citation","rights_decision","rights_statement","attribution"],"source");
  ["provider","rights_statement","attribution"].forEach(k=>text(d[k],k));
  ["exact_url","doi","citation"].forEach(k=>{if(d[k]!==null)text(d[k],k);});
  expect(["mirror","provider-link-only","derivative-only"].includes(String(d.rights_decision)),"source rights"); return value as MtSource;
}
function physical(value: unknown, count: number) {
  const p=rawPhysical(value), g=p.geometry; expect(["ohm","mV/km/nT"].includes(p.measurement_unit),"input impedance unit");
  text(g.station_id,"station"); same(g.frequency_count,count,"declared count");
  expect(["+","-"].includes(String(g.sign_convention)) && ["complex","per-real-component"].includes(String(g.variance_convention)),"explicit sign/variance");
  number(g.rotation_degrees); expect(Array.isArray(g.tensor_components),"full tensor components");
  const c=[...(g.tensor_components as string[])].sort().join(); expect(c === "Zxx,Zxy,Zyx,Zyy" || c === "Tx,Ty,Zxx,Zxy,Zyx,Zyy","full tensor/tipper");
  expect(p.component_frame === "instrument axes" && g.rotation_reference === "unspecified" || p.component_frame === "geographic ENU" && g.rotation_reference === "geographic-north","frame/reference"); return p;
}
export function parseEdiDataset(value: unknown): EdiDataset {
  const d=obj(value,"EDI envelope"); keys(d,["schema","dataset_id","version","owner_id","project_id","raw_asset_id","parent_raw_sha256","parent_raw_bytes","parser_version","modality","dimensions","axis_order","physical_metadata","qc_verdict","source"],"EDI envelope");
  expect(d.schema === "geophysics.observation-dataset/v1" && d.version===1 && d.modality==="edi_transfer_function" && d.parser_version==="edi-strict-envelope/v1" && d.qc_verdict==="awaiting_full_tensor_qc","envelope discriminator");
  ["dataset_id","owner_id","project_id","raw_asset_id"].forEach(k=>id(d[k])); hash(d.parent_raw_sha256); integer(d.parent_raw_bytes,128,5*1048576);
  const dim=obj(d.dimensions,"frequency dimensions"); keys(dim,["frequency"],"dimensions"); integer(dim.frequency,2,512); same(d.axis_order,["frequency"],"frequency axis"); physical(d.physical_metadata,dim.frequency); source(d.source); return value as EdiDataset;
}
export function bindEdiDataset(dataset: EdiDataset, receipt: EdiDatasetReceipt) {
  for(const key of ["dataset_id","project_id","raw_asset_id","version","schema","modality","parser_version","qc_verdict"] as const)same(dataset[key],receipt[key],`envelope ${key}`);
  same(dataset.parent_raw_sha256,receipt.raw_sha256,"original hash"); same(dataset.dimensions.frequency,receipt.row_count,"declared frequency count");
}
export function validateMtParameters(value: unknown): MtInverseParameters {
  const p=obj(value,"M06 parameters"); keys(p,["qc_job_id","thickness_m","initial_ohm_m","beta","bootstrap_samples","seed"],"M06 parameters"); id(p.qc_job_id);
  const h=vector(p.thickness_m), rho=vector(p.initial_ohm_m,h.length+1); expect(h.length<=1 && h.every(v=>v>=2 && v<=4000) && rho.every(v=>v>1 && v<6000),"imposed layer bounds");
  number(p.beta); expect(p.beta>=0 && p.beta<=1,"beta bounds"); integer(p.bootstrap_samples,20,40); integer(p.seed,0,2147483647); return value as MtInverseParameters;
}
function curves(value: unknown, f: number[], sigma = false): MtCurves {
  const c=obj(value,"curves"); keys(c,["real","imag","apparent","phase",...(sigma?["sigma_real_imag_ohm"]:[])],"complex curves");
  const real=vector(c.real,f.length), imag=vector(c.imag,f.length), apparent=vector(c.apparent,f.length), phase=vector(c.phase,f.length);
  f.forEach((freq,i)=>{close(apparent[i],(real[i]**2+imag[i]**2)/(4e-7*Math.PI*2*Math.PI*freq),"apparent resistivity"); close(phase[i],Math.atan2(imag[i],real[i])*180/Math.PI,"principal phase");});
  if(sigma)vector(c.sigma_real_imag_ohm,f.length,true); return value as MtCurves;
}
function tensor(value: unknown, n: number): MtTensor {
  const t=obj(value,"tensor"); keys(t,["real","imag","sigma","rotation_deg"],"tensor");
  ["real","imag","sigma"].forEach(k=>{expect(Array.isArray(t[k]) && t[k].length===n,"frequency/electric/magnetic tensor dimensions"); (t[k] as unknown[]).forEach(row=>{expect(Array.isArray(row)&&row.length===2,"electric axis"); (row as unknown[]).forEach(v=>vector(v,2,k==="sigma"));});});
  vector(t.rotation_deg,n); return value as MtTensor;
}
export function tensorScores(t: MtTensor) {
  const n=t.real.length, score=(a:number,b:number,anti=false)=> Math.sqrt(t.real.reduce((sum,row,i)=>{
    const re=anti ? row[0][1]+row[1][0] : row[a][b], im=anti ? t.imag[i][0][1]+t.imag[i][1][0] : t.imag[i][a][b];
    const s=anti ? t.sigma[i][0][1]+t.sigma[i][1][0] : t.sigma[i][a][b]; return sum+(re**2+im**2)/s**2;
  },0)/(2*n));
  return {xx_component_wrms:score(0,0),yy_component_wrms:score(1,1),antisymmetry_conservative_wrms:score(0,1,true)};
}
function provenance(value: unknown, f: number[], p: RawPhysicalMetadata): MtProvenance {
  const d=obj(value,"parser provenance"); const n=f.length; hash(d.source_sha256); integer(d.source_bytes,128,5*1048576);
  ["source_file","parser","parser_version","preflight","sigma_definition","error_assumption","rotation_action","data_kind"].forEach(k=>text(d[k],k));
  expect(d.output_units==="ohm" && d.output_sign_convention==="+" && d.target_known===false && typeof d.synthetic==="boolean" && d.tipper_used_in_1d_inversion===false,"output conventions/null target");
  same(d.original_units,p.measurement_unit==="ohm"?"ohm":"mt","input unit provenance"); same(d.original_sign_convention,p.geometry.sign_convention,"time sign provenance"); same(d.variance_convention,p.geometry.variance_convention,"variance provenance");
  close(Number(d.units_multiplier_to_ohm),p.measurement_unit==="ohm"?1:4e-7*Math.PI*1000,"E/H unit conversion");
  const angles=vector(d.original_rotation_deg,n); angles.forEach(v=>expect(Math.abs((v-Number(p.geometry.rotation_degrees)+540)%360-180)<1e-7,"original rotation"));
  const original=vector(d.original_frequency_hz,n,true), perm=vector(d.frequency_permutation,n); expect(new Set(perm).size===n,"frequency permutation");
  perm.forEach((index,i)=>{integer(index,0,n-1); same(original[index],f[i],"original sorted frequency mapping");});
  same(d.rotation_reference,p.component_frame==="geographic ENU"?"geographic-north":null,"rotation reference"); same(d.tipper_present,(p.geometry.tensor_components as string[]).length===6,"tipper declaration"); obj(d.interpretation_arguments,"supplied interpretations"); return value as MtProvenance;
}
function parseScreen(value: unknown, f: number[], p: RawPhysicalMetadata): MtScreen {
  const s=obj(value,"M05 screen"); keys(s,["schema","id","family","source_kind","truth","methods","inversion_performed","one_d_fit_performed","one_d_inversion_eligible","interpretation","frequencies_hz","observed","tensor","compatibility","provenance","metadata"],"M05 screen");
  expect(s.schema==="inverse-earth/edi-screen/v1" && s.family==="mt" && s.truth===null && s.inversion_performed===false && s.one_d_fit_performed===false,"QC only"); keys(obj(s.methods,"QC methods"),[],"no inverse methods"); same(s.id,p.geometry.station_id,"station"); text(s.source_kind,"source kind"); text(s.interpretation,"interpretation"); same(s.frequencies_hz,f,"screen frequencies");
  const t=tensor(s.tensor,f.length), obs=obj(s.observed,"both components"); keys(obs,["xy","yx"],"components");
  (["xy","yx"] as const).forEach((key,j)=>{const c=curves(obs[key],f,true) as MtCurves & {sigma_real_imag_ohm:number[]}; f.forEach((_,i)=>{close(c.real[i],(j?-1:1)*t.real[i][j][1-j],"component real sign"); close(c.imag[i],(j?-1:1)*t.imag[i][j][1-j],"component imag sign"); same(c.sigma_real_imag_ohm[i],t.sigma[i][j][1-j],"marginal errors unchanged");});});
  const q=obj(s.compatibility,"necessary screen"); const scores=tensorScores(t); Object.entries(scores).forEach(([k,v])=>close(Number(q[k]),v,"QC score")); same(q.threshold,3,"predeclared threshold"); same(q.passes_screen,Object.values(scores).every(v=>v<=3),"necessary verdict"); same(s.one_d_inversion_eligible,q.passes_screen,"QC eligibility"); text(q.criteria,"criteria"); text(q.caveat,"caveat");
  const prov=provenance(s.provenance,f,p); same(s.source_kind,prov.synthetic?"original synthetic EDI transfer functions":"measured EDI transfer functions","source label");
  const metadata=obj(s.metadata,"station metadata"); ["header","info","mtsect","measurement_layout"].forEach(k=>obj(metadata[k],k));
  if(prov.tipper_present){const tip=obj(metadata.tipper,"ancillary tipper"); expect(tip.present===true && tip.used_in_1d_inversion===false,"ancillary only"); text(tip.raw_variance_convention,"raw tipper variance"); vector(tip.rotation_deg,f.length); const missing=vector(tip.missing_frequency_hz); const components=obj(tip.components,"tipper components"); keys(components,["X","Y"],"tipper axes");
    for(const axis of ["X","Y"]){const c=obj(components[axis],"tipper"); for(const key of ["real","imag","variance"]){expect(Array.isArray(c[key])&&c[key].length===f.length,"tipper shape"); (c[key] as unknown[]).forEach((v,i)=>{if(missing.includes(f[i]))same(v,null,"tipper missing mask"); else {number(v); if(key==="variance")expect(v>0,"tipper variance");}});}}
  } else expect(metadata.tipper===undefined,"unexpected tipper"); return value as MtScreen;
}
export function componentWrms(real: number[], imag: number[], sigma: number[], mask: boolean[]) {
  const count=mask.filter(Boolean).length; expect(count>0,"empty scoring mask"); return Math.sqrt(real.reduce((sum,re,i)=>sum+(mask[i]?(re**2+imag[i]**2)/sigma[i]**2:0),0)/(2*count));
}
const percentile=(values:number[],q:number)=>{const a=[...values].sort((x,y)=>x-y), k=(a.length-1)*q, lo=Math.floor(k); return a[lo]+(a[Math.min(lo+1,a.length-1)]-a[lo])*(k-lo);};
function inverse(value: unknown, s: MtScreen, params: MtInverseParameters): MtInverse {
  const d=obj(value,"M06 inverse"); const f=s.frequencies_hz,n=f.length,l=params.initial_ohm_m.length;
  keys(d,["schema","id","family","source_kind","component","geometry","units","data_units","frequencies","thickness","observed","sigma","active","methods","tensor","compatibility","provenance","metadata","parameters","truth","clean","evaluation_protocol"],"M06 inverse");
  expect(n>=12 && n<=64 && s.one_d_inversion_eligible && d.schema==="inverse-earth/edi-1d/v1" && d.truth===null && d.clean===null && d.component==="xy" && d.units==="ohm m" && d.data_units==="ohm" && d.family==="mt","eligible conditional inverse"); same(d.id,s.id,"inverse station"); same(d.frequencies,f,"inverse Hz"); same(d.thickness,params.thickness_m,"imposed thickness");
  for(const k of ["tensor","compatibility","provenance","metadata"] as const)same(d[k],s[k],`inverse ${k}`);
  same(d.parameters,{regularization:params.beta,bounds_ohm_m:[1,6000],component:"xy"},"inverse physics");
  const observed=curves(d.observed,f); for(const k of ["real","imag","apparent","phase"] as const)same(observed[k],s.observed.xy[k],"fit observed XY"); same(d.sigma,s.observed.xy.sigma_real_imag_ohm,"fit sigma");
  const mask=bools(d.active,n); same(mask,f.map((_,i)=>i%5!==4),"frozen holdout");
  const methods=obj(d.methods,"inverse methods"); keys(methods,["mt-lm"],"bounded TRF only"); const m=obj(methods["mt-lm"],"TRF method");
  ["name","name_es"].forEach(k=>text(m[k],k)); same(m.device,"cpu","method device"); text(d.geometry,"imposed geometry"); same(d.source_kind,"EDI transfer functions","inverse source");
  const model=vector(m.model,l,true); expect(model.every(v=>v>=1&&v<=6000),"model bounds"); const predicted=curves(m.predicted,f), expected=mtForward(model,params.thickness_m,f); for(const k of ["real","imag","apparent","phase"] as const)predicted[k].forEach((v,i)=>close(v,expected[k][i],"final forward prediction"));
  const residual=curves(m.residual,f); f.forEach((_,i)=>{close(residual.real[i],observed.real[i]-predicted.real[i],"signed real residual"); close(residual.imag[i],observed.imag[i]-predicted.imag[i],"signed imaginary residual");});
  const metrics=obj(m.metrics,"fit metrics"); Object.values(metrics).forEach(number); const sig=s.observed.xy.sigma_real_imag_ohm;
  keys(metrics,["wrms","active_component_wrms","withheld_component_wrms","initial_component_wrms","objective","data_objective","regularization_objective","other_component_wrms"],"complete metrics");
  close(Number(metrics.active_component_wrms),componentWrms(residual.real,residual.imag,sig,mask),"training WRMS"); close(Number(metrics.withheld_component_wrms),componentWrms(residual.real,residual.imag,sig,mask.map(v=>!v)),"holdout WRMS");
  close(Number(metrics.wrms),Math.SQRT2*componentWrms(residual.real,residual.imag,sig,mask.map(()=>true)),"legacy complex WRMS convention");
  close(Number(metrics.other_component_wrms),componentWrms(s.observed.yx.real.map((v,i)=>v-predicted.real[i]),s.observed.yx.imag.map((v,i)=>v-predicted.imag[i]),s.observed.yx.sigma_real_imag_ohm,mask.map(()=>true)),"unfitted other-component WRMS");
  const solver=obj(m.solver,"TRF solver"); expect(solver.algorithm==="scipy.optimize.least_squares(method=trf)" && solver.device==="cpu" && solver.dtype==="float64" && solver.scipy_cost_multiplier_to_J===2 && typeof solver.success==="boolean","real TRF contract"); same(solver.beta,params.beta,"solver beta"); same(solver.fixed_thickness_m,params.thickness_m,"solver thickness"); same(solver.bounds_ohm_m,[1,6000],"bounds"); text(solver.stop_reason,"solver stop"); integer(solver.max_nfev,1); integer(solver.nfev,1,Number(solver.max_nfev)); integer(solver.residual_calls,1); integer(solver.status); number(solver.optimality); vector(solver.initial_model,l,true);
  const frames=m.frames; expect(Array.isArray(frames)&&frames.length>0 && frames.length<=1500,"state budget"); (frames as unknown[]).forEach(row=>vector(row,l,true));
  const history=vector(m.history,(frames as unknown[]).length); const si=obj(m.state_identity,"state identity"); same(si.final_frame_index,history.length-1,"selected final frame"); same(si.predictions,"final-model","state prediction"); same((frames as unknown[]).at(-1),model,"final model frame"); integer(si.selected_iteration);
  expect(Array.isArray(m.states)&&m.states.length===history.length,"objective states"); (m.states as unknown[]).forEach((item,i)=>{const state=obj(item,"state"); same(state.frame_index,i,"frame index"); integer(state.step); text(state.kind,"state kind"); const o=obj(state.objective,"objective components"); Object.values(o).forEach(number); close(Number(o.total),Number(o.data)+Number(o.regularization),"state objective sum"); close(Number(o.total),history[i],"paired objective");});
  const diag=obj(m.identifiability,"local identifiability"); expect(["locally_resolved","unresolved"].includes(String(diag.status)),"local diagnostic status"); vector(diag.singular_values,l); integer(diag.effective_rank,0,l); integer(diag.numerical_rank,0,l); same(diag.parameter_count,l,"local parameters"); vector(diag.local_logrho_sd,l); vector(diag.weak_direction_participation,l); bools(diag.near_bound,l); vector(diag.unresolved_layers).forEach(v=>integer(v,0,l-1)); if(diag.condition_number!==null)number(diag.condition_number); text(diag.caveat,"identifiability caveat");
  const evaluation=obj(m.evaluation,"field evaluation"); expect(["unresolved","failed"].includes(String(evaluation.status)) && evaluation.model_recovery==="not_evaluated_without_independent_truth","no geological recovery claim"); expect(Array.isArray(evaluation.reason_codes)&&evaluation.reason_codes.includes("no_independent_geological_truth"),"null-truth reasons"); evaluation.reason_codes.forEach(v=>text(v,"reason"));
  ["target","criteria"].forEach(k=>text(evaluation[k],k)); same(evaluation.target_units,"ohm m","evaluation units");
  const objective=obj(m.objective,"complete objective"); text(objective.definition,"objective definition"); same(objective.beta,params.beta,"objective beta"); ["data","regularization","total"].forEach(k=>number(objective[k])); close(Number(objective.total),Number(objective.data)+Number(objective.regularization),"objective sum"); close(Number(objective.total),Number(metrics.objective),"objective metric"); close(Number(objective.data),Number(metrics.data_objective),"data metric"); close(Number(objective.regularization),Number(metrics.regularization_objective),"regularization metric");
  const tol=obj(solver.tolerance,"solver tolerances"); keys(tol,["ftol","xtol","gtol"],"tolerances"); Object.values(tol).forEach(v=>{number(v);expect(v>0,"positive tolerance");}); ["objective","residual_normalization","sigma_definition","regularization_normalization"].forEach(k=>text(solver[k],k));
  const initialPrediction=mtForward(solver.initial_model as number[],params.thickness_m,f); close(Number(metrics.initial_component_wrms),componentWrms(observed.real.map((v,i)=>v-initialPrediction.real[i]),observed.imag.map((v,i)=>v-initialPrediction.imag[i]),sig,mask),"initial training WRMS"); close(Number(objective.data),Number(metrics.active_component_wrms)**2,"mean marginal-error data objective"); close(Number(objective.regularization),params.beta*(l===1?0:(Math.log(model[1])-Math.log(model[0]))**2),"adjacent log-resistivity penalty");
  const state=obj(m.state,"selected computation"); same(state.selected_frame,history.length-1,"selected state"); same(state.selected_step,si.selected_iteration,"selected residual call"); hash(state.model_sha256); same(state.final_is_last_frame,true,"final state"); same(state.predictions_from,"selected_final","selected prediction"); ["history_quantity","model_sha256_encoding"].forEach(k=>text(state[k],k));
  const target=obj(m.target,"estimated target"); same(target.quantity,"electrical resistivity","target quantity"); same(target.units,"ohm m","target units"); ["dimensionality","provenance"].forEach(k=>text(target[k],k)); text(si.frame_quantity,"frame quantity"); text(diag.kind,"diagnostic kind"); number(diag.singular_threshold);
  const protocol=obj(d.evaluation_protocol,"frozen evaluation protocol"); same(protocol.training_mask,mask,"protocol holdout"); vector(protocol.selected_start_ohm_m,l,true); same(solver.initial_model,protocol.selected_start_ohm_m,"selected start");
  const summary=(value:unknown,layers:number)=>{const row=obj(value,"comparator"); vector(row.model_ohm_m,layers,true); ["training_objective","training_component_wrms","heldout_component_wrms"].forEach(k=>{number(row[k]);expect(row[k]>=0,"comparator metric");}); expect(typeof row.solver_success==="boolean","comparator outcome"); text(row.stop_reason,"comparator stop"); return row;};
  expect(Array.isArray(protocol.starts)&&protocol.starts.length===3,"three fixed starts"); protocol.starts.forEach(row=>{summary(row,l); vector(obj(row,"start").initial_ohm_m,l,true);});
  const successful=protocol.starts.map(v=>obj(v,"start")).filter(v=>v.solver_success); expect(successful.length>0,"successful training start"); const winner=successful.reduce((a,b)=>Number(a.training_objective)<=Number(b.training_objective)?a:b); same(winner.initial_ohm_m,protocol.selected_start_ohm_m,"training-only selection");
  summary(protocol.halfspace_baseline,1); const alternate=summary(protocol.beta_sensitivity,l); same(alternate.beta,params.beta===0?.01:params.beta<=.1?params.beta*10:params.beta/10,"predeclared beta sensitivity");
  expect(Array.isArray(protocol.thickness_sensitivity)&&protocol.thickness_sensitivity.length===(l===2?2:0),"thickness sensitivity count"); protocol.thickness_sensitivity.forEach((row,i)=>{summary(row,l); same(obj(row,"thickness").thickness_m,params.thickness_m.map(v=>v*(i===0?.8:1.2)),"predeclared thickness sensitivity");});
  ["frequency_partition","selection","uncertainty_limit"].forEach(k=>text(protocol[k],k));
  const u=obj(m.uncertainty,"conditional bootstrap"); expect(u.kind==="conditional-parametric-bootstrap" && u.units==="ohm m" && ["computed","incomplete"].includes(String(u.status)),"conditional interval kind/status"); integer(u.requested,20,40); same(u.requested,params.bootstrap_samples,"draw request"); integer(u.completed,0,Number(u.requested)); same(u.members,u.completed,"members"); same(u.seed,params.seed+1,"bootstrap child root seed"); same(u.conditioning_model,model,"conditioning model"); same(u.fixed_thickness_m,params.thickness_m,"conditioning thickness"); same(u.beta,params.beta,"conditioning beta"); same(u.bounds_ohm_m,[1,6000],"conditioning bounds"); same(u.active,mask,"conditioning mask"); same(u.sigma_per_real_component,sig,"conditioning sigma"); same(u.initial_model,solver.initial_model,"conditioning start");
  const seeds=vector(u.sample_seeds,Number(u.requested)); expect(new Set(seeds).size===seeds.length,"unique draw seeds"); seeds.forEach(v=>integer(v,0,4294967295)); const good=vector(u.successful_seeds,Number(u.completed)); expect(new Set(good).size===good.length&&good.every(v=>seeds.includes(v)),"successful seeds");
  expect(Array.isArray(u.samples)&&u.samples.length===u.completed,"actual draw models"); const samples=u.samples as number[][]; samples.forEach(row=>expect(vector(row,l,true).every(v=>v>=1&&v<=6000),"draw model bounds"));
  expect(Array.isArray(u.failures)&&u.failures.length===Number(u.requested)-Number(u.completed),"retained failed draws"); const bad=(u.failures as unknown[]).map(v=>{const row=obj(v,"failed draw"); integer(row.seed,0,4294967295); text(row.error,"failure reason"); return row.seed as number;}); expect(new Set([...bad,...good]).size===seeds.length && bad.every(v=>seeds.includes(v)),"draw outcome partition");
  const quantiles=vector(u.quantiles,2); same(u.confidence,.95,"nominal percentile span"); close(quantiles[0],.025,"lower quantile"); close(quantiles[1],.975,"upper quantile"); ["conditioning","sampling_law","interval_method","limitations","target","solver"].forEach(k=>text(u[k],k));
  if(samples.length>=20){["lower","upper","mean","std"].forEach(k=>vector(u[k],l)); for(let j=0;j<l;j++){const values=samples.map(row=>row[j]), mean=values.reduce((a,b)=>a+b,0)/values.length; close((u.lower as number[])[j],percentile(values,quantiles[0]),"percentile lower"); close((u.upper as number[])[j],percentile(values,quantiles[1]),"percentile upper"); close((u.mean as number[])[j],mean,"draw mean"); close((u.std as number[])[j],Math.sqrt(values.reduce((a,b)=>a+(b-mean)**2,0)/(values.length-1)),"draw SD");} same(u.interval_ohm_m,[u.lower,u.upper],"interval arrays");}
  else {same(u.interval_ohm_m,null,"no manufactured interval"); same(u.lower,[],"absent bounds"); same(u.upper,[],"absent bounds");}
  same(u.status,bad.length===0&&samples.length>=20?"computed":"incomplete","conditional completion status"); return value as MtInverse;
}
export function parseMtResult(value: unknown): MtResult {
  const d=obj(value,"MT result"); keys(d,["schema","job_id","dataset_id","dataset_sha256","method_id","request_sha256","parameters","raw_asset_id","raw_sha256","raw_bytes","engine_sha256","parser_sha256","forward_sha256","environment","environment_sha256","axis_order","dimensions","frequency_hz","physical_metadata","source","screen","inverse","qc_screen_sha256","truth","interpretation_limit"],"MT result");
  expect(d.schema==="geophysics.processing-result/v1" && [M05_METHOD,M06_METHOD].includes(d.method_id as typeof M05_METHOD) && d.truth===null,"MT result discriminator"); ["job_id","dataset_id","raw_asset_id"].forEach(k=>id(d[k])); ["dataset_sha256","request_sha256","raw_sha256","engine_sha256","parser_sha256","forward_sha256","environment_sha256"].forEach(k=>hash(d[k])); integer(d.raw_bytes,128,5*1048576);
  const dim=obj(d.dimensions,"dimensions"); keys(dim,["frequency"],"frequency dimension"); integer(dim.frequency,2,512); const f=vector(d.frequency_hz,dim.frequency,true); expect(f.every((v,i)=>i===0||v>f[i-1]),"ascending unique Hz"); same(d.axis_order,["frequency"],"frequency axis"); const p=physical(d.physical_metadata,f.length); source(d.source);
  const env=obj(d.environment,"environment"); keys(env,["python","packages"],"environment"); text(env.python,"Python version"); const packages=obj(env.packages,"packages"); keys(packages,["numpy","scipy","mt-metadata","pandas","matplotlib","xarray"],"scientific environment"); Object.values(packages).forEach(v=>text(v,"package version"));
  const s=parseScreen(d.screen,f,p); same(s.provenance.source_sha256,d.raw_sha256,"screen original hash"); same(s.provenance.source_bytes,d.raw_bytes,"screen original bytes"); text(d.interpretation_limit,"interpretation limit");
  if(d.method_id===M05_METHOD){keys(obj(d.parameters,"M05 params"),[],"no M05 tuning"); same(d.inverse,null,"QC has no inverse"); same(d.qc_screen_sha256,null,"no inverse admission");}
  else {hash(d.qc_screen_sha256); inverse(d.inverse,s,validateMtParameters(d.parameters));} return value as MtResult;
}
export function bindMtResult(result: MtResult, job: MtProcessingJob, dataset: EdiDataset) {
  expect(job.state==="succeeded","success-only result"); for(const k of ["job_id","dataset_id","dataset_sha256","method_id","request_sha256"] as const)same(result[k],job[k],`result ${k}`);
  same(result.parameters,job.request.parameters,"submitted parameters"); same(result.dataset_id,dataset.dataset_id,"selected dataset"); same(result.raw_asset_id,dataset.raw_asset_id,"selected original"); same(result.raw_sha256,dataset.parent_raw_sha256,"original hash"); same(result.raw_bytes,dataset.parent_raw_bytes,"original bytes"); same(job.request.raw_asset_id,result.raw_asset_id,"requested original"); same(job.request.raw_sha256,result.raw_sha256,"requested raw hash"); same(result.source,dataset.source,"unchanged source rights"); same(result.physical_metadata,dataset.physical_metadata,"physical metadata"); same(result.dimensions,dataset.dimensions,"declared dimensions"); if(job.method_id===M06_METHOD)same(result.qc_screen_sha256,job.request.qc_screen_sha256,"QC admission hash");
}
export async function verifyMtBundle(blob: Blob, job: MtProcessingJob, dataset: EdiDataset) {
  expect(job.state==="succeeded"&&blob.size>=22&&blob.size<=17*1048576,"export state/size"); const names=new Set<string>(); const files=unzipSync(new Uint8Array(await blob.arrayBuffer()),{filter:file=>{expect(["manifest.json","dataset.json","result.json"].includes(file.name)&&!names.has(file.name)&&file.compression===0&&file.size===file.originalSize&&file.originalSize<=(file.name==="manifest.json"?262144:8*1048576),"bounded unique stored ZIP members"); names.add(file.name);return true;}}); expect(names.size===3,"exact MT export members");
  const decode=(name:string)=>JSON.parse(new TextDecoder("utf-8",{fatal:true}).decode(files[name])) as unknown;
  const m=obj(decode("manifest.json"),"MT export manifest"); keys(m,["schema","dataset_id","job_id","method_id","parameters","source","environment","axes","dimensions","units","provenance","members","raw_bytes_included"],"MT manifest, not gravity"); expect(m.schema==="geophysics.processing-bundle/v1"&&m.raw_bytes_included===false,"no private raw export");
  const exported=parseEdiDataset(decode("dataset.json")), result=parseMtResult(decode("result.json")); same(exported,dataset,"unchanged exported envelope"); bindMtResult(result,job,dataset);
  if(result.inverse){const model=result.inverse.methods["mt-lm"].model, bytes=new Uint8Array(model.length*8), view=new DataView(bytes.buffer);model.forEach((value,i)=>view.setFloat64(i*8,value,true));same(await sha(bytes),result.inverse.methods["mt-lm"].state.model_sha256,"selected little-endian float64 model identity");}
  const digests=await Promise.all([sha(files["dataset.json"]),sha(files["result.json"])]); same(digests[0],job.dataset_sha256,"dataset receipt SHA"); same(digests[1],job.result_sha256,"result receipt SHA"); same(m.members,{"dataset.json":{sha256:digests[0],bytes:files["dataset.json"].length},"result.json":{sha256:digests[1],bytes:files["result.json"].length}},"original member hashes");
  for(const k of ["dataset_id","job_id","method_id","parameters","source","environment","dimensions"] as const)same(m[k],result[k],`MT manifest ${k}`); same(m.axes,["frequency"],"MT axes"); same(m.units,{frequency:"Hz",impedance:"ohm E/H",resistivity:"ohm m",thickness:"m",uncertainty:"ohm SD per real/imaginary component"},"MT units");
  same(m.provenance,{raw_sha256:result.raw_sha256,raw_bytes:result.raw_bytes,dataset_sha256:digests[0],request_sha256:job.request_sha256,engine_sha256:result.engine_sha256,parser_sha256:result.parser_sha256,forward_sha256:result.forward_sha256,environment_sha256:result.environment_sha256},"MT provenance");
  const canonicalEnv=JSON.stringify({packages:Object.fromEntries(Object.entries(result.environment.packages).sort(([a],[b])=>a.localeCompare(b))),python:result.environment.python}); same(await sha(new TextEncoder().encode(canonicalEnv)),result.environment_sha256,"environment digest"); return {manifest:m,dataset:exported,result};
}
