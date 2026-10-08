/** Real magnetic leaf browser matrix; build/captures only in explicit temp root. */
import { createServer } from "node:http";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { resolve, dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createHash } from "node:crypto";
const args=process.argv.slice(2),arg=k=>{const i=args.indexOf(k);if(i<0||!args[i+1])throw Error(`Required ${k}`);return resolve(args[i+1]);};
const viewPath=arg("--view"),output=arg("--output-root"),packages=arg("--packages"),bundleExport=arg("--bundle-export"),repo=resolve(dirname(fileURLToPath(import.meta.url)),"..");
for(const p of [viewPath,output,bundleExport])if(p.toLowerCase().startsWith("d:\\_repos\\")||p.toLowerCase().startsWith("e:\\_worktrees\\"))throw Error("Explicit external artifacts required");
await mkdir(output); // Fresh directory only, never reuse or delete prior proof.
const {build}=await import(pathToFileURL(join(packages,"esbuild/lib/main.js")).href);
await build({entryPoints:[join(repo,"tests/ui/magnetic_leaf.tsx")],outfile:join(output,"leaf.js"),bundle:true,format:"esm",platform:"browser",nodePaths:[packages],jsx:"automatic",loader:{".woff":"dataurl",".woff2":"dataurl",".ttf":"dataurl"},define:{"process.env.NODE_ENV":"\"production\""}});
const raw=await readFile(viewPath),v=JSON.parse(raw), receipt=JSON.stringify(v.binding);
const zip=await readFile(bundleExport);if(zip.length>128*1024**2)throw Error("Bounded actual numeric ZIP required");
const zipHash=createHash("sha256").update(zip).digest("hex");
const html='<!doctype html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Private magnetic leaf QA</title><link rel="stylesheet" href="/leaf.css"></head><body><div id="root"></div><script type="module" src="/leaf.js"></script></body></html>';
const server=createServer(async(req,res)=>{
  try{
    const p=new URL(req.url,"http://127.0.0.1").pathname;
    if(p==="/favicon.ico"){res.writeHead(204);res.end();return;}
    if(req.method==="GET"&&p==="/export.zip"){res.setHeader("Content-Type","application/zip");res.setHeader("Content-Disposition","attachment; filename=magnetic-numeric.zip");res.end(zip);return;}
    if(req.method!=="GET"||!["/","/leaf.js","/leaf.css","/view.json","/receipt.json"].includes(p)){res.writeHead(404);res.end();return;}
    res.setHeader("Cache-Control","no-store");res.setHeader("Content-Type",p==="/"?"text/html; charset=utf-8":p.endsWith(".js")?"text/javascript; charset=utf-8":p.endsWith(".css")?"text/css; charset=utf-8":"application/json");
    res.end(p==="/"?html:p==="/view.json"?raw:p==="/receipt.json"?receipt:await readFile(join(output,p.slice(1))));
  }catch(error){res.writeHead(500);res.end(String(error));}
});
await new Promise(r=>server.listen(0,"127.0.0.1",r));
const origin=`http://127.0.0.1:${server.address().port}`;
const {chromium}=await import(pathToFileURL(join(packages,"playwright-core/index.mjs")).href);
let browser;const proofs=[];
try{
  browser=await chromium.launch({headless:true});
  for(const [width,height] of [[1280,800],[390,844]])for(const lang of ["en","es"])for(const theme of ["light","dark"]){
    const context=await browser.newContext({viewport:{width,height},reducedMotion:"reduce"}),page=await context.newPage(),errors=[];
    page.on("pageerror",e=>errors.push(String(e)));page.on("console",m=>{if(m.type()==="error")errors.push(m.text());});
    page.on("response",r=>{if(r.status()>=400)errors.push(`${r.status()} ${r.url()}`);});
    await page.goto(`${origin}/?lang=${lang}&theme=${theme}`);await page.locator(".magnetic-result").waitFor();
    if(await page.locator(".magnetic-result").getAttribute("data-generation")!==v.binding.generation_sha256)throw Error("Wrong generation displayed");
    const tr=(en,es)=>lang==="es"?es:en,visited=[];
    const click=async(name)=>{const tab=page.getByRole("tab",{name,exact:true});await tab.scrollIntoViewIfNeeded();const box=await tab.boundingBox();if(!box)throw Error(`Unreachable ${name}`);await page.mouse.click(box.x+box.width/2,box.y+box.height/2);};
    const views=[
      [tr("Observations","Observaciones"),tr("Map","Mapa")],
      [tr("Observations","Observaciones"),tr("Flight","Vuelo")],
      [tr("Observations","Observaciones"),tr("Residual","Residuo")],
      [tr("Susceptibility","Susceptibilidad"),tr("3D cells","Celdas 3D")],
      [tr("Susceptibility","Susceptibilidad"),tr("Depth slice","Corte en profundidad")],
      [tr("Resolution","Resolución"),null],[tr("Iteration","Iteración"),null],[tr("Residual spectrum","Espectro residual"),null]
    ];
    for(const [group,sub] of views){await click(group);if(sub)await click(sub);await page.locator(".magnetic-result svg:visible").waitFor();
      const label=sub??group;visited.push(label);
      await page.screenshot({path:join(output,`${width}-${lang}-${theme}-${visited.length}.png`),fullPage:true});
      if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1))throw Error(`Horizontal overflow ${width} ${label}`);
    }
    await click(tr("Observations","Observaciones"));await click(tr("Map","Mapa"));
    await page.locator(".magnetic-result label").filter({hasText:tr("Original acquisition group","Grupo de adquisición original")}).locator("select").selectOption(v.rows.find(r=>r.group_id!==v.rows[0].group_id).group_id);
    const selected=await page.locator(".magnetic-readout:visible").first().getAttribute("data-row-id");
    if(selected===v.rows[0].row_id)throw Error("Original group control is a no-op");
    await click(tr("Flight","Vuelo"));if(await page.locator(".magnetic-readout:visible").first().getAttribute("data-row-id")!==selected)throw Error("Map/flight linked row changed");
    const downloadEvent=page.waitForEvent("download");await page.getByRole("button",{name:tr("Export verified numeric bundle","Exportar bundle numérico verificado"),exact:true}).click();
    const download=await downloadEvent, downloaded=join(output,`${width}-${lang}-${theme}-numeric.zip`);await download.saveAs(downloaded);
    if(createHash("sha256").update(await readFile(downloaded)).digest("hex")!==zipHash)throw Error("Browser numeric export bytes changed");
    if(errors.length)throw Error(errors.join("\n"));
    proofs.push({width,height,lang,theme,reduced_motion:true,views:visited,same_original_row_linked:true,horizontal_overflow:false,numeric_export_sha256:zipHash,errors});
    console.log(`PASS ${width} ${lang} ${theme} eight scientific leaf views`);await context.close();
  }
  const proof={schema:"magnetic-local-browser-proof-1",view_sha256:createHash("sha256").update(raw).digest("hex"),generation_sha256:v.binding.generation_sha256,states:proofs,authenticated_api:false,field_acceptance:false,online_admitted:false};
  await writeFile(join(output,"browser-proof.json"),JSON.stringify(proof),{flag:"wx"});
}finally{if(browser)await browser.close();await new Promise(r=>server.close(r));}
