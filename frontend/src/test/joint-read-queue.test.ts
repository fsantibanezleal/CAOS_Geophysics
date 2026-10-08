import {it,expect} from "vitest";
import {readFileSync,readdirSync,statSync} from "node:fs";
import {join,relative} from "node:path";
import {importJointOutput,type JointFile} from "../api/joint-result";

it("starts the fifth real small header before a delayed first read, with only four live slots",async()=>{
  const root=process.env.GEOPHYSICS_JOINT_OUTPUT_FIXTURE;if(!root)throw new Error("Actual external original output required");
  let started=0,live=0,peak=0,firstReleased=false;let release!:()=>void;
  const held=new Promise<void>(resolve=>{release=()=>{firstReleased=true;resolve();};}),files:JointFile[]=[];
  function visit(dir:string){for(const name of readdirSync(dir)){const path=join(dir,name),info=statSync(path);if(info.isDirectory())visit(path);else files.push({path:relative(root!,path).replaceAll("\\","/"),size:info.size,read:async()=>{
    const bytes=new Uint8Array(readFileSync(path));if(!path.endsWith(".npy"))return bytes;
    const order=++started;live++;peak=Math.max(peak,live);
    try {if(order===1)await held;if(order===5){expect(firstReleased).toBe(false);release();}return bytes;}
    finally {live--;}
  }});}}
  visit(root);
  try {const actual=await importJointOutput(files);expect(actual.candidates).toHaveLength(26);expect(peak).toBeLessThanOrEqual(4);expect(started).toBe(files.filter(f=>f.path.endsWith(".npy")).length);}
  finally {release();}
});
