/** Opaque original input custody. No native value decode or browser inversion. */
import { ApiClient } from "./client";
import { parseSourceRecord, type SourceRecord } from "./contracts";
import { jointJson, jointSha, obj, type Json, type JointFile, type Obj } from "./joint-result";

export type JointRole = "development" | "sealed";
export type JointDescriptor = { dtype: string; shape: number[]; file_bytes: number; file_sha256: string; data_sha256: string };
export type JointInputMember = { role: JointRole; name: string; file: JointFile; descriptor: JointDescriptor | null; sha256: string };
export type JointInput = { members: JointInputMember[]; bytes: number; manifests: Record<JointRole, Obj>; scientific_values_decoded: false };
export type JointSourceAttestation = { provider: string; doi: string | null; citation: string | null; rights_statement: string;
  rights_decision: "mirror" | "provider-link-only" | "derivative-only"; private_storage_permission: "attested"; attribution: string };
export type JointMemberReceipt = { asset_id: string; owner_id: string; project_id: string; source: SourceRecord;
  byte_count: number; sha256: string; physical_metadata: { schema: string; role: JointRole; name: string; descriptor: JointDescriptor | null } };
export type JointDatasetReceipt = { dataset_id: string; project_id: string; raw_asset_id: string; parser_version: "m11-native-members/v1";
  modality: "joint_gravity_magnetic_native"; row_count: number; sha256: string; qc_verdict: "structural_native_members_only";
  scientific_accepted: false; receipt_url: string };
const CAP=268435456, JSON_CAP=262144, roles=["development","sealed"] as const;
const development=["mesh_origin","mesh_hx","mesh_hy","mesh_hz","mesh_active","prior_lengths",
  ...["density","susceptibility"].flatMap(p=>["lower","upper","start","reference"].map(k=>`${p}_${k}`)),
  ...["gravity","magnetic"].flatMap(m=>["receivers","mask","groups","partition"].map(k=>`${m}_${k}`)),
  ...["gravity","magnetic"].flatMap(m=>["rows","observed","noise"].map(k=>`${m}_development_${k}`))];
const sealed=["gravity","magnetic"].flatMap(m=>["rows","observed","noise"].map(k=>`${m}_${k}`));
function check(test: unknown, why: string): asserts test { if (!test) throw new Error(`Joint custody: ${why}`); }
function keys(v: Obj, expected: string[]) { check(Object.keys(v).length===expected.length&&expected.every(k=>Object.hasOwn(v,k)),"closed fields"); }
function sha(v: Json) { check(typeof v==="string"&&/^[a-f0-9]{64}$/.test(v),"digest"); return v; }
function id(v: unknown): string { check(typeof v==="string"&&/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(v),"UUID");return v; }
function equal(a: unknown,b: unknown): boolean {
  const stable=(v: unknown): string=>v&&typeof v==="object" ? Array.isArray(v)?`[${v.map(stable).join()}]`:
    `{${Object.entries(v).sort(([a],[b])=>a.localeCompare(b)).map(([k,x])=>`${JSON.stringify(k)}:${stable(x)}`).join()}}`:JSON.stringify(v);
  return stable(a)===stable(b);
}
function abort(signal?: AbortSignal) { signal?.throwIfAborted(); }
function descriptor(name: string,value: Json): JointDescriptor {
  const d=obj(value);keys(d,["dtype","shape","file_bytes","file_sha256","data_sha256"]);
  const dtype=/_(active|mask)$/.test(name)?"|b1":/_(groups|partition|rows)$/.test(name)?"<i8":"<f8";
  check(d.dtype===dtype&&Array.isArray(d.shape)&&d.shape.length>=1&&d.shape.length<=2&&
    d.shape.every(n=>typeof n==="number"&&Number.isInteger(n)&&n>=1&&n<=4096),"descriptor shape");
  const shape=d.shape as number[];
  check(["mesh_origin","prior_lengths"].includes(name)?equal(shape,[3]):name.endsWith("_receivers")?shape.length===2&&shape[1]===3&&shape[0]<=2048:
    name.endsWith("_noise")?shape[0]<=2048&&(shape.length===1||shape[0]===shape[1]):shape.length===1&&( /^(mesh|density|susceptibility)_/.test(name)||shape[0]<=2048),"role shape");
  const logical=shape.reduce((a,b)=>a*b,1)*(dtype==="|b1"?1:8);
  check(typeof d.file_bytes==="number"&&Number.isInteger(d.file_bytes)&&d.file_bytes>=11+logical&&d.file_bytes<=4106+logical,"native length");
  sha(d.file_sha256);sha(d.data_sha256);return d as unknown as JointDescriptor;
}
function header(bytes: Uint8Array,d: JointDescriptor): number {
  check(bytes.length===d.file_bytes&&bytes.length>=10&&bytes[0]===147&&new TextDecoder().decode(bytes.subarray(1,6))==="NUMPY"&&bytes[6]===1&&bytes[7]===0,"NPY1");
  const length=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength).getUint16(8,true),offset=10+length;
  check(length>=1&&length<=4096&&offset<=bytes.length,"header cap");
  const raw=bytes.subarray(10,offset);check(raw[raw.length-1]===10,"header newline");
  const literal=Array.from(raw,b=>String.fromCharCode(b)).join("").trim();
  // Closed three-field Python literal, accepting either quote and field order.
  // No eval, Python expressions, boolean dimensions or native-value decoding.
  check(literal.startsWith("{")&&literal.endsWith("}"),"literal dictionary");
  let cursor=1;const found=new Map<string,string|number[]>();
  const token=(pattern: RegExp)=>{pattern.lastIndex=cursor;const m=pattern.exec(literal);check(m,"literal header");cursor=pattern.lastIndex;return m;};
  for(let field=0;field<3;field++) {
    const name=token(/\s*(['"])(descr|fortran_order|shape)\1\s*:\s*/y)[2];check(!found.has(name),"duplicate header field");
    if(name==="descr")found.set(name,token(/(['"])(<f8|<i8|\|b1)\1/y)[2]);
    else if(name==="fortran_order"){token(/False/y);found.set(name,"False");}
    else { const tuple=token(/\(\s*([1-9][0-9]*\s*,\s*(?:[1-9][0-9]*\s*,?\s*)?)\)/y)[1];found.set(name,tuple.split(",").map(v=>v.trim()).filter(Boolean).map(Number)); }
    const separator=token(/\s*(,|(?=\}))/y)[1];check(field===2||separator===",","header field separator");
  }
  check(/^\s*\}$/.test(literal.slice(cursor))&&found.get("descr")===d.dtype&&found.get("fortran_order")==="False","literal header binding");
  const shape=found.get("shape");check(Array.isArray(shape),"literal shape");
  check(equal(shape,d.shape)&&offset+shape.reduce((a,b)=>a*b,1)*(d.dtype==="|b1"?1:8)===bytes.length,"header binding");return offset;
}

export async function inspectJointInputs(files: JointFile[],signal?: AbortSignal): Promise<JointInput> {
  abort(signal);check(files.length>=2&&files.length<=40,"member count");
  let total=0;const paths=new Map<string,JointFile>();
  for (const f of files) {
    check(/^(development|sealed)\/[a-z_]+(?:\.corrections)?\.(json|npy|raw)$/.test(f.path)&&!paths.has(f.path),"ordinary unique role/name");
    check(Number.isSafeInteger(f.size)&&f.size>0,"member size");total+=f.size;check(total<=CAP,"whole byte cap");
    if(f.path.endsWith(".json"))check(f.size<=JSON_CAP,"JSON cap");paths.set(f.path,f);
  }
  const manifests={} as Record<JointRole,Obj>,expected=new Map<string,{sha: string; descriptor: JointDescriptor|null; bytes: number|null}>();
  for (const role of roles) {
    const main=role==="development"?"request.json":"sealed.json",file=paths.get(`${role}/${main}`);check(file,"manifest required");
    const bytes=await file.read();abort(signal);check(bytes.length===file.size,"manifest length");const value=jointJson(bytes);manifests[role]=value;
    keys(value,role==="development"?["schema","survey","development","arrays","sealed_manifest","raw_access"]:["schema","payload","arrays"]);
    check(value.schema===(role==="development"?"joint-survey-intake-1":"joint-survey-sealed-input-1"),"manifest schema");
    if(role==="sealed") { const payload=obj(value.payload);keys(payload,["plan_sha256"]);sha(payload.plan_sha256); }
    const arrays=obj(value.arrays);keys(arrays,role==="development"?development:sealed);
    expected.set(`${role}/${main}`,{sha:await jointSha(bytes),descriptor:null,bytes:bytes.length});
    for (const [name,value] of Object.entries(arrays)) { const d=descriptor(name,value);expected.set(`${role}/${name}.npy`,{sha:d.file_sha256,descriptor:d,bytes:d.file_bytes}); }
    if(role==="development") {
      const access=obj(value.raw_access);keys(access,["gravity","magnetic"]);
      for(const m of ["gravity","magnetic"]) {
        const r=obj(access[m]);keys(r,["availability","raw_present","correction_present"]);
        if(equal(r,{availability:"provider_reference_only",raw_present:false,correction_present:false}))continue;
        check(equal(r,{availability:"provided",raw_present:true,correction_present:true}),"original presence");
        const source=obj(obj(obj(value.survey)[m]).source);
        check(typeof source.raw_bytes==="number"&&Number.isSafeInteger(source.raw_bytes)&&source.raw_bytes>0&&source.raw_bytes<=CAP,"raw length");
        expected.set(`${role}/${m}.raw`,{sha:sha(source.raw_sha256),bytes:source.raw_bytes,descriptor:null});
        expected.set(`${role}/${m}.corrections.json`,{sha:sha(source.correction_sha256),bytes:null,descriptor:null});
      }
    }
  }
  check(paths.size===expected.size&&[...paths.keys()].every(p=>expected.has(p)),"exact inventory");
  for(const [path,d] of expected)check(d.bytes===null||paths.get(path)!.size===d.bytes,"declared length");
  check(obj(manifests.sealed.payload).plan_sha256===obj(manifests.development.development).plan_sha256,"plan binding");
  const seal=obj(manifests.development.sealed_manifest);keys(seal,["schema","gravity","magnetic"]);check(seal.schema==="joint-survey-sealed-manifest-1","sealed manifest schema");
  for(const m of ["gravity","magnetic"]) {
    const declaration=obj(seal[m]);keys(declaration,["count","noise_kind","observations_file_sha256","noise_file_sha256","rows_sha256"]);
    const arrays=obj(manifests.sealed.arrays),rows=descriptor(`${m}_rows`,arrays[`${m}_rows`]),observed=descriptor(`${m}_observed`,arrays[`${m}_observed`]),noise=descriptor(`${m}_noise`,arrays[`${m}_noise`]);
    check(typeof declaration.count==="number"&&Number.isInteger(declaration.count)&&equal(rows.shape,[declaration.count])&&equal(observed.shape,rows.shape)&&
      declaration.rows_sha256===rows.data_sha256&&declaration.observations_file_sha256===observed.file_sha256&&declaration.noise_file_sha256===noise.file_sha256&&
      (declaration.noise_kind==="diagonal_sd"&&equal(noise.shape,rows.shape)||declaration.noise_kind==="full_covariance"&&equal(noise.shape,[declaration.count,declaration.count])),"sealed source binding");
  }
  // All descriptors/counts/lengths above pass before opaque NPY/raw reads.
  const members: JointInputMember[]=[];
  for(const [path,d] of expected) {
    abort(signal);const file=paths.get(path)!,bytes=await file.read();abort(signal);check(bytes.length===file.size,"original length");
    let offset=0;if(d.descriptor)offset=header(bytes,d.descriptor);
    check(await jointSha(bytes)===d.sha,"original digest");
    if(d.descriptor)check(await jointSha(bytes.subarray(offset))===d.descriptor.data_sha256,"native data digest");
    else if(path.endsWith(".json"))jointJson(bytes);
    const [role,name]=path.split("/");members.push({role:role as JointRole,name,file,descriptor:d.descriptor,sha256:d.sha});
  }
  return {members,bytes:total,manifests,scientific_values_decoded:false};
}

export function browserJointInputs(role: JointRole,files: FileList): JointFile[] {
  return Array.from(files,file=> { const path=file.webkitRelativePath;
    check(!path||path.split("/").length===2,"flat original directory");
    return {path:`${role}/${file.name}`,size:file.size,read:async()=>new Uint8Array(await file.arrayBuffer())}; });
}
export function parseJointMemberReceipt(value: unknown): JointMemberReceipt {
  const v=obj(value as Json);keys(v,["schema_version","asset_id","owner_id","project_id","source_id","source","original_filename","mime_type","detected_format","byte_count","sha256","physical_metadata","created_at","receipt","download_url","validation_status"]);
  const source=parseSourceRecord(v.source);for(const k of ["asset_id","owner_id","project_id","source_id"])id(v[k]);sha(v.sha256);
  check(typeof v.created_at==="string"&&/^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/.test(v.created_at)&&!Number.isNaN(Date.parse(v.created_at)),"receipt timestamp");
  check(v.schema_version==="geophysics.raw-asset-view/v1"&&v.detected_format==="joint_native"&&v.mime_type==="application/octet-stream"&&v.validation_status==="raw_metadata_checked","native receipt");
  const m=obj(v.physical_metadata);keys(m,["schema","role","name","descriptor","scientific_values_decoded","scientific_accepted"]);
  check(m.schema==="joint-native-member-1"&&roles.includes(m.role as JointRole)&&m.name===v.original_filename&&m.scientific_values_decoded===false&&m.scientific_accepted===false,"native member binding");
  check(typeof v.byte_count==="number"&&Number.isSafeInteger(v.byte_count)&&v.byte_count>0&&v.byte_count<=CAP,"receipt length");
  check(source.source_id===v.source_id&&source.sha256===v.sha256&&source.expected_bytes===v.byte_count&&source.declared_format==="joint_native"&&source.location.filename===m.name&&source.private_storage_permission==="attested"&&source.rights_decision!=="forbidden","source binding");
  const path=`/api/projects/${v.project_id}/assets/${v.asset_id}`;check(v.receipt===path&&v.download_url===`${path}/download`,"owner receipt URL");
  if(m.descriptor!==null){check(typeof m.name==="string"&&m.name.endsWith(".npy"),"descriptor name");const d=descriptor(m.name.slice(0,-4),m.descriptor);check(d.file_sha256===v.sha256&&d.file_bytes===v.byte_count,"descriptor receipt");}
  return v as unknown as JointMemberReceipt;
}
export function parseJointDatasetReceipt(value: unknown): JointDatasetReceipt {
  const v=obj(value as Json);keys(v,["dataset_id","project_id","raw_asset_id","parser_version","modality","row_count","sha256","qc_verdict","scientific_accepted","receipt_url"]);
  for(const k of ["dataset_id","project_id","raw_asset_id"])id(v[k]);sha(v.sha256);
  check(v.parser_version==="m11-native-members/v1"&&v.modality==="joint_gravity_magnetic_native"&&v.qc_verdict==="structural_native_members_only"&&v.scientific_accepted===false,"structural-only dataset");
  check(typeof v.row_count==="number"&&Number.isInteger(v.row_count)&&v.row_count>=2&&v.row_count<=4096,"source rows");
  check(v.receipt_url===`/api/projects/${v.project_id}/joint-datasets/${v.dataset_id}`,"dataset URL");return v as unknown as JointDatasetReceipt;
}

export class JointInputApi {
  constructor(private readonly api: ApiClient) {}
  async upload(project: string,member: JointInputMember,attestation: JointSourceAttestation,signal?: AbortSignal) {
    id(project);abort(signal);
    check(attestation.private_storage_permission==="attested"&&["mirror","provider-link-only","derivative-only"].includes(attestation.rights_decision),"private rights attestation");
    for(const key of ["provider","rights_statement","attribution"] as const)check(attestation[key].trim().length>0,"source text");
    const bytes=await member.file.read();abort(signal);check(bytes.length===member.file.size&&await jointSha(bytes)===member.sha256,"original changed before upload");
    const meta={role:member.role,name:member.name,descriptor:member.descriptor,source:{...attestation,expected_bytes:bytes.length,expected_sha256:member.sha256}};
    const token=await this.api.requestJson("/api/auth/csrf",v=>obj(v as Json),{signal});check(typeof token.csrf_token==="string"&&token.csrf_token,"CSRF token");
    const receipt=await this.api.requestNativeMember(`/api/projects/${project}/joint-members`,new Blob([bytes.slice().buffer]),JSON.stringify(meta),parseJointMemberReceipt,token.csrf_token,signal);
    check(receipt.project_id===project&&receipt.sha256===member.sha256&&receipt.byte_count===bytes.length&&
      equal(receipt.physical_metadata,{schema:"joint-native-member-1",role:member.role,name:member.name,descriptor:member.descriptor,scientific_values_decoded:false,scientific_accepted:false}),"returned original binding");
    return receipt;
  }
  async index(project: string,input: JointInput,receipts: Map<string,JointMemberReceipt>,signal?: AbortSignal) {
    id(project);abort(signal);const map: Record<JointRole,Record<string,string>>={development:{},sealed:{}};
    check(receipts.size===input.members.length,"complete receipt inventory");
    const owners=new Set<string>(),ids=new Set<string>();
    for(const m of input.members) { const r=receipts.get(`${m.role}/${m.name}`);check(r&&r.project_id===project&&r.sha256===m.sha256&&r.byte_count===m.file.size&&r.physical_metadata.role===m.role&&r.physical_metadata.name===m.name&&equal(r.physical_metadata.descriptor,m.descriptor),"index source binding");
      owners.add(r.owner_id);check(!ids.has(r.asset_id),"unique original asset");ids.add(r.asset_id);map[m.role][m.name]=r.asset_id; }
    check(owners.size===1,"single original owner");
    const token=await this.api.requestJson("/api/auth/csrf",v=>obj(v as Json),{signal});check(typeof token.csrf_token==="string"&&token.csrf_token,"CSRF token");
    const result=await this.api.requestJson(`/api/projects/${project}/joint-datasets`,parseJointDatasetReceipt,
      {method:"POST",csrfToken:token.csrf_token,body:map,signal});
    check(result.project_id===project&&result.raw_asset_id===map.development["request.json"],"indexed primary binding");return result;
  }
}
