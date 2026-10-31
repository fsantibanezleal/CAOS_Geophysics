import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it, vi } from "vitest";
import { useLangStore } from "@fasl-work/caos-app-shell";
import { ApiClient } from "../api/client";
import { inspectJointInputs, JointInputApi, parseJointMemberReceipt, type JointInput,
  type JointInputMember, type JointMemberReceipt, type JointSourceAttestation } from "../api/joint-input";
import { jointSha, type JointFile } from "../api/joint-result";
import { JointNativeInputPanel } from "../components/JointNativeInputPanel";

vi.mock("@fasl-work/caos-app-shell", async original=> {
  const shell=await original<typeof import("@fasl-work/caos-app-shell")>();
  return {...shell,useShellLang:()=>shell.useLangStore.getState().lang};
});
const owner="11111111-1111-4111-8111-111111111111",project="22222222-2222-4222-8222-222222222222";
const other="33333333-3333-4333-8333-333333333333",stamp="2026-10-08T00:00:00Z";
const attestation: JointSourceAttestation={provider:"Original user survey",doi:null,citation:null,
  rights_statement:"I attest private storage permission for every original",rights_decision:"provider-link-only",private_storage_permission:"attested",attribution:"Owner"};
function originals(): JointFile[] {
  const root=process.env.GEOPHYSICS_JOINT_MATRIX_FIXTURE;
  if(!root)throw new Error("Explicit original external matrix fixture required, no skipped custody gate");
  return ["development","sealed"].flatMap(role=>readdirSync(join(root,"joint-control-00",role)).map(name=>{
    const path=join(root,"joint-control-00",role,name);return {path:`${role}/${name}`,size:statSync(path).size,read:vi.fn(async()=>new Uint8Array(readFileSync(path)))};
  }));
}
function replace(files: JointFile[],path: string,bytes: Uint8Array) {
  return files.map(file=>file.path===path?{path,size:bytes.length,read:vi.fn(async()=>bytes)}:file);
}
const encode=(value: unknown)=>new TextEncoder().encode(JSON.stringify(value));
const response=(value: unknown,status=200)=>new Response(JSON.stringify(value),{status,headers:{"Content-Type":"application/json"}});
function receipt(member: JointInputMember,index=1): JointMemberReceipt {
  const asset=`44444444-4444-4444-8444-${index.toString().padStart(12,"0")}`,source=`55555555-5555-4555-8555-${index.toString().padStart(12,"0")}`;
  return parseJointMemberReceipt({schema_version:"geophysics.raw-asset-view/v1",asset_id:asset,owner_id:owner,project_id:project,
    source_id:source,source:{schema_version:"geophysics.source-record-view/v1",source_id:source,version:1,provider:attestation.provider,
      location:{kind:"upload",filename:member.name},doi:null,citation:null,retrieved_at:stamp,rights_statement:attestation.rights_statement,
      rights_decision:attestation.rights_decision,private_storage_permission:"attested",declared_format:"joint_native",
      expected_bytes:member.file.size,sha256:member.sha256,attribution:attestation.attribution},
    original_filename:member.name,mime_type:"application/octet-stream",detected_format:"joint_native",byte_count:member.file.size,
    sha256:member.sha256,physical_metadata:{schema:"joint-native-member-1",role:member.role,name:member.name,descriptor:member.descriptor,
      scientific_values_decoded:false,scientific_accepted:false},created_at:stamp,receipt:`/api/projects/${project}/assets/${asset}`,
    download_url:`/api/projects/${project}/assets/${asset}/download`,validation_status:"raw_metadata_checked"});
}
function dataset(input: JointInput,receipts: Map<string,JointMemberReceipt>) {
  return {dataset_id:"66666666-6666-4666-8666-666666666666",project_id:project,
    raw_asset_id:receipts.get("development/request.json")!.asset_id,parser_version:"m11-native-members/v1",modality:"joint_gravity_magnetic_native",
    row_count:(input.manifests.development.arrays as Record<string,{shape:number[]}>).gravity_receivers.shape[0]+(input.manifests.development.arrays as Record<string,{shape:number[]}>).magnetic_receivers.shape[0],
    sha256:"a".repeat(64),qc_verdict:"structural_native_members_only",scientific_accepted:false,
    receipt_url:`/api/projects/${project}/joint-datasets/66666666-6666-4666-8666-666666666666`};
}
describe("native original custody client, never a scientific run",()=> {
  it("verifies the complete actual36 originals without decoding sealed values",async()=> {
    const files=originals(),input=await inspectJointInputs(files);
    expect(input.members).toHaveLength(36);expect(input.scientific_values_decoded).toBe(false);
    expect(input.bytes).toBe(files.reduce((n,f)=>n+f.size,0));
    expect(input.members.filter(m=>m.role==="sealed")).toHaveLength(7);
    for(const m of input.members)expect(m.sha256).toBe(await jointSha(await m.file.read()));
  });
  it.each(["count","bytes","json","duplicate","path"])("closes whole %s before any body read",async bad=> {
    const read=vi.fn(async()=>new Uint8Array());let files: JointFile[]=[{path:"development/request.json",size:100,read},{path:"sealed/sealed.json",size:100,read}];
    if(bad==="count")files=Array.from({length:41},(_,i)=>({path:`development/${i}.npy`,size:1,read}));
    if(bad==="bytes")files=[{path:"development/gravity.raw",size:268435456,read},files[1]];
    if(bad==="json")files[0].size=262145;
    if(bad==="duplicate")files[1].path=files[0].path;
    if(bad==="path")files[0].path="development/../request.json";
    await expect(inspectJointInputs(files)).rejects.toThrow();expect(read).not.toHaveBeenCalled();
  });
  it.each(["missing","extra","shape","sealed_digest","plan","provided"])("closes metadata %s before any NPY read",async bad=> {
    let files=originals();const manifest=files.find(f=>f.path==="development/request.json")!,value=JSON.parse(new TextDecoder().decode(await manifest.read()));
    if(bad==="missing")files=files.filter(f=>f.path!=="sealed/gravity_rows.npy");
    if(bad==="extra")files.push({path:"sealed/extra.npy",size:1,read:vi.fn(async()=>new Uint8Array([0]))});
    if(bad==="shape")value.arrays.density_start.shape=[false];
    if(bad==="sealed_digest")value.sealed_manifest.gravity.rows_sha256="f".repeat(64);
    if(bad==="plan")value.development.plan_sha256="f".repeat(64);
    if(bad==="provided")value.raw_access.gravity={availability:"provided",raw_present:true,correction_present:true};
    files=replace(files,manifest.path,encode(value));
    await expect(inspectJointInputs(files)).rejects.toThrow();
    for(const f of files.filter(f=>f.path.endsWith(".npy")))expect(f.read).not.toHaveBeenCalled();
  });
  it.each(["shape","executable","fortran","duplicate"])("rejects altered literal %s NPY header",async bad=> {
    let files=originals();const path="development/density_start.npy",file=files.find(f=>f.path===path)!,bytes=(await file.read()).slice();
    const request=files.find(f=>f.path==="development/request.json")!,manifest=JSON.parse(new TextDecoder().decode(await request.read()));
    const length=new DataView(bytes.buffer).getUint16(8,true);
    const shape=manifest.arrays.density_start.shape[0];
    const literal=bad==="shape"?`{'descr':'<f8','fortran_order':False,'shape':(${shape+1},)}`:
      bad==="executable"?`{'descr':'<f8','fortran_order':False,'shape':tuple([${shape}])}`:
      bad==="fortran"?`{'descr':'<f8','fortran_order':True,'shape':(${shape},)}`:
      `{'descr':'<f8','descr':'<f8','fortran_order':False,'shape':(${shape},)}`;
    bytes.set(new TextEncoder().encode(literal.padEnd(length-1," ")+"\n"),10);
    manifest.arrays.density_start.file_sha256=await jointSha(bytes);
    files=replace(replace(files,path,bytes),request.path,encode(manifest));
    await expect(inspectJointInputs(files)).rejects.toThrow();
  });
  it("accepts reordered quoted literal headers without changing original array bytes",async()=> {
    let files=originals();const path="development/density_start.npy",file=files.find(f=>f.path===path)!,bytes=(await file.read()).slice();
    const request=files.find(f=>f.path==="development/request.json")!,manifest=JSON.parse(new TextDecoder().decode(await request.read()));
    const length=new DataView(bytes.buffer).getUint16(8,true),offset=10+length,before=bytes.slice(offset);
    const literal=`{ "shape": (${manifest.arrays.density_start.shape[0]},), 'fortran_order': False, "descr": "<f8", }`;
    bytes.set(new TextEncoder().encode(literal.padEnd(length-1," ")+"\n"),10);
    manifest.arrays.density_start.file_sha256=await jointSha(bytes);
    files=replace(replace(files,path,bytes),request.path,encode(manifest));
    expect((await inspectJointInputs(files)).scientific_values_decoded).toBe(false);expect(bytes.slice(offset)).toEqual(before);
  });
  it("uses actual same-origin dedicated headers, byte body, CSRF and cancellation",async()=> {
    const input=await inspectJointInputs(originals()),member=input.members[0],wire=receipt(member),signal=new AbortController().signal;
    const transport=vi.fn(async(url: URL|RequestInfo,_options?: RequestInit)=>response(String(url).endsWith("/csrf")?{csrf_token:"token"}:wire));
    const client=new JointInputApi(new ApiClient("https://geophysics.example.org",transport as typeof fetch));
    expect((await client.upload(project,member,attestation,signal)).sha256).toBe(member.sha256);
    const [url,options]=transport.mock.calls[1] as unknown as [URL,RequestInit];expect(url.pathname).toBe(`/api/projects/${project}/joint-members`);
    expect(options).toMatchObject({method:"POST",credentials:"same-origin",redirect:"error",cache:"no-store",signal});
    const headers=new Headers(options.headers);expect(headers.get("X-CSRF-Token")).toBe("token");expect(headers.get("X-Asset-Metadata")).toBeNull();
    expect(headers.get("Content-Type")).toBe("application/octet-stream");expect(JSON.parse(headers.get("X-Joint-Member-Metadata")!).name).toBe(member.name);
    expect(new Uint8Array(await (options.body as Blob).arrayBuffer())).toEqual(await member.file.read());
  });
  it.each(["missing","owner","duplicate","hash"])("does not POST an incomplete/contradictory %s index",async bad=> {
    const input=await inspectJointInputs(originals()),receipts=new Map(input.members.map((m,i)=>[`${m.role}/${m.name}`,receipt(m,i+1)]));
    const first=input.members[0],key=`${first.role}/${first.name}`,r=receipts.get(key)!;
    if(bad==="missing")receipts.delete(key);
    if(bad==="owner")r.owner_id=other;
    if(bad==="duplicate")r.asset_id=[...receipts.values()][1].asset_id;
    if(bad==="hash")r.sha256="f".repeat(64);
    const transport=vi.fn(async()=>response({csrf_token:"token"}));
    await expect(new JointInputApi(new ApiClient("https://geophysics.example.org",transport as typeof fetch)).index(project,input,receipts)).rejects.toThrow();
    expect(transport).not.toHaveBeenCalled();
  });
  it("indexes exact36 receipts and checks returned primary identity",async()=> {
    const input=await inspectJointInputs(originals()),receipts=new Map(input.members.map((m,i)=>[`${m.role}/${m.name}`,receipt(m,i+1)])),value=dataset(input,receipts);
    const transport=vi.fn(async(url: URL|RequestInfo,_options?: RequestInit)=>response(String(url).endsWith("/csrf")?{csrf_token:"token"}:value));
    const client=new JointInputApi(new ApiClient("https://geophysics.example.org",transport as typeof fetch));
    expect((await client.index(project,input,receipts)).scientific_accepted).toBe(false);
    const options=transport.mock.calls[1][1] as unknown as RequestInit,body=JSON.parse(options.body as string);
    expect(Object.keys(body.development)).toHaveLength(29);expect(Object.keys(body.sealed)).toHaveLength(7);
    value.raw_asset_id=other;await expect(client.index(project,input,receipts)).rejects.toThrow("primary binding");
  });
  it.each(["rights","version","source","path","accepted"])("rejects %s fabricated custody receipt",async bad=> {
    const input=await inspectJointInputs(originals()),r=receipt(input.members[0]) as unknown as Record<string,any>;
    if(bad==="rights")r.source.private_storage_permission=null;
    if(bad==="version")r.source.version=0;
    if(bad==="source")r.source.source_id=other;
    if(bad==="path")r.download_url="https://foreign.example.org/native";
    if(bad==="accepted")r.physical_metadata.scientific_accepted=true;
    expect(()=>parseJointMemberReceipt(r)).toThrow();
  });
  it("denies metadata overflow and external API targets before transport",async()=> {
    const transport=vi.fn(async()=>response({})),client=new ApiClient("https://geophysics.example.org",transport as typeof fetch);
    await expect(client.requestNativeMember("/api/native",new Blob(["x"]),"x".repeat(16385),v=>v,"token")).rejects.toThrow("16 KiB");
    await expect(client.requestNativeMember("https://foreign.example.org/api/native",new Blob(["x"]),"{}",v=>v,"token")).rejects.toThrow("same-origin");
    expect(transport).not.toHaveBeenCalled();
  });
  it.each(["en","es"] as const)("renders ADR leaf boundaries and exact accessible selectors %s",lang=> {
    useLangStore.setState({lang});const html=renderToStaticMarkup(createElement(JointNativeInputPanel,{projectId:project,ownerId:owner,
      api:new ApiClient("https://geophysics.example.org"),onIndexed:()=>undefined}));
    expect(html).toContain(lang==="en"?'aria-label="Original input section"':'aria-label="Sección de datos originales"');
    expect(html).toContain(lang==="en"?"Sealed values are not decoded here":"Los valores reservados no se decodifican aquí");
    expect(html).toContain("24_private_joint_execution.md");expect(html).toContain("disabled");
    expect(html).not.toContain("<style");expect(html).not.toContain("<iframe");expect(html).not.toContain("<script");
  });
});
