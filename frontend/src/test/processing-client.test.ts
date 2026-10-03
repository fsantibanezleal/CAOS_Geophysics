import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiClient, ApiHttpError } from "../api/client";
import { ProcessingApi } from "../api/processing";
import { fixture, id } from "./fixtures/processing";
const origin = "http://127.0.0.1:8876";
function client(replies: unknown[]) {
  const fetcher = vi.fn(async () => new Response(JSON.stringify(replies.shift()),{headers: {"content-type": "application/json"}}));
  vi.stubGlobal("fetch",fetcher); return {api: new ProcessingApi(new ApiClient(origin)),fetcher};
}
afterEach(() => vi.unstubAllGlobals());
describe("authenticated processing client", () => {
  it("binds all replies to the requested project dataset and job", async () => {
    const f = fixture(); const {api} = client([{datasets: [{...f.receipt,project_id: id(8)}]}, {...f.dataset,raw_asset_id: id(8)}, {dataset_id: id(8),methods: [],unavailable: []}, {jobs: [{...f.job,project_id: id(8),request: {...f.job.request,project_id: id(8)},result_url: `/api/projects/${id(8)}/jobs/${id(5)}/result`}]}, {...f.job,job_id: id(8),request: {...f.job.request,job_id: id(8)},result_url: `/api/projects/${id(2)}/jobs/${id(8)}/result`}, {...f.result,request_sha256: "d".repeat(64)}]);
    await expect(api.datasets(id(2))).rejects.toThrow("project"); await expect(api.dataset(id(2),f.receipt)).rejects.toThrow(); await expect(api.methods(id(2),id(3))).rejects.toThrow("dataset");
    await expect(api.jobs(id(2))).rejects.toThrow("project"); await expect(api.job(id(2),id(5))).rejects.toThrow("job"); await expect(api.result(id(2),f.job,f.dataset,f.receipt)).rejects.toThrow("request hash");
    await expect(api.result(id(2),f.job,f.dataset,{...f.receipt,sha256: "d".repeat(64)})).rejects.toThrow("dataset hash");
    await expect(api.export(id(2),{...f.job,state: "failed"},f.dataset,f.receipt)).rejects.toThrow("non-success");
  });
  it("submits explicit parameters with CSRF and abortable same-origin reads", async () => {
    const f = fixture(); const {api,fetcher} = client([{csrf_token: "csrf"}, f.receipt, {csrf_token: "csrf"}, f.job, {datasets: [f.receipt]}, {csrf_token: "csrf"}, {...f.job,state: "cancelled",result_sha256: null,result_url: null,error: {code:"user_cancelled",message:"Owner cancelled"}}]);
    const signal = new AbortController().signal;
    await api.validateAsset(id(2),id(4),signal); await api.submit(id(2),f.receipt,6,signal); await api.datasets(id(2),signal); await api.cancel(id(2),id(5),signal);
    const calls = fetcher.mock.calls as unknown as [string, RequestInit][];
    expect(JSON.parse(calls[1][1].body as string)).toEqual({asset_id: id(4)}); expect(JSON.parse(calls[3][1].body as string)).toEqual({dataset_id:id(3),method_id:f.job.method_id,parameters:{threshold:6}});
    for (const [url,request] of calls) { expect(String(url)).toMatch(new RegExp(`^${origin}/api/`)); expect(request.credentials).toBe("same-origin"); expect(request.signal).toBe(signal); expect(request.cache).toBe("no-store"); }
    expect(new Headers(calls[3][1].headers).get("x-csrf-token")).toBe("csrf");
  });
  it("forwards abort and typed transport failures", async () => {
    const fetcher = vi.fn(async () => {throw new DOMException("Aborted","AbortError");}); vi.stubGlobal("fetch",fetcher);
    const api = new ProcessingApi(new ApiClient(origin)); await expect(api.jobs(id(2),new AbortController().signal)).rejects.toMatchObject({name:"AbortError"});
    vi.stubGlobal("fetch",async () => new Response(JSON.stringify({code:"session_expired",message:"Expired",fields:[]}),{status:401,headers:{"content-type":"application/json"}}));
    await expect(new ProcessingApi(new ApiClient(origin)).jobs(id(2))).rejects.toBeInstanceOf(ApiHttpError);
  });
});
