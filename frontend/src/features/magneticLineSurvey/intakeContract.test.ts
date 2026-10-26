import {describe,it,expect} from 'vitest';
import {assetMime,parseAssetHeader,parseAssetReceipt,parseDatasetRequest,parseDatasetReceipt,
  datasetRequestFromReceipts,startFromPublishedDataset,type AssetRole} from './intakeContract';
const id=(n:number)=>`00000000-0000-0000-0000-${String(n).padStart(12,'0')}`;
const header=()=>({schema:'m03-owner-asset/1',role:'original_csv',filename:'original.csv',mime:'text/csv',source:{
  provider:'Actual declared user source',doi:null,citation:null,rights_statement:'Actual source permits private original storage.',
  rights_decision:'mirror',private_storage_permission:true,attribution:'Actual declared owner',expected_bytes:100,expected_sha256:'a'.repeat(64)}});
const receipt=(n:number,role:AssetRole)=>({schema:'m03-owner-asset-receipt/1',asset_id:id(n),source_id:id(n+10),role,
  bytes:100,sha256:'a'.repeat(64),provider_verification:'not_verified',field_eligibility:'not_established'});
const dataset=()=>({schema:'m03-owner-dataset-receipt/1',dataset_id:id(20),sha256:'b'.repeat(64),bytes:800,rows:8201,
  parser_version:'m03-original-geometry/1',provider_verification:'not_verified',field_eligibility:'not_established'});

describe('closed original intake representation, not provider or field evidence',()=>{
  it('preserves explicit rights, source, bytes, SHA and MIME without a grant',()=>{
    expect(parseAssetHeader(header())).toEqual(header());
    expect(assetMime('typed_auxiliary_bundle')).toBe('application/octet-stream');
    expect(parseAssetReceipt(receipt(1,'original_csv')).provider_verification).toBe('not_verified');
  });
  it('refuses paths, hidden fields, inferred permission, wrong MIME and coercions',()=>{
    for(const changed of [{...header(),filename:'../raw'},{...header(),mime:'application/json'},
      {...header(),url:'hidden'},{...header(),source:{...header().source,private_storage_permission:'true'}},
      {...header(),source:{...header().source,expected_bytes:true}},
      {...header(),source:{...header().source,expected_sha256:'A'.repeat(64)}}])expect(()=>parseAssetHeader(changed)).toThrow();
  });
  it('cannot upgrade a receipt to verified provider, field, activation or a guessed UUID',()=>{
    for(const changed of [{...receipt(1,'original_csv'),provider_verification:'verified'},
      {...receipt(1,'original_csv'),field_eligibility:'pass'},{...receipt(1,'original_csv'),asset_id:'filename.csv'},
      {...receipt(1,'original_csv'),host_admission:'pass'}])expect(()=>parseAssetReceipt(changed)).toThrow();
  });
  it('builds only the real paired9-key dataset and published11-key start identities',()=>{
    const references=[parseAssetReceipt(receipt(1,'original_csv')),parseAssetReceipt(receipt(2,'metadata_json')),
      parseAssetReceipt(receipt(3,'request_json')),parseAssetReceipt(receipt(4,'typed_auxiliary_bundle'))];
    const request=datasetRequestFromReceipts(references);
    expect(Object.keys(request)).toHaveLength(9);expect(request.auxiliary_asset_ids).toEqual([id(4)]);
    const start=startFromPublishedDataset(request,parseDatasetReceipt(dataset()));
    expect(Object.keys(start)).toHaveLength(11);expect(start.dataset_id).toBe(id(20));
    expect(start.dataset_sha256).toBe('b'.repeat(64));expect(start.original_asset_id).toBe(id(1));
    // Literal row8201 here is DTO grammar only, NEVER an acquired field result.
  });
  it('refuses missing/duplicate roles or bundles and duplicate UUID/hash pairs',()=>{
    const references=[parseAssetReceipt(receipt(1,'original_csv')),parseAssetReceipt(receipt(2,'metadata_json')),
      parseAssetReceipt(receipt(3,'request_json')),parseAssetReceipt(receipt(4,'typed_auxiliary_bundle'))];
    for(const wrong of [references.slice(1),references.slice(0,3),[...references,references[0]]])
      expect(()=>datasetRequestFromReceipts(wrong)).toThrow();
    const request=datasetRequestFromReceipts(references);
    for(const wrong of [{...request,auxiliary_sha256:[]},{...request,request_asset_id:id(1)},
      {...request,solver_epoch:'qr'},{...request,path:'hidden'}])expect(()=>parseDatasetRequest(wrong)).toThrow();
  });
  it('rejects partial/false publication, coercion and invented parser identity',()=>{
    for(const wrong of [{...dataset(),dataset_id:null},{...dataset(),rows:'8201'},{...dataset(),rows:0},
      {...dataset(),field_eligibility:'pass'},{...dataset(),parser_version:'gravity'},
      {...dataset(),scientific_verdict:'pass'}])expect(()=>parseDatasetReceipt(wrong)).toThrow();
  });
});
