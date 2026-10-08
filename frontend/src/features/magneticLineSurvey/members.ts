/** Bounded original-row windows, not downsampled fits or whole-array loading. */
import { object,parseRepresentation,type ArrayRef,type FileIdentity,type SurveyResult,type TableRef,type CrossoverRow } from './contract';

export type MemberReader = (identity: FileIdentity,signal: AbortSignal) => Promise<Uint8Array>;
export interface ArrayWindow {
  first: number; rows: number; columns: number; cells: (number|string)[];
  byte_custody: 'verified_fragments'; whole_array_content: 'not_recomputed';
}
type Entry = FileIdentity & {sequence:number;first_row:number;rows:number};
type Page = {sequence:number;first_row:number;rows:number;file:FileIdentity};
const fail = (): never => { throw new Error('Survey member fragment rejected'); };
function same(a: unknown,b: unknown) { if (JSON.stringify(a) !== JSON.stringify(b)) fail(); }
async function bytes(identity: FileIdentity,read: MemberReader,signal: AbortSignal,maximum = 8388608) {
  if (signal.aborted) throw new DOMException('Aborted','AbortError');
  if (!Number.isSafeInteger(identity.bytes) || identity.bytes < 1 || identity.bytes > maximum || !/^[A-Za-z0-9_.-]{1,64}$/.test(identity.name)) fail();
  const value = await read(identity,signal);
  if (value.byteLength !== identity.bytes) fail();
  // Verify even a trusted owner's transport again before interpreting bytes.
  const digest = new Uint8Array(await crypto.subtle.digest('SHA-256',new Uint8Array(value).buffer));
  if ([...digest].map(v=>v.toString(16).padStart(2,'0')).join('') !== identity.sha256) fail();
  return value;
}
async function json(identity: FileIdentity,read: MemberReader,signal: AbortSignal,maximum: number) {
  return object(JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(await bytes(identity,read,signal,maximum))));
}
export async function resolveChannelMask(result: SurveyResult,data: ArrayRef,read: MemberReader,signal: AbortSignal): Promise<ArrayRef> {
  if (!data.mask_array_id) fail();
  const present=result.geometry.arrays.find(ref=>ref.array_id===data.mask_array_id) ??
    (result.inventory.flags.array_id===data.mask_array_id?result.inventory.flags:undefined);
  if (present) return present;
  // This is the explicitly declared legacy channel-mask target. Its role is
  // channel-bound, never inferred from a directory scan or generic filename.
  const targets=result.artifacts.filter(item=>item.name===`array-${data.mask_array_id}.json` && item.disposition==='included');
  if (targets.length!==1 || targets[0].sha256===null) fail();
  const target=targets[0],identity={name:target.name,bytes:target.bytes,sha256:target.sha256!};
  const manifest=await json(identity,read,signal,2097152);
  const epoch=manifest.schema==='magnetic-line-array-manifest/1'?1:manifest.schema==='magnetic-line-array-manifest/2'?2:fail();
  parseRepresentation('ArrayManifest',manifest,epoch);
  if (manifest.array_id!==data.mask_array_id || manifest.dtype!=='uint32' || manifest.unit!=='identity') fail();
  same(manifest.shape,data.shape);
  const ref:ArrayRef={array_id:data.mask_array_id!,role:'qc_mask',dtype:'uint32',unit:'identity',shape:[...data.shape],
    chunk_rows:4096,manifest:identity,ordered_ids_sha256:data.ordered_ids_sha256,mask_array_id:null};
  parseRepresentation('ArrayRef',ref,epoch);
  return ref;
}
export async function readArrayWindow(ref: ArrayRef,first: number,count: number,read: MemberReader,signal: AbortSignal): Promise<ArrayWindow> {
  parseRepresentation('ArrayRef',ref,2);
  if (!Number.isSafeInteger(first) || !Number.isSafeInteger(count) || first < 0 || count < 1 || count > 4096 || first+count > ref.shape[0]) fail();
  const columns = ref.shape.length === 2 ? ref.shape[1] : 1;
  if (count*columns > 65536) fail();
  const widths = {float64:8,uint64:8,uint32:4,uint8:1,ascii64:64,ascii30:30};
  const width = widths[ref.dtype]*columns;
  const root = await json(ref.manifest,read,signal,2097152);
  const epoch = root.schema === 'magnetic-line-array-manifest/1' ? 1 : root.schema === 'magnetic-line-array-manifest/2' ? 2 : fail();
  parseRepresentation('ArrayManifest',root,epoch);
  for (const key of ['array_id','shape','dtype','unit'] as const) same(root[key],ref[key]);
  if (epoch === 1) parseRepresentation('ArrayRef',ref,1);
  const pages = root.pages as Page[];
  let total = 0;
  for (const [index,page] of pages.entries()) {
    if (page.sequence !== index || page.first_row !== total || page.file.name !== `array-${ref.array_id}-page-${String(index).padStart(6,'0')}.json`) fail();
    total += page.rows;
  }
  if (total !== ref.shape[0]) fail();
  const output: (number|string)[] = [];
  let retained = 0;
  for (const page of pages) {
    if (page.first_row >= first+count || page.first_row+page.rows <= first) continue;
    const body = parseRepresentation('ManifestPage',await json(page.file,read,signal,4194304),1);
    if (body.owner_id !== ref.array_id || body.sequence !== page.sequence) fail();
    const entries = body.entries as Entry[];
    let position = page.first_row;
    for (const [index,entry] of entries.entries()) {
      if (entry.first_row !== position || entry.rows > ref.chunk_rows || index && entry.sequence !== entries[index-1].sequence+1 ||
          entry.name !== `array-${ref.array_id}-${String(entry.sequence).padStart(8,'0')}.bin` || entry.bytes !== entry.rows*width) fail();
      position += entry.rows;
      if (entry.first_row >= first+count || position <= first) continue;
      const data = await bytes(entry,read,signal);
      const view = new DataView(data.buffer,data.byteOffset,data.byteLength);
      const begin = Math.max(first,entry.first_row), end = Math.min(first+count,position);
      for (let row=begin;row<end;row++) {
        for (let column=0;column<columns;column++) {
          const offset = (row-entry.first_row)*width+column*widths[ref.dtype];
          let value: number|string;
          if (ref.dtype === 'float64') value = view.getFloat64(offset,true);
          else if (ref.dtype === 'uint64') {
            const actual = view.getBigUint64(offset,true);
            if (actual > BigInt(Number.MAX_SAFE_INTEGER)) fail();
            value = Number(actual);
          } else if (ref.dtype === 'uint32') value = view.getUint32(offset,true);
          else if (ref.dtype === 'uint8') value = view.getUint8(offset);
          else {
            const token = data.subarray(offset,offset+widths[ref.dtype]);
            let zero = token.indexOf(0);
            if (zero < 0) zero = token.length;
            if (token.some((v,i)=>v>127 || i>=zero && v!==0)) fail();
            value = new TextDecoder('ascii',{fatal:true}).decode(token.subarray(0,zero));
          }
          if (typeof value === 'number' && !Number.isFinite(value)) fail();
          output.push(value);
        }
        retained++;
      }
    }
    if (position !== page.first_row+page.rows) fail();
  }
  if (retained !== count || output.length !== count*columns) fail();
  return {first,rows:count,columns,cells:output,byte_custody:'verified_fragments',whole_array_content:'not_recomputed'};
}

/** Decode retained geometry/measurement crossover rows, never derive offsets. */
export async function readCrossoverWindow(ref:TableRef,first:number,count:number,read:MemberReader,signal:AbortSignal):Promise<CrossoverRow[]> {
  parseRepresentation('TableRef',ref,2);
  if (!['crossover_geometry','crossover_value'].includes(ref.row_schema) || ref.manifest.name!==`table-${ref.table_id}.json` ||
      !Number.isSafeInteger(first) || !Number.isSafeInteger(count) || first<0 || count<1 || count>128 || first+count>ref.rows) fail();
  const root=await json(ref.manifest,read,signal,2097152);
  const epoch=root.schema==='magnetic-line-table-manifest/1'?1:root.schema==='magnetic-line-table-manifest/2'?2:fail();
  parseRepresentation('TableManifest',root,epoch);
  if (root.table_id!==ref.table_id || root.row_schema!==ref.row_schema || root.rows!==ref.rows) fail();
  const pages=root.pages as Page[];
  let total=0;
  for (const [index,page] of pages.entries()) {
    if (page.sequence!==index || page.first_row!==total || page.file.name!==`table-${ref.table_id}-page-${String(index).padStart(6,'0')}.json`) fail();
    total+=page.rows;
  }
  if(total!==ref.rows) fail();
  const result:CrossoverRow[]=[];
  for(const page of pages) {
    if(page.first_row>=first+count || page.first_row+page.rows<=first) continue;
    const body=parseRepresentation('ManifestPage',await json(page.file,read,signal,4194304),1);
    if(body.owner_id!==ref.table_id || body.sequence!==page.sequence) fail();
    const entries=body.entries as Entry[];
    let position=page.first_row;
    for(const [index,entry] of entries.entries()) {
      if(entry.first_row!==position || index && entry.sequence!==entries[index-1].sequence+1 ||
          entry.name!==`table-${ref.table_id}-${String(entry.sequence).padStart(8,'0')}.jsonl`) fail();
      position+=entry.rows;
      if(entry.first_row>=first+count || position<=first) continue;
      const raw=await bytes(entry,read,signal);
      const text=new TextDecoder('utf-8',{fatal:true}).decode(raw);
      if(!text.endsWith('\n')) fail();
      const lines=text.slice(0,-1).split('\n');
      if(lines.length!==entry.rows || lines.some(line=>!line.length || new TextEncoder().encode(line).length>65536)) fail();
      for(let row=Math.max(first,entry.first_row);row<Math.min(first+count,position);row++) {
        const value=parseRepresentation(ref.row_schema==='crossover_geometry'?'CrossoverGeometry':'CrossoverValue',JSON.parse(lines[row-entry.first_row]),epoch);
        result.push(value as unknown as CrossoverRow);
      }
    }
    if(position!==page.first_row+page.rows) fail();
  }
  if(result.length!==count) fail();
  return result;
}
