import {it,expect,vi} from "vitest";
import {readFile} from "node:fs/promises";
import {readdirSync,statSync} from "node:fs";
import {join,relative} from "node:path";
import {performance} from "node:perf_hooks";
import {importJointOutput,type JointFile} from "../api/joint-result";

it("profiles original small native intake without altering bytes or predicates",async()=>{
  const root=process.env.GEOPHYSICS_JOINT_MATRIX_FIXTURE;if(!root)throw new Error("Actual external originals required");
  let hashMs=0,readMs=0,hashes=0;const digest=crypto.subtle.digest.bind(crypto.subtle);
  const spy=vi.spyOn(crypto.subtle,"digest").mockImplementation(async(...args)=>{const at=performance.now();try{return await digest(...args);}finally{hashMs+=performance.now()-at;hashes++;}});
  try {for(const i of [0,8,16,23]){
    const path=join(root,`joint-control-${String(i).padStart(2,"0")}`,"output"),files:JointFile[]=[];let bytes=0;
    const start=performance.now();hashMs=readMs=hashes=0;
    function visit(dir:string){for(const name of readdirSync(dir)){const p=join(dir,name),s=statSync(p);if(s.isDirectory())visit(p);else{bytes+=s.size;files.push({path:relative(path,p).replaceAll("\\","/"),size:s.size,read:async()=>{const at=performance.now();try{return new Uint8Array(await readFile(p));}finally{readMs+=performance.now()-at;}}});}}}
    visit(path);const listed=performance.now(),actual=await importJointOutput(files);
    expect(actual.candidates).toHaveLength(26);expect(actual.limitations.scientific_acceptance_verified).toBe(false);
    process.stdout.write(JSON.stringify({case:i,bytes,members:files.length,list_ms:listed-start,import_ms:performance.now()-listed,read_sum_ms:readMs,hash_sum_ms:hashMs,hashes})+"\n");
  }} finally {spy.mockRestore();}
});
