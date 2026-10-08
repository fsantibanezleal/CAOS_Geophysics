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
const {verifyMagneticView,magneticCells,magneticProjection,magneticSpectrum}=await import(pathToFileURL(compiled).href);
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
const cameraAngles=[0,35,90,180,270,360];
for(const angle of cameraAngles){
  const c=magneticProjection(parsed,angle), base=c.project(c.origin_m), a=angle*Math.PI/180;
  const deltas=[[Math.cos(a),.5*Math.sin(a)],[-Math.sin(a),.5*Math.cos(a)],[0,-Math.sqrt(3)/2]];
  for(let axis=0;axis<3;axis++){const p=c.project(c.origin_m.map((v,k)=>v+(axis===k?1:0)));for(let j=0;j<2;j++)if(Math.abs((p[j]-base[j])-c.scale*deltas[axis][j])>1e-10)throw Error("Physical orthographic camera unit scale differs");}
  for(let i=0;i<8;i++){const xyz=c.origin_m.map((v,k)=>v+((i>>k)&1?c.widths_m[k]:0)),p=c.project(xyz),q=c.slice(xyz);if(p[0]<45-1e-10||p[0]>655+1e-10||p[1]<45-1e-10||p[1]>395+1e-10||q[0]<45-1e-10||q[0]>655+1e-10||q[1]<45-1e-10||q[1]>395+1e-10)throw Error("Complete physical mesh edges clipped");}
}
const proof={schema:"magnetic-frontend-numeric-parity-1",generation_sha256:value.binding.generation_sha256,view_sha256:createHash("sha256").update(raw).digest("hex"),rows:parsed.rows.length,active_cells:cells.length,rejected_binding_fields:rejected,actual_numeric_tamper_rejected:true,native_descriptors_sha256_verified:true,physical_orthographic_camera_unit_scale_verified:true,full_mesh_edge_angles_checked:cameraAngles,spectra,api_owner_mounted:false,browser_verified:false,field_accepted:false};
await writeFile(output,JSON.stringify(proof),{flag:"wx"});console.log(JSON.stringify(proof));
