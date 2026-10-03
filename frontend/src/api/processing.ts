import { ApiClient } from "./client";
import {
  FLAG_METHOD, bindDataset, bindResult, parseDatasetReceipt, parseProjectDatasetReceipt, parseEligibility,
  parseFlagResult, parseGravityDataset, parseProcessingJob, parseProjectProcessingJob, processingId,
  processingObject, processingText, validateThreshold, verifyProcessingBundle,
  type DatasetReceipt, type GravityDataset, type ProcessingJob,
} from "./processing-contracts";

const root = (projectId: string) => `/api/projects/${processingId(projectId)}`;
const datasetPath = (projectId: string, datasetId: string) => `${root(projectId)}/datasets/${processingId(datasetId)}`;
const jobPath = (projectId: string, jobId: string) => `${root(projectId)}/jobs/${processingId(jobId)}`;
function identity(actual: string, expected: string, label: string) {
  if (actual !== expected) throw new Error(`Processing response disagrees with requested ${label}`);
}
function list<T>(value: unknown, key: string, parse: (value: unknown) => T): T[] {
  const wrapper = processingObject(value, key);
  if (Object.keys(wrapper).join() !== key || !Array.isArray(wrapper[key])) throw new Error(`Invalid processing ${key} list`);
  return wrapper[key].map(parse);
}
export class ProcessingApi {
  constructor(private readonly api: ApiClient) {}
  private async csrf(signal?: AbortSignal) {
    const token = await this.api.requestJson("/api/auth/csrf", value => processingObject(value, "csrf"), { signal });
    return processingText(token.csrf_token, "csrf token");
  }
  async datasets(projectId: string, signal?: AbortSignal) {
    const rows = await this.api.requestJson(`${root(projectId)}/datasets`, value => list(value, "datasets", parseProjectDatasetReceipt), { signal });
    const ids = new Set<string>();
    rows.forEach(row => { identity(row.project_id, projectId, "project"); if (ids.has(row.dataset_id)) throw new Error("Duplicate dataset receipt"); ids.add(row.dataset_id); });
    return rows;
  }
  async validateAsset(projectId: string, assetId: string, signal?: AbortSignal) {
    const receipt = await this.api.requestJson(`${root(projectId)}/datasets`, parseDatasetReceipt, { method: "POST", csrfToken: await this.csrf(signal), body: { asset_id: processingId(assetId) }, signal });
    identity(receipt.project_id, projectId, "project"); identity(receipt.raw_asset_id, assetId, "raw asset");
    return receipt;
  }
  async dataset(projectId: string, receipt: DatasetReceipt, signal?: AbortSignal) {
    identity(receipt.project_id, projectId, "project");
    const dataset = await this.api.requestJson(datasetPath(projectId, receipt.dataset_id), parseGravityDataset, { signal });
    bindDataset(dataset, receipt);
    return dataset;
  }
  async methods(projectId: string, datasetId: string, signal?: AbortSignal) {
    const eligibility = await this.api.requestJson(`${datasetPath(projectId, datasetId)}/methods`, parseEligibility, { signal });
    identity(eligibility.dataset_id, datasetId, "dataset");
    return eligibility;
  }
  async jobs(projectId: string, signal?: AbortSignal) {
    const rows = await this.api.requestJson(`${root(projectId)}/jobs`, value => list(value, "jobs", parseProjectProcessingJob), { signal });
    const ids = new Set<string>();
    rows.forEach(row => { identity(row.project_id, projectId, "project"); if (ids.has(row.job_id)) throw new Error("Duplicate job identity"); ids.add(row.job_id); });
    return rows;
  }
  async job(projectId: string, jobId: string, signal?: AbortSignal) {
    const job = await this.api.requestJson(jobPath(projectId, jobId), parseProjectProcessingJob, { signal });
    identity(job.project_id, projectId, "project"); identity(job.job_id, jobId, "job");
    return job;
  }
  async submit(projectId: string, receipt: DatasetReceipt, threshold: number, signal?: AbortSignal) {
    identity(receipt.project_id, projectId, "project");
    const body = { dataset_id: receipt.dataset_id, method_id: FLAG_METHOD, parameters: { threshold: validateThreshold(threshold) } };
    const job = await this.api.requestJson(`${root(projectId)}/jobs`, parseProcessingJob, { method: "POST", csrfToken: await this.csrf(signal), body, signal });
    identity(job.project_id, projectId, "project"); identity(job.dataset_id, receipt.dataset_id, "dataset");
    identity(job.dataset_sha256, receipt.sha256, "dataset hash");
    if (job.request.parameters.threshold !== threshold) throw new Error("Admitted threshold differs from submitted parameter");
    return job;
  }
  async cancel(projectId: string, jobId: string, signal?: AbortSignal) {
    const job = await this.api.requestJson(`${jobPath(projectId, jobId)}/cancel`, parseProjectProcessingJob, { method: "POST", csrfToken: await this.csrf(signal), signal });
    identity(job.project_id, projectId, "project"); identity(job.job_id, jobId, "job");
    return job;
  }
  async result(projectId: string, job: ProcessingJob, dataset: GravityDataset, receipt: DatasetReceipt, signal?: AbortSignal) {
    identity(job.project_id, projectId, "project"); identity(dataset.project_id, projectId, "project");
    bindDataset(dataset, receipt); identity(job.dataset_sha256, receipt.sha256, "dataset hash");
    if (job.state !== "succeeded") throw new Error("A non-success job has no result");
    const result = await this.api.requestJson(`${jobPath(projectId, job.job_id)}/result`, parseFlagResult, { signal });
    bindResult(result, job, dataset);
    return result;
  }
  async export(projectId: string, job: ProcessingJob, dataset: GravityDataset, receipt: DatasetReceipt, signal?: AbortSignal) {
    identity(job.project_id, projectId, "project"); identity(dataset.project_id, projectId, "project");
    bindDataset(dataset, receipt); identity(job.dataset_sha256, receipt.sha256, "dataset hash");
    if (job.state !== "succeeded") throw new Error("A non-success job has no export");
    const blob = await this.api.requestBlob(`${jobPath(projectId, job.job_id)}/export`, { signal });
    await verifyProcessingBundle(blob, job, dataset);
    return blob;
  }
}
