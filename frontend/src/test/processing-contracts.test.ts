import { describe, expect, it } from "vitest";
import { bindDataset, bindResult, parseDatasetReceipt, parseEligibility, parseFlagResult, parseGravityDataset, parseProcessingJob, validateThreshold, verifyProcessingBundle } from "../api/processing-contracts";
import { bytes, fixture, id } from "./fixtures/processing";

describe("activated flag-only processing contracts", () => {
  it("rejects identity shape physics and fake inverse drift", () => {
    const f = fixture();
    expect(parseDatasetReceipt(f.receipt)).toEqual(f.receipt); expect(parseGravityDataset(f.dataset)).toEqual(f.dataset); expect(parseFlagResult(f.result)).toEqual(f.result);
    expect(() => bindDataset(f.dataset, {...f.receipt, raw_sha256: "d".repeat(64)})).toThrow();
    expect(() => bindResult({...f.result, request_sha256: "d".repeat(64)}, f.job, f.dataset)).toThrow();
    for (const change of [{station_ids: ["S1"]}, {sigma_mgal: [0,.1,.1,.1,.1]}, {xyz_m: Array(5).fill([0,0,0])}, {mask: [true,false,false,false,false]}, {physical_metadata: {...f.dataset.physical_metadata, horizontal_unit: "deg"}}, {residual: [0,0,0,0,0]}]) expect(() => parseGravityDataset({...f.dataset,...change})).toThrow();
    for (const change of [{model: []}, {predicted_mgal: f.dataset.observed_mgal}, {robust_score: [0,0,0,0,0]}, {statistics: {...f.result.statistics, flagged_count: 0}}, {outlier_flag: [false,false,false,false,false]}]) expect(() => parseFlagResult({...f.result,...change})).toThrow();
    const changed = {...f.dataset, sigma_mgal: [1,1,1,1,1]}; expect(() => bindResult(f.result, f.job, changed)).toThrow("unchanged sigma");
    expect(() => parseDatasetReceipt({...f.receipt,dataset_id: "../../"})).toThrow();
    for (const n of [NaN, Infinity, "6", 0, 10.1]) expect(() => validateThreshold(n)).toThrow(); expect(validateThreshold(1.5)).toBe(1.5);
    const eligibility = {dataset_id: id(3), methods: [{method_id: "future.mt/v1", eligible: true, lane: "online_processing", scope: "API says eligible"}], unavailable: [{method_id: "M01", eligible: false, lane: "not_activated", reason: "No full adapter"}]};
    expect(parseEligibility(eligibility)).toEqual(eligibility); expect(() => parseEligibility({...eligibility, unavailable: [...eligibility.unavailable,...eligibility.unavailable]})).toThrow();
  });
  it("validates state dependent job fields", () => {
    const {job} = fixture(); expect(parseProcessingJob(job)).toEqual(job);
    const queued = {...job,state: "queued", started_at: null, finished_at: null, result_sha256: null, result_url: null}; expect(parseProcessingJob(queued).state).toBe("queued");
    expect(() => parseProcessingJob({...queued,result_url: job.result_url})).toThrow();
    expect(() => parseProcessingJob({...job,request: {...job.request,project_id: id(7)}})).toThrow();
    expect(() => parseProcessingJob({...job,started_at: null})).toThrow();
    expect(() => parseProcessingJob({...job,result_url: "https://other.test/result"})).toThrow();
    expect(() => parseProcessingJob({...job,state: "failed", result_url: null, result_sha256: null})).toThrow();
    expect(parseProcessingJob({...queued,state: "cancelled",cancel_requested: true,finished_at: job.finished_at,error: {code: "user_cancelled",message: "Cancelled before execution"}}).state).toBe("cancelled");
  });
  it("verifies processing export and rejects tamper", async () => {
    const f = fixture(); expect((await verifyProcessingBundle(f.bundle(),f.job,f.dataset)).result).toEqual(f.result);
    const mutations: Record<string, Uint8Array>[] = [{"result.json": bytes({...f.result,engine_sha256: "d".repeat(64)})}, {"manifest.json": bytes({...f.manifest,raw_bytes_included: true})}, {"private/file": bytes({})}, {"dataset.json": bytes({...f.dataset,attribution: "Changed"})}];
    for (const changes of mutations) await expect(verifyProcessingBundle(f.bundle(changes),f.job,f.dataset)).rejects.toThrow();
    await expect(verifyProcessingBundle(new Blob(["Not a ZIP"]),f.job,f.dataset)).rejects.toThrow();
    await expect(verifyProcessingBundle(f.bundle(),{...f.job,state: "failed"},f.dataset)).rejects.toThrow();
  });
});
