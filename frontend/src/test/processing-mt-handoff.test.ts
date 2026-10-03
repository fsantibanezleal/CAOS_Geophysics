import { describe, expect, it, vi, afterEach } from "vitest";
import { ApiClient } from "../api/client";
import { ProcessingApi } from "../api/processing";
import { M05_METHOD, M06_METHOD, parseDatasetReceipt, parseEligibility, parseFlagResult, parseProcessingJob, parseProjectDatasetReceipt, parseProjectProcessingJob } from "../api/processing-contracts";
import { fixture, id } from "./fixtures/processing";
// Schema-accurate list/receipt controls from PR100's frozen contract. These are
// not scientific output fixtures or evidence of browser MT execution.
const receipt = () => ({...fixture().receipt, dataset_id:id(6), modality:"edi_transfer_function",parser_version:"edi-strict-envelope/v1",qc_verdict:"awaiting_full_tensor_qc",row_count:24});
const m05 = () => {
  const f = fixture();
  return {...f.job,dataset_id:id(6),method_id:M05_METHOD,
    request:{...f.job.request,dataset_id:id(6),method_id:M05_METHOD,parameters:{},raw_asset_id:id(4),raw_sha256:f.receipt.raw_sha256},
    preflight:{estimated_memory_bytes:192*1048576,memory_limit_bytes:768*1048576,estimated_scratch_bytes:3*1048576,scratch_limit_bytes:8*1048576,wall_limit_seconds:90}};
};
const m06 = () => {
  const qc = m05(); return {...qc,method_id:M06_METHOD,request:{...qc.request,method_id:M06_METHOD,qc_screen_sha256:"d".repeat(64),parameters:{qc_job_id:id(5),thickness_m:[350],initial_ohm_m:[120,12],beta:.05,bootstrap_samples:40,seed:61001}},preflight:{...qc.preflight,memory_limit_bytes:1024*1048576,scratch_limit_bytes:32*1048576,wall_limit_seconds:300}};
};
afterEach(() => vi.unstubAllGlobals());
describe("MT frozen handoff without activating an unreviewed scientific adapter", () => {
  it("keeps immutable EDI envelopes distinct from parsed gravity", () => {
    expect(parseProjectDatasetReceipt(receipt())).toEqual(receipt());
    expect(parseProjectDatasetReceipt({...receipt(),row_count:512}).row_count).toBe(512);
    expect(() => parseProjectDatasetReceipt({...receipt(),row_count:513})).toThrow();
    expect(() => parseProjectDatasetReceipt({...receipt(),qc_verdict:"parsed_for_flag_qc_only"})).toThrow();
    expect(() => parseDatasetReceipt(receipt())).toThrow("not parsed gravity");
  });
  it("binds immutable raw and QC requests and preserves closed-host eligibility", () => {
    expect(parseProjectProcessingJob(m05())).toEqual(m05()); expect(parseProjectProcessingJob(m06())).toEqual(m06());
    expect(() => parseProcessingJob(m05())).toThrow("QC/candidate");
    expect(() => parseProjectProcessingJob({...m05(),request:{...m05().request,parameters:{threshold:6}}})).toThrow();
    const candidate = m06();
    for (const parameters of [{...candidate.request.parameters,bootstrap_samples:19},{...candidate.request.parameters,seed:-1},{...candidate.request.parameters,thickness_m:[350,100]},{...candidate.request.parameters,initial_ohm_m:[1,12]},{...candidate.request.parameters,qc_job_id:"../"}]) expect(() => parseProjectProcessingJob({...candidate,request:{...candidate.request,parameters}})).toThrow();
    expect(() => parseProjectProcessingJob({...candidate,request:{...candidate.request,qc_screen_sha256:undefined}})).toThrow();
    expect(() => parseProjectProcessingJob({...candidate,preflight:{...candidate.preflight,estimated_scratch_bytes:33*1048576}})).toThrow();
    const closed = {dataset_id:id(6),methods:[],unavailable:[M05_METHOD,M06_METHOD].map(method_id => ({method_id,eligible:false,lane:"pending_host_admission",reason:"Actual ML VPS numerical and resource admission is not recorded"}))}; expect(parseEligibility(closed)).toEqual(closed);
    const eligible = {dataset_id:id(6),methods:[{method_id:M06_METHOD,eligible:true,lane:"online_processing",qc_job_id:id(5),scope:"conditional fixed-thickness 1D TRF"}],unavailable:[]}; expect(parseEligibility(eligible)).toEqual(eligible);
    expect(() => parseEligibility({...eligible,methods:[{...eligible.methods[0],qc_job_id:undefined}]})).toThrow();
    expect(() => parseFlagResult({...fixture().result,method_id:M05_METHOD,inverse:null})).toThrow();
  });
  it("mixed project lists preserve MT identities without routing results through gravity", async () => {
    const f = fixture(), replies = [{datasets:[f.receipt,receipt()]},{jobs:[f.job,m05()]}];
    const qc = {...m05(),job_id:id(7),request:{...m05().request,job_id:id(7)},result_url:`/api/projects/${id(2)}/jobs/${id(7)}/result`}; replies[1] = {jobs:[f.job,qc]};
    vi.stubGlobal("fetch",vi.fn(async () => new Response(JSON.stringify(replies.shift()),{headers:{"Content-Type":"application/json"}})));
    const api = new ProcessingApi(new ApiClient("http://127.0.0.1:8876"));
    expect((await api.datasets(id(2))).map(row => row.modality)).toEqual(["gravity_station","edi_transfer_function"]);
    expect((await api.jobs(id(2))).map(row => row.method_id)).toEqual([f.job.method_id,M05_METHOD]);
  });
});
