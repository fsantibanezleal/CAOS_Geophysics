/** UI editing of the existing explicit contract, never numerical method defaults. */
import type { RawAsset } from "../api/contracts";

type Draft=Record<string,unknown>;
const object=(v:unknown):v is Draft=>v!==null&&typeof v==="object"&&!Array.isArray(v);
export function readWaveformDraft(text:string):Draft {
  if(new TextEncoder().encode(text).length>65536)throw new Error("Request exceeds 64 KiB");
  const value=text.trim()?JSON.parse(text):{};
  if(!object(value))throw new Error("Scientific request must be an object");
  return value;
}
export function editWaveformDraft(text:string,path:(string|number)[],value:unknown):string {
  const draft=readWaveformDraft(text);let node:Record<string|number,unknown>=draft;
  if(!path.length||path.some(p=>["__proto__","constructor","prototype"].includes(String(p))))throw new Error("Invalid control path");
  for(let i=0;i<path.length-1;i++){
    const key=path[i];if(node[key]===undefined)node[key]=typeof path[i+1]==="number"?[]:{};
    if(!object(node[key])&&!Array.isArray(node[key]))throw new Error("Malformed imported field; edit advanced JSON");
    node=node[key] as Record<string|number,unknown>;
  }
  const key=path[path.length-1];if(value===undefined)delete node[key];else node[key]=value;
  return JSON.stringify(draft,null,2);
}
export function editWaveformChannels(text:string,remove?:number):string {
  const draft=readWaveformDraft(text);
  const channels=draft.channels===undefined?[]:draft.channels;
  const rails=draft.adc_rails===undefined&&Array.isArray(channels)&&channels.length===0?[]:draft.adc_rails;
  if(!Array.isArray(channels)||!Array.isArray(rails)||rails.length!==channels.length)throw new Error("Malformed channel/ADC evidence; edit advanced JSON");
  if(remove!==undefined&&(!Number.isInteger(remove)||remove<0||remove>=channels.length))throw new Error("Invalid channel index");
  if(remove===undefined&&channels.length>=3)throw new Error("Channel limit");
  const initial=text.trim()?text:JSON.stringify({schema:"caos.local-waveform-request.v1",representation:"unrestituted_integer_counts"});
  const next=editWaveformDraft(initial,["channels"],remove===undefined?[...channels,{}]:channels.filter((_,i)=>i!==remove));
  return editWaveformDraft(next,["adc_rails"],remove===undefined?[...rails,null]:rails.filter((_,i)=>i!==remove));
}
export function requestBinding(asset:Pick<RawAsset,"asset_id"|"sha256"> & {physical_metadata:{geometry:Record<string,unknown>}}|undefined,request:string):string {
  return asset?JSON.stringify([asset.asset_id,asset.sha256,asset.physical_metadata.geometry.stationxml_asset_id,request]):"";
}
const exact=(v:unknown,names:string)=>object(v)&&Object.keys(v).sort().join(" ")===names.split(" ").sort().join(" ");
const finite=(v:unknown):v is number=>typeof v==="number"&&Number.isFinite(v);
export function waveformUtcUs(text:unknown):number {
  if(typeof text!=="string"||!/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?Z$/.test(text))return NaN;
  const whole=text.slice(0,19)+"Z",ms=Date.parse(whole);
  if(!Number.isFinite(ms)||Number(text.slice(0,4))>2100||new Date(ms).toISOString().slice(0,19)!==text.slice(0,19))return NaN;
  const micros=Number((text.match(/\.(\d+)Z$/)?.[1]??"").padEnd(6,"0"));
  const total=ms*1000+micros;return Number.isSafeInteger(total)&&total>=0?total:NaN;
}
/** Local completeness/constraint feedback. API revalidates the canonical request. */
export function draftIssues(text:string):string[] {
  let d:Draft;try{d=readWaveformDraft(text);}catch{return ["JSON object / 64 KiB"];}
  const issues:string[]=[];
  if(!exact(d,"schema channels conditioning_start_utc conditioning_end_utc analysis_start_utc analysis_end_utc representation source adc_rails processing")||d.schema!=="caos.local-waveform-request.v1"||d.representation!=="unrestituted_integer_counts")issues.push("request schema");
  const channels=d.channels;
  if(!Array.isArray(channels)||channels.length<1||channels.length>3||channels.some(c=>!exact(c,"network station location channel")||!object(c)||!["network","station","location","channel"].every(k=>typeof c[k]==="string"&&new RegExp(k==="network"?"^[A-Z0-9]{1,2}$":k==="station"?"^[A-Z0-9]{1,5}$":k==="location"?"^[A-Z0-9]{0,2}$":"^[A-Z0-9]{3}$").test(c[k] as string)))||new Set(channels.map(c=>object(c)?[c.network,c.station,c.location,c.channel].join("."):"invalid")).size!==channels.length||new Set(channels.map(c=>object(c)?`${c.network}.${c.station}`:"invalid")).size!==1)issues.push("channels");
  const [a,b,c,e]=[d.conditioning_start_utc,d.conditioning_end_utc,d.analysis_start_utc,d.analysis_end_utc].map(waveformUtcUs);
  if(![a,b,c,e].every(Number.isFinite)||b-a<10000000||b-a>300000000||!(a<=c&&c<e&&e<=b)||e-c<5000000)issues.push("UTC windows");
  const source=d.source;
  if(!exact(source,"kind citation provider_url declared_sha256 rights processing_statement")||!object(source)||!["user","provider"].includes(String(source.kind))||!["private-use-attested","reviewed-public-scsn"].includes(String(source.rights))||!["citation","processing_statement"].every(k=>typeof source[k]==="string"&&Boolean((source[k] as string).trim()))||!(source.provider_url===null||typeof source.provider_url==="string"&&/^https:\/\/[^\s/]+(?:\/[^\s]*)?$/.test(source.provider_url))||!(source.declared_sha256===null||typeof source.declared_sha256==="string"&&/^[a-f0-9]{64}$/.test(source.declared_sha256)))issues.push("source / rights");
  if(!Array.isArray(d.adc_rails)||!Array.isArray(channels)||d.adc_rails.length!==channels.length||d.adc_rails.some(r=>r!==null&&(!exact(r,"minimum_count maximum_count evidence")||!object(r)||!Number.isInteger(r.minimum_count)||!Number.isInteger(r.maximum_count)||!finite(r.minimum_count)||!finite(r.maximum_count)||!(r.minimum_count>=-2147483648&&r.minimum_count<r.maximum_count&&r.maximum_count<=2147483647)||typeof r.evidence!=="string"||!r.evidence.trim())))issues.push("adc_rails");
  const p=object(d.processing)?d.processing:{};
  if(!exact(p,"output prefilter_hz water_level_db taper_fraction bandpass_hz filter_order filter_mode edge_guard_s sta_s lta_s threshold_on threshold_off refractory_s welch_segment_samples")||p.output!=="native"||p.filter_mode!=="offline-zero-phase")issues.push("processing schema");
  for(const [key,lo,hi] of [["taper_fraction",.01,.10],["edge_guard_s",0,150],["sta_s",.05,2],["lta_s",.5,20],["refractory_s",0,10]] as const)if(!finite(p[key])||p[key]<lo||p[key]>hi)issues.push(`processing.${key}`);
  if(!(p.water_level_db===null||finite(p.water_level_db)&&p.water_level_db>=20&&p.water_level_db<=120))issues.push("processing.water_level_db");
  if(!finite(p.threshold_on)||!finite(p.threshold_off)||!(1<p.threshold_off&&p.threshold_off<p.threshold_on&&p.threshold_on<=100)||!(finite(p.sta_s)&&finite(p.lta_s)&&p.sta_s<p.lta_s))issues.push("STA/LTA windows / thresholds");
  const pre=p.prefilter_hz,band=p.bandpass_hz;
  const ordered=(v:unknown,n:number):v is number[]=>Array.isArray(v)&&v.length===n&&v.every(finite)&&v.every((x,i)=>i===0||x>v[i-1]);
  if(!ordered(pre,4)||!ordered(band,2)||pre[0]<.05||!(pre[1]<=band[0]&&band[1]<=pre[2]))issues.push("prefilter / bandpass");
  if(!finite(p.filter_order)||!Number.isInteger(p.filter_order)||p.filter_order<2||p.filter_order>6)issues.push("processing.filter_order");
  const m=p.welch_segment_samples;
  if(!finite(m)||!Number.isInteger(m)||m<64||m>8192||(m&(m-1))!==0)issues.push("processing.welch_segment_samples");
  return issues;
}
export function responseDisplay(arrays:Record<string,number[]>,descriptors:{name:string;unit:string}[]) {
  const f=arrays.response_frequency_hz,r=arrays.response_real,i=arrays.response_imag;
  if(!f&&!r&&!i)return null;
  const rd=descriptors.find(d=>d.name==="response_real"),id=descriptors.find(d=>d.name==="response_imag");
  if(!f||!r||!i||f.length!==r.length||r.length!==i.length||!rd||!id||rd.unit!==id.unit)throw new Error("Complex response array contract");
  const amplitude=r.map((v,n)=>Math.hypot(v,i[n])),phase=r.map((v,n)=>Math.atan2(i[n],v));
  if(![...f,...amplitude,...phase].every(Number.isFinite))throw new Error("Complex response display is nonfinite");
  return {frequency:f,amplitude,phase,amplitudeUnit:rd.unit};
}
