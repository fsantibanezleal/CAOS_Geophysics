/** Exact rights-bearing intake and dataset DTOs, without provider certification. */
import {hash,object,uuid,parseStart,type SurveyStart} from './contract';

export const assetRoles=['original_csv','metadata_json','request_json','typed_auxiliary_bundle','navigation_original',
  'base_original','calibration_original','reference_original','offset_original'] as const;
export type AssetRole=typeof assetRoles[number];
export type RightsDecision='mirror'|'provider-link-only'|'derivative-only'|'forbidden';
export interface AssetHeader {
  schema:'m03-owner-asset/1';role:AssetRole;filename:string;mime:string;
  source:{provider:string;doi:string|null;citation:string|null;rights_statement:string;rights_decision:RightsDecision;
    private_storage_permission:true;attribution:string;expected_bytes:number;expected_sha256:string};
}
export interface AssetReceipt {schema:'m03-owner-asset-receipt/1';asset_id:string;source_id:string;role:AssetRole;
  bytes:number;sha256:string;provider_verification:'not_verified';field_eligibility:'not_established'}
export interface DatasetRequest {schema:'m03-owner-dataset-request/1';original_asset_id:string;original_sha256:string;
  metadata_asset_id:string;metadata_sha256:string;request_asset_id:string;request_sha256:string;
  auxiliary_asset_ids:string[];auxiliary_sha256:string[]}
export interface DatasetReceipt {schema:'m03-owner-dataset-receipt/1';dataset_id:string;sha256:string;bytes:number;rows:number;
  parser_version:'m03-original-geometry/1';provider_verification:'not_verified';field_eligibility:'not_established'}
const fail=():never=>{throw new Error('Survey intake or dataset receipt rejected');};
const fields=(value:unknown,names:string)=>{
  const item=object(value);if(Object.keys(item).sort().join('|')!==names.split(' ').sort().join('|'))fail();return item;
};
const text=(value:unknown,min:number,max:number)=>{
  if(typeof value!=='string'||value.length<min||value.length>max||value.includes('\0'))fail();return value as string;
};
const count=(value:unknown,maximum:number)=>{if(typeof value!=='number'||!Number.isSafeInteger(value)||value<1||value>maximum)fail();};
const role=(value:unknown):AssetRole=>{if(!assetRoles.includes(value as AssetRole))fail();return value as AssetRole;};
export const assetMime=(value:AssetRole)=>value.endsWith('_json')?'application/json':value==='typed_auxiliary_bundle'?'application/octet-stream':'text/csv';
export const assetByteLimit=(value:AssetRole)=>value==='metadata_json'||value==='request_json'?2097152:4294967296;
export function parseAssetHeader(value:unknown):AssetHeader {
  const v=fields(value,'schema role filename mime source'),kind=role(v.role);
  if(v.schema!=='m03-owner-asset/1'||v.mime!==assetMime(kind))fail();
  const name=text(v.filename,1,255);if(['.','..'].includes(name)||/[\\/:\x00-\x1f]/.test(name))fail();
  const s=fields(v.source,'provider doi citation rights_statement rights_decision private_storage_permission attribution expected_bytes expected_sha256');
  for(const [key,min,max] of [['provider',1,200],['rights_statement',10,4000],['attribution',1,2000]] as const)
    if(!text(s[key],min,max).trim())fail();
  if(s.doi!==null)text(s.doi,0,200);if(s.citation!==null)text(s.citation,0,2000);
  if(!['mirror','provider-link-only','derivative-only','forbidden'].includes(String(s.rights_decision))||s.private_storage_permission!==true)fail();
  count(s.expected_bytes,assetByteLimit(kind));hash(s.expected_sha256);
  if(new TextEncoder().encode(JSON.stringify(v)).length>16384)fail();
  return structuredClone(v) as unknown as AssetHeader;
}
export function parseAssetReceipt(value:unknown):AssetReceipt {
  const v=fields(value,'schema asset_id source_id role bytes sha256 provider_verification field_eligibility');
  if(v.schema!=='m03-owner-asset-receipt/1'||v.provider_verification!=='not_verified'||v.field_eligibility!=='not_established')fail();
  uuid(v.asset_id);uuid(v.source_id);count(v.bytes,assetByteLimit(role(v.role)));hash(v.sha256);
  return structuredClone(v) as unknown as AssetReceipt;
}
export function parseDatasetRequest(value:unknown):DatasetRequest {
  const v=fields(value,'schema original_asset_id original_sha256 metadata_asset_id metadata_sha256 request_asset_id request_sha256 auxiliary_asset_ids auxiliary_sha256');
  if(v.schema!=='m03-owner-dataset-request/1'||!Array.isArray(v.auxiliary_asset_ids)||!Array.isArray(v.auxiliary_sha256)||
    v.auxiliary_asset_ids.length>16||v.auxiliary_asset_ids.length!==v.auxiliary_sha256.length)fail();
  const ids=['original_asset_id','metadata_asset_id','request_asset_id'].map(key=>uuid(v[key]));
  ids.push(...(v.auxiliary_asset_ids as unknown[]).map(uuid));if(new Set(ids).size!==ids.length)fail();
  ['original_sha256','metadata_sha256','request_sha256'].forEach(key=>hash(v[key]));(v.auxiliary_sha256 as unknown[]).forEach(hash);
  return structuredClone(v) as unknown as DatasetRequest;
}
export function parseDatasetReceipt(value:unknown):DatasetReceipt {
  const v=fields(value,'schema dataset_id sha256 bytes rows parser_version provider_verification field_eligibility');
  if(v.schema!=='m03-owner-dataset-receipt/1'||v.parser_version!=='m03-original-geometry/1'||
    v.provider_verification!=='not_verified'||v.field_eligibility!=='not_established')fail();
  uuid(v.dataset_id);hash(v.sha256);count(v.bytes,2097152);count(v.rows,8000000);
  return structuredClone(v) as unknown as DatasetReceipt;
}
export function datasetRequestFromReceipts(receipts:AssetReceipt[]):DatasetRequest {
  const all=receipts.map(parseAssetReceipt);
  const one=(kind:AssetRole)=>{const found=all.filter(v=>v.role===kind);if(found.length!==1)fail();return found[0];};
  const original=one('original_csv'),metadata=one('metadata_json'),request=one('request_json');
  const auxiliary=all.filter(v=>!['original_csv','metadata_json','request_json'].includes(v.role));
  if(!auxiliary.some(v=>v.role==='typed_auxiliary_bundle'))fail();
  return parseDatasetRequest({schema:'m03-owner-dataset-request/1',original_asset_id:original.asset_id,original_sha256:original.sha256,
    metadata_asset_id:metadata.asset_id,metadata_sha256:metadata.sha256,request_asset_id:request.asset_id,request_sha256:request.sha256,
    auxiliary_asset_ids:auxiliary.map(v=>v.asset_id),auxiliary_sha256:auxiliary.map(v=>v.sha256)});
}
export function startFromPublishedDataset(request:DatasetRequest,receipt:DatasetReceipt):SurveyStart {
  const r=parseDatasetRequest(request),d=parseDatasetReceipt(receipt);
  return parseStart({...r,schema:'m03-owner-start/1',dataset_id:d.dataset_id,dataset_sha256:d.sha256});
}
