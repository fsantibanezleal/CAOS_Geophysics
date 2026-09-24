import {describe,expect,it,vi} from 'vitest';
import {readFileSync} from 'node:fs';
import {mtForward} from '../mt';
import {extent,sliceVolume,loadArtifact} from '../science';
const read=(p:string)=>JSON.parse(readFileSync(new URL(`../../../data/derived/v2/${p}`,import.meta.url),'utf8'));
describe('scientific rendering contracts',()=>{
 it('preserves x-fast mesh and downward depth in sections',()=>{expect(sliceVolume([0,1,2,3,4,5,6,7],[2,2,2],0)).toEqual([[4,5],[0,1]]);});
 it('handles empty and constant plot scales',()=>{expect(extent([])).toEqual([0,1]);expect(extent([3,3])).toEqual([2,4]);});
 it('matches halfspace apparent resistivity and phase',()=>{const c=mtForward([100],[],[.001,1,1000]);c.apparent.forEach(v=>expect(v).toBeCloseTo(100,10));c.phase.forEach(v=>expect(v).toBeCloseTo(45,10));});
 it('matches offline layered impedance for every MT case and variant',()=>{const cat=read('catalog.json');for(const c of cat.cases.filter((x:{family:string})=>x.family==='mt'))for(const v of c.variants){const r=read(v.path);const actual=mtForward(r.truth,r.thickness,r.frequencies);actual.apparent.forEach((x,i)=>expect(Math.abs(x-r.clean.apparent[i])/x).toBeLessThan(2e-6));actual.phase.forEach((x,i)=>expect(Math.abs(x-r.clean.phase[i])).toBeLessThan(2e-5));}});
 it('rejects invalid live model inputs',()=>{expect(()=>mtForward([0],[],[1])).toThrow();expect(()=>mtForward([1,2],[],[1])).toThrow();expect(()=>mtForward([1],[],[NaN])).toThrow();});
 it('rejects unavailable artifacts without generating fallback results',async()=>{const request=vi.spyOn(globalThis,'fetch').mockResolvedValue(new Response('Unavailable',{status:503}));try{await expect(loadArtifact('missing.json')).rejects.toThrow('HTTP 503: missing.json');}finally{request.mockRestore();}});
});
