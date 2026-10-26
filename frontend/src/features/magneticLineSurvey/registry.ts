/** Actual durable registry -> UUID bytes. A page cache is not a survey array. */
import { object,uuid,hash,type FileIdentity,type SurveyJob } from './contract';
import type { MemberReader } from './members';

export interface RegistryEntry extends FileIdentity {
  member_id:string;kind:'result'|'manifest'|'chunk'|'page'|'receipt';
}
export interface RegistryPage {
  schema:'m03-owner-members/1';job_id:string;result_sha256:string;
  offset:number;total:number;next_offset:number|null;entries:RegistryEntry[];
}
const fail=():never=>{throw new Error('Survey durable registry rejected');};
function exact(value:unknown,keys:string[]) {
  const item=object(value);
  if(Object.keys(item).sort().join('|')!==[...keys].sort().join('|')) fail();
  return item;
}
function integer(value:unknown,low:number,high:number):number {
  if(typeof value!=='number'||!Number.isSafeInteger(value)||value<low||value>high) fail();
  return value as number;
}
export function parseRegistry(value:unknown):RegistryPage {
  const page=exact(value,['schema','job_id','result_sha256','offset','total','next_offset','entries']);
  if(page.schema!=='m03-owner-members/1'||!Array.isArray(page.entries)) fail();
  const rawEntries=page.entries as unknown[];
  const total=integer(page.total,1,1000000),offset=integer(page.offset,0,total-1);
  if(offset%512!==0 || rawEntries.length!==Math.min(512,total-offset)) fail();
  const next=offset+rawEntries.length;
  if(page.next_offset!==(next<total?next:null)) fail();
  const ids=new Set<string>();let previous='';
  const entries=rawEntries.map(value=>{
    const row=exact(value,['member_id','name','bytes','sha256','kind']);
    const id=uuid(row.member_id);
    if(ids.has(id)||typeof row.name!=='string'||!/^result\/[A-Za-z0-9_.-]{1,64}$/.test(row.name)||
       row.name<=previous||!['result','manifest','chunk','page','receipt'].includes(String(row.kind))) fail();
    ids.add(id);previous=row.name as string;
    return {member_id:id,name:row.name as string,bytes:integer(row.bytes,1,8388608),sha256:hash(row.sha256),kind:row.kind as RegistryEntry['kind']};
  });
  return {schema:'m03-owner-members/1',job_id:uuid(page.job_id),result_sha256:hash(page.result_sha256),
    offset,total,next_offset:page.next_offset as number|null,entries};
}
export function registryReader(job:SurveyJob,
  pageAt:(offset:number,signal:AbortSignal)=>Promise<RegistryPage>,
  member:(entry:RegistryEntry,signal:AbortSignal)=>Promise<Uint8Array>):MemberReader {
  if(job.state!=='succeeded'||!job.result_sha256) fail();
  let cached:RegistryPage|null=null;
  const find=(page:RegistryPage,identity:FileIdentity)=>{
    const row=page.entries.find(row=>row.name===`result/${identity.name}`);
    if(row && (row.bytes!==identity.bytes||row.sha256!==identity.sha256)) fail();
    return row;
  };
  return async(identity,signal)=>{
    if(signal.aborted) throw new DOMException('Aborted','AbortError');
    if(!/^[A-Za-z0-9_.-]{1,64}$/.test(identity.name)) fail();
    integer(identity.bytes,1,8388608);hash(identity.sha256);
    const hit=cached && find(cached,identity);
    if(hit) return member(hit,signal);
    let offset=0,total:number|null=null,previous='';
    for(;;) {
      if(signal.aborted) throw new DOMException('Aborted','AbortError');
      const page=parseRegistry(await pageAt(offset,signal));
      if(page.job_id!==job.job_id||page.result_sha256!==job.result_sha256||page.offset!==offset||
         total!==null&&page.total!==total||page.entries[0].name<=previous) fail();
      total=page.total;previous=page.entries[page.entries.length-1].name;cached=page;
      const entry=find(page,identity);
      if(entry) return member(entry,signal);
      if(page.next_offset===null||previous>`result/${identity.name}`) fail();
      offset=page.next_offset as number;
    }
  };
}
