import { describe, expect, it } from "vitest";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import actual from "./fixtures/waveform-authored-calculation.json";
import { draftIssues, editWaveformDraft, editWaveformChannels, readWaveformDraft, requestBinding, responseDisplay } from "../components/waveform-request";
import { WaveformRequestControls } from "../components/WaveformRequestControls";

const request=JSON.stringify(actual.request.submitted);
describe("M08 explicit structured request and measured response",()=>{
  it("does not seed numerical parameters, NSLC or provider declarations",()=>{
    expect(readWaveformDraft("")).toEqual({});
    const draft=readWaveformDraft(editWaveformDraft("",["processing","sta_s"],0.25));
    expect(draft.processing).toEqual({sta_s:0.25});
    expect(draft.channels).toBeUndefined();expect(draft.source).toBeUndefined();
    expect(draftIssues(JSON.stringify(draft)).length).toBeGreaterThan(0);
  });
  it("roundtrips an exact authored request and keeps source/rails unchanged",()=>{
    expect(draftIssues(request)).toEqual([]);
    const updated=readWaveformDraft(editWaveformDraft(request,["processing","sta_s"],0.3));
    expect(updated).toEqual({...actual.request.submitted,processing:{...actual.request.submitted.processing,sta_s:0.3}});
    expect(actual.request.submitted.processing.sta_s).toBe(0.2);
  });
  it("keeps invalid/unknown imported fields rather than repairing them",()=>{
    const imported=JSON.stringify({...actual.request.submitted,undeclared:true});
    const updated=editWaveformDraft(imported,["processing","sta_s"],"invalid");
    expect(readWaveformDraft(updated).undeclared).toBe(true);expect(draftIssues(updated).length).toBeGreaterThan(0);
    expect(()=>editWaveformDraft("{broken",["processing","sta_s"],0.3)).toThrow();
    expect(()=>readWaveformDraft("[]")).toThrow();
    expect(draftIssues(editWaveformDraft(request,["processing","sta_s"],undefined))).toContain("processing.sta_s");
  });
  it("adds/removes matching channel and ADC rows without changing existing evidence",()=>{
    const added=readWaveformDraft(editWaveformChannels(request));
    expect(added.channels).toEqual([...actual.request.submitted.channels,{}]);
    expect(added.adc_rails).toEqual([...actual.request.submitted.adc_rails,null]);
    expect(readWaveformDraft(editWaveformChannels(JSON.stringify(added),1))).toEqual(actual.request.submitted);
    expect(readWaveformDraft(editWaveformChannels("")).channels).toEqual([{}]);
  });
  it("refuses malformed imported channel/ADC containers instead of discarding evidence",()=>{
    for(const change of [{channels:{evidence:"retain"}},{adc_rails:{evidence:"retain"}},{adc_rails:[]}]){
      const text=JSON.stringify({...actual.request.submitted,...change});
      expect(()=>editWaveformChannels(text)).toThrow();expect(()=>editWaveformChannels(text,0)).toThrow();
    }
  });
  it.each(["sta_s","lta_s","edge_guard_s","filter_order","welch_segment_samples"])("rejects numeric strings/booleans/null for %s",key=>{
    for(const value of ["1",true,null])expect(draftIssues(editWaveformDraft(request,["processing",key],value))).toContain(`processing.${key}`);
  });
  it("retains microsecond UTC and rejects normalized invalid dates",()=>{
    const aligned=readWaveformDraft(request);aligned.conditioning_start_utc="2020-01-01T00:00:00.008300Z";
    expect(draftIssues(JSON.stringify(aligned))).toEqual([]);
    aligned.conditioning_start_utc="2020-02-30T00:00:00Z";
    expect(draftIssues(JSON.stringify(aligned))).toContain("UTC windows");
  });
  it("requires explicit empty location and source-bound review for each exact draft",()=>{
    expect(draftIssues(editWaveformDraft(request,["channels",0,"location"],undefined))).toContain("channels");
    const asset={asset_id:"owned",sha256:"a".repeat(64),physical_metadata:{geometry:{stationxml_asset_id:"xml"}}};
    const binding=requestBinding(asset,request);
    expect(binding).not.toBe(requestBinding({...asset,asset_id:"other"},request));
    expect(binding).not.toBe(requestBinding(asset,editWaveformDraft(request,["processing","sta_s"],0.3)));
    expect(requestBinding(undefined,request)).toBe("");
  });
  it("rejects interdependent frequency/trigger/Welch conditions without changing values",()=>{
    for(const [path,value] of [["threshold_off",4],["welch_segment_samples",127],["prefilter_hz",[0.5,1,0.9,25]],["bandpass_hz",[0.1,10]] ] as const){
      expect(draftIssues(editWaveformDraft(request,["processing",path],value)).length).toBeGreaterThan(0);
    }
  });
  it("derives amplitude and principal phase from exact complex samples/frequency/units only",()=>{
    const arrays={response_frequency_hz:[0,1,2],response_real:[3,-1,0],response_imag:[4,0,-2]},before=JSON.stringify(arrays);
    const curves=responseDisplay(arrays,[{name:"response_real",unit:"counts/m/s2"},{name:"response_imag",unit:"counts/m/s2"}]);
    expect(curves).toEqual({frequency:[0,1,2],amplitude:[5,1,2],phase:[Math.atan2(4,3),Math.PI,-Math.PI/2],amplitudeUnit:"counts/m/s2"});
    expect(JSON.stringify(arrays)).toBe(before);expect(responseDisplay({},[])).toBeNull();
    expect(()=>responseDisplay({...arrays,response_real:[3]},[{name:"response_real",unit:"counts/m/s2"},{name:"response_imag",unit:"counts/m/s2"}])).toThrow();
  });
  it.each([false,true])("renders grouped controls with no seeded scientific values, Spanish=%s",es=>{
    const html=renderToStaticMarkup(createElement(WaveformRequestControls,{request:"",onChange:()=>{},es,disabled:false}));
    for(const label of es?["Sección de solicitud","NSLC","Respuesta y prefiltro","Filtro acausal","STA/LTA","PSD Welch"]:["Request section","NSLC","Response and prefilter","Acausal filter","STA/LTA","Welch PSD"])expect(html).toContain(label);
    expect(html).toContain('value="utc" selected');expect(html).toContain(es?"Inicio de acondicionamiento UTC":"Conditioning start UTC");
    expect(html).not.toContain('aria-label="STA [s]"');
    expect(html).not.toContain('value="0.2"');expect(html).not.toContain('value="60"');expect(html).not.toContain("font-family");
  });
});
