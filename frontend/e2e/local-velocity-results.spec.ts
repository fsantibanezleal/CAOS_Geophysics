import { test, expect, type BrowserContext, type Page } from "@playwright/test";
import { spawn, execFileSync, type ChildProcess } from "node:child_process";
import { createServer } from "node:net";
import { createHash } from "node:crypto";
import { readFileSync, readdirSync, mkdirSync, writeFileSync } from "node:fs";
import { resolve, join } from "node:path";

// Opt-in public local inspection: ORIGINAL actual producer generations, no APIs.
test.describe.configure({ mode: "serial", timeout: 180_000 });
test.use({ headless: false });
const required = (key: string) => { if (!process.env[key]) throw new Error(`Supply trusted existing ${key}`); return resolve(process.env[key]!); };
const build = required("GEOPHYSICS_VELOCITY_BUILD"), generationRoot = required("GEOPHYSICS_VELOCITY_GENERATIONS"), evidence = required("GEOPHYSICS_VELOCITY_EVIDENCE"), python = required("GEOPHYSICS_REVIEW_PYTHON");
let origin: string, server: ChildProcess, context: BrowserContext, page: Page;
const protocols = ["classical", "original", "physics-v2"] as const;
const actual = Object.fromEntries(protocols.map(p => [p, JSON.parse(readFileSync(join(generationRoot, "velocity-actual-" + p, "result.json"), "utf8"))]));
const writes: string[] = [], errors: string[] = [], outcomes: {name:string;status:string|undefined}[] = [];
const sha = (p: string) => createHash("sha256").update(readFileSync(p)).digest("hex");
function inventory(root: string, relative = ""): Record<string,string> {
  return Object.fromEntries(readdirSync(join(root,relative),{withFileTypes:true}).flatMap(f => {
    const p=join(relative,f.name); return f.isDirectory() ? Object.entries(inventory(root,p)) : [[p.replaceAll("\\","/"),sha(join(root,p))]];
  }).sort(([a],[b]) => a.localeCompare(b)));
}
let before: Record<string,string>, generationsBefore: Record<string,string>, sourceBefore: Record<string,string>;
const generations = () => Object.fromEntries(protocols.flatMap(p => ["result.json","manifest.json"].map(f => [p+"/"+f,sha(join(generationRoot,"velocity-actual-"+p,f))])));
const ownPaths = ["src/api/velocity-local-contracts.ts","src/components/VelocityLocalWorkbench.tsx","src/components/VelocityLocalInstrument.tsx","src/pages/Workbench.tsx","e2e/local-velocity-results.spec.ts"];
const sources = () => Object.fromEntries(ownPaths.map(p => [p,sha(resolve(p))]));
const started = new Date().toISOString();
test.beforeAll(async ({browser}) => {
  mkdirSync(evidence,{recursive:true}); before=inventory(build); generationsBefore=generations(); sourceBefore=sources();
  const sock=createServer(); await new Promise<void>(done=>sock.listen(0,"127.0.0.1",done)); const address=sock.address();
  if (!address || typeof address === "string") throw new Error("No loopback QA port");
  await new Promise<void>(done=>sock.close(()=>done())); origin=`http://127.0.0.1:${address.port}`;
  server=spawn(process.execPath,[resolve("node_modules/vite/bin/vite.js"),"preview","--outDir",build,"--host","127.0.0.1","--port",String(address.port),"--strictPort"],{cwd:process.cwd(),windowsHide:true,stdio:"ignore"});
  await expect.poll(async()=>{if(server.exitCode!==null)throw new Error("Owned preview exited");try{return (await fetch(origin)).ok;}catch{return false;}},{timeout:20000}).toBe(true);
  context=await browser.newContext({acceptDownloads:true,viewport:{width:1600,height:900}}); page=await context.newPage();
  page.on("pageerror",e=>errors.push(e.message)); page.on("request",r=>{if(r.method()!=="GET"&&r.url().includes("/api/"))writes.push(r.url());});
  await page.addInitScript(()=>{if(!localStorage.getItem("caos.lang"))localStorage.setItem("caos.lang","en");if(!localStorage.getItem("caos.theme"))localStorage.setItem("caos.theme","light");});
});
test.afterEach(async({},info)=>{outcomes.push({name:info.title,status:info.status});});
test.afterAll(async()=>{
  await context?.close();
  if(server?.pid&&server.exitCode===null)execFileSync(python,["-B","-c","import sys,psutil\ntry:\n p=psutil.Process(int(sys.argv[1])); c=p.children(recursive=True)\n for x in c:\n  try: x.terminate()\n  except psutil.NoSuchProcess: pass\n psutil.wait_procs(c,timeout=5); p.terminate(); p.wait(timeout=10)\nexcept psutil.NoSuchProcess: pass",String(server.pid)]);
  if(!before)return;
  const after=inventory(build), generationsAfter=generations(), sourceAfter=sources();
  writeFileSync(join(evidence,"source-and-outcomes.json"),JSON.stringify({schema:"geophysics.local-velocity-view-review/v1",started_utc:started,completed_utc:new Date().toISOString(),build_before:before,build_after:after,generations_before:generationsBefore,generations_after:generationsAfter,source_before:sourceBefore,source_after:sourceAfter,tests:outcomes,browser_errors:errors,api_writes:writes,public_no_credentials:true,api_interception:false,compute:false,host_or_field_acceptance:false},null,2));
  expect(after).toEqual(before); expect(generationsAfter).toEqual(generationsBefore); expect(sourceAfter).toEqual(sourceBefore);expect(errors).toEqual([]);expect(writes).toEqual([]);
});
const combo=(name:string)=>page.getByRole("combobox",{name,exact:true});
async function open(protocol:typeof protocols[number],es=false,width=1600) {
  await page.goto(origin+"/?instrument=velocity-local");
  if(width===390)await page.getByRole("button",{name:es?"Controles de resultado local":"Local result controls",exact:true}).click();
  await page.getByLabel(es?"result.json original":"Original result.json",{exact:true}).setInputFiles(join(generationRoot,"velocity-actual-"+protocol,"result.json"));
  await page.getByLabel(es?"manifest.json correspondiente":"Matching manifest.json",{exact:true}).setInputFiles(join(generationRoot,"velocity-actual-"+protocol,"manifest.json"));
  await page.getByRole("button",{name:es?"Abrir resultado local de velocidad":"Open local velocity result",exact:true}).click();
  await expect(page.getByTestId("velocity-local-instrument")).toBeVisible();
}
async function snapshot(label:string) {
  const [file]=await Promise.all([page.waitForEvent("download"),page.getByRole("button",{name:"Export local exact inspection JSON",exact:true}).click()]);
  const p=join(evidence,label);await file.saveAs(p);return JSON.parse(readFileSync(p,"utf8"));
}
test("public actual classical / original / physics-v2 files, no login or learned substitution",async()=>{
  for(const protocol of protocols){
    await open(protocol);const r=actual[protocol];
    await expect(combo("Returned model").locator("option")).toHaveCount(protocol==="classical"?1:2);
    if(protocol!=="classical"){await combo("Returned model").selectOption("learned");await expect(page.getByRole("status").filter({hasText:"NEGATIVE matched CNN benchmark"})).toBeVisible();}
    await combo("Selected ray").selectOption("3");await combo("x [m]").selectOption("4");await combo("Depth [m] · positive down").selectOption("5");
    await expect(page.getByTestId("velocity-ray-readout")).toContainText(String(r.request.times_s[3]));
    const saved=await snapshot(protocol+"-inspection.json");expect(saved.result).toEqual(r);expect(saved.physics_replayed).toBe(false);
    expect(saved.selected.ray.endpoints_m).toEqual(r.request.rays_m[3]);expect(saved.selected.ray.sigma_s).toBe(r.request.sigma_s[3]);
    expect(saved.selected.cell.velocity_m_s).toBe(r.results[protocol==="classical"?"classical":"learned"].velocity_m_s[5][4]);
  }
});
test("rehashed scalar corruption and wrong manifest cannot replace admitted view",async()=>{
  await open("classical");const good=actual.classical, bad=structuredClone(good);bad.results.classical.residual_s[0]+=.01;
  const buffer=Buffer.from(JSON.stringify(bad)), originalManifest=JSON.parse(readFileSync(join(generationRoot,"velocity-actual-classical","manifest.json"),"utf8"));
  const manifest={...originalManifest,result_sha256:createHash("sha256").update(buffer).digest("hex"),result_bytes:buffer.length};
  await page.getByLabel("Original result.json",{exact:true}).setInputFiles({name:"bad.json",mimeType:"application/json",buffer});
  await page.getByLabel("Matching manifest.json",{exact:true}).setInputFiles({name:"manifest.json",mimeType:"application/json",buffer:Buffer.from(JSON.stringify(manifest))});
  await page.getByRole("button",{name:"Open local velocity result",exact:true}).click();await expect(page.getByRole("alert")).toContainText("Files rejected");
  expect((await snapshot("after-scalar-rejection.json")).result).toEqual(good);
  await page.getByLabel("Original result.json",{exact:true}).setInputFiles(join(generationRoot,"velocity-actual-classical","result.json"));
  await page.getByLabel("Matching manifest.json",{exact:true}).setInputFiles(join(generationRoot,"velocity-actual-original","manifest.json"));
  await page.getByRole("button",{name:"Open local velocity result",exact:true}).click();await expect(page.getByRole("alert")).toContainText("Files rejected");
  expect((await snapshot("after-manifest-rejection.json")).result).toEqual(good);
});
test("actual pointer / keyboard linked rays and cells, display colour does not change data",async()=>{
  await open("physics-v2");
  const area=page.locator(".heatmap-area");await area.scrollIntoViewIfNeeded();const rect=(await area.boundingBox())!;
  writeFileSync(join(evidence,"pointer-map-bounds.json"),JSON.stringify({rect,viewport:page.viewportSize(),cell:[4,5]}));
  await page.mouse.move(rect.x+rect.width*4.5/16,rect.y+rect.height*5.5/16);
  await expect(page.locator(".heatmap .plot-readout")).toContainText("225");
  await page.mouse.click(rect.x+rect.width*4.5/16,rect.y+rect.height*5.5/16);
  await expect(combo("x [m]")).toHaveValue("4");await expect(combo("Depth [m] · positive down")).toHaveValue("5");
  await page.getByLabel("Colour minimum [m/s]",{exact:true}).fill("1600");await page.getByLabel("Colour maximum [m/s]",{exact:true}).fill("3200");
  expect((await snapshot("after-colour.json")).result).toEqual(actual["physics-v2"]);
  await combo("Local scientific view").selectOption("times");const graph=page.getByRole("group",{name:"Observed / returned prediction",exact:true});
  await graph.scrollIntoViewIfNeeded();const g=(await graph.boundingBox())!;await page.mouse.click(g.x+g.width*.45,g.y+g.height*.45);
  expect(Number(await combo("Selected ray").inputValue())).toBeGreaterThan(0);
  await graph.focus();await graph.press("End");await expect(combo("Selected ray")).toHaveValue("15");
  await combo("Local scientific view").selectOption("residual");await expect(page.getByRole("group",{name:"Observed minus predicted",exact:true})).toHaveAttribute("data-selected-index","15");
});
test("changing local selection discards delayed byte completion without replacing the view",async()=>{
  await open("classical");
  await page.getByLabel("Original result.json",{exact:true}).setInputFiles(join(generationRoot,"velocity-actual-original","result.json"));
  await page.getByLabel("Matching manifest.json",{exact:true}).setInputFiles(join(generationRoot,"velocity-actual-original","manifest.json"));
  // Only the local File read is delayed; no HTTP/producer data interception.
  await page.evaluate(()=>{const original=File.prototype.arrayBuffer;File.prototype.arrayBuffer=function(){const file=this;File.prototype.arrayBuffer=original;return new Promise<ArrayBuffer>(done=>{(window as unknown as {resumeVelocityRead:()=>void}).resumeVelocityRead=()=>{void original.call(file).then(done);};});};});
  await page.getByRole("button",{name:"Open local velocity result",exact:true}).click();
  await expect(page.getByRole("status").filter({hasText:"Checking original"})).toBeVisible();
  await page.getByLabel("Matching manifest.json",{exact:true}).setInputFiles(join(generationRoot,"velocity-actual-classical","manifest.json"));
  await page.evaluate(()=>(window as unknown as {resumeVelocityRead:()=>void}).resumeVelocityRead());
  expect((await snapshot("after-stale-read.json")).result).toEqual(actual.classical);
});
test("six real local views EN/ES light/dark four viewports",async()=>{
  test.setTimeout(240000);
  for(const lang of ["en","es"])for(const theme of ["light","dark"])for(const [width,height] of [[1280,800],[1600,900],[2560,1440],[390,844]]){
    const es=lang==="es";await page.setViewportSize({width,height});
    // Current document only: no mandatory native-controller or property override.
    await page.evaluate(({lang,theme})=>{localStorage.setItem("caos.lang",lang);localStorage.setItem("caos.theme",theme);},{lang,theme});
    // This spec's initialization applies defaults only; keep selected matrix language.
    await open("physics-v2",es,width);
    for(const view of ["velocity","coverage","geometry","times","residual","standardized"]){
      await combo(es?"Vista científica local":"Local scientific view").selectOption(view);
      const main=page.locator(".processing-main");await main.evaluate(el=>{el.scrollTop=0;});
      expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
      for(const graph of await main.locator('svg[role="group"]').all()){await graph.scrollIntoViewIfNeeded();await graph.focus();await graph.press("End");expect(await graph.getAttribute("data-selected-index")).not.toBeNull();}
      await main.locator(".science-plot").scrollIntoViewIfNeeded();
      if(view==="geometry")await expect(main.locator(".science-plot svg path[stroke]")).not.toHaveCount(0);
      await page.screenshot({path:join(evidence,`${lang}-${theme}-${width}-${view}.png`)});
    }
  }
});
