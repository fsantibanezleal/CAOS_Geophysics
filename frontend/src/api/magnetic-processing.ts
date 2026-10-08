/** Existing owner-route magnetic consumer. No online inverse is submitted. */
import { ApiClient } from "./client";
import { keys, processingId, processingObject, processingText } from "./processing-contracts";
import { verifyMagneticView, type MagneticBinding } from "./magnetic-result";

export const MAGNETIC_LOCAL_METHOD = "magnetic.survey-l2-irls-local/v1";
const hash = (v: unknown): v is string => typeof v === "string" && /^[0-9a-f]{64}$/.test(v);
const refuse = (why: string): never => { throw new Error(`Magnetic processing: ${why}`); };
const object = (v: unknown) => processingObject(v, "magnetic");
const root = (project: string) => `/api/projects/${processingId(project)}`;
const jobPath = (project: string, job: string) => `${root(project)}/jobs/${processingId(job)}`;
const equal = (a: unknown, b: unknown, why: string) => { if (a !== b) refuse(why); };

export interface MagneticDatasetReceipt {
  dataset_id: string; project_id: string; raw_asset_id: string; version: number;
  schema: "geophysics.observation-dataset/v1"; modality: "magnetic_survey";
  row_count: number; parser_version: string;
  raw_sha256: string; sha256: string; created_at: string; qc_verdict: string;
}

export function parseMagneticDatasetReceipt(raw: unknown): MagneticDatasetReceipt {
  const r = object(raw);
  keys(r, ["dataset_id", "project_id", "raw_asset_id", "version", "schema", "modality", "row_count", "parser_version", "raw_sha256", "sha256", "created_at", "qc_verdict"], "magnetic dataset receipt");
  ["dataset_id", "project_id", "raw_asset_id"].forEach(k => processingId(processingText(r[k], k)));
  if (r.schema !== "geophysics.observation-dataset/v1" || r.modality !== "magnetic_survey"
      || typeof r.parser_version !== "string" || !/^mag-survey\/v1:[0-9a-f]{64}$/.test(r.parser_version) || r.version !== 1
      || !Number.isSafeInteger(r.row_count) || Number(r.row_count) < 1 || Number(r.row_count) > 2048
      || !hash(r.raw_sha256) || !hash(r.sha256) || r.qc_verdict !== "geometry_sealed_not_numerically_inverted"
      || typeof r.created_at !== "string" || !Number.isFinite(Date.parse(r.created_at))) refuse("dataset receipt");
  return raw as MagneticDatasetReceipt;
}

export interface MagneticReplayJob {
  job_id: string; project_id: string; dataset_id: string; dataset_sha256: string;
  method_id: typeof MAGNETIC_LOCAL_METHOD; state: string; cancel_requested: boolean;
  result_sha256: string | null; result_url: string | null;
  request: { schema: "magnetic-owned-replay-request-1"; dataset_id: string; dataset_sha256: string;
    method_id: typeof MAGNETIC_LOCAL_METHOD; parameters: { request_sha256: string; generation_sha256: string; configuration_sha256: string } };
  request_sha256: string;
  preflight: { schema: "magnetic-owned-replay-custody-1"; magnetic_binding: MagneticBinding;
    source_record_id: string; request_sha256: string; online_admitted: false };
}

const bindingKeys = ["job_id", "dataset_id", "source_id", "generation_sha256", "configuration_sha256", "original_sha256"];
export function parseMagneticReplayJob(raw: unknown): MagneticReplayJob {
  const j = object(raw), req = object(j.request), params = object(req.parameters), pre = object(j.preflight), binding = object(pre.magnetic_binding);
  keys(j, ["job_id", "project_id", "dataset_id", "dataset_sha256", "method_id", "request", "request_sha256", "preflight", "state", "cancel_requested", "created_at", "started_at", "finished_at", "wall_ms", "peak_rss_bytes", "scratch_bytes", "result_sha256", "error", "result_url"], "magnetic job");
  keys(req, ["schema", "dataset_id", "dataset_sha256", "method_id", "parameters"], "magnetic replay request");
  keys(params, ["request_sha256", "generation_sha256", "configuration_sha256"], "magnetic parameters");
  keys(pre, ["schema", "magnetic_binding", "source_record_id", "request_sha256", "online_admitted"], "magnetic custody");
  keys(binding, bindingKeys, "magnetic binding");
  ["job_id", "project_id", "dataset_id"].forEach(k => processingId(processingText(j[k], k)));
  processingId(processingText(pre.source_record_id, "source record"));
  if (j.method_id !== MAGNETIC_LOCAL_METHOD || req.method_id !== MAGNETIC_LOCAL_METHOD || req.schema !== "magnetic-owned-replay-request-1"
      || pre.schema !== "magnetic-owned-replay-custody-1" || pre.online_admitted !== false
      || typeof binding.source_id !== "string" || !/^[A-Za-z0-9_.-]{1,96}$/.test(binding.source_id)
      || !["queued", "running", "succeeded", "failed", "cancelled"].includes(String(j.state)) || typeof j.cancel_requested !== "boolean"
      || !hash(j.dataset_sha256) || !hash(j.request_sha256) || Object.values(params).some(v => !hash(v))
      || ["generation_sha256", "configuration_sha256", "original_sha256"].some(k => !hash(binding[k]))) refuse("closed local replay");
  equal(req.dataset_id, j.dataset_id, "request dataset"); equal(req.dataset_sha256, j.dataset_sha256, "request dataset hash");
  equal(binding.job_id, j.job_id, "receipt job"); equal(binding.dataset_id, j.dataset_id, "receipt dataset");
  equal(params.generation_sha256, binding.generation_sha256, "generation"); equal(params.configuration_sha256, binding.configuration_sha256, "configuration");
  equal(params.request_sha256, pre.request_sha256, "physical request");
  if (j.state === "succeeded") {
    if (j.cancel_requested || !hash(j.result_sha256) || j.error !== null) refuse("successful custody");
    equal(j.result_url, `${jobPath(String(j.project_id), String(j.job_id))}/result`, "owned result URL");
  } else if (j.result_sha256 !== null || j.result_url !== null) refuse("non-success result pointer");
  return raw as MagneticReplayJob;
}

function bindJob(project: string, receipt: MagneticDatasetReceipt, job: MagneticReplayJob) {
  processingId(project); parseMagneticDatasetReceipt(receipt);
  equal(project, receipt.project_id, "project"); equal(job.project_id, project, "job project");
  equal(job.dataset_id, receipt.dataset_id, "selected dataset"); equal(job.dataset_sha256, receipt.sha256, "selected dataset hash");
  equal(job.preflight.magnetic_binding.original_sha256, receipt.raw_sha256, "original acquisition");
}

function checkAbort(signal?: AbortSignal) {
  if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
}

async function digest(bytes: Uint8Array) {
  return [...new Uint8Array(await crypto.subtle.digest("SHA-256", bytes as Uint8Array<ArrayBuffer>))].map(x => x.toString(16).padStart(2, "0")).join("");
}

async function verifyJob(raw: MagneticReplayJob) {
  const job = parseMagneticReplayJob(raw);
  const sorted = (value: unknown): unknown => value !== null && typeof value === "object"
    ? Object.fromEntries(Object.entries(value).sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0).map(([k, v]) => [k, sorted(v)])) : value;
  // This request is a closed string-only protocol, not scientific floating
  // arrays. Canonical sorting cannot round-trip/alter producer numeric bytes.
  equal(await digest(new TextEncoder().encode(JSON.stringify(sorted(job.request)))), job.request_sha256, "durable request hash");
  return job;
}

/** Hash exact downloaded ZIP bytes against independently authenticated job state.
 * The server revalidates the complete native generation for every export. This
 * check is transfer/selected-custody parity, not a browser scientific solver.
 */
export async function verifyMagneticDownload(blob: Blob, expectedSha: string) {
  if (!hash(expectedSha) || blob.size < 1 || blob.size > 128*1024**2) refuse("bounded ZIP receipt");
  const raw = new Uint8Array(await blob.arrayBuffer());
  if (raw.length < 22 || new DataView(raw.buffer).getUint32(0, true) !== 0x04034b50
      || await digest(raw) !== expectedSha) refuse("exact retained ZIP bytes");
  return blob;
}

export class MagneticProcessingApi {
  constructor(private readonly api: ApiClient) {}
  async validateAsset(project: string, asset: string, requestUtf8: string, signal?: AbortSignal) {
    if (typeof requestUtf8 !== "string" || new TextEncoder().encode(requestUtf8).length > 8388608 || !requestUtf8.length) refuse("request bytes");
    if (new TextDecoder("utf-8", {fatal:true}).decode(new TextEncoder().encode(requestUtf8)) !== requestUtf8) refuse("exact UTF8 request text");
    checkAbort(signal);
    const csrf = await this.api.requestJson("/api/auth/csrf", object, {signal});
    const receipt = await this.api.requestJson(`${root(project)}/datasets`, parseMagneticDatasetReceipt,
      {method: "POST", csrfToken: processingText(csrf.csrf_token, "CSRF"), body: {asset_id: processingId(asset), magnetic_request_utf8: requestUtf8}, signal});
    equal(receipt.project_id, project, "project"); equal(receipt.raw_asset_id, asset, "owned original");
    checkAbort(signal);
    return receipt;
  }
  async dataset(project: string, receipt: MagneticDatasetReceipt, signal?: AbortSignal) {
    checkAbort(signal);
    parseMagneticDatasetReceipt(receipt); equal(project, receipt.project_id, "project");
    const datasetBytes = await this.api.requestBoundedBytes(`${root(project)}/datasets/${processingId(receipt.dataset_id)}`, 8388608, {signal});
    checkAbort(signal);
    const payload = object(JSON.parse(new TextDecoder("utf-8", {fatal:true}).decode(datasetBytes)));
    keys(payload, "schema dataset_id version owner_id project_id raw_asset_id parent_raw_sha256 parent_raw_bytes parser_version modality dimensions axis_order request_utf8 request_sha256 geometry_plan source_record_id survey_source_id rights_decision private_storage_permission qc_verdict".split(" "), "magnetic physical dataset");
    equal(payload.schema, receipt.schema, "dataset schema"); equal(payload.modality, receipt.modality, "modality");
    equal(payload.dataset_id, receipt.dataset_id, "dataset"); equal(payload.project_id, project, "dataset project");
    equal(payload.raw_asset_id, receipt.raw_asset_id, "raw asset"); equal(payload.parent_raw_sha256, receipt.raw_sha256, "original hash");
    equal(payload.parser_version, receipt.parser_version, "immutable request parser"); equal(payload.version, receipt.version, "version");
    processingId(processingText(payload.owner_id, "owner")); processingId(processingText(payload.source_record_id, "source record"));
    const dimensions = object(payload.dimensions); keys(dimensions, ["row", "component"], "physical dimensions");
    if (dimensions.row !== receipt.row_count || ![1,3].includes(Number(dimensions.component))
        || !Number.isSafeInteger(payload.parent_raw_bytes) || Number(payload.parent_raw_bytes)<1
        || typeof payload.request_utf8 !== "string" || !hash(payload.request_sha256)
        || JSON.stringify(payload.axis_order) !== '["row","component"]'
        || payload.private_storage_permission !== "attested" || payload.rights_decision === "forbidden"
        || payload.qc_verdict !== receipt.qc_verdict) refuse("physical dataset");
    const requestUtf8 = payload.request_utf8;
    if (typeof requestUtf8 !== "string") return refuse("physical request text");
    const requestBytes = new TextEncoder().encode(requestUtf8);
    if (!requestBytes.length || requestBytes.length>8388608 || await digest(requestBytes) !== payload.request_sha256) refuse("exact physical request bytes");
    equal(receipt.parser_version, `mag-survey/v1:${payload.request_sha256}`, "physical request version");
    const claims = object(object(payload.geometry_plan).claims);
    keys(claims,["full_method_accepted","field_source_verified","geology_truth_known","online_admitted"],"geometry claims");
    if (Object.values(claims).some(v=>v!==false)) refuse("geometry is not numerical acceptance");
    checkAbort(signal);
    return payload;
  }
  async method(project: string, receipt: MagneticDatasetReceipt, signal?: AbortSignal) {
    checkAbort(signal);
    parseMagneticDatasetReceipt(receipt); equal(project,receipt.project_id,"project");
    const mapping = await this.api.requestJson(`${root(project)}/datasets/${processingId(receipt.dataset_id)}/methods`,object,{signal});
    keys(mapping,"schema dataset_id dataset_sha256 method_id lane online_admitted online_reason request_sha256 configuration_sha256 functions".split(" "),"magnetic source mapping");
    equal(mapping.dataset_id,receipt.dataset_id,"mapping dataset"); equal(mapping.dataset_sha256,receipt.sha256,"mapping dataset hash");
    if (mapping.schema!=="magnetic-owned-method-1" || mapping.method_id!==MAGNETIC_LOCAL_METHOD || mapping.lane!=="local_replay"
        || mapping.online_admitted!==false || mapping.online_reason!=="magnetic_online_not_admitted"
        || !hash(mapping.request_sha256) || !hash(mapping.configuration_sha256)
        || receipt.parser_version!==`mag-survey/v1:${mapping.request_sha256}`) refuse("closed source-backed lane");
    const functions=object(mapping.functions);
    const expected: Record<string,[string,string]> = {parse:["magnetic_survey_json.py","parse_request"],seal:["magnetic_survey.py","plan_geometry"],
      calibrate:["magnetic_calibration.py","calibrate"],local_tools:["run_magnetic_survey.py","main"],read:["magnetic_result_bundle.py","read_bundle"],export:["magnetic_result_export.py","export_zip"]};
    keys(functions,Object.keys(expected),"executable magnetic functions");
    for (const [role,[file,fn]] of Object.entries(expected)) {
      const entry=object(functions[role]); keys(entry,["file","function","sha256"],"source identity");
      if (entry.file!==file || entry.function!==fn || !hash(entry.sha256)) refuse("source mapping drift");
    }
    checkAbort(signal); return mapping;
  }
  async job(project: string, receipt: MagneticDatasetReceipt, id: string, signal?: AbortSignal) {
    checkAbort(signal);
    const job = await this.api.requestJson(jobPath(project, id), parseMagneticReplayJob, {signal});
    await verifyJob(job); bindJob(project, receipt, job); equal(job.job_id, id, "selected job"); checkAbort(signal); return job;
  }
  async result(project: string, receipt: MagneticDatasetReceipt, job: MagneticReplayJob, signal?: AbortSignal) {
    checkAbort(signal);
    await verifyJob(job); bindJob(project, receipt, job);
    if (job.state !== "succeeded") refuse("non-success selected job");
    const raw = await this.api.requestJson(`${jobPath(project, job.job_id)}/result`, value => value, {signal});
    if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
    const view = await verifyMagneticView(raw, job.preflight.magnetic_binding);
    if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
    return view;
  }
  async export(project: string, receipt: MagneticDatasetReceipt, job: MagneticReplayJob, signal?: AbortSignal) {
    checkAbort(signal);
    await verifyJob(job); bindJob(project, receipt, job);
    const expectedSha = job.result_sha256;
    if (job.state !== "succeeded" || expectedSha === null) return refuse("non-success export");
    const bytes = await this.api.requestBoundedBytes(`${jobPath(project, job.job_id)}/export`, 128*1024**2, {signal});
    checkAbort(signal);
    const blob = new Blob([bytes as Uint8Array<ArrayBuffer>], {type:"application/zip"});
    const verified = await verifyMagneticDownload(blob, expectedSha);
    if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
    return verified;
  }
}
