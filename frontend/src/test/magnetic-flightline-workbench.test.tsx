import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiClient } from "../api/client";
import { MagneticFlightlineApi } from "../api/magnetic-flightline";
import { MagneticFlightlineWorkbench } from "../components/MagneticFlightlineWorkbench";

const project="11111111-1111-4111-8111-111111111111",asset="22222222-2222-4222-8222-222222222222",dataset="33333333-3333-4333-8333-333333333333";
const sha="a".repeat(64);
afterEach(()=>{vi.unstubAllGlobals();vi.restoreAllMocks();});

describe("M03 flight-line user-data workbench",()=>{
  it.each([false,true])("renders mapped CSV processing and honest method scope in locale (Spanish=%s)",es=>{
    vi.stubGlobal("window",{location:{origin:"https://geophysics.example"}});
    const html=renderToStaticMarkup(createElement(MagneticFlightlineWorkbench,{projectId:project,es}));
    expect(html).toContain(es?"Procesamiento de líneas de vuelo":"Flight-line processing");
    expect(html).toContain(es?"Mapeo de columnas":"Column mapping");
    for(const column of ["easting","northing","value","line_id","line_role","sensor_height_m","sample_order"])expect(html).toContain(`placeholder="${column}"`);
    expect(html).toContain(es?"líneas completas retenidas":"held-out complete lines");
    expect(html).toContain(es?"No aplica correcciones magnéticas":"applies no magnetic corrections");
    expect(html).toContain(es?"La predicción retenida no equivale a precisión":"Held-out prediction is not model accuracy");
  });

  it("posts explicit magnetic mapping and verifies the standard dataset receipt identity",async()=>{
    vi.stubGlobal("window",{location:{origin:"https://geophysics.example"}});
    const requests: Array<{url:string;init:RequestInit}> = [];
    const transport=vi.fn(async(input:URL|RequestInfo,init:RequestInit={})=>{
      const url=String(input);requests.push({url,init});
      const payload=url.endsWith("/api/auth/csrf")?{csrf_token:"csrf-test"}:{dataset_id:dataset,project_id:project,raw_asset_id:asset,version:1,schema:"geophysics.observation-dataset/v1",modality:"magnetic_flightline",row_count:480,parser_version:"magnetic-flightline-original/v1",qc_verdict:"source_bound_not_numerically_processed",raw_sha256:sha,sha256:"b".repeat(64),created_at:"2026-10-27T12:00:00Z"};
      return new Response(JSON.stringify(payload),{status:200,headers:{"Content-Type":"application/json"}});
    });
    const api=new MagneticFlightlineApi(new ApiClient("https://geophysics.example",transport));
    const request={mapping:{easting:"UTM_E",northing:"UTM_N",value:"MAG_NT",line_id:"LINE",line_role:"ROLE",sensor_height_m:"HEIGHT",sample_order:"SEQ"},processing_state:"IGRF removed; levelling unknown",value_quantity:"total-field anomaly [nT]",sensor_height_reference:"above-ground"};
    const receipt=await api.createDataset(project,asset,request);
    expect(receipt.dataset_id).toBe(dataset);expect(requests.map(r=>r.url)).toEqual(["https://geophysics.example/api/auth/csrf",`https://geophysics.example/api/projects/${project}/datasets`]);
    const post=JSON.parse(String(requests[1].init.body));expect(post).toEqual({asset_id:asset,magnetic_request:request});
    expect((requests[1].init.headers as Record<string,string>)["X-CSRF-Token"]).toBe("csrf-test");
  });

  it("rejects a receipt returned for a different project/source",async()=>{
    vi.stubGlobal("window",{location:{origin:"https://geophysics.example"}});
    const transport=vi.fn(async(input:URL|RequestInfo)=>new Response(JSON.stringify(String(input).endsWith("/csrf")?{csrf_token:"x"}:{dataset_id:dataset,project_id:project,raw_asset_id:"44444444-4444-4444-8444-444444444444",version:1,schema:"geophysics.observation-dataset/v1",modality:"magnetic_flightline",row_count:12,parser_version:"magnetic-flightline-original/v1",qc_verdict:"source_bound_not_numerically_processed",raw_sha256:sha,sha256:sha,created_at:"2026-10-27T12:00:00Z"}),{status:200,headers:{"Content-Type":"application/json"}}));
    const api=new MagneticFlightlineApi(new ApiClient("https://geophysics.example",transport));
    await expect(api.createDataset(project,asset,{mapping:{}})).rejects.toThrow("does not match requested project and source");
  });

  it.each([
    {methods:[],unavailable:[{method_id:"magnetic.flightline-qc-grid/v1",eligible:false,lane:"pending_host_admission",source_eligible:true,reason:"Source-bound M03 is ready; execution remains closed until its worker is validated"}]},
    {methods:[{method_id:"magnetic.flightline-qc-grid/v1",eligible:true,lane:"online_processing",scope:"pending_host_admission"}],unavailable:[]},
  ])("keeps execution closed for pending-host response %#",async verdict=>{
    vi.stubGlobal("window",{location:{origin:"https://geophysics.example"}});
    const transport=vi.fn(async()=>new Response(JSON.stringify({dataset_id:dataset,...verdict}),{status:200,headers:{"Content-Type":"application/json"}}));
    const api=new MagneticFlightlineApi(new ApiClient("https://geophysics.example",transport));
    const result=await api.methods(project,dataset);expect(result.eligible).toBe(false);expect(result.reason).toMatch(/pending_host_admission|worker/i);
  });
});
