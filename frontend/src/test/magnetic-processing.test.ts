import { readFileSync } from "node:fs";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiClient } from "../api/client";
import { MagneticProcessingApi, parseMagneticDatasetReceipt, parseMagneticReplayJob, verifyMagneticDownload } from "../api/magnetic-processing";

const origin = "http://127.0.0.1:8876";
const fixturePath = process.env.GEOPHYSICS_MAGNETIC_BROWSER_CONTROL;
if (!fixturePath) throw new Error("Supply actual owned-custody browser-control.json; no invented complete magnetic fixture");
const actual = JSON.parse(readFileSync(fixturePath, "utf8"));
const bytes = readFileSync(actual.zip_path);
const receipt = parseMagneticDatasetReceipt(actual.receipt), job = parseMagneticReplayJob(actual.job);
const inputFixture = process.env.GEOPHYSICS_MAGNETIC_BROWSER_INPUT_CONTROL;
if (!inputFixture) throw new Error("Supply actual owned dataset/source mapping fixture");
const input = JSON.parse(readFileSync(inputFixture,"utf8"));
function client(replies: unknown[]) {
  const fetcher = vi.fn(async () => {
    const value = replies.shift();
    return value instanceof Blob ? new Response(value, {headers:{"content-type":"application/zip"}})
      : new Response(JSON.stringify(value), {headers:{"content-type":"application/json"}});
  });
  return {api: new MagneticProcessingApi(new ApiClient(origin, fetcher as typeof fetch)), fetcher};
}
afterEach(() => vi.unstubAllGlobals());

describe("actual local magnetic custody client, not nonzero scientific acceptance", () => {
  it("consumes the actual lexical input and executable closed-online mapping", async () => {
    const {api}=client([input.payload,input.mapping]);
    const inputReceipt=parseMagneticDatasetReceipt(input.receipt);
    expect((await api.dataset(inputReceipt.project_id,inputReceipt)).request_utf8).toBe(input.payload.request_utf8);
    const mapping=await api.method(inputReceipt.project_id,inputReceipt);
    expect(mapping.online_admitted).toBe(false);
  });
  it.each(["request","claim","mapping"])("refuses supplied input %s drift",async attack=>{
    const payload=structuredClone(input.payload),mapping=structuredClone(input.mapping);
    if (attack==="request") payload.request_utf8+=" ";
    if (attack==="claim") payload.geometry_plan.claims.online_admitted=true;
    if (attack==="mapping") mapping.functions.calibrate.function="pretend";
    const {api}=client([attack==="mapping"?mapping:payload]);
    const r=parseMagneticDatasetReceipt(input.receipt);
    await expect(attack==="mapping"?api.method(r.project_id,r):api.dataset(r.project_id,r)).rejects.toThrow();
  });
  it("reads genuine selected native descriptors and identical numeric ZIP", async () => {
    const {api, fetcher} = client([actual.job, actual.view, new Blob([bytes])]);
    const selected = await api.job(job.project_id, receipt, job.job_id);
    const view = await api.result(job.project_id, receipt, selected);
    expect(view.binding.generation_sha256).toBe(actual.view.binding.generation_sha256);
    expect(view.rows).toHaveLength(receipt.row_count);
    expect(Object.values(view.claims).every(x => x === false)).toBe(true);
    const blob = await api.export(job.project_id, receipt, selected);
    expect(new Uint8Array(await blob.arrayBuffer())).toEqual(new Uint8Array(bytes));
    for (const [url, request] of fetcher.mock.calls as unknown as [URL, RequestInit][]) {
      expect(String(url)).toMatch(new RegExp(`^${origin}/api/projects/${job.project_id}/jobs/`));
      expect(request.credentials).toBe("same-origin"); expect(request.cache).toBe("no-store");
    }
  });
  it("submits the physical request as exact UTF8 string with CSRF, not reconstructed floats", async () => {
    const {api, fetcher} = client([{csrf_token:"csrf"}, actual.receipt]);
    const raw = ' \n{"measurement":1.234567890123456789e-10}\n';
    const signal = new AbortController().signal;
    await api.validateAsset(job.project_id, receipt.raw_asset_id, raw, signal);
    const request = (fetcher.mock.calls as unknown as [URL, RequestInit][])[1][1];
    expect(JSON.parse(request.body as string).magnetic_request_utf8).toBe(raw);
    expect(new Headers(request.headers).get("x-csrf-token")).toBe("csrf"); expect(request.signal).toBe(signal);
  });
  it.each(["job_id", "dataset_id", "source_id", "generation_sha256", "configuration_sha256", "original_sha256"])("refuses substituted view %s", async field => {
    const changed = structuredClone(actual.view); changed.binding[field] = "changed";
    const {api} = client([changed]);
    await expect(api.result(job.project_id, receipt, job)).rejects.toThrow();
  });
  it.each(["online", "method", "generation", "request", "pointer", "unknown"])("refuses job %s drift", attack => {
    const changed = structuredClone(actual.job);
    if (attack === "online") changed.preflight.online_admitted = true;
    if (attack === "method") changed.method_id = "magnetic.invented/v1";
    if (attack === "generation") changed.request.parameters.generation_sha256 = "a".repeat(64);
    if (attack === "request") changed.request.parameters.request_sha256 = "a".repeat(64);
    if (attack === "pointer") changed.result_url = "/api/projects/foreign/jobs/foreign/result";
    if (attack === "unknown") changed.preflight.unknown = true;
    expect(() => parseMagneticReplayJob(changed)).toThrow();
  });
  it("refuses non-success before transport and wrong dataset without trusting response binding", async () => {
    const {api, fetcher} = client([]);
    const failed = {...actual.job, state:"failed", result_sha256:null, result_url:null};
    await expect(api.result(job.project_id, receipt, failed)).rejects.toThrow("non-success");
    await expect(api.export(job.project_id, {...receipt,sha256:"a".repeat(64)}, job)).rejects.toThrow("dataset hash");
    expect(fetcher).not.toHaveBeenCalled();
  });
  it("refuses exact retained ZIP hash corruption", async () => {
    const corrupt = new Uint8Array(bytes); corrupt[corrupt.length-1] ^= 1;
    await expect(verifyMagneticDownload(new Blob([corrupt]), job.result_sha256!)).rejects.toThrow("exact retained");
    await expect(verifyMagneticDownload(new Blob([bytes]), "a".repeat(64))).rejects.toThrow();
  });
  it("checks physical request hash even when all job identifiers agree", async () => {
    const changed = structuredClone(actual.job); changed.request_sha256 = "0".repeat(64);
    const {api} = client([changed]);
    await expect(api.job(job.project_id, receipt, job.job_id)).rejects.toThrow("durable request hash");
  });
  it("forwards abort and refuses a late completed response after abort", async () => {
    const controller = new AbortController();
    const fetcher = vi.fn(async () => { controller.abort(); return new Response(JSON.stringify(actual.view), {headers:{"content-type":"application/json"}}); });
    const api = new MagneticProcessingApi(new ApiClient(origin, fetcher as typeof fetch));
    await expect(api.result(job.project_id, receipt, job, controller.signal)).rejects.toMatchObject({name:"AbortError"});
    expect((fetcher.mock.calls as unknown as [URL, RequestInit][])[0][1].signal).toBe(controller.signal);
  });
  it.each(["dataset","method","job"])("refuses a late completed %s response after abort",async kind=>{
    const controller=new AbortController();
    const value=kind==="dataset"?input.payload:kind==="method"?input.mapping:actual.job;
    const fetcher=vi.fn(async()=>{controller.abort();return new Response(JSON.stringify(value),{headers:{"content-type":"application/json"}});});
    const api=new MagneticProcessingApi(new ApiClient(origin,fetcher as typeof fetch));
    const r=parseMagneticDatasetReceipt(input.receipt);
    const action=kind==="dataset"?api.dataset(r.project_id,r,controller.signal):kind==="method"?api.method(r.project_id,r,controller.signal):api.job(job.project_id,receipt,job.job_id,controller.signal);
    await expect(action).rejects.toMatchObject({name:"AbortError"});
  });
  it("rejects an unpaired surrogate before creating a dataset",async()=>{
    const {api,fetcher}=client([]);
    await expect(api.validateAsset(job.project_id,receipt.raw_asset_id,'{"source":"\ud800"}')).rejects.toThrow("exact UTF8");
    expect(fetcher).not.toHaveBeenCalled();
  });
  it("refuses an already aborted job before transport",async()=>{
    const {api,fetcher}=client([]); const controller=new AbortController(); controller.abort();
    await expect(api.job(job.project_id,receipt,job.job_id,controller.signal)).rejects.toMatchObject({name:"AbortError"});
    expect(fetcher).not.toHaveBeenCalled();
  });
});
