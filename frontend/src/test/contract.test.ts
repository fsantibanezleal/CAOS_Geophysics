import {describe,expect,it,vi} from 'vitest';
import {readFileSync} from 'node:fs';
import {gzipSync} from 'node:zlib';
import {mtForward} from '../mt';
import {extent,sliceVolume,preferredSection,loadArtifact} from '../science';
const read=(p:string)=>JSON.parse(readFileSync(new URL(`../../../data/derived/v2/${p}`,import.meta.url),'utf8'));
describe('scientific rendering contracts',()=>{
 it('preserves x-fast mesh and downward depth in sections',()=>{expect(sliceVolume([0,1,2,3,4,5,6,7],[2,2,2],0)).toEqual([[4,5],[0,1]]);});
 it('opens a volume at the plane with the broadest resolvable body, with a deterministic empty-volume fallback',()=>{
  const volume=Array(4*5*6).fill(0);
  for(let z=1;z<4;z++)for(let x=1;x<5;x++)volume[(4-1-z)*5*6+3*6+x]=2;
  expect(preferredSection(volume,[4,5,6])).toBe(3);
  expect(preferredSection(Array(120).fill(0),[4,5,6])).toBe(2);
  expect(preferredSection([1,2],[4,5,6])).toBe(0);
 });
 it('handles empty and constant plot scales',()=>{expect(extent([])).toEqual([0,1]);expect(extent([3,3])).toEqual([2,4]);});
 it('matches halfspace apparent resistivity and phase',()=>{const c=mtForward([100],[],[.001,1,1000]);c.apparent.forEach(v=>expect(v).toBeCloseTo(100,10));c.phase.forEach(v=>expect(v).toBeCloseTo(45,10));});
 it('matches offline layered impedance for every MT case and variant',()=>{const cat=read('catalog.json');for(const c of cat.cases.filter((x:{family:string})=>x.family==='mt'))for(const v of c.variants){const r=read(v.path);const actual=mtForward(r.truth,r.thickness,r.frequencies);actual.apparent.forEach((x,i)=>expect(Math.abs(x-r.clean.apparent[i])/x).toBeLessThan(2e-6));actual.phase.forEach((x,i)=>expect(Math.abs(x-r.clean.phase[i])).toBeLessThan(2e-5));}});
 it('rejects invalid live model inputs',()=>{expect(()=>mtForward([0],[],[1])).toThrow();expect(()=>mtForward([1,2],[],[1])).toThrow();expect(()=>mtForward([1],[],[NaN])).toThrow();});
 it('rejects unavailable artifacts without generating fallback results',async()=>{const request=vi.spyOn(globalThis,'fetch').mockResolvedValue(new Response('Unavailable',{status:503}));try{await expect(loadArtifact('missing.json')).rejects.toThrow('HTTP 503: missing.json');}finally{request.mockRestore();}});
 it('decodes the exact JSON bytes from the compressed FWI transport',async()=>{
  const expected={id:'FWI_LAYERED',wavefields:[[[0,1],[-1,0]]],methods:{'fwi-l2':{frames:[[1800,1950],[1810,1960]]}}};
  const compressed=gzipSync(Buffer.from(JSON.stringify(expected)));
  const request=vi.spyOn(globalThis,'fetch').mockResolvedValue(new Response(compressed as unknown as BodyInit,{status:200}));
  try{await expect(loadArtifact('FWI_LAYERED/reference.json')).resolves.toEqual(expected);expect(String(request.mock.calls[0][0])).toContain('FWI_LAYERED/reference.json.gz');}
  finally{request.mockRestore();}
 });
 it('accepts browser-decoded JSON when the gzip transport has Content-Encoding',async()=>{
  const expected={id:'FWI_LAYERED',wavefields:[[[0,1],[-1,0]]]};
  const request=vi.spyOn(globalThis,'fetch').mockResolvedValue(new Response(JSON.stringify(expected),{
   status:200,headers:{'content-encoding':'gzip','content-type':'application/json'},
  }));
  try{await expect(loadArtifact('FWI_LAYERED/reference.json')).resolves.toEqual(expected);expect(String(request.mock.calls[0][0])).toContain('FWI_LAYERED/reference.json.gz');}
  finally{request.mockRestore();}
 });
 it('loads compressed FWI condition variants from their gzip sidecars',async()=>{
  const expected={id:'FWI_LAYERED',variant:'noise'};
  const request=vi.spyOn(globalThis,'fetch').mockResolvedValue(new Response(gzipSync(Buffer.from(JSON.stringify(expected))) as unknown as BodyInit,{status:200}));
  try{await expect(loadArtifact('FWI_LAYERED/noise.json')).resolves.toEqual(expected);expect(String(request.mock.calls[0][0])).toContain('FWI_LAYERED/noise.json.gz');}
  finally{request.mockRestore();}
 });
 it('finishes a started large FWI response before requesting the next case after cancellation',async()=>{
  let finishFirst:(response:Response)=>void=()=>{};
  const first=new Promise<Response>(resolve=>{finishFirst=resolve;});
  const paths:string[]=[];
  const request=vi.spyOn(globalThis,'fetch').mockImplementation(async(input)=>{
   const url=String(input);paths.push(url);
   return paths.length===1?first:new Response(gzipSync(Buffer.from('{"id":"FWI_FAULT"}')) as unknown as BodyInit,{status:200});
  });
  const controller=new AbortController();
  const stale=loadArtifact<{id:string}>('FWI_LAYERED/reference.json',controller.signal);
  await Promise.resolve();
  controller.abort();
  await expect(stale).rejects.toMatchObject({name:'AbortError'});
  const next=loadArtifact<{id:string}>('FWI_FAULT/reference.json');
  expect(paths).toHaveLength(1);
  finishFirst(new Response(gzipSync(Buffer.from('{"id":"FWI_LAYERED"}')) as unknown as BodyInit,{status:200}));
  await expect(next).resolves.toEqual({id:'FWI_FAULT'});
  expect(paths).toHaveLength(2);
  expect(paths[0]).toContain('FWI_LAYERED/reference.json');
  expect(paths[1]).toContain('FWI_FAULT/reference.json');
  request.mockRestore();
 });
});
