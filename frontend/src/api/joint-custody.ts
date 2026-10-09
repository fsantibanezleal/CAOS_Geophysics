import { unzipSync } from "fflate";
import { ApiClient } from "./client";
import { importJointOutput, jointJson, jointSha, JOINT_IMPORT_CAP, type JointInspection, type Obj } from "./joint-result";

export const JOINT_NATIVE_METHOD = "joint.gravity-magnetic-native/v1";
const INDEX = "private-custody-index.json", CAP = 262144;
export type JointCustodyJob = {
  job_id: string; owner_id: string; project_id: string; dataset_id: string; dataset_sha256: string;
  method_id: typeof JOINT_NATIVE_METHOD; request_sha256: string;
  state: "queued" | "running" | "succeeded" | "failed" | "cancelled";
  cancel_requested: boolean; error_code: string | null; index_available: boolean;
  result_sha256: string | null; result_bytes: number | null;
};
export type JointCustodyIndex = {
  schema: "geophysics.joint-result-custody/v1"; job_id: string; owner_id: string; project_id: string;
  dataset_id: string; dataset_sha256: string; method_id: typeof JOINT_NATIVE_METHOD; request_sha256: string;
  state: "succeeded" | "failed" | "cancelled"; native_bytes: number;
  members: Record<string, { byte_count: number; sha256: string }>;
  scientific_acceptance: false; authenticity_verified: false; public_activation: false;
};
function assert(value: unknown, reason: string): asserts value { if (!value) throw new Error(`Native custody: ${reason}`); }
function closed(value: Obj, keys: string[]) { assert(Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key)), "closed fields"); }
function id(value: unknown): string { assert(typeof value === "string" && /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(value), "UUID"); return value; }
function sha(value: unknown): string { assert(typeof value === "string" && /^[a-f0-9]{64}$/.test(value), "digest"); return value; }
function integer(value: unknown, max: number) { assert(typeof value === "number" && Number.isSafeInteger(value) && value > 0 && value <= max, "integer cap"); return value; }
const binding = ["job_id", "owner_id", "project_id", "dataset_id", "dataset_sha256", "method_id", "request_sha256"] as const;
function validateBinding(value: Obj, owner: string, project: string) {
  for (const key of binding.slice(0, 4)) id(value[key]); sha(value.dataset_sha256); sha(value.request_sha256);
  assert(value.method_id === JOINT_NATIVE_METHOD && value.owner_id === id(owner) && value.project_id === id(project), "owned identity");
}
function object(value: unknown): Obj { assert(value && typeof value === "object" && !Array.isArray(value), "object"); return value as Obj; }
export function parseJointHistory(value: Obj, owner: string, project: string): JointCustodyJob[] {
  closed(value, ["schema", "owner_id", "project_id", "jobs"]);
  assert(value.schema === "geophysics.joint-custody-history/v1" && value.owner_id === owner && value.project_id === project, "history scope");
  assert(Array.isArray(value.jobs) && value.jobs.length <= 200, "history cap"); const ids = new Set<string>();
  return value.jobs.map(item => {
    const row = object(item); closed(row, [...binding, "state", "cancel_requested", "error_code", "index_available", "result_sha256", "result_bytes"]);
    validateBinding(row, owner, project); assert(!ids.has(id(row.job_id)), "duplicate job"); ids.add(id(row.job_id));
    assert(["queued", "running", "succeeded", "failed", "cancelled"].includes(String(row.state)) && typeof row.cancel_requested === "boolean" && typeof row.index_available === "boolean", "literal state");
    assert(row.error_code === null || typeof row.error_code === "string" && row.error_code.length <= 80, "literal failure");
    if (row.index_available) { sha(row.result_sha256); integer(row.result_bytes, CAP); assert(!["queued", "running"].includes(String(row.state)), "terminal custody only"); }
    else assert(row.result_sha256 === null && row.result_bytes === null, "absent index");
    return Object.freeze(row) as unknown as JointCustodyJob;
  });
}
export function parseJointCustodyIndex(value: Obj, job: JointCustodyJob): JointCustodyIndex {
  closed(value, ["schema", ...binding, "state", "members", "native_bytes", "scientific_acceptance", "authenticity_verified", "public_activation"]);
  validateBinding(value, job.owner_id, job.project_id);
  assert(binding.every(key => value[key] === job[key]) && value.schema === "geophysics.joint-result-custody/v1" &&
    value.state === job.state && !["queued", "running"].includes(String(value.state)), "complete job binding");
  assert(value.scientific_acceptance === false && value.authenticity_verified === false && value.public_activation === false, "claim boundary");
  const members = object(value.members), names = Object.keys(members); assert(names.length > 0 && names.length <= 1100, "member cap"); let bytes = 0;
  for (const name of names) {
    assert(/^(?:workflow\.json|failure\.json|(?:calibration|frozen|models|result|instrument|aborted)\/[a-z][a-z0-9_]{0,120}\.(?:json|npy))$/.test(name), "member grammar");
    const member = object(members[name]); closed(member, ["byte_count", "sha256"]); bytes += integer(member.byte_count, JOINT_IMPORT_CAP); sha(member.sha256);
  }
  assert(bytes === integer(value.native_bytes, JOINT_IMPORT_CAP), "whole native bytes");
  return value as unknown as JointCustodyIndex;
}

export async function inspectCustodyArchive(bytes: Uint8Array, indexBytes: Uint8Array, job: JointCustodyJob, signal?: AbortSignal): Promise<JointInspection> {
  assert(job.index_available && indexBytes.length === job.result_bytes && await jointSha(indexBytes) === job.result_sha256, "original index bytes");
  const index = parseJointCustodyIndex(jointJson(indexBytes), job), seen = new Set<string>();
  assert(bytes.length >= 22 && bytes.length <= JOINT_IMPORT_CAP, "archive transport cap");
  const files = unzipSync(bytes, { filter: file => {
    assert(!seen.has(file.name) && file.compression === 0 && file.size === file.originalSize, "unique stored originals"); seen.add(file.name);
    assert(file.name === INDEX ? file.originalSize === indexBytes.length :
      Object.hasOwn(index.members, file.name) && file.originalSize === index.members[file.name].byte_count, "closed declared archive member");
    return true;
  } });
  assert(seen.size === Object.keys(index.members).length + 1 && Object.hasOwn(files, INDEX), "complete archive inventory");
  assert(files[INDEX].length === indexBytes.length && await jointSha(files[INDEX]) === job.result_sha256, "archive index identity");
  for (const [name, member] of Object.entries(index.members)) {
    assert(files[name] && files[name].length === member.byte_count && await jointSha(files[name]) === member.sha256, "original member identity");
    if (signal?.aborted) throw new Error("Native custody cancelled");
  }
  return importJointOutput(Object.entries(index.members).map(([path, member]) => ({path, size: member.byte_count, read: async () => files[path]})), signal);
}

export class JointCustodyApi {
  constructor(private readonly api: ApiClient) {}
  async history(owner: string, project: string, signal?: AbortSignal) {
    const bytes = await this.api.requestBoundedBytes(`/api/projects/${id(project)}/joint-results`, CAP, {signal});
    return parseJointHistory(jointJson(bytes), owner, project);
  }
  async inspect(job: JointCustodyJob, signal?: AbortSignal) {
    const root = `/api/projects/${id(job.project_id)}/joint-results/${id(job.job_id)}`;
    const index = await this.api.requestBoundedBytes(root, CAP, {signal});
    assert(job.index_available && index.length === job.result_bytes && await jointSha(index) === job.result_sha256, "index receipt");
    parseJointCustodyIndex(jointJson(index), job); // Close inventory before archive download.
    const archive = await this.api.requestBoundedBytes(`${root}/export`, JOINT_IMPORT_CAP, {signal});
    return inspectCustodyArchive(archive, index, job, signal);
  }
}
