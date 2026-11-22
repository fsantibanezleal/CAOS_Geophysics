import { describe, expect, it } from "vitest";
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { parseFwiManifest, readFwiFiles } from "../api/fwi-local-contracts";

const root=process.env.GEOPHYSICS_FWI_GENERATION;
type Item={name:string;size:number;arrayBuffer:()=>Promise<ArrayBuffer>};
function file(name:string,bytes:Uint8Array):Item{return {name,size:bytes.length,arrayBuffer:async()=>new Uint8Array(bytes).buffer};}
const files=()=>readdirSync(root!).map(name=>file(name,new Uint8Array(readFileSync(join(root!,name)))));
describe("actual original full-budget CUDA FWI generation, local inspection only",()=>{
  it.skipIf(!root)("binds every full sample and all terminal saved states",async()=>{
    const admitted=await readFwiFiles(files());
    expect(admitted.physicsReplayed).toBe(false);expect(admitted.manifest.truth).toBeNull();
    expect(admitted.manifest.request.observed.shape).toEqual([3,20,3200]);
    expect(admitted.arrays.observed.length).toBe(192000);
    for(const method of ["fwi-l2","fwi-multiscale"] as const){
      expect(admitted.manifest.methods[method].solver.optimizer_calls).toBe(112);
      expect(admitted.manifest.methods[method].numerical_verdict).toBe("finite-budget");
    }
  });
  it.skipIf(!root)("rejects array damage, unknown/missing members and altered physical/state claims",async()=>{
    const actual=files();await expect(readFwiFiles(actual.slice(1))).rejects.toThrow();
    await expect(readFwiFiles([...actual,file("secret.bin",new Uint8Array([1]))])).rejects.toThrow();
    const broken=actual.map(item=>item.name==="observed.f32"?file(item.name,new Uint8Array(item.size)):item);
    await expect(readFwiFiles(broken)).rejects.toThrow();
    const bytes=new Uint8Array(readFileSync(join(root!,"manifest.json"))),source=parseFwiManifest(bytes);
    for(const kind of ["truth","dt","shape","units","mask","iteration","verdict"]){
      const m=structuredClone(source);
      if(kind==="truth") (m as unknown as {truth:unknown}).truth=[[2200]];
      if(kind==="dt")m.request.acquisition.dt_s=.004;
      if(kind==="shape")m.arrays.observed.shape=[20,3,3200];
      if(kind==="units")m.arrays["fwi-l2-model"].units="km/s";
      if(kind==="mask")m.active_receivers[2]=true;
      if(kind==="iteration")m.methods["fwi-l2"].state_identity.final_frame_index=0;
      if(kind==="verdict")(m.methods["fwi-l2"] as unknown as {numerical_verdict:string}).numerical_verdict="recovered";
      expect(()=>parseFwiManifest(new TextEncoder().encode(JSON.stringify(m)))).toThrow();
    }
    expect(()=>parseFwiManifest(new TextEncoder().encode('{"id":"a","id":"b"}'))).toThrow();
  });
});
