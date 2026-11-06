import {cpSync,existsSync,mkdirSync,lstatSync,readFileSync,readdirSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {dirname,join,resolve,relative,isAbsolute} from 'node:path';
import {fileURLToPath} from 'node:url';
const here=dirname(fileURLToPath(import.meta.url));
const sourceArg=process.argv.indexOf('--source');
const configuredDataRoot=process.env.GEOPHYSICS_LOCAL_DATA_ROOT;
if(configuredDataRoot&&!isAbsolute(configuredDataRoot))throw new Error('GEOPHYSICS_LOCAL_DATA_ROOT must be an absolute device data root.');
const externalDataRoot=configuredDataRoot?resolve(configuredDataRoot):null;
const repositoryDataRoot=resolve(here,'../data');
const derivedSource=(relativePath)=>{
  const external=externalDataRoot&&join(externalDataRoot,'data/derived',relativePath);
  return external&&existsSync(external)?external:join(repositoryDataRoot,'derived',relativePath);
};
const source=sourceArg<0?derivedSource('v2'):resolve(here,process.argv[sourceArg+1]??'');
const phaseSource=derivedSource('phase/browser-assets/stead');
const courseSource=derivedSource('m01-scientific-course');
const fieldSource=derivedSource('field');
const m12Source=resolve(here,'../models/experimental/m12-physics-cuda-20261004');
const m12ModelPath=join(m12Source,'m12-physics.onnx');
const m12ReceiptPath=join(m12Source,'m12-physics-browser-receipt.json');
const m12TrainingReceiptPath=join(m12Source,'receipt.json');
const m12CheckpointPath=join(m12Source,'m12-physics.npz');
const m12ModelSha256='92e5a3cc5bc70d81c122a1d64c2b4bd722eed47cfa55e2f2473f755cf499f261';
const m12CheckpointSha256='23d51c42b079f37c85fe77796556962e9b7f4f2fe179650a329641a6faa9ded1';
for(const path of [m12Source,m12ModelPath,m12ReceiptPath,m12TrainingReceiptPath,m12CheckpointPath]){
  const stat=lstatSync(path);
  const directory=path===m12Source;
  if(stat.isSymbolicLink()||(directory?!stat.isDirectory():!stat.isFile()))
    throw new Error('M12 model source is not a regular reviewed file.');
}
const m12Receipt=JSON.parse(readFileSync(m12ReceiptPath,'utf8'));
const m12TrainingReceipt=JSON.parse(readFileSync(m12TrainingReceiptPath,'utf8'));
const m12ModelBytes=readFileSync(m12ModelPath);
if(m12Receipt.schema!=='geophysics.m12-browser-model/v1'||m12Receipt.status!=='parity-verified'||
  m12Receipt.model?.file!=='m12-physics.onnx'||m12Receipt.model?.bytes!==m12ModelBytes.byteLength||
  m12Receipt.model?.sha256!==m12ModelSha256||createHash('sha256').update(m12ModelBytes).digest('hex')!==m12ModelSha256||
  m12Receipt.checkpoint?.sha256!==m12CheckpointSha256||m12Receipt.training?.scientific_verdict!=='failed-held-out-comparator'||
  m12TrainingReceipt.schema!=='geophysics.m12-physics/v2'||m12TrainingReceipt.checkpoint_sha256!==m12CheckpointSha256||
  m12Receipt.training?.receipt_sha256!==createHash('sha256').update(readFileSync(m12TrainingReceiptPath)).digest('hex')||
  createHash('sha256').update(readFileSync(m12CheckpointPath)).digest('hex')!==m12CheckpointSha256||
  m12Receipt.training?.source_sha256!==m12TrainingReceipt.code_sha256||
  m12Receipt.training?.operator_source_sha256!==m12TrainingReceipt.operator_code_sha256||
  m12Receipt.parity?.passed!==true||m12Receipt.parity?.records!==640||m12Receipt.parity?.max_absolute_error_m_s>0.002)
  throw new Error('M12 browser model or parity receipt does not match the pinned experiment.');
const courseIndex=JSON.parse(readFileSync(join(here,'src/data/m01-course-record-index.json'),'utf8'));
const fieldIndex=JSON.parse(readFileSync(join(here,'src/data/field-study-index.json'),'utf8'));
if(!Array.isArray(courseIndex)||courseIndex.length!==3)throw new Error('Invalid authored M01 course index.');
// Copy only each explicitly bound public artifact, never a raw/private directory.
// Validate the complete set before changing the build overlay.
const courseFiles=courseIndex.flatMap((record,i)=>{
  if(record.scenario_id!==`prism-case-${i}`||record.label_kind!=='synthetic_control_replay'||!Array.isArray(record.artifacts)||record.artifacts.length!==11)
    throw new Error('Invalid authored M01 scenario.');
  return record.artifacts.map(artifact=>{
    if(typeof artifact.path!=='string'||!/^prism-case-[012]\/[a-z-]+\.(json|svg|png)$/.test(artifact.path)||
      !Number.isSafeInteger(artifact.bytes)||artifact.bytes<1||artifact.bytes>32*1024*1024||!/^[0-9a-f]{64}$/.test(artifact.sha256))
      throw new Error('Invalid authored M01 artifact binding.');
    const file=join(courseSource,artifact.path),stat=lstatSync(file);
    if(!stat.isFile()||stat.isSymbolicLink()||stat.size!==artifact.bytes||createHash('sha256').update(readFileSync(file)).digest('hex')!==artifact.sha256)
      throw new Error('Authored M01 artifact byte identity mismatch.');
    return artifact.path;
  });
});
if(new Set(courseFiles).size!==33)throw new Error('Duplicate authored M01 artifact.');
if(fieldIndex.schema!=='geophysics.field-study-index/v1'||!Array.isArray(fieldIndex.artifacts)||fieldIndex.artifacts.length!==1)
  throw new Error('Invalid field-study artifact index.');
const fieldFiles=fieldIndex.artifacts.map(artifact=>{
  if(typeof artifact.path!=='string'||!/^long-valley\/1982-06_to_1999-07\.json$/.test(artifact.path)||
    !Number.isSafeInteger(artifact.bytes)||artifact.bytes<1||artifact.bytes>2*1024*1024||!/^[0-9a-f]{64}$/.test(artifact.sha256))
    throw new Error('Invalid field-study artifact binding.');
  const file=join(fieldSource,artifact.path),stat=lstatSync(file);
  if(!stat.isFile()||stat.isSymbolicLink()||stat.size!==artifact.bytes||createHash('sha256').update(readFileSync(file)).digest('hex')!==artifact.sha256)
    throw new Error('Field-study artifact byte identity mismatch.');
  return artifact.path;
});
if(new Set(fieldFiles).size!==1)throw new Error('Duplicate field-study artifact.');
if(sourceArg>=0){
  const within=relative(resolve(here,'../data/experiments'),source);
  if(within.startsWith('..')||isAbsolute(within))throw new Error('Preview source must be an ignored data/experiments candidate.');
}
if(!existsSync(join(source,'catalog.json')))throw new Error('Missing committed v2 catalogue; run scripts/precompute first.');
if(!existsSync(join(phaseSource,'manifest.json')))throw new Error('Missing reviewed M13 browser assets; run scripts/export_stead_browser_assets.py after the held-out benchmark.');
mkdirSync(join(here,'public-release/data/v2'),{recursive:true});
cpSync(source,join(here,'public-release/data/v2'),{recursive:true});
// FWI traces are served as bounded, serial gzip sidecars to keep the browser's
// peak memory controlled. Generate these only in the ignored build overlay.
function gzipFwiArtifacts(directory){
  for(const entry of readdirSync(directory,{withFileTypes:true})){
    const path=join(directory,entry.name);
    if(entry.isDirectory())gzipFwiArtifacts(path);
    else if(entry.isFile()&&entry.name.endsWith('.json'))
      writeFileSync(`${path}.gz`,gzipSync(readFileSync(path),{level:9,mtime:0}));
  }
}
for(const entry of readdirSync(join(here,'public-release/data/v2'),{withFileTypes:true}))
  if(entry.isDirectory()&&/^FWI_[A-Z0-9_]+$/.test(entry.name))gzipFwiArtifacts(join(here,'public-release/data/v2',entry.name));
mkdirSync(join(here,'public-release/data/phase'),{recursive:true});
cpSync(phaseSource,join(here,'public-release/data/phase/stead'),{recursive:true});
cpSync(join(here,'public/svg'),join(here,'public-release/svg'),{recursive:true});
const m12Destination=join(here,'public-release/data/models/m12-physics-v2');
mkdirSync(m12Destination,{recursive:true});
cpSync(m12ModelPath,join(m12Destination,'m12-physics.onnx'));
cpSync(m12ReceiptPath,join(m12Destination,'m12-physics-browser-receipt.json'));
for(const file of courseFiles){
  const destination=join(here,'public-release/data/m01-scientific-course',file);
  mkdirSync(dirname(destination),{recursive:true});
  cpSync(join(courseSource,file),destination);
}
for(const file of fieldFiles){
  const destination=join(here,'public-release/data/field',file);
  mkdirSync(dirname(destination),{recursive:true});
  cpSync(join(fieldSource,file),destination);
}
console.log(sourceArg<0?'Copied canonical v2 experiments and reviewed M13 browser assets. No computation in build.':'Copied candidate v2 artifacts and reviewed M13 browser assets for local QA only; canonical data unchanged.');
