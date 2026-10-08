import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
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
const datasetPath = input.dataset_bytes_path ?? process.env.GEOPHYSICS_MAGNETIC_BROWSER_DATASET_BYTES;
if (!datasetPath) throw new Error("Supply retained Python-produced dataset body; never JS reserialization");
const datasetBytes = new Uint8Array(readFileSync(datasetPath));
if (createHash("sha256").update(datasetBytes).digest("hex") !== input.receipt.sha256)
  throw new Error("Retained dataset fixture bytes differ from authenticated receipt");
function client(replies: unknown[]) {
  const fetcher = vi.fn(async () => {
    const value = replies.shift();
    return value instanceof Uint8Array ? new Response(new Uint8Array(value), {headers:{"content-type":"application/json"}})
      : value instanceof Blob ? new Response(value, {headers:{"content-type":"application/zip"}})
      : new Response(JSON.stringify(value), {headers:{"content-type":"application/json"}});
  });
  return {api: new MagneticProcessingApi(new ApiClient(origin, fetcher as typeof fetch)), fetcher};
}
afterEach(() => vi.unstubAllGlobals());

describe("actual local magnetic custody client, not nonzero scientific acceptance", () => {
  function streamed(kind: "ZIP" | "dataset", stream: ReadableStream<Uint8Array>, headers: Record<string,string> = {}, signal?: AbortSignal) {
    const transport = vi.fn(async () => new Response(stream, {headers}));
    const api = new MagneticProcessingApi(new ApiClient(origin, transport as typeof fetch));
    const r = parseMagneticDatasetReceipt(input.receipt);
    return kind === "ZIP" ? api.export(job.project_id, receipt, job, signal) : api.dataset(r.project_id, r, signal);
  }
  it.each(["ZIP", "dataset"] as const)("bounds %s before Blob/JSON allocation for bad declared lengths", async kind => {
    for (const length of ["bad", "-1", String((kind === "ZIP" ? 128 : 8)*1024**2+1)]) {
      const cancel = vi.fn();
      const stream = new ReadableStream<Uint8Array>({cancel}, {highWaterMark:0});
      await expect(streamed(kind, stream, {"Content-Length":length})).rejects.toThrow("declared byte cap");
      expect(cancel).toHaveBeenCalledOnce();
    }
  });
  it.each(["ZIP", "dataset"] as const)("cancels %s streamed overflow before aggregate allocation", async kind => {
    // Reuse one bounded chunk; no oversized source buffer/Blob is allocated.
    const chunk = new Uint8Array(1024**2), cancel = vi.fn(); let pulls = 0;
    const maximumMiB = kind === "ZIP" ? 128 : 8;
    const stream = new ReadableStream<Uint8Array>({pull(controller) {pulls++; controller.enqueue(chunk);}, cancel}, {highWaterMark:0});
    await expect(streamed(kind, stream)).rejects.toThrow("byte cap");
    expect(pulls).toBe(maximumMiB+1); expect(cancel).toHaveBeenCalledOnce();
  });
  it.each(["ZIP", "dataset"] as const)("refuses %s declared size drift before decoding or hashing", async kind => {
    const stream = new ReadableStream<Uint8Array>({start(controller) {controller.enqueue(new Uint8Array([0])); controller.close();}});
    await expect(streamed(kind, stream, {"Content-Length":"2"})).rejects.toThrow("size drift");
  });
  it.each(["ZIP", "dataset"] as const)("cancels a mid-stream %s read", async kind => {
    const abort = new AbortController(), cancel = vi.fn();
    const stream = new ReadableStream<Uint8Array>({pull(controller) {controller.enqueue(new Uint8Array([0])); abort.abort();}, cancel}, {highWaterMark:0});
    await expect(streamed(kind, stream, {}, abort.signal)).rejects.toMatchObject({name:"AbortError"});
    expect(cancel).toHaveBeenCalledOnce();
  });
  it("refuses malformed dataset UTF8 before JSON parsing", async () => {
    const stream = new ReadableStream<Uint8Array>({start(controller) {controller.enqueue(new Uint8Array([0xff])); controller.close();}});
    await expect(streamed("dataset", stream)).rejects.toThrow();
  });
  it("consumes the actual lexical input and executable closed-online mapping", async () => {
    const {api}=client([datasetBytes,input.mapping]);
    const inputReceipt=parseMagneticDatasetReceipt(input.receipt);
    expect((await api.dataset(inputReceipt.project_id,inputReceipt)).request_utf8).toBe(input.payload.request_utf8);
    const mapping=await api.method(inputReceipt.project_id,inputReceipt);
    expect(mapping.online_admitted).toBe(false);
  });
  it.each([['"rights_decision":"mirror"', '"rights_decision":"unknown"'],
           ['"active_cells":7', '"active_cells":8']])("refuses exact raw-body mutation %s with unchanged IDs/request hash",async (before,after)=>{
    const raw=new TextDecoder().decode(datasetBytes), changed=raw.replace(before,after);
    expect(changed).not.toBe(raw);
    const decoded=JSON.parse(changed);
    expect(decoded.dataset_id).toBe(input.receipt.dataset_id);
    expect(decoded.request_sha256).toBe(input.payload.request_sha256);
    expect(decoded.request_utf8).toBe(input.payload.request_utf8);
    const {api}=client([new TextEncoder().encode(changed)]);
    const r=parseMagneticDatasetReceipt(input.receipt);
    await expect(api.dataset(r.project_id,r)).rejects.toThrow("complete dataset byte hash");
  });
  it("refuses unbound bytes before JSON parsing",async()=>{
    const {api}=client([new TextEncoder().encode('{Not valid JSON')]);
    const r=parseMagneticDatasetReceipt(input.receipt), parse=vi.spyOn(JSON,"parse");
    try {await expect(api.dataset(r.project_id,r)).rejects.toThrow("complete dataset byte hash");
      expect(parse).not.toHaveBeenCalled();
    } finally {parse.mockRestore();}
  });
  it("refuses completion after abort during complete-byte hashing before parse",async()=>{
    const abort=new AbortController(), actualDigest=crypto.subtle.digest.bind(crypto.subtle);
    const hash=vi.spyOn(crypto.subtle,"digest").mockImplementation(async (algorithm,data)=>{
      const result=await actualDigest(algorithm,data);abort.abort();return result;
    });
    const {api}=client([datasetBytes]), r=parseMagneticDatasetReceipt(input.receipt), parse=vi.spyOn(JSON,"parse");
    try {await expect(api.dataset(r.project_id,r,abort.signal)).rejects.toMatchObject({name:"AbortError"});
      expect(parse).not.toHaveBeenCalled();
    } finally {parse.mockRestore();hash.mockRestore();}
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
