/** Real magnetic leaf browser matrix; build/captures only in explicit temp root. */
import { createServer } from "node:http";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { resolve, dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createHash } from "node:crypto";
const args=process.argv.slice(2),arg=k=>{const i=args.indexOf(k);if(i<0||!args[i+1])throw Error(`Required ${k}`);return resolve(args[i+1]);};
const course=args.includes("--course");
const spectrumControls=args.includes("--spectrum-controls");
const modelControls=args.includes("--model-state-controls");
if(course&&spectrumControls)throw Error("Separate course and spectrum gates required");
if(course&&modelControls)throw Error("Separate course and saved-model gates required");
const viewPath=arg("--view"),output=arg("--output-root"),packages=arg("--packages"),bundleExport=arg("--bundle-export"),repo=resolve(dirname(fileURLToPath(import.meta.url)),"..");
for(const p of [viewPath,output,bundleExport])if(p.toLowerCase().startsWith("d:\\_repos\\")||p.toLowerCase().startsWith("e:\\_worktrees\\"))throw Error("Explicit external artifacts required");
await mkdir(output); // Fresh directory only, never reuse or delete prior proof.
const {build}=await import(pathToFileURL(join(packages,"esbuild/lib/main.js")).href);
const shellRaw=await readFile(join(packages,"@fasl-work/caos-app-shell/package.json")),shellVersion=JSON.parse(shellRaw).version;
if(shellVersion!=="0.8.1")throw Error("Explicit current shared shell0.8.1 required; no stale local resolution");
const alias=Object.fromEntries(["@fasl-work/caos-app-shell","react","react-dom","react-router","katex","lucide-react"].map(name=>[name,join(packages,name)]));
alias["@fasl-work/caos-app-shell/styles.css"]=join(packages,"@fasl-work/caos-app-shell/styles.css");
alias["@fasl-work/caos-app-shell"]=join(packages,"@fasl-work/caos-app-shell/dist/index.js");
alias["react-router"]=join(packages,"react-router/dist/production/index.js");
const spectrumPlugin={name:"magnetic-spectrum-test-counter",setup(builder){
  builder.onLoad({filter:/magnetic-result\.ts$/},async ({path})=>{
    const text=await readFile(path,"utf8"),marker="export function magneticSpectrum(rows: MagneticRow[], component: number) {";
    if(text.split(marker).length!==2)throw Error("Exact production spectrum signature required for test-only counter");
    return {contents:text.replace(marker,marker+"\nglobalThis.__magneticSpectrumCalls=(globalThis.__magneticSpectrumCalls??0)+1;"),loader:"ts"};
  });
}};
await build({entryPoints:[join(repo,"tests/ui/magnetic_leaf.tsx")],outfile:join(output,"leaf.js"),bundle:true,format:"esm",platform:"browser",nodePaths:[packages],alias,plugins:spectrumControls?[spectrumPlugin]:[],jsx:"automatic",loader:{".woff":"dataurl",".woff2":"dataurl",".ttf":"dataurl"},define:{"process.env.NODE_ENV":"\"production\""}});
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
    await page.goto(`${origin}/?lang=${lang}&theme=${theme}${course?"&course=1":""}`);
    if(course){
      const root=page.locator(".magnetic-course");await root.waitFor();
      if(await root.getAttribute("data-generation")!==v.binding.generation_sha256)throw Error("Course result binding differs");
      const chapter=root.locator("select"),count=await chapter.locator("option").count(),lessons=[];
      if(count!==9)throw Error("Complete nine-chapter course required");
      for(let k=0;k<count;k++){await chapter.selectOption(String(k));await root.locator(".katex").first().waitFor();
        if(await root.locator(".katex-error").count())throw Error("Equation failed to render");
        if(await root.locator("article > .equation, article .katex-display").count()<2||await root.locator("[data-magnetic-method-diagram]").count()!==1)throw Error("Complete derivation equations and conceptual figure required");
        if(await root.locator("article > p").count()<5)throw Error("Research derivation and worked question depth missing");
        const inline=await root.locator("article > p:first-of-type .cite-inline a").evaluateAll(links=>links.map(a=>a.href));
        const section=await root.locator("article > .th-refs .cite-inline a").evaluateAll(links=>links.map(a=>a.href));
        if(inline.length<1||JSON.stringify(inline)!==JSON.stringify(section)||inline.some(url=>!url.startsWith("https://raw.githubusercontent.com/")))throw Error("Chapter inline/section primary references differ or are unresolved");
        if(await root.locator("article ul, article .reference-list").count())throw Error("Custom bibliography must not replace shell citations");
        if(/authenticated API mounting|montaje API autenticado|owner bootstrap|bootstrap de dueño/i.test(await root.innerText()))throw Error("Operational mounting backlog in scientific course");
        lessons.push(await root.getAttribute("data-lesson"));
        await page.screenshot({path:join(output,`${width}-${lang}-${theme}-chapter-${k+1}.png`),fullPage:true});
        if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1))throw Error("Course horizontal overflow");
      }
      if(new Set(lessons).size!==9||errors.length)throw Error("Course chapter control/error gate failed");
      proofs.push({width,height,lang,theme,reduced_motion:true,lessons,verified_generation:true,chapter_inline_and_section_references:true,scientific_scope:true,horizontal_overflow:false,errors});
      console.log(`PASS ${width} ${lang} ${theme} nine source-bound course chapters`);await context.close();continue;
    }
    await page.locator(".magnetic-result").waitFor();
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
    let spectrumProof=null;
    if(spectrumControls){
      const calls=()=>page.evaluate(()=>globalThis.__magneticSpectrumCalls);
      const before=await calls();if(!Number.isSafeInteger(before)||before<1)throw Error("Instrumented real spectrum invocation missing");
      const point=page.locator(".magnetic-result svg:visible circle[role=button]").nth(1);
      await point.scrollIntoViewIfNeeded();const box=await point.boundingBox();if(!box)throw Error("Original point is not pointer reachable");
      await page.mouse.move(box.x+box.width/2,box.y+box.height/2);
      await page.waitForFunction(id=>document.querySelector('.magnetic-readout')?.getAttribute('data-row-id')===id,v.rows[1].row_id);
      if(await calls()!==before)throw Error(`Pointer selection recomputed quadratic spectrum (${before} -> ${await calls()})`);
      await click(tr("Susceptibility","Susceptibilidad"));await click(tr("3D cells","Celdas 3D"));
      const rotation=page.locator(".magnetic-result label").filter({hasText:tr("View rotation (degrees; does not refit)","Rotación de vista (grados; no reajusta)")}).locator("input");
      const previous=await rotation.inputValue();await rotation.focus();await rotation.press("ArrowRight");
      if(await rotation.inputValue()===previous)throw Error("Camera control did not change");
      if(await calls()!==before)throw Error("Camera scrub recomputed spectrum");
      const target=page.locator(".magnetic-cell:visible").last();await target.scrollIntoViewIfNeeded();const cellBox=await target.boundingBox();if(!cellBox)throw Error("Physical cell is not pointer reachable");
      await page.mouse.move(cellBox.x+cellBox.width/2,cellBox.y+cellBox.height/2);
      const expectedCell=await target.getAttribute("aria-label");
      await page.waitForFunction(index=>document.querySelector('.magnetic-readout[data-cell-index]')?.getAttribute('data-cell-index')===index,expectedCell.split(':')[0]);
      if(await calls()!==before)throw Error("Cell pointer selection recomputed spectrum");
      await click(tr("Iteration","Iteración"));const history=page.locator(".magnetic-result input[type=range]:visible").first();
      if(await history.count()&&Number(await history.getAttribute('max'))>0){const previous=await history.inputValue();await history.focus();await history.press("ArrowRight");if(await history.inputValue()===previous)throw Error("Objective history control did not change");}
      if(await calls()!==before)throw Error("Objective scrub recomputed spectrum");
      const component=page.locator(".magnetic-controls select").first();
      if(await component.locator('option').count()<2)throw Error("Actual multi-component fixture required");
      await component.selectOption("1");await page.waitForFunction(n=>globalThis.__magneticSpectrumCalls>=n,before+1);
      if(await calls()!==before+1)throw Error("Component must recompute exactly once");
      spectrumProof={baseline_calls:before,pointer_camera_cell_history_calls:before,component_change_calls:before+1,group_change_calls:null};
      await click(tr("Observations","Observaciones"));await click(tr("Map","Mapa"));
    }
    let modelProof=null;
    if(modelControls){
      if(v.schema!=="magnetic-owner-result-view-2"||!v.model_states)throw Error("Actual versioned saved-model projection required");
      await click(tr("Susceptibility","Susceptibilidad"));await click(tr("3D cells","Celdas 3D"));
      const count=v.model_states.chi_si.shape[0],saved=page.locator("[data-saved-model-state]:visible"),scrub=saved.locator("input[type=range]");
      if(await scrub.getAttribute("step")!=="1"||Number(await scrub.getAttribute("max"))!==count-1||Number(await scrub.inputValue())!==count-1)throw Error("Discrete final saved model was not selected");
      const assertState=async index=>{
        const history=Number(v.model_states.history_indices.data[index]);
        if(Number(await saved.getAttribute("data-saved-model-state"))!==index||Number(await saved.getAttribute("data-saved-history-index"))!==history)throw Error("Saved model/history readout drift");
        const cell=page.locator(".magnetic-cell:visible").first();await cell.scrollIntoViewIfNeeded();await cell.focus();await cell.press("Enter");
        const k=v.model.active_indices.data.indexOf(Number((await cell.getAttribute("aria-label")).split(':')[0])),chi=Number(v.model_states.chi_si.data[index*v.model.chi_si.data.length+k]);
        const expected=new Intl.NumberFormat(lang,{maximumSignificantDigits:6}).format(chi);
        if(!(await page.locator(".magnetic-readout[data-cell-index]:visible").innerText()).includes(`χ ${expected} SI`))throw Error("Actual saved physical cell readout differs");
        if(Math.abs(Number(await cell.getAttribute("opacity"))-(.15+.65*chi/.1))>1e-14)throw Error("Opacity must use fixed 0..0.1 SI, not per-case normalization");
      };
      await assertState(count-1);
      if(count===1){if(!await scrub.isDisabled()||!/zero accepted moves|cero movimientos aceptados/.test(await saved.innerText()))throw Error("One actual state must not invent motion");}
      else {await scrub.focus();await scrub.press("Home");await assertState(0);await scrub.press("End");await assertState(count-1);}
      const finalState=await saved.getAttribute("data-saved-model-state");
      await click(tr("Iteration","Iteración"));const record=page.locator(".magnetic-result input[type=range]:visible").first();
      if(await record.count()&&Number(await record.getAttribute("max"))>0){await record.focus();await record.press("End");}
      if(!/no model replay|sin reproducción de modelo/.test(await page.locator(".magnetic-result label:visible").allTextContents().then(x=>x.join(" "))))throw Error("Objective records must not claim model replay");
      await click(tr("Susceptibility","Susceptibilidad"));await click(tr("3D cells","Celdas 3D"));
      if(await saved.getAttribute("data-saved-model-state")!==finalState)throw Error("Objective record control changed physical model");
      await assertState(count-1);
      await page.screenshot({path:join(output,`${width}-${lang}-${theme}-saved-final-model.png`),fullPage:true});
      modelProof={schema:v.model_states.schema,count,initially_final:true,discrete_indices:true,exact_history_mapping:true,actual_cell_SI:true,fixed_opacity_range_SI:[0,.1],zero_move_no_motion:count===1,objective_records_do_not_change_model:true};
      await click(tr("Observations","Observaciones"));await click(tr("Map","Mapa"));
    }
    await page.locator(".magnetic-result label").filter({hasText:tr("Original acquisition group","Grupo de adquisición original")}).locator("select").selectOption(v.rows.find(r=>r.group_id!==v.rows[0].group_id).group_id);
    if(spectrumControls){await page.waitForFunction(n=>globalThis.__magneticSpectrumCalls>=n,spectrumProof.component_change_calls+1);spectrumProof.group_change_calls=await page.evaluate(()=>globalThis.__magneticSpectrumCalls);if(spectrumProof.group_change_calls!==spectrumProof.component_change_calls+1)throw Error("Group must recompute exactly once");}
    const selected=await page.locator(".magnetic-readout:visible").first().getAttribute("data-row-id");
    if(selected===v.rows[0].row_id)throw Error("Original group control is a no-op");
    await click(tr("Flight","Vuelo"));if(await page.locator(".magnetic-readout:visible").first().getAttribute("data-row-id")!==selected)throw Error("Map/flight linked row changed");
    const downloadEvent=page.waitForEvent("download");await page.getByRole("button",{name:tr("Export verified numeric bundle","Exportar bundle numérico verificado"),exact:true}).click();
    const download=await downloadEvent, downloaded=join(output,`${width}-${lang}-${theme}-numeric.zip`);await download.saveAs(downloaded);
    if(createHash("sha256").update(await readFile(downloaded)).digest("hex")!==zipHash)throw Error("Browser numeric export bytes changed");
    if(errors.length)throw Error(errors.join("\n"));
    proofs.push({width,height,lang,theme,reduced_motion:true,views:visited,same_original_row_linked:true,horizontal_overflow:false,numeric_export_sha256:zipHash,spectrum_recomputation:spectrumProof,saved_models:modelProof,errors});
    console.log(`PASS ${width} ${lang} ${theme} eight scientific leaf views`);await context.close();
  }
  const proof={schema:course?"magnetic-local-course-browser-proof-1":"magnetic-local-browser-proof-1",view_sha256:createHash("sha256").update(raw).digest("hex"),generation_sha256:v.binding.generation_sha256,shell_version:shellVersion,shell_package_sha256:createHash("sha256").update(shellRaw).digest("hex"),instrumented_spectrum_counter:spectrumControls,component_sha256:createHash("sha256").update(await readFile(join(repo,"frontend/src/components/MagneticSurveyResult.tsx"))).digest("hex"),spectrum_source_sha256:createHash("sha256").update(await readFile(join(repo,"frontend/src/api/magnetic-result.ts"))).digest("hex"),states:proofs,authenticated_api:false,field_acceptance:false,online_admitted:false};
  await writeFile(join(output,"browser-proof.json"),JSON.stringify(proof),{flag:"wx"});
}catch(error){
  await writeFile(join(output,"failed-browser-proof.json"),JSON.stringify({status:"FAIL",error:String(error),completed_states:proofs,instrumented_spectrum_counter:spectrumControls,component_sha256:createHash("sha256").update(await readFile(join(repo,"frontend/src/components/MagneticSurveyResult.tsx"))).digest("hex"),scientific_acceptance:false,authenticated_api:false}),{flag:"wx"});throw error;
}finally{if(browser)await browser.close();await new Promise(r=>server.close(r));}
