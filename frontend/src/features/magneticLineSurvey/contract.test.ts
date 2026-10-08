import { describe,it,expect } from 'vitest';
import { parseStart,parseJob,parseRepresentation,type ArrayRef,type FileIdentity } from './contract';
import { readArrayWindow,readCrossoverWindow } from './members';

const id=(index:number)=>`00000000-0000-0000-0000-${String(index).padStart(12,'0')}`;
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
