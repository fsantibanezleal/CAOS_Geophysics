/** Real complete native generation -> browser-contract/math parity, external only. */
import { readFile, writeFile } from "node:fs/promises";
import { createHash, webcrypto } from "node:crypto";
import { resolve, dirname, join } from "node:path";
import { pathToFileURL, fileURLToPath } from "node:url";
const args=process.argv.slice(2), flag=k=>{const i=args.indexOf(k);if(i<0||!args[i+1])throw Error(`Required ${k}`);return resolve(args[i+1]);};
const viewPath=flag("--view"), output=flag("--output"), packages=flag("--packages");
const repo=resolve(dirname(fileURLToPath(import.meta.url)),"..");
for (const p of [viewPath,output]) if (p.toLowerCase().startsWith(repo.toLowerCase()+"\\") || p.toLowerCase().startsWith("d:\\_repos\\") || p.toLowerCase().startsWith("e:\\_worktrees\\")) throw Error("External artifact roots required");
const {build}=await import(pathToFileURL(join(packages,"esbuild/lib/main.js")).href);
const compiled=join(dirname(output),"magnetic-contract-parity.mjs");
await build({entryPoints:[join(repo,"frontend/src/api/magnetic-result.ts")],outfile:compiled,bundle:true,format:"esm",platform:"node"});
const {verifyMagneticView,magneticCells,magneticSpectrum}=await import(pathToFileURL(compiled).href);
globalThis.crypto ??= webcrypto;
const raw=await readFile(viewPath),value=JSON.parse(raw);
const parsed=await verifyMagneticView(value,value.binding),cells=magneticCells(parsed);
if(cells.length!==parsed.model.chi_si.data.length || parsed.rows.some((r,i)=>r.row!==i))throw Error("Complete original/model inventory parity failed");
const rejected=[];
for(const field of ["source_id","original_sha256","configuration_sha256","generation_sha256","job_id","dataset_id"]){
  const expected={...value.binding,[field]:"changed"};
  try{await verifyMagneticView(value,expected);throw Error("Unexpected accepted selected receipt");}catch(error){if(String(error).includes("Unexpected"))throw error;rejected.push(field);}
}
const tampered=structuredClone(value);tampered.model.chi_si.data[0]=.00001;
try{await verifyMagneticView(tampered,value.binding);throw Error("Unexpected numeric tamper accepted");}catch(error){if(String(error).includes("Unexpected"))throw error;}
const spectra=[...new Set(parsed.rows.map(r=>r.group_id))].map(group=>{const rows=parsed.rows.filter(r=>r.group_id===group);return {group,available:magneticSpectrum(rows,0)!==null};});
const proof={schema:"magnetic-frontend-numeric-parity-1",generation_sha256:value.binding.generation_sha256,view_sha256:createHash("sha256").update(raw).digest("hex"),rows:parsed.rows.length,active_cells:cells.length,rejected_binding_fields:rejected,actual_numeric_tamper_rejected:true,native_descriptors_sha256_verified:true,spectra,api_owner_mounted:false,browser_verified:false,field_accepted:false};
await writeFile(output,JSON.stringify(proof),{flag:"wx"});console.log(JSON.stringify(proof));
