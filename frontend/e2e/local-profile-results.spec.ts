import { test, expect, type BrowserContext, type Page } from "@playwright/test";
import { spawn, execFileSync, type ChildProcess } from "node:child_process";
import { createServer } from "node:net";
import { createHash } from "node:crypto";
import { readFileSync, readdirSync, mkdirSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";

test.describe.configure({mode:"serial"});
const required=(key:string)=>{if(!process.env[key])throw new Error(`Supply ${key}`);return resolve(process.env[key]!);};
const build=required("GEOPHYSICS_PROFILE_BUILD"),evidence=required("GEOPHYSICS_PROFILE_EVIDENCE"),python=required("GEOPHYSICS_REVIEW_PYTHON");
const roots={ert:required("GEOPHYSICS_PROFILE_ERT"),traveltime:required("GEOPHYSICS_PROFILE_TRAVELTIME")};
const actual=Object.fromEntries(Object.entries(roots).map(([key,root])=>[key,JSON.parse(readFileSync(join(root,"result.json"),"utf8"))]));
let server:ChildProcess,origin:string,context:BrowserContext,page:Page;
const errors:string[]=[],writes:string[]=[],outcomes:{name:string;status:string|undefined}[]=[];
const sha=(path:string)=>createHash("sha256").update(readFileSync(path)).digest("hex");
function inventory(root:string,relative=""):Record<string,string>{return Object.fromEntries(readdirSync(join(root,relative),{withFileTypes:true}).flatMap(f=>{const p=join(relative,f.name);return f.isDirectory()?Object.entries(inventory(root,p)):[[p.replaceAll("\\","/"),sha(join(root,p))]];}));}
const originals=()=>Object.fromEntries(Object.entries(roots).flatMap(([key,root])=>["result.json","manifest.json"].map(name=>[`${key}/${name}`,sha(join(root,name))])));
let before:Record<string,string>,filesBefore:Record<string,string>;
test.beforeAll(async({browser})=>{
  mkdirSync(evidence,{recursive:false});before=inventory(build);filesBefore=originals();
  const sock=createServer();await new Promise<void>(done=>sock.listen(0,"127.0.0.1",done));const address=sock.address();if(!address||typeof address==="string")throw new Error("No loopback port");await new Promise<void>(done=>sock.close(()=>done()));origin=`http://127.0.0.1:${address.port}`;
  server=spawn(process.execPath,[resolve("node_modules/vite/bin/vite.js"),"preview","--outDir",build,"--host","127.0.0.1","--port",String(address.port),"--strictPort"],{cwd:process.cwd(),windowsHide:true,stdio:"ignore"});
  await expect.poll(async()=>{if(server.exitCode!==null)throw new Error("Owned preview exited");try{return (await fetch(origin)).ok;}catch{return false;}},{timeout:20000}).toBe(true);
  context=await browser.newContext({viewport:{width:1600,height:900},acceptDownloads:true});page=await context.newPage();page.on("pageerror",e=>errors.push(e.message));page.on("request",r=>{if(r.method()!=="GET"&&r.url().includes("/api/"))writes.push(r.url());});
  await page.addInitScript(()=>{if(!localStorage.getItem("caos.lang"))localStorage.setItem("caos.lang","en");if(!localStorage.getItem("caos.theme"))localStorage.setItem("caos.theme","light");});
});
test.afterEach(async({},info)=>{outcomes.push({name:info.title,status:info.status});});
test.afterAll(async()=>{
  await context?.close();if(server?.pid&&server.exitCode===null)execFileSync(python,["-B","-c","import sys,psutil\ntry:\n p=psutil.Process(int(sys.argv[1])); c=p.children(recursive=True)\n for x in c:\n  try: x.terminate()\n  except psutil.NoSuchProcess: pass\n psutil.wait_procs(c,timeout=5);p.terminate();p.wait(timeout=10)\nexcept psutil.NoSuchProcess:pass",String(server.pid)]);
  if(!before)return;const after=inventory(build),filesAfter=originals();writeFileSync(join(evidence,"outcomes.json"),JSON.stringify({schema:"geophysics.supplied-profile-visual-review/v1",build_before:before,build_after:after,files_before:filesBefore,files_after:filesAfter,outcomes,browser_errors:errors,api_writes:writes,api_interception:false,physics_replayed:false},null,2));expect(after).toEqual(before);expect(filesAfter).toEqual(filesBefore);expect(errors).toEqual([]);expect(writes).toEqual([]);
});
async function open(method:keyof typeof roots,es=false,width=1600){
  await page.goto(origin+"/?instrument=profile-local");if(width===390)await page.getByRole("button",{name:es?"Controles de perfil local":"Local profile controls",exact:true}).click();
  await page.getByLabel(es?"result.json original":"Original result.json",{exact:true}).setInputFiles(join(roots[method],"result.json"));await page.getByLabel(es?"manifest.json correspondiente":"Matching manifest.json",{exact:true}).setInputFiles(join(roots[method],"manifest.json"));await page.getByRole("button",{name:es?"Abrir resultado de perfil local":"Open local profile result",exact:true}).click();await expect(page.getByTestId("profile-local-instrument")).toBeVisible();
}
async function download(name:string){const [file]=await Promise.all([page.waitForEvent("download"),page.getByRole("button",{name:"Export exact local inspection JSON",exact:true}).click()]);const path=join(evidence,name);await file.saveAs(path);return JSON.parse(readFileSync(path,"utf8"));}
test("actual ERT / Dijkstra native cells, exact linked rows, folds and export",async()=>{
  for(const method of ["ert","traveltime"] as const){await open(method);const r=actual[method],m=method==="ert"?r.engine_report.inverse:r.engine_report.inverse.interleaved;
    await expect(page.locator("polygon[data-cell-index]")).toHaveCount(m.mesh_cells);
    await page.getByRole("combobox",{name:"Original measurement row",exact:true}).selectOption("3");await page.getByLabel("Native model cell",{exact:true}).fill("4");
    const saved=await download(method+"-inspection.json");expect(saved.result).toEqual(r);expect(saved.selected.row.index).toBe(3);expect(saved.selected.cell.index).toBe(4);expect(saved.selected.cell.value).toBe(method==="ert"?m.model_resistivity_ohm_m[4]:m.model_velocity_m_s[4]);
    const graph=page.getByRole("group",{name:"Native parameter mesh",exact:true});await graph.focus();await graph.press("ArrowRight");await expect(page.getByLabel("Native model cell",{exact:true})).toHaveValue("5");
    if(method==="traveltime"){await page.getByRole("combobox",{name:"Returned fit",exact:true}).selectOption("1");expect((await download("blocked-inspection.json")).selected.fold).toBe("central_block");}
    await page.getByRole("button",{name:"Play acquisition rows",exact:true}).click();await expect.poll(async()=>Number(await page.getByRole("combobox",{name:"Original measurement row",exact:true}).inputValue())).not.toBe(3);await page.getByRole("button",{name:"Pause row playback",exact:true}).click();
  }
});
test("wrong original manifest cannot replace previous admitted result",async()=>{
  await open("ert");await page.getByLabel("Matching manifest.json",{exact:true}).setInputFiles(join(roots.traveltime,"manifest.json"));await page.getByRole("button",{name:"Open local profile result",exact:true}).click();await expect(page.getByRole("alert")).toContainText("Files rejected");expect((await download("after-manifest-refusal.json")).result).toEqual(actual.ert);
});
test("actual EN/ES light/dark phone and desktop linked maps / residuals",async()=>{
  test.setTimeout(240000);
  for(const lang of ["en","es"])for(const theme of ["light","dark"])for(const [width,height] of [[1600,900],[390,844]])for(const method of ["ert","traveltime"] as const){
    const es=lang==="es";await page.setViewportSize({width,height});await page.evaluate(({lang,theme})=>{localStorage.setItem("caos.lang",lang);localStorage.setItem("caos.theme",theme);},{lang,theme});await open(method,es,width);
    const main=page.locator(".processing-main");await main.locator(".science-plot").first().scrollIntoViewIfNeeded();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await page.screenshot({path:join(evidence,`${lang}-${theme}-${width}-${method}-mesh.png`)});
    await page.getByRole("combobox",{name:es?"Vista de mediciones":"Measurement view",exact:true}).selectOption("standardized");const curve=page.getByRole("group",{name:es?"Residual / sigma supuesta":"Residual / assumed sigma",exact:true});await curve.scrollIntoViewIfNeeded();await curve.focus();await curve.press("End");await expect(curve).toHaveAttribute("data-selected-index",String(actual[method].geometry.row_ids_zero_based.length-1));await page.screenshot({path:join(evidence,`${lang}-${theme}-${width}-${method}-residual.png`)});
  }
});
