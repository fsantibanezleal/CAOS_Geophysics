import {cpSync,existsSync,mkdirSync,lstatSync,readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {dirname,join,resolve,relative,isAbsolute} from 'node:path';
import {fileURLToPath} from 'node:url';
const here=dirname(fileURLToPath(import.meta.url));
const sourceArg=process.argv.indexOf('--source');
const source=sourceArg<0?join(here,'../data/derived/v2'):resolve(here,process.argv[sourceArg+1]??'');
const phaseSource=join(here,'../data/derived/phase/browser-assets/stead');
const courseSource=join(here,'../data/derived/m01-scientific-course');
const courseIndex=JSON.parse(readFileSync(join(here,'src/data/m01-course-record-index.json'),'utf8'));
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
if(sourceArg>=0){
  const within=relative(resolve(here,'../data/experiments'),source);
  if(within.startsWith('..')||isAbsolute(within))throw new Error('Preview source must be an ignored data/experiments candidate.');
}
if(!existsSync(join(source,'catalog.json')))throw new Error('Missing committed v2 catalogue; run scripts/precompute first.');
if(!existsSync(join(phaseSource,'manifest.json')))throw new Error('Missing reviewed M13 browser assets; run scripts/export_stead_browser_assets.py after the held-out benchmark.');
mkdirSync(join(here,'public-release/data/v2'),{recursive:true});
cpSync(source,join(here,'public-release/data/v2'),{recursive:true});
mkdirSync(join(here,'public-release/data/phase'),{recursive:true});
cpSync(phaseSource,join(here,'public-release/data/phase/stead'),{recursive:true});
cpSync(join(here,'public/svg'),join(here,'public-release/svg'),{recursive:true});
for(const file of courseFiles){
  const destination=join(here,'public-release/data/m01-scientific-course',file);
  mkdirSync(dirname(destination),{recursive:true});
  cpSync(join(courseSource,file),destination);
}
console.log(sourceArg<0?'Copied canonical v2 experiments and reviewed M13 browser assets. No computation in build.':'Copied candidate v2 artifacts and reviewed M13 browser assets for local QA only; canonical data unchanged.');
