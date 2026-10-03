import { afterEach, describe, expect, it, vi } from "vitest";
import actual from "./fixtures/mt-actual.json";
import { ApiClient } from "../api/client";
import { MtProcessingApi } from "../api/mt-processing";
import { parseEdiDataset, parseMtResult, validateMtParameters, tensorScores, verifyMtBundle } from "../api/mt-contracts";
import { parseProjectDatasetReceipt, type EdiDatasetReceipt, type MtProcessingJob } from "../api/processing-contracts";
import { frequencyAxis, mtResidual, partition, quantityUnit } from "../components/mt-view-data";
import { zipSync } from "fflate";
import { sha } from "../api/processing-contracts";
const clone=()=>structuredClone(actual);
afterEach(()=>vi.unstubAllGlobals());
describe("actual compute MT serialization",()=>{
  it("accepts actual QC and near-zero halfspace inverse, never creates truth",()=>{expect(parseEdiDataset(actual.dataset)).toEqual(actual.dataset);expect(parseMtResult(actual.m05).inverse).toBeNull();const r=parseMtResult(actual.m06);expect(r.inverse!.methods["mt-lm"].model[0]).toBeCloseTo(100,6);expect(r.truth).toBeNull();});
  it.each(["real","imag","apparent","phase"] as const)("rejects modified %s predictions",q=>{const f=clone();f.m06.inverse.methods["mt-lm"].predicted[q][0]+=.01;expect(()=>parseMtResult(f.m06)).toThrow();});
  it("rejects sign/unit/variance/shape/truth and masked QC departures",()=>{
    const changes=[(f:ReturnType<typeof clone>)=>{f.m05.screen.observed.yx.real[0]*=-1;},(f:ReturnType<typeof clone>)=>{f.m05.frequency_hz[0]=0;},(f:ReturnType<typeof clone>)=>{f.m05.screen.tensor.sigma[0][0][0]=0;},(f:ReturnType<typeof clone>)=>{f.m05.screen.compatibility.xx_component_wrms=10;},(f:ReturnType<typeof clone>)=>{f.m05.physical_metadata.geometry.sign_convention="-";},(f:ReturnType<typeof clone>)=>{f.m05.screen.tensor.real.pop();}];
    for(const change of changes){const f=clone();change(f);expect(()=>parseMtResult(f.m05)).toThrow();}expect(()=>parseMtResult({...actual.m05,truth:[100]})).toThrow();expect(()=>parseMtResult({...actual.m05,inverse:actual.m06.inverse})).toThrow();
  });
  it("rejects changing frozen mask, winner, residual and bootstrap receipt",()=>{
    const changes=[(f:ReturnType<typeof clone>)=>{f.m06.inverse.active[4]=true;},(f:ReturnType<typeof clone>)=>{f.m06.inverse.methods["mt-lm"].residual.real[0]=.1;},(f:ReturnType<typeof clone>)=>{f.m06.inverse.methods["mt-lm"].uncertainty.lower[0]+=1;},(f:ReturnType<typeof clone>)=>{f.m06.inverse.methods["mt-lm"].uncertainty.samples.pop();},(f:ReturnType<typeof clone>)=>{f.m06.inverse.evaluation_protocol.selected_start_ohm_m=[999];}];
    for(const change of changes){const f=clone();change(f);expect(()=>parseMtResult(f.m06)).toThrow();}
  });
  it("checks imposed parameter bounds, not inferred solver defaults",()=>{expect(validateMtParameters(actual.m06.parameters)).toEqual(actual.m06.parameters);for(const changes of [{thickness_m:[1]},{initial_ohm_m:[1]},{initial_ohm_m:[6000]},{beta:NaN},{bootstrap_samples:19},{seed:-1},{qc_job_id:"../"}])expect(()=>validateMtParameters({...actual.m06.parameters,...changes})).toThrow();});
  it("rejects executable source links and invalid coordinate/units declarations",()=>{const f=clone();expect(()=>parseEdiDataset({...f.dataset,source:{...f.dataset.source,exact_url:"javascript:alert(1)"}})).toThrow();expect(()=>parseMtResult({...f.m05,physical_metadata:{...f.m05.physical_metadata,measurement_unit:"nT"}})).toThrow();});
  it("maps period, partitions and signed other-component residual using actual output",()=>{const r=parseMtResult(actual.m06);expect(quantityUnit("real")).toBe("Ω E/H");expect(frequencyAxis([.1,10],true)).toEqual([10,.1]);expect(partition([1,2],[true,false],true)[1]).toBeNaN();expect(mtResidual(r,"yx","real",true)[0]).toBe((r.screen.observed.yx.real[0]-r.inverse!.methods["mt-lm"].predicted.real[0])/r.screen.observed.yx.sigma_real_imag_ohm[0]);expect(()=>mtResidual(parseMtResult(actual.m05),"xy","real",true)).toThrow();expect(tensorScores(r.screen.tensor).xx_component_wrms).toBe(0);});
  it("refuses non-success result/export before making a request",async()=>{const f=clone(),api=new MtProcessingApi(new ApiClient("http://127.0.0.1:8877")),fetch=vi.fn();vi.stubGlobal("fetch",fetch);const receipt=parseProjectDatasetReceipt({dataset_id:f.dataset.dataset_id,project_id:f.dataset.project_id,raw_asset_id:f.dataset.raw_asset_id,version:1,schema:f.dataset.schema,modality:f.dataset.modality,row_count:24,parser_version:f.dataset.parser_version,raw_sha256:f.dataset.parent_raw_sha256,sha256:f.m05.dataset_sha256,created_at:"2026-10-03T00:00:00Z",qc_verdict:f.dataset.qc_verdict}) as EdiDatasetReceipt;
    const job={state:"cancelled",project_id:f.dataset.project_id,dataset_sha256:receipt.sha256} as MtProcessingJob;
    await expect(api.mtResult(job.project_id,job,parseEdiDataset(f.dataset),receipt)).rejects.toThrow("Non-success");await expect(api.mtExport(job.project_id,job,parseEdiDataset(f.dataset),receipt)).rejects.toThrow("Non-success");expect(fetch).not.toHaveBeenCalled();
    await expect(verifyMtBundle(new Blob(),job,parseEdiDataset(f.dataset))).rejects.toThrow();
  });
  it("verifies original stored ZIP bytes and rejects member/hash/unit drift",async()=>{
    const f=clone(),encode=(v:unknown)=>new TextEncoder().encode(JSON.stringify(v)),datasetBytes=encode(f.dataset),dsSha=await sha(datasetBytes);
    f.m06.dataset_sha256=dsSha;const r=parseMtResult(f.m06),resultBytes=encode(r),resultSha=await sha(resultBytes);
    const job={state:"succeeded",job_id:r.job_id,project_id:f.dataset.project_id,dataset_id:r.dataset_id,dataset_sha256:dsSha,method_id:r.method_id,request_sha256:r.request_sha256,result_sha256:resultSha,request:{parameters:r.parameters,raw_asset_id:r.raw_asset_id,raw_sha256:r.raw_sha256,qc_screen_sha256:r.qc_screen_sha256}} as MtProcessingJob;
    const manifest={schema:"geophysics.processing-bundle/v1",dataset_id:r.dataset_id,job_id:r.job_id,method_id:r.method_id,parameters:r.parameters,source:r.source,environment:r.environment,axes:["frequency"],dimensions:r.dimensions,units:{frequency:"Hz",impedance:"ohm E/H",resistivity:"ohm m",thickness:"m",uncertainty:"ohm SD per real/imaginary component"},provenance:{raw_sha256:r.raw_sha256,raw_bytes:r.raw_bytes,dataset_sha256:dsSha,request_sha256:r.request_sha256,engine_sha256:r.engine_sha256,parser_sha256:r.parser_sha256,forward_sha256:r.forward_sha256,environment_sha256:r.environment_sha256},members:{"dataset.json":{sha256:dsSha,bytes:datasetBytes.length},"result.json":{sha256:resultSha,bytes:resultBytes.length}},raw_bytes_included:false};
    const files={"manifest.json":encode(manifest),"dataset.json":datasetBytes,"result.json":resultBytes};const blob=(entries:Record<string,Uint8Array>,level:0|1=0)=>new Blob([Uint8Array.from(zipSync(entries,{level})).buffer]);
    expect((await verifyMtBundle(blob(files),job,parseEdiDataset(f.dataset))).result.inverse).not.toBeNull();
    for(const malformed of [blob({...files,"raw.edi":encode("forbidden")}),blob(files,1),blob({...files,"result.json":encode({...r,truth:[100]})}),blob({...files,"manifest.json":encode({...manifest,units:{...manifest.units,impedance:"nT"}})}),blob({...files,"result.json":encode({...r,request_sha256:"c".repeat(64)})})])await expect(verifyMtBundle(malformed,job,parseEdiDataset(f.dataset))).rejects.toThrow();
  });
});
