/** The activated processing API; deliberately separate from the future solver contracts. */
import { unzipSync } from "fflate";
import { rawPhysical, type RawPhysicalMetadata, type RightsDecision } from "./contracts";

export const FLAG_METHOD = "gravity.station-outlier-flags/v1" as const;
export const M05_METHOD = "mt.edi-full-tensor-qc/v1" as const;
export const M06_METHOD = "mt.edi-fixed-thickness-trf/v1" as const;
export type ProcessingState = "queued" | "running" | "succeeded" | "failed" | "cancelled";
export interface DatasetReceipt {
  dataset_id: string; project_id: string; raw_asset_id: string; version: 1;
  schema: "geophysics.observation-dataset/v1"; modality: "gravity_station";
  row_count: number; parser_version: "gravity-station-csv/v1"; raw_sha256: string;
  sha256: string; created_at: string; qc_verdict: "parsed_for_flag_qc_only";
}
export interface GravityDataset {
  schema: "geophysics.observation-dataset/v1"; dataset_id: string; version: 1;
  owner_id: string; project_id: string; raw_asset_id: string; parent_raw_sha256: string;
  parser_version: "gravity-station-csv/v1"; modality: "gravity_station";
  dimensions: { station: number }; axis_order: ["station"]; station_ids: string[];
  xyz_m: [number, number, number][]; observed_mgal: number[]; sigma_mgal: number[];
  uncertainty_kind: "per_station_standard_deviation"; mask: false[]; missing_reasons: null[];
  physical_metadata: RawPhysicalMetadata; correction_history: [];
  qc_verdict: "parsed_for_flag_qc_only"; rights_decision: RightsDecision;
  rights_statement: string; attribution: string;
}
export type EdiDatasetReceipt = Omit<DatasetReceipt, "modality" | "parser_version" | "qc_verdict"> & {
  modality: "edi_transfer_function"; parser_version: "edi-strict-envelope/v1"; qc_verdict: "awaiting_full_tensor_qc";
};
export type ProjectDatasetReceipt = DatasetReceipt | EdiDatasetReceipt;
export const isGravityReceipt = (receipt: ProjectDatasetReceipt): receipt is DatasetReceipt => receipt.modality === "gravity_station";
export interface MethodEligibility {
  dataset_id: string;
  methods: { method_id: string; eligible: true; lane: string; scope: string; qc_job_id?: string }[];
  unavailable: { method_id: string; eligible: false; lane: string; reason: string }[];
}
export interface ProcessingRequest {
  schema: "geophysics.processing-request/v1"; job_id: string; project_id: string;
  dataset_id: string; dataset_sha256: string; method_id: typeof FLAG_METHOD;
  parameters: { threshold: number };
}
export interface ProcessingJob {
  job_id: string; project_id: string; dataset_id: string; dataset_sha256: string;
  method_id: typeof FLAG_METHOD; request: ProcessingRequest; request_sha256: string;
  preflight: { estimated_memory_bytes: number; memory_limit_bytes: number; scratch_limit_bytes: number; wall_limit_seconds: number };
  state: ProcessingState; cancel_requested: boolean; created_at: string;
  started_at: string | null; finished_at: string | null; wall_ms: number | null;
  peak_rss_bytes: number | null; scratch_bytes: number | null; result_sha256: string | null;
  error: { code: string; message: string } | null; result_url: string | null;
}
export interface FlagResult {
  schema: "geophysics.processing-result/v1"; job_id: string; dataset_id: string;
  dataset_sha256: string; method_id: typeof FLAG_METHOD; request_sha256: string;
  engine_sha256: string; parameters: { threshold: number }; axis_order: ["station"];
  dimensions: { station: number }; station_ids: string[]; xyz_m: [number, number, number][];
  observed_mgal: number[]; sigma_mgal: number[]; outlier_flag: boolean[]; robust_score: number[];
  statistics: { median_mgal: number; mad_mgal: number; scaled_mad_mgal: number; flagged_count: number };
  uncertainty_kind: "per_station_standard_deviation"; physical_metadata: RawPhysicalMetadata;
  rights_decision: RightsDecision; rights_statement: string;
  correction_history: [{ method_id: typeof FLAG_METHOD; parameters: { threshold: number }; effect: "flag_only; observations and uncertainty unchanged" }];
  interpretation_limit: string;
}
export interface MtInverseParameters {
  qc_job_id: string; thickness_m: number[]; initial_ohm_m: number[]; beta: number; bootstrap_samples: number; seed: number;
}
export type MtProcessingJob = Omit<ProcessingJob, "method_id" | "request" | "preflight"> & {
  method_id: typeof M05_METHOD | typeof M06_METHOD;
  request: Omit<ProcessingRequest, "method_id" | "parameters"> & {
    method_id: typeof M05_METHOD | typeof M06_METHOD; parameters: Record<string, never> | MtInverseParameters;
    raw_asset_id: string; raw_sha256: string; qc_screen_sha256?: string;
  };
  preflight: ProcessingJob["preflight"] & {estimated_scratch_bytes: number};
};
export type ProjectProcessingJob = ProcessingJob | MtProcessingJob;
export const isFlagJob = (job: ProjectProcessingJob): job is ProcessingJob => job.method_id === FLAG_METHOD;

function fail(context: string): never { throw new Error(`Processing contract rejected: ${context}`); }
export function processingObject(value: unknown, context: string): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) fail(`${context}: expected object`);
  return value as Record<string, unknown>;
}
export function keys(value: Record<string, unknown>, expected: string[], context: string) {
  if (Object.keys(value).sort().join(",") !== [...expected].sort().join(",")) fail(`${context}: unexpected or missing fields`);
}
export function processingText(value: unknown, context: string): string {
  if (typeof value !== "string" || !value.trim()) fail(`${context}: expected text`);
  return value;
}
export function processingId(value: unknown): string {
  const id = processingText(value, "identity");
  if (!/^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(id)) fail("identity: expected UUID");
  return id;
}
export function hash(value: unknown) {
  if (typeof value !== "string" || !/^[0-9a-f]{64}$/.test(value)) fail("expected SHA-256");
}
export function number(value: unknown): asserts value is number {
  if (typeof value !== "number" || !Number.isFinite(value)) fail("expected finite number");
}
export function integer(value: unknown, min = 0, max = Number.MAX_SAFE_INTEGER): asserts value is number {
  number(value);
  if (!Number.isSafeInteger(value) || value < min || value > max) fail("integer out of range");
}
function timestamp(value: unknown) {
  const text = processingText(value, "timestamp");
  if (!/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)$/.test(text) || !Number.isFinite(Date.parse(text))) fail("timestamp needs timezone");
}
export function same(a: unknown, b: unknown, context: string) {
  // Physical metadata object key order is not a semantic property.
  if (Array.isArray(a) && Array.isArray(b)) {
    if (a.length !== b.length) fail(context);
    a.forEach((item, i) => same(item, b[i], context));
  } else if (a && b && typeof a === "object" && typeof b === "object") {
    const first = a as Record<string, unknown>, second = b as Record<string, unknown>;
    if (Object.keys(first).sort().join() !== Object.keys(second).sort().join()) fail(context);
    Object.keys(first).forEach(key => same(first[key], second[key], context));
  } else if (a !== b) fail(context);
}
function rights(data: Record<string, unknown>) {
  if (!["mirror", "provider-link-only", "derivative-only"].includes(String(data.rights_decision))) fail("rights decision");
  processingText(data.rights_statement, "rights statement");
}
function stationArrays(data: Record<string, unknown>): number {
  const dimensions = processingObject(data.dimensions, "dimensions");
  keys(dimensions, ["station"], "dimensions"); integer(dimensions.station, 4, 4096);
  const count = dimensions.station;
  same(data.axis_order, ["station"], "station axis order");
  for (const key of ["station_ids", "xyz_m", "observed_mgal", "sigma_mgal"]) {
    if (!Array.isArray(data[key]) || data[key].length !== count) fail(`${key}: station shape`);
  }
  const ids = data.station_ids as unknown[];
  ids.forEach(id => processingText(id, "station ID"));
  if (new Set(ids).size !== count) fail("duplicate station ID");
  const coordinates = data.xyz_m as unknown[];
  coordinates.forEach(point => {
    if (!Array.isArray(point) || point.length !== 3) fail("XYZ shape");
    point.forEach(number);
  });
  if (new Set(coordinates.map(point => JSON.stringify(point))).size !== count) fail("duplicate XYZ");
  (data.observed_mgal as unknown[]).forEach(number);
  (data.sigma_mgal as unknown[]).forEach(sigma => { number(sigma); if (sigma <= 0) fail("sigma must be positive mGal"); });
  if (data.uncertainty_kind !== "per_station_standard_deviation") fail("uncertainty kind");
  const physical = rawPhysical(data.physical_metadata);
  if (physical.coordinate_reference !== "epsg" || physical.epsg === null || physical.axis_order !== "xy" ||
      physical.horizontal_unit !== "m" || physical.vertical_unit !== "m" || physical.measurement_unit !== "mGal") fail("gravity physical reference or units");
  const cols = ["station_id_column", "x_column", "y_column", "z_column", "value_column", "sigma_column"].map(key => processingText(physical.geometry[key], key));
  if (new Set(cols).size !== 6) fail("six distinct gravity columns");
  rights(data);
  return count;
}
export function validateThreshold(value: unknown): number {
  number(value);
  if (value < 1 || value > 10) fail("threshold must be in [1,10]");
  return value;
}
function parameters(value: unknown) {
  const params = processingObject(value, "parameters"); keys(params, ["threshold"], "parameters"); validateThreshold(params.threshold);
}
export function parseProjectDatasetReceipt(value: unknown): ProjectDatasetReceipt {
  const data = processingObject(value, "dataset receipt");
  keys(data, ["dataset_id", "project_id", "raw_asset_id", "version", "schema", "modality", "row_count", "parser_version", "raw_sha256", "sha256", "created_at", "qc_verdict"], "dataset receipt");
  for (const key of ["dataset_id", "project_id", "raw_asset_id"]) processingId(data[key]);
  if (data.schema !== "geophysics.observation-dataset/v1" || data.version !== 1) fail("dataset receipt schema/version");
  if (data.modality === "gravity_station" && data.parser_version === "gravity-station-csv/v1" && data.qc_verdict === "parsed_for_flag_qc_only") integer(data.row_count, 4, 4096);
  else if (data.modality === "edi_transfer_function" && data.parser_version === "edi-strict-envelope/v1" && data.qc_verdict === "awaiting_full_tensor_qc") integer(data.row_count, 2, 512);
  else fail("dataset receipt modality/parser/verdict");
  hash(data.raw_sha256); hash(data.sha256); timestamp(data.created_at);
  return value as ProjectDatasetReceipt;
}
export function parseDatasetReceipt(value: unknown): DatasetReceipt {
  const receipt = parseProjectDatasetReceipt(value);
  if (!isGravityReceipt(receipt)) fail("EDI envelope is not parsed gravity");
  return receipt;
}
export function parseGravityDataset(value: unknown): GravityDataset {
  const data = processingObject(value, "dataset");
  keys(data, ["schema", "dataset_id", "version", "owner_id", "project_id", "raw_asset_id", "parent_raw_sha256", "parser_version", "modality", "dimensions", "axis_order", "station_ids", "xyz_m", "observed_mgal", "sigma_mgal", "uncertainty_kind", "mask", "missing_reasons", "physical_metadata", "correction_history", "qc_verdict", "rights_decision", "rights_statement", "attribution"], "dataset");
  if (data.schema !== "geophysics.observation-dataset/v1" || data.version !== 1 || data.modality !== "gravity_station" || data.parser_version !== "gravity-station-csv/v1" || data.qc_verdict !== "parsed_for_flag_qc_only") fail("dataset schema/verdict");
  for (const key of ["dataset_id", "owner_id", "project_id", "raw_asset_id"]) processingId(data[key]);
  hash(data.parent_raw_sha256); processingText(data.attribution, "attribution");
  const count = stationArrays(data);
  same(data.mask, Array(count).fill(false), "flag QC input mask");
  same(data.missing_reasons, Array(count).fill(null), "flag QC missingness");
  same(data.correction_history, [], "input correction history");
  return value as GravityDataset;
}
export function bindDataset(dataset: GravityDataset, receipt: DatasetReceipt) {
  for (const key of ["dataset_id", "project_id", "raw_asset_id", "version", "parser_version", "modality", "qc_verdict"] as const)
    same(dataset[key], receipt[key], `dataset receipt ${key}`);
  same(dataset.parent_raw_sha256, receipt.raw_sha256, "parent raw hash");
  same(dataset.dimensions.station, receipt.row_count, "receipt station count");
}
export function parseEligibility(value: unknown): MethodEligibility {
  const data = processingObject(value, "eligibility"); keys(data, ["dataset_id", "methods", "unavailable"], "eligibility"); processingId(data.dataset_id);
  const ids = new Set<string>();
  for (const [key, eligible] of [["methods", true], ["unavailable", false]] as const) {
    if (!Array.isArray(data[key])) fail("method list");
    for (const item of data[key]) {
      const row = processingObject(item, "method");
      const qc = eligible && row.method_id === M06_METHOD;
      keys(row, ["method_id", "eligible", "lane", eligible ? "scope" : "reason", ...(qc ? ["qc_job_id"] : [])], "method");
      if (qc) processingId(row.qc_job_id);
      const id = processingText(row.method_id, "method ID");
      if (ids.has(id) || row.eligible !== eligible) fail("duplicate or contradictory eligibility");
      ids.add(id); processingText(row.lane, "method lane"); processingText(row[eligible ? "scope" : "reason"], "method reason");
      if (id === FLAG_METHOD && eligible && row.lane !== "online_processing") fail("gravity method lane");
    }
  }
  return value as MethodEligibility;
}
export function parseProjectProcessingJob(value: unknown): ProjectProcessingJob {
  const data = processingObject(value, "job");
  keys(data, ["job_id", "project_id", "dataset_id", "dataset_sha256", "method_id", "request", "request_sha256", "preflight", "state", "cancel_requested", "created_at", "started_at", "finished_at", "wall_ms", "peak_rss_bytes", "scratch_bytes", "result_sha256", "error", "result_url"], "job");
  for (const key of ["job_id", "project_id", "dataset_id"]) processingId(data[key]);
  hash(data.dataset_sha256); hash(data.request_sha256);
  if (!new Set<string>([FLAG_METHOD,M05_METHOD,M06_METHOD]).has(String(data.method_id))) fail("unsupported job method version");
  const mt = data.method_id !== FLAG_METHOD, inverse = data.method_id === M06_METHOD;
  const request = processingObject(data.request, "request");
  keys(request, ["schema", "job_id", "project_id", "dataset_id", "dataset_sha256", "method_id", "parameters", ...(mt ? ["raw_asset_id","raw_sha256"] : []), ...(inverse ? ["qc_screen_sha256"] : [])], "request");
  if (request.schema !== "geophysics.processing-request/v1") fail("request schema");
  for (const key of ["job_id", "project_id", "dataset_id", "dataset_sha256", "method_id"]) same(request[key], data[key], `request ${key}`);
  if (!mt) parameters(request.parameters);
  else {
    processingId(request.raw_asset_id); hash(request.raw_sha256);
    const params = processingObject(request.parameters, "MT parameters");
    if (!inverse) keys(params, [], "M05 has no inverse parameters");
    else {
      hash(request.qc_screen_sha256);
      keys(params,["qc_job_id","thickness_m","initial_ohm_m","beta","bootstrap_samples","seed"],"M06 parameters");
      processingId(params.qc_job_id); number(params.beta);
      if (params.beta < 0 || params.beta > 1) fail("M06 beta bounds");
      integer(params.bootstrap_samples,20,40); integer(params.seed,0,2147483647);
      if (!Array.isArray(params.thickness_m) || params.thickness_m.length > 1 || !Array.isArray(params.initial_ohm_m) || params.initial_ohm_m.length !== params.thickness_m.length+1) fail("M06 imposed layer shape");
      params.thickness_m.forEach(v => {number(v); if (v < 2 || v > 4000) fail("M06 imposed thickness bounds");});
      params.initial_ohm_m.forEach(v => {number(v); if (v <= 1 || v >= 6000) fail("M06 initial resistivity bounds");});
    }
  }
  const preflight = processingObject(data.preflight, "preflight");
  keys(preflight, ["estimated_memory_bytes", "memory_limit_bytes", "scratch_limit_bytes", "wall_limit_seconds", ...(mt ? ["estimated_scratch_bytes"] : [])], "preflight");
  Object.values(preflight).forEach(value => integer(value, 1));
  if (Number(preflight.estimated_memory_bytes) > Number(preflight.memory_limit_bytes)) fail("admitted memory estimate exceeds ceiling");
  if (mt && Number(preflight.estimated_scratch_bytes) > Number(preflight.scratch_limit_bytes)) fail("admitted scratch estimate exceeds ceiling");
  if (!["queued", "running", "succeeded", "failed", "cancelled"].includes(String(data.state)) || typeof data.cancel_requested !== "boolean") fail("job state");
  timestamp(data.created_at);
  for (const key of ["started_at", "finished_at"]) if (data[key] !== null) { timestamp(data[key]); if (Date.parse(data[key] as string) < Date.parse(data.created_at as string)) fail("job timestamp order"); }
  if (data.started_at !== null && data.finished_at !== null && Date.parse(data.finished_at as string) < Date.parse(data.started_at as string)) fail("job timestamp order");
  for (const key of ["wall_ms", "peak_rss_bytes", "scratch_bytes"]) if (data[key] !== null) integer(data[key]);
  const terminal = !["queued", "running"].includes(String(data.state));
  if (terminal !== (data.finished_at !== null) || (data.state === "queued" && data.started_at !== null) || (["running", "succeeded"].includes(String(data.state)) && data.started_at === null)) fail("state/timestamp mismatch");
  if (data.state === "succeeded") {
    hash(data.result_sha256);
    if (data.error !== null || data.result_url !== `/api/projects/${data.project_id}/jobs/${data.job_id}/result`) fail("success result path/error");
  } else if (data.result_sha256 !== null || data.result_url !== null) fail("non-success result present");
  if (["failed", "cancelled"].includes(String(data.state))) {
    const error = processingObject(data.error, "job error"); keys(error, ["code", "message"], "job error"); processingText(error.code, "error code"); processingText(error.message, "error message");
  } else if (data.error !== null) fail("non-failure error present");
  return value as ProjectProcessingJob;
}
export function parseProcessingJob(value: unknown): ProcessingJob {
  const job = parseProjectProcessingJob(value);
  if (!isFlagJob(job)) fail("MT job requires its own QC/candidate result and bundle adapter");
  return job;
}
const median = (values: number[]) => { const sorted = [...values].sort((a, b) => a - b), n = sorted.length; return n % 2 ? sorted[(n - 1) / 2] : (sorted[n / 2 - 1] + sorted[n / 2]) / 2; };
const near = (a: number, b: number) => Math.abs(a - b) <= 1e-12 * Math.max(1, Math.abs(a), Math.abs(b));
export function parseFlagResult(value: unknown): FlagResult {
  const data = processingObject(value, "result");
  keys(data, ["schema", "job_id", "dataset_id", "dataset_sha256", "method_id", "request_sha256", "engine_sha256", "parameters", "axis_order", "dimensions", "station_ids", "xyz_m", "observed_mgal", "sigma_mgal", "outlier_flag", "robust_score", "statistics", "uncertainty_kind", "physical_metadata", "rights_decision", "rights_statement", "correction_history", "interpretation_limit"], "result");
  if (data.schema !== "geophysics.processing-result/v1" || data.method_id !== FLAG_METHOD) fail("result schema/method");
  processingId(data.job_id); processingId(data.dataset_id);
  for (const key of ["dataset_sha256", "request_sha256", "engine_sha256"]) hash(data[key]);
  parameters(data.parameters);
  const count = stationArrays(data);
  for (const key of ["outlier_flag", "robust_score"]) if (!Array.isArray(data[key]) || data[key].length !== count) fail(`${key}: shape`);
  const flags = data.outlier_flag as unknown[]; if (flags.some(flag => typeof flag !== "boolean")) fail("flag type");
  const scores = data.robust_score as unknown[]; scores.forEach(score => { number(score); if (score < 0) fail("negative robust score"); });
  const stats = processingObject(data.statistics, "statistics");
  keys(stats, ["median_mgal", "mad_mgal", "scaled_mad_mgal", "flagged_count"], "statistics");
  Object.values(stats).forEach(number); integer(stats.flagged_count, 0, count);
  const values = data.observed_mgal as number[], center = median(values), mad = median(values.map(value => Math.abs(value - center))), scale = 1.4826 * mad;
  if (!(scale > 0) || !near(Number(stats.median_mgal), center) || !near(Number(stats.mad_mgal), mad) || !near(Number(stats.scaled_mad_mgal), scale) || stats.flagged_count !== flags.filter(Boolean).length) fail("QC statistics mismatch");
  const threshold = (data.parameters as { threshold: number }).threshold;
  values.forEach((observation, i) => {
    const expected = Math.abs(observation - center) / scale;
    if (!near(Number(scores[i]), expected) || flags[i] !== (expected > threshold)) fail("returned flag/score semantics mismatch");
  });
  same(data.correction_history, [{ method_id: FLAG_METHOD, parameters: data.parameters, effect: "flag_only; observations and uncertainty unchanged" }], "flag-only lineage");
  processingText(data.interpretation_limit, "interpretation limit");
  return value as FlagResult;
}
export function bindResult(result: FlagResult, job: ProcessingJob, dataset: GravityDataset) {
  if (job.state !== "succeeded") fail("result for non-success job");
  same(result.job_id, job.job_id, "result job"); same(result.dataset_id, job.dataset_id, "result dataset");
  same(result.dataset_id, dataset.dataset_id, "selected dataset"); same(result.dataset_sha256, job.dataset_sha256, "result dataset hash");
  same(result.request_sha256, job.request_sha256, "result request hash"); same(result.parameters, job.request.parameters, "result submitted parameters");
  for (const key of ["station_ids", "xyz_m", "observed_mgal", "sigma_mgal", "axis_order", "dimensions", "uncertainty_kind", "physical_metadata", "rights_decision", "rights_statement"] as const) same(result[key], dataset[key], `unchanged ${key}`);
}
export async function sha(bytes: Uint8Array): Promise<string> {
  const buffer = Uint8Array.from(bytes).buffer;
  return Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", buffer)), byte => byte.toString(16).padStart(2, "0")).join("");
}
export async function verifyProcessingBundle(blob: Blob, job: ProcessingJob, dataset: GravityDataset) {
  if (job.state !== "succeeded" || blob.size > 17 * 1024 * 1024 || blob.size < 22) fail("export state/size");
  const names = new Set<string>();
  const members = unzipSync(new Uint8Array(await blob.arrayBuffer()), { filter: file => {
    if (!["manifest.json", "dataset.json", "result.json"].includes(file.name) || names.has(file.name) || file.compression !== 0 || file.size !== file.originalSize || file.originalSize > (file.name === "manifest.json" ? 256 * 1024 : 8 * 1024 * 1024)) fail("export member bounds or identity");
    names.add(file.name); return true;
  } });
  if (names.size !== 3) fail("export requires exactly three members");
  const decode = (name: string) => JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(members[name])) as unknown;
  const manifest = processingObject(decode("manifest.json"), "export manifest");
  keys(manifest, ["schema", "dataset_id", "job_id", "method_id", "parameters", "rights_decision", "rights_statement", "axes", "dimensions", "units", "provenance", "members", "raw_bytes_included"], "export manifest");
  if (manifest.schema !== "geophysics.processing-bundle/v1" || manifest.raw_bytes_included !== false) fail("export schema/raw bytes");
  const exportedDataset = parseGravityDataset(decode("dataset.json")), result = parseFlagResult(decode("result.json"));
  same(exportedDataset, dataset, "exported dataset changed"); bindResult(result, job, dataset);
  const digests = await Promise.all([sha(members["dataset.json"]), sha(members["result.json"])]);
  same(manifest.members, { "dataset.json": { sha256: digests[0], bytes: members["dataset.json"].length }, "result.json": { sha256: digests[1], bytes: members["result.json"].length } }, "export member hashes");
  same(digests[0], job.dataset_sha256, "export dataset receipt hash"); same(digests[1], job.result_sha256, "export result receipt hash");
  for (const key of ["dataset_id", "job_id", "method_id", "parameters", "rights_decision", "rights_statement"] as const) same(manifest[key], result[key], `export ${key}`);
  same(manifest.axes, dataset.axis_order, "export axes"); same(manifest.dimensions, dataset.dimensions, "export dimensions");
  same(manifest.units, { position: "m", observation: "mGal", uncertainty: "mGal" }, "export units");
  same(manifest.provenance, { raw_sha256: dataset.parent_raw_sha256, dataset_sha256: digests[0], request_sha256: job.request_sha256, engine_sha256: result.engine_sha256 }, "export provenance");
  return { manifest, dataset: exportedDataset, result };
}
