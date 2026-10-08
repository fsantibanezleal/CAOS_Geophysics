/** Closed wire/representation validation. Scientific acceptance stays server-side. */
import descriptor from './schema.json';
import qrDescriptor from './schema_qr.json';

type ObjectValue = Record<string, unknown>;
type Spec = string | unknown[];
type Registry = Record<string, Record<string, Spec>>;
const fail = (): never => { throw new Error('Magnetic survey response or request rejected'); };
export const object = (value: unknown): ObjectValue => {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) fail();
  return value as ObjectValue;
};
function closed(value: unknown, fields: string[]): ObjectValue {
  const item = object(value);
  if (Object.keys(item).sort().join('|') !== [...fields].sort().join('|')) fail();
  return item;
}
export const uuid = (value: unknown): string => {
  if (typeof value !== 'string' || !/^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/.test(value)) fail();
  return value as string;
};
export const hash = (value: unknown): string => {
  if (typeof value !== 'string' || !/^[0-9a-f]{64}$/.test(value)) fail();
  return value as string;
};
const numeric = (value: unknown, low = -Infinity, high = Infinity, integer = false): number => {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < low || value > high ||
      integer && !Number.isSafeInteger(value)) fail();
  return value as number;
};
function utc(value: unknown): string {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?Z$/.test(value) ||
      !Number.isFinite(Date.parse(value))) fail();
  const stem = (value as string).slice(0,19);
  if (new Date(Date.parse(value as string)).toISOString().slice(0,19) !== stem) fail();
  return value as string;
}
function typed(value: unknown, spec: Spec, registry: Registry, parent?: ObjectValue, depth = 0): unknown {
  if (depth > 64) fail();
  if (typeof spec === 'string' && spec.startsWith('?')) return value === null ? null : typed(value,spec.slice(1),registry,parent,depth+1);
  if (Array.isArray(spec)) {
    const [tag, item, low, high] = spec;
    if (tag === 'literal') { if (value !== item) fail(); return value; }
    if (tag === 'enum') { if (typeof value !== 'string' || !(item as string[]).includes(value)) fail(); return value; }
    if (tag === 'int') return numeric(value,item as number,low as number,true);
    if (tag === 'nullable') return value === null ? null : typed(value,item as Spec,registry,parent,depth+1);
    if (tag === 'list') {
      if (!Array.isArray(value) || value.length < (low as number) || value.length > (high as number)) fail();
      return (value as unknown[]).map(v => typed(v,item as Spec,registry,undefined,depth+1));
    }
    if (tag === 'parameters') {
      if (value === null && item) return null;
      const name = (descriptor.parameters as Record<string,string>)[String(parent?.operation)];
      if (!name) fail();
      return typed(value,name,registry,undefined,depth+1);
    }
    if (tag === 'aux_payload') {
      const name = ({navigation:'SurveyNavigation',base:'SurveyBase',calibration:'SurveyCalibration',independent_offsets:'SurveyOffsets',reference:'SurveyReference'} as Record<string,string>)[String(parent?.kind)];
      if (!name) fail();
      return typed(value,name,registry,undefined,depth+1);
    }
    if (tag === 'policy_geometry' || tag === 'policy_fit') {
      const target = parent?.policy_epoch === 'fixed_basis_v1' ? descriptor.v1 : parent?.policy_epoch === 'augmented_direct_qr_v3' ? qrDescriptor : descriptor.v2;
      return typed(value,tag === 'policy_geometry' ? 'GeometrySeal' : 'FitReceipt',target as Registry,undefined,depth+1);
    }
    fail();
  }
  if (typeof spec !== 'string') return fail();
  const table: Record<string,Spec>|undefined = registry[spec] ?? (descriptor.environment as Registry)[spec];
  if (table) {
    const item = closed(value,Object.keys(table));
    for (const [key,child] of Object.entries(table)) typed(item[key],child,registry,item,depth+1);
    if (registry === (qrDescriptor as unknown as Registry)) qrConditions(spec,item);
    return item;
  }
  if (spec === 'Bool') { if (typeof value !== 'boolean') fail(); return value; }
  if (spec === 'F64' || spec === 'Pos' || spec === 'Nonneg') {
    const result = numeric(value,spec === 'Nonneg' || spec === 'Pos' ? 0 : -Infinity);
    if (spec === 'Pos' && result === 0) fail();
    return result;
  }
  if (spec === 'Hash') return hash(value);
  if (spec === 'UTC') return utc(value);
  if (spec === 'CrossoverReason') {
    if (typeof value !== 'string' || !descriptor.reasons.includes(value)) fail();
    return value;
  }
  if (typeof value !== 'string') fail();
  if (spec === 'ID' && !/^[A-Za-z0-9_.-]{1,64}$/.test(value as string)) fail();
  else if (spec === 'Text' && (!(value as string).length || new TextEncoder().encode(value as string).length > 8192 || (value as string).includes('\0'))) fail();
  else if (spec !== 'ID' && spec !== 'Text') fail();
  return value;
}
export function parseRepresentation(name: string,value: unknown,epoch: 1|2|3): ObjectValue {
  return typed(value,name,(epoch === 1 ? descriptor.v1 : epoch === 3 ? qrDescriptor : descriptor.v2) as Registry) as ObjectValue;
}

/** Exact QR representation invariants, never a browser scientific recomputation. */
function qrConditions(name:string,v:ObjectValue) {
  if(name==='DenseCapacity') {
    const n=Number(v.rows),m=Number(v.sources),r=n+m,work=Number(v.lwork);
    if(m>n||work<2*m||v.augmented_rows!==r||v.augmented_matrix_bytes!==8*r*m||v.triangular_matrix_bytes!==8*m*m||
      v.extra_peak_bytes!==8*(4*r*m+4*m*m+8*r+16*m+work)+33554432||
      v.factorization_work_bound!==8*r*m*m+8*m*m*m)fail();
  } else if(name==='OriginalDiagnostics') {
    const denominator=Number(v.gradient_denominator),gradient=Number(v.stationarity_inf);
    if(v.objective!==Number(v.data_term)+Number(v.regularization_term)||
      denominator===0&&gradient!==0||v.stationarity_relative!==(denominator?gradient/denominator:0)||Number(v.stationarity_relative)>1e-9)fail();
  } else if(name==='EngineIdentity') {
    const pools=v.blas as ObjectValue[];
    if(pools[0].library!=='numpy.libs'||pools[1].library!=='scipy.libs'||
      pools[0].sha256!=='6547e9fb966e9773caee2755e91a8bf4d6f3a2f0eebf9646b0158f8675ea4ab5'||
      pools[1].sha256!=='6b2103f2ae4d8547998b5d188e9801fba6cb12404ae8e4bfff319e8cc1949000')fail();
  } else if(name==='QRSolve') {
    const capacity=object(v.dense_capacity);
    if(v.augmented_rows!==Number(v.rows)+Number(v.sources)||Number(v.condition_upper_bound)>=1e8||
      Number(v.triangular_diagonal_min_abs)>Number(v.triangular_diagonal_max_abs)||
      ['rows','sources','augmented_rows','lwork'].some(key=>v[key]!==capacity[key]))fail();
  } else if(name==='CandidateFit'||name==='SolveIdentity') {
    if(v.damping!==object(v.solve).damping)fail();
    if(name==='CandidateFit') {
      const verdict=object(v.verdict),gates=verdict.gates as ObjectValue[];
      if(v.rmse_nT===null||Number(v.scored)<1||verdict.overall!=='pass'||verdict.numerical_success!==true||
        (verdict.reasons as unknown[]).length!==0||gates.length!==1||gates[0].gate_id!=='solve'||gates[0].verdict!=='pass'||
        gates[0].reason!==null||typeof gates[0].evidence_sha256!=='string')fail();
    }
  } else if((name==='TableRef'||name==='TableManifest')&&['candidate_fit_qr_v3','qr_solve_identity'].includes(String(v.row_schema))) {
    if(v.rows!==(v.row_schema==='candidate_fit_qr_v3'?96:97)||String(v.table_id).length>32||
      name==='TableRef'&&object(v.manifest).name!==`table-${v.table_id}.json`)fail();
  } else if(name==='FitReceipt') {
    if(object(v.candidates).row_schema!=='candidate_fit_qr_v3'||object(v.solve_identities).row_schema!=='qr_solve_identity'||
      v.selected_damping!==object(v.solve).damping||
      (object(v.sources).shape as number[])[0]!==object(v.solve).sources)fail();
  }
}

export interface SurveyStart {
  schema: 'm03-owner-start/1'; dataset_id: string; original_asset_id: string;
  metadata_asset_id: string; request_asset_id: string; auxiliary_asset_ids: string[];
  dataset_sha256: string; original_sha256: string; metadata_sha256: string;
  request_sha256: string; auxiliary_sha256: string[];
}
export function parseStart(value: unknown): SurveyStart {
  const item = closed(value,['schema','dataset_id','original_asset_id','metadata_asset_id','request_asset_id','auxiliary_asset_ids',
    'dataset_sha256','original_sha256','metadata_sha256','request_sha256','auxiliary_sha256']);
  if (item.schema !== 'm03-owner-start/1' || !Array.isArray(item.auxiliary_asset_ids) || !Array.isArray(item.auxiliary_sha256) ||
      item.auxiliary_asset_ids.length > 16 || item.auxiliary_asset_ids.length !== item.auxiliary_sha256.length) fail();
  const ids = ['dataset_id','original_asset_id','metadata_asset_id','request_asset_id'].map(key => uuid(item[key]));
  ids.push(...(item.auxiliary_asset_ids as unknown[]).map(uuid));
  if (new Set(ids).size !== ids.length) fail();
  ['dataset_sha256','original_sha256','metadata_sha256','request_sha256'].forEach(key => hash(item[key]));
  (item.auxiliary_sha256 as unknown[]).forEach(hash);
  return structuredClone(item) as unknown as SurveyStart;
}
export interface SurveyJob {
  schema: 'm03-owner-job/1'; job_id: string; project_id: string; dataset_id: string;
  method: 'magnetic_line_survey_v1'; state: 'queued'|'running'|'succeeded'|'failed'|'cancelled';
  cancel_requested: boolean; request_sha256: string; result_sha256: string|null;
  result_bytes: number|null; error_code: string|null; created_at: string;
  started_at: string|null; finished_at: string|null;
}
export function parseJob(value: unknown): SurveyJob {
  const item = closed(value,['schema','job_id','project_id','dataset_id','method','state','cancel_requested','request_sha256',
    'result_sha256','result_bytes','error_code','created_at','started_at','finished_at']);
  if (item.schema !== 'm03-owner-job/1' || item.method !== 'magnetic_line_survey_v1' ||
      !['queued','running','succeeded','failed','cancelled'].includes(String(item.state)) || typeof item.cancel_requested !== 'boolean') fail();
  ['job_id','project_id','dataset_id'].forEach(key => uuid(item[key]));
  hash(item.request_sha256);
  if (item.result_sha256 !== null) hash(item.result_sha256);
  if (item.result_bytes !== null) numeric(item.result_bytes,1,34359738368,true);
  if (item.error_code !== null) typed(item.error_code,'ID',descriptor.v1 as Registry);
  utc(item.created_at);
  for (const key of ['started_at','finished_at']) if (item[key] !== null) utc(item[key]);
  const success = item.state === 'succeeded';
  if (success !== (item.result_sha256 !== null && item.result_bytes !== null) ||
      !success && (item.result_sha256 !== null || item.result_bytes !== null) ||
      ['succeeded','failed','cancelled'].includes(String(item.state)) && item.finished_at === null ||
      item.state === 'running' && item.started_at === null) fail();
  return item as unknown as SurveyJob;
}
export interface FileIdentity { name: string; bytes: number; sha256: string }
export interface TableRef { table_id:string;row_schema:string;rows:number;manifest:FileIdentity }
export interface CrossoverRow {
  crossover_id:string;flight_segment_id:string;tie_segment_id:string;
  easting_m:number|null;northing_m:number|null;disposition:string;reasons:string[];
  height_difference_m:number|null;time_separation_s:number|null;
}
export interface ArrayRef {
  array_id: string; role: string; dtype: 'float64'|'uint64'|'uint32'|'uint8'|'ascii64'|'ascii30';
  unit: string; shape: number[]; chunk_rows: number; manifest: FileIdentity;
  ordered_ids_sha256: string; mask_array_id: string|null;
}
export interface SurveyVerdict { overall: 'pass'|'fail'|'unresolved'; numerical_success: boolean; reasons: string[];
  gates: { gate_id: string; verdict: string; evidence_sha256: string|null; reason: string|null }[] }
export interface SurveyResult {
  schema: 'magnetic-line-survey-result/2'|'magnetic-line-survey-result/3'; policy_epoch: 'fixed_basis_v1'|'resolution_v2'|'augmented_direct_qr_v3'; run_id: string; lane: string;
  execution?:FileIdentity;
  input: { dataset_sha256: string; original: {csv_sha256:string;csv_bytes:number}; metadata: FileIdentity; arrays: ArrayRef[] };
  request: FileIdentity; geometry: { rows:number;arrays:ArrayRef[];capacity:{profile:string;scratch_bound_bytes:number;kernel_pair_bound:number} };
  inventory: {original_rows:number;retained:number;invalid:number;excluded:number;flags:ArrayRef};
  channels: {channel_id:string;kind:string;role:string;data:ArrayRef;state:ObjectValue[]}[];
  fit: {fit_count:number;selected_depth_m:number;selected_damping:number;selected_source_geometry_index?:number;
    solve?:{condition_domain:string;condition_upper_bound:number;original_diagnostics:{stationarity_relative:number}}};
  grid: {role:string;values:ArrayRef;support_mask:ArrayRef;easting_axis:ArrayRef;northing_axis:ArrayRef;
    config:{nx:number;ny:number;origin_e_m:number;origin_n_m:number;spacing_e_m:number;spacing_n_m:number;plane_upward_m:number;datum:string}}[];
  evaluation: {rmse_nT:number;signal_rms_nT:number;coverage:number;observed:ArrayRef;predicted:ArrayRef;residual:ArrayRef;verdict:SurveyVerdict};
  artifacts: {name:string;role:string;bytes:number;sha256:string|null;permission:string;disposition:string;reason:string|null}[];
  crossovers:TableRef|null;
  verdict: SurveyVerdict;
}
export function parseResult(value: unknown): SurveyResult {
  const isQr=object(value).schema==='magnetic-line-survey-result/3';
  typed(value,'SurveyResult',(isQr?qrDescriptor:descriptor.v2) as Registry);
  const result = value as SurveyResult;
  if (result.inventory.original_rows !== result.geometry.rows || result.inventory.retained + result.inventory.invalid + result.inventory.excluded !== result.geometry.rows ||
      result.fit.fit_count !== (result.policy_epoch === 'fixed_basis_v1' ? 25 : 97) && !(result.policy_epoch === 'resolution_v2' && result.fit.fit_count === 98)) fail();
  if(isQr&&(!result.execution||result.policy_epoch!=='augmented_direct_qr_v3'||result.fit.fit_count!==97))fail();
  const inspect = (item: unknown): void => {
    if (Array.isArray(item)) { item.forEach(inspect); return; }
    if (!item || typeof item !== 'object') return;
    const obj = item as ObjectValue;
    if ('array_id' in obj && 'manifest' in obj) {
      const ref = obj as unknown as ArrayRef;
      if (ref.array_id.length > 32 || ref.manifest.name !== `array-${ref.array_id}.json`) fail();
      const cells = ref.shape.reduce((a,b) => a*b,1);
      if (ref.role === 'navigation' ? ref.shape.length !== 2 || ref.shape[1] !== 3 || ref.shape[0] > 16000000 : cells > 16000000) fail();
      if (ref.role === 'grid_axis' && (ref.dtype !== 'float64' || ref.unit !== 'm' || ref.shape.length !== 1 || ref.mask_array_id !== null)) fail();
      if (ref.role === 'microlevel_transfer' && (ref.dtype !== 'float64' || ref.unit !== 'dimensionless' || ref.shape.length !== 2 || cells > 4194304 || ref.mask_array_id !== null)) fail();
      return;
    }
    Object.values(obj).forEach(inspect);
  };
  inspect(result);
  return result;
}
