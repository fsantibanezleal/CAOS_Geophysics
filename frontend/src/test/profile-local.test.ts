import { describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { readProfileFiles, parseProfileResult, profileSelection } from "../api/profile-local-contracts";

// Authored structural controls only, not a computed geophysical inverse.
function control() {
  return {schema:"geophysics.supplied-profile-result/v1",method:"ert.topographic-profile/v1",
    metadata:{schema:"geophysics.supplied-profile/v1",method:"ert.topographic-profile/v1",source:{source_id:"own-profile",kind:"user_upload",citation:"Structural parser control, not computed evidence",rights:{holder:"Operator",processing_allowed:true,redistribution_allowed:false},sha256:"a".repeat(64),bytes:512},frame:{horizontal_reference:"Local baseline",vertical_datum:"Local datum",coordinate_unit:"m",vertical_positive:"up",profile_axes:["distance","elevation"]},weights:{policy:"provider-example-conditional/v1"}},
    original:{sha256:"a".repeat(64),bytes:512},geometry:{sensor_xz_m:[[0,0],[1,0],[2,0],[3,0]],abmn_zero_based:[[0,3,1,2],[0,3,1,2],[0,3,1,2],[0,3,1,2]],row_ids_zero_based:[0,1,2,3]},
    engine_report:{schema:"inverse-earth.local-ert-m07/v1",source_id:"own-profile",source_sha256:"a".repeat(64),source_bytes:512,rights_decision:"supplied-declaration-not-verified",raw_publication:false,truth:null,field_geology_claim:null,inverse_status:"not-converged",qc:{measurement_count:4},split:{training_rows:[0,1],heldout_rows:[2,3]},inverse:{mesh_cells:2,model_resistivity_ohm_m:[100,200],model_cell_center_xz_m:[[1/3,-1/3],[2/3,-2/3]],coverage_log10_sensitivity_per_cell:[-2,-1],observed_r_ohm:[1,2,3,4],predicted_r_ohm:[1.1,1.9,3.2,3.8],signed_residual_r_ohm:[.1,-.1,.2,-.2],parameter_mesh:{schema:"geophysics.profile-parameter-mesh/v1",coordinate_unit:"m",vertical_positive:"up",node_xz_m:[[0,0],[1,0],[0,-1],[1,-1]],cell_node_ids:[[0,1,2],[1,3,2]]}}},
    code_hashes:{"ert.py":"b".repeat(64),"supplied_profiles.py":"c".repeat(64),"profile_mesh.py":"d".repeat(64)},numerical_settings:{lam:10,maxIter:12},scope:{uploaded:false,raw_copied:false,execution:"explicit-local",rights:"operator-declaration-not-independent-permission-review",uncertainty:"assumed-not-calibrated",truth_available:false,residual_convention:"predicted-minus-observed"},content_sha256:"e".repeat(64)};
}
async function hash(raw: string) { return [...new Uint8Array(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(raw)))].map(v=>v.toString(16).padStart(2,"0")).join(""); }
function canonical(v:unknown):string { if(Array.isArray(v))return `[${v.map(canonical).join(",")}]`;if(v&&typeof v==="object")return `{${Object.keys(v).sort().map(k=>`${JSON.stringify(k)}:${canonical((v as Record<string,unknown>)[k])}`).join(",")}}`;return JSON.stringify(v); }
async function files(value: ReturnType<typeof control>) {
  const body={...value}; delete (body as Partial<typeof body>).content_sha256;
  value.content_sha256=await hash(canonical(body));const raw=canonical(value);
  return {result:new Blob([raw]),manifest:new Blob([JSON.stringify({schema:"geophysics.supplied-profile-manifest/v1",result:{name:"result.json",bytes:new TextEncoder().encode(raw).byteLength,sha256:await hash(raw)},method:value.method,source_sha256:value.original.sha256,content_sha256:value.content_sha256,configuration_sha256:await hash(canonical(value.numerical_settings))})])};
}
describe("supplied profile original-byte and numerical display admission",()=>{
  it("bounds BOTH original files before either read",async()=>{
    const read=vi.fn();await expect(readProfileFiles({size:33554433,arrayBuffer:read} as unknown as Blob,new Blob(["{}"])) ).rejects.toThrow();
    await expect(readProfileFiles({size:1,arrayBuffer:read} as unknown as Blob,{size:65537,arrayBuffer:read} as unknown as Blob)).rejects.toThrow();expect(read).not.toHaveBeenCalled();
  });
  it("binds content and original result bytes without physics replay",async()=>{
    const c=control(), f=await files(c), admitted=await readProfileFiles(f.result,f.manifest);
    expect(admitted.result).toEqual(c);expect(admitted.physicsReplayed).toBe(false);
    await expect(readProfileFiles(new Blob([await f.result.text()+" "]),f.manifest)).rejects.toThrow();
  });
  it("returns exact native cell and acquisition identity",()=>{
    const c=control(), before=JSON.stringify(c), parsed=parseProfileResult(c);
    const picked=profileSelection(parsed,0,2,1);
    expect(picked.row.index).toBe(2);expect(picked.row.sensors_zero_based).toEqual([0,3,1,2]);
    expect(picked.row.observed).toBe(3);expect(picked.cell.value).toBe(200);
    expect(picked.cell.nodes_m).toEqual([[1,0],[1,-1],[0,-1]]);expect(JSON.stringify(c)).toBe(before);
  });
  it.each([
    (c:ReturnType<typeof control>)=>{c.scope.truth_available=true;},
    c=>{c.metadata.frame.coordinate_unit="ft";},
    c=>{c.metadata.source.rights.processing_allowed=false;},
    c=>{c.engine_report.inverse.signed_residual_r_ohm[0]=10;},
    c=>{c.engine_report.inverse.model_resistivity_ohm_m[0]=-1;},
    c=>{c.engine_report.inverse.parameter_mesh.cell_node_ids[0]=[0,0,2];},
    c=>{c.engine_report.inverse.parameter_mesh.node_xz_m[1]=[0,0];},
    c=>{c.engine_report.source_id="false-source";},
    c=>{c.engine_report.split.heldout_rows=[0,2,3];},
    c=>{c.engine_report.truth={} as never;},
  ] satisfies ((c:ReturnType<typeof control>)=>void)[])("rejects malformed scientific contract %#",mutate=>{const c=control();mutate(c);expect(()=>parseProfileResult(c)).toThrow();});
  it("retains genuine QC-only result without inventing model",()=>{
    const c=control();c.engine_report.inverse_status="ineligible";delete (c.engine_report as Partial<typeof c.engine_report>).inverse;
    expect(parseProfileResult(c).models).toHaveLength(0);
  });
  for(const key of ["GEOPHYSICS_PROFILE_ERT","GEOPHYSICS_PROFILE_TRAVELTIME"]){
    it.skipIf(!process.env[key])(`admits actual external producer bytes ${key}`,async()=>{
      const root=process.env[key]!;
      const result=new Blob([readFileSync(join(root,"result.json"))]),manifest=new Blob([readFileSync(join(root,"manifest.json"))]);
      const admitted=await readProfileFiles(result,manifest);
      expect(admitted.verdict).toBe("passed");expect(admitted.models.length).toBe(key.endsWith("ERT")?1:2);
      for(const m of admitted.models){expect(m.mesh!.cells.length).toBe(m.values.length);expect(m.held.length).toBeGreaterThan(0);}
    });
  }
});
