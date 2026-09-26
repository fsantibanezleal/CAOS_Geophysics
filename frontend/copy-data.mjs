import {cpSync,existsSync,mkdirSync} from 'node:fs';
import {dirname,join,resolve,relative,isAbsolute} from 'node:path';
import {fileURLToPath} from 'node:url';
const here=dirname(fileURLToPath(import.meta.url));
const sourceArg=process.argv.indexOf('--source');
const source=sourceArg<0?join(here,'../data/derived/v2'):resolve(here,process.argv[sourceArg+1]??'');
if(sourceArg>=0){
  const within=relative(resolve(here,'../data/experiments'),source);
  if(within.startsWith('..')||isAbsolute(within))throw new Error('Preview source must be an ignored data/experiments candidate.');
}
if(!existsSync(join(source,'catalog.json')))throw new Error('Missing committed v2 catalogue; run scripts/precompute first.');
mkdirSync(join(here,'public-release/data/v2'),{recursive:true});
cpSync(source,join(here,'public-release/data/v2'),{recursive:true});
cpSync(join(here,'public/svg'),join(here,'public-release/svg'),{recursive:true});
console.log(sourceArg<0?'Copied canonical v2 experiments and checkpoints. No computation in build.':'Copied candidate artifacts for local QA only; canonical data unchanged.');
