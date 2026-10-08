import { describe,it,expect } from 'vitest';
import {profileOrdinal,sameDisplayWindow,type DisplayWindowBinding} from './display';
import { parseStart,parseJob,parseRepresentation,type ArrayRef,type FileIdentity } from './contract';
import { readArrayWindow,readCrossoverWindow } from './members';
import { parseRegistry,registryReader,type RegistryPage } from './registry';

const id=(index:number)=>`00000000-0000-0000-0000-${String(index).padStart(12,'0')}`;
describe('display-only source-order selection',()=>{
  it('maps actual SVG coordinates independently of CSS letterboxing',()=>{
    expect(profileOrdinal(55,363)).toBe(0);
    expect(profileOrdinal(615,363)).toBe(362);
    expect(profileOrdinal(335,363)).toBe(181);
    expect(profileOrdinal(-100,363)).toBe(0);
    expect(profileOrdinal(999,363)).toBe(362);
    expect(profileOrdinal(335,1)).toBe(0);
  });
  it('does not turn invalid display geometry into a fabricated ordinal',()=>{
    for(const x of [NaN,Infinity,-Infinity])expect(profileOrdinal(x,363)).toBeNull();
    for(const rows of [0,4097,1.5,NaN,Infinity])expect(profileOrdinal(55,rows)).toBeNull();
  });
});
describe('asynchronous display-window custody',()=>{
  const binding:DisplayWindowBinding={job_id:id(6),result_sha256:'a'.repeat(64),view:'lines',selection:2,first:4096};
  it('matches the exact job, bytes, scientific view, channel/plane and window',()=>{
    expect(sameDisplayWindow(binding,{...binding})).toBe(true);
    for(const changed of [{job_id:id(7)},{result_sha256:'b'.repeat(64)},
      {view:'validation' as const},{view:'grid' as const},{selection:1},{first:0}])
      expect(sameDisplayWindow(binding,{...binding,...changed})).toBe(false);
  });
  it('does not reuse equal-hash evidence across jobs or equal-ordinal evidence across views',()=>{
    for(const view of ['lines','validation','grid'] as const){
      const saved={...binding,view,selection:0,first:0};
      expect(sameDisplayWindow(saved,{...saved,job_id:id(8)})).toBe(false);
      expect(sameDisplayWindow(saved,{...saved,view:view==='grid'?'lines':'grid'})).toBe(false);
    }
  });
});
const start=()=>({schema:'m03-owner-start/1',dataset_id:id(1),original_asset_id:id(2),metadata_asset_id:id(3),request_asset_id:id(4),
  auxiliary_asset_ids:[id(5)],dataset_sha256:'a'.repeat(64),original_sha256:'b'.repeat(64),metadata_sha256:'c'.repeat(64),request_sha256:'d'.repeat(64),auxiliary_sha256:['e'.repeat(64)]});
const job=()=>({schema:'m03-owner-job/1',job_id:id(6),project_id:id(7),dataset_id:id(1),method:'magnetic_line_survey_v1',state:'queued',cancel_requested:false,
  request_sha256:'f'.repeat(64),result_sha256:null,result_bytes:null,error_code:null,created_at:'2001-01-01T00:00:00Z',started_at:null,finished_at:null});
async function digest(bytes:Uint8Array) {return [...new Uint8Array(await crypto.subtle.digest('SHA-256',new Uint8Array(bytes).buffer))].map(v=>v.toString(16).padStart(2,'0')).join('');}

describe('exact owner contract, not an executor',()=>{
  it('roundtrips eleven required keys and strict owner references',()=>{expect(parseStart(start())).toEqual(start());expect(parseJob(job())).toEqual(job());});
  it.each(['url','worker_module','csv_path','owner_id'])('refuses %s even if harmless-looking',field=>{expect(()=>parseStart({...start(),[field]:'hidden'})).toThrow();});
  it('refuses duplicates, upper hashes, mismatched lists, coercions and missing fields',()=>{
    for(const value of [{...start(),metadata_asset_id:id(2)},{...start(),dataset_sha256:'A'.repeat(64)},
      {...start(),auxiliary_sha256:[]},{...start(),dataset_id:1},{...start(),schema:undefined}]) expect(()=>parseStart(value)).toThrow();
  });
  it('refuses invented state and successful jobs without a terminal byte receipt',()=>{
    for(const value of [{...job(),state:'online'},{...job(),state:'succeeded'},{...job(),state:'running'},
      {...job(),result_bytes:100},{...job(),created_at:'2001-02-30T00:00:00Z'}]) expect(()=>parseJob(value)).toThrow();
  });
  it('keeps new metre axes separate from the legacy grid coordinate role',()=>{
    const axis={array_id:'axis',role:'grid_axis',dtype:'float64',unit:'m',shape:[2],chunk_rows:4096,
      manifest:{name:'array-axis.json',bytes:10,sha256:'0'.repeat(64)},ordered_ids_sha256:'1'.repeat(64),mask_array_id:null};
    expect(parseRepresentation('ArrayRef',axis,2)).toEqual(axis);
    expect(()=>parseRepresentation('ArrayRef',axis,1)).toThrow();
  });
});
describe('bounded actual finite fragments',()=>{
  it('binds crossover table identity, verified bytes, nullable geometry and exact row schema',async()=>{
    const store=new Map<string,Uint8Array>();
    async function member(name:string,value:unknown,lines=false):Promise<FileIdentity> {
      const bytes=new TextEncoder().encode(JSON.stringify(value)+(lines?'\n':''));store.set(name,bytes);
      return {name,bytes:bytes.byteLength,sha256:await digest(bytes)};
    }
    const row={crossover_id:'X0',flight_segment_id:'S0',tie_segment_id:'S1',a:null,b:null,
      constraint_representative:null,easting_m:null,northing_m:null,height_difference_m:null,time_separation_s:null,
      disposition:'rejected',reasons:['parallel_or_collinear'],shared_endpoint_group_id:null,
      tolerance:{coordinate_m:1e-10,determinant_m2:1e-8,matrix_residual_m:1e-10,parameter_dimensionless:1e-12,sine_dimensionless:1e-6}};
    const chunk=await member('table-control-00000000.jsonl',row,true);
    const page=await member('table-control-page-000000.json',{schema:'magnetic-line-manifest-page/1',owner_id:'control',sequence:0,entries:[{...chunk,sequence:0,first_row:0,rows:1}]});
    const root=await member('table-control.json',{schema:'magnetic-line-table-manifest/1',table_id:'control',row_schema:'crossover_geometry',rows:1,
      pages:[{sequence:0,first_row:0,rows:1,file:page}],content_sha256:chunk.sha256});
    const ref={table_id:'control',row_schema:'crossover_geometry',rows:1,manifest:root},signal=new AbortController().signal;
    const read=async(identity:FileIdentity)=>store.get(identity.name)!;
    expect(await readCrossoverWindow(ref,0,1,read,signal)).toEqual([row]);
    await expect(readCrossoverWindow(ref,0,129,read,signal)).rejects.toThrow();
    await expect(readCrossoverWindow({...ref,table_id:'other'},0,1,read,signal)).rejects.toThrow();
    store.get(chunk.name)![0]^=1;
    await expect(readCrossoverWindow(ref,0,1,read,signal)).rejects.toThrow();
  });
  it('decodes exact little-endian values and refuses mutated bytes, excess window and layout',async()=>{
    const store=new Map<string,Uint8Array>();
    async function member(name:string,bytes:Uint8Array):Promise<FileIdentity> {store.set(name,bytes);return{name,bytes:bytes.byteLength,sha256:await digest(bytes)};}
    const payload=new Uint8Array(16),view=new DataView(payload.buffer);view.setFloat64(0,2.5,true);view.setFloat64(8,-7.25,true);
    const chunk=await member('array-control-00000000.bin',payload);
    const page=await member('array-control-page-000000.json',new TextEncoder().encode(JSON.stringify({schema:'magnetic-line-manifest-page/1',owner_id:'control',sequence:0,
      entries:[{...chunk,sequence:0,first_row:0,rows:2}]})));
    const manifest=await member('array-control.json',new TextEncoder().encode(JSON.stringify({schema:'magnetic-line-array-manifest/2',array_id:'control',shape:[2],dtype:'float64',unit:'nT',
      pages:[{sequence:0,first_row:0,rows:2,file:page}],content_sha256:await digest(payload)})));
    const ref:ArrayRef={array_id:'control',role:'magnetic',dtype:'float64',unit:'nT',shape:[2],chunk_rows:4096,manifest,ordered_ids_sha256:'a'.repeat(64),mask_array_id:null};
    const reader=async(identity:FileIdentity)=>store.get(identity.name)!;
    const signal=new AbortController().signal;
    expect((await readArrayWindow(ref,0,2,reader,signal)).cells).toEqual([2.5,-7.25]);
    expect((await readArrayWindow(ref,1,1,reader,signal)).whole_array_content).toBe('not_recomputed');
    await expect(readArrayWindow(ref,0,4097,reader,signal)).rejects.toThrow();
    payload[0]^=1;
    await expect(readArrayWindow(ref,0,2,reader,signal)).rejects.toThrow();
    payload[0]^=1;
    await expect(readArrayWindow({...ref,shape:[3]},0,1,reader,signal)).rejects.toThrow();
  });
});

describe('actual durable UUID registry',()=>{
  function completed() {return parseJob({...job(),state:'succeeded',started_at:'2001-01-01T00:00:00Z',
    finished_at:'2001-01-01T00:00:01Z',result_sha256:'a'.repeat(64),result_bytes:123});}
  function page() {return {schema:'m03-owner-members/1',job_id:id(6),result_sha256:'a'.repeat(64),offset:0,total:1,next_offset:null,
    entries:[{member_id:id(8),name:'result/result.json',bytes:123,sha256:'a'.repeat(64),kind:'result'}]};}
  it('binds exact schema and refuses malformed pagination, paths, duplicate names and extra fields',()=>{
    expect(parseRegistry(page())).toEqual(page());
    for(const wrong of [{...page(),next_offset:1},{...page(),offset:1},{...page(),total:2},{...page(),url:'/x'},
      {...page(),entries:[{...page().entries[0],name:'result/../raw.csv'}]},
      {...page(),total:2,entries:[page().entries[0],page().entries[0]]}]) expect(()=>parseRegistry(wrong)).toThrow();
  });
  it('resolves a real member UUID and never guesses one from a file name',async()=>{
    const calls:string[]=[];
    const read=registryReader(completed(),async()=>parseRegistry(page()),async(entry)=>{calls.push(entry.member_id);return new Uint8Array(123);});
    const identity={name:'result.json',bytes:123,sha256:'a'.repeat(64)};
    await read(identity,new AbortController().signal);
    expect(calls).toEqual([id(8)]);
    await expect(read({...identity,sha256:'b'.repeat(64)},new AbortController().signal)).rejects.toThrow();
    await expect(read({...identity,name:'unknown.bin'},new AbortController().signal)).rejects.toThrow();
  });
  it('refuses stale cross-job/result SHA and aborted generations',async()=>{
    for(const wrong of [{...page(),job_id:id(9)},{...page(),result_sha256:'b'.repeat(64)}]) {
      const read=registryReader(completed(),async()=>parseRegistry(wrong),async()=>{throw new Error('must not read bytes');});
      await expect(read({name:'result.json',bytes:123,sha256:'a'.repeat(64)},new AbortController().signal)).rejects.toThrow();
    }
    const abort=new AbortController();abort.abort();
    await expect(registryReader(completed(),async()=>{throw new Error('no request');},async()=>new Uint8Array())(
      {name:'result.json',bytes:123,sha256:'a'.repeat(64)},abort.signal)).rejects.toThrow();
  });
  it('walks exact sorted 512-entry pages without materializing an unbounded map',async()=>{
    const first={...page(),total:513,next_offset:512,entries:Array.from({length:512},(_,i)=>({member_id:id(i+10),
      name:`result/a-${String(i).padStart(8,'0')}.bin`,bytes:8,sha256:'c'.repeat(64),kind:'chunk'}))};
    const last={...page(),offset:512,total:513};
    const offsets:number[]=[];
    const read=registryReader(completed(),async offset=>{offsets.push(offset);return parseRegistry(offset?last:first);},async()=>new Uint8Array(123));
    await read({name:'result.json',bytes:123,sha256:'a'.repeat(64)},new AbortController().signal);
    expect(offsets).toEqual([0,512]);
    await read({name:'result.json',bytes:123,sha256:'a'.repeat(64)},new AbortController().signal);
    expect(offsets).toEqual([0,512]);
    const changed=registryReader(completed(),async offset=>parseRegistry(offset?{...last,total:514,
      entries:[...last.entries,{...last.entries[0],member_id:id(999),name:'result/z.bin'}]}:first),async()=>new Uint8Array());
    await expect(changed({name:'result.json',bytes:123,sha256:'a'.repeat(64)},new AbortController().signal)).rejects.toThrow();
    const malformed=registryReader(completed(),async()=>({...parseRegistry(page()),offset:512} as RegistryPage),async()=>new Uint8Array());
    await expect(malformed({name:'result.json',bytes:123,sha256:'a'.repeat(64)},new AbortController().signal)).rejects.toThrow();
  });
});
