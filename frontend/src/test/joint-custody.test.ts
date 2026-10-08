import {createElement} from "react";
import {renderToStaticMarkup} from "react-dom/server";
import {readFileSync, readdirSync, statSync} from "node:fs";
import {join, relative} from "node:path";
import {zipSync, type Zippable} from "fflate";
import {describe, expect, it, vi} from "vitest";
import {ApiClient} from "../api/client";
import {inspectCustodyArchive, parseJointCustodyIndex, parseJointHistory, JOINT_NATIVE_METHOD, type JointCustodyJob} from "../api/joint-custody";
import {jointJson, jointSha} from "../api/joint-result";
import {JointProjectWorkbench} from "../components/JointProjectWorkbench";

const owner="11111111-1111-4111-8111-111111111111", project="22222222-2222-4222-8222-222222222222", jobid="33333333-3333-4333-8333-333333333333";
const job: JointCustodyJob={job_id:jobid,owner_id:owner,project_id:project,dataset_id:"44444444-4444-4444-8444-444444444444",dataset_sha256:"a".repeat(64),method_id:JOINT_NATIVE_METHOD,request_sha256:"b".repeat(64),state:"failed",cancel_requested:false,error_code:"custody_fixture_no_execution",index_available:true,result_sha256:"c".repeat(64),result_bytes:100};
const encode=(value: unknown)=>new TextEncoder().encode(JSON.stringify(value));
function index() {return {schema:"geophysics.joint-result-custody/v1",job_id:job.job_id,owner_id:owner,project_id:project,dataset_id:job.dataset_id,dataset_sha256:job.dataset_sha256,method_id:job.method_id,request_sha256:job.request_sha256,state:job.state,members:{"workflow.json":{byte_count:1,sha256:"d".repeat(64)}},native_bytes:1,scientific_acceptance:false,authenticity_verified:false,public_activation:false};}
describe("native stored custody never admits science",()=> {
  it("binds literal failed history and all index identities",()=> {
    const history={schema:"geophysics.joint-custody-history/v1",owner_id:owner,project_id:project,jobs:[job]};
    expect(parseJointHistory(jointJson(encode(history)),owner,project)[0]).toEqual(job);
    expect(parseJointCustodyIndex(jointJson(encode(index())),job).scientific_acceptance).toBe(false);
    expect(()=>parseJointHistory(jointJson(encode({...history,jobs:[job,job]})),owner,project)).toThrow("duplicate");
    expect(()=>parseJointHistory(jointJson(encode(history)),project,project)).toThrow("scope");
  });
  it.each(["job_id","owner_id","project_id","dataset_id","dataset_sha256","request_sha256","state","scientific_acceptance","native_bytes","unknown"])("refuses changed index %s",field=> {
    const value: Record<string,unknown>={...index()}; value[field]=field==="scientific_acceptance"?true:field==="native_bytes"?2:field==="state"?"succeeded":field.endsWith("sha256")?"f".repeat(64):"55555555-5555-4555-8555-555555555555";
    expect(()=>parseJointCustodyIndex(jointJson(encode(value)),job)).toThrow();
  });
  it.each(["declared","streamed","size_drift"])("bounds transport %s before buffer assembly",async mode=> {
    const transport=vi.fn(async()=>new Response(new Uint8Array([1,2,3]),{headers: mode==="declared"?{"Content-Length":"999999"}:mode==="size_drift"?{"Content-Length":"2"}:{}}));
    const api=new ApiClient("http://localhost",transport);
    await expect(api.requestBoundedBytes("/api/projects",mode==="streamed"?2:4)).rejects.toThrow();
    expect(transport.mock.calls).toHaveLength(1);
  });
  it("verifies the complete real native archive and retains failed server state separately",async()=> {
    const root=process.env.GEOPHYSICS_JOINT_INSTRUMENT_FIXTURE; if(!root)throw new Error("Actual external native instrument required");
    const native: Record<string,Uint8Array>={};
    function visit(path: string){for(const name of readdirSync(path)){const p=join(path,name); if(statSync(p).isDirectory())visit(p);else native[relative(root!,p).replaceAll("\\","/")]=new Uint8Array(readFileSync(p));}}
    visit(root); const members: Record<string,{byte_count:number;sha256:string}>={};
    for(const [name,bytes] of Object.entries(native))members[name]={byte_count:bytes.length,sha256:await jointSha(bytes)};
    const payload={...index(),members,native_bytes:Object.values(members).reduce((n,v)=>n+v.byte_count,0)}, indexBytes=encode(payload);
    const bound={...job,result_sha256:await jointSha(indexBytes),result_bytes:indexBytes.length};
    const zipped: Zippable={}; for(const [name,bytes]of Object.entries(native))zipped[name]=[bytes,{level:0}]; zipped["private-custody-index.json"]=[indexBytes,{level:0}];
    const archive=zipSync(zipped), inspected=await inspectCustodyArchive(archive,indexBytes,bound);
    expect(inspected.instrument).not.toBeNull(); expect(inspected.files.size).toBe(Object.keys(native).length);
    expect(bound.state).toBe("failed"); expect(inspected.limitations.scientific_acceptance_verified).toBe(false);
    await expect(inspectCustodyArchive(archive,indexBytes,{...bound,request_sha256:"f".repeat(64)})).rejects.toThrow("binding");
  });
  it.each([false,true])("mount wrapper uses exactly one parent rail, language=%s",es=> {
    vi.stubGlobal("window",{location:{origin:"http://localhost"}});
    try {const html=renderToStaticMarkup(createElement(JointProjectWorkbench,{projectId:project,es,onManage:()=>{},onCurated:()=>{},methodNavigation:createElement("nav",{"data-testid":"parent-method-rail"},"Methods")}));
      expect(html.match(/<aside/g)).toHaveLength(1);expect(html.match(/parent-method-rail/g)).toHaveLength(1);
      expect(html).toContain(es?"Custodia de levantamiento conjunto":"Joint survey custody");expect(html).not.toContain("<style");
    } finally {vi.unstubAllGlobals();}
  });
  it("admits actual Python owner-only API archive, not only a JS-created ZIP",async()=> {
    const root=process.env.GEOPHYSICS_JOINT_CUSTODY_API_RECEIPT;
    if(!root)throw new Error("Explicit actual Python custody API receipt required");
    const history=jointJson(new Uint8Array(readFileSync(join(root,"actual-history.json"))));
    const actual=parseJointHistory(history,String(history.owner_id),String(history.project_id))[0];
    const archive=new Uint8Array(readFileSync(join(root,"actual-export.zip"))), bytes=new Uint8Array(readFileSync(join(root,"actual-index.json")));
    const inspected=await inspectCustodyArchive(archive,bytes,actual);
    expect(actual.state).toBe("failed");expect(actual.error_code).toBe("custody_fixture_no_execution");
    expect(inspected.instrument).not.toBeNull();expect(inspected.limitations.scientific_acceptance_verified).toBe(false);
  });
});
