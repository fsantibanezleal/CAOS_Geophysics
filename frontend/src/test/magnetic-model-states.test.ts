import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { describe, expect, it } from "vitest";
import { magneticCells, magneticStateCells, parseMagneticView, verifyMagneticView, type MagneticArray, type MagneticView } from "../api/magnetic-result";

const path=process.env.GEOPHYSICS_MAGNETIC_STATE_BROWSER_CONTROL;
if(!path)throw Error("Supply retained actual selected-final audit extraction control; no invented actual fit");
const raw=readFileSync(path),control=JSON.parse(raw.toString("utf8"));
if(control.schema!=="magnetic-model-state-browser-control-1"||control.nonzero_fit!==false||control.host_qualified!==false||control.accepted_method!==false||control.extraction_only!==true)throw Error("Actual extraction-only fixture required");
const actual=control.view as MagneticView;
function descriptor(data:number[],shape:number[],dtype:"float64"|"int64"="float64"):MagneticArray {
  const bytes=new Uint8Array(8*data.length),view=new DataView(bytes.buffer);
  data.forEach((x,i)=>dtype==="float64"?view.setFloat64(8*i,x,true):view.setBigInt64(8*i,BigInt(x),true));
  return {dtype,shape,data,sha256:createHash("sha256").update(bytes).digest("hex")};
}

describe("saved selected-final native model arrays, not scientific admission",()=>{
  it("verifies the actual retained one-model seven-cell audit projection without inventing motion",async()=>{
    const value=await verifyMagneticView(actual,actual.binding);
    expect(value.schema).toBe("magnetic-owner-result-view-2");
    expect(value.model_states!.candidate).toBe("b07-l2");
    expect(value.model_states!.q_models.shape).toEqual([1,7]);
    expect(value.model_states!.audit_sha256).toBe("1b80e987438af768ec877a750b8452ddd8418af9faad84a90a507741a69e46da");
    expect(magneticStateCells(value,0)).toEqual(magneticCells(value));
    expect(value.history[Number(value.model_states!.history_indices.data[0])].inner_iteration).toBe(0);
    expect(Object.values(value.claims).every(x=>x===false)).toBe(true);
    expect(createHash("sha256").update(readFileSync(path!)).digest("hex")).toBe(createHash("sha256").update(raw).digest("hex"));
  });
  it.each(["unknown","missing","candidate","fold","source_hash","audit_hash","unit","scale","count","shape","index","index_fraction","history_candidate","history_fold","history_phase","history_failed","q_conversion","final_model"])("refuses structural or native binding drift: %s",attack=>{
    const v=structuredClone(actual),s=v.model_states!;
    if(attack==="unknown")Object.assign(s,{invented_state:true});
    else if(attack==="missing")delete (v as Partial<MagneticView>).model_states;
    else if(attack==="candidate")s.candidate="b06-l2";
    else if(attack==="fold")Object.assign(s,{fold:0});
    else if(attack==="source_hash")s.source_inventory_sha256="unknown";
    else if(attack==="audit_hash")s.audit_sha256="unknown";
    else if(attack==="unit")Object.assign(s,{physical_unit:"nT"});
    else if(attack==="scale")Object.assign(s,{physical_scale:.1});
    else if(attack==="count")s.q_models.shape[0]=202;
    else if(attack==="shape")s.chi_si.shape=[7];
    else if(attack==="index")s.history_indices.data[0]=v.history.length;
    else if(attack==="index_fraction")s.history_indices.data[0]=.5;
    else if(attack.startsWith("history_")) {
      const h=v.history[Number(s.history_indices.data[0])];
      if(attack==="history_candidate")h.candidate="b06-l2";
      if(attack==="history_fold")h.fold=0;
      if(attack==="history_phase")h.phase="irls_fixed";
      if(attack==="history_failed")h.status="failed";
    }
    else if(attack==="q_conversion")s.q_models.data[0]=1;
    else if(attack==="final_model"){s.q_models.data[0]=1;s.chi_si.data[0]=.01;}
    expect(()=>parseMagneticView(v,v.binding)).toThrow();
  });
  it.each(["q_models","chi_si","history_indices"] as const)("checks exact native descriptor SHA before replay: %s",async name=>{
    const v=structuredClone(actual);v.model_states![name].sha256="0".repeat(64);
    await expect(verifyMagneticView(v,v.binding)).rejects.toThrow("native descriptor SHA256 mismatch");
  });
  it("independently compares every saved q row with its mapped history hash",async()=>{
    const v=structuredClone(actual);v.history[Number(v.model_states!.history_indices.data[0])].model_sha256="0".repeat(64);
    await expect(verifyMagneticView(v,v.binding)).rejects.toThrow("saved q-model history SHA256 mismatch");
  });
  it("keeps legacy view1 closed and objective-only",async()=>{
    const v=structuredClone(actual);delete v.model_states;v.schema="magnetic-owner-result-view-1";
    const parsed=await verifyMagneticView(v,v.binding);
    expect(magneticStateCells(parsed,0)).toEqual(magneticCells(parsed));
    expect(()=>magneticStateCells(parsed,1)).toThrow("legacy has no saved states");
    expect(()=>parseMagneticView({...v,model_states:actual.model_states},v.binding)).toThrow("closed fields");
  });
  it.each([-1,.5,1,NaN,Infinity])("refuses an unrecorded state index %s",index=>{
    expect(()=>magneticStateCells(actual,index)).toThrow("saved state index");
  });
  it("replays two explicit authored structural states without interpolation (not an actual fit fixture)",async()=>{
    const v=structuredClone(actual),s=v.model_states!,a=7;
    const first=[1,...Array(a-1).fill(0)],final=Array(a).fill(0);
    const h=v.history[Number(s.history_indices.data[0])];
    const initial={...h,model_sha256:descriptor(first,[a]).sha256,inner_iteration:0};
    const terminal={...h,inner_iteration:1};
    v.history.push(initial,terminal);
    s.q_models=descriptor([...first,...final],[2,a]);s.chi_si=descriptor([...first.map(x=>x*.01),...final],[2,a]);
    s.history_indices=descriptor([v.history.length-2,v.history.length-1],[2],"int64");
    const parsed=await verifyMagneticView(v,v.binding);
    expect(magneticStateCells(parsed,0)[0].chi_si).toBe(.01);
    expect(magneticStateCells(parsed,1)[0].chi_si).toBe(0);
    expect(()=>magneticStateCells(parsed,.5)).toThrow();
    s.history_indices=descriptor([v.history.length-1,v.history.length-2],[2],"int64");
    expect(()=>parseMagneticView(v,v.binding)).toThrow("exact state/history mapping");
  });
});
